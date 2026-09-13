# SPDX-License-Identifier: Apache-2.0
"""Independent original-parameter normal feet for general conic offsets.

Numerical scans are cross-checks, not completeness proofs. Exact multiple and
rank-one examples are covered separately by analytical unittest invariants.
"""
import argparse
from dataclasses import replace
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import json
from pathlib import Path
import time
import numpy as np

from validate_coincident_circle_arcs import fingerprints
from validate_general_coincident_circle_arcs import decimal_value as dec, sine_cosine
from validate_conic_offset_projection import source_scan, source_point
from superfish_ng.conics import EllipseArc, HyperbolaArc, rotation_cos_sin, curve_to_dict
from superfish_ng.conic_offset_intersections import classify_conic_offset_intersections
from superfish_ng.tangent_construction import _json_value


def original_derivatives(curve, parameter):
    a, b = map(dec, curve.semiaxes_m)
    if isinstance(curve, EllipseArc):
        s, c = sine_cosine(parameter)
        local, tangent, second = (a*c, b*s), (-a*s, b*c), (-a*c, -b*s)
    else:
        ex = parameter.exp(); c, s = (ex+1/ex)/2, (ex-1/ex)/2
        local = curve.branch*a*c, b*s
        tangent, second = (curve.branch*a*s, b*c), local
    c, s = map(dec, rotation_cos_sin(curve.rotation_rad))
    def rotate(pair): return c*pair[0]-s*pair[1], s*pair[0]+c*pair[1]
    point = tuple(dec(o)+p for o, p in zip(curve.center_zr_m, rotate(local)))
    return point, rotate(tangent), rotate(second), (local[0]/a, local[1]/b)


def normal_feet(target, center):
    """Locate roots of (center-C(t)) dot C'(t) in the original finite domain."""
    begin, end = ((target.start_rad, target.start_rad+target.sweep_rad) if isinstance(target, EllipseArc)
                  else (target.start_parameter, target.end_parameter))
    scans = []
    for count in (2048, 4096):
        parameters = np.linspace(min(begin, end), max(begin, end), count+1)
        a, b = target.semiaxes_m
        if isinstance(target, EllipseArc):
            s, c = np.sin(parameters), np.cos(parameters)
            x, y, vx, vy = a*c, b*s, -a*s, b*c
        else:
            s, c = np.sinh(parameters), np.cosh(parameters)
            x, y, vx, vy = target.branch*a*c, b*s, target.branch*a*s, b*c
        c, s = rotation_cos_sin(target.rotation_rad)
        px, py = target.center_zr_m[0]+c*x-s*y, target.center_zr_m[1]+s*x+c*y
        values = (float(center[0])-px)*(c*vx-s*vy)+(float(center[1])-py)*(s*vx+c*vy)
        assert np.all(np.isfinite(values)) and np.all(values != 0), 'sampled zero needs an analytical endpoint/multiple-root check'
        scans.append([(D(float(parameters[i])), D(float(parameters[i+1]))) for i in np.flatnonzero(values[:-1]*values[1:] < 0)])
    assert len(scans[0]) == len(scans[1]), 'independent target scan densities disagree'
    def value(t):
        point, tangent, _, _ = original_derivatives(target, t)
        return sum((p-q)*v for p, q, v in zip(center, point, tangent))
    result = []
    for (left, right), (coarse_left, coarse_right) in zip(scans[1], scans[0]):
        assert coarse_left <= left < right <= coarse_right
        low = value(left); assert low*value(right) < 0
        for _ in range(380):
            mid = (left+right)/2; at_mid = value(mid)
            if at_mid == 0: left = right = mid; break
            if low*at_mid > 0: left, low = mid, at_mid
            else: right = mid
            if right-left < D('1e-108'): break
        else: raise AssertionError('independent normal-foot bisection did not converge')
        result.append((left+right)/2)
    return result


