# SPDX-License-Identifier: Apache-2.0
"""Independent original-normal fillet contacts, output bounds and real FEM scaling.

Generic scans cross-check finite roots; they do not prove completeness. Exact
multiple-source and cusp families use separate physical invariants.
"""
import argparse
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import json
import math
from pathlib import Path
import time
import numpy as np

from validate_algebraic_conic_fillet import evaluate, rescale, reverse
from validate_coincident_circle_arcs import fingerprints
from validate_conic_offset_projection import source_scan, source_point
from validate_conic_offset_intersections import normal_feet
from validate_equal_distance_conic_branches import reference as branch_reference
from validate_general_coincident_circle_arcs import decimal_value as dec, phase_reference, reference_pi
from superfish_ng.conics import EllipseArc, HyperbolaArc, curve_from_dict, curve_to_dict, rotation_cos_sin
from superfish_ng.noncircular_conic_fillet import noncircular_conic_fillet_candidates
from superfish_ng.tangent_construction import _json_value

ROOT = Path(__file__).resolve().parents[1]


def parameters(curve):
    start = dec(curve.start_rad if isinstance(curve, EllipseArc) else curve.start_parameter)
    span = dec(curve.sweep_rad) if isinstance(curve, EllipseArc) else dec(curve.end_parameter)-start
    return start, span


def pair(curves, values, distance):
    fractions = tuple((t-start)/span for curve, t in zip(curves, values) for start, span in (parameters(curve),))
    contacts = tuple(evaluate(curve, F(f))[0] for curve, f in zip(curves, fractions))
    centers = [source_point(curve, t, distance) for curve, t in zip(curves, values)]
    assert max(abs(x-y) for x, y in zip(*centers)) < abs(dec(distance))*D('1e-95')
    return dict(fractions=fractions, contacts=contacts, center=centers[0])


def reflected_pair(first, second, distance):
    """Bisect one finite half-branch's original normal, then reflect its foot."""
    c, s = map(dec, rotation_cos_sin(first.rotation_rad)); n = c*c+s*s
    def local_y(t):
        p = source_point(first, t, distance)
        x, y = (x-dec(o) for x, o in zip(p, first.center_zr_m))
        return (-s*x+c*y)/n
    start, span = parameters(first); left, right = sorted((start, start+span)); low = local_y(left)
    assert low*local_y(right) < 0
    for _ in range(380):
        mid = (left+right)/2; value = local_y(mid)
        if value == 0: left = right = mid; break
        if low*value > 0: left, low = mid, value
        else: right = mid
        if right-left < D('1e-108'): break
    else: raise AssertionError('independent reflection bisection did not converge')
    t = (left+right)/2
    point = evaluate(first, F((t-start)/span))[0]
    x, y = (x-dec(o) for x, o in zip(point, first.center_zr_m)); x, y = (c*x+s*y)/n, -(-s*x+c*y)/n
    point = tuple(dec(o)+v for o, v in zip(first.center_zr_m, (c*x-s*y, s*x+c*y)))
    c, s = map(dec, rotation_cos_sin(second.rotation_rad)); n = c*c+s*s
    x, y = (x-dec(o) for x, o in zip(point, second.center_zr_m))
    x, y = (c*x+s*y)/(n*dec(second.semiaxes_m[0])), (-s*x+c*y)/(n*dec(second.semiaxes_m[1]))
    if isinstance(second, EllipseArc): other = phase_reference(F(x), F(y))
    else:
        assert (x > 0) == (second.branch > 0)
        other = (y+(1+y*y).sqrt()).ln()
    return pair((first, second), (t, other), distance)


