# SPDX-License-Identifier: Apache-2.0
"""Run dedicated static FEM Projects with verified success or nonlinear failure."""
import hashlib
import importlib
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from .config import keys
from .project import parse_json
from .static_field_project import StaticFieldProject, static_case_families
from .nonlinear_magnetic import MagneticNonlinearFailure
from .planar_magnetic_multipole_saved import _canonical, _report_bytes

KIND = 'static_field_solve'
PROJECT_FORMAT = 'superfish_ng_static_field_project'
CASE_FORMATS = {row['case_format'] for row in static_case_families()}
SUCCESS_FILES = {'case.json', 'results.json', 'fields.npz', 'mesh.npz', 'manifest.json'}
FAILURE_FILES = {'case.json', 'failure.json', 'manifest.json'}


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _bindings(case):
    # Project validation fixes the exact Case type before module dispatch.
    case = StaticFieldProject(case).case
    name = type(case).__module__.rsplit('.', 1)[-1]
    model = importlib.import_module('superfish_ng.' + name)
    saved = importlib.import_module('superfish_ng.' + name + '_saved')
    solver = getattr(model, 'solve_axisymmetric_electrostatic' if name == 'electrostatic' else 'solve_' + name)
    return name, solver, saved


def _solve(case):
    return _bindings(case)[1](case)


def _native_bytes(directory, failed):
    directory = Path(directory)
    names = FAILURE_FILES if failed else SUCCESS_FILES
    if (directory.is_symlink() or not directory.is_dir()
            or {p.name for p in directory.iterdir()} != names):
        raise ValueError('static job requires exactly the dedicated success or failure native files in a regular directory')
    return {name: _report_bytes(directory / name) for name in sorted(names)}


def _job_hashes(directory, failed):
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('static job requires a regular directory')
    native = _native_bytes(directory / 'solution', failed)
    return {**{'solution/' + n: _sha(raw) for n, raw in native.items()},
            **{n: _sha(_report_bytes(directory / n)) for n in ('project.json', 'job.json', 'manifest.json')}}


def is_static_field_job(directory, state, manifest=None):
    if state.get('kind') == KIND or (manifest or {}).get('kind') == KIND:
        return True
    for name in ('project.json', 'solution/case.json'):
        path = Path(directory) / name
        if path.is_file():
            data = parse_json(_report_bytes(path).decode('utf-8'))
            if isinstance(data, dict) and type(data.get('format')) is str:
                if data['format'] == PROJECT_FORMAT or data['format'] in CASE_FORMATS:
                    return True
    return False


def _outcome(directory, project, failed):
    name, _, saved = _bindings(project.case)
    case = parse_json(_report_bytes(Path(directory) / 'case.json').decode('utf-8'))
    if _canonical(case) != _canonical(project.case.to_dict()):
        raise ValueError('static native Case differs from the submitted Project')
    if failed:
        if not name.endswith('_bh'):
            raise ValueError('only a dedicated B-H solver can retain a nonlinear failure')
        return getattr(saved, 'read_' + name + '_failure')(directory)
    solution = getattr(saved, 'read_' + name + '_run')(directory)
    return getattr(saved, name + '_result')(solution)


def read_static_field_job(directory):
    """Replay the original dedicated FEM, including a saved actual failure."""
    directory = Path(directory)
    state = parse_json(_report_bytes(directory / 'job.json').decode('utf-8'))
    manifest = parse_json(_report_bytes(directory / 'manifest.json').decode('utf-8'))
    names = ['manifest_version', 'kind', 'outcome', 'files', 'implementation_sha256', 'source_changed_during_run']
    keys(manifest, names, names, 'static job completion manifest')
    failed = manifest['outcome'] == 'nonlinear_failed'
    if (type(manifest['manifest_version']) is not int or manifest['manifest_version'] != 1
            or manifest['kind'] != KIND or manifest['outcome'] not in ('complete', 'nonlinear_failed')
            or state.get('kind') != KIND or state.get('status') != ('failed' if failed else 'complete')
            or state.get('solver_status') != manifest['outcome'] or state.get('outcome_saved') is not True):
        raise ValueError('static job requires matching dedicated kind, saved outcome and terminal status')
    before = _job_hashes(directory, failed)
    required = {n: h for n, h in before.items() if n not in ('job.json', 'manifest.json')}
    if manifest['files'] != required or state.get('project_sha256') != before['project.json']:
        raise ValueError('static job output integrity failure')
    implementation = manifest['implementation_sha256']
    if (not isinstance(implementation, dict) or not implementation
            or any(type(n) is not str or type(h) is not str or len(h) != 64
                   or any(c not in '0123456789abcdef' for c in h) for n, h in implementation.items())
            or manifest['source_changed_during_run'] is not False):
        raise ValueError('static job requires stable implementation provenance')
    project = StaticFieldProject.load(directory / 'project.json')
    case = project.case.to_dict()
    if (state.get('case_format') != case['format'] or state.get('physics') != case['physics']
            or type(state.get('element_order')) is not int or state['element_order'] != case['element_order']
            or state.get('numerical_validation') != 'not_checked'):
        raise ValueError('static job summary differs from its Project')
    outcome = _outcome(directory / 'solution', project, failed)
    if (parse_json(_report_bytes(directory / 'job.json').decode('utf-8')) != state
            or parse_json(_report_bytes(directory / 'manifest.json').decode('utf-8')) != manifest
            or _job_hashes(directory, failed) != before):
        raise ValueError('static job changed during dedicated FEM replay')
    return dict(format='superfish_ng_static_field_project_result', schema_version=1,
                status=manifest['outcome'], project=project.to_dict(), outcome=outcome)


