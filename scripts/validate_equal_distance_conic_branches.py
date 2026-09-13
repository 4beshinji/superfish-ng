# SPDX-License-Identifier: Apache-2.0
"""Independent original-normal branch centers and convex nearest-foot checks."""
import argparse
from dataclasses import replace
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import itertools
import json
import math
from pathlib import Path
import time

from validate_coincident_circle_arcs import fingerprints
from validate_general_coincident_circle_arcs import decimal_value as dec
from validate_conic_offset_projection import source_point
from validate_conic_offset_intersections import original_derivatives, speed_sign
from superfish_ng.conics import EllipseArc, HyperbolaArc, rotation_cos_sin, curve_to_dict
from superfish_ng.equal_distance_conic_branches import classify_equal_distance_conic_branches
from superfish_ng.tangent_construction import _json_value


def reference(first, second, distances, domains):
    """Bisect the original outward-normal offset's transverse-axis crossing."""
    for curve, distance in zip((first, second), distances):
        if curve.branch*distance*(curve.end_parameter-curve.start_parameter) <= 0:
            return []
    c, s = map(dec, rotation_cos_sin(first.rotation_rad)); n = c*c+s*s
    def transverse_equation(parameter):
        point = source_point(first, parameter, distances[0])
        delta = tuple(x-dec(o) for x, o in zip(point, first.center_zr_m))
        return first.branch*(c*delta[0]+s*delta[1])/n
    at_vertex = transverse_equation(D(0))
    if at_vertex > 0: return []
    if at_vertex == 0: parameters = [D(0)]
    else:
        left, right = D(0), D(1)
        while transverse_equation(right) < 0:
            right *= 2
            assert right <= 16, 'independent bracket exceeded its declared range'
        for _ in range(380):
            middle = (left+right)/2
            if transverse_equation(middle) < 0: left = middle
            else: right = middle
            if right-left < D('1e-108'): break
        else: raise AssertionError('independent original-normal bisection did not converge')
        parameters = [-(left+right)/2, (left+right)/2]
    result = []
    for parameter in parameters:
        center = source_point(first, parameter, distances[0])
        _, _, _, local = original_derivatives(first, parameter)
        x, y = -dec(first.semiaxes_m[0])*local[0], dec(first.semiaxes_m[1])*local[1]
        other_point = tuple(dec(o)+v for o, v in zip(first.center_zr_m, (c*x-s*y, s*x+c*y)))
        cs, sn = map(dec, rotation_cos_sin(second.rotation_rad)); norm = cs*cs+sn*sn
        dx, dy = tuple(p-dec(o) for p, o in zip(other_point, second.center_zr_m))
        other_local = (cs*dx+sn*dy)/(norm*dec(second.semiaxes_m[0])), (-sn*dx+cs*dy)/(norm*dec(second.semiaxes_m[1]))
        other_parameter = (other_local[1]+(1+other_local[1]**2).sqrt()).ln()
        assert (other_local[0] > 0) == (second.branch > 0)
        other_center = source_point(second, other_parameter, distances[1])
        tolerance = max(map(dec, first.semiaxes_m))*D('1e-95')
        assert max(abs(p-q) for p, q in zip(center, other_center)) < tolerance
        fractions = [(t-dec(curve.start_parameter))/(dec(curve.end_parameter)-dec(curve.start_parameter))
                     for t, curve in zip((parameter, other_parameter), (first, second))]
        if all(dec(low)-D('1e-95') <= fraction <= dec(high)+D('1e-95') for fraction, (low, high) in zip(fractions, domains)):
            result.append(dict(center=center, local=local, target_local=other_local, parameters=(parameter, other_parameter)))
    return result


