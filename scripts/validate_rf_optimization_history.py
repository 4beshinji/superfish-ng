# SPDX-License-Identifier: Apache-2.0
"""Frozen-history RF searches: real CLI, analytic sphere and Maxwell scaling."""
import argparse
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from superfish_ng.analytic_sphere import SphereTM
from superfish_ng.constants import MU0
from superfish_ng.curved_project_transform import transform_curved_project
from superfish_ng.project import Project
from superfish_ng.rf_optimization import read_rf_optimization, replay_rf_optimization
from superfish_ng.saved import read_solution
from superfish_ng.surface_convergence import replay_surface_convergence
from validate_large_curved_mesh_selection import fingerprints, boundary_moments


def sphere_errors(assessment, radius, energy):
    reference = SphereTM(radius, normalization_j=energy)
    q = reference.quantities()
    eacc = abs(complex(q['voltage_real_v'], q['voltage_imag_v'])) / (2 * radius)
    exact = {k: q[k] for k in ('frequency_hz', 'r_over_q_accelerator_ohm', 'geometry_factor_ohm')}
    exact['epk_over_eacc'] = abs(float(reference.fields([[0., 0.]])['Ez_quadrature_V_per_m'][0])) / eacc
    exact['bpk_over_eacc_mt_per_mv_per_m'] = MU0 * abs(float(reference.fields([[radius, radius]])['Hphi_A_per_m'][0])) / eacc * 1e9
    errors = {k: max(abs(value / target - 1) for value in assessment['rows'][-1]['intervals'][k])
              for k, target in exact.items()}
    # Independent analytical targets, not imported from the assessment gates.
    limits = dict(frequency_hz=1e-4, r_over_q_accelerator_ohm=.005,
                  geometry_factor_ohm=.005, epk_over_eacc=.01,
                  bpk_over_eacc_mt_per_mv_per_m=.01)
    assert all(errors[k] <= limits[k] for k in errors), errors
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    before = fingerprints()
    reports, solutions, rows, analytic = [], [], [], []
    for scale in (1, 2):
        request = json.loads((ROOT / 'examples/optimization/frozen_history_rf.json').read_text())
        original = Project.from_dict(request['project'])
        project = transform_curved_project(original, dict(radial_scale=float(scale),
            axial_scale=float(scale), axial_shear=0.), rf_coordinates='axial')
        project = replace(project, case=replace(project.case, normalization_j=float(scale**2)))
        request['project'] = project.to_dict()
        request['objective_improvement'] /= scale
        path = out / f'request-{scale}.json'
        path.write_text(json.dumps(request, indent=2) + '\n')
        first, resumed = out / f'first-{scale}', out / f'resumed-{scale}'
        commands = [
            ['optimize-rf', str(path), '--out', str(first), '--max-new-trials', '1'],
            ['replay-rf-optimization', str(first / 'checkpoint-001.json')],
            ['resume-rf-optimization', str(first / 'checkpoint-001.json'), '--out', str(resumed)],
        ]
        for index, command in enumerate(commands):
            process = subprocess.run([sys.executable, '-m', 'superfish_ng', *command],
                                     capture_output=True, text=True, cwd=ROOT)
            (out / f'cli-{scale}-{index}.log').write_text(process.stdout + process.stderr)
            assert process.returncode == 0, process.stderr
        report = read_rf_optimization(resumed / 'checkpoint-004.json')
        assert report['status'] == 'SEARCH_COMPLETE' and report['completed_fem_solves'] == 12
        assert report['decision']['search_stop'] == 'TRIAL_LIMIT'
        assert [trial['values'] for trial in report['trials']] == [[1., 1.], [1.01, 1.], [1.01, 1.01], [1.01, 1.01]]
        assert report['trials'][-1]['assessment']['objective']['eligible_value'] < report['trials'][0]['assessment']['objective']['eligible_value']
        prefix = project.case.curved_refinement_steps
        scale_solutions, scale_rows = [], []
        for trial, directory in zip(report['trials'], report['trial_directories']):
            assessment = trial['assessment']['assessment']
            assert assessment['schema_version'] == 2
            assert assessment['refinement_sequence']['fixed_prefix'] == [step.to_dict() for step in prefix]
            counts = [1, 2, 3] if trial['phase'] == 'final' else [0, 1, 2]
            assert [row['refinement_level'] for row in assessment['rows']] == counts
            trial_solutions, trial_rows = [], []
            for level, count in enumerate(counts):
                solution = read_solution(Path(directory) / f'level-{level}/solution')
                steps = solution.case.curved_refinement_steps
                assert steps[:len(prefix)] == prefix and len(steps) == len(prefix) + count
                assert all(step.kind == 'uniform' for step in steps[len(prefix):])
                moments = boundary_moments(solution.space)
                trial_solutions.append(solution)
                trial_rows.append(dict(additional_uniform_steps=count, moments=moments,
                                       triangles=len(solution.space.geometry.cell_nodes), dofs=len(solution.u)))
            # Fixed-domain restriction must preserve the actual quadratic boundary.
            for row in trial_rows[1:]:
                assert max(abs(row['moments'][k] / trial_rows[0]['moments'][k] - 1)
                           for k in row['moments']) < 2e-12
            scale_solutions.append(trial_solutions)
            scale_rows.append(trial_rows)
        final = report['trials'][-1]['assessment']['assessment']
        assert replay_surface_convergence(final) == final
        forged = deepcopy(final)
        forged['refinement_sequence']['fixed_prefix'] = []
        try:
            replay_surface_convergence(forged)
        except ValueError:
            pass
        else:
            raise AssertionError('forged refinement prefix passed replay')
        forged = deepcopy(report)
        forged['request']['project']['case']['mesh']['curved_refinement_steps'][0]['marked_cells'] = [1]
        try:
            replay_rf_optimization(forged)
        except ValueError:
            pass
        else:
            raise AssertionError('changed marked cells passed optimization replay')
        analytic.append(sphere_errors(final, .08 * scale * 1.01, float(scale**2)))
        reports.append(report)
        solutions.append(scale_solutions)
        rows.append(scale_rows)
        print(f'scale {scale}: 12 FEM, preserved prefix, final five analytical quantities and replay PASS', flush=True)
    rf_errors, field_errors, geometry_errors = [], [], []
    for index, (a, b) in enumerate(zip(reports[0]['trials'], reports[1]['trials'])):
        for level, (old, new) in enumerate(zip(solutions[0][index], solutions[1][index])):
            np.testing.assert_array_equal(old.space.geometry.cell_nodes, new.space.geometry.cell_nodes)
            np.testing.assert_allclose(2 * old.space.geometry.points_rz_m, new.space.geometry.points_rz_m, rtol=0, atol=4e-15)
            old_row, new_row = rows[0][index][level], rows[1][index][level]
            for key, factor in [('signed_area_m2', 4), ('signed_volume_m3', 8)]:
                geometry_errors.append(abs(new_row['moments'][key] / old_row['moments'][key] / factor - 1))
            for key, interval in a['assessment']['assessment']['rows'][level]['intervals'].items():
                other = b['assessment']['assessment']['rows'][level]['intervals'][key]
                rf_errors.extend(abs(y * (2 if key == 'frequency_hz' else 1) / x - 1) for x, y in zip(interval, other))
            old_values, new_values = [], []
            for cell in range(len(old.space.geometry.cell_nodes)):
                for solution, values in [(old, old_values), (new, new_values)]:
                    values.append(solution.fields_in_cell(cell, np.array([[.2, .3], [.4, .2]])))
            for key in ('Hphi_A_per_m', 'Er_quadrature_V_per_m', 'Ez_quadrature_V_per_m'):
                x, y = [np.concatenate([value[key] for value in values]) for values in (old_values, new_values)]
                # Length doubles, while energy is multiplied by four.
                field_errors.append(float(np.linalg.norm(x - np.sqrt(2) * y) / np.linalg.norm(x)))
    assert max(rf_errors + field_errors + geometry_errors) < 2e-9
    assert fingerprints() == before
    result = dict(passed=True, dedicated_fem_solves=24, rows=rows,
        analytic_final_relative_errors=analytic, maximum_rf_scaling_error=max(rf_errors),
        maximum_field_scaling_error=max(field_errors), maximum_geometry_scaling_error=max(geometry_errors),
        source_sha256=before, source_unchanged=True, seconds=time.monotonic()-started,
        scope='two real frozen-history RF searches, CLI pause/resume, fixed-domain Green integrals, Maxwell field and five-quantity scaling, independent sphere final errors, native replay and forgery rejection; no general optimizer or physical-error certificate')
    (out / 'validation.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('rows', 'source_sha256')}), flush=True)


if __name__ == '__main__':
    main()
