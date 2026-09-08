# SPDX-License-Identifier: Apache-2.0
"""Finite-arc membership from rational contact and endpoint enclosures.

Angles/parameters mean the exact stored binary numbers. Supporting rotation
coefficients remain the binary conic convention. No float atan/asinh or endpoint
snapping is used as proof. This module does not yet trim or select a connector.
"""
from fractions import Fraction as F
import math
from .conics import EllipseArc, HyperbolaArc
from .contact_enclosures import supporting_contact_enclosures, _interval_subtract


DEFAULT_ENDPOINT_WIDTH = F(1, 2**100)


def _number(value, name):
    if type(value) not in (int, float, F) or type(value) is float and not math.isfinite(value):
        raise ValueError(f'{name} must be a finite int, float or Fraction')
    return F(value)


def transcendental_interval(kind, value, *, endpoint_width=DEFAULT_ENDPOINT_WIDTH, max_terms=96):
    """Enclose sin, cos or sinh of an exact rational input using Taylor bounds.

    Sin/cos use the Lagrange remainder (derivatives have magnitude <=1).
    Positive sinh terms have a geometric tail bound once the successive-term
    ratio is <1. A term budget failure raises instead of returning an estimate.
    No range reduction or floating transcendental evaluation supplies a bound.
    """
    x = _number(value, 'value')
    width = _number(endpoint_width, 'endpoint_width')
    if width <= 0 or type(max_terms) is not int or max_terms <= 0:
        raise ValueError('endpoint_width and integer max_terms must be positive')
    if kind not in ('sin', 'cos', 'sinh'):
        raise ValueError('kind must be sin, cos or sinh')
    sign = -1 if x < 0 and kind != 'cos' else 1
    x = abs(x)
    term = F(1) if kind == 'cos' else x
    total = F(0)
    for k in range(max_terms):
        total += term
        degree = 2*k if kind == 'cos' else 2*k+1
        following = term*x*x/F((degree+1)*(degree+2))
        if kind == 'sinh':
            ratio = x*x/F((degree+3)*(degree+4))
            bound = (total, total+following/(1-ratio)) if ratio < 1 else None
        else:
            bound = (total-abs(following), total+abs(following))
        if bound is not None and bound[1]-bound[0] <= width:
            return bound if sign > 0 else (-bound[1], -bound[0])
        term = following if kind == 'sinh' else -following
    raise ValueError(f'{kind} endpoint series budget exhausted before requested enclosure width')


def _multiply(a, b):
    values = [x*y for x in a for y in b]
    return min(values), max(values)


def _cross(a, b):
    return _interval_subtract(_multiply(a[0], b[1]), _multiply(a[1], b[0]))


def _equal_point(a, b):
    return all(x[0] == x[1] == y[0] == y[1] for x, y in zip(a, b))


def _disjoint(a, b):
    return any(x[1] < y[0] or y[1] < x[0] for x, y in zip(a, b))


def _arc_membership(curve, local_box, *, endpoint_width=DEFAULT_ENDPOINT_WIDTH, max_series_terms=96,
                    parameter_endpoints=None):
    """Classify a known supporting-conic contact enclosed by local_box.

    Internal helper: the box must come from the corresponding conic enclosure;
    arbitrary off-conic points are not classified as points of a finite arc.
    """
    controls = dict(endpoint_width=endpoint_width, max_terms=max_series_terms)
    if isinstance(curve, HyperbolaArc):
        xlo, xhi = sorted(curve.branch*x for x in local_box[0])
        if xhi < 0:
            return dict(status='EXTERIOR', reason='other hyperbola branch')
        if xlo <= 0:
            return dict(status='UNVERIFIED', reason='branch sign is not separated')
        a, b = parameter_endpoints or (F(curve.start_parameter), F(curve.end_parameter))
        start = transcendental_interval('sinh', a, **controls)
        end = transcendental_interval('sinh', b, **controls)
        y = local_box[1]
        for name, endpoint in (('START', start), ('END', end)):
            if endpoint[0] == endpoint[1] == y[0] == y[1]:
                return dict(status=name, endpoint_bounds=(start, end))
        low, high = (start, end) if a < b else (end, start)
        if y[1] < low[0] or y[0] > high[1]:
            status = 'EXTERIOR'
        elif y[0] > low[1] and y[1] < high[0]:
            status = 'INTERIOR'
        else:
            status = 'UNVERIFIED'
        return dict(status=status, endpoint_bounds=(start, end), reason='monotone sinh endpoint comparison')
    if not isinstance(curve, EllipseArc):
        raise ValueError('finite-arc certification requires ellipse or hyperbola')

    def direction(theta):
        return tuple(transcendental_interval(kind, theta, **controls) for kind in ('cos', 'sin'))

    start_parameter, end_parameter = parameter_endpoints or (F(curve.start_rad), F(curve.start_rad)+F(curve.sweep_rad))
    start, end = direction(start_parameter), direction(end_parameter)
    for name, endpoint in (('START', start), ('END', end)):
        if _equal_point(local_box, endpoint):
            return dict(status=name, endpoint_bounds=(start, end))
    endpoints_separated = _disjoint(local_box, start) and _disjoint(local_box, end)
    low, high = sorted((start_parameter, end_parameter))
    # Every CCW sector spans at most 2 radians, strictly less than pi. Their
    # union covers the directed arc image even across the atan branch cut.
    count = math.ceil((high-low)/2)
    parameters = [low+(high-low)*F(i, count) for i in range(count+1)]
    directions = [direction(t) for t in parameters]
    sectors = []
    interior = False
    for a, b in zip(directions, directions[1:]):
        left, right = _cross(a, local_box), _cross(local_box, b)
        outside = left[1] < 0 or right[1] < 0
        inside = (left[0] > 0 and right[0] > 0 or
                  left[0] >= 0 and right[0] >= 0 and endpoints_separated)
        sectors.append(dict(left_cross=left, right_cross=right, excluded=outside))
        interior |= inside
    status = 'INTERIOR' if interior else 'EXTERIOR' if all(s['excluded'] for s in sectors) else 'UNVERIFIED'
    return dict(status=status, endpoint_bounds=(start, end), sectors=sectors,
                reason='closed short-sector union with original endpoint separation')