def check_output(curves, distance, expected, out, name, *, subset=False):
    unit = max(abs(dec(distance)), D('1e-100')); tolerance = unit*D('1e-85'); pi = reference_pi()
    settings = dict(radius_m=abs(distance), turn_direction=1 if distance > 0 else -1,
                    max_sweep_rad=5.9, position_tolerance_m=float(unit)*1e-9, angle_tolerance_rad=1e-8)
    actual = noncircular_conic_fillet_candidates(*curves, **settings)
    (out/f'{name}.json').write_text(json.dumps(_json_value(dict(curves=[curve_to_dict(c) for c in curves],
        controls=settings, enumeration=actual)), indent=2)+'\n')
    assert actual['status'] == 'PASS', (name, actual['unresolved'])
    expected.sort(key=lambda r:r['fractions']); candidates = actual['candidates']
    if not subset: assert len(candidates) == len(expected), (name, len(candidates), len(expected))
    states = {}; matches = []
    for target in expected:
        found = [i for i, row in enumerate(candidates) if all(dec(lo)-D('1e-85') <= f <= dec(hi)+D('1e-85')
                 for (lo, hi), f in zip(row['root']['parameter_box'], target['fractions']))]
        assert len(found) == 1 and found[0] not in matches, (name, 'original fraction match', found)
        matches.extend(found); row = candidates[found[0]]; center = target['center']; p, q = target['contacts']
        assert all(dec(lo)-tolerance <= v <= dec(hi)+tolerance for (lo, hi), v in zip(row['root']['center_box_zr_m'], center))
        state = row['connection_direction']; states[state] = states.get(state, 0)+1
        if max(abs(x-y) for x, y in zip(p, q)) < tolerance:
            assert state == 'ZERO_LENGTH' and row['root']['source_contacts_coincide']; continue
        assert row['root']['source_contacts_coincide'] is False
        if target['fractions'][0] < D('1e-85') or target['fractions'][1] > 1-D('1e-85'):
            assert state != 'FORWARD'; continue
        phases = [phase_reference(F(x[0]-center[0]), F(x[1]-center[1])) for x in (p, q)]
        sweep = settings['turn_direction']*(phases[1]-phases[0])
        while sweep <= 0: sweep += 2*pi
        while sweep > 2*pi: sweep -= 2*pi
        assert abs(sweep-dec(settings['max_sweep_rad'])) > D('1e-12')
        if sweep > dec(settings['max_sweep_rad']): assert state == 'SWEEP_LIMIT'; continue
        assert state == 'FORWARD', (name, row.get('construction_reason'))
        output = [curve_from_dict(x) for x in row['trimmed_curves']]
        assert output[1].semiaxes_m == (abs(distance), abs(distance))
        for point, trimmed, ff, endpoint, trim_bound, fillet_bound in zip((p, q), (output[0], output[2]),
                (0, 1), (1, 0), row['trim_contact_error_bounds_m'], row['fillet_contact_error_bounds_m']):
            for actual_point, bound in ((evaluate(trimmed, endpoint)[0], trim_bound), (evaluate(output[1], ff)[0], fillet_bound)):
                error = sum((x-y)**2 for x, y in zip(actual_point, point)).sqrt()
                assert error <= dec(bound)+tolerance, (name, 'contact output bound')
                assert bound <= settings['position_tolerance_m']
        for left, right in zip(output, output[1:]):
            u, v = evaluate(left, 1)[1], evaluate(right, 0)[1]
            angle = abs(phase_reference(F(sum(x*y for x, y in zip(u, v))), F(u[0]*v[1]-u[1]*v[0])))
            assert angle <= dec(settings['angle_tolerance_rad'])
    assert matches == sorted(matches), (name, 'lexicographic source-pair order')
    return dict(name=name, checked_pairs=len(expected), enumerated_pairs=len(candidates), states=states,
                reference_scope='known cusp pair only' if subset else 'all independent reference pairs')