def _prepare(project, directory):
    from .jobs import _state
    if type(project) is not StaticFieldProject:
        raise ValueError('expected a dedicated StaticFieldProject')
    project = StaticFieldProject.from_dict(project.to_dict())
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    project.save(directory / 'project.json')
    _state(directory, 'queued', kind=KIND, project_sha256=_sha(_report_bytes(directory / 'project.json')))


def execute_prepared_static_field_project(directory):
    from .jobs import _state, _write_json, _implementation_hashes
    directory = Path(directory)
    if directory.is_symlink():
        raise ValueError('prepared static job must not be linked')
    state = parse_json(_report_bytes(directory / 'job.json').decode('utf-8'))
    if state.get('kind') != KIND or state.get('status') != 'queued':
        raise ValueError('static worker requires a new queued dedicated job')
    with (directory / 'worker.claim').open('x') as stream:
        stream.write(str(os.getpid()) + '\n')
    started = time.monotonic()
    try:
        implementation = _implementation_hashes()
        raw = _report_bytes(directory / 'project.json')
        if _sha(raw) != state.get('project_sha256'):
            raise ValueError('static Project changed after submission')
        project = StaticFieldProject.from_dict(parse_json(raw.decode('utf-8')))
        name, _, saved = _bindings(project.case)
        _state(directory, 'running', kind=KIND, stage='dedicated static finite element solve')
        failed = False
        try:
            solution = _solve(project.case)
        except MagneticNonlinearFailure as failure:
            if not name.endswith('_bh'):
                raise
            failed = True
            _state(directory, 'running', kind=KIND, stage='saving and reproducing nonlinear failure')
            getattr(saved, 'save_' + name + '_failure')(project.case, failure, directory / 'solution')
        else:
            _state(directory, 'running', kind=KIND, stage='saving original static fields and integrals')
            getattr(saved, 'save_' + name + '_run')(project.case, solution, directory / 'solution')
        native = _native_bytes(directory / 'solution', failed)
        outcome = _outcome(directory / 'solution', project, failed)
        if (_report_bytes(directory / 'project.json') != raw
                or _native_bytes(directory / 'solution', failed) != native):
            raise ValueError('static Project or native output changed during completion')
        if _implementation_hashes() != implementation:
            raise ValueError('implementation changed during static execution')
        solver_status = 'nonlinear_failed' if failed else 'complete'
        files = {'project.json': _sha(raw), **{'solution/' + n: _sha(b) for n, b in native.items()}}
        _write_json(directory / 'manifest.json', dict(manifest_version=1, kind=KIND, outcome=solver_status,
                    files=files, implementation_sha256=implementation, source_changed_during_run=False))
        case = project.case.to_dict()
        _state(directory, 'failed' if failed else 'complete', kind=KIND, solver_status=solver_status,
               outcome_saved=True, project_sha256=_sha(raw), physics=case['physics'], case_format=case['format'],
               element_order=case['element_order'], numerical_validation='not_checked',
               stage='saved reproducible nonlinear failure' if failed else 'saved static fields and integrals',
               elapsed_seconds=time.monotonic() - started)
        return dict(format='superfish_ng_static_field_project_result', schema_version=1,
                    status=solver_status, project=project.to_dict(), outcome=outcome)
    except Exception as exc:
        _state(directory, 'failed', kind=KIND, outcome_saved=False, error=str(exc),
               elapsed_seconds=time.monotonic() - started)
        raise


def execute_static_field_project(project, directory):
    _prepare(project, directory)
    return execute_prepared_static_field_project(directory)


def start_static_field(manager, project):
    from .jobs import _state
    with manager.lock:
        if manager.closed:
            raise ValueError('job manager is closed')
        identifier = time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:10]
        directory = manager.directory(identifier)
        _prepare(project, directory)
        try:
            with (directory / 'log.txt').open('x') as log:
                process = subprocess.Popen([sys.executable, '-m', 'superfish_ng.static_field_jobs', str(directory)],
                    stdout=log, stderr=subprocess.STDOUT, env={**os.environ, 'OPENBLAS_NUM_THREADS': '1'})
            manager.processes[identifier] = process
        except Exception as exc:
            _state(directory, 'failed', kind=KIND, outcome_saved=False, error=str(exc))
            raise
        return identifier


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: python -m superfish_ng.static_field_jobs PREPARED_DIRECTORY')
    result = execute_prepared_static_field_project(Path(sys.argv[1]))
    raise SystemExit(1 if result['status'] == 'nonlinear_failed' else 0)
