# SPDX-License-Identifier: Apache-2.0
"""Separate analytic-boundary and fixed-domain FEM surface refinement evidence.

Revalidate the archived G03 ellipse's three geometry approximations and extend
each from two to three FEM levels. No archived field is silently recomputed.
"""
import argparse
from dataclasses import replace
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import json
import math
from pathlib import Path
import time
import numpy as np

from validate_algebraic_conic_fillet import evaluate
from validate_coincident_circle_arcs import fingerprints
from validate_curved_geometry_convergence import mapped_moments
from validate_general_coincident_circle_arcs import decimal_value as dec, reference_pi
from superfish_ng import Case, solve
from superfish_ng.conics import EllipseArc
from superfish_ng.constants import MU0
from superfish_ng.curved_fem import assemble_curved
from superfish_ng.curved_rf import quantities_curved
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution
from superfish_ng.saved_mode_tracking import _snapshot
from superfish_ng.studies import compare_refinement, _physical_spec
from superfish_ng.surface_convergence import _geometry_assessment

LIMITS = dict(frequency_hz=1e-4, r_over_q_accelerator_ohm=.005, geometry_factor_ohm=.005,
              epk_over_eacc=.01, bpk_over_eacc_mt_per_mv_per_m=.01)


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def outward(value, upper):
    result = float(value)
    if (F(result) < value if upper else F(result) > value):
        result = math.nextafter(result, math.inf if upper else -math.inf)
    return result


def intervals(q):
    """Form peak ratios directly from the verified saved field bounds."""
    result = {k: [q[k], q[k]] for k in ('frequency_hz', 'r_over_q_accelerator_ohm', 'geometry_factor_ohm')}
    assert q['eacc_v_per_m'] > 0
    for name, prefix, factor in (('epk_over_eacc', 'epk', F(1)),
            ('bpk_over_eacc_mt_per_mv_per_m', 'hpk', F(MU0)*10**9)):
        unit = 'v_per_m' if prefix == 'epk' else 'a_per_m'
        result[name] = [outward(F(q[f'{prefix}_discrete_{side}_bound_{unit}'])*factor/F(q['eacc_v_per_m']), i == 1)
                       for i, side in enumerate(('lower', 'upper'))]
    assert all(0 < lo <= hi and math.isfinite(hi) for lo, hi in result.values())
    return result


def change(a, b):
    values = {key: outward(max(abs(F(b[key][1])/F(a[key][0])-1), abs(F(b[key][0])/F(a[key][1])-1)), True) for key in LIMITS}
    return dict(passed=all(value <= LIMITS[key] for key, value in values.items()), relative_changes=values)


def boundary_error(space, contour):
    """Cubic interpolation remainder plus binary-node error, at fixed geometry.

For ellipse angle width h, max|C'''| <= max(a,b). The maximum
|x(x-1/2)(x-1)|/6 is 1/(72 sqrt(3)). The quadratic Lagrange
Lebesgue constant is 5/4. Decimal evaluation is an independent reference,
not a new formally verified transcendental implementation.
"""
    rows = []
    with localcontext() as context:
        context.prec = 140
        for nodes, index, (low, high) in zip(space.geometry.boundary_nodes,
                space.geometry.boundary_curve_indices, space.geometry.boundary_parameters):
            curve = contour.curves[int(index)]; lo, hi = dec(float(low)), dec(float(high))
            fractions = lo, hi, (lo+hi)/2
            exact = [evaluate(curve, F(f))[0][::-1] for f in fractions]
            stored = [tuple(map(dec, space.geometry.points_rz_m[node])) for node in nodes]
            node_error = max(sum((x-y)**2 for x, y in zip(a, b)).sqrt() for a, b in zip(exact, stored))
            assert not isinstance(curve, EllipseArc) or curve.rotation_rad == 0., 'reference specifies unrotated example'
            interpolation = (max(map(dec, curve.semiaxes_m))*abs(dec(curve.sweep_rad)*(hi-lo))**3/(72*D(3).sqrt())
                             if isinstance(curve, EllipseArc) else D(0))
            bound = interpolation+D(5)/4*node_error
            sampled = D(0)
            for x in (D('.25'), D('.75')):
                weights = (2*x-1)*(x-1), x*(2*x-1), 4*x*(1-x)
                point = [sum(w*p[k] for w, p in zip(weights, stored)) for k in (0, 1)]
                reference = evaluate(curve, F(lo+x*(hi-lo)))[0][::-1]
                error = sum((p-q)**2 for p, q in zip(point, reference)).sqrt(); sampled = max(sampled, error)
                assert error <= bound+D('1e-120')
            rows.append(dict(curve_index=int(index), source_fractions=[float(low), float(high)],
                             node_error_m=float(node_error), interpolation_bound_m=float(interpolation),
                             boundary_error_bound_m=outward(F(bound), True), sampled_error_m=float(sampled)))
    return dict(maximum_boundary_error_bound_m=max(r['boundary_error_bound_m'] for r in rows),
                maximum_sampled_error_m=max(r['sampled_error_m'] for r in rows), edges=rows,
                scope='analytic quadratic interpolation remainder plus 140-digit node-rounding reference; no electromagnetic error bound')