def geometry_checks(out):
    rows = []; base = EllipseArc((0, 0), (2, 1), -3., 6.); pi = reference_pi()
    generic = [('symmetric', base, replace(base, semiaxes_m=(1, 2)), .25),
        ('shifted', base, replace(base, semiaxes_m=(1, 2), center_zr_m=(1., .25)), .25),
        ('rotated', replace(base, rotation_rad=.3), replace(base, semiaxes_m=(1, 2), center_zr_m=(1., .25), rotation_rad=.7), .25),
        ('ellipse-hyperbola', base, HyperbolaArc((0, .25), (1, 1.5), -2., 2.), .25),
        ('hyperbola-ellipse', HyperbolaArc((0, 0), (1, 1.5), -2., 2., branch=-1), replace(base, center_zr_m=(-1., 0)), -.25),
        ('hyperbola-hyperbola', HyperbolaArc((-2, 0), (2, 1), -2., 2.), HyperbolaArc((0, 0), (1, 2), -2., 2.), .25)]
    for name, first, second, d in generic:
        expected = []; source_parameters = source_scan(first, second, d, d)
        for t in source_parameters:
            center = source_point(first, t, d)
            for other in normal_feet(second, center):
                error = max(abs(x-y) for x, y in zip(center, source_point(second, other, d)))
                assert error < D('1e-95') or error > D('1e-20')
                if error < D('1e-95'): expected.append(pair((first, second), (t, other), d))
        print(name, 'independent reference pairs', len(expected), flush=True)
        rows.append(check_output((first, second), d, expected, out, name))
        print(name, 'PASS', flush=True)
    h = HyperbolaArc((0, 2), (2, 1), -.5, .5); e = EllipseArc((0, 0), (2, 1), -2., 2.)
    reflection = replace(e, start_rad=-1.5, sweep_rad=1.3); hyper = HyperbolaArc((0, 0), (2, 1), -2., -.1)
    families = [('branches-tangent', h, replace(h, branch=-1, start_parameter=.5, end_parameter=-.5), 2., 'branches'),
        ('branches-crossing', h, replace(h, branch=-1, start_parameter=.5, end_parameter=-.5), 2.25, 'branches'),
        ('shared-endpoint', e, replace(e, start_rad=0., sweep_rad=4.), 2., 'endpoint'),
        ('four-feet-one-center', replace(e, semiaxes_m=(2, 3), start_rad=-.1, sweep_rad=3.5), replace(e, start_rad=-.1, sweep_rad=3.5), 2., 'four'),
        ('ellipse-reflection', reflection, replace(reflection, start_rad=.2), .75, 'reflection'),
        ('hyperbola-reflection', hyper, replace(hyper, start_parameter=-.1, end_parameter=-2., branch=-1, rotation_rad=math.pi), -.75, 'reflection')]
    for name, first, second, d, kind in families:
        if kind == 'branches': expected = [pair((first, second), r['parameters'], d) for r in branch_reference(first, second, (d, d), ((0, 1), (0, 1)))]
        elif kind == 'endpoint': expected = [pair((first, second), values, d) for values in ((D(0), D(0)), (D(0), pi))]
        elif kind == 'four': expected = [pair((first, second), (a, b), d) for a in (D(0), pi) for b in (D(0), pi)]
        else: expected = [reflected_pair(first, second, d)]
        for variant, unit in enumerate((2.**-40, 1., 2.**40, 1.)):
            curves = (rescale(first, unit), rescale(second, unit)); distance = d*unit
            targets = deepcopy(expected)
            for r in targets:
                r['center'] = tuple(x*dec(unit) for x in r['center'])
                r['contacts'] = tuple(tuple(x*dec(unit) for x in p) for p in r['contacts'])
            if variant == 3:
                curves = reverse(curves[1]), reverse(curves[0]); distance = -distance
                retained = []
                for r in targets:
                    # The constructor normalizes a reversed ellipse's start
                    # with binary pi. Re-enter each physical foot using true pi
                    # and the resulting stored finite domain. A shared endpoint
                    # can consequently move outside; never force its retention.
                    values = [(parameters(c)[0]+parameters(c)[1]*f) for c, f in zip((first, second), r['fractions'])]
                    fractions = []
                    for c, t in zip(curves, reversed(values)):
                        start, span = parameters(c)
                        possible = [(t+2*j*pi-start)/span for j in (range(-3, 4) if isinstance(c, EllipseArc) else (0,))]
                        accepted = [f for f in possible if -D('1e-85') <= f <= 1+D('1e-85')]
                        assert len(accepted) <= 1
                        if not accepted: break
                        fractions.extend(accepted)
                    if len(fractions) == 2:
                        r['fractions'] = tuple(fractions); r['contacts'] = tuple(reversed(r['contacts'])); retained.append(r)
                targets = retained
            rows.append(check_output(curves, distance, targets, out, f'{name}-{variant}'))
        print(name, 'four variants PASS', flush=True)
    a = EllipseArc((0, 0), (2, 1), -.5, 1.); b = EllipseArc((1.5, -1), (1, 1.5), 0., 2.)
    for i, (curves, values) in enumerate((((a, b), (D(0), pi/2)), ((b, a), (pi/2, D(0))))):
        rows.append(check_output(curves, .5, [pair(curves, values, .5)], out, f'cusp-{i}', subset=True))
    return rows


