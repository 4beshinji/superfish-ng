# SPDX-License-Identifier: Apache-2.0
"""Measure curved adaptive versus uniform FEM errors, DOFs and solve time."""
import argparse
from dataclasses import replace
import csv
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time
from unittest.mock import patch

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from superfish_ng import solve
from superfish_ng import curved_adaptive_refinement as adaptive
from superfish_ng.analytic_sphere import SphereTM
from superfish_ng.constants import MU0
from superfish_ng.curved_refinement_steps import CurvedRefinementStep
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution
from superfish_ng.saved_mode_tracking import build_saved_mode_tracking
from superfish_ng.curved_residual_indicator import curved_residual_indicator
from superfish_ng.adaptive_surface_stopping import surface_changes

LIMITS = dict(frequency_hz=1e-4, r_over_q_accelerator_ohm=.005,
              geometry_factor_ohm=.005, epk_over_eacc=.01,
              bpk_over_eacc_mt_per_mv_per_m=.01)


def fingerprints():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('src', 'tests', 'scripts', 'examples')
            for p in sorted((ROOT / folder).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def reference():
    sphere = SphereTM(.08, normalization_j=1.)
    q = sphere.quantities()
    eacc = abs(complex(q['voltage_real_v'], q['voltage_imag_v'])) / .16
    exact = {key: q[key] for key in adaptive.RF}
    exact.update(epk_over_eacc=abs(float(sphere.fields([[0., 0.]])['Ez_quadrature_V_per_m'][0])) / eacc,
                 bpk_over_eacc_mt_per_mv_per_m=MU0 * abs(float(sphere.fields([[.08, .08]])['Hphi_A_per_m'][0])) / eacc * 1e9)
    return exact


def summarize(level, elapsed, exact):
    intervals = {key: [level['quantities'][key]] * 2 for key in adaptive.RF}
    intervals.update(level['surface']['intervals'])
    errors = {key: max(abs(value / exact[key] - 1) for value in values)
              if values else None for key, values in intervals.items()}
    return dict(triangles=level['triangles'], dofs=level['dofs'], solve_seconds=elapsed,
                analytical_relative_errors=errors, intervals=intervals,
                analytical_targets_met=all(v is not None and v <= LIMITS[k] for k, v in errors.items()),
                quadrature_check=level['quadrature_check'], refinement_kind=level['refinement_kind'])


def uniform_confirmed(levels, request):
    if len(levels) < 3:
        return False
    pairs = list(zip(levels[-3:], levels[-2:]))
    rf = all(abs(b['quantities'][key] / a['quantities'][key] - 1) <= request['relative_tolerances'][key]
             for a, b in pairs for key in adaptive.RF)
    peaks = all(value['passed'] for row in surface_changes(levels, request['surface_relative_tolerances']) for value in row.values())
    return rf and peaks and all(level['quadrature_check']['passed'] for level in levels)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path, help='new output directory')
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    before = fingerprints()
    request = json.loads((ROOT / 'examples/adaptive_refinement/curved_sphere_confirmed.json').read_text())
    case = adaptive.validate_request(request)
    _, plan = adaptive.assemble(request, [])
    # Both methods receive exactly the same initial mesh, geometry, modes and quadrature.
    request['initial_mesh'] = plan.source_mesh
    exact = reference()
    times = []
    original_solve = adaptive.solve
    def timed_solve(*args, **kwargs):
        start = time.perf_counter()
        result = original_solve(*args, **kwargs)
        times.append(time.perf_counter() - start)
        return result
    start = time.perf_counter()
    # Observation only: every solve is the unmodified production FEM implementation.
    with patch.object(adaptive, 'solve', timed_solve):
        result = adaptive.execute(request, out / 'adaptive')
    adaptive_seconds = time.perf_counter() - start
    assert len(times) == len(result['levels'])
    adaptive_rows = [summarize(level, elapsed, exact) for level, elapsed in zip(result['levels'], times)]
    uniform_levels, uniform_rows, runs = [], [], []
    start = time.perf_counter()
    uniform_status = 'LEVEL_LIMIT'
    for index in range(request['max_levels']):
        if len(plan.space.geometry.cell_nodes) * 4**index > request['max_triangles']:
            uniform_status = 'REFINEMENT_LIMIT'
            break
        current_case = replace(case, curved_refinement_levels=0,
                               curved_refinement_steps=(CurvedRefinementStep('uniform'),) * index)
        clock = time.perf_counter()
        solution = solve(current_case, mesh_data=plan.source_mesh)
        elapsed = time.perf_counter() - clock
        run = out / f'uniform-{index:03d}'
        save_run(current_case, solution, run)
        current = read_solution(run)
        if runs:
            pair = build_saved_mode_tracking(dict(schema_version=1, previous_run=str(runs[-1]),
                current_run=str(run), previous_ids=request['initial_ids'], controls=request['controls']))
            (out / f'uniform-tracking-{index:03d}.json').write_text(json.dumps(pair, indent=2) + '\n')
            if pair['tracking']['status'] != 'PASS' or pair['tracking']['current_mode_ids'] != request['initial_ids']:
                uniform_status = 'UNVERIFIED'
                break
        q = json.loads((run / 'results.json').read_text())['modes'][0]
        indicator = curved_residual_indicator(current.case, current, mode=0, quadrature_order=case.quadrature_order)
        level = dict(triangles=len(current.space.geometry.cell_nodes), dofs=len(current.u), quantities=q,
                     surface=adaptive._surface(current, 0, q),
                     quadrature_check=adaptive._quadrature(current, request, 0, indicator),
                     refinement_kind='initial' if index == 0 else 'uniform_confirmation')
        adaptive._quality(current.space, request)
        uniform_levels.append(level)
        uniform_rows.append(summarize(level, elapsed, exact))
        runs.append(run)
        if not level['quadrature_check']['passed']:
            uniform_status = 'QUADRATURE_UNVERIFIED'
            break
        if uniform_confirmed(uniform_levels, request):
            uniform_status = 'TARGETS_MET'
            break
    uniform_seconds = time.perf_counter() - start
    first_equal = adaptive_rows[0]['intervals'] == uniform_rows[0]['intervals']
    ritz = all(all(b['intervals']['frequency_hz'][0] <= a['intervals']['frequency_hz'][0] * (1 + 1e-10)
                   for a, b in zip(rows, rows[1:])) for rows in (adaptive_rows, uniform_rows))
    passed = (before == fingerprints() and first_equal and ritz and result['status'] == uniform_status == 'TARGETS_MET'
              and adaptive_rows[-1]['analytical_targets_met'] and uniform_rows[-1]['analytical_targets_met'])
    report = dict(passed=passed, source_sha256=before, source_changed_during_run=before != fingerprints(),
        environment=dict(python=platform.python_version(), platform=platform.platform(), openblas_num_threads=os.environ.get('OPENBLAS_NUM_THREADS')),
        request=request, analytical_reference=exact, analytical_limits=LIMITS,
        identical_initial_quantities=first_equal, ritz_monotonicity=ritz,
        adaptive=dict(status=result['status'], rows=adaptive_rows, workflow_seconds=adaptive_seconds,
                      first_analytical_target_level=next((i for i, row in enumerate(adaptive_rows) if row['analytical_targets_met']), None)),
        uniform=dict(status=uniform_status, rows=uniform_rows, workflow_seconds=uniform_seconds,
                     first_analytical_target_level=next((i for i, row in enumerate(uniform_rows) if row['analytical_targets_met']), None)),
        final_dof_ratio_adaptive_over_uniform=adaptive_rows[-1]['dofs'] / uniform_rows[-1]['dofs'],
        final_solve_time_ratio_adaptive_over_uniform=adaptive_rows[-1]['solve_seconds'] / uniform_rows[-1]['solve_seconds'],
        scope='synthetic sphere on one fixed quadratic geometry; two-interval five-quantity confirmation and independent analytical errors; timing is one local observation, not a performance guarantee; adaptive workflow replays all ancestors, uniform evaluation visits each level once, so workflow times have different verification workloads; no physical error bound or general efficiency acceptance')
    (out / 'validation.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    with (out / 'errors-and-cost.csv').open('w') as stream:
        writer = csv.writer(stream)
        writer.writerow(['method', 'level', 'triangles', 'dofs', 'solve_seconds', *LIMITS])
        for method, rows in [('adaptive', adaptive_rows), ('uniform', uniform_rows)]:
            for index, row in enumerate(rows):
                writer.writerow([method, index, row['triangles'], row['dofs'], row['solve_seconds'], *[row['analytical_relative_errors'][k] for k in LIMITS]])
    print(f'Curved refinement comparison {"PASS" if passed else "FAIL"}: {out}')
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
