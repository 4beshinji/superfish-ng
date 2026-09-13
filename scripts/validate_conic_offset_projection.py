# SPDX-License-Identifier: Apache-2.0
"""Independent conic/circle matrices, Sylvester determinants and source scans."""
import argparse
from dataclasses import replace
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import itertools
import json
from pathlib import Path
import time
import numpy as np

from validate_coincident_circle_arcs import fingerprints
from validate_general_coincident_circle_arcs import decimal_value as dec, phase_reference, sine_cosine
from superfish_ng.conics import EllipseArc, HyperbolaArc, rotation_cos_sin, curve_to_dict
from superfish_ng.conic_offset_projection import conic_offset_projection, project_conic_offset_candidates
from superfish_ng.polynomial_roots import _value
from superfish_ng.tangent_construction import _json_value


def determinant(matrix):
    matrix = [list(row) for row in matrix]; result = D(1)
    for i in range(len(matrix)):
        pivot = max(range(i, len(matrix)), key=lambda j: abs(matrix[j][i]))
        if matrix[pivot][i] == 0: return D(0)
        if pivot != i: matrix[i], matrix[pivot] = matrix[pivot], matrix[i]; result = -result
        value = matrix[i][i]; result *= value
        for j in range(i+1, len(matrix)):
            factor = matrix[j][i]/value
            for k in range(i, len(matrix)): matrix[j][k] -= factor*matrix[i][k]
    return result


def source_point(curve, parameter, distance):
    a, b = map(dec, curve.semiaxes_m)
    if isinstance(curve, EllipseArc):
        s, c = sine_cosine(parameter); local = a*c, b*s; tangent = -a*s, b*c
        direction = 1 if curve.sweep_rad > 0 else -1
    else:
        ex = parameter.exp(); c, s = (ex+1/ex)/2, (ex-1/ex)/2
        local = curve.branch*a*c, b*s; tangent = curve.branch*a*s, b*c
        direction = 1 if curve.end_parameter > curve.start_parameter else -1
    c, s = map(dec, rotation_cos_sin(curve.rotation_rad))
    x, y = local; vx, vy = tangent; vx, vy = c*vx-s*vy, s*vx+c*vy
    length = (vx*vx+vy*vy).sqrt(); d = direction*dec(distance)
    return (dec(curve.center_zr_m[0])+c*x-s*y-d*vy/length,
            dec(curve.center_zr_m[1])+s*x+c*y+d*vx/length)


def pencil_discriminant(point, target, distance):
    """Build 3x3 matrices, interpolate their cubic determinant, then use a 5x5 resultant."""
    a, b = map(dec, target.semiaxes_m); epsilon = 1 if isinstance(target, EllipseArc) else -1
    c, s = map(dec, rotation_cos_sin(target.rotation_rad)); n = c*c+s*s
    x, y = (p-dec(center) for p, center in zip(point, target.center_zr_m))
    x, y = (c*x+s*y)/n, (-s*x+c*y)/n
    Q = ((1/(a*a), D(0), D(0)), (D(0), epsilon/(b*b), D(0)), (D(0), D(0), D(-1)))
    C = ((n, D(0), -n*x), (D(0), n, -n*y), (-n*x, -n*y, n*(x*x+y*y)-dec(distance)**2))
    step = 1/max(a, b)**2
    values = [a*a*b*b*determinant([[Q[i][j]+k*step*C[i][j] for j in range(3)] for i in range(3)])
              for k in (0, 1, -1, 2)]
    c0, f1, fm1, f2 = values; c2 = (f1+fm1-2*c0)/2; odd = (f1-fm1)/2
    c3 = (f2-c0-4*c2-2*odd)/6; c1 = odd-c3
    matrix = ((c3, c2, c1, c0, D(0)), (D(0), c3, c2, c1, c0),
              (3*c3, 2*c2, c1, D(0), D(0)), (D(0), 3*c3, 2*c2, c1, D(0)),
              (D(0), D(0), 3*c3, 2*c2, c1))
    return -determinant(matrix)/c3, step


