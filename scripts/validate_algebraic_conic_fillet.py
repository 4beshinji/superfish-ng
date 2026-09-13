# SPDX-License-Identifier: Apache-2.0
"""Independent source pairs, output geometry bounds, and constructed FEM scaling."""
import argparse
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import time
import numpy as np
from validate_line_noncircular_crossings import reference
from validate_general_coincident_circle_arcs import decimal_value, phase_reference, sine_cosine, reference_pi
from superfish_ng.conics import EllipseArc, HyperbolaArc, LineSegment, curve_from_dict
from superfish_ng.algebraic_conic_fillet import algebraic_conic_fillet_candidates


ROOT = Path(__file__).resolve().parents[1]


def evaluate(curve, fraction):
    f = decimal_value(fraction)
    if isinstance(curve, LineSegment):
        p, q = [tuple(map(decimal_value, x)) for x in (curve.start_zr_m, curve.end_zr_m)]
        tangent = tuple(b-a for a, b in zip(p, q))
        return tuple(a+f*d for a, d in zip(p, tangent)), tangent
    cardinal = {0.: (1, 0), math.pi/2: (0, 1), -math.pi/2: (0, -1), math.pi: (-1, 0), -math.pi: (-1, 0)}
    c, s = map(decimal_value, cardinal.get(curve.rotation_rad, (math.cos(curve.rotation_rad), math.sin(curve.rotation_rad))))
    a, b = map(decimal_value, curve.semiaxes_m)
    if isinstance(curve, EllipseArc):
        span = decimal_value(curve.sweep_rad); t = decimal_value(curve.start_rad)+span*f
        sn, cs = sine_cosine(t); x, y, dx, dy = a*cs, b*sn, -a*sn, b*cs
    else:
        span = decimal_value(curve.end_parameter)-decimal_value(curve.start_parameter)
        t = decimal_value(curve.start_parameter)+span*f; sn, cs = (t.exp()-(-t).exp())/2, (t.exp()+(-t).exp())/2
        x, y, dx, dy = curve.branch*a*cs, b*sn, curve.branch*a*sn, b*cs
    z, r = map(decimal_value, curve.center_zr_m)
    return (z+c*x-s*y, r+s*x+c*y), (span*(c*dx-s*dy), span*(s*dx+c*dy))


def rescale(curve, factor):
    if isinstance(curve, LineSegment):
        return LineSegment(tuple(factor*x for x in curve.start_zr_m), tuple(factor*x for x in curve.end_zr_m))
    return replace(curve, center_zr_m=tuple(factor*x for x in curve.center_zr_m), semiaxes_m=tuple(factor*x for x in curve.semiaxes_m))


def reverse(curve):
    if isinstance(curve, LineSegment): return LineSegment(curve.end_zr_m, curve.start_zr_m)
    if isinstance(curve, EllipseArc): return replace(curve, start_rad=curve.start_rad+curve.sweep_rad, sweep_rad=-curve.sweep_rad)
    return replace(curve, start_parameter=curve.end_parameter, end_parameter=curve.start_parameter)


def families():
    yield 'endpoint-two', LineSegment((-1.125, -4.375), (4.875, 3.625)), EllipseArc((0, 0), (2, 1), 0., 1.), .625
    yield 'endpoint-one', LineSegment((-1.125, -4.375), (4.875, 3.625)), EllipseArc((0, 0), (2, 1.5), 0., 1.), .625
    yield 'cusp', LineSegment((1.75, -4.75), (7.75, 3.25)), EllipseArc((0, 0), (5, 2.5), -.5, 1.), 1.25
    yield 'shared-center', LineSegment((2, -2), (2, 2)), EllipseArc((0, 0), (2, 1), -.1, 3.4), 2.
    for distance in (-.5, .25, 1.):
        yield 'rotated-ellipse', LineSegment((0, -3), (1, 3)), EllipseArc((0, 0), (2, 1), -3., 6., .3), distance
    for branch in (-1, 1):
        yield 'rotated-hyperbola', LineSegment((3*branch, -3), (3*branch+1, 3)), HyperbolaArc((0, 0), (2, 1), -2., 2., branch=branch, rotation_rad=.3), -.5*branch