def quadrature_check(solution):
    high = 16; u = solution.u[:, 0]; u = u/max(abs(u))
    k, m = assemble_curved(solution.space, quadrature_order=high)
    low_k, low_m = float(u@(solution.stiffness@u)), float(u@(solution.mass@u))
    high_k, high_m = float(u@(k@u)), float(u@(m@u))
    differences = dict(rayleigh_frequency=abs(math.sqrt(high_k/high_m/(low_k/low_m))-1), mass=abs(high_m/low_m-1))
    a, b = [quantities_curved(solution, wall_quadrature_order=order, include_surface_peaks=False) for order in (8, 16)]
    differences['geometry_factor_wall_integral'] = abs(b['geometry_factor_ohm']/a['geometry_factor_ohm']-1)
    return dict(passed=max(differences.values()) < 1e-8, relative_differences=differences,
                base_order=solution.case.quadrature_order, high_order=high, tolerance=1e-8)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(); archive = args.archive.resolve(); out = args.out.resolve()
    accepted_path = archive/'comparison.json'; accepted = json.loads(accepted_path.read_text())
    assert accepted['status'] == 'PASS' and accepted['physical_peak_convergence'] == 'UNVERIFIED'
    out.mkdir(parents=True, exist_ok=False); started = time.monotonic(); before = fingerprints()
    write(out/'input-sha256.json', before)
    paths = [[archive/f'ellipse-geometry-{g}'/f'point-{level+1:03d}'/'solution' for level in range(2)] for g in range(3)]
    snapshots = [_snapshot(p) for group in paths for p in group]
    write(out/'archive-provenance.json', dict(directory=str(archive), snapshots=snapshots,
          prior_report=accepted, scope='six archived native fields will be revalidated; three further FEM solves will be new'))
    with localcontext() as context:
        context.prec = 140; a, b = dec(.1), dec(.08); pi = reference_pi()
        exact_area, exact_volume = pi*a*b/2, 4*pi*a*b*b/3
    groups = []; physical = None; final_paths = []
    for index, group in enumerate(paths):
        originals = [read_solution(p) for p in group]; first, second = originals
        assert [s.case.curved_refinement_levels for s in originals] == [0, 1]
        assert all(s.case.geometry_order == 2 and s.case.element_order == 2 and s.case.modes == 1 and s.case.quadrature_order == 12 for s in originals)
        assert replace(second.case, curved_refinement_levels=0).to_dict() == first.case.to_dict()
        assert first.source_mesh_data == second.source_mesh_data and not first.case.curved_refinement_steps
        current_physical = _physical_spec(first.case)
        if physical is None: physical = current_physical
        assert current_physical == physical
        native = first.case.curved_contour
        assert abs(native.area_m2/float(exact_area)-1) < 1e-12 and abs(native.volume_m3/float(exact_volume)-1) < 1e-12
        geometry = _geometry_assessment(native); assert geometry['status'] == 'SMOOTH_WITHIN_TOLERANCE'
        boundary = boundary_error(first.space, native)
        write(out/f'geometry-{index}-boundary.json', boundary)
        third_case = replace(first.case, curved_refinement_levels=2); run = out/f'geometry-{index}-fem-2'
        print('geometry', index, 'extending fixed-domain FEM', 4*len(second.space.geometry.cell_nodes), 'triangles', flush=True)
        third = solve(third_case, mesh_data=first.source_mesh_data); save_run(third_case, third, run)
        all_paths = [*group, run]; solutions = [*originals, read_solution(run)]; rows = []
        for path, solution in zip(all_paths, solutions):
            q = json.loads((path/'results.json').read_text())['modes'][0]
            area, volume = mapped_moments(solution.space)
            rows.append(dict(run=str(path), new_solve=path == run, cells=len(solution.space.geometry.cell_nodes),
                             intervals=intervals(q), mapped_area_m2=area, mapped_volume_m3=volume))
        fixed_moments = all(abs(row[key]/rows[0][key]-1) < 2e-12 for row in rows for key in ('mapped_area_m2', 'mapped_volume_m3'))
        ritz = all(v.frequencies_hz[0] <= u.frequencies_hz[0]*(1+1e-10) for u, v in zip(solutions, solutions[1:]))
        comparisons = [compare_refinement(p, q) for p, q in zip(all_paths, all_paths[1:])]
        changes = [change(p['intervals'], q['intervals']) for p, q in zip(rows, rows[1:])]
        quadrature = quadrature_check(solutions[-1])
        gates = dict(two_fem_intervals=all(c['passed'] for c in changes), paired_fields_and_rf=all(c['status'] == 'PASS' for c in comparisons),
                     fixed_moments=fixed_moments, parent_child_ritz=ritz, quadrature=quadrature['passed'])
        record = dict(status='PASS' if all(gates.values()) else 'FAIL', gates=gates, rows=rows, fem_changes=changes,
                      field_comparisons=comparisons, quadrature=quadrature, geometry_diagnostic=geometry,
                      chord_tolerance_m=first.case.curve_chord_tolerance_m,
                      boundary_error_bound_m=boundary['maximum_boundary_error_bound_m'],
                      relative_area_error=abs(rows[0]['mapped_area_m2']/float(exact_area)-1),
                      relative_volume_error=abs(rows[0]['mapped_volume_m3']/float(exact_volume)-1))
        groups.append(record); final_paths.append(run); write(out/f'geometry-{index}.json', record)
        print('geometry', index, record['status'], [c['relative_changes'] for c in changes], flush=True)
    comparisons = [compare_refinement(p, q) for p, q in zip(final_paths, final_paths[1:])]
    changes = [change(p['rows'][-1]['intervals'], q['rows'][-1]['intervals']) for p, q in zip(groups, groups[1:])]
    decreasing = all(q[key] < p[key] for p, q in zip(groups, groups[1:]) for key in ('boundary_error_bound_m', 'relative_area_error', 'relative_volume_error'))
    negative_case = Case.load(archive/'hyperbola-geometry-0/point-001/solution/case.json')
    negative = _geometry_assessment(negative_case.curved_contour); assert negative['status'] != 'SMOOTH_WITHIN_TOLERANCE'
    stable_archive = snapshots == [_snapshot(p) for group in paths for p in group] and accepted == json.loads(accepted_path.read_text())
    after = fingerprints(); changed = [p for p in set(before)|set(after) if before.get(p) != after.get(p)]
    gates = dict(each_fixed_geometry=all(g['status'] == 'PASS' for g in groups), two_geometry_intervals=all(c['passed'] for c in changes),
                 geometry_field_comparisons=all(c['status'] == 'PASS' for c in comparisons), geometric_errors_decrease=decreasing,
                 archive_unchanged=stable_archive, source_unchanged=not changed)
    report = dict(status='PASS' if all(gates.values()) else 'FAIL', gates=gates, seconds=time.monotonic()-started,
                  limits=LIMITS, geometry_groups=groups, geometry_changes=changes, geometry_field_comparisons=comparisons,
                  nonsmooth_hyperbola_control=negative, source_sha256=before, changed_paths=changed,
                  scope='one synthetic smooth ellipsoid, three quadratic geometry approximations, each with two fixed-domain FEM intervals; archived native replay plus three new solves; scalar peak intervals and paired fields',
                  physical_error_bound=None, interpretation='empirical separated geometry/FEM convergence for this geometry and computed mode; no independent exact nonspherical Maxwell reference or general physical-peak guarantee')
    write(out/'report.json', report); print(report['status'], gates, flush=True)
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__': raise SystemExit(main())