def _parameter_fraction_enclosure(curve, box, *, fraction_width=F(1, 2**32), max_fraction_steps=64,
                                   endpoint_width=DEFAULT_ENDPOINT_WIDTH, max_series_terms=96):
    """Bisect the monotone traversal fraction using certified prefix membership."""
    width = _number(fraction_width, 'fraction_width')
    if not 0 < width < 1 or type(max_fraction_steps) is not int or max_fraction_steps < 1:
        raise ValueError('fraction_width must be between zero and one; max_fraction_steps must be a positive integer')
    controls = dict(endpoint_width=endpoint_width, max_series_terms=max_series_terms)
    membership = _arc_membership(curve, box, **controls)['status']
    if membership in ('START', 'END'):
        point = F(0 if membership == 'START' else 1)
        return dict(status='PASS', interval=(point, point), steps=0)
    if membership != 'INTERIOR':
        return dict(status='UNVERIFIED', interval=None, steps=0, reason='contact is not certified inside the original arc')
    a, b = ((F(curve.start_rad), F(curve.start_rad)+F(curve.sweep_rad)) if isinstance(curve, EllipseArc)
            else (F(curve.start_parameter), F(curve.end_parameter)))
    lo, hi = F(0), F(1)
    for step in range(1, max_fraction_steps+1):
        middle = (lo+hi)/2
        try:
            status = _arc_membership(curve, box, parameter_endpoints=(a, a+(b-a)*middle), **controls)['status']
        except ValueError as error:
            return dict(status='UNVERIFIED', interval=(lo, hi), steps=step, reason=str(error))
        if status == 'END':
            return dict(status='PASS', interval=(middle, middle), steps=step)
        if status == 'INTERIOR':
            hi = middle
        elif status == 'EXTERIOR':
            lo = middle
        else:
            return dict(status='UNVERIFIED', interval=(lo, hi), steps=step,
                        reason='prefix endpoint comparison is not separated')
        if hi-lo <= width:
            return dict(status='PASS', interval=(lo, hi), steps=step)
    return dict(status='UNVERIFIED', interval=(lo, hi), steps=max_fraction_steps,
                reason='fraction bisection budget exhausted')


def certified_finite_arc_tangents(first, second, *, endpoint_width=DEFAULT_ENDPOINT_WIDTH,
                                  max_series_terms=96, fraction_width=F(1, 2**32),
                                  max_fraction_steps=64, **enclosure_controls):
    """Certify geometric arc membership of supporting tangent contacts.

    PASS means the enclosure search, memberships and fraction widths passed. START/END
    are exact point equalities; INTERIOR/EXTERIOR use rational inequalities.
    Unknowns remain visible. Direction-compatible trimming is a separate step.
    """
    transcendental_interval('sin', 0, endpoint_width=endpoint_width, max_terms=max_series_terms)
    width = _number(fraction_width, 'fraction_width')
    if not 0 < width < 1 or type(max_fraction_steps) is not int or max_fraction_steps < 1:
        raise ValueError('fraction_width must be between zero and one; max_fraction_steps must be a positive integer')
    search = supporting_contact_enclosures(first, second, **enclosure_controls)
    candidates, excluded = [], []
    unresolved = list(search['unresolved'])
    for item in search['contacts']:
        record = dict(item)
        assessments = []
        for curve, box in zip((first, second), item['local_contact_boxes']):
            try:
                assessments.append(_arc_membership(curve, box, endpoint_width=endpoint_width,
                                                    max_series_terms=max_series_terms))
            except ValueError as error:
                assessments.append(dict(status='UNVERIFIED', reason=str(error)))
        record['arc_memberships'] = assessments
        if any(row['status'] == 'EXTERIOR' for row in assessments):
            excluded.append(record)
        elif any(row['status'] == 'UNVERIFIED' for row in assessments):
            unresolved.append(dict(record, stage='finite_arc', reason='finite arc membership not separated'))
        else:
            fractions = []
            for curve, box in zip((first, second), item['local_contact_boxes']):
                try:
                    fractions.append(_parameter_fraction_enclosure(curve, box, fraction_width=width,
                                     max_fraction_steps=max_fraction_steps, endpoint_width=endpoint_width,
                                     max_series_terms=max_series_terms))
                except ValueError as error:
                    fractions.append(dict(status='UNVERIFIED', interval=(F(0), F(1)), reason=str(error)))
            record['parameter_fractions'] = fractions
            candidates.append(record)
            if any(row['status'] != 'PASS' for row in fractions):
                unresolved.append(dict(supporting_candidate_index=item['supporting_candidate_index'],
                                       stage='parameter_fraction', reason='parameter fraction enclosure not resolved'))
    return dict(status='UNVERIFIED' if unresolved else 'PASS', candidates=candidates,
                excluded=excluded, unresolved=unresolved, contact_enclosures=search,
                endpoint_width=F(endpoint_width), max_series_terms=max_series_terms,
                fraction_width=width, max_fraction_steps=max_fraction_steps,
                scope='finite arc membership for exact binary parameters and supporting coefficients; no trimming or original real-input uncertainty guarantee')