def fem_checks(out):
    from superfish_ng.tangent_construction import construct_tangent_case
    from superfish_ng.config import Case
    from superfish_ng.solver import solve
    from superfish_ng.rf import quantities
    request = json.loads((ROOT/'examples/construction/noncircular_conic_fillet_request.json').read_text())
    results = []; reports = []; integral_errors = []
    with localcontext() as context:
        context.prec = 140
        a, b, height, t = D(2), D(1), D(2), D('.5'); pi = reference_pi()
        ch, sh = (t.exp()+(-t).exp())/2, (t.exp()-(-t).exp())/2
        area = 2*a*height*ch+pi*a*a/2-a*b*(ch*sh-t)
        volume = pi*(2*a*height**2*ch+height*pi*a*a+4*a**3/3-2*height*a*b*(ch*sh-t)+2*a*b*b*(ch**3/3-ch+D(2)/3))
    for factor in (1., 2.):
        r = deepcopy(request)
        for curve in r['case_template']['geometry']['curves']:
            for key in ('start_zr_m', 'end_zr_m', 'center_zr_m', 'semiaxes_m'):
                if key in curve: curve[key] = [x*factor for x in curve[key]]
        for key in ('join_tolerance_m', 'minimum_gap_m', 'chord_tolerance_m'): r['case_template']['geometry'][key] *= factor
        r['case_template']['mesh']['contour_mesh']['max_edge_m'] *= factor
        for key in ('radius_m', 'position_tolerance_m'): r['controls'][key] *= factor
        document = construct_tangent_case(r, candidate_index=0); case = Case.from_dict(document['case'])
        errors = {key: abs(getattr(case.curved_contour, key)/expected-1) for key, expected in
                  (('area_m2', float(area)*factor**2), ('volume_m3', float(volume)*factor**3))}
        assert max(errors.values()) < 1e-10; integral_errors.append(errors)
        solution = solve(case); rf = quantities(case, solution)
        (out/f'constructed-{int(factor)}.json').write_text(json.dumps(document, indent=2)+'\n')
        (out/f'rf-{int(factor)}.json').write_text(json.dumps(rf, indent=2)+'\n')
        results.append(solution); reports.append(rf)
    first, second = results
    np.testing.assert_allclose(second.space.geometry.points_rz_m, 2*first.space.geometry.points_rz_m, rtol=1e-13, atol=1e-15)
    np.testing.assert_array_equal(second.space.geometry.cell_nodes, first.space.geometry.cell_nodes)
    correlation = abs(np.dot(first.u[:, 0], second.u[:, 0]))/(np.linalg.norm(first.u[:, 0])*np.linalg.norm(second.u[:, 0]))
    assert 1-correlation < 1e-10
    ratios = {key: reports[1][key]/reports[0][key] for key in ('frequency_hz', 'r_over_q_accelerator_ohm', 'r_over_q_circuit_ohm', 'geometry_factor_ohm', 'transit_time_factor_abs')}
    assert abs(ratios['frequency_hz']-.5) < 1e-10
    assert all(abs(value-1) < 1e-9 for key, value in ratios.items() if key != 'frequency_hz')
    np.savez(out/'field-shape-scaling.npz', first=first.u, second=second.u,
             first_points=first.space.geometry.points_rz_m, second_points=second.space.geometry.points_rz_m, cell_nodes=first.space.geometry.cell_nodes)
    return dict(independent_area_m2=str(area), independent_volume_m3=str(volume), analytic_integral_relative_errors=integral_errors,
                ratios=ratios, coefficient_shape_correlation=float(correlation), nodes=len(first.space.geometry.points_rz_m),
                scope='same constructed synthetic cavity at scales 1 and 2; independent continuous integrals and FEM invariants, not discretization-error bounds')


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--only', choices=('geometry', 'fem', 'all'), default='all'); args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False); before = fingerprints(); started = time.monotonic()
    (args.out/'input-sha256.json').write_text(json.dumps(before, indent=2)+'\n')
    geometry = []
    if args.only != 'fem':
        with localcontext() as context:
            context.prec = 140; geometry = geometry_checks(args.out)
        (args.out/'geometry-report.json').write_text(json.dumps(dict(status='PASS', rows=geometry), indent=2)+'\n')
    fem = fem_checks(args.out) if args.only != 'geometry' else None
    after = fingerprints(); changed = sorted(p for p in set(before)|set(after) if before.get(p) != after.get(p))
    report = dict(status='PASS' if not changed else 'FAILED_SOURCE_FREEZE', seconds=time.monotonic()-started,
                  geometry_cases=len(geometry), checked_pairs=sum(r['checked_pairs'] for r in geometry), geometry=geometry, fem=fem,
                  source_sha256=before, changed_paths=changed,
                  reference='140-digit original normals, independent conic/circle matrix discriminants and original target normal-foot scans; reflected-foot bisection; exact vertex/rank-one/shared-endpoint/cusp invariants; numerical scans do not prove completeness')
    (args.out/'report.json').write_text(json.dumps(report, indent=2)+'\n'); assert not changed, changed
    print({k: report[k] for k in ('status', 'seconds', 'geometry_cases', 'checked_pairs')})


if __name__ == '__main__': main()
