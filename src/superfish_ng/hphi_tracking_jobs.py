# SPDX-License-Identifier: Apache-2.0
"""Workers and portable copied-native replay for hphi mode correspondence."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
import numpy as np
from .config import keys
from .project import parse_json
from .jobs import _digest, _state, _write_json, _implementation_hashes
from .hphi_jobs import _native_hashes, _job_hashes, verify_hphi_job, NATIVE
from .hphi_native import read_hphi_run
from .hphi_project import HphiProject
from .hphi_tracking import HphiTrackingRequest, track_hphi_modes

KIND = 'hphi_tracking'


def _load(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('hphi tracking metadata must be regular files, not links')
    return parse_json(path.read_text(encoding='utf-8'))


def _input_hashes(directory):
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('hphi tracking directory must be a regular directory')
    result = {}
    for name in ('tracking.json', 'sources.json'):
        _load(directory/name); result[name] = _digest(directory/name)
    for side in ('previous', 'current'):
        point=directory/side
        if point.is_symlink() or not point.is_dir() or {p.name for p in point.iterdir()}!={'project.json','solution','job.json','manifest.json'}:
            raise ValueError('Hphi tracking sides require complete owned imported Hphi jobs')
        result.update({f'{side}/{name}':value for name,value in _job_hashes(point).items()})
    return result


def _snapshot(directory):
    result = _input_hashes(directory)
    for name in ('tracking-results.json', 'manifest.json', 'job.json'):
        _load(directory/name); result[name] = _digest(directory/name)
    return result


def _source(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError('hphi tracking source must not be linked')
    managed = (path/'job.json').exists()
    hashes = _job_hashes(path) if managed else _native_hashes(path)
    if managed:
        solution = verify_hphi_job(path, _load(path/'job.json'), _load(path/'manifest.json'))
        project=HphiProject.load(path/'project.json')
    else:
        solution = read_hphi_run(path)
        project=HphiProject(solution.case)
    if hashes != (_job_hashes(path) if managed else _native_hashes(path)):
        raise ValueError('hphi tracking source changed during verification')
    return (path/'solution' if managed else path), solution, project, dict(
        path=str(path.resolve()), kind='hphi_job' if managed else 'hphi_native', files=hashes)


def _check_sources(document, directory):
    names = ['format', 'sources_version', 'previous', 'current']
    keys(document, names, names, 'hphi tracking sources')
    if document['format'] != 'superfish_ng_hphi_tracking_sources' or type(document['sources_version']) is not int or document['sources_version'] != 1:
        raise ValueError('expected hphi tracking sources version 1')
    for side in ('previous', 'current'):
        source = document[side]
        keys(source, ['path', 'kind', 'files'], ['path', 'kind', 'files'], 'hphi tracking source')
        if type(source['path']) is not str or not source['path'] or source['kind'] not in ('hphi_job', 'hphi_native'):
            raise ValueError('hphi tracking source path/kind is invalid')
        files = source['files']; prefix = 'solution/' if source['kind'] == 'hphi_job' else ''
        expected = {prefix+name for name in NATIVE}
        if prefix: expected |= {'project.json', 'job.json', 'manifest.json'}
        if (type(files) is not dict or set(files) != expected or any(
                type(v) is not str or len(v) != 64 or any(c not in '0123456789abcdef' for c in v) for v in files.values())):
            raise ValueError('hphi tracking source hashes are incomplete or invalid')
        if {name: files[prefix+name] for name in NATIVE} != _native_hashes(directory/side/'solution'):
            raise ValueError('copied hphi native differs from recorded source bytes')
        state=_load(directory/side/'job.json');manifest=_load(directory/side/'manifest.json')
        solution=verify_hphi_job(directory/side,state,manifest);project=HphiProject.load(directory/side/'project.json')
        if (manifest.get('imported_from')!=source['path'] or state.get('origin')!='imported'
                or state.get('source_completion')!=('verified hphi job' if prefix else 'verified hphi native')):
            raise ValueError('owned Hphi tracking side must retain its verified import origin')
        if project.case.to_dict()!=solution.case.to_dict():raise ValueError('Hphi tracking Project differs from its owned original Case')
        if prefix:
            if _digest(directory/side/'project.json')!=files['project.json']:raise ValueError('copied Hphi Project differs from recorded source bytes')
        elif project.to_dict()!=HphiProject(solution.case).to_dict():
            raise ValueError('native source must use the explicit default Project for its saved Case')


def is_hphi_tracking(directory, state, manifest):
    if KIND in (state.get('kind'), manifest.get('kind')): return True
    for name in ('tracking.json', 'tracking-results.json'):
        if (directory/name).is_file():
            data = _load(directory/name)
            if isinstance(data, dict) and data.get('format') in ('superfish_ng_hphi_tracking_request', 'superfish_ng_hphi_tracking_result'):
                return True
    return False


def verify_hphi_tracking(directory, state, manifest):
    directory = Path(directory); before = _snapshot(directory)
    if state.get('status') != 'complete' or state.get('kind') != KIND or manifest.get('kind') != KIND:
        raise ValueError('hphi tracking state and manifest require complete kind=hphi_tracking')
    names = ['manifest_version', 'kind', 'files', 'implementation_sha256', 'source_changed_during_run']
    keys(manifest, names, names, 'hphi tracking manifest')
    implementation = manifest['implementation_sha256']
    if (type(manifest['manifest_version']) is not int or manifest['manifest_version'] != 1
            or type(implementation) is not dict or not implementation
            or any(type(k) is not str or type(v) is not str or len(v) != 64
                   or any(c not in '0123456789abcdef' for c in v) for k, v in implementation.items())
            or manifest['source_changed_during_run'] is not False):
        raise ValueError('hphi tracking requires stable implementation provenance')
    if manifest['files'] != {k: v for k, v in before.items() if k not in ('job.json', 'manifest.json')}:
        raise ValueError('hphi tracking manifest must bind the full request and both complete native snapshots')
    _check_sources(_load(directory/'sources.json'), directory)
    request = HphiTrackingRequest.load(directory/'tracking.json')
    solutions = [read_hphi_run(directory/side/'solution') for side in ('previous', 'current')]
    expected = track_hphi_modes(*solutions, request)
    result = _load(directory/'tracking-results.json')
    if json.dumps(result, sort_keys=True, allow_nan=False) != json.dumps(expected, sort_keys=True, allow_nan=False):
        raise ValueError('saved hphi tracking differs from full native E/H-field and spectral-resolution replay')
    if (state.get('input_sha256') != _input_hashes(directory)
            or state.get('physics') != 'axisymmetric_hphi_rf' or state.get('numerical_validation') != result['status']
            or type(state.get('individual_ids_complete')) is not bool
            or state['individual_ids_complete'] != result['individual_ids_complete']):
        raise ValueError('hphi tracking state differs from the verified correspondence')
    if _snapshot(directory) != before or _load(directory/'job.json') != state or _load(directory/'manifest.json') != manifest:
        raise ValueError('hphi tracking changed during verification')
    return result


def read_hphi_tracking(directory):
    directory = Path(directory)
    return verify_hphi_tracking(directory, _load(directory/'job.json'), _load(directory/'manifest.json'))


def _prepare(previous, current, request, directory):
    if not isinstance(request, HphiTrackingRequest): raise ValueError('expected HphiTrackingRequest')
    request = HphiTrackingRequest.from_dict(request.to_dict())
    sources = [_source(path) for path in (previous, current)]
    cases = [source[1].case for source in sources]
    from .hphi_field_overlap import _declared_mesh
    from .hphi_spectral_resolution import _maximum_edge
    from .meridional_overlap import meridional_overlay
    original=[_declared_mesh(source[1]) for source in sources]
    controls=request.controls
    for case,count,old,fine,order in zip(cases,(request.previous_mode_count,request.current_mode_count),original,
            (request.previous_comparison_mesh,request.current_comparison_mesh),
            (request.previous_comparison_order,request.current_comparison_order)):
        if count>=case.modes:raise ValueError('tracked band requires a computed upper guard mode')
        if case.modes>controls.max_gram_modes:raise ValueError('Hphi tracking exceeds max_gram_modes')
        if type(old) is not type(fine):raise ValueError('Hphi comparison mesh has a different scalar unknown')
        if order<case.element_order or len(fine.triangles)<=len(old.triangles) or _maximum_edge(fine)>=_maximum_edge(old):
            raise ValueError('comparison requires at least the original order, more triangles and smaller maximum edges')
        for declared,p in ((old,case.element_order),(fine,order)):
            dofs=len(declared.points_rz_m)
            if p==2:dofs+=len(np.unique(np.sort(declared.triangles[:,[[0,1],[1,2],[2,0]]].reshape(-1,2),axis=1),axis=0))
            if dofs>controls.max_dofs:raise ValueError('Hphi tracking comparison exceeds max_dofs')
        meridional_overlay(old,fine,max_candidate_tests=controls.max_candidate_tests,max_overlay_triangles=controls.max_overlay_triangles)
    meridional_overlay(*original,max_candidate_tests=controls.max_candidate_tests,max_overlay_triangles=controls.max_overlay_triangles)
    source_document = dict(format='superfish_ng_hphi_tracking_sources', sources_version=1,
                           previous=sources[0][3], current=sources[1][3])
    raw = json.dumps(request.to_dict(), ensure_ascii=False, indent=2, allow_nan=False)+'\n'
    source_raw = json.dumps(source_document, ensure_ascii=False, indent=2, allow_nan=False)+'\n'
    expected = {'tracking.json': hashlib.sha256(raw.encode()).hexdigest(),
                'sources.json': hashlib.sha256(source_raw.encode()).hexdigest()}
    directory.mkdir(parents=True, exist_ok=False)
    try:
        request.save(directory/'tracking.json'); _write_json(directory/'sources.json', source_document)
        for side, (native, _, project, descriptor) in zip(('previous', 'current'), sources):
            (directory/side).mkdir()
            (directory/side/'solution').mkdir()
            if descriptor['kind']=='hphi_job':shutil.copyfile(native.parent/'project.json',directory/side/'project.json')
            else:project.save(directory/side/'project.json')
            for name in sorted(NATIVE): shutil.copyfile(native/name, directory/side/'solution'/name)
            prefix = 'solution/' if descriptor['kind'] == 'hphi_job' else ''
            if prefix and _digest(directory/side/'project.json')!=descriptor['files']['project.json']:
                raise ValueError('Hphi source Project changed during copying')
            if _native_hashes(directory/side/'solution')!={name:descriptor['files'][prefix+name] for name in NATIVE}:
                raise ValueError('Hphi source native changed during copying')
            from .hphi_jobs import _complete
            _complete(directory/side,project,project_hash=_digest(directory/side/'project.json'),started=time.monotonic(),
                imported_from=descriptor['path'],source_completion='verified hphi job' if prefix else 'verified hphi native')
            expected.update({f'{side}/{name}':value for name,value in _job_hashes(directory/side).items()})
        for _, _, _, descriptor in sources:
            path = Path(descriptor['path'])
            if descriptor['files'] != (_job_hashes(path) if descriptor['kind'] == 'hphi_job' else _native_hashes(path)):
                raise ValueError('hphi tracking source changed during snapshot copy')
        if _input_hashes(directory) != expected: raise ValueError('hphi tracking prepared inputs changed during copying')
        _state(directory, 'queued', kind=KIND, input_sha256=expected)
    except Exception as exc:
        _state(directory, 'failed', kind=KIND, error=str(exc)); raise


def execute_prepared_hphi_tracking(directory):
    directory = Path(directory); state = _load(directory/'job.json'); started = time.monotonic()
    if directory.is_symlink() or state.get('status') != 'queued' or state.get('kind') != KIND:
        raise ValueError('hphi tracking worker requires a fresh queued hphi_tracking job')
    with (directory/'worker.claim').open('x') as stream: stream.write(str(os.getpid())+'\n')
    try:
        inputs = _input_hashes(directory); implementation = _implementation_hashes()
        if inputs != state.get('input_sha256'): raise ValueError('queued hphi tracking inputs changed')
        _state(directory, 'running', kind=KIND, input_sha256=inputs, stage='integrating electric and magnetic fields and checking spectral resolution')
        _check_sources(_load(directory/'sources.json'), directory)
        result = track_hphi_modes(*(read_hphi_run(directory/side/'solution') for side in ('previous', 'current')),
                                    HphiTrackingRequest.load(directory/'tracking.json'))
        if inputs != _input_hashes(directory) or implementation != _implementation_hashes():
            raise ValueError('hphi tracking input or implementation changed during execution')
        _write_json(directory/'tracking-results.json', result)
        _write_json(directory/'manifest.json', dict(manifest_version=1, kind=KIND,
            files={**inputs, 'tracking-results.json': _digest(directory/'tracking-results.json')},
            implementation_sha256=implementation, source_changed_during_run=False))
        _state(directory, 'complete', kind=KIND, input_sha256=inputs, stage='saved E/H-field correspondence', physics='axisymmetric_hphi_rf',
               numerical_validation=result['status'], individual_ids_complete=result['individual_ids_complete'],
               elapsed_seconds=time.monotonic()-started)
        result = read_hphi_tracking(directory)
        if inputs != _input_hashes(directory) or implementation != _implementation_hashes():
            raise ValueError('hphi tracking input or implementation changed during completion')
        return result
    except Exception as exc:
        _state(directory, 'failed', kind=KIND, error=str(exc), elapsed_seconds=time.monotonic()-started); raise


def execute_hphi_tracking(previous, current, request, directory):
    directory = Path(directory); _prepare(previous, current, request, directory)
    return execute_prepared_hphi_tracking(directory)


def start_hphi_tracking(manager, previous, current, request):
    with manager.lock:
        if manager.closed: raise ValueError('job manager is closed')
        identifier = time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:10]
        directory = manager.directory(identifier); _prepare(previous, current, request, directory)
        try:
            with (directory/'log.txt').open('x') as log:
                manager.processes[identifier] = subprocess.Popen(
                    [sys.executable, '-m', 'superfish_ng.hphi_tracking_jobs', str(directory)],
                    stdout=log, stderr=subprocess.STDOUT, env={**os.environ, 'OPENBLAS_NUM_THREADS': '1'})
        except Exception as exc:
            _state(directory, 'failed', kind=KIND, error=str(exc)); raise
        return identifier


if __name__ == '__main__':
    if len(sys.argv) != 2: raise SystemExit('usage: python -m superfish_ng.hphi_tracking_jobs PREPARED_DIRECTORY')
    execute_prepared_hphi_tracking(sys.argv[1])
