# SPDX-License-Identifier: Apache-2.0
"""Explicit trimming guarded by certified contact/fraction enclosures."""
from dataclasses import replace
from fractions import Fraction as F
import math
from .arc_tangents import _positive
from .certified_arcs import certified_finite_arc_tangents, transcendental_interval, _multiply, DEFAULT_ENDPOINT_WIDTH
from .contact_enclosures import _interval_add
from .conics import EllipseArc, LineSegment, check_curve_join, curve_from_dict, curve_to_dict, rotation_cos_sin
from .rational_bounds import _sqrt_bound


def _endpoint_box(curve, at_end, endpoint_controls):
    if isinstance(curve, EllipseArc):
        parameter = F(curve.start_rad)+(F(curve.sweep_rad) if at_end else 0)
        local = tuple(transcendental_interval(kind, parameter, **endpoint_controls) for kind in ('cos', 'sin'))
    else:
        parameter = curve.end_parameter if at_end else curve.start_parameter
        y = transcendental_interval('sinh', parameter, **endpoint_controls)
        lower = F(0) if y[0] <= 0 <= y[1] else min(x*x for x in y)
        upper = max(x*x for x in y)
        positive = (F(_sqrt_bound(1+lower, upper=False)), F(_sqrt_bound(1+upper, upper=True)))
        local = (positive if curve.branch > 0 else (-positive[1], -positive[0]), y)
    local = [_multiply(box, (F(axis),)*2) for box, axis in zip(local, curve.semiaxes_m)]
    c, s = map(F, rotation_cos_sin(curve.rotation_rad))
    result = []
    emitted = curve.evaluate(1. if at_end else 0.)['points_zr_m']
    for row, center, point in zip(((c,-s),(s,c)),curve.center_zr_m,emitted):
        box = (F(center),)*2
        for coefficient, coordinate in zip(row,local):
            box = _interval_add(box,_multiply((coefficient,)*2,coordinate))
        # Also cover the float coordinates used by LineSegment/GUI evaluation.
        result.append((min(box[0],F(float(point))),max(box[1],F(float(point)))))
    return tuple(result)


def _distance_bound(first, second):
    squared = sum(max(abs(a[0]-b[1]),abs(a[1]-b[0]))**2 for a,b in zip(first,second))
    return _sqrt_bound(squared,upper=True)


def _build(first, second, item, position_tolerance_m, angle_tolerance_rad, endpoint_controls):
    statuses = [row['status'] for row in item['arc_memberships']]
    if statuses[0] == 'START' or statuses[1] == 'END':
        return dict(connection_direction='EMPTY_ARC', construction_reason='selection would remove a retained arc; empty arcs are not silently deleted')
    if any(row['status'] != 'PASS' for row in item['parameter_fractions']):
        raise ValueError('parameter fraction enclosure is UNVERIFIED')
    fractions = []
    for row in item['parameter_fractions']:
        lo, hi = row['interval']
        value = float((lo+hi)/2)
        if not lo <= F(value) <= hi:
            raise ValueError('fraction enclosure has no representable midpoint; refine representation or request')
        fractions.append(value)
    f, g = fractions
    if not 0 < f <= 1 or not 0 <= g < 1:
        raise ValueError('trimming would create an empty or unrepresentable arc')
    if statuses[0] == 'END':
        left = first
    elif isinstance(first, EllipseArc):
        left = replace(first, sweep_rad=float(F(first.sweep_rad)*F(f)))
    else:
        left = replace(first, end_parameter=float(F(first.start_parameter)+(F(first.end_parameter)-F(first.start_parameter))*F(f)))
    if statuses[1] == 'START':
        right = second
    elif isinstance(second, EllipseArc):
        right = replace(second, start_rad=float(F(second.start_rad)+F(second.sweep_rad)*F(g)),
                        sweep_rad=float(F(second.sweep_rad)*(1-F(g))))
    else:
        right = replace(second, start_parameter=float(F(second.start_parameter)+(F(second.end_parameter)-F(second.start_parameter))*F(g)))
    p = tuple(map(float, left.evaluate(1.)['points_zr_m']))
    q = tuple(map(float, right.evaluate(0.)['points_zr_m']))
    trim_boxes = (_endpoint_box(left,True,endpoint_controls),_endpoint_box(right,False,endpoint_controls))
    error_bounds = []
    for trim_box, contact_box in zip(trim_boxes,item['contact_boxes_zr_m']):
        bound = _distance_bound(trim_box,contact_box)
        error_bounds.append(bound)
        if F(bound) > F(position_tolerance_m):
            raise ValueError(f'trimmed contact error bound {bound:.9g} m exceeds position_tolerance_m={position_tolerance_m:.9g}; refine root/fraction intervals')
    if p == q:
        return dict(connection_direction='ZERO_LENGTH', construction_reason='trimmed contacts coincide at output precision')
    line = LineSegment(p, q)
    direction = line.evaluate(.5)['tangent_zr']
    tangents = (left.evaluate(1.)['tangent_zr'], right.evaluate(0.)['tangent_zr'])
    if any(sum(float(t[i])*float(direction[i]) for i in range(2)) <= 0 for t in tangents):
        return dict(connection_direction='OPPOSED', construction_reason='line does not follow both directed arcs')
    joins = [check_curve_join(a, b, position_tolerance_m=position_tolerance_m,
                             angle_tolerance_rad=angle_tolerance_rad, require_tangent=True)
             for a, b in ((left, line), (line, right))]
    end_gap = math.dist(tuple(map(float, second.evaluate(1.)['points_zr_m'])),
                        tuple(map(float, right.evaluate(1.)['points_zr_m'])))
    outer_bound = _distance_bound(_endpoint_box(second,True,endpoint_controls),
                                  _endpoint_box(right,True,endpoint_controls))
    if F(outer_bound) > F(position_tolerance_m):
        raise ValueError('rounded trimming changes the retained outer endpoint beyond position_tolerance_m')
    return dict(connection_direction='FORWARD', contact_fractions=tuple(fractions),
                trim_contacts_zr_m=(p, q), trim_contact_error_bounds_m=tuple(error_bounds),
                retained_outer_endpoint_gap_m=end_gap, retained_outer_endpoint_error_bound_m=outer_bound,
                trim_endpoint_boxes_zr_m=trim_boxes, joins=joins,
                trimmed_curves=[curve_to_dict(curve) for curve in (left, line, right)])