def geometry_checks():
    records = []; pi = reference_pi()
    for index, (name, line, arc, distance) in enumerate(families()):
        for variant in range(4):
            unit = (2.**-40, 1., 2.**40, 1.)[variant]
            a, l = rescale(arc, unit), rescale(line, unit); d = distance*unit
            if variant == 1:
                a, l, d = reverse(a), reverse(l), -d
            line_first = variant % 2 == 0
            expected, groups, _ = reference(a, l, (d, d), ((0, 1), (0, 1)), unit)
            start = decimal_value(a.start_rad if isinstance(a, EllipseArc) else a.start_parameter)
            span = decimal_value(a.sweep_rad) if isinstance(a, EllipseArc) else decimal_value(a.end_parameter)-start
            origin, tangent = evaluate(l, 0); squared = sum(x*x for x in tangent); length = squared.sqrt()
            for row in expected:
                center = row['point']; af = (row['parameter']-start)/span
                lf = sum(t*(x-p) for t, x, p in zip(tangent, center, origin))/squared
                arc_point = evaluate(a, F(af))[0]; line_point = evaluate(l, F(lf))[0]
                row['fractions'] = (lf, af) if line_first else (af, lf)
                row['contacts'] = (line_point, arc_point) if line_first else (arc_point, line_point)
            # Reference self-contact grouping precedes lexicographic ordering:
            # numerical noise in two evaluations of one center is not an order.
            line_coordinate = 0 if line_first else 1
            for group in groups:
                common = sum(expected[i]['fractions'][line_coordinate] for i in group)/len(group)
                for i in group:
                    fractions = list(expected[i]['fractions']); fractions[line_coordinate] = common
                    expected[i]['fractions'] = tuple(fractions)
            expected.sort(key=lambda r: r['fractions'])
            settings = dict(radius_m=abs(d), turn_direction=1 if d > 0 else -1, max_sweep_rad=4.5,
                            position_tolerance_m=1e-9*unit, angle_tolerance_rad=1e-8)
            curves = (l, a) if line_first else (a, l)
            result = algebraic_conic_fillet_candidates(*curves, **settings)
            assert result['status'] == 'PASS', result['unresolved']
            assert len(result['candidates']) == len(expected)
            counts = {}; tolerance = decimal_value(unit)*D('1e-85')
            for actual, target in zip(result['candidates'], expected):
                for bounds, f in zip(actual['root']['parameter_box'], target['fractions']):
                    assert decimal_value(bounds[0])-D('1e-85') <= f <= decimal_value(bounds[1])+D('1e-85')
                state = actual['connection_direction']; counts[state] = counts.get(state, 0)+1
                p, q = target['contacts']; center = target['point']
                zero = max(abs(x-y) for x, y in zip(p, q)) < tolerance
                empty = target['fractions'][0] < D('1e-85') or target['fractions'][1] > 1-D('1e-85')
                if zero:
                    assert state == 'ZERO_LENGTH'; continue
                phases = [phase_reference(F(x[0]-center[0]), F(x[1]-center[1])) for x in (p, q)]
                sweep = settings['turn_direction']*(phases[1]-phases[0])
                while sweep <= 0: sweep += 2*pi
                while sweep > 2*pi: sweep -= 2*pi
                if empty:
                    assert state != 'FORWARD'; continue
                if sweep > decimal_value(settings['max_sweep_rad']):
                    assert state == 'SWEEP_LIMIT'; continue
                assert state == 'FORWARD', actual.get('construction_reason')
                output = [curve_from_dict(r) for r in actual['trimmed_curves']]
                assert output[1].semiaxes_m == (abs(d), abs(d))
                for target_point, trimmed, fillet_fraction, endpoint, trim_bound, fillet_bound in zip(
                        (p, q), (output[0], output[2]), (0, 1), (1, 0),
                        actual['trim_contact_error_bounds_m'], actual['fillet_contact_error_bounds_m']):
                    for actual_point, bound in ((evaluate(trimmed, endpoint)[0], trim_bound), (evaluate(output[1], fillet_fraction)[0], fillet_bound)):
                        error = sum((x-y)**2 for x, y in zip(actual_point, target_point)).sqrt()
                        assert error <= decimal_value(bound)+tolerance
                        assert bound <= settings['position_tolerance_m']
                for left, right in zip(output, output[1:]):
                    u, v = evaluate(left, 1)[1], evaluate(right, 0)[1]
                    angle = abs(phase_reference(F(sum(x*y for x, y in zip(u, v))), F(u[0]*v[1]-u[1]*v[0])))
                    assert angle <= decimal_value(settings['angle_tolerance_rad'])
            records.append(dict(family=name, variant=variant, scale=unit, source_pairs=len(expected), centers=len(groups), states=counts))
            print(json.dumps(dict(geometry_cases=len(records), family=name)), flush=True)
    return records


