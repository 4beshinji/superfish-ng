# SPDX-License-Identifier: Apache-2.0
"""Reflect one end symmetry plane, without another solve or amplitude fitting."""
from dataclasses import replace
import numpy as np
from .fem import assemble
from .mesh import Mesh, element_geometry
from .solver import Solution


def reflect_solution(case, solution):
    """Return the mirrored full cavity and its parity-filtered FEM fields.

    Exactly one endpoint must be a symmetry plane and the other PEC. Amplitudes
    are unchanged, so energy and loss double. The original mode indices are a
    subset of the full spectrum, not its global frequency ranks.
    """
    sides = [side for side in ('z_min', 'z_max') if getattr(case, side) != 'pec']
    if len(sides) != 1:
        raise ValueError('reflection requires exactly one symmetry end and one PEC end')
    side = sides[0]
    acceleration = case.reflected_acceleration_parameters(side)
    tag = getattr(case, side)
    parity = 1 if tag == 'electric_symmetry' else -1
    mesh = solution.mesh
    plane = 0. if side == 'z_min' else case.length
    on_plane = mesh.points[:, 1] == plane
    if parity == -1 and np.any(solution.u[on_plane] != 0.):
        raise ValueError('magnetic symmetry requires zero u at the reflection plane')
    original = mesh.points.copy()
    mirrored = original.copy()
    mirrored[:, 1] = 2*plane-mirrored[:, 1]
    if side == 'z_min':
        original[:, 1] += case.length
        mirrored[:, 1] += case.length
        profile = tuple((case.length-z, r) for z, r in reversed(case.profile))
        profile += tuple((case.length+z, r) for z, r in case.profile[1:])
        count = len(case.profile)
        arcs = tuple((count-i, radius, direction) for i, radius, direction in case.arcs)
        arcs += tuple((count-1+i, radius, direction) for i, radius, direction in case.arcs)
    else:
        profile = case.profile + tuple((2*case.length-z, r) for z, r in reversed(case.profile[:-1]))
        arcs = case.arcs+tuple((2*len(case.profile)-1-i, radius, direction) for i, radius, direction in case.arcs)
    mapping = np.arange(len(original))
    mapping[~on_plane] = np.arange(len(original), len(original)+np.count_nonzero(~on_plane))
    points = np.vstack((original, mirrored[~on_plane]))
    triangles = np.vstack((mesh.triangles, mapping[mesh.triangles][:, [0, 2, 1]]))
    keep = mesh.boundary_tags != tag
    edges = np.vstack((mesh.boundary_edges[keep], mapping[mesh.boundary_edges[keep]]))
    cells = np.concatenate((mesh.boundary_cells[keep], mesh.boundary_cells[keep]+len(mesh.triangles)))
    tags = np.tile(mesh.boundary_tags[keep], 2)
    axis = np.flatnonzero(points[:, 0] == 0.)
    axis = axis[np.argsort(points[axis, 1])]
    reflected = Mesh(points, triangles, edges, tags, cells, axis)
    element_geometry(reflected)
    u = np.vstack((solution.u, parity*solution.u[~on_plane]))
    k, m = assemble(reflected)
    ku, mu = k @ u, m @ u
    residuals = np.linalg.norm(ku-mu*solution.eigenvalues, axis=0)/(np.linalg.norm(ku, axis=0)+solution.eigenvalues*np.linalg.norm(mu, axis=0))
    if np.max(residuals) > 1e-7:
        raise ValueError('reflected full-domain field fails the free-equation residual check')
    gram = u.T @ mu
    norms = np.sqrt(np.diag(gram))
    orthogonality = float(np.max(np.abs(gram/np.outer(norms, norms)-np.eye(case.modes))))
    # Reflection reverses orientation, as does traversing the mirrored wall in
    # increasing z; together they preserve each minor arc's cw/ccw direction.
    full = replace(case, profile=profile, arcs=arcs, z_min='pec', z_max='pec', nz=2*case.nz,
                   normalization_j=2*case.normalization_j, name=case.name+' [reflected full cavity]', **acceleration)
    result = Solution(reflected, k, m, solution.eigenvalues.copy(), solution.frequencies_hz.copy(),
                      u, residuals, orthogonality,
                      f'{tag} reflection at {side}; parity-filtered spectrum, indices are NOT full-spectrum ranks',
                      case.to_dict())
    if solution.mesh_input is not None:
        from .mesh_input import mesh_to_dict
        result.mesh_input = mesh_to_dict(reflected)
    return full, result