def certified_construction_candidates(first, second, *, position_tolerance_m, angle_tolerance_rad,
                                       **certification_controls):
    """Enumerate certified memberships and assess each possible numeric trim.

    Search status concerns completeness of certificates. Individual construction
    failures remain visible and unselectable; they do not hide other candidates.
    Position error is bounded against contact boxes. G1 angle and outer endpoint
    checks concern the actual floating primitives, not certified tangent angles.
    """
    _positive(position_tolerance_m, 'position_tolerance_m')
    _positive(angle_tolerance_rad, 'angle_tolerance_rad', upper=math.pi/2)
    certificate = certified_finite_arc_tangents(first, second, **certification_controls)
    candidates = []
    unresolved = list(certificate['unresolved'])
    for item in certificate['candidates']:
        record = dict(item['candidate'], **item)
        try:
            record.update(_build(first, second, item, position_tolerance_m, angle_tolerance_rad,
                                 dict(endpoint_width=certification_controls.get('endpoint_width',DEFAULT_ENDPOINT_WIDTH),
                                      max_terms=certification_controls.get('max_series_terms',96))))
        except (ValueError, OverflowError) as error:
            record.update(connection_direction='UNVERIFIED', construction_reason=str(error))
            unresolved.append(dict(stage='numeric_trim', candidate_index=len(candidates), reason=str(error)))
        candidates.append(record)
    return dict(status=certificate['status'], candidates=candidates, unresolved=unresolved,
                excluded=certificate['excluded'], certificate=certificate,
                position_tolerance_m=position_tolerance_m, angle_tolerance_rad=angle_tolerance_rad,
                arc_filter_status='CERTIFIED_MEMBERSHIP_AND_FRACTIONS',
                scope='certified binary-model membership/fractions and trim contact error; floating G1 angle; closed contour checked separately')


def connect_certified_arcs(first, second, *, candidate_index, **controls):
    if type(candidate_index) is not int or candidate_index < 0:
        raise ValueError('candidate_index must be an explicit nonnegative integer')
    report = certified_construction_candidates(first, second, **controls)
    if report['status'] != 'PASS':
        raise ValueError('certified tangent enumeration is UNVERIFIED; resolve interval diagnostics before selecting')
    if candidate_index >= len(report['candidates']):
        raise ValueError('candidate_index is outside the certified finite-arc candidate list')
    candidate = report['candidates'][candidate_index]
    if candidate['connection_direction'] != 'FORWARD':
        raise ValueError(candidate.get('construction_reason', 'selected tangent is not a forward verified construction'))
    return dict(curves=tuple(curve_from_dict(row) for row in candidate['trimmed_curves']),
                selected_candidate=candidate, joins=candidate['joins'], enumeration=report)
