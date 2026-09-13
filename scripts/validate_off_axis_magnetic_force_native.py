# SPDX-License-Identifier: Apache-2.0
"""Compare full-ring force native/API/CLI reports to independent FEM references."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from superfish_ng.off_axis_magnetostatic import OffAxisMagnetostaticCase, solve_off_axis_magnetostatic
from superfish_ng.off_axis_magnetostatic_saved import save_off_axis_magnetostatic_run, _snapshot
from superfish_ng.off_axis_magnetic_force_saved import export_off_axis_magnetic_force, replay_off_axis_magnetic_force


def fingerprints():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('src', 'tests', 'scripts', 'examples')
            for p in sorted((ROOT / folder).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out, reference = args.out.resolve(), args.reference.resolve()
    out.mkdir(parents=True, exist_ok=False)
    source_report = json.loads((reference / 'report.json').read_text())
    assert source_report['status'] == 'PASS' and source_report['cases'] == 50
    start = time.monotonic()
    before, preserved, reference_files, records = fingerprints(), {}, {}, []
    calls = 0
    # Both element orders, signs and scales; magnetic bodies, q=4/32 and psi offsets.
    indices = [0, 3, 5, 6, 8, 11, 13, 14, 16, 19, 21, 22, 30, 33, 43, 46, 35, 36, 48, 49]
    with_work = {0, 3, 8, 11, 16, 19, 21, 22, 35, 49}
    selected = [source_report['records'][i] for i in indices]

    def retain(path):
        preserved[str(path.relative_to(out))] = hashlib.sha256(path.read_bytes()).hexdigest()

    def read_reference(path):
        reference_files[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
        return json.loads(path.read_text())

    def cli(name, arguments, code=0):
        nonlocal calls
        calls += 1
        environment = dict(os.environ, PYTHONPATH=str(ROOT / 'src'), OPENBLAS_NUM_THREADS='1')
        result = subprocess.run([sys.executable, '-m', 'superfish_ng', *map(str, arguments)],
                                cwd=ROOT, env=environment, capture_output=True, text=True, timeout=300)
        (out / (name + '.stdout')).write_text(result.stdout)
        (out / (name + '.stderr')).write_text(result.stderr)
        assert result.returncode == code, (name, result.returncode, result.stderr)
        return json.loads(result.stdout) if code == 0 else None

    for index, row in zip(indices, selected):
        name = row['name']
        original = read_reference(reference / (name + '.json'))
        expected_force = read_reference(reference / (name + '.stress.json'))
        virtual = index in with_work
        expected_work = read_reference(reference / (name + '.work.json')) if virtual else None
        steps = {'translation_steps_m': expected_work['translation_steps_m']} if virtual else None
        request = dict(format='superfish_ng_off_axis_magnetic_force_request', schema_version=1,
                       body_region_ids=original['body_region_ids'], weights=original['weights'], virtual_work=steps)
        directory = out / name
        directory.mkdir()
        case = OffAxisMagnetostaticCase.from_dict(original['case'])
        run = directory / 'source'
        save_off_axis_magnetostatic_run(case, solve_off_axis_magnetostatic(case), run)
        native = _snapshot(run)
        for path in run.iterdir():
            retain(path)
        req = directory / 'request.json'
        req.write_text(json.dumps(request, indent=2) + '\n')
        retain(req)
        first, second, target = [directory / n for n in ('api.json', 'repeat.json', 'cli.json')]
        report = export_off_axis_magnetic_force(run, first, request)
        assert report['force'] == expected_force and report['virtual_work'] == expected_work
        assert report['schema_version'] == 1
        if not virtual:
            assert report['stress_virtual_work_comparison'] is None
        assert export_off_axis_magnetic_force(run, second, request) == report
        assert second.read_bytes() == first.read_bytes()
        assert replay_off_axis_magnetic_force(run, first) == report
        actual = cli(f'{index}-analyze', ['analyze-off-axis-magnetic-force', run, '--request', req, '--out', target])
        assert actual == report and target.read_bytes() == first.read_bytes()
        for j, path in enumerate((first, target)):
            assert cli(f'{index}-replay-{j}', ['replay-off-axis-magnetic-force', run, path]) == report
        for path in (first, second, target):
            retain(path)
        assert _snapshot(run) == native
        records.append(dict(name=name, kind=row['kind'], order=row['order'],
                            quadrature_order=row['quadrature_order'], virtual_work=virtual,
                            full_stress_and_requested_work_json_identical=True,
                            native_files=5, reports=3, cli_calls=3))
        print('DONE', name, 'virtual', virtual, flush=True)

    last = out / selected[-1]['name']
    cli('overwrite', ['analyze-off-axis-magnetic-force', last / 'source', '--request', last / 'request.json', '--out', last / 'cli.json'], 2)
    invalid = out / 'invalid-request.json'
    bad = json.loads((last / 'request.json').read_text())
    bad['rotation_steps_rad'] = [.01, .005]
    invalid.write_text(json.dumps(bad))
    cli('invalid', ['analyze-off-axis-magnetic-force', last / 'source', '--request', invalid, '--out', out / 'invalid-output.json'], 2)
    assert not (out / 'invalid-output.json').exists()
    for name, digest in preserved.items():
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == digest
    for name, digest in reference_files.items():
        assert hashlib.sha256((reference / name).read_bytes()).hexdigest() == digest
    assert fingerprints() == before and calls == 62 and len(preserved) == 180 and len(reference_files) == 50
    report = dict(status='PASS', cases=20, virtual_work_cases=10, stress_only_cases=10,
                  native_files_unchanged=100, report_files=60, request_files=20,
                  preserved_files=len(preserved), reference_files_unchanged=len(reference_files),
                  cli_calls=calls, records=records, source_sha256=before, seconds=time.monotonic()-start,
                  interpretation='Actual positive-radius P1/P2 full-ring axial force N and optional displaced-FEM potential J; source/reference and full API/CLI JSON and bytes unchanged. Null omits work. No radial net force, meridional torque, axis-connected/BH/recoil force or GUI acceptance.')
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print({k: v for k, v in report.items() if k not in ('records', 'source_sha256')})


if __name__ == '__main__':
    main()
