# SPDX-License-Identifier: Apache-2.0
"""Symmetric generalized eigensolve with mass diagonal equilibration."""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import diags
from scipy.sparse.linalg import eigsh, ArpackNoConvergence
from .constants import C0, MU0, TAU
from .fem import assemble
from .mesh import make_mesh


@dataclass
class Solution:
    mesh: object
    stiffness: object
    mass: object
    eigenvalues: np.ndarray
    frequencies_hz: np.ndarray
    u: np.ndarray  # columns, physical Hphi=r*u, normalized to specified U
    residuals: np.ndarray
    orthogonality_error: float
    construction: str = "direct eigensolve; mode indices within the specified boundary conditions"
    source_case: dict | None = None
    mesh_input: dict | None = None
    element_order: int = 1
    space: object | None = None


def solve(case, *, mesh_data=None):
    return _solve(case, mesh_data=mesh_data, element_order=1)


def _solve(case, *, mesh_data=None, element_order=1):
    if mesh_data is None:
        mesh = make_mesh(case)
    else:
        from .mesh_input import mesh_from_dict
        mesh = mesh_from_dict(case, mesh_data)
    space = None
    if element_order == 2:
        from .high_order import quadratic_space, assemble_p2
        space = quadratic_space(mesh)
        k, m = assemble_p2(space)
        count = len(space.dof_points)
        boundary_dofs = space.boundary_dofs
    elif element_order == 1:
        k, m = assemble(mesh)
        count = len(mesh.points)
        boundary_dofs = mesh.boundary_edges
    else:
        raise ValueError('only element orders 1 and 2 are implemented')
    constrained = np.unique(boundary_dofs[mesh.boundary_tags == "magnetic_symmetry"])
    free = np.setdiff1d(np.arange(count), constrained)
    if case.modes >= len(free)-1:
        raise ValueError("modes must be smaller than free node count minus one")
    reduced_k, reduced_m = (mat[free][:, free] for mat in (k, m))
    d = 1/np.sqrt(reduced_m.diagonal())
    scale = diags(d)
    a, b = (scale @ mat @ scale for mat in (reduced_k, reduced_m))
    # Fixed non-symmetric start excites odd/even modes reproducibly.
    start = np.random.default_rng(20260905).normal(size=len(d))
    try:
        lam, vectors = eigsh(a, k=case.modes, M=b, sigma=0., which="LM",
                             tol=1e-10, v0=start, maxiter=10000)
    except ArpackNoConvergence as exc:
        raise RuntimeError("eigensolver did not converge; refine/recondition case") from exc
    order = np.argsort(lam)
    lam = lam[order]
    u = np.zeros((count, case.modes))
    u[free] = d[:, None]*vectors[:, order]
    if np.any(lam <= 0) or not np.all(np.isfinite(lam)):
        raise RuntimeError("nonpositive/nonfinite eigenvalue in axis-connected TM cavity")
    norms = np.sqrt(np.sum(u*(m @ u), axis=0))
    u /= norms
    orthogonality = float(np.max(np.abs(u.T @ (m @ u)-np.eye(case.modes))))
    residuals = []
    for i, value in enumerate(lam):
        # Essential-boundary rows are reactions, not free-equation residuals.
        ku, mu = (k @ u[:, i])[free], (m @ u[:, i])[free]
        residuals.append(np.linalg.norm(ku-value*mu)/(np.linalg.norm(ku)+value*np.linalg.norm(mu)))
        if u[np.argmax(np.abs(u[:, i])), i] < 0:
            u[:, i] *= -1
    if max(residuals) > 1e-7:
        raise RuntimeError(f"eigenpair residual too large: {max(residuals):.3g}")
    # U = mu0/2 integral |H|^2 dV = mu0*pi*u^T M u.
    u *= np.sqrt(case.normalization_j/(MU0*np.pi))
    result = Solution(mesh, k, m, lam, C0*np.sqrt(lam)/TAU, u,
                      np.array(residuals), orthogonality, element_order=element_order, space=space)
    if mesh_data is not None:
        from .mesh_input import mesh_to_dict
        result.mesh_input = mesh_to_dict(mesh)
        result.construction = 'direct eigensolve on validated external tagged mesh; mode indices within specified boundary conditions'
    return result