def float_discriminants(first, second, d, e, parameters):
    a, b = first.semiaxes_m
    if isinstance(first, EllipseArc):
        s, c = np.sin(parameters), np.cos(parameters); x, y = a*c, b*s; vx, vy = -a*s, b*c
        direction = 1 if first.sweep_rad > 0 else -1
    else:
        s, c = np.sinh(parameters), np.cosh(parameters); x, y = first.branch*a*c, b*s; vx, vy = first.branch*a*s, b*c
        direction = 1 if first.end_parameter > first.start_parameter else -1
    c, s = rotation_cos_sin(first.rotation_rad); vx, vy = c*vx-s*vy, s*vx+c*vy; length = np.hypot(vx, vy)
    x, y = first.center_zr_m[0]+c*x-s*y-direction*d*vy/length, first.center_zr_m[1]+s*x+c*y+direction*d*vx/length
    a, b = second.semiaxes_m; c, s = rotation_cos_sin(second.rotation_rad); n = c*c+s*s
    x, y = x-second.center_zr_m[0], y-second.center_zr_m[1]; x, y = (c*x+s*y)/n, (-s*x+c*y)/n
    Q = np.diag([1/(a*a), (1 if isinstance(second, EllipseArc) else -1)/(b*b), -1.])
    C = np.zeros((len(parameters), 3, 3)); C[:, 0, 0] = C[:, 1, 1] = n
    C[:, 0, 2] = C[:, 2, 0] = -n*x; C[:, 1, 2] = C[:, 2, 1] = -n*y
    C[:, 2, 2] = n*(x*x+y*y)-e*e
    values = np.linalg.det(Q+np.array([0., 1., -1., 2.])[None, :, None, None]*C[:, None, :, :]/max(a, b)**2)*a*a*b*b
    c0, f1, fm1, f2 = values.T; c2 = (f1+fm1-2*c0)/2; odd = (f1-fm1)/2
    c3 = (f2-c0-4*c2-2*odd)/6; c1 = odd-c3
    matrix = np.zeros((len(parameters), 5, 5))
    for shift in (0, 1): matrix[:, shift, shift:shift+4] = np.array([c3, c2, c1, c0]).T
    for shift in (0, 1, 2): matrix[:, shift+2, shift:shift+3] = np.array([3*c3, 2*c2, c1]).T
    return -np.linalg.det(matrix)/c3


