# SPDX-License-Identifier: Apache-2.0
"""Compare static Study GUI transport with accepted original native fields and failures."""
import argparse
import hashlib
import importlib
import json
from pathlib import Path
import sys
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
from scripts.validate_static_field_project import fingerprints
from scripts.validate_static_field_gui import units
from superfish_ng.static_field_project import StaticFieldProject
from superfish_ng.static_field_study import StaticFieldStudy
from scripts.validate_static_field_study_jobs import expected_summary, neutral_native
from scripts.validate_static_field_jobs import failure_references
from superfish_ng.gui_static_field_studies import StaticFieldStudyAccess, static_field_study_response
from superfish_ng.jobs import JobManager


def canonical(value): return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def reference_view(point, directory):
    result = point['result']; project = StaticFieldProject.from_dict(result['project']); case = project.case
    from superfish_ng.static_field_project import static_case_families
    family = next(value for value in static_case_families() if value['case_format'] == case.to_dict()['format'])
    planar = family['coordinates'] == 'cartesian_xy'; plot = None
    if result['status'] == 'complete':
        name = type(case).__module__.rsplit('.', 1)[-1]; saved = importlib.import_module('superfish_ng.' + name + '_saved')
        solution = getattr(saved, 'read_' + name + '_run')(directory / 'solution')
        mesh = case.partition.mesh; points = mesh.points_xy_m if planar else mesh.points_rz_m
        probe = solution.probe_at(points[mesh.triangles].mean(axis=1))
        assert probe['cell_indices'] == list(range(len(mesh.triangles)))
        plot = dict(points_m=points.tolist(), triangles=mesh.triangles.tolist(), boundary_edges=mesh.boundary_edges.tolist(),
                    coordinate_labels=['x', 'y'] if planar else ['r', 'z'], cell_center_probe=probe,
                    field_units={field: units(field) for field in probe['fields']})
    return dict(project=result['project'], outcome=result['outcome'], solver_status=result['status'], family=family,
                measure='per_unit_length' if planar else 'full_axisymmetric_domain', plot=plot,
                not_applicable=['RF frequency', 'R/Q (circuit)', 'R/Q (accelerator)', 'RF mode index'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-reference', required=True, type=Path)
    parser.add_argument('--reference-root', required=True, type=Path); parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args(); reference = args.input_reference.resolve(); out = args.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    reference_report = json.loads((reference / 'report.json').read_text())
    assert reference_report['status'] == 'PASS' and reference_report['derived_points'] == 165 and reference_report['actual_failure_points'] == 0
    started = time.monotonic(); before = fingerprints(); old = {}; owned = {}; records = []; browser_cases = []; downloads = 0; coverage = set()
    def remember(directory, hashes):
        for path in sorted(directory.rglob('*')):
            if path.is_file():
                name = str(path); digest = hashlib.sha256(path.read_bytes()).hexdigest()
                if name in hashes: assert hashes[name] == digest
                else: hashes[name] = digest
    inputs = []
    for path in sorted(reference.glob('*/api.json')):
        study = StaticFieldStudy.load(path); natives = [path.parent / f'{index}-api-native' for index in range(len(study.values))]
        remember(path.parent, old); inputs.append((path.parent.name, study, natives, str(path)))
    assert len(inputs) == 66 and sum(len(study.values) for _, study, _, _ in inputs) == 165
    for index, (family, directory, case, _) in enumerate(failure_references(args.reference_root.resolve())):
        study = StaticFieldStudy(StaticFieldProject.from_dict(case), 'uniform_scale', (1., 1.))
        remember(directory, old); inputs.append((f'failure-{index}-{family}', study, [directory, directory], None))
    for family in ('planar_bh', 'axis_bh', 'off_axis_bh'):
        factory = getattr(importlib.import_module('scripts.' + family + '_reference'), 'radial_field' if family == 'off_axis_bh' else 'uniform_field')
        study = StaticFieldStudy(StaticFieldProject(factory(n=2)[0], 'm'), 'excitation_scale', (0., 1., 1000.))
        directory = out / ('neutral-' + family); directory.mkdir(); natives = []
        for index, project in enumerate(study.projects()):
            native = directory / str(index); neutral_native(project, native); natives.append(native)
        expected = expected_summary(study, natives); assert expected['successful_points'] == 2 and expected['nonlinear_failed_points'] == 1
        remember(directory, owned); inputs.append(('mixed-' + family, study, natives, None))
    assert len(inputs) == 78 and sum(len(study.values) for _, study, _, _ in inputs) == 192
    # Expected data comes from the original point natives, without executing any Study workflow.
    reference_directory = out / 'original-native-references'; reference_directory.mkdir()
    references = []
    for index, (name, study, natives, input_path) in enumerate(inputs):
        source = reference_directory / f'{index:02d}'; source.mkdir(); study.save(source / 'study.json')
        original = expected_summary(study, natives)
        for point, project, native in zip(original['points'], study.projects(), natives):
            assert canonical(project.case.to_dict()) == canonical(json.loads((native / 'case.json').read_text()))
            target = source / point['directory']; target.mkdir(); project.save(target / 'project.json')
            shutil.copytree(native, target / 'solution')
            assert {p.name: p.read_bytes() for p in native.iterdir()} == {p.name: p.read_bytes() for p in (target / 'solution').iterdir()}
        (source / 'study-results.json').write_text(json.dumps(original, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
        (source / 'reference-provenance.json').write_text(json.dumps(dict(input_path=input_path, original_point_native_directories=[str(p) for p in natives],
            interpretation='Expected Study summary assembled from original native Case/outcomes, not a Study execution or worker PASS report.'), indent=2) + '\n')
        remember(source, owned); references.append(dict(name=name, source=source, summary=original, study=study))
    print('REFERENCE READY', len(references), 'Studies with 192 original native points', flush=True)
    manager = JobManager(out / 'workspace'); access = StaticFieldStudyAccess(manager)
    def call(action, **data): return static_field_study_response(manager, access, action, data)[0]
    def ready(identifier, index=None):
        end = time.monotonic() + 900
        while time.monotonic() < end:
            result = call('static-study-result', id=identifier) if index is None else call('static-study-point', id=identifier, index=index)
            if result['status'] == 'ready': return result
            assert result['status'] in ('queued', 'running', 'verifying'), result
            time.sleep(.05)
        raise AssertionError(('static Study async display timeout', identifier, index))
    def check_view(actual, expected):
        actual = json.loads(canonical(actual))
        if actual['plot'] is not None:
            assert actual['plot'].pop('interpretation').startswith('Original one-sided FEM values')
        assert canonical(actual) == canonical(expected)
    try:
        for index, row in enumerate(references):
            source = row['source']; original = row['summary']; study = row['study']; raw = (source / 'study.json').read_bytes()
            case_metadata = original['study']['project']['case']
            coverage.add((case_metadata['format'], case_metadata['element_order'], original['study']['parameter']))
            assert canonical(call('static-study-validate', document=raw.decode(), display_length_unit=None)) == canonical(original['study'])
            assert call('static-study-download-input', document=raw.decode(), display_length_unit=None) == raw
            for unit in ('m', 'mm'):
                changed = call('static-study-validate', document=raw.decode(), display_length_unit=unit)
                expected = json.loads(canonical(original['study'])); expected['project']['display_length_unit'] = unit
                assert canonical(changed) == canonical(expected)
            identifier = call('static-study-solve', document=raw.decode(), display_length_unit=None)['id']
            result = ready(identifier); manager.processes[identifier].wait(timeout=900)
            assert canonical(result['summary']) == canonical(original)
            directory = manager.directory(identifier); views = []
            expected_files = ['study.json', 'study-results.json']
            for point in original['points']:
                prefix = point['directory']; expected = reference_view(point, source / prefix)
                displayed = ready(identifier, point['index']); assert canonical(displayed['point']) == canonical(point)
                check_view(displayed['view'], expected); views.append(displayed['view'])
                point_files = [prefix + '/project.json'] + [prefix + '/solution/' + path.name for path in sorted((source / prefix / 'solution').iterdir())]
                assert displayed['files'] == sorted(point_files); expected_files.extend(point_files)
            assert result['files'] == sorted(expected_files)
            for name in result['files']:
                assert call('static-study-download', id=identifier, file=name) == (source / name).read_bytes(); downloads += 1
            remember(directory, owned)
            views_file = out / f'{index:02d}-views.json'; views_file.write_text(json.dumps(views, indent=2) + '\n')
            summary_file = out / f'{index:02d}-summary.json'; summary_file.write_text(json.dumps(original, indent=2) + '\n')
            browser_cases.append(dict(name=row['name'], source_job=str(source), study_file=str(source / 'study.json'),
                                      expected_summary_file=str(summary_file), expected_views_file=str(views_file)))
            records.append(dict(name=row['name'], id=identifier, points=len(original['points']), successful_points=original['successful_points'],
                                nonlinear_failed_points=original['nonlinear_failed_points'], files=result['files']))
            print('DONE', index, row['name'], len(views), 'point views', flush=True)
    finally: access.close(); manager.close()
    manager = JobManager(out / 'workspace'); access = StaticFieldStudyAccess(manager); restart_downloads = 0
    try:
        for index, row in enumerate(records):
            result = ready(row['id']); source = references[index]['source']
            assert canonical(result['summary']) == canonical(json.loads((out / f'{index:02d}-summary.json').read_text()))
            views = json.loads((out / f'{index:02d}-views.json').read_text()); assert result['files'] == row['files']
            for point_index, expected in enumerate(views): assert canonical(ready(row['id'], point_index)['view']) == canonical(expected)
            for name in row['files']:
                assert call('static-study-download', id=row['id'], file=name) == (source / name).read_bytes(); restart_downloads += 1
            remember(manager.directory(row['id']), owned)
            print('RESTART', index, row['name'], flush=True)
    finally: access.close(); manager.close()
    from superfish_ng.static_field_project import static_case_families
    expected_coverage = {(row['case_format'], order, parameter) for row in static_case_families()
                         for order in row['element_orders'] for parameter in ('uniform_scale', 'excitation_scale')}
    assert coverage == expected_coverage and len(coverage) == 38
    assert downloads == restart_downloads == 1266
    assert sum(row['points'] for row in records) == 192 and sum(row['nonlinear_failed_points'] for row in records) == 21
    for hashes in (old, owned):
        for path, digest in hashes.items(): assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
    assert before == fingerprints()
    (out / 'cases.json').write_text(json.dumps(browser_cases, indent=2) + '\n')
    from superfish_ng.config import Case
    from superfish_ng.project import Project
    Project(Case(profile=((0., .1), (.12, .1)), nr=8, nz=10, modes=2, element_order=2)).save(out / 'rf-project.json')
    from scripts.axis_bh_reference import current_cylinder
    project = StaticFieldProject(current_cylinder(n=16, quadrature_order=32)[0], 'mm')
    StaticFieldStudy(project, 'excitation_scale', (1., 2.)).save(out / 'cancel-study.json')
    report = dict(status='PASS', reference_kind='original_input_and_point_native_outcomes', reference_input_studies=66, source_failure_studies=9, mixed_studies=3, studies=78, points=192, successful_points=171, actual_nonlinear_failure_points=21, case_families=len({row[0] for row in coverage}), family_order_parameter_combinations=len(coverage),
                  real_gui_workers=78, initial_async_study_replays=78, restart_async_study_replays=78,
                  initial_async_point_views=192, restart_async_point_views=192, initial_downloads=downloads, restart_downloads=restart_downloads,
                  original_files_unchanged=len(old), owned_files_unchanged=len(owned), reference_bundle=str(reference_directory), source_sha256=before,
                  records=[{key: value for key, value in row.items() if key != 'files'} for row in records], seconds=time.monotonic() - started,
                  interpretation='GUI transport preserves every accepted static Study point, original material cell-center FEM field and full actual failure history. Browser rendering and target compatibility require separate evidence.')
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n'); print({key: value for key, value in report.items() if key not in ('source_sha256', 'records')})


if __name__ == '__main__': main()
