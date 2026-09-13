# SPDX-License-Identifier: Apache-2.0
"""Known Pythagorean intersections with an independent Decimal angle oracle.

Generate supports through (0,+/-4); do not solve the implementation's radical
axis equation to obtain expected intersections. No solver or legacy assets.
"""
import argparse
from dataclasses import replace
from decimal import localcontext
from fractions import Fraction as F
import itertools
import json
import math
from pathlib import Path
import time

from validate_coincident_circle_arcs import reference_pi
from validate_general_coincident_circle_arcs import decimal_value, phase_reference
from superfish_ng.conics import EllipseArc, LineSegment
from superfish_ng.offset_degeneracies import classify_offset_degeneracies


def arc_contains(curve, vector, domain, pi):
    phase = phase_reference(*map(F, vector))
    ends = sorted(F(curve.start_rad) + F(curve.sweep_rad)*t for t in domain)
    low, high = map(decimal_value, ends)
    for period in range(-4, 5):
        angle = phase + 2*period*pi
        assert min(abs(angle-low), abs(angle-high)) > decimal_value(F(1, 10**90))
        if low < angle < high:
            return True
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    rows = []
    counts = {0: 0, 1: 0, 2: 0}
    # Each (horizontal leg, radius) satisfies leg^2 + 4^2 = radius^2.
    triangles = ((0., 4.), (3., 5.), (7.5, 8.5))
    arcs = ((-3., 6.), (0., 3.), (-2., 1.))
    domains = (((F(0), F(1)), (F(0), F(1))),
               ((F(1,4), F(3,4)), (F(1,8), F(7,8))))
    with localcontext() as context:
        context.prec = 120
        pi = reference_pi()
        cases = itertools.product(('circles', 'line_circle'), triangles, triangles,
                                  arcs, domains, (2.**-200, 1., 2.**200),
                                  (False, True), (False, True), (False, True))
        for kind, first, second, arc, domain, scale, quarter, reverse, negative in cases:
            if kind == 'circles' and first[0] == second[0] == 0:
                continue
            def point(z, r):
                z, r = (-r, z) if quarter else (z, r)
                return ((11+z)*scale, (13+r)*scale)
            rotation = math.pi/2 if quarter else 0.
            sign = -1 if negative else 1
            a = EllipseArc(point(-first[0], 0), ((first[1]+.5)*scale,)*2, *arc, rotation)
            b = EllipseArc(point(second[0], 0), ((second[1]+.5)*scale,)*2, -3., 6., rotation)
            distance = [(.5 if not negative else 2*first[1]+.5)*scale,
                        (.5 if not negative else 2*second[1]+.5)*scale]
            curves = [a, b]
            if kind == 'line_circle':
                curves[1] = LineSegment(point(.5, -6), point(.5, 6))
                distance[1] = .5*scale
            if reverse:
                b = curves[1]
                curves[1] = (replace(b, start_rad=3., sweep_rad=-6.) if isinstance(b, EllipseArc)
                             else LineSegment(b.end_zr_m, b.start_zr_m))
                distance[1] *= -1
            expected = []
            for y in (-4, 4):
                first_in = arc_contains(curves[0], (sign*first[0], sign*y), domain[0], pi)
                if kind == 'circles':
                    second_in = arc_contains(curves[1], (-sign*second[0], sign*y), domain[1], pi)
                else:
                    fraction = F(6-y if reverse else y+6, 12)
                    second_in = domain[1][0] <= fraction <= domain[1][1]
                if first_in and second_in:
                    expected.append(tuple(map(F, point(0, y))))
            for exchange in (False, True):
                result = classify_offset_degeneracies(*(curves[::-1] if exchange else curves),
                    first_distance_m=distance[1 if exchange else 0], second_distance_m=distance[0 if exchange else 1],
                    first_interval=domain[1 if exchange else 0], second_interval=domain[0 if exchange else 1])
                row = dict(index=len(rows), kind=kind, first=first, second=second, arc=arc,
                           domain=[[str(x) for x in pair] for pair in domain], scale=scale,
                           quarter=quarter, reverse=reverse, negative=negative, exchange=exchange,
                           expected=len(expected), observed=result['finite_center_count'])
                try:
                    assert result['finite_domain_complete'], result['reason']
                    assert result['finite_center_count'] == len(expected)
                    actual = [item for item in result['evidence']['candidates'] if item['parameter_pair_in_domain']]
                    for p in expected:
                        assert sum(all(lo <= value <= hi for (lo, hi), value in zip(item['center_box_zr_m'], p))
                                   for item in actual) == 1
                except AssertionError:
                    (args.out/'failure.json').write_text(json.dumps(row, indent=2)+'\n')
                    raise
                counts[len(expected)] += 1
                rows.append(row)
    report = dict(passed=True, cases=len(rows), center_count_distribution=counts,
                  elapsed_seconds=time.monotonic()-start, decimal_precision=120,
                  reference='constructed Pythagorean intersections; independent Newton angle and AGM pi',
                  records=rows)
    (args.out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({key: value for key, value in report.items() if key != 'records'}))


if __name__ == '__main__':
    main()
