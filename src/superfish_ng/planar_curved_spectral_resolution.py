# SPDX-License-Identifier: Apache-2.0
"""Fixed quadratic-boundary enrichment of Cartesian cutoff spectra.

A shifted inverse residual locates a nearby finite comparison eigenvalue.
It is never a rank isolation, continuum enclosure or mode identity.
"""
from dataclasses import replace
from fractions import Fraction
import numpy as np
from scipy.sparse.linalg import splu
from .config import integer
from .constants import C0, TAU
from .planar_curved_comparison import (PlanarCurvedComparisonDomain,
    PlanarCurvedComparisonBudgetExceeded, build_planar_curved_comparison)
from .planar_curved_field_overlap import verified_planar_curved_solution
from .planar_curved_fem import planar_curved_matrices
from .planar_curved_refinement import refine_planar_curved_domain


def _diameter(domain):
    p = domain.points_xy_m[domain.cell_nodes]
    controls = np.concatenate((p[:, :3], 2*p[:, 3:]-(p[:, [0,1,2]]+p[:, [1,2,0]])/2), axis=1)
    value = float(np.max(np.linalg.norm(np.ptp(controls, axis=1), axis=1)))
    if not np.isfinite(value) or value <= 0:
        raise ValueError('UNVERIFIED: quadratic comparison diameter exceeds finite positive SI range')
    return value


