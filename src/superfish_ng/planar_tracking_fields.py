# SPDX-License-Identifier: Apache-2.0
"""Physical electric Gram matrices on a declared common rectangle partition."""
import numpy as np
from .config import integer
from .planar import PlanarCase, PlanarSolution
from .planar_project import PlanarProject
from .planar_convergence_compare import _verified_solution
from .planar_tracking_overlap import rectangle_tracking_overlay
from .fem import triangle_quadrature


def verified_rectangular_solutions(previous, current):
    verified = []
    for solution in (previous, current):
        if not isinstance(solution, PlanarSolution) or not isinstance(solution.case, PlanarCase):
            raise ValueError('normalized_rectangle tracking requires rectangle Case schema_version 1; explicit polygon meshes need a separate mapping contract')
        verified.append(_verified_solution(solution, PlanarProject(solution.case)))
    if previous.case.polarization != current.case.polarization:
        raise ValueError('planar tracking cannot mix TE and TM polarizations')
    return verified


def _electric_grams(previous, current, overlay, quadrature_order, *, current_to_previous_rotation=None):
    a_count, b_count = previous.case.modes, current.case.modes
    aa = np.zeros((a_count, a_count))
    ab = np.zeros((a_count, b_count))
    bb = np.zeros((b_count, b_count))
    # Every omitted component is identically zero in the verified cutoff model.
    components = (('Ez_real_V_per_m',) if previous.case.polarization == 'tm'
                  else ('Ex_quadrature_V_per_m', 'Ey_quadrature_V_per_m'))
    for bary, weight in triangle_quadrature(quadrature_order):
        samples = []
        for solution, cells, vertices in (
                (previous, overlay.previous_cells, overlay.previous_vertex_barycentric),
                (current, overlay.current_cells, overlay.current_vertex_barycentric)):
            parent_bary = np.einsum('j,njk->nk', bary, vertices)
            fields = [solution.fields_in_cells(cells, parent_bary, i) for i in range(solution.case.modes)]
            samples.append([np.column_stack([f[key] for f in fields]) for key in components])
        if current_to_previous_rotation is not None and len(components)==2:
            rotation = np.asarray(current_to_previous_rotation)
            if rotation.shape == (2, 2):
                samples[1] = list(np.einsum('ij,jnm->inm', rotation, np.asarray(samples[1])))
            elif rotation.shape == (len(overlay.previous_cells), 2, 2):
                samples[1] = list(np.einsum('nij,jnm->inm', rotation, np.asarray(samples[1])))
            else:
                raise ValueError('planar field transport requires a 2x2 matrix or one per comparison triangle')
        weights = (weight*overlay.reference_determinants)[:, None]
        for a, b in zip(*samples):
            aa += a.T @ (weights*a)
            ab += a.T @ (weights*b)
            bb += b.T @ (weights*b)
    if not all(np.isfinite(g).all() for g in (aa, ab, bb)) or min(np.min(np.diag(aa)), np.min(np.diag(bb))) <= 0:
        raise ValueError('planar electric area inner products are not finite positive')
    return aa, ab, bb


def rectangle_electric_grams(previous, current, *, quadrature_order=3, max_overlay_triangles=250000):
    """Integrate actual E, pulled back by x=a*rho, y=b*eta, with d_rho d_eta.

    The constant physical area is removed, and each mode remains in its own
    original SI amplitude and phase. This operation creates no new eigenfield.
    """
    integer(quadrature_order, 'quadrature_order', 3)
    if quadrature_order > 8:
        raise ValueError('rectangle tracking quadrature_order must be from 3 to 8')
    previous, current = verified_rectangular_solutions(previous, current)
    overlay = rectangle_tracking_overlay(
        (previous.case.nx, previous.case.ny), (current.case.nx, current.case.ny),
        max_overlay_triangles=max_overlay_triangles)
    return _electric_grams(previous, current, overlay, quadrature_order)


def electric_gram_features(aa, ab, bb):
    """Compress a joint Gram matrix without changing its normalized inner products."""
    joint = np.block([[aa, ab], [ab.T, bb]])
    norms = np.sqrt(np.diag(joint))
    if not np.isfinite(joint).all() or not np.isfinite(norms).all() or np.any(norms <= 0):
        raise ValueError('electric Gram features require finite positive column norms')
    normalized = joint/norms[:, None]/norms[None, :]
    normalized = (normalized+normalized.T)/2
    values, vectors = np.linalg.eigh(normalized)
    if values[0] < -1e-11*max(1., values[-1]):
        raise ValueError('joint electric Gram matrix is not positive semidefinite')
    features = np.sqrt(np.maximum(values, 0.))[:, None]*vectors.T
    if not np.allclose(features.T @ features, normalized, rtol=1e-10, atol=1e-11):
        raise ValueError('electric Gram compression lost the physical inner products')
    return features[:, :len(aa)], features[:, len(aa):]
