# SPDX-License-Identifier: Apache-2.0
"""Equal normal offsets on one noncircular conic in different principal frames.

Support equality and the change of normalized source coordinates are exact
rational identities. Angle shifts remain symbolic multiples of pi; no rounded
replacement curve is made. Reflected contacts retain both original frames.
"""
from fractions import Fraction as F

from .conics import EllipseArc, HyperbolaArc, rotation_cos_sin
from .coincident_circle_arcs import pi_bounds
from .certified_arcs import _arc_membership
from .same_conic_offset_intersections import _scale, _self_contacts, _same_endpoint_as_contact


def _support_map(first, second):
    """Return A_first^-1 A_second if both parameterizations share one branch.

    A=R diag(a,b). Distinct orthogonal ellipse principal axes allow only four
    signed permutations. Orthogonal hyperbola axes allow only I and -I.
    Testing those identities also retains the norm of each binary rotation.
    """
    if type(first) is not type(second) or not isinstance(first, (EllipseArc, HyperbolaArc)):
        return None
    if isinstance(first, EllipseArc) and first.semiaxes_m[0] == first.semiaxes_m[1]:
        return None
    if first.center_zr_m != second.center_zr_m:
        return None
    a, b = map(F, first.semiaxes_m); u, v = map(F, second.semiaxes_m)
    c, s = map(F, rotation_cos_sin(first.rotation_rad))
    x, y = map(F, rotation_cos_sin(second.rotation_rad))
    norm = c*c+s*s; dot, cross = c*x+s*y, c*y-s*x
    matrix = ((dot*u/(norm*a), -cross*v/(norm*a)),
              (cross*u/(norm*b), dot*v/(norm*b)))
    phases = {((1, 0), (0, 1)): F(0), ((0, -1), (1, 0)): F(1, 2),
              ((-1, 0), (0, -1)): F(1), ((0, 1), (-1, 0)): F(-1, 2)}
    if isinstance(first, EllipseArc):
        if matrix not in phases:
            return None
        orientation, phase = 1, phases[matrix]
    else:
        if matrix not in (((1, 0), (0, 1)), ((-1, 0), (0, -1))):
            return None
        if first.branch != matrix[0][0]*second.branch:
            return None
        orientation, phase = int(matrix[1][1]), F(0)
    return dict(second_to_first=matrix, parameter_orientation=orientation,
                phase_pi_coefficient=phase, first_rotation=(c, s), first_rotation_square=norm)


def _ranges(curves, domains):
    ranges, endpoints = [], []
    for curve, domain in zip(curves, domains):
        if isinstance(curve, EllipseArc):
            start, span = F(curve.start_rad), F(curve.sweep_rad)
        else:
            start, span = F(curve.start_parameter), F(curve.end_parameter)-F(curve.start_parameter)
        endpoints.append(tuple(start+span*F(t) for t in domain))
        ranges.append(tuple(sorted(endpoints[-1])))
    return ranges, endpoints


