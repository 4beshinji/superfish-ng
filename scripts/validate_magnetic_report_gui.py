# SPDX-License-Identifier: Apache-2.0
"""Independent saved-reference comparisons through real magnetic GUI workers."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from superfish_ng.jobs import JobManager
from superfish_ng.gui_magnetic_reports import MagneticReportAccess, magnetic_report_response
from superfish_ng.magnetic_report_jobs import magnetic_report_job_hashes


def fingerprints():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('src', 'tests', 'scripts', 'examples')
            for p in sorted((ROOT / folder).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def selected_references(root):
    def catalog(slug):
        directory = root / (slug + '-independent-trial-20260913')
        assert json.loads((directory / 'report.json').read_text())['status'] == 'PASS'
        rows = []
        for path in sorted(directory.glob('*/api.json')):
            report = json.loads(path.read_text())
            case = json.loads((path.parent / 'source/case.json').read_text())
            rows.append(dict(name=slug + '/' + path.parent.name, source=str(path.parent / 'source'),
                             report=str(path), data=report, case=case))
        return rows
    def one(rows, predicate):
        return next(row for row in rows if predicate(row))
    selected = []
    rows = catalog('planar-magnetic-multipole-native')
    for order in (1, 2): selected.append(one(rows, lambda row: row['case']['element_order'] == order))
    rows = catalog('planar-magnetic-multipole-material-native')
    for kind in ('bh', 'recoil'):
        for field in ('dipole', 'quadrupole'):
            selected.append(one(rows, lambda row: row['name'].split('/')[-1].startswith(kind + '-' + field)))
    rows = catalog('planar-magnetic-force-native')
    for order in (1, 2):
        for work in (False, True):
            selected.append(one(rows, lambda row: row['case']['element_order'] == order and (row['data']['virtual_work'] is not None) == work))
    rows = catalog('planar-magnetic-force-material-native')
    for physics in ('nonlinear_isotropic_magnetostatic', 'linear_recoil_magnetostatic'):
        for work in (False, True):
            selected.append(one(rows, lambda row: row['case']['physics'] == physics and row['data']['status'] == 'complete' and (row['data']['virtual_work'] is not None) == work))
    for failure in ('first_displacement', 'later_rotation'):
        selected.append(one(rows, lambda row: '/failure-' + failure in row['name']))
    rows = catalog('off-axis-magnetic-force-native')
    for order in (1, 2):
        for work in (False, True):
            selected.append(one(rows, lambda row: row['case']['element_order'] == order and (row['data']['virtual_work'] is not None) == work))
    assert len(selected) == len({row['name'] for row in selected}) == 20
    return selected


def compare_view(view, row):
    report, case = row['data'], row['case']
    assert view['source_case'] == case and view['physics'] == case['physics']
    assert view['source_native_sha256'] == report['source_native_sha256']
    assert view['request'] == report['request'] and view['report_schema_version'] == report['schema_version']
    if 'extraction' in report:
        extraction = report['extraction']; series = extraction['series']
        assert view['kind'] == 'planar_multipole' and view['frame'] == series['frame']
        assert view['convention'] == series['convention'] and view['traces'] == extraction['traces']
        assert [r['normal_t'] for r in view['coefficients']] == series['normal_t']
        assert [r['skew_t'] for r in view['coefficients']] == series['skew_t']
        assert len(view['traces']) == 4
        for name, value in view['diagnostics'].items(): assert value == extraction[name]
        assert view['virtual_work_status'] == 'not_applicable'
    else:
        force, work = report['force'], report['virtual_work']
        expected_status = 'not_performed' if work is None else 'failed' if report.get('status') == 'virtual_work_failed' else 'complete'
        assert view['virtual_work_status'] == expected_status
        assert view['virtual_work'] == work and view['work_comparison'] == report['stress_virtual_work_comparison']
        assert view['body_region_ids'] == force['body_region_ids'] and view['convention'] == force['conventions']
        if 'force_xy_n_per_m' in force:
            assert [q['value'] for q in view['quantities']] == [*force['force_xy_n_per_m'], force['torque_z_nm_per_m'], force['nodal_rotation_stress_torque_z_nm_per_m']]
            assert [q['unit'] for q in view['quantities']] == ['N/m', 'N/m', 'N m/m', 'N m/m']
            assert view['origin_xy_m'] == force['origin_xy_m'] and view['work_potential_unit'] == 'J/m'
        else:
            assert [q['value'] for q in view['quantities']] == [force['force_z_n']]
            assert [q['unit'] for q in view['quantities']] == ['N'] and view['work_potential_unit'] == 'J'
            assert view['origin_xy_m'] is None
        for name, value in view['diagnostics'].items(): assert value == force[name]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(); out = args.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic(); before = fingerprints(); rows = selected_references(args.reference_root.resolve())
    reference_hashes = {}
    for row in rows:
        for path in [Path(row['report']), *Path(row['source']).iterdir()]:
            reference_hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    (out / 'cases.json').write_text(json.dumps([{k:v for k,v in row.items() if k not in ('data','case')} for row in rows], indent=2) + '\n')
    from superfish_ng.config import Case
    from superfish_ng.project import Project
    Project(Case(profile=((0., .1), (.12, .1)), nr=8, nz=10, modes=2, element_order=2,
                 name='synthetic magnetic GUI RF regression pillbox')).save(out / 'rf-project.json')
    manager = JobManager(out / 'workspace'); access = MagneticReportAccess(manager)
    identifiers, owned, records = [], {}, []
    def call(action, **data): return magnetic_report_response(manager, access, action, data)[0]
    def ready(identifier):
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            result = call('magnetic-report-result', id=identifier)
            if result['status'] != 'verifying':
                assert result['status'] == 'ready', result
                return result['view']
            time.sleep(.02)
        raise AssertionError('asynchronous magnetic replay timed out')
    try:
        for index, row in enumerate(rows):
            identifier = call('magnetic-report-import', source=row['source'], report=row['report'])['id']
            identifiers.append(identifier)
            assert manager.processes[identifier].wait(timeout=300) == 0, (manager.directory(identifier) / 'log.txt').read_text()
            view = ready(identifier); compare_view(view, row)
            directory = manager.directory(identifier); owned[identifier] = magnetic_report_job_hashes(directory)
            output = out / f'case-{index:02d}'; output.mkdir()
            for name in ['report.json', 'request.json', *('source/' + n for n in view['source_native_sha256'])]:
                raw = call('magnetic-report-download', id=identifier, file=name)
                assert raw == (directory / name).read_bytes()
                target = output / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
                if name == 'report.json': assert raw == Path(row['report']).read_bytes()
                elif name.startswith('source/'): assert raw == (Path(row['source']) / name.removeprefix('source/')).read_bytes()
            (output / 'view.json').write_text(json.dumps(view, indent=2) + '\n')
            records.append(dict(name=row['name'], id=identifier, kind=view['kind'], physics=view['physics'],
                                virtual_work_status=view['virtual_work_status'], full_numbers_and_diagnostics_identical=True,
                                downloaded_files=7, original_report_bytes_identical=True))
            print('DONE', index, row['name'], view['virtual_work_status'], flush=True)
        assert {r['id'] for r in call('magnetic-report-jobs')} == set(identifiers)
        access.close(); manager.close()
        manager = JobManager(out / 'workspace'); access = MagneticReportAccess(manager)
        for row, identifier in zip(rows, identifiers):
            compare_view(ready(identifier), row)
            assert magnetic_report_job_hashes(manager.directory(identifier)) == owned[identifier]
        try: call('magnetic-report-download', id=identifiers[0], file='../job.json')
        except ValueError: pass
        else: raise AssertionError('unlisted download accepted')
    finally:
        access.close(); manager.close()
    for path, digest in reference_hashes.items(): assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
    assert len(reference_hashes) == 120 and fingerprints() == before
    counts = {state: sum(row['virtual_work_status'] == state for row in records)
              for state in ('not_applicable', 'not_performed', 'complete', 'failed')}
    assert counts == dict(not_applicable=6, not_performed=6, complete=6, failed=2)
    result = dict(status='PASS', cases=20, real_import_workers=20, initial_async_replays=20, restart_async_replays=20,
                  downloaded_files=140, reference_files_unchanged=120, owned_job_files_unchanged=180,
                  workflow_counts=counts, records=records, owned_job_sha256=owned,
                  source_sha256=before, seconds=time.monotonic()-started,
                  interpretation='Actual local workers and GUI response API match accepted original FEM reports in full; SI, two torques, four traces, null/complete/real nonlinear failure and all Cases retained. Restart replays all reports. This test does not execute HTTP or a browser and is not continuum accuracy certification.')
    (out / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    print({k:v for k,v in result.items() if k not in ('records','source_sha256','owned_job_sha256')})


if __name__ == '__main__':
    main()
