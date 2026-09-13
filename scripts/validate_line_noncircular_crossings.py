# SPDX-License-Identifier: Apache-2.0
"""Independent direct-parameter projection extrema and monotone root brackets.

The reference evaluates original trigonometric/hyperbolic normal offsets. It
does not use product rational charts, elimination polynomials or Sturm roots.
"""
import argparse
from dataclasses import replace
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import itertools
import json
from pathlib import Path
import time
from validate_general_coincident_circle_arcs import decimal_value, phase_reference, sine_cosine, reference_pi
from superfish_ng.conics import EllipseArc, HyperbolaArc, LineSegment
from superfish_ng.line_noncircular_crossings import classify_line_noncircular_crossings


def reference(curve, line, distances, domains, scale):
    import math
    ellipse = isinstance(curve, EllipseArc)
    # Independent binary rotation convention, including exact quarter turns.
    quarter = round(curve.rotation_rad/(math.pi/2))
    if curve.rotation_rad == quarter*(math.pi/2):
        c, s = ((1, 0), (0, 1), (-1, 0), (0, -1))[quarter % 4]
    else:
        c, s = math.cos(curve.rotation_rad), math.sin(curve.rotation_rad)
    c, s = decimal_value(c), decimal_value(s)
    unit = decimal_value(scale)
    a, b = [decimal_value(x)/unit for x in curve.semiaxes_m]
    center = [decimal_value(x)/unit for x in curve.center_zr_m]
    p, end = [tuple(decimal_value(x)/unit for x in row) for row in (line.start_zr_m, line.end_zr_m)]
    delta = tuple(y-x for x, y in zip(p, end)); normal = -delta[1], delta[0]
    squared = sum(x*x for x in delta); length = squared.sqrt()
    start = decimal_value(curve.start_rad if ellipse else curve.start_parameter)
    span = decimal_value(curve.sweep_rad) if ellipse else decimal_value(curve.end_parameter)-start
    low, high = sorted(start+span*decimal_value(t) for t in domains[0])
    distance, line_distance = [decimal_value(x)/unit for x in distances]
    distance *= 1 if span > 0 else -1
    branch = 1 if ellipse else curve.branch
    n = c*c+s*s
    curvature_numerator = a*b*n*(1 if ellipse else -branch)
    u, v = c*normal[0]+s*normal[1], -s*normal[0]+c*normal[1]
    tolerance = D('1e-90')

    def evaluate(t):
        if ellipse:
            sn, cs = sine_cosine(t); x, y = a*cs, b*sn; dx, dy = -a*sn, b*cs
        else:
            positive, negative = t.exp(), (-t).exp()
            sn, cs = (positive-negative)/2, (positive+negative)/2
            x, y = branch*a*cs, b*sn; dx, dy = branch*a*sn, b*cs
        tx, ty = c*dx-s*dy, s*dx+c*dy
        speed = (tx*tx+ty*ty).sqrt()
        point = center[0]+c*x-s*y-distance*ty/speed, center[1]+s*x+c*y+distance*tx/speed
        incidence = sum(n*(x-y) for n, x, y in zip(normal, point, p))-line_distance*length
        factor = 1-distance*curvature_numerator/speed**3
        tangent = normal[0]*tx+normal[1]*ty
        fraction = sum(d*(x-y) for d, x, y in zip(delta, point, p))/squared
        return incidence, point, factor, tangent, fraction

    critical = [low, high]
    pi = reference_pi()
    def add_angle(angle):
        for turn in range(-4, 5):
            t = angle+2*turn*pi
            if low < t < high:
                critical.append(t)
    if ellipse:
        tangent = phase_reference(F(a*u), F(b*v))
        add_angle(tangent); add_angle(tangent+pi)
    elif u:
        ratio = -b*v/(branch*a*u)
        if abs(ratio) < 1:
            t = ((1+ratio)/(1-ratio)).ln()/2
            if low < t < high:
                critical.append(t)
    if distance*curvature_numerator > 0:
        speed_squared = (2*(distance*curvature_numerator).ln()/3).exp()
        q = (speed_squared/n-b*b)/(a*a-b*b if ellipse else a*a+b*b)
        if abs(q) < tolerance:
            q = D(0)
        if ellipse:
            if abs(q-1) < tolerance:
                q = D(1)
            if 0 <= q <= 1:
                angle = phase_reference(F((1-q).sqrt()), F(q.sqrt()))
                for t in (angle, -angle, pi-angle, pi+angle): add_angle(t)
        elif q >= 0:
            t = (q.sqrt()+(1+q).sqrt()).ln()
            for value in (-t, t):
                if low < value < high:
                    critical.append(value)
    critical.sort()
    unique = []
    for t in critical:
        if not unique or t-unique[-1] > tolerance:
            unique.append(t)
    def sign(value):
        return 0 if abs(value) < tolerance else 1 if value > 0 else -1
    values = [evaluate(t)[0] for t in unique]
    roots = [t for t, value in zip(unique, values) if sign(value) == 0]
    for lo, hi, left, right in zip(unique, unique[1:], values, values[1:]):
        if sign(left)*sign(right) != -1:
            continue
        for _ in range(360):
            mid = (lo+hi)/2; value = evaluate(mid)[0]
            if value == 0:
                lo = hi = mid; break
            if (left > 0) == (value > 0): lo, left = mid, value
            else: hi = mid
        assert hi-lo < D('1e-100')
        roots.append((lo+hi)/2)
    accepted = []
    for t in sorted(roots):
        residual, point, factor, tangent, fraction = evaluate(t)
        assert abs(residual) < tolerance
        if decimal_value(domains[1][0])-tolerance <= fraction <= decimal_value(domains[1][1])+tolerance:
            accepted.append(dict(parameter=t, point=tuple(x*unit for x in point),
                                 kind='CUSP' if sign(factor) == 0 else 'REGULAR_TANGENCY' if sign(tangent) == 0 else 'TRANSVERSE'))
    groups = []
    for i, row in enumerate(accepted):
        for group in groups:
            if max(abs(x-y) for x, y in zip(row['point'], accepted[group[0]]['point'])) < unit*tolerance:
                group.append(i); break
        else: groups.append([i])
    return accepted, groups, len(unique)-1