def planar_curved_spectral_resolution(solution, *, quadrature_order=None,
        max_refined_triangles=250000, max_dofs=250000, max_pair_tests=2000000,
        max_sample_points=2000000):
    """Use true parent P2 restrictions and a finer same-boundary P2 space.

    T=(K+sM)^-1 M is self-adjoint in the M inner product. For each original
    vector prolonged into the enriched space, its M-norm inverse residual
    locates at least one nearby eigenvalue of that finite operator in exact
    arithmetic. Floating residuals receive separately disclosed padding.
    This function performs no enriched eigensolve, reorders no original mode,
    and changes neither saved fields nor frequencies. TE's constant kernel
    remains in the enriched operator and intervals reaching it are unresolved.
    """
    for name, value in (('max_refined_triangles', max_refined_triangles), ('max_dofs', max_dofs),
                       ('max_pair_tests', max_pair_tests), ('max_sample_points', max_sample_points)):
        integer(value, name)
    if quadrature_order is not None:
        integer(quadrature_order, 'quadrature_order', 4)
        if quadrature_order > 32:
            raise ValueError('curved planar enrichment quadrature_order must be from 4 to 32')
    solution = verified_planar_curved_solution(solution)
    case, domain = solution.case, solution.case.domain
    count = 4*len(domain.cell_nodes)
    if count > max_refined_triangles:
        raise PlanarCurvedComparisonBudgetExceeded('complete uniform curved enrichment exceeds max_refined_triangles')
    edges = {tuple(sorted((int(cell[a]), int(cell[b])))) for cell in domain.cell_nodes
             for a, b in ((0,1), (1,2), (2,0))}
    dofs = len(domain.points_xy_m)+2*len(edges)+3*len(domain.cell_nodes)
    if dofs > max_dofs:
        raise PlanarCurvedComparisonBudgetExceeded('complete uniform curved enrichment exceeds max_dofs')
    order = min(32, max(16, case.quadrature_order+4)) if quadrature_order is None else quadrature_order
    sample_points = count*order**2
    if sample_points > max_sample_points:
        raise PlanarCurvedComparisonBudgetExceeded('complete curved enrichment area quadrature exceeds max_sample_points')
    # Uniform refinement costs six self pairs plus four intersections per
    # original owner. Preflight prevents partial expensive geometry construction.
    if 10*len(domain.cell_nodes) > max_pair_tests:
        raise PlanarCurvedComparisonBudgetExceeded('complete curved enrichment correspondence exceeds max_pair_tests')
    fine = refine_planar_curved_domain(domain, max_geometry_boxes=case.max_geometry_boxes)
    if len(fine.domain.points_xy_m) != dofs or _diameter(fine.domain) >= _diameter(domain):
        raise ValueError('UNVERIFIED: enrichment must have the declared DOFs and smaller whole-P2 diameter')
    charts = [dict(base_cell=int(owner), reference_vertices=[[[Fraction(float(v)).numerator,
              Fraction(float(v)).denominator] for v in point] for point in vertices])
              for owner, vertices in zip(fine.parent_cells, fine.parent_reference_vertices)]
    comparison_domain = PlanarCurvedComparisonDomain(domain, domain, restriction_policy='binary64_roundoff',
        max_geometry_boxes_per_domain=case.max_geometry_boxes)
    comparison = build_planar_curved_comparison(domain, fine.domain, comparison_domain,
        current_cells=charts, max_pair_tests=max_pair_tests, max_triangles=max_refined_triangles)
    space, stiffness, mass, free = planar_curved_matrices(replace(case, domain=fine.domain, quadrature_order=order))
    vectors = (fine.prolongation@solution.coefficients)[free]
    # TM prolongation must keep every new quadratic PEC node exactly zero.
    constrained = np.setdiff1d(np.arange(len(space.points_xy_m)), free)
    if np.any((fine.prolongation@solution.coefficients)[constrained] != 0):
        raise ValueError('UNVERIFIED: enriched scalar violates the original PEC boundary')
    stiffness, mass = stiffness[free][:, free], mass[free][:, free]
    original_norm = np.sum(solution.coefficients*(solution.mass@solution.coefficients), axis=0)
    rhs = mass@vectors
    norm = np.sum(vectors*rhs, axis=0)
    if (not np.isfinite(norm).all() or np.any(norm <= 0)
            or not np.isfinite(original_norm).all() or np.any(original_norm <= 0)):
        raise ValueError('UNVERIFIED: curved scalar enrichment has no finite positive mass norm')
    mass_difference = abs(norm/original_norm-1)
    if np.max(mass_difference) > 1e-8:
        raise ValueError('UNVERIFIED: parent restrictions fail to preserve original scalar mass norms')
    shift = 1/domain.area_m2
    if not np.isfinite(shift) or shift <= 0:
        raise ValueError('UNVERIFIED: curved inverse shift is outside finite positive SI range')
    matrix = (stiffness+shift*mass).tocsc()
    inverse = splu(matrix).solve(rhs)
    equation_error = np.linalg.norm(matrix@inverse-rhs, axis=0)/np.linalg.norm(rhs, axis=0)
    mu = 1/(solution.eigenvalues+shift)
    residual = inverse-vectors*mu
    squared = np.sum(residual*(mass@residual), axis=0)/norm
    if (not np.isfinite(squared).all() or np.any(squared < 0)
            or not np.isfinite(equation_error).all() or np.max(equation_error) > 1e-10):
        raise ValueError('UNVERIFIED: curved shifted inverse comparison is numerically unresolved')
    delta = np.sqrt(squared)
    padded = delta+1e-10*mu
    lower = np.maximum(0., 1/(mu+padded)-shift)
    upper = np.full(len(mu), np.inf)
    bounded = mu > padded
    upper[bounded] = 1/(mu[bounded]-padded[bounded])-shift
    lower_hz, upper_hz = C0/TAU*np.sqrt(lower), C0/TAU*np.sqrt(upper)
    rows = []
    for i, (lo, hi) in enumerate(zip(lower_hz, upper_hz)):
        reasons = []
        if not np.isfinite(hi):reasons.append('inverse residual gives no finite upper frequency')
        if case.polarization == 'te' and lo == 0:reasons.append('interval reaches the TE constant static kernel')
        rows.append(dict(mode_rank=i+1, status='UNVERIFIED' if reasons else 'PASS', reasons=reasons))
    return dict(method='fixed_quadratic_boundary_uniform_enrichment_shifted_inverse_residual',
        status='PASS' if all(row['status'] == 'PASS' for row in rows) else 'UNVERIFIED', modes=rows,
        original_frequencies_hz=solution.frequencies_hz.tolist(), comparison_geometry=fine.domain.to_dict(),
        comparison_domain=comparison_domain.to_dict(), comparison_cells=charts, geometry=comparison.report,
        refined_triangles=count, comparison_native_dofs=dofs, comparison_free_dofs=len(free),
        max_refined_triangles=max_refined_triangles, max_dofs=max_dofs,
        quadrature_order=order, enrichment_area_sample_points=sample_points, max_sample_points=max_sample_points,
        maximum_original_map_relative_bound=fine.maximum_relative_coordinate_bound,
        relative_scalar_mass_difference=mass_difference.tolist(), scalar_mass_tolerance=1e-8,
        shift_per_m2=shift, shift_geometry='inverse_original_quadratic_xy_area',
        relative_inverse_residual=(delta/mu).tolist(), inverse_residual_m2=delta.tolist(),
        roundoff_relative_padding=1e-10, linear_solve_relative_residual=equation_error.tolist(), linear_solve_tolerance=1e-10,
        nearby_enriched_frequency_intervals_hz=[[float(a), float(b) if np.isfinite(b) else None] for a,b in zip(lower_hz,upper_hz)],
        zero_mode='TE constant retained in enriched operator' if case.polarization == 'te' else 'TM Dirichlet has no constant kernel',
        scope='nearby finite-enrichment eigenvalue only; original nodal restriction, numerical residual with padding; no rank isolation, certified enclosure, continuum error bound or mode identity')