def speed_sign(curve, parameter, distance):
    _, v, acceleration, _ = original_derivatives(curve, parameter)
    length = sum(x*x for x in v).sqrt()
    direction = (1 if curve.sweep_rad > 0 else -1) if isinstance(curve, EllipseArc) else (
                 1 if curve.end_parameter > curve.start_parameter else -1)
    speed = 1-direction*dec(distance)*(v[0]*acceleration[1]-v[1]*acceleration[0])/length**3
    assert abs(speed) > D('1e-50'), 'numerical reference cusp needs an analytical check'
    return 1 if speed > 0 else -1


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, required=True); args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False); before = fingerprints(); start = time.monotonic(); rows = []
    (args.out/'input-sha256.json').write_text(json.dumps(before, indent=2)+'\n')
    base = EllipseArc((0, 0), (2, 1), -3., 6.)
    cases = [('symmetric', base, replace(base, semiaxes_m=(1, 2)), .25, .25),
             ('shifted', base, replace(base, semiaxes_m=(1, 2), center_zr_m=(1., .25)), .25, .375),
             ('rotated', replace(base, rotation_rad=.3), replace(base, semiaxes_m=(1, 2), center_zr_m=(1., .25), rotation_rad=.7), .25, .375),
             ('ellipse-hyperbola', base, HyperbolaArc((0, .25), (1, 1.5), -2., 2.), .25, .375),
             ('hyperbola-ellipse', HyperbolaArc((0, 0), (1, 1.5), -2., 2., branch=-1), replace(base, center_zr_m=(-1., 0)), -.25, .375),
             ('hyperbola-hyperbola-disjoint', HyperbolaArc((0, 0), (1, 1.5), -2., 2.), HyperbolaArc((.5, .25), (2, 1), -2., 2., branch=-1), -.25, .375),
             ('hyperbola-hyperbola-crossing', HyperbolaArc((-2, 0), (2, 1), -2., 2.), HyperbolaArc((0, 0), (1, 2), -2., 2.), .25, .25)]
    with localcontext() as context:
        context.prec = 140
        for name, first, target, d, e in cases:
            timing = time.monotonic(); source_parameters = source_scan(first, target, d, e); reference = []; feet_count = 0
            for parameter in source_parameters:
                center = source_point(first, parameter, d)
                for t in normal_feet(target, center):
                    feet_count += 1
                    point = source_point(target, t, e)
                    error = max(abs(p-q) for p, q in zip(center, point))
                    assert error < D('1e-95') or error > D('1e-20'), 'ambiguous independent signed incidence'
                    if error < D('1e-95'):
                        reference.append((parameter, t, center, original_derivatives(target, t)[3]))
            print(name, 'independent', len(source_parameters), 'source candidates;', len(reference), 'signed target pairs', flush=True)
            actual = classify_conic_offset_intersections((first, target), (d, e), ((0, 1), (0, 1)),
                        endpoint_width=F(1, 2**100), max_series_terms=96)
            (args.out/f'{name}-classification.json').write_text(json.dumps(_json_value(actual), indent=2)+'\n')
            assert actual['complete'], (name, actual['evidence']['unresolved'])
            intersections = actual['evidence']['intersections']; matched = []
            assert len(intersections) == len(reference), (name, len(intersections), len(reference))
            for parameter, t, center, local in reference:
                matches = [i for i, row in enumerate(intersections) if all(
                    dec(lo)-D('1e-95') <= p <= dec(hi)+D('1e-95')
                    for (lo, hi), p in zip(row['center_box_zr_m']+row['target_local_box'], center+local))]
                assert len(matches) == 1 and matches[0] not in matched, (name, 'center or recovered target enclosure mismatch')
                matched.extend(matches); row = intersections[matches[0]]
                assert row['source_offset_speed_factor_sign'] == speed_sign(first, parameter, d)
                assert row['target_offset_speed_factor_sign'] == speed_sign(target, t, e)
                v, w = original_derivatives(first, parameter)[1], original_derivatives(target, t)[1]
                assert abs(v[0]*w[1]-v[1]*w[0]) > D('1e-50') and row['contact_kind'] == 'TRANSVERSE'
            row = dict(name=name, source_candidates=len(source_parameters), numerical_normal_feet=feet_count,
                       signed_target_pairs=len(reference), centers=actual['centers'], seconds=time.monotonic()-timing,
                       curves=[curve_to_dict(c) for c in (first, target)], distances=(d, e))
            rows.append(row); print(name, row['seconds'], 'PASS', flush=True)
    after = fingerprints()
    changed = sorted(p for p in set(before)|set(after) if before.get(p) != after.get(p))
    report = dict(status='PASS', seconds=time.monotonic()-start, cases=len(rows),
                  source_candidates=sum(r['source_candidates'] for r in rows),
                  signed_target_pairs=sum(r['signed_target_pairs'] for r in rows),
                  numerical_normal_feet=sum(r['numerical_normal_feet'] for r in rows),
                  source_sha256=before, source_changed_during_run=bool(changed), changed_paths=changed, rows=rows,
                  reference='140-digit original source normals and independent conic/circle matrices; original target angle normal-foot equations; 2048/4096 scans and bisection',
                  scope='generic finite intersections, target feet and speed/contact signs; numerical scans are not completeness proofs; analytical multiple-root, scale, branch, endpoint and identity tests are separate')
    if changed: report['status'] = 'FAILED_SOURCE_FREEZE'
    (args.out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    assert not changed, changed
    print({k: report[k] for k in ('status', 'seconds', 'cases', 'source_candidates', 'signed_target_pairs', 'numerical_normal_feet')})


if __name__ == '__main__': main()
