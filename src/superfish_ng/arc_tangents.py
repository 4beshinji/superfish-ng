# SPDX-License-Identifier: Apache-2.0
"""Numerical finite-arc assessment of supporting-conic tangent candidates.

Membership is checked with a parameter guard and a physical reconstruction
residual. This is not interval-certified contact containment. Explicit selection
can trim and connect arcs; cavity validation remains a separate operation.
"""
import math
from .conics import EllipseArc, HyperbolaArc, rotation_cos_sin
from .conic_tangents import supporting_conic_tangents


def _positive(value, name, *, upper=None):
    if (type(value) not in (int, float) or not math.isfinite(value) or value <= 0
            or upper is not None and value >= upper):
        raise ValueError(f'{name} must be finite and positive' +
                         (f' and smaller than {upper}' if upper is not None else ''))


def _contact_on_arc(curve, point, guard, position_tolerance):
    c, s = rotation_cos_sin(curve.rotation_rad)
    dz, dr = (point[i]-curve.center_zr_m[i] for i in range(2))
    x = (c*dz+s*dr)/curve.semiaxes_m[0]
    y = (-s*dz+c*dr)/curve.semiaxes_m[1]
    if not all(math.isfinite(v) for v in (x, y)):
        return dict(status='UNVERIFIED', reason='nonfinite local contact coordinates')
    if isinstance(curve, EllipseArc):
        theta = math.atan2(y, x)
        start, span = curve.start_rad, curve.sweep_rad
        # start is normalized and |span|<2pi: these lifts cover the finite arc
        # and both endpoints, including the negative-pi/positive-pi seam.
        fractions = [(theta+turn*2*math.pi-start)/span for turn in range(-2, 3)]
        roundoff = 32*math.ulp(max(1., abs(start), abs(start+span)))/abs(span)
    else:
        if x*curve.branch <= 0:
            return dict(status='EXCLUDED', reason='contact on the other hyperbola branch')
        parameter = math.asinh(y)
        start, span = curve.start_parameter, curve.end_parameter-curve.start_parameter
        fractions = [(parameter-start)/span]
        roundoff = 32*math.ulp(max(1., abs(start), abs(start+span), abs(parameter)))/abs(span)
    if not math.isfinite(roundoff) or roundoff >= guard:
        return dict(status='UNVERIFIED', reason='parameter precision is insufficient for the requested guard')
    if any(min(abs(f), abs(f-1)) <= guard for f in fractions):
        return dict(status='UNVERIFIED', reason='contact near an arc endpoint; no snapping applied',
                    fraction_estimates=fractions)
    interior = [f for f in fractions if guard < f < 1-guard]
    if not interior:
        return dict(status='EXCLUDED', reason='contact outside the finite parameter interval',
                    fraction_estimates=fractions)
    if len(interior) != 1:
        return dict(status='UNVERIFIED', reason='multiple parameter representations in the finite arc')
    fraction = interior[0]
    evaluation = curve.evaluate(fraction)
    distance = math.hypot(*(float(evaluation['points_zr_m'][i])-point[i] for i in range(2)))
    if not math.isfinite(distance) or distance > position_tolerance:
        return dict(status='UNVERIFIED', reason='finite-arc contact reconstruction exceeds position tolerance',
                    position_residual_m=distance, fraction=fraction)
    return dict(status='INTERIOR', fraction=fraction, position_residual_m=distance,
                tangent_zr=tuple(map(float, evaluation['tangent_zr'])))


