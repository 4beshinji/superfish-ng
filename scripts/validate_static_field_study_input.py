# SPDX-License-Identifier: Apache-2.0
"""Compare static Study transformations with independent Case/FEM invariants."""
import argparse
import copy
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from superfish_ng.static_field_study import StaticFieldStudy
from superfish_ng.static_field_project import StaticFieldProject, static_case_from_dict
from superfish_ng.nonlinear_magnetic import MagneticNonlinearFailure
from scripts.validate_static_field_project import fingerprints


def transformed(source, parameter, factor):
    """Walk input units/locations, independently of the Study implementation."""
    raw = copy.deepcopy(source)
    def walk(value, path=()):
        if not isinstance(value, dict): return
        for name, child in value.items():
            if parameter == 'uniform_scale' and path and path[0] == 'partition':
                if name in ('points_rz_m', 'outer_rz_m', 'points_xy_m', 'polygon_xy_m'):
                    value[name] = (np.asarray(child) * factor).tolist(); continue
                if name == 'holes_rz_m':
                    value[name] = [(np.asarray(hole) * factor).tolist() for hole in child]; continue
            if parameter == 'excitation_scale':
                if not path and name in ('charge_density_c_per_m3', 'current_density_z_a_per_m2', 'current_density_phi_a_per_m2'):
                    value[name] = {region: density * factor for region, density in child.items()}; continue
                if name == 'boundaries':
                    for boundary in child:
                        for field in set(boundary) - {'id', 'kind', 'edge_indices'}: boundary[field] *= factor
                    continue
                if name == 'materials':
                    for material in child:
                        if 'remanent_b_local_t' in material:
                            material['remanent_b_local_t'] = (np.asarray(material['remanent_b_local_t']) * factor).tolist()
                    continue
            walk(child, path + (name,))
    walk(raw)
    return static_case_from_dict(raw)


def bindings(case):
    model = importlib.import_module(type(case).__module__)
    name = model.__name__.rsplit('.', 1)[-1]
    return name, getattr(model, 'solve_axisymmetric_electrostatic' if name == 'electrostatic' else 'solve_' + name), importlib.import_module(model.__name__ + '_saved')


def compute(case, path):
    name, solve, saved = bindings(case)
    try: solution = solve(case)
    except MagneticNonlinearFailure as failure:
        getattr(saved, 'save_' + name + '_failure')(case, failure, path)
        return True, getattr(saved, 'read_' + name + '_failure')(path), None
    getattr(saved, 'save_' + name + '_run')(case, solution, path)
    return False, getattr(saved, name + '_result')(solution), solution


def probe(solution):
    mesh = solution.case.partition.mesh
    points = mesh.points_xy_m if 'planar' in solution.case.to_dict()['format'] else mesh.points_rz_m
    return solution.probe_at(points[mesh.triangles].mean(axis=1))['fields']


