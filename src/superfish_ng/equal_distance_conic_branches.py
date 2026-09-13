# SPDX-License-Identifier: Apache-2.0
"""Equal-magnitude offsets on one conic when finite projection is an identity.

Opposite normal sides of one convex branch are disjoint by uniqueness of the
nearest point of a closed convex set. For opposite hyperbola branches, two
distinct conic feet on one tangent circle force a rank-one pencil; its kernel
gives every possible cross-branch center and the required outward signs.
"""
from dataclasses import replace
from fractions import Fraction as F

from .conics import EllipseArc, HyperbolaArc
from .certified_arcs import _arc_membership
from .quadratic_radicals import _sqrt_rational
from .reparameterized_conic_offsets import _support_map, _ranges, _inverse_point
from .same_conic_offset_intersections import _scale


def _sqrt_box(value, width):
    return _sqrt_rational(value, width/max(F(1), value))


def classify_equal_distance_conic_branches(curves, distances, domains, *, endpoint_width, max_series_terms):
    """Private diagnosis extension; a missing exact support map returns None."""
    first, second = curves
    if any(d == 0 for d in distances) or abs(F(distances[0])) != abs(F(distances[1])):
        return None
    mapping = _support_map(first, second); opposite_branches = False
    if mapping is None and all(isinstance(c, HyperbolaArc) for c in curves):
        mapping = _support_map(first, replace(second, branch=-second.branch))
        opposite_branches = mapping is not None
    if mapping is None:
        return None
    spans = [F(c.sweep_rad) if isinstance(c, EllipseArc) else F(c.end_parameter)-F(c.start_parameter) for c in curves]
    oriented = [F(d)*(1 if span > 0 else -1) for d, span in zip(distances, spans)]
    oriented[1] *= mapping['parameter_orientation']
    evidence = dict(identity='equal-magnitude normal offsets on an exactly shared noncircular support',
                    support_map=mapping, second_physical_branch='OPPOSITE' if opposite_branches else 'SAME',
                    distances_in_first_parameter_frame=oriented, intersections=[], excluded=[], unresolved=[],
                    same_center_groups=[])
    if not opposite_branches:
        if oriented[0] == oriented[1]:
            return None  # Existing equal-offset diagonal and reflection classification.
        evidence['proof'] = 'opposite normal sides of one strictly convex boundary cannot share an equal-distance center: the exterior normal foot is the unique nearest boundary point'
        return dict(classification='DISJOINT', complete=True, centers=0, infinite=False, evidence=evidence,
                    reason='opposite equal-distance normal sides of the same physical branch are disjoint')
    branch = first.branch
    if oriented[0]*branch <= 0 or oriented[1]*branch >= 0:
        evidence['proof'] = 'cross-branch kernel feet require lambda=-1/(n*a²), hence both offsets must follow the outward normal of their own convex branch'
        return dict(classification='DISJOINT', complete=True, centers=0, infinite=False, evidence=evidence,
                    reason='equal-distance cross-branch incidence requires both outward normals')
    a, b = map(F, first.semiaxes_m); n = mapping['first_rotation_square']; distance = abs(oriented[0])
    square = b*b*(distance*distance-n*a*a)/(n*a*a*(a*a+b*b))
    evidence.update(proof='two distinct feet of one conic/circle imply rank-one pencil; only the zero transverse-center coordinate kernel can meet opposite branches',
                    normalized_transverse_coordinate_squared=square, pencil_eigenvalue=-1/(n*a*a),
                    distance_squared_minus_half_gap_squared=distance*distance-n*a*a)
    if square < 0:
        return dict(classification='DISJOINT', complete=True, centers=0, infinite=False, evidence=evidence,
                    reason='offset distance is smaller than half the exact distance between branch vertices')
    width = F(endpoint_width)/256
    x, y = _sqrt_box(1+square, width), _sqrt_box(square, width)
    _, endpoints = _ranges(curves, domains)
    c, s = mapping['first_rotation']
    for sign in ((1,) if square == 0 else (-1, 1)):
        transverse = _scale(y, sign)
        local = (_scale(x, branch), transverse)
        target_local = _inverse_point(mapping['second_to_first'], (_scale(x, -branch), transverse))
        displacement = _scale(transverse, (a*a+b*b)/b)
        center = tuple(tuple(F(origin)+t for t in _scale(displacement, coefficient))
                       for origin, coefficient in zip(first.center_zr_m, (-s, c)))
        row = dict(source_local_box=local, target_local_box=target_local, center_box_zr_m=center,
                   normalized_transverse_sign=sign if square else 0, source_contacts_coincide=False,
                   source_offset_speed_factor_sign=1, target_offset_speed_factor_sign=1,
                   contact_kind='REGULAR_TANGENCY' if square == 0 else 'TRANSVERSE',
                   tangent_parallel=square == 0, real_incidence_certified=True)
        memberships = []
        for curve, box, ends in zip(curves, (local, target_local), endpoints):
            try:
                memberships.append(_arc_membership(curve, box, parameter_endpoints=ends,
                    endpoint_width=endpoint_width, max_series_terms=max_series_terms))
            except ValueError as error:
                memberships.append(dict(status='UNVERIFIED', reason=str(error)))
        row['membership'] = memberships
        statuses = [m['status'] for m in memberships]
        if 'EXTERIOR' in statuses:
            evidence['excluded'].append(dict(row, parameter_pair_in_domain=False, reason='outside at least one finite arc'))
        elif 'UNVERIFIED' in statuses:
            evidence['unresolved'].append(dict(row, parameter_pair_in_domain=None, reason='finite branch membership unresolved'))
        else:
            row.update(parameter_pair_in_domain=True, source_membership=memberships[0], target_membership=memberships[1])
            evidence['same_center_groups'].append([len(evidence['intersections'])])
            evidence['intersections'].append(row)
    complete = not evidence['unresolved']; count = len(evidence['intersections'])
    return dict(classification=('FINITE_CENTERS' if count else 'DISJOINT') if complete else 'UNVERIFIED',
                complete=complete, centers=count if complete else None, infinite=False if complete else None,
                evidence=evidence, reason='all equal-distance cross-branch centers, normal signs and finite memberships classified' if complete
                else 'cross-branch centers proved but some finite memberships remain unresolved')
