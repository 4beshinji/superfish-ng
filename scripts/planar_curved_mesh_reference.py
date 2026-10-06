# SPDX-License-Identifier: Apache-2.0
"""Validator-only common parent charts for independent curved planar meshes.

Both meshes must be regenerated restrictions of one complete original Domain.
Exact rational clipping checks every reference cell, before original Cartesian
fields are integrated. This is finite mesh evidence, not mode tracking.
"""
from dataclasses import dataclass
from fractions import Fraction
import numpy as np
from superfish_ng.constants import EPS0, MU0
from superfish_ng.planar_curved_geometry import _map_coefficients
from superfish_ng.planar_curved_refinement import refine_planar_curved_domain, _evaluate
from superfish_ng.planar_curved_solver import planar_curved_quantities
from superfish_ng.planar_tracking_exact_affine import _RationalTriangulation
from superfish_ng.planar_tracking_overlap import _clip, _cross, _barycentric
from superfish_ng.planar_tracking_remesh import _candidate_pairs
from validate_planar_curved_convergence import _rule, _vectors, RF_VALUES, RF_NULLS


@dataclass(frozen=True)
class ParentCharts:
    original: object
    domain: object
    parents: np.ndarray
    vertices: np.ndarray
    patterns: tuple
    coordinate_bounds_m: np.ndarray
    maximum_relative_coordinate_bound: float


def restriction_chain(original, patterns=(), *, max_geometry_boxes=100000000):
    """Regenerate geometry/ancestry, measuring FINAL maps against the base map."""
    domain = original
    parents = np.arange(len(domain.cell_nodes))
    vertices = np.tile([[0., 0.], [1., 0.], [0., 1.]], (len(parents), 1, 1))
    for pattern in patterns:
        restriction = refine_planar_curved_domain(domain, pattern=pattern,
            max_geometry_boxes=max_geometry_boxes)
        previous = vertices[restriction.parent_cells]
        vertices = previous[:, :1]+np.einsum('cva,cab->cvb',
            restriction.parent_reference_vertices, previous[:, 1:]-previous[:, :1])
        parents = parents[restriction.parent_cells]
        domain = restriction.domain
    covered = [Fraction(0) for _ in original.cell_nodes]
    coefficients = [_map_coefficients(original.points_xy_m[cell]) for cell in original.cell_nodes]
    bounds = []
    for cell, (parent, chart) in enumerate(zip(parents, vertices)):
        exact = [tuple(Fraction(float(x)) for x in point) for point in chart]
        if any(min(p) < 0 or sum(p) > 1 for p in exact):
            raise ValueError('regenerated chart lies outside its original parent')
        determinant = _cross(*exact)
        if determinant <= 0:
            raise ValueError('regenerated chart orientation is invalid')
        covered[parent] += determinant
        refs = exact+[tuple((exact[i][a]+exact[j][a])/2 for a in range(2))
            for i, j in ((0, 1), (1, 2), (2, 0))]
        expected = [_evaluate(coefficients[parent], ref) for ref in refs]
        actual = [tuple(Fraction(float(x)) for x in point)
            for point in domain.points_xy_m[domain.cell_nodes[cell]]]
        error = [[a-b for a, b in zip(p, q)] for p, q in zip(actual, expected)]
        controls = error[:3]+[[2*error[3+k][a]-(error[i][a]+error[j][a])/2
            for a in range(2)] for k, (i, j) in enumerate(((0, 1), (1, 2), (2, 0)))]
        bound = [max(abs(p[a]) for p in controls) for a in range(2)]
        bounds.append([float(np.nextafter(float(x), np.inf)) if x else 0. for x in bound])
    if covered != [Fraction(1)]*len(covered):
        raise ValueError('regenerated charts do not exactly cover every original parent')
    bounds = np.array(bounds)
    extents = np.max(np.ptp(domain.points_xy_m[domain.cell_nodes], axis=1), axis=1)
    relative = float(np.max(np.max(bounds, axis=1)/extents))
    if not np.isfinite(relative) or relative > 512*np.finfo(float).eps:
        raise ValueError('UNVERIFIED: cumulative original-map roundoff exceeds local resolution')
    for array in (parents, vertices, bounds):
        array.setflags(write=False)
    return ParentCharts(original, domain, parents, vertices, tuple(patterns), bounds, relative)