def _diagonal(ranges, mapping, ellipse, width, max_terms):
    first, raw_second = ranges
    second = tuple(sorted(mapping['parameter_orientation']*t for t in raw_second))
    phase = mapping['phase_pi_coefficient']
    records = []
    if ellipse:
        pi = pi_bounds(width/64, max_terms)
        shift = _scale(pi, phase)
        quotients = [value/(2*p) for value in
                     (first[0]-second[1]-shift[1], first[1]-second[0]-shift[0]) for p in pi]
        lower, upper = min(quotients), max(quotients)
        first_period = -((-lower.numerator)//lower.denominator)
        last_period = upper.numerator//upper.denominator
    else:
        pi = None; first_period = last_period = 0
    for period in range(first_period, last_period+1):
        coefficient = phase+2*period
        shift = (F(0), F(0)) if coefficient == 0 else _scale(pi, coefficient)
        low = tuple(max(first[0], second[0]+t) for t in shift)
        high = tuple(min(first[1], second[1]+t) for t in shift)
        if low[0] > high[1]:
            kind = 'DISJOINT'
        elif low[1] < high[0]:
            kind = 'POSITIVE_INTERVAL'
        elif coefficient == 0 and low[0] == low[1] == high[0] == high[1]:
            kind = 'SHARED_ENDPOINT'
        else:
            kind = 'UNVERIFIED'
        records.append(dict(period=period, pi_coefficient=coefficient, shift_bounds=shift,
                            overlap_start_bounds=low, overlap_end_bounds=high, classification=kind))
    return dict(original_parameter_ranges=ranges, second_oriented_range=second, pi_bounds=pi,
                period_range=(first_period, last_period), periodic_intersections=records,
                complete=all(row['classification'] != 'UNVERIFIED' for row in records),
                positive_components=sum(row['classification'] == 'POSITIVE_INTERVAL' for row in records),
                shared_endpoints=[row['overlap_start_bounds'][0] for row in records
                                  if row['classification'] == 'SHARED_ENDPOINT'])


def _inverse_point(matrix, point):
    # The exact support map is orthogonal, so the inverse is its transpose.
    result = []
    for column in zip(*matrix):
        terms = [_scale(box, value) for value, box in zip(column, point)]
        result.append(tuple(sum(term[i] for term in terms) for i in (0, 1)))
    return tuple(result)


def classify_reparameterized_conic_offsets(curves, distances, domains, *, endpoint_width, max_series_terms):
    """Private extension; None means no proved common offset, not disjointness."""
    first, second = curves; mapping = _support_map(first, second)
    if mapping is None:
        return None
    spans = [F(c.sweep_rad) if isinstance(c, EllipseArc) else F(c.end_parameter)-F(c.start_parameter)
             for c in curves]
    oriented = [(1 if span > 0 else -1)*F(d) for span, d in zip(spans, distances)]
    oriented[1] *= mapping['parameter_orientation']
    if oriented[0] != oriented[1]:
        return None
    width = F(endpoint_width); ranges, endpoints = _ranges(curves, domains)
    evidence = dict(identity='one noncircular conic and equal normal distance under an exact principal-frame map',
                    support_map=mapping, oriented_distances=oriented, self_contacts=[], unresolved=[])
    try:
        diagonal = _diagonal(ranges, mapping, isinstance(first, EllipseArc), width, max_series_terms)
    except ValueError as error:
        diagonal = dict(complete=False, positive_components=0, shared_endpoints=[])
        evidence['unresolved'].append(dict(stage='diagonal overlap', reason=str(error)))
    evidence['diagonal'] = diagonal; complete = diagonal['complete']; accepted = 0
    controls = dict(endpoint_width=endpoint_width, max_series_terms=max_series_terms)
    candidates = _self_contacts(first, oriented[0], mapping['first_rotation_square'], width/64)
    for row in candidates:
        contacts = (row['contacts'], tuple(_inverse_point(mapping['second_to_first'], p) for p in row['contacts']))
        memberships = []
        for curve, points, ends in zip(curves, contacts, endpoints):
            values = []
            for point in points:
                try:
                    values.append(_arc_membership(curve, point, parameter_endpoints=ends, **controls))
                except ValueError as error:
                    values.append(dict(status='UNVERIFIED', reason=str(error)))
            memberships.append(values)
        directions = []
        for left, right in ((0, 1), (1, 0)):
            statuses = memberships[0][left]['status'], memberships[1][right]['status']
            directions.append(False if 'EXTERIOR' in statuses else None if 'UNVERIFIED' in statuses else True)
        row.update(contacts_in_original_frames=contacts, membership=memberships,
                   parameter_pair_directions=directions,
                   included_parameter_pairs=[pair for pair, present in zip(((0, 1), (1, 0)), directions) if present],
                   parameter_pair_in_domain=True if True in directions else None if None in directions else False)
        if None in directions:
            complete = False
        if True in directions:
            duplicates = []
            for parameter in diagonal['shared_endpoints']:
                try:
                    duplicates.append(_same_endpoint_as_contact(first, parameter, row['contacts'],
                                      dict(endpoint_width=endpoint_width, max_terms=max_series_terms)))
                except ValueError:
                    duplicates.append(None)
            row['duplicates_shared_endpoint'] = duplicates
            if None in duplicates:
                complete = False
            if all(value is False for value in duplicates):
                accepted += 1
        evidence['self_contacts'].append(row)
    positive, shared = diagonal['positive_components'], len(diagonal['shared_endpoints'])
    evidence['distinct_added_centers'] = accepted
    if positive:
        classification, centers, infinite = 'INFINITE_PARAMETER_PAIRS', None, True
    elif not complete:
        classification, centers, infinite = ('SHARED_PARAMETER_ENDPOINT' if shared else 'UNVERIFIED'), None, None
    elif accepted:
        classification, centers, infinite = 'FINITE_CENTERS', accepted+shared, False
    elif shared:
        classification, centers, infinite = 'SHARED_PARAMETER_ENDPOINT', shared, False
    else:
        classification, centers, infinite = 'DISJOINT', 0, False
    return dict(classification=classification, complete=complete, centers=centers, infinite=infinite, evidence=evidence,
                reason='all mapped equal-point intervals and reflected source pairs classified' if complete else
                'some mapped intervals, source memberships or endpoint identities remain unresolved')
