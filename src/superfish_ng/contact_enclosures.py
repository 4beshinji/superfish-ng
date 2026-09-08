# SPDX-License-Identifier: Apache-2.0
"""Exact-rational contact boxes for isolated binary-coefficient conic tangents.

The boxes enclose contacts of the supporting conics defined by their exact
binary input coefficients. Finite-arc membership and transcendental input
rounding are separate questions. No approximate contact is used as a bound.
"""
from fractions import Fraction as F
import math
from .conic_tangents import supporting_conic_tangents, _central, _quadratic, _range, _subtract
from .polynomial_roots import _value
from .conics import HyperbolaArc, rotation_cos_sin
from .rational_bounds import polynomial, add, multiply, _sqrt_bound


def _interval_add(a, b):
    return a[0]+b[0], a[1]+b[1]


def _interval_subtract(a, b):
    return a[0]-b[1], a[1]-b[0]


def _interval_divide(a, b):
    if b[0] <= 0 <= b[1]:
        raise ValueError('contact denominator interval contains zero; refine the normal root interval')
    quotients = [x/y for x in a for y in b]
    return min(quotients), max(quotients)


def _contact_boxes(centers, matrices, candidate):
    chart = candidate['chart']
    lo, hi = candidate['normal_interval']
    if candidate['normal_parameter_is_exact_root']:
        lo = hi = candidate['normal_parameter']
    difference = tuple(centers[1][i]-centers[0][i] for i in range(2))
    d = polynomial(difference if chart == 0 else difference[::-1])
    q1, q2 = (_quadratic(q, chart) for q in matrices)
    D = _range(d, lo, hi)
    if D == (0, 0):
        if lo != hi:
            # Concentric conics have D identically zero. Q1(t)=Q2(t) at the
            # isolated root, and both signs of sqrt(Q1(t)) are distinct lines.
            a, b = _range(q1, lo, hi)
        else:
            a = b = _value(q1, lo)
        if a <= 0:
            raise ValueError('contact square interval is not strictly positive')
        positive = (F(_sqrt_bound(a, upper=False)), F(_sqrt_bound(b, upper=True)))
        offset = candidate['offset_from_origin_m']
        if offset == 0:
            raise ValueError('returned line offset cannot distinguish the contact sign')
        w1 = positive if offset > 0 else (-positive[1], -positive[0])
    else:
        numerator = add(multiply(d, d), _subtract(q1, q2))
        w1 = _interval_divide(_range(numerator, lo, hi), (2*D[0], 2*D[1]))
    w2 = _interval_subtract(w1, D)
    boxes = []
    for center, matrix, offset in zip(centers, matrices, (w1, w2)):
        coordinates = []
        for i in range(2):
            coefficients = matrix[i] if chart == 0 else matrix[i][::-1]
            delta = _interval_divide(_range(coefficients, lo, hi), offset)
            coordinates.append(_interval_add((center[i], center[i]), delta))
        boxes.append(tuple(coordinates))
    return tuple(boxes)


def _local_contact_box(curve, box):
    # Invert the exact binary rotation matrix, not its transpose: the rounded
    # cos/sin coefficients need not satisfy c*c+s*s == 1 as rational numbers.
    c, s = map(F, rotation_cos_sin(curve.rotation_rad))
    determinant = c*c+s*s
    delta = [_interval_subtract(interval, (F(center), F(center)))
             for interval, center in zip(box, curve.center_zr_m)]
    result = []
    for coefficients, axis in zip(((c, s), (-s, c)), curve.semiaxes_m):
        interval = (F(0), F(0))
        for coefficient, source in zip(coefficients, delta):
            product = sorted(coefficient*value for value in source)
            interval = _interval_add(interval, product)
        result.append(_interval_divide(interval, (F(axis)*determinant,)*2))
    return tuple(result)


def supporting_contact_enclosures(first, second, *, max_contact_width_m=1e-9, **supporting_controls):
    """Enclose each isolated supporting tangent contact in closed rational boxes.

    PASS requires a complete supporting search, nonzero denominator separation,
    and each coordinate width <= max_contact_width_m. Returned-point error
    bounds are separate from box widths. An exact rational root is evaluated as
    a point; other open root intervals are conservatively treated as closed.
    Existing construction/GUI documents are not changed by this separate API.
    """
    if (type(max_contact_width_m) not in (int, float) or not math.isfinite(max_contact_width_m)
            or max_contact_width_m <= 0):
        raise ValueError('max_contact_width_m must be finite and positive')
    search = supporting_conic_tangents(first, second, **supporting_controls)
    data = (_central(first), _central(second))
    centers, matrices = tuple(row[0] for row in data), tuple(row[1] for row in data)
    contacts = []
    unresolved = [dict(row, stage='supporting_search') for row in search['unresolved']]
    for index, candidate in enumerate(search['candidates']):
        record = dict(supporting_candidate_index=index, candidate=candidate)
        try:
            boxes = _contact_boxes(centers, matrices, candidate)
            record['contact_boxes_zr_m'] = boxes
            local_boxes = tuple(_local_contact_box(curve, box) for curve, box in zip((first, second), boxes))
            branches = []
            for curve, box in zip((first, second), local_boxes):
                if not isinstance(curve, HyperbolaArc):
                    branches.append('NOT_APPLICABLE')
                else:
                    lo, hi = sorted(curve.branch*x for x in box[0])
                    branches.append('MATCHES' if lo > 0 else 'OTHER' if hi < 0 else 'UNVERIFIED')
            record.update(local_contact_boxes=local_boxes, specified_branch_status=tuple(branches))
            widths = tuple(tuple(hi-lo for lo, hi in box) for box in boxes)
            error_bounds = []
            for point, box in zip(candidate['contacts_zr_m'], boxes):
                square = sum(max(abs(F(x)-lo), abs(F(x)-hi))**2 for x, (lo, hi) in zip(point, box))
                error_bounds.append(_sqrt_bound(square, upper=True))
            width_ok = all(width <= F(max_contact_width_m) for row in widths for width in row)
            record.update(enclosure_status='ENCLOSED', coordinate_widths_m=widths,
                          returned_point_error_bounds_m=tuple(error_bounds),
                          width_status='PASS' if width_ok else 'UNVERIFIED')
            contacts.append(record)
            if not width_ok:
                unresolved.append(dict(supporting_candidate_index=index, reason='contact box exceeds requested coordinate width',
                                       stage='contact_enclosure'))
        except (ValueError, OverflowError, ZeroDivisionError) as error:
            unresolved.append(dict(record, stage='contact_enclosure', reason=str(error)))
    return dict(status='UNVERIFIED' if unresolved else 'PASS', contacts=contacts,
                unresolved=unresolved, supporting_result=search, max_contact_width_m=max_contact_width_m,
                scope='closed rational contact boxes for binary-coefficient supporting conics; finite arcs and input rounding not certified')