def _partition(first, second, *, max_candidate_tests, max_overlay_triangles):
    triangles = [[tuple(Fraction(float(x)) for x in p) for p in tri] for tri in first]
    other = [[tuple(Fraction(float(x)) for x in p) for p in tri] for tri in second]
    rational = [_RationalTriangulation(np.asarray(ts, dtype=object).reshape(-1, 2),
        np.arange(3*len(ts)).reshape(-1, 3)) for ts in (triangles, other)]
    covered = [[Fraction(0) for _ in ts] for ts in (triangles, other)]
    output = []
    for i, j in _candidate_pairs(*rational, max_candidate_tests):
        polygon = _clip(triangles[i], other[j])
        for k in range(1, len(polygon)-1):
            child = [polygon[0], polygon[k], polygon[k+1]]
            determinant = _cross(*child)
            if determinant < 0:
                raise ValueError('common chart orientation is invalid')
            if determinant == 0:
                continue
            if len(output) >= max_overlay_triangles:
                raise ValueError('common charts exceed max_overlay_triangles')
            covered[0][i] += determinant
            covered[1][j] += determinant
            output.append((i, j, np.array(child, dtype=float), float(determinant),
                np.array(_barycentric(child, triangles[i]), dtype=float)[:, 1:],
                np.array(_barycentric(child, other[j]), dtype=float)[:, 1:]))
    for actual, ts in zip(covered, (triangles, other)):
        if actual != [_cross(*tri) for tri in ts]:
            raise ValueError('common charts do not exactly cover every original cell')
    return output


def common_charts(first, second, *, max_candidate_tests=2000000, max_overlay_triangles=250000):
    """Exact overlay in EACH original parent; bounds apply to complete output.

    Repeated dyadic chart layouts are cached, with no cached field values.
    """
    for limit in (max_candidate_tests, max_overlay_triangles):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError('common chart budgets require positive integers')
    if first.original != second.original:
        raise ValueError('common charts require the same complete original quadratic domain')
    cache, count = {}, 0
    for parent in range(len(first.original.cell_nodes)):
        left = np.flatnonzero(first.parents == parent)
        right = np.flatnonzero(second.parents == parent)
        a, b = first.vertices[left], second.vertices[right]
        key = (a.tobytes(), b.tobytes())
        if key not in cache:
            cache[key] = _partition(a, b, max_candidate_tests=max_candidate_tests,
                max_overlay_triangles=max_overlay_triangles)
        for i, j, child, det, ra, rb in cache[key]:
            count += 1
            if count > max_overlay_triangles:
                raise ValueError('complete common charts exceed max_overlay_triangles')
            yield parent, int(left[i]), int(right[j]), child, det, ra, rb