def source_scan(first, second, d, e):
    begin, end = ((first.start_rad, first.start_rad+first.sweep_rad) if isinstance(first, EllipseArc)
                  else (first.start_parameter, first.end_parameter))
    scans = []
    for count in (2048, 4096):
        parameters = np.linspace(min(begin, end), max(begin, end), count+1)
        values = float_discriminants(first, second, d, e, parameters)
        assert np.all(np.isfinite(values)) and np.all(values != 0), 'reference sampled zero needs a separate multiple-root check'
        scans.append([(D(float(parameters[i])), D(float(parameters[i+1]))) for i in np.flatnonzero(values[:-1]*values[1:] < 0)])
    assert len(scans[0]) == len(scans[1]), 'independent sample densities disagree'
    def value(t): return pencil_discriminant(source_point(first, t, d), second, e)[0]
    result = []
    for (a, b), (coarse_a, coarse_b) in zip(scans[1], scans[0]):
        assert coarse_a <= a < b <= coarse_b
        left, right = value(a), value(b); assert left*right < 0
        for _ in range(380):
            middle = (a+b)/2; f = value(middle)
            if f == 0: a = b = middle; break
            if left*f > 0: a, left = middle, f
            else: b, right = middle, f
            if b-a < D('1e-108'): break
        else: raise AssertionError('independent matrix-root bisection did not converge')
        result.append((a+b)/2)
    return result


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, required=True); args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False); before = fingerprints(); start = time.monotonic()
    matrix_rows = []; root_rows = []
    with localcontext() as context:
        context.prec = 140
        for first_kind, second_kind, rotated, variant in itertools.product(('ellipse', 'hyperbola'), ('ellipse', 'hyperbola'), (False, True), range(4)):
            unit = (1., 2.**-40, 2.**40, 1.)[variant]; angle, other = (.3, .7) if rotated else (0., 0.)
            first = (EllipseArc((0, 0), (2*unit, unit), -3., 6., angle) if first_kind == 'ellipse' else
                     HyperbolaArc((0, 0), (2*unit, unit), -2., 2., rotation_rad=angle, branch=-1))
            second = (EllipseArc((unit, .25*unit), (unit, 2*unit), -3., 6., other) if second_kind == 'ellipse' else
                      HyperbolaArc((unit, .25*unit), (unit, 2*unit), -2., 2., rotation_rad=other, branch=1))
            d, e = .25*unit, .375*unit
            if variant == 1:
                first = (replace(first, start_rad=3., sweep_rad=-6.) if isinstance(first, EllipseArc) else
                         replace(first, start_parameter=2., end_parameter=-2.)); d = -d
            elif variant == 2: first, second, d, e = second, first, e, d
            elif variant == 3: d = -d
            for side in ((1, -1) if isinstance(first, EllipseArc) else (first.branch,)):
                projection = conic_offset_projection(first, second, first_distance_m=d, second_distance_m=e, side=side)
                for q in (F(-3, 4), F(-1, 2), F(-1, 4), F(0), F(1, 4), F(1, 2), F(3, 4)):
                    parameter = (phase_reference(side*(1-q*q), 2*q) if isinstance(first, EllipseArc) else
                                 ((1+dec(q))/(1-dec(q))).ln())
                    expected, step = pencil_discriminant(source_point(first, parameter, d), second, e)
                    s = dec(_value(projection['source_chart']['S'], q)).sqrt()
                    a, b = (dec(_value(projection[key], q)) for key in ('discriminant_rational', 'discriminant_radical'))
                    factor = F(1)
                    for row in projection['removed_positive_factors']: factor *= _value(row['polynomial'], q)**row['power']
                    observed = dec(factor)*(a+b*s)/dec(_value(projection['positive_denominator'], q))**4*step**6
                    error = abs(observed-expected)/max(D(1), abs(expected))
                    row = dict(first_kind=first_kind, second_kind=second_kind, rotated=rotated, variant=variant, side=side,
                               q=str(q), degree=projection['degree'], relative_matrix_error=str(error))
                    matrix_rows.append(row)
                    if error >= D('1e-100'):
                        (args.out/'matrix-failure.json').write_text(json.dumps(row, indent=2)+'\n')
                        raise AssertionError('independent matrix discriminant identity failed')
        first = EllipseArc((0, 0), (2, 1), -3., 6.)
        cases = [('symmetric', first, replace(first, semiaxes_m=(1, 2)), .25, .25),
                 ('shifted', first, replace(first, semiaxes_m=(1, 2), center_zr_m=(1., .25)), .25, .375),
                 ('rotated', replace(first, rotation_rad=.3), replace(first, semiaxes_m=(1, 2), center_zr_m=(1., .25), rotation_rad=.7), .25, .375),
                 ('ellipse-hyperbola', first, HyperbolaArc((0, .25), (1, 1.5), -2., 2.), .25, .375),
                 ('hyperbola-ellipse', HyperbolaArc((0, 0), (1, 1.5), -2., 2., branch=-1), replace(first, center_zr_m=(-1., 0)), -.25, .375),
                 ('hyperbola-hyperbola', HyperbolaArc((0, 0), (1, 1.5), -2., 2.), HyperbolaArc((.5, .25), (2, 1), -2., 2., branch=-1), -.25, .375)]
        for name, first, second, d, e in cases:
            timing = time.monotonic(); reference = source_scan(first, second, d, e)
            print(name, 'independent source roots', len(reference), flush=True)
            actual = project_conic_offset_candidates(first, second, first_distance_m=d, second_distance_m=e)
            (args.out/f'{name}-projection.json').write_text(json.dumps(_json_value(actual), indent=2)+'\n')
            assert actual['projection_complete'] and not actual['target_incidence_certified']
            assert len(actual['source_candidates']) == len(reference), (name, len(actual['source_candidates']), len(reference))
            matched = []
            for parameter in reference:
                point = source_point(first, parameter, d)
                matches = [i for i, row in enumerate(actual['source_candidates']) if all(
                    dec(lo)-D('1e-100') <= p <= dec(hi)+D('1e-100') for (lo, hi), p in zip(row['center_box_zr_m'], point))]
                assert len(matches) == 1 and matches[0] not in matched, (name, 'independent source center enclosure mismatch')
                matched.extend(matches)
            row = dict(name=name, source_candidates=len(reference), seconds=time.monotonic()-timing,
                       curves=[curve_to_dict(c) for c in (first, second)], distances=(d, e),
                       projection_degrees=[c['degree'] for c in actual['charts']], target_incidence_certified=False)
            root_rows.append(row); print(row['name'], row['seconds'], 'PASS', flush=True)
    assert fingerprints() == before
    report = dict(status='PASS', seconds=time.monotonic()-start, matrix_checks=len(matrix_rows), root_cases=len(root_rows),
                  source_candidates=sum(row['source_candidates'] for row in root_rows), source_sha256=before,
                  source_changed_during_run=False, maximum_relative_matrix_error=max((row['relative_matrix_error'] for row in matrix_rows), key=D),
                  reference='140-digit original source point/unit normal; independently assembled 3x3 conic/circle pencils and 5x5 Sylvester determinants; 2048/4096 source-parameter scans and bisection',
                  scope='necessary source projection only; numerical reference scans are not completeness proofs and target signed incidence/finite membership are not certified',
                  matrices=matrix_rows, roots=root_rows)
    (args.out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print({key: report[key] for key in ('status', 'seconds', 'matrix_checks', 'root_cases', 'source_candidates')})


if __name__ == '__main__': main()
