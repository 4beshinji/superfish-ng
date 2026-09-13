# SPDX-License-Identifier: Apache-2.0
"""Independent high-precision Euclidean geometry for algebraic offset diagnoses."""
import argparse
from dataclasses import replace
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import itertools
import json
import math
from pathlib import Path
import time

from validate_coincident_circle_arcs import reference_pi
from validate_general_coincident_circle_arcs import decimal_value, phase_reference
from superfish_ng.conics import EllipseArc, LineSegment, rotation_cos_sin
from superfish_ng.offset_degeneracies import classify_offset_degeneracies


def vector_subtract(a, b): return tuple(x-y for x, y in zip(a, b))
def dot(a, b): return sum(x*y for x, y in zip(a, b))
def cross(a, b): return a[0]*b[1]-a[1]*b[0]


def model(curve, distance):
    if isinstance(curve, EllipseArc):
        c, s = map(decimal_value, rotation_cos_sin(curve.rotation_rad))
        radius = decimal_value(curve.semiaxes_m[0])*(c*c+s*s).sqrt()
        radius -= decimal_value(distance)*(1 if curve.sweep_rad > 0 else -1)
        return dict(center=tuple(map(decimal_value, curve.center_zr_m)), radius=radius, rotation=(c, s))
    start, end = [tuple(map(decimal_value, p)) for p in (curve.start_zr_m, curve.end_zr_m)]
    delta = vector_subtract(end, start)
    length = dot(delta, delta).sqrt()
    offset = decimal_value(distance)/length
    return dict(origin=(start[0]-offset*delta[1], start[1]+offset*delta[0]), delta=delta)


def supporting_points(models, scale):
    circles = ['radius' in m for m in models]
    epsilon = decimal_value(scale)**2*D('1e-110')
    if all(circles):
        a, b = models
        delta = vector_subtract(b['center'], a['center'])
        distance = dot(delta, delta).sqrt()
        radii = abs(a['radius']), abs(b['radius'])
        if distance > sum(radii) or distance < abs(radii[0]-radii[1]): return []
        direction = tuple(v/distance for v in delta)
        along = (radii[0]**2-radii[1]**2+distance**2)/(2*distance)
        height_squared = radii[0]**2-along**2
        assert abs(height_squared) > epsilon, 'independent near-tangency requires a dedicated exact invariant'
        height = height_squared.sqrt()
        base = tuple(x+along*v for x, v in zip(a['center'], direction))
        return [(base[0]-side*height*direction[1], base[1]+side*height*direction[0]) for side in (-1, 1)]
    if any(circles):
        circle, line = (models[0], models[1]) if circles[0] else (models[1], models[0])
        delta = line['delta']; squared = dot(delta, delta)
        projection = dot(vector_subtract(circle['center'], line['origin']), delta)/squared
        base = tuple(x+projection*v for x, v in zip(line['origin'], delta))
        gap = vector_subtract(base, circle['center'])
        height_squared = circle['radius']**2-dot(gap, gap)
        assert abs(height_squared) > epsilon, 'independent near-tangency requires a dedicated exact invariant'
        if height_squared < 0: return []
        amount = (height_squared/squared).sqrt()
        return [tuple(x+side*amount*v for x, v in zip(base, delta)) for side in (-1, 1)]
    a, b = models
    parameter = cross(vector_subtract(b['origin'], a['origin']), b['delta'])/cross(a['delta'], b['delta'])
    return [tuple(x+parameter*v for x, v in zip(a['origin'], a['delta']))]


