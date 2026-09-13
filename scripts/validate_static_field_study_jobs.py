# SPDX-License-Identifier: Apache-2.0
"""Check static Study workers against accepted transformed native runs and real B-H failures."""
import argparse
import contextlib
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from superfish_ng.static_field_project import StaticFieldProject
from superfish_ng.static_field_study import StaticFieldStudy
from superfish_ng.static_field_study_jobs import execute_static_field_study, read_static_field_study
from superfish_ng.jobs import JobManager
from superfish_ng.nonlinear_magnetic import MagneticNonlinearFailure
from scripts.validate_static_field_project import fingerprints
from scripts.validate_static_field_jobs import failure_references


def canonical(value): return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def bindings(case):
    model = importlib.import_module(type(case).__module__); name = model.__name__.rsplit('.', 1)[-1]
    return name, getattr(model, 'solve_axisymmetric_electrostatic' if name == 'electrostatic' else 'solve_' + name), importlib.import_module(model.__name__ + '_saved')


def native_result(project, directory):
    name, _, saved = bindings(project.case)
    failed = (directory / 'failure.json').is_file()
    if failed: outcome = getattr(saved, 'read_' + name + '_failure')(directory)
    else: outcome = getattr(saved, name + '_result')(getattr(saved, 'read_' + name + '_run')(directory))
    return dict(format='superfish_ng_static_field_project_result', schema_version=1,
                status='nonlinear_failed' if failed else 'complete', project=project.to_dict(), outcome=outcome)


def neutral_native(project, directory):
    name, solve, saved = bindings(project.case)
    try: solution = solve(project.case)
    except MagneticNonlinearFailure as failure: getattr(saved, 'save_' + name + '_failure')(project.case, failure, directory)
    else: getattr(saved, 'save_' + name + '_run')(project.case, solution, directory)