def compare_meshes(first, second, first_charts, second_charts, mode_groups, *, quadrature_order=10):
    """Full-area direct original E/H differences using ONE scalar rotation.

    Measure is the original parent area. Both actual rounded native maps are
    retained for field gradients, with final coordinate error bounds recorded.
    """
    for name in ('polarization', 'modes', 'normalization_j_per_m', 'conductivity_s_per_m'):
        if getattr(first.case, name) != getattr(second.case, name):
            raise ValueError(f'common-domain comparison requires matching {name}')
    if first.case.domain != first_charts.domain or second.case.domain != second_charts.domain:
        raise ValueError('solutions must match regenerated complete native geometry')
    if not mode_groups or any(isinstance(n, bool) or not isinstance(n, int) or n < 1
            for n in mode_groups) or sum(mode_groups) != first.case.modes:
        raise ValueError('comparison groups must partition the entire positive band')
    refs, ref_weights = _rule(quadrature_order)
    partitions = list(common_charts(first_charts, second_charts))
    cross = np.zeros((first.case.modes, first.case.modes))

    def samples(piece):
        parent, a, b, child, determinant, ra, rb = piece
        parent_refs = child[0]+refs@(child[1:]-child[0])
        weight = ref_weights*determinant*first_charts.original.elements[parent].evaluate(parent_refs)['determinant_m2']
        left_refs = ra[0]+refs@(ra[1:]-ra[0])
        right_refs = rb[0]+refs@(rb[1:]-rb[0])
        left, right = _vectors(first, a, left_refs), _vectors(second, b, right_refs)
        return weight, left, right

    scalar_field = 1 if first.case.polarization == 'te' else 0
    for piece in partitions:
        weight, left, right = samples(piece)
        a, b = left[scalar_field][:, 2, :].real, right[scalar_field][:, 2, :].real
        cross += (a*weight[:, None]).T@b
    material = MU0 if first.case.polarization == 'te' else EPS0
    cross *= material/(2*first.case.normalization_j_per_m)
    rotations, singulars, selections = [], [], []
    offset = 0
    for n in mode_groups:
        selected = slice(offset, offset+n)
        u, singular, vt = np.linalg.svd(cross[selected, selected])
        rotations.append(u@vt)
        singulars.append(singular.tolist())
        selections.append(selected)
        offset += n
    numerator = np.zeros((len(mode_groups), 2))
    denominator = np.zeros_like(numerator)
    for piece in partitions:
        weight, left, right = samples(piece)
        for group, (selected, rotation) in enumerate(zip(selections, rotations)):
            for field in range(2):
                reference = right[field][:, :, selected]
                difference = left[field][:, :, selected]@rotation-reference
                numerator[group, field] += np.einsum('p,pcm,pcm->', weight, difference.conj(), difference).real
                denominator[group, field] += np.einsum('p,pcm,pcm->', weight, reference.conj(), reference).real
    if not np.isfinite(numerator).all() or not np.isfinite(denominator).all() or np.any(denominator <= 0):
        raise ValueError('comparison requires finite positive E and H norms')
    errors = np.sqrt(numerator/denominator)
    rf = [[planar_curved_quantities(solution, i) for i in range(solution.case.modes)]
        for solution in (first, second)]
    records = []
    for group, selected in enumerate(selections):
        ranks = list(range(selected.start, selected.stop))
        frequency = float(np.max(abs(first.frequencies_hz[selected]/second.frequencies_hz[selected]-1)))
        rf_errors = {name: max(abs(rf[0][i][name]/rf[1][i][name]-1) for i in ranks) for name in RF_VALUES}
        for i in ranks:
            if any(rf[side][i][name] is not None for side in (0, 1) for name in RF_NULLS):
                raise ValueError('cutoff accelerating RF must remain unavailable')
            for name in ('accelerating_quantities_reason', 'phasor_convention', 'longitudinal_units'):
                if rf[0][i][name] != rf[1][i][name]:
                    raise ValueError(f'RF metadata differs: {name}')
        gates = dict(frequency=frequency <= 1e-4, electric=bool(errors[group, 0] <= .01),
            magnetic=bool(errors[group, 1] <= .01), all_RF=max(rf_errors.values()) <= .005)
        records.append(dict(numerical_ranks_zero_based=ranks, frequency_relative_difference=frequency,
            electric_relative_L2_difference=float(errors[group, 0]), magnetic_relative_L2_difference=float(errors[group, 1]),
            RF_relative_differences=rf_errors, common_scalar_rotation=rotations[group].tolist(),
            scalar_alignment_singular_values=singulars[group], gates=gates, passed=all(gates.values())))
    return dict(groups=records, comparison_quadrature_order=quadrature_order,
        common_reference_triangles=len(partitions), first_RF=rf[0], second_RF=rf[1],
        final_original_map_relative_bounds=[c.maximum_relative_coordinate_bound for c in (first_charts, second_charts)],
        scope='exact full-parent reference overlay; original E/H; common scalar rotation; no mode identity or continuous error bound')