def contains(curve, model, point, domain, pi):
    if isinstance(curve, LineSegment):
        fraction = dot(vector_subtract(point, model['origin']), model['delta'])/dot(model['delta'], model['delta'])
        low, high = map(decimal_value, domain)
        assert min(abs(fraction-low), abs(fraction-high)) > D('1e-100')
        return low < fraction < high
    delta = vector_subtract(point, model['center']); c, s = model['rotation']
    sign = 1 if model['radius'] > 0 else -1
    x, y = sign*(c*delta[0]+s*delta[1]), sign*(-s*delta[0]+c*delta[1])
    phase = phase_reference(F(x), F(y))
    low, high = sorted(decimal_value(F(curve.start_rad)+F(curve.sweep_rad)*t) for t in domain)
    for period in range(-4, 5):
        angle = phase+2*period*pi
        assert min(abs(angle-low), abs(angle-high)) > D('1e-100')
        if low < angle < high: return True
    return False


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(); args.out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic(); rows = []; counts = {0:0, 1:0, 2:0}
    with localcontext() as context:
        context.prec = 160; pi = reference_pi()
        domains = (((F(0), F(1)), (F(0), F(1))), ((F(1,4), F(3,4)), (F(1,8), F(7,8))))
        cases = itertools.product(('circles', 'line_circle', 'lines'), ((.1,.3),(.3,.7),(.7,1.2)),
                                  (.75, 2.25, 4.5), ((.25,.5),(-.5,.75),(3.,3.5)),
                                  domains, (2.**-160, 1., 2.**160), (False, True))
        for kind, angles, separation, distances, domain, scale, reverse in cases:
            a = EllipseArc((0, 0), (2*scale, 2*scale), -2.7, 5.4, angles[0])
            b = EllipseArc((separation*scale, .375*scale), (1.5*scale, 1.5*scale), -2.2, 4.4, angles[1])
            if kind != 'circles': b = LineSegment((separation*scale, -2*scale), ((separation+1)*scale, 2*scale))
            if kind == 'lines': a = LineSegment((-2*scale, -scale), (2*scale, scale))
            distances = [d*scale for d in distances]
            if reverse:
                b = (replace(b, start_rad=2.2, sweep_rad=-4.4) if isinstance(b, EllipseArc)
                     else LineSegment(b.end_zr_m, b.start_zr_m))
                distances[1] *= -1
            curves = [a, b]; models = [model(c, d) for c, d in zip(curves, distances)]
            points = supporting_points(models, scale)
            expected = [p for p in points if all(contains(c, m, p, bounds, pi) for c, m, bounds in zip(curves, models, domain))]
            for exchange in (False, True):
                actual = classify_offset_degeneracies(*(curves[::-1] if exchange else curves),
                    first_distance_m=distances[1 if exchange else 0], second_distance_m=distances[0 if exchange else 1],
                    first_interval=domain[1 if exchange else 0], second_interval=domain[0 if exchange else 1])
                row = dict(index=len(rows), kind=kind, angles=angles, separation=separation,
                           distances=distances, scale=scale, reverse=reverse, exchange=exchange,
                           domains=[[str(x) for x in pair] for pair in domain],
                           expected=len(expected), observed=actual['finite_center_count'])
                try:
                    assert actual['finite_domain_complete'], actual['reason']
                    assert actual['finite_center_count'] == len(expected)
                    accepted = [p for p in actual['evidence'].get('candidates', []) if p['parameter_pair_in_domain']]
                    for point in expected:
                        uncertainty = decimal_value(scale)*D('1e-110')
                        assert sum(all(decimal_value(lo)-uncertainty <= value <= decimal_value(hi)+uncertainty
                                       for (lo, hi), value in zip(p['center_box_zr_m'], point)) for p in accepted) == 1
                    # Every independent point also satisfies both original support equations.
                    for point in points:
                        for m in models:
                            error = (abs(dot(vector_subtract(point, m['center']), vector_subtract(point, m['center']))-m['radius']**2)
                                     if 'radius' in m else abs(cross(vector_subtract(point, m['origin']), m['delta'])))
                            assert error < decimal_value(scale)**2*D('1e-110')
                except AssertionError:
                    (args.out/'failure.json').write_text(json.dumps(row, indent=2)+'\n')
                    raise
                counts[len(expected)] += 1; rows.append(row)
    report = dict(passed=True, cases=len(rows), counts=counts, seconds=time.monotonic()-start,
                  decimal_precision=160, reference='independent Euclidean distances, directed projection, Newton angles and AGM pi',
                  records=rows)
    (args.out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'records'}))


if __name__ == '__main__': main()