def finite_arc_tangents(first, second, *, parameter_guard=1e-8,
                        position_tolerance_m=1e-9, angle_tolerance_rad=1e-8,
                        **supporting_controls):
    """Assess finite contacts and first-to-second directed G1 compatibility.

    PASS means the supporting search finished and every returned candidate was
    numerically classified under the explicit tolerances. It does not certify
    real-number containment or permit automatic selection. Endpoint guard hits
    are UNVERIFIED, including apparent exact endpoints. Supporting diagnostics
    and rejected candidates remain in the report. Opposed and zero-length
    candidates remain visible but must not be used as forward line connectors.
    """
    _positive(parameter_guard, 'parameter_guard', upper=.5)
    _positive(position_tolerance_m, 'position_tolerance_m')
    _positive(angle_tolerance_rad, 'angle_tolerance_rad', upper=math.pi/2)
    supporting = supporting_conic_tangents(first, second, **supporting_controls)
    candidates, excluded = [], []
    unresolved = [dict(item, stage='supporting_conic') for item in supporting['unresolved']]
    for index, candidate in enumerate(supporting['candidates']):
        record = dict(candidate, supporting_candidate_index=index)
        try:
            assessments = [_contact_on_arc(curve, point, parameter_guard, position_tolerance_m)
                           for curve, point in zip((first, second), candidate['contacts_zr_m'])]
        except (ValueError, OverflowError, ZeroDivisionError) as error:
            unresolved.append(dict(record, reason=f'finite-arc evaluation failed: {error}'))
            continue
        record['arc_assessments'] = assessments
        # One definite exclusion suffices even if the other arc is unresolved.
        if any(a['status'] == 'EXCLUDED' for a in assessments):
            excluded.append(dict(record, reason='contact excluded by finite arc or branch'))
            continue
        if any(a['status'] == 'UNVERIFIED' for a in assessments):
            reasons = '; '.join(a['reason'] for a in assessments if a['status'] == 'UNVERIFIED')
            unresolved.append(dict(record, reason=reasons))
            continue
        record['contact_fractions'] = tuple(a['fraction'] for a in assessments)
        record['position_residuals_m'] = tuple(a['position_residual_m'] for a in assessments)
        length = candidate['contact_distance_m']
        if length == 0:
            record.update(connection_direction='ZERO_LENGTH', tangent_angles_rad=None)
        else:
            p, q = candidate['contacts_zr_m']
            direction = tuple((q[i]-p[i])/length for i in range(2))
            angles = []
            for assessment in assessments:
                t = assessment['tangent_zr']
                angles.append(math.atan2(abs(t[0]*direction[1]-t[1]*direction[0]),
                                         sum(t[i]*direction[i] for i in range(2))))
            if any(min(a, math.pi-a) > angle_tolerance_rad for a in angles):
                unresolved.append(dict(record, reason='reconstructed directed tangents are not collinear',
                                       tangent_angles_rad=angles))
                continue
            record.update(connection_direction='FORWARD' if max(angles) <= angle_tolerance_rad else 'OPPOSED',
                          tangent_angles_rad=angles)
        candidates.append(record)
    return dict(status='UNVERIFIED' if unresolved else 'PASS', candidates=candidates,
                excluded=excluded, unresolved=unresolved, supporting_result=supporting,
                arc_filter_status='NUMERICALLY_ASSESSED',
                parameter_guard=parameter_guard, position_tolerance_m=position_tolerance_m,
                angle_tolerance_rad=angle_tolerance_rad,
                scope='finite directed arcs; guarded floating parameter estimates, not certified parameter intervals')


def connect_finite_arcs(first, second, *, candidate_index, position_tolerance_m,
                        angle_tolerance_rad, parameter_guard=1e-8, **supporting_controls):
    """Explicitly select a forward tangent and return trimmed arc/line/arc.

    Keep the first arc from its original start to contact and the second from
    contact to its original end. Inputs are immutable. The index is local to
    this exact request, not a persistent identifier across geometry edits.
    Tolerances must be supplied explicitly. Closed-contour validity remains
    the responsibility of the canonical contour validator.
    """
    from dataclasses import replace
    from .conics import LineSegment, check_curve_join

    if type(candidate_index) is not int or candidate_index < 0:
        raise ValueError('candidate_index must be an explicit nonnegative integer')
    report = finite_arc_tangents(first, second, parameter_guard=parameter_guard,
                                position_tolerance_m=position_tolerance_m,
                                angle_tolerance_rad=angle_tolerance_rad, **supporting_controls)
    if report['status'] != 'PASS':
        raise ValueError('tangent enumeration is UNVERIFIED; resolve search or endpoint diagnostics before selecting')
    if candidate_index >= len(report['candidates']):
        raise ValueError('candidate_index is outside the finite-arc candidate list')
    candidate = report['candidates'][candidate_index]
    if candidate['connection_direction'] != 'FORWARD':
        raise ValueError('selected tangent must be forward on both arcs and have nonzero contact distance')
    f, g = candidate['contact_fractions']
    if isinstance(first, EllipseArc):
        left = replace(first, sweep_rad=first.sweep_rad*f)
    else:
        left = replace(first, end_parameter=first.start_parameter+(first.end_parameter-first.start_parameter)*f)
    if isinstance(second, EllipseArc):
        right = replace(second, start_rad=second.start_rad+second.sweep_rad*g,
                        sweep_rad=second.sweep_rad*(1-g))
    else:
        right = replace(second, start_parameter=second.start_parameter+(second.end_parameter-second.start_parameter)*g)
    # Evaluate actual trimmed endpoints so there is no tolerance-based movement
    # of either conic. Recheck G1 on this constructed segment, not the support.
    line = LineSegment(tuple(map(float, left.evaluate(1.)['points_zr_m'])),
                       tuple(map(float, right.evaluate(0.)['points_zr_m'])))
    joins = [check_curve_join(a, b, position_tolerance_m=position_tolerance_m,
                             angle_tolerance_rad=angle_tolerance_rad, require_tangent=True)
             for a, b in ((left, line), (line, right))]
    return dict(curves=(left, line, right), candidate_index=candidate_index,
                selected_candidate=candidate, joins=joins, enumeration=report,
                scope='local directed G1 construction only; closed contour and physical domain not validated')
