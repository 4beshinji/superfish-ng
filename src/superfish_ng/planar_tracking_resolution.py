# SPDX-License-Identifier: Apache-2.0
"""Finite-enrichment spectral resolution; never a continuum error certificate."""
import numpy as np
from scipy.sparse.linalg import splu
from .planar import planar_mesh_matrices
from .planar_mesh import PlanarMesh
from .planar_refinement import refine_planar_mesh, planar_prolongation
from .constants import C0, TAU


def rectangle_spectral_resolution(solution, *, max_refined_triangles=250000):
    """Bound a nearby eigenvalue of the enriched shifted inverse operator.

    For T=(K+sM)^-1 M, mu=1/(lambda+s), and the prolonged vector u,
    dist(mu,spectrum(T)) <= ||T u-mu u||_M/||u||_M. This locates at least
    one enriched eigenvalue, not its rank and not the continuous spectrum.
    No enriched eigenvector or synthetic frequency replaces a saved mode.
    The caller supplies a verified rectangle solution.
    """
    case = solution.case
    mesh = PlanarMesh.create([[0., 0.], [case.width_m, 0.],
                              [case.width_m, case.height_m], [0., case.height_m]],
                             solution.space.points_xy_m, solution.space.triangles)
    fine = refine_planar_mesh(mesh, max_triangles=max_refined_triangles)
    _, stiffness, mass, free = planar_mesh_matrices(fine, case.element_order, case.polarization)
    transfer = planar_prolongation(mesh, fine, case.element_order, case.polarization)
    vectors = (transfer @ solution.coefficients)[free]
    stiffness, mass = stiffness[free][:, free], mass[free][:, free]
    shift = 1/max(case.width_m, case.height_m)**2
    matrix = (stiffness+shift*mass).tocsc()
    rhs = mass @ vectors
    inverse_vectors = splu(matrix).solve(rhs)
    equation_error = np.linalg.norm(matrix @ inverse_vectors-rhs, axis=0)/np.linalg.norm(rhs, axis=0)
    if not np.isfinite(equation_error).all() or np.max(equation_error) > 1e-8:
        raise ValueError('enriched shifted inverse solve is numerically unresolved')
    mu = 1/(solution.eigenvalues+shift)
    residual = inverse_vectors-vectors*mu
    delta = np.sqrt(np.maximum(0., np.sum(residual*(mass @ residual), axis=0))
                    /np.sum(vectors*(mass @ vectors), axis=0))
    if not np.isfinite(delta).all():
        raise ValueError('enriched inverse residual is not finite')
    # A fixed roundoff floor is disclosed separately from the enrichment defect.
    padded = delta+1e-10*mu
    lower = np.maximum(0., 1/(mu+padded)-shift)
    upper = np.full(len(mu), np.inf)
    bounded = mu > padded
    upper[bounded] = 1/(mu[bounded]-padded[bounded])-shift
    lower_hz, upper_hz = np.sqrt(lower)*C0/TAU, np.sqrt(upper)*C0/TAU
    return dict(method='uniform_refinement_shifted_inverse_residual',
                refined_triangles=len(fine.triangles), shift_per_m2=shift,
                relative_inverse_residual=(delta/mu).tolist(), roundoff_relative_padding=1e-10,
                linear_solve_relative_residual=equation_error.tolist(),
                nearby_enriched_frequency_intervals_hz=[
                    [float(a), float(b) if np.isfinite(b) else None] for a, b in zip(lower_hz, upper_hz)],
                scope='nearby finite-enrichment eigenvalue only; no rank isolation, continuous-spectrum enclosure or physical error bound')


def resolution_frequency_groups(frequencies, resolution, relative_gap):
    """Merge adjacent ranks when either frequency proximity or intervals overlap."""
    intervals = resolution['nearby_enriched_frequency_intervals_hz']
    groups = []
    upper = None
    for i, (frequency, interval) in enumerate(zip(frequencies, intervals)):
        close = i and (frequency-frequencies[i-1] <= relative_gap*frequency
                       or upper is None or interval[0] <= upper)
        if close:
            groups[-1].append(i+1)
            upper = None if upper is None or interval[1] is None else max(upper, interval[1])
        else:
            groups.append([i+1])
            upper = interval[1]
    return groups
