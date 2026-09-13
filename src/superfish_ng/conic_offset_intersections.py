# SPDX-License-Identifier: Apache-2.0
"""Recover every real target foot of finite conic-offset projection roots.

The repeated eigenvalue of the target conic/circle pencil yields either one
rank-two kernel point or a rank-one kernel line with zero, one or two real
feet. Signed normal incidence, finite arcs and distinct centers are separate
proof obligations. An identically zero projection remains unresolved.
"""
from fractions import Fraction as F

from .conics import EllipseArc, HyperbolaArc, rotation_cos_sin
from .certified_arcs import _arc_membership, _number
from .rational_bounds import multiply
from .algebraic_root_signs import scale
from .conic_offset_projection import _project_conic_offset_candidates
from .line_noncircular_crossings import _dot, _same_center
from .quadratic_radicals import _sqrt_rational
from .root_radical_arithmetic import RootRadicalArithmetic


def _recover_target(root, projection, target, *, endpoint_width):
    """All real pencil feet, with exact signed incidence and contact evidence."""
    chart = projection['source_chart']
    arithmetic = RootRadicalArithmetic(root, chart['S'])
    r, plus, minus, times, scaled = (arithmetic.rational, arithmetic.add, arithmetic.subtract,
                                    arithmetic.multiply, arithmetic.scale)
    D = r(projection['positive_denominator'])
    E1, E2 = projection['pencil_linear_numerator'], projection['pencil_quadratic_numerator']
    c0, c3 = projection['pencil_constant'], projection['pencil_cubic']
    discriminant_factor = minus(times(E2, E2), scaled(times(E1, D), 3*c3))
    factor_sign = arithmetic.sign(discriminant_factor)
    if factor_sign < 0:
        raise ValueError('real repeated pencil root requires c2²-3*c3*c1 >= 0')
    if factor_sign == 0:
        numerator, denominator = scaled(E2, -1), scaled(D, 3*c3)
    else:
        numerator = minus(scaled(times(D, D), 9*c3*c0), times(E1, E2))
        denominator = scaled(discriminant_factor, 2)
    eigenvalue_sign = arithmetic.sign(numerator)*arithmetic.sign(denominator)
    if eigenvalue_sign == 0:
        raise ValueError('nonzero repeated pencil eigenvalue required')
    ellipse = isinstance(target, EllipseArc)
    epsilon = 1 if ellipse else -1
    a, b = map(F, target.semiaxes_m)
    A, B = 1/a**2, epsilon/b**2
    c, s = map(F, rotation_cos_sin(target.rotation_rad)); n = c*c+s*s
    if A == B:
        raise ValueError('noncircular target required for pencil foot recovery')
    span = F(target.sweep_rad) if ellipse else F(target.end_parameter)-F(target.start_parameter)
    e = projection['target_signed_distance']
    oriented_sign = (1 if e*span > 0 else -1)
    required_sign = -(1 if ellipse else target.branch)*eigenvalue_sign
    proof = dict(pencil_root_multiplicity=3 if factor_sign == 0 else 2,
                 pencil_eigenvalue_sign=eigenvalue_sign, target_oriented_distance_sign=oriented_sign,
                 recovered_normal_distance_sign=required_sign, target_feet=[],
                 method='repeated conic/circle pencil eigenvalue; real kernel feet and original normal sign')
    if oriented_sign != required_sign:
        proof['exclusion'] = 'opposite target normal distance sign on the declared branch'
        return proof
    h, S = chart['H'], chart['S']
    T = multiply(h, S)
    d = projection['source_oriented_distance']
    center = tuple((multiply(_dot(axis, chart['W']), S),
                    scale(multiply(h, _dot(axis, chart['JV'])), d)) for axis in ((c, s), (-s, c)))
    lx, ly = (plus(scaled(denominator, coefficient), scaled(numerator, n)) for coefficient in (A, B))
    signs = arithmetic.sign(lx), arithmetic.sign(ly)
    g0, g1 = (_dot(axis, chart['V']) for axis in ((c, s), (-s, c)))
    width = F(endpoint_width)/64
    if all(signs):
        # det=det'=0 and rank=2 imply both conic and circle incidence of the
        # unique kernel vector. Nonzero diagonal entries make it a finite point.
        local = tuple(arithmetic.ratio_bounds(times(numerator, u), times(r(scale(T, axis)), diagonal), width)
                      for u, diagonal, axis in zip(center, (lx, ly), (a, b)))
        tangent = plus(scaled(times(times(r(g0), center[0]), ly), A),
                       scaled(times(times(r(g1), center[1]), lx), B))
        tangent_zero = arithmetic.sign(tangent) == 0
        speed_numerator = plus(scaled(times(numerator, D), 3*c3), times(E2, denominator))
        speed_denominator = scaled(times(numerator, D), c3)
        speed_sign = arithmetic.sign(speed_numerator)*arithmetic.sign(speed_denominator)
        proof.update(pencil_rank=2, target_offset_speed_factor_sign=speed_sign)
        proof['target_feet'].append(dict(target_local_box=local, tangent_parallel=tangent_zero,
                                          real_incidence_certified=True))
        return proof
    if signs == (0, 0):
        raise ValueError('noncircular pencil cannot have two zero leading diagonals')
    free_axis = 0 if signs[0] == 0 else 1
    if arithmetic.sign(center[free_axis]) != 0:
        raise ValueError('rank-one pencil requires zero center coordinate on its free axis')
    if free_axis == 0:
        eigenvalue = -A/n
        known_numerator = scaled(center[1], A)
        known_denominator = r(scale(T, n*(A-B)*b))
        known_square = epsilon*(e*e*A*A/n-A)/(B-A)
        free_square = 1-epsilon*known_square
        known_coefficient, free_coefficient = scale(g1, epsilon/b), scale(g0, 1/a)
    else:
        eigenvalue = -B/n
        known_numerator = scaled(center[0], B)
        known_denominator = r(scale(T, n*(B-A)*a))
        known_square = (e*e*B*B/n-B)/(A-B)
        free_square = epsilon*(1-known_square)
        known_coefficient, free_coefficient = scale(g0, 1/a), scale(g1, epsilon/b)
    speed = 1+c0/(c3*eigenvalue**3)
    proof.update(pencil_rank=1, free_axis=free_axis, free_coordinate_squared=free_square,
                 target_offset_speed_factor_sign=(speed > 0)-(speed < 0))
    if free_square < 0:
        proof['exclusion'] = 'rank-one kernel has no real target conic point'
        return proof
    known = arithmetic.ratio_bounds(known_numerator, known_denominator, width)
    radical = _sqrt_rational(free_square, width/max(F(1), free_square))
    tangent_rational = times(r(known_coefficient), known_numerator)
    tangent_radical = times(r(free_coefficient), known_denominator)
    for sign in ((1,) if free_square == 0 else (-1, 1)):
        free = radical if sign == 1 else (-radical[1], -radical[0])
        local = (free, known) if free_axis == 0 else (known, free)
        tangent_zero = arithmetic.nested_sign(tangent_rational, scaled(tangent_radical, sign), free_square) == 0
        proof['target_feet'].append(dict(target_local_box=local, tangent_parallel=tangent_zero,
                                          real_incidence_certified=True, free_coordinate_sign=sign if free_square else 0))
    return proof


