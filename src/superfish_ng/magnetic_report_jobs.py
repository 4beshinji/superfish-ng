# SPDX-License-Identifier: Apache-2.0
"""Owned magnetic postprocessing reports, verified by their original FEM APIs."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from .config import keys
from .project import parse_json
from .planar_magnetostatic_saved import _snapshot
from .planar_magnetic_multipole_saved import _canonical, _report_bytes

KIND = 'magnetic_report_import'
FORMATS = {
    'superfish_ng_planar_magnetic_multipole_report': (1, 2),
    'superfish_ng_planar_magnetic_force_report': (1, 2),
    'superfish_ng_off_axis_magnetic_force_report': (1,),
}


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _report(path):
    raw = _report_bytes(path)
    value = parse_json(raw.decode('utf-8'))
    if (not isinstance(value, dict) or type(value.get('format')) is not str
            or value['format'] not in FORMATS or type(value.get('schema_version')) is not int
            or value['schema_version'] not in FORMATS[value['format']]):
        raise ValueError('expected a supported magnetic multipole or force report format/version')
    return raw, value


def _replay(source, report):
    _, value = _report(report)
    if value['format'] == 'superfish_ng_planar_magnetic_multipole_report':
        from .planar_magnetic_multipole_saved import replay_planar_magnetic_multipoles
        return replay_planar_magnetic_multipoles(source, report)
    if value['format'] == 'superfish_ng_planar_magnetic_force_report':
        from .planar_magnetic_force_saved import replay_planar_magnetic_force
        return replay_planar_magnetic_force(source, report)
    from .off_axis_magnetic_force_saved import replay_off_axis_magnetic_force
    return replay_off_axis_magnetic_force(source, report)


def _input(source, report):
    source, report = Path(source), Path(report)
    native = _snapshot(source)
    raw, value = _report(report)
    if report.resolve().is_relative_to(source.resolve()):
        raise ValueError('magnetic report must be outside the source native directory')
    request = dict(source_native_path=str(source.resolve()), report_path=str(report.resolve()),
                   source_native_sha256={n: _sha(b) for n, b in sorted(native.items())},
                   report_sha256=_sha(raw))
    return request, native, raw, value


def _request(value):
    names = ['source_native_path', 'report_path', 'source_native_sha256', 'report_sha256']
    keys(value, names, names, 'magnetic report import request')
    for key in ('source_native_path', 'report_path'):
        if type(value[key]) is not str or not Path(value[key]).is_absolute():
            raise ValueError('magnetic report import requires explicit absolute source and report paths')
    hashes = value['source_native_sha256']
    if not isinstance(hashes, dict) or len(hashes) != 5:
        raise ValueError('magnetic report import requires five source native hashes')
    for digest in [value['report_sha256'], *hashes.values()]:
        if type(digest) is not str or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('magnetic report import requires SHA256 digests')
    return value


def magnetic_report_job_hashes(directory):
    """Read every owned input and both metadata files without executing a solver."""
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('magnetic report job requires a regular directory')
    native = _snapshot(directory / 'source')
    result = {'source/' + n: _sha(b) for n, b in sorted(native.items())}
    for name in ('request.json', 'report.json', 'manifest.json', 'job.json'):
        result[name] = _sha(_report_bytes(directory / name))
    return result


def is_magnetic_report_job(directory, state, manifest):
    if state.get('kind') == KIND or manifest.get('kind') == KIND:
        return True
    # Removing both kind markers must not bypass the dedicated verifier.
    path = Path(directory) / 'report.json'
    if path.is_file():
        value = parse_json(_report_bytes(path).decode('utf-8'))
        return isinstance(value, dict) and value.get('format') in FORMATS
    return False


def verify_magnetic_report_job(directory, state=None, manifest=None):
    """Recompute the complete stored report, including actual failed work trials."""
    directory = Path(directory)
    before = magnetic_report_job_hashes(directory)
    actual_state = parse_json(_report_bytes(directory / 'job.json').decode('utf-8'))
    actual_manifest = parse_json(_report_bytes(directory / 'manifest.json').decode('utf-8'))
    if state is not None and _canonical(state) != _canonical(actual_state):
        raise ValueError('magnetic report job state changed during verification')
    if manifest is not None and _canonical(manifest) != _canonical(actual_manifest):
        raise ValueError('magnetic report manifest changed during verification')
    state, manifest = actual_state, actual_manifest
    if state.get('status') != 'complete' or state.get('kind') != KIND or manifest.get('kind') != KIND:
        raise ValueError('magnetic report requires a completed dedicated import job')
    names = ['manifest_version', 'kind', 'files', 'implementation_sha256', 'source_changed_during_run']
    keys(manifest, names, names, 'magnetic report job manifest')
    if type(manifest['manifest_version']) is not int or manifest['manifest_version'] != 1:
        raise ValueError('magnetic report manifest_version must be 1')
    expected_files = {n: digest for n, digest in before.items() if n not in ('job.json', 'manifest.json')}
    if manifest['files'] != expected_files:
        raise ValueError('magnetic report output integrity failure')
    implementation = manifest['implementation_sha256']
    if (not isinstance(implementation, dict) or not implementation
            or any(type(n) is not str or type(h) is not str or len(h) != 64
                   or any(c not in '0123456789abcdef' for c in h) for n, h in implementation.items())
            or manifest['source_changed_during_run'] is not False):
        raise ValueError('magnetic report verification requires stable implementation provenance')
    request = _request(parse_json(_report_bytes(directory / 'request.json').decode('utf-8')))
    native = {n.removeprefix('source/'): h for n, h in before.items() if n.startswith('source/')}
    if request['source_native_sha256'] != native or request['report_sha256'] != before['report.json']:
        raise ValueError('magnetic report owned copy differs from submitted source hashes')
    report = _replay(directory / 'source', directory / 'report.json')
    case = parse_json(_report_bytes(directory / 'source/case.json').decode('utf-8'))
    if (state.get('report_format') != report['format']
            or type(state.get('report_schema_version')) is not int
            or state['report_schema_version'] != report['schema_version']
            or state.get('report_status') != report.get('status', 'complete')
            or state.get('physics') != case['physics']
            or state.get('numerical_validation') != 'not_checked'
            or state.get('source_completion') != 'original FEM report replayed'
            or state.get('origin') != 'imported'):
        raise ValueError('magnetic report job summary differs from its verified report')
    if magnetic_report_job_hashes(directory) != before:
        raise ValueError('magnetic report job changed during FEM replay')
    return report


def execute_prepared_magnetic_report(directory):
    from .jobs import _state, _write_json, _implementation_hashes
    directory = Path(directory)
    if directory.is_symlink():
        raise ValueError('prepared magnetic report directory must not be linked')
    state = parse_json(_report_bytes(directory / 'job.json').decode('utf-8'))
    if state.get('status') != 'queued' or state.get('kind') != KIND:
        raise ValueError('magnetic report worker requires a new queued dedicated job')
    with (directory / 'worker.claim').open('x') as stream:
        stream.write(str(os.getpid()) + '\n')
    started = time.monotonic()
    try:
        implementation = _implementation_hashes()
        request_raw = _report_bytes(directory / 'request.json')
        if _sha(request_raw) != state.get('request_sha256'):
            raise ValueError('magnetic report request changed after submission')
        request = _request(parse_json(request_raw.decode('utf-8')))
        _state(directory, 'running', kind=KIND, stage='copying source-bound report')
        actual, native, raw_report, _ = _input(request['source_native_path'], request['report_path'])
        if actual != request:
            raise ValueError('magnetic source or report changed after submission')
        target = directory / 'source'
        target.mkdir()
        for name, raw in sorted(native.items()):
            with (target / name).open('xb') as stream:
                stream.write(raw)
        with (directory / 'report.json').open('xb') as stream:
            stream.write(raw_report)
        _state(directory, 'running', kind=KIND, stage='replaying original FEM and postprocessing')
        report = _replay(target, directory / 'report.json')
        if _input(request['source_native_path'], request['report_path'])[0] != request:
            raise ValueError('magnetic source or report changed during import verification')
        if (_snapshot(target) != native or _report_bytes(directory / 'report.json') != raw_report
                or _report_bytes(directory / 'request.json') != request_raw):
            raise ValueError('owned magnetic report changed during verification')
        if _implementation_hashes() != implementation:
            raise ValueError('implementation changed during magnetic report verification')
        files = {**{'source/' + n: _sha(b) for n, b in sorted(native.items())},
                 'request.json': _sha(request_raw), 'report.json': _sha(raw_report)}
        _write_json(directory / 'manifest.json', dict(manifest_version=1, kind=KIND, files=files,
                    implementation_sha256=implementation, source_changed_during_run=False))
        case = parse_json(native['case.json'].decode('utf-8'))
        return _state(directory, 'complete', kind=KIND, stage='verified report imported',
                      origin='imported', source_completion='original FEM report replayed',
                      numerical_validation='not_checked', physics=case['physics'],
                      report_format=report['format'], report_schema_version=report['schema_version'],
                      report_status=report.get('status', 'complete'), elapsed_seconds=time.monotonic()-started)
    except Exception as exc:
        _state(directory, 'failed', kind=KIND, error=str(exc), elapsed_seconds=time.monotonic()-started)
        raise


def _prepare(request, directory):
    from .jobs import _state, _write_json
    _request(request)
    directory.mkdir(parents=True, exist_ok=False)
    _write_json(directory / 'request.json', request)
    _state(directory, 'queued', kind=KIND, request_sha256=_sha(_report_bytes(directory / 'request.json')))


def start_magnetic_report(manager, source, report):
    from .jobs import _state
    # No FEM work under the manager lock or in the HTTP request thread.
    request, _, _, _ = _input(source, report)
    with manager.lock:
        if manager.closed:
            raise ValueError('job manager is closed')
        identifier = time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:10]
        directory = manager.directory(identifier)
        _prepare(request, directory)
        try:
            with (directory / 'log.txt').open('x') as log:
                process = subprocess.Popen([sys.executable, '-m', 'superfish_ng.magnetic_report_jobs', str(directory)],
                    stdout=log, stderr=subprocess.STDOUT, env={**os.environ, 'OPENBLAS_NUM_THREADS': '1'})
            manager.processes[identifier] = process
        except Exception as exc:
            _state(directory, 'failed', kind=KIND, error=str(exc))
            raise
        return identifier


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: python -m superfish_ng.magnetic_report_jobs PREPARED_DIRECTORY')
    execute_prepared_magnetic_report(Path(sys.argv[1]))