def fem_checks(out):
    from superfish_ng.tangent_construction import construct_tangent_case
    from superfish_ng.config import Case
    from superfish_ng.solver import solve
    from superfish_ng.rf import quantities
    request = json.loads((ROOT/'examples/construction/algebraic_endpoint_fillet_request.json').read_text())
    results = []; reports = []
    for scale_factor in (1., 2.):
        r = deepcopy(request)
        for curve in r['case_template']['geometry']['curves']:
            for key in ('start_zr_m', 'end_zr_m', 'center_zr_m', 'semiaxes_m'):
                if key in curve: curve[key] = [x*scale_factor for x in curve[key]]
        for key in ('join_tolerance_m', 'minimum_gap_m', 'chord_tolerance_m'):
            r['case_template']['geometry'][key] *= scale_factor
        r['case_template']['mesh']['contour_mesh']['max_edge_m'] *= scale_factor
        for key in ('radius_m', 'position_tolerance_m'): r['controls'][key] *= scale_factor
        document = construct_tangent_case(r, candidate_index=0); case = Case.from_dict(document['case'])
        solution = solve(case); rf = quantities(case, solution)
        (out/f'constructed-{int(scale_factor)}.json').write_text(json.dumps(document, indent=2)+'\n')
        (out/f'rf-{int(scale_factor)}.json').write_text(json.dumps(rf, indent=2)+'\n')
        results.append(solution); reports.append(rf)
    first, second = results
    np.testing.assert_allclose(second.space.geometry.points_rz_m, 2*first.space.geometry.points_rz_m, rtol=1e-13, atol=1e-15)
    np.testing.assert_array_equal(second.space.geometry.cell_nodes, first.space.geometry.cell_nodes)
    assert first.u.shape == second.u.shape
    correlation = abs(np.dot(first.u[:, 0], second.u[:, 0]))/(np.linalg.norm(first.u[:, 0])*np.linalg.norm(second.u[:, 0]))
    assert 1-correlation < 1e-10
    ratios = {key: reports[1][key]/reports[0][key] for key in ('frequency_hz', 'r_over_q_accelerator_ohm', 'r_over_q_circuit_ohm', 'geometry_factor_ohm', 'transit_time_factor_abs')}
    assert abs(ratios['frequency_hz']-.5) < 1e-10
    assert all(abs(value-1) < 1e-9 for key, value in ratios.items() if key != 'frequency_hz')
    np.savez(out/'field-shape-scaling.npz', first=first.u, second=second.u,
             first_points=first.space.geometry.points_rz_m, second_points=second.space.geometry.points_rz_m,
             cell_nodes=first.space.geometry.cell_nodes)
    return dict(ratios=ratios, coefficient_shape_correlation=float(correlation), nodes=len(first.space.geometry.points_rz_m), scope='same constructed synthetic geometry at scales 1 and 2; invariant checks, not discretization-error bounds')


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--only', choices=('geometry', 'fem', 'all'), default='all')
    args = parser.parse_args(); args.out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    def hashes():
        return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'src').rglob('*'))
                if p.is_file() and p.suffix in ('.py', '.js', '.html', '.css')}
    before = hashes()
    geometry = []
    if args.only != 'fem':
        with localcontext() as context:
            context.prec = 140
            geometry = geometry_checks()
        (args.out/'geometry-report.json').write_text(json.dumps(dict(passed=True, geometry=geometry, source_sha256=before), indent=2)+'\n')
    fem = fem_checks(args.out) if args.only != 'geometry' else None
    assert hashes() == before
    report = dict(passed=True, seconds=time.monotonic()-start, selection=args.only, geometry_cases=len(geometry), source_pairs=sum(r['source_pairs'] for r in geometry),
                  decimal_precision=140, geometry=geometry, fem_scaling=fem, source_sha256=before, source_changed_during_run=False)
    (args.out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ('passed', 'seconds', 'geometry_cases', 'source_pairs')}))


if __name__ == '__main__': main()