def convex_checks():
    checks = 0
    for kind, angle, unit, radius in itertools.product(('ellipse', 'right', 'left'), (0., .3), (2.**-40, 1., 2.**40), (.25, 2., 20.)):
        curve = (EllipseArc((unit, 3*unit), (2*unit, unit), -3., 6., angle) if kind == 'ellipse' else
                 HyperbolaArc((unit, 3*unit), (2*unit, unit), -2., 2., rotation_rad=angle, branch=1 if kind == 'right' else -1))
        distance = dec(radius*unit)
        parameters = (D(-2), D(-1), D(0), D(1), D(2))
        for first_parameter, second_parameter in itertools.permutations(parameters, 2):
            first, tangent, _, _ = original_derivatives(curve, first_parameter)
            second = original_derivatives(curve, second_parameter)[0]
            length = sum(t*t for t in tangent).sqrt()
            normal_sign = -1 if kind == 'ellipse' else curve.branch
            outward = -normal_sign*tangent[1]/length, normal_sign*tangent[0]/length
            delta = tuple(y-x for x, y in zip(first, second))
            dot = sum(x*y for x, y in zip(outward, delta))
            assert dot < 0, 'strict supporting half-plane inequality failed'
            point = tuple(x+distance*v for x, v in zip(first, outward))
            assert sum((x-y)**2 for x, y in zip(point, second)) > distance**2
            checks += 1
    return checks


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, required=True); args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False); before = fingerprints(); started = time.monotonic(); rows = []
    (args.out/'input-sha256.json').write_text(json.dumps(before, indent=2)+'\n')
    with localcontext() as context:
        context.prec = 140
        for axes_index, frame, scale_index, factor, signs in itertools.product(range(4), range(3), range(3), (.5, 1., 1.125, 8.), itertools.product((-1, 1), repeat=2)):
            unit = (2.**-40, 1., 2.**40)[scale_index]; axes = ((2., 1.), (1., 2.), (1., 1.), (3., 2.))[axes_index]
            branch = 1 if axes_index%2 == 0 else -1
            first = HyperbolaArc((unit, 3*unit), tuple(x*unit for x in axes), -2., 2., rotation_rad=.3 if frame == 1 else 0., branch=branch)
            second = replace(first, branch=-branch) if frame != 2 else replace(first, rotation_rad=math.pi)
            if scale_index == 1: first = replace(first, start_parameter=2., end_parameter=-2.)
            if frame == 0: second = replace(second, start_parameter=2., end_parameter=-2.)
            distances = tuple(sign*factor*axes[0]*unit for sign in signs)
            domains = (((0, 1), (0, 1)), ((.5, 1), (0, 1)), ((.5, 1), (0, .5)))[(axes_index+frame+scale_index)%3]
            expected = reference(first, second, distances, domains)
            actual = classify_equal_distance_conic_branches((first, second), distances, domains,
                        endpoint_width=F(1, 2**100), max_series_terms=96)
            assert actual is not None and actual['complete'] and actual['centers'] == len(expected), (axes_index, frame, scale_index, factor, signs)
            matches = []
            for target in expected:
                indices = [i for i, row in enumerate(actual['evidence']['intersections']) if all(
                    dec(low)-D('1e-90')*dec(unit) <= x <= dec(high)+D('1e-90')*dec(unit)
                    for x, (low, high) in zip(target['center'], row['center_box_zr_m']))]
                assert len(indices) == 1 and indices[0] not in matches
                matches.extend(indices); row = actual['evidence']['intersections'][indices[0]]
                for point, boxes in ((target['local'], row['source_local_box']), (target['target_local'], row['target_local_box'])):
                    assert all(dec(low)-D('1e-95') <= x <= dec(high)+D('1e-95') for x, (low, high) in zip(point, boxes))
                assert [speed_sign(c, t, d) for c, t, d in zip((first, second), target['parameters'], distances)] == [1, 1]
                assert row['contact_kind'] == ('REGULAR_TANGENCY' if target['parameters'][0] == 0 else 'TRANSVERSE')
            record = dict(axes_index=axes_index, frame=frame, scale=unit, factor=factor, signs=signs, domains=domains,
                          centers=len(expected), curves=[curve_to_dict(c) for c in (first, second)])
            rows.append(record)
            (args.out/f'case-{len(rows):03d}.json').write_text(json.dumps(_json_value(dict(input=record,classification=actual)),indent=2)+'\n')
        nearest_checks = convex_checks()
    after = fingerprints(); changed = sorted(p for p in set(before)|set(after) if before.get(p) != after.get(p))
    report = dict(status='PASS' if not changed else 'FAILED_SOURCE_FREEZE', seconds=time.monotonic()-started,
                  branch_cases=len(rows), finite_source_pairs=sum(r['centers'] for r in rows), convex_nearest_foot_checks=nearest_checks,
                  source_sha256=before, changed_paths=changed, rows=rows,
                  reference='140-digit original point and unit normal; transverse-axis equation bisection without the product closed-form squared coordinate; reflected original source and inverse target frame; strict convex supporting half-plane and distance inequalities',
                  scope='finite opposite-branch centers, signs, finite fractions, source coordinates and speed/contact kinds; convex sample checks supplement the written uniqueness proof')
    (args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    assert not changed, changed
    print({k:report[k] for k in ('status','seconds','branch_cases','finite_source_pairs','convex_nearest_foot_checks')})


if __name__ == '__main__': main()