def proportional(actual, expected, multiplier, label):
    scale = max(float(np.max(np.abs(expected))), 1e-30)
    np.testing.assert_allclose(actual, np.asarray(expected) * multiplier, rtol=2e-11, atol=2e-12 * scale, err_msg=label)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(); out = args.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic(); before = fingerprints(); source_files = {}; owned = {}; records = []; calls = linear = geometric = failed = 0
    def retain(directory, collection):
        for file in sorted(directory.rglob('*')):
            if file.is_file(): collection[str(file)] = hashlib.sha256(file.read_bytes()).hexdigest()
    reference = json.loads((args.reference / 'report.json').read_text()); assert reference['status'] == 'PASS'
    selected = [row for row in json.loads((args.reference / 'cases.json').read_text()) if not row['failed']]; assert len(selected) == 33
    for index, row in enumerate(selected):
        source = Path(row['source_job']); retain(source, source_files)
        project = StaticFieldProject.load(source / 'project.json'); case = project.case; name, _, saved = bindings(case)
        original_solution = getattr(saved, 'read_' + name + '_run')(source / 'solution')
        original = getattr(saved, name + '_result')(original_solution); original_fields = probe(original_solution)
        original_case = case.to_dict()
        for parameter, values in [('uniform_scale', (.5, 2.)), ('excitation_scale', (-2., 0., 2.))]:
            directory = out / f'{index:02d}-{parameter}'; directory.mkdir()
            study = StaticFieldStudy(project, parameter, values); study.save(directory / 'api.json')
            command = [sys.executable, '-m', 'superfish_ng', 'normalize-static-study', str(directory / 'api.json'), '--out', str(directory / 'cli.json')]
            completed = subprocess.run(command, cwd=ROOT, env={**os.environ, 'PYTHONPATH': str(ROOT / 'src'), 'OPENBLAS_NUM_THREADS': '1'}, capture_output=True); calls += 1
            (directory / 'cli-stdout.json').write_bytes(completed.stdout); (directory / 'cli-stderr.log').write_bytes(completed.stderr)
            assert completed.returncode == 0, completed.stderr.decode()
            assert (directory / 'api.json').read_bytes() == (directory / 'cli.json').read_bytes() == completed.stdout
            loaded = StaticFieldStudy.load(directory / 'cli.json'); assert loaded.to_dict() == study.to_dict()
            for point, (value, derived, cli_project) in enumerate(zip(values, study.projects(), loaded.projects())):
                expected_case = transformed(original_case, parameter, value)
                assert derived.case.to_dict() == cli_project.case.to_dict() == expected_case.to_dict()
                assert derived.display_length_unit == project.display_length_unit
                first = directory / f'{point}-api-native'; second = directory / f'{point}-independent-native'
                api_failed, outcome, solution = compute(derived.case, first)
                expected_failed, expected_outcome, _ = compute(expected_case, second)
                assert api_failed == expected_failed and outcome == expected_outcome
                assert {p.name: p.read_bytes() for p in first.iterdir()} == {p.name: p.read_bytes() for p in second.iterdir()}
                failed += int(api_failed)
                if not '_bh_case' in original_case['format'] and parameter == 'excitation_scale':
                    assert not api_failed
                    for field, data in original_fields.items(): proportional(probe(solution)[field], data, value, row['name'] + '/' + field)
                    names = [key for key in original['quantities'] if key in ('energy_j', 'energy_j_per_m', 'b_quadratic_j', 'b_quadratic_j_per_m', 'remanence_coupling_j', 'remanence_coupling_j_per_m', 'constitutive_potential_b0_j', 'constitutive_potential_b0_j_per_m', 'constitutive_potential_h0_j', 'constitutive_potential_h0_j_per_m')]
                    assert names
                    for key in names: proportional(outcome['quantities'][key], original['quantities'][key], value**2, key)
                    linear += 1
                if parameter == 'uniform_scale' and original_case['physics'] == 'linear_electrostatic' and all(v == 0 for v in original_case['charge_density_c_per_m3'].values()) and all(b.get('outward_displacement_c_per_m2', 0) == 0 for b in original_case['boundaries']):
                    actual_fields = probe(solution)
                    for prefix in ('potential_', 'E', 'D'):
                        fields = [field for field in original_fields if field.startswith(prefix)]; assert fields
                        proportional(np.column_stack([actual_fields[field] for field in fields]), np.column_stack([original_fields[field] for field in fields]), 1 if prefix == 'potential_' else 1/value, prefix)
                    key = 'energy_j_per_m' if 'planar' in original_case['format'] else 'energy_j'; proportional(outcome['quantities'][key], original['quantities'][key], 1 if 'planar' in original_case['format'] else value, key); geometric += 1
                records.append(dict(source=row['name'], parameter=parameter, value=value, failed=api_failed, complete_case_and_native_identical=True))
            assert case.to_dict() == original_case; retain(directory, owned)
        print('DONE', index, row['name'], flush=True)
    assert len(records) == 165 and calls == 66 and linear == 72 and geometric == 4
    assert before == fingerprints()
    for paths in (source_files, owned):
        for name, digest in paths.items(): assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest
    report = dict(status='PASS', source_cases=33, studies=66, derived_points=165, paired_original_fem_runs=330, actual_failure_points=failed,
                  cli_calls=calls, linear_excitation_invariant_points=linear, geometric_invariant_points=geometric,
                  reference_files_unchanged=len(source_files), owned_files_unchanged=len(owned), seconds=time.monotonic()-start,
                  source_sha256=before, records=records, interpretation='Strict static Study input and derived Cases only; nonlinear initial values unchanged; actual dedicated FEM comparisons retain real failures. Study workers/results/GUI require separate acceptance.')
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n'); print({k: v for k, v in report.items() if k not in ('source_sha256', 'records')})


if __name__ == '__main__': main()
