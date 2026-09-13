# SPDX-License-Identifier: Apache-2.0
"""Independent static Study workers retaining every successful or failed FEM point."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from .config import keys
from .project import parse_json
from .static_field_study import StaticFieldStudy
from .static_field_jobs import execute_static_field_project, read_static_field_job, _job_hashes
from .planar_magnetic_multipole_saved import _canonical, _report_bytes
from .jobs import _digest, _implementation_hashes, _state, _write_json

KIND = 'static_field_study'
FORMAT = 'superfish_ng_static_field_study_result'


def _load(path):
    return parse_json(_report_bytes(path).decode('utf-8'))


def is_static_field_study(directory, state, manifest=None):
    if KIND in (state.get('kind'), (manifest or {}).get('kind')): return True
    for name in ('study.json', 'study-results.json'):
        path = Path(directory) / name
        if path.is_file():
            data = _load(path)
            if isinstance(data, dict) and data.get('format') in ('superfish_ng_static_field_study', FORMAT): return True
    return False


def _point_name(index):
    return f'point-{index:04d}'


def _point_hashes(directory):
    manifest = _load(directory / 'manifest.json')
    if not isinstance(manifest, dict) or manifest.get('outcome') not in ('complete', 'nonlinear_failed'):
        raise ValueError('static Study point requires a dedicated success or nonlinear failure manifest')
    return _job_hashes(directory, manifest['outcome'] == 'nonlinear_failed')


def _snapshot(directory, count):
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('static Study requires a regular directory')
    names = ('study.json', 'study-results.json', 'job.json', 'manifest.json')
    result = {name: hashlib.sha256(_report_bytes(directory / name)).hexdigest() for name in names}
    expected = {_point_name(index) for index in range(count)}
    if {path.name for path in directory.iterdir() if path.name.startswith('point-')} != expected:
        raise ValueError('static Study point directories differ from all requested points')
    for name in sorted(expected):
        result.update({name + '/' + key: value for key, value in _point_hashes(directory / name).items()})
    return result


def _summary(study, points):
    successful = sum(point['result']['status'] == 'complete' for point in points)
    return dict(format=FORMAT, schema_version=1, study=study.to_dict(),
                execution_status='complete', all_points_successful=successful == len(points),
                successful_points=successful, nonlinear_failed_points=len(points) - successful,
                mode_tracking='not_applicable', solution_branch_tracking='not_performed',
                numerical_validation='not_checked', points=points)


def _point(index, value, result):
    return dict(index=index, value=value, directory=_point_name(index), result=result)


def read_static_field_study(directory):
    """Rebuild every requested Case and replay every saved dedicated FEM outcome."""
    directory = Path(directory)
    study = StaticFieldStudy.from_dict(_load(directory / 'study.json'))
    state = _load(directory / 'job.json'); manifest = _load(directory / 'manifest.json')
    if not isinstance(state, dict): raise ValueError('static Study Job state must be a JSON object')
    before = _snapshot(directory, len(study.values))
    if state.get('status') != 'complete' or state.get('kind') != KIND or state.get('outcome_saved') is not True:
        raise ValueError('static Study requires complete execution; successful points alone do not complete an interrupted Study')
    names = ['manifest_version', 'kind', 'files', 'implementation_sha256', 'source_changed_during_run']
    keys(manifest, names, names, 'static Study completion manifest')
    if type(manifest['manifest_version']) is not int or manifest['manifest_version'] != 1 or manifest['kind'] != KIND:
        raise ValueError('static Study manifest requires version 1 and kind=static_field_study')
    expected = {name: value for name, value in before.items() if name not in ('job.json', 'manifest.json')}
    if manifest['files'] != expected or state.get('study_sha256') != before['study.json']:
        raise ValueError('static Study manifest must bind the complete input, summary, point Projects and native files')
    implementation = manifest['implementation_sha256']
    if (not isinstance(implementation, dict) or not implementation
            or any(type(name) is not str or type(value) is not str or len(value) != 64
                   or any(c not in '0123456789abcdef' for c in value) for name, value in implementation.items())
            or manifest['source_changed_during_run'] is not False):
        raise ValueError('static Study requires stable implementation provenance')
    points = []
    for index, (value, project) in enumerate(zip(study.values, study.projects())):
        point = directory / _point_name(index)
        result = read_static_field_job(point)
        if _canonical(result['project']) != _canonical(project.to_dict()):
            raise ValueError('static Study point Project differs from its requested parameter value')
        if _load(point / 'manifest.json')['implementation_sha256'] != implementation or _load(point / 'job.json').get('origin') is not None:
            raise ValueError('static Study point must retain the same executed implementation provenance')
        points.append(_point(index, value, result))
    result = _summary(study, points)
    if _canonical(_load(directory / 'study-results.json')) != _canonical(result):
        raise ValueError('static Study summary differs from all verified Cases, original quantities or failure histories')
    expected_state = dict(computed_points=len(points), successful_points=result['successful_points'],
                          nonlinear_failed_points=result['nonlinear_failed_points'])
    if any(type(state.get(name)) is not int or state[name] != value for name, value in expected_state.items()):
        raise ValueError('static Study completion counts differ from its verified points')
    case = study.project.case.to_dict()
    if (state.get('all_points_successful') is not result['all_points_successful']
            or state.get('physics') != case['physics'] or state.get('case_format') != case['format']
            or state.get('parameter') != study.parameter or state.get('numerical_validation') != 'not_checked'
            or state.get('solution_branch_tracking') != 'not_performed' or state.get('mode_tracking') != 'not_applicable'):
        raise ValueError('static Study status differs from its independent execution contract')
    if _load(directory / 'job.json') != state or _load(directory / 'manifest.json') != manifest or _snapshot(directory, len(points)) != before:
        raise ValueError('static Study changed during full point replay')
    return result


def _prepare(study, directory):
    if type(study) is not StaticFieldStudy:
        raise ValueError('expected a dedicated StaticFieldStudy')
    study = StaticFieldStudy.from_dict(study.to_dict())
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=False)
    study.save(directory / 'study.json')
    _state(directory, 'queued', kind=KIND, study_sha256=_digest(directory / 'study.json'), outcome_saved=False)


def execute_prepared_static_field_study(directory):
    directory = Path(directory)
    if directory.is_symlink(): raise ValueError('prepared static Study must not be linked')
    state = _load(directory / 'job.json')
    if not isinstance(state, dict): raise ValueError('prepared static Study Job state must be a JSON object')
    if state.get('status') != 'queued' or state.get('kind') != KIND:
        raise ValueError('static Study worker requires a new queued study; use a new output directory')
    with (directory / 'worker.claim').open('x') as stream: stream.write(str(os.getpid()) + '\n')
    started = time.monotonic(); points = []
    try:
        implementation = _implementation_hashes(); raw = _report_bytes(directory / 'study.json')
        source_hash = hashlib.sha256(raw).hexdigest()
        if source_hash != state.get('study_sha256'):
            raise ValueError('static Study input changed after submission')
        study = StaticFieldStudy.from_dict(parse_json(raw.decode('utf-8'))); projects = study.projects()
        point_files = {}
        for index, (value, project) in enumerate(zip(study.values, projects)):
            _state(directory, 'running', kind=KIND, stage=f'point {index + 1}/{len(projects)}', computed_points=index, outcome_saved=False)
            name = _point_name(index); result = execute_static_field_project(project, directory / name)
            points.append(_point(index, value, result))
            point_files.update({name + '/' + key: digest for key, digest in _point_hashes(directory / name).items()})
            if _report_bytes(directory / 'study.json') != raw or _implementation_hashes() != implementation:
                raise ValueError('static Study input or implementation changed during execution')
        result = _summary(study, points); _write_json(directory / 'study-results.json', result)
        files = dict(point_files, **{'study.json': source_hash, 'study-results.json': _digest(directory / 'study-results.json')})
        _write_json(directory / 'manifest.json', dict(manifest_version=1, kind=KIND, files=files,
                    implementation_sha256=implementation, source_changed_during_run=False))
        case = study.project.case.to_dict()
        _state(directory, 'complete', kind=KIND, outcome_saved=True, study_sha256=source_hash,
               stage='saved every independent static outcome', computed_points=len(points),
               all_points_successful=result['all_points_successful'], successful_points=result['successful_points'],
               nonlinear_failed_points=result['nonlinear_failed_points'], physics=case['physics'], case_format=case['format'],
               parameter=study.parameter, mode_tracking='not_applicable', solution_branch_tracking='not_performed',
               numerical_validation='not_checked', elapsed_seconds=time.monotonic() - started)
        verified = read_static_field_study(directory)
        if _report_bytes(directory / 'study.json') != raw or _implementation_hashes() != implementation:
            raise ValueError('static Study input or implementation changed during completion')
        return verified
    except Exception as exc:
        _state(directory, 'failed', kind=KIND, outcome_saved=False, computed_points=len(points),
               error=str(exc), elapsed_seconds=time.monotonic() - started)
        raise


def execute_static_field_study(study, directory):
    _prepare(study, directory)
    return execute_prepared_static_field_study(directory)


def start_static_field_study(manager, study):
    with manager.lock:
        if manager.closed: raise ValueError('job manager is closed')
        identifier = time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:10]
        directory = manager.directory(identifier); _prepare(study, directory)
        try:
            with (directory / 'log.txt').open('x') as log:
                manager.processes[identifier] = subprocess.Popen([sys.executable, '-m', 'superfish_ng.static_field_study_jobs', str(directory)],
                    stdout=log, stderr=subprocess.STDOUT, env={**os.environ, 'OPENBLAS_NUM_THREADS': '1'})
        except Exception as exc:
            _state(directory, 'failed', kind=KIND, outcome_saved=False, error=str(exc)); raise
        return identifier


if __name__ == '__main__':
    if len(sys.argv) != 2: raise SystemExit('usage: python -m superfish_ng.static_field_study_jobs PREPARED_DIRECTORY')
    execute_prepared_static_field_study(Path(sys.argv[1]))