def cases():
    for ellipse, branch, scale, distance, partial in itertools.product((False, True), (-1, 1), (2.**-80, 1., 2.**80), (-.5, .25, 1., 2.), (False, True)):
        if ellipse and branch != 1: continue
        curve = (EllipseArc((0, 0), (2*scale, scale), -3., 6.) if ellipse else
                 HyperbolaArc((0, 0), (2*scale, scale), -2., 2., branch=branch))
        line = LineSegment(((1 if ellipse else 3*branch)*scale, -3*scale), ((1 if ellipse else 3*branch)*scale, 3*scale))
        domains = ((F(1, 4), F(3, 4)) if partial else (0, 1), (0, 1))
        yield 'axis', curve, line, (distance*scale, distance*scale), domains, scale
    for ellipse, branch, angle, distance in itertools.product((False, True), (-1, 1), (0., .3, .7), (-.5, .25, 1.)):
        if ellipse and branch != 1: continue
        curve = (EllipseArc((0, 0), (2, 1), -3., 6., angle) if ellipse else
                 HyperbolaArc((0, 0), (2, 1), -2., 2., branch=branch, rotation_rad=angle))
        x = 0 if ellipse else 3*branch
        yield 'general', curve, LineSegment((x, -3), (x+1, 3)), (distance, distance), ((0, 1), (0, 1)), 1.
    yield 'ellipse-cusp', EllipseArc((0, 0), (2, 1), 0., 3.), LineSegment((-5, -8), (5, 2)), (4., 0.), ((0, 1), (0, 1)), 1.
    yield 'hyperbola-cusp', HyperbolaArc((0, 0), (2, 1), -2., 2.), LineSegment((.5, -2), (4.5, 2)), (-.5, 0.), ((0, 1), (0, 1)), 1.
    yield 'shared-center', EllipseArc((0, 0), (2, 1), -.1, 3.4), LineSegment((2, -2), (2, 2)), (2., 2.), ((0, 1), (0, 1)), 1.
    for ellipse, branch, angle, distance in itertools.product((False, True), (-1, 1), (0., .3), (-.75, .5)):
        if ellipse and branch != 1: continue
        curve = (EllipseArc((1.25, -.5), (1, 2), -3., 6., angle) if ellipse else
                 HyperbolaArc((1.25, -.5), (1, 2), -2., 2., branch=branch, rotation_rad=angle))
        x = 1.25 if ellipse else 1.25+2*branch
        yield 'additional', curve, LineSegment((x, -3.5), (x+1, 2.5)), (distance, .125), ((F(1, 8), F(7, 8)), (-1, 2)), 1.
    yield 'additional', EllipseArc((0, 0), (1, 2), -3., 6.), LineSegment((-3, -2), (3, -2)), (2., 2.), ((0, 1), (0, 1)), 1.


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--family', help='Run only this named case family; omitted means all families')
    args = parser.parse_args(); args.out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic(); records = []
    with localcontext() as context:
        context.prec = 140
        for index, (name, curve, line, distances, domains, scale) in enumerate(cases()):
            if args.family and name != args.family: continue
            expected, groups, intervals = reference(curve, line, distances, domains, scale)
            reverse = index % 2 == 1
            if reverse:
                curve = (replace(curve, start_rad=curve.start_rad+curve.sweep_rad, sweep_rad=-curve.sweep_rad) if isinstance(curve, EllipseArc) else
                         replace(curve, start_parameter=curve.end_parameter, end_parameter=curve.start_parameter))
                line = LineSegment(line.end_zr_m, line.start_zr_m)
                distances = tuple(-x for x in distances)
                domains = tuple((1-b, 1-a) for a, b in domains)
            exchange = index % 3 == 1
            result = classify_line_noncircular_crossings((line, curve) if exchange else (curve, line),
                distances[::-1] if exchange else distances, domains[::-1] if exchange else domains,
                endpoint_width=F(1, 2**100), max_series_terms=96)
            row = dict(index=index, family=name, ellipse=isinstance(curve, EllipseArc), reverse=reverse, exchange=exchange,
                       expected_centers=len(groups), expected_sources=len(expected), centers=result['centers'],
                       sources=len(result['evidence']['intersections']), reference_monotone_intervals=intervals,
                       product_complete=result['complete'])
            try:
                assert result['complete'], result['evidence']['unresolved']
                assert result['centers'] == len(groups)
                assert len(result['evidence']['intersections']) == len(expected)
                for actual in result['evidence']['intersections']:
                    uncertainty = decimal_value(scale)*D('1e-85')
                    matches = [e for e in expected if all(decimal_value(lo)-uncertainty <= x <= decimal_value(hi)+uncertainty
                               for (lo, hi), x in zip(actual['center_box_zr_m'], e['point']))]
                    assert matches
                    assert any(e['kind'] == actual['contact_kind'] for e in matches)
            except AssertionError:
                (args.out/'failure.json').write_text(json.dumps(row, indent=2)+'\n'); raise
            records.append(row)
            if index % 12 == 0:
                print(json.dumps(dict(cases=len(records), seconds=time.monotonic()-start)), flush=True)
    if not records: raise ValueError('no cases match requested family')
    report = dict(passed=True, cases=len(records), family=args.family, seconds=time.monotonic()-start, decimal_precision=140,
                  reference='direct original trigonometric/hyperbolic normal offsets, analytic derivative critical points and monotone bisection',
                  records=records)
    (args.out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'records'}))


if __name__ == '__main__': main()