def expected_summary(study, natives):
    points = [dict(index=index, value=value, directory=f'point-{index:04d}', result=native_result(project, native))
              for index, (value, project, native) in enumerate(zip(study.values, study.projects(), natives))]
    successes = sum(point['result']['status'] == 'complete' for point in points)
    return dict(format='superfish_ng_static_field_study_result', schema_version=1, study=study.to_dict(),
                execution_status='complete', all_points_successful=successes == len(points),
                successful_points=successes, nonlinear_failed_points=len(points) - successes,
                mode_tracking='not_applicable', solution_branch_tracking='not_performed',
                numerical_validation='not_checked', points=points)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--reference-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(); out = args.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic(); before = fingerprints(); reference = args.reference.resolve(); reference_root = args.reference_root.resolve()
    report = json.loads((reference / 'report.json').read_text()); assert report['status'] == 'PASS' and report['derived_points'] == 165
    inputs = []; old_files = {}; owned_files = {}; records = []; cli_calls = 0
    def remember(directory, target):
        for path in sorted(directory.rglob('*')):
            if path.is_file():
                name = str(path); digest = hashlib.sha256(path.read_bytes()).hexdigest()
                if name in target: assert target[name] == digest, 'previously recorded file changed: ' + name
                else: target[name] = digest
    for path in sorted(reference.glob('*/api.json')):
        study = StaticFieldStudy.load(path); natives = [path.parent / f'{index}-api-native' for index in range(len(study.values))]
        for project, native in zip(study.projects(), natives): assert canonical(project.case.to_dict()) == canonical(json.loads((native / 'case.json').read_text()))
        inputs.append((path.parent.name, study, natives)); remember(path.parent, old_files)
    assert len(inputs) == 66 and sum(len(study.values) for _, study, _ in inputs) == 165
    for index, (family, directory, case, _) in enumerate(failure_references(reference_root)):
        study = StaticFieldStudy(StaticFieldProject.from_dict(case), 'uniform_scale', (1., 1.))
        inputs.append((f'failure-{index}-{family}', study, [directory, directory])); remember(directory, old_files)
    # Each mixed Study has genuine zero/normal success and an excessive excitation failure.
    for family in ('planar_bh', 'axis_bh', 'off_axis_bh'):
        factory = getattr(importlib.import_module('scripts.' + family + '_reference'), 'radial_field' if family == 'off_axis_bh' else 'uniform_field')
        study = StaticFieldStudy(StaticFieldProject(factory(n=2)[0], 'm'), 'excitation_scale', (0., 1., 1000.))
        directory = out / ('neutral-' + family); directory.mkdir(); natives = []
        for index, project in enumerate(study.projects()):
            native = directory / str(index); neutral_native(project, native); natives.append(native)
        expected = expected_summary(study, natives); assert expected['successful_points'] == 2 and expected['nonlinear_failed_points'] == 1
        inputs.append(('mixed-' + family, study, natives)); remember(directory, owned_files)
    assert len(inputs) == 78 and sum(len(study.values) for _, study, _ in inputs) == 192
    def cli(name, arguments, expected_status):
        nonlocal cli_calls
        cli_calls += 1
        result = subprocess.run([sys.executable, '-m', 'superfish_ng', *map(str, arguments)], cwd=ROOT,
                                env={**os.environ, 'OPENBLAS_NUM_THREADS': '1', 'PYTHONPATH': str(ROOT / 'src')}, capture_output=True, timeout=900)
        (out / (name + '.stdout')).write_bytes(result.stdout); (out / (name + '.stderr')).write_bytes(result.stderr)
        assert result.returncode == expected_status, (name, result.returncode, result.stderr.decode())
        return json.loads(result.stdout)
    def compare(directory, study, natives, expected):
        actual = read_static_field_study(directory); assert canonical(actual) == canonical(expected)
        assert (directory / 'study.json').read_bytes() == study.dumps().encode()
        for index, (project, native) in enumerate(zip(study.projects(), natives)):
            point = directory / f'point-{index:04d}'
            assert (point / 'project.json').read_bytes() == project.dumps().encode()
            assert {p.name: p.read_bytes() for p in (point / 'solution').iterdir()} == {p.name: p.read_bytes() for p in native.iterdir()}
        remember(directory, owned_files)
    manager = JobManager(out / 'workspace'); restart = []
    try:
        for index, (name, study, natives) in enumerate(inputs):
            expected = expected_summary(study, natives); code = 0 if expected['all_points_successful'] else 1
            api_directory = out / f'{index:02d}-api'; actual = execute_static_field_study(study, api_directory)
            assert canonical(actual) == canonical(expected); compare(api_directory, study, natives, expected)
            identifier = manager.start_static_field_study(study); end = time.monotonic() + 900
            while time.monotonic() < end:
                state = manager.status(identifier)
                if state['status'] not in ('queued', 'running'): break
                time.sleep(.03)
            else: raise AssertionError('static Study worker did not complete')
            manager.processes[identifier].wait(timeout=max(.001, end - time.monotonic()))
            state = manager.status(identifier)
            assert state['status'] == 'complete' and state['all_points_successful'] == expected['all_points_successful']
            compare(manager.directory(identifier), study, natives, expected); restart.append((identifier, study, natives, expected))
            cli_directory = out / f'{index:02d}-cli'
            assert canonical(cli(f'{index:02d}-solve', ['solve-static-study', api_directory / 'study.json', '--out', cli_directory], code)) == canonical(expected)
            assert canonical(cli(f'{index:02d}-replay', ['replay-static-study', cli_directory], code)) == canonical(expected)
            compare(cli_directory, study, natives, expected)
            records.append(dict(name=name, worker_id=identifier, points=len(study.values), successful_points=expected['successful_points'],
                                nonlinear_failed_points=expected['nonlinear_failed_points'], all_cases_quantities_histories_and_native_bytes_identical=True))
            print('DONE', index, name, 'points', len(study.values), 'failures', expected['nonlinear_failed_points'], flush=True)
    finally: manager.close()
    with contextlib.closing(JobManager(out / 'workspace')) as manager:
        for identifier, study, natives, expected in restart:
            assert manager.status(identifier)['status'] == 'complete'; compare(manager.directory(identifier), study, natives, expected)
    assert cli_calls == 156 and len(records) == len(restart) == 78
    assert sum(row['nonlinear_failed_points'] for row in records) == 21
    assert before == fingerprints()
    for files in (old_files, owned_files):
        for name, digest in files.items(): assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest
    report = dict(status='PASS', studies=78, reference_input_studies=66, source_failure_studies=9, mixed_studies=3,
                  points_per_route=192, successful_points_per_route=171, actual_nonlinear_failure_points_per_route=21,
                  api_studies=78, real_worker_studies=78, cli_studies=78, restart_worker_studies=78, cli_calls=cli_calls,
                  reference_files_unchanged=len(old_files), owned_files_unchanged=len(owned_files), source_sha256=before,
                  records=records, seconds=time.monotonic()-started,
                  interpretation='Every requested Case and original native outcome agrees across static Study API, actual worker, CLI and restart. Execution completion and physical success are distinct. No new solver, warm start, branch tracking, GUI or target-version claim.')
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n'); print({k: v for k, v in report.items() if k not in ('source_sha256', 'records')})


if __name__ == '__main__': main()