def classify_conic_offset_intersections(curves, distances, domains, *, endpoint_width,
                                        max_series_terms, max_root_boxes=10000, max_refinements=512):
    """Private extension for two noncircular conics with nonzero offsets."""
    if not all(isinstance(c, (EllipseArc, HyperbolaArc)) and not (
            isinstance(c, EllipseArc) and c.semiaxes_m[0] == c.semiaxes_m[1]) for c in curves):
        return None
    if any(d == 0 for d in distances):
        return None
    if not isinstance(domains[1], (tuple, list)) or len(domains[1]) != 2:
        raise ValueError('target fraction interval requires a pair')
    domain = tuple(_number(x, 'target fraction interval') for x in domains[1])
    if not 0 <= domain[0] < domain[1] <= 1:
        raise ValueError('target fraction interval must increase within [0,1]')
    first, target = curves
    ellipse = isinstance(target, EllipseArc)
    start = F(target.start_rad) if ellipse else F(target.start_parameter)
    span = F(target.sweep_rad) if ellipse else F(target.end_parameter)-start
    endpoints = tuple(start+span*f for f in domain)
    evidence = dict(identity='finite source projection and complete real target pencil recovery',
                    target_recoveries=[], intersections=[], excluded=[], unresolved=[], same_center_groups=[])
    included = []

    def recover(root, projection, source):
        index = len(evidence['target_recoveries'])
        record = dict(source_candidate_index=index)
        evidence['target_recoveries'].append(record)
        try:
            proof = _recover_target(root, projection, target, endpoint_width=endpoint_width)
            record.update(proof)
            if 'exclusion' in proof:
                evidence['excluded'].append(dict(source_candidate_index=index, reason=proof['exclusion']))
            for foot in proof['target_feet']:
                membership = _arc_membership(target, foot['target_local_box'], parameter_endpoints=endpoints,
                                              endpoint_width=endpoint_width, max_series_terms=max_series_terms)
                foot['target_membership'] = membership
                row = dict(source, **foot, source_candidate_index=index,
                           target_offset_speed_factor_sign=proof['target_offset_speed_factor_sign'])
                if membership['status'] == 'UNVERIFIED':
                    evidence['unresolved'].append(dict(row, reason='finite target membership unresolved'))
                elif membership['status'] == 'EXTERIOR':
                    evidence['excluded'].append(dict(row, reason='outside finite target domain or branch'))
                else:
                    row.update(membership=[source['source_membership'], membership], parameter_pair_in_domain=True,
                        contact_kind='CUSP' if 0 in (source['source_offset_speed_factor_sign'],
                            proof['target_offset_speed_factor_sign']) else 'REGULAR_TANGENCY' if foot['tangent_parallel'] else 'TRANSVERSE')
                    included.append((root, projection['source_chart'], row))
                    evidence['intersections'].append(row)
        except ValueError as error:
            record['unresolved'] = str(error)
            evidence['unresolved'].append(dict(source_candidate_index=index, reason=str(error)))

    projection = _project_conic_offset_candidates(first, target, first_distance_m=distances[0],
        second_distance_m=distances[1], first_interval=domains[0], endpoint_width=endpoint_width,
        max_series_terms=max_series_terms, max_root_boxes=max_root_boxes, max_refinements=max_refinements,
        candidate_handler=recover)
    evidence['source_projection'] = projection
    groups = evidence['same_center_groups']
    source_span = F(first.sweep_rad) if isinstance(first, EllipseArc) else F(first.end_parameter)-F(first.start_parameter)
    distance = F(distances[0])*(1 if source_span > 0 else -1)
    try:
        for i, item in enumerate(included):
            for group in groups:
                other = included[group[0]]
                if item[2]['source_candidate_index'] == other[2]['source_candidate_index'] or _same_center(item, other, first, distance):
                    group.append(i)
                    break
            else:
                groups.append([i])
    except ValueError as error:
        evidence['unresolved'].append(dict(reason=str(error), stage='distinct center grouping'))
    for root, _, row in included:
        row.update(rational_parameter_interval=root.interval, refinements=root.refinements)
    complete = projection['projection_complete'] and not evidence['unresolved']
    return dict(classification=('FINITE_CENTERS' if groups else 'DISJOINT') if complete else 'UNVERIFIED',
                complete=complete, centers=len(groups) if complete else None, infinite=False if complete else None,
                evidence=evidence, reason='all source roots, real signed target feet, finite membership and distinct centers certified' if complete
                else 'some projection roots, target feet, memberships or center identities remain unresolved')
