# SPDX-License-Identifier: Apache-2.0
"""Workers and portable copied-native replay for planar mode correspondence."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
from .config import keys
from .project import parse_json
from .jobs import _digest, _state, _write_json, _implementation_hashes
from .planar_jobs import _native_hashes, _job_hashes, verify_planar_job, NATIVE
from .planar_saved import read_planar_run
from .planar import PlanarCase
from .planar_tracking import PlanarTrackingRequest, track_planar_modes

KIND = 'planar_tracking'


def _load(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('planar tracking metadata must be regular files, not links')
    return parse_json(path.read_text(encoding='utf-8'))


def _input_hashes(directory):
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('planar tracking directory must be a regular directory')
    result = {}
    for name in ('tracking.json', 'sources.json'):
        _load(directory/name); result[name] = _digest(directory/name)
    for side in ('previous', 'current'):
        result.update({f'{side}/{name}': value for name, value in _native_hashes(directory/side).items()})
    return result


def _snapshot(directory):
    result = _input_hashes(directory)
    for name in ('tracking-results.json', 'manifest.json', 'job.json'):
        _load(directory/name); result[name] = _digest(directory/name)
    return result


def _source(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError('planar tracking source must not be linked')
    managed = (path/'job.json').exists()
    hashes = _job_hashes(path) if managed else _native_hashes(path)
    if managed:
        solution = verify_planar_job(path, _load(path/'job.json'), _load(path/'manifest.json'))
    else:
        solution = read_planar_run(path)
    if hashes != (_job_hashes(path) if managed else _native_hashes(path)):
        raise ValueError('planar tracking source changed during verification')
    return (path/'solution' if managed else path), solution, dict(
        path=str(path.resolve()), kind='planar_job' if managed else 'planar_native', files=hashes)


def _check_sources(document, directory):
    names = ['format', 'sources_version', 'previous', 'current']
    keys(document, names, names, 'planar tracking sources')
    if document['format'] != 'superfish_ng_planar_tracking_sources' or type(document['sources_version']) is not int or document['sources_version'] != 1:
        raise ValueError('expected planar tracking sources version 1')
    for side in ('previous', 'current'):
        source = document[side]
        keys(source, ['path', 'kind', 'files'], ['path', 'kind', 'files'], 'planar tracking source')
        if type(source['path']) is not str or not source['path'] or source['kind'] not in ('planar_job', 'planar_native'):
            raise ValueError('planar tracking source path/kind is invalid')
        files = source['files']; prefix = 'solution/' if source['kind'] == 'planar_job' else ''
        expected = {prefix+name for name in NATIVE}
        if prefix: expected |= {'project.json', 'job.json', 'manifest.json'}
        if (type(files) is not dict or set(files) != expected or any(
                type(v) is not str or len(v) != 64 or any(c not in '0123456789abcdef' for c in v) for v in files.values())):
            raise ValueError('planar tracking source hashes are incomplete or invalid')
        if {name: files[prefix+name] for name in NATIVE} != _native_hashes(directory/side):
            raise ValueError('copied planar native differs from recorded source bytes')


def is_planar_tracking(directory, state, manifest):
    if KIND in (state.get('kind'), manifest.get('kind')): return True
    for name in ('tracking.json', 'tracking-results.json'):
        if (directory/name).is_file():
            data = _load(directory/name)
            if isinstance(data, dict) and data.get('format') in ('superfish_ng_planar_tracking_request', 'superfish_ng_planar_tracking_result'):
                return True
    return False


def verify_planar_tracking(directory, state, manifest):
    directory = Path(directory); before = _snapshot(directory)
    if state.get('status') != 'complete' or state.get('kind') != KIND or manifest.get('kind') != KIND:
        raise ValueError('planar tracking state and manifest require complete kind=planar_tracking')
    names = ['manifest_version', 'kind', 'files', 'implementation_sha256', 'source_changed_during_run']
    keys(manifest, names, names, 'planar tracking manifest')
    implementation = manifest['implementation_sha256']
    if (type(manifest['manifest_version']) is not int or manifest['manifest_version'] != 1
            or type(implementation) is not dict or not implementation
            or any(type(k) is not str or type(v) is not str or len(v) != 64
                   or any(c not in '0123456789abcdef' for c in v) for k, v in implementation.items())
            or manifest['source_changed_during_run'] is not False):
        raise ValueError('planar tracking requires stable implementation provenance')
    if manifest['files'] != {k: v for k, v in before.items() if k not in ('job.json', 'manifest.json')}:
        raise ValueError('planar tracking manifest must bind the full request and both complete native snapshots')
    _check_sources(_load(directory/'sources.json'), directory)
    request = PlanarTrackingRequest.load(directory/'tracking.json')
    solutions = [read_planar_run(directory/side) for side in ('previous', 'current')]
    expected = track_planar_modes(*solutions, request)
    result = _load(directory/'tracking-results.json')
    if json.dumps(result, sort_keys=True, allow_nan=False) != json.dumps(expected, sort_keys=True, allow_nan=False):
        raise ValueError('saved planar tracking differs from full native electric-field and spectral-resolution replay')
    if (state.get('input_sha256') != _input_hashes(directory)
            or state.get('physics') != 'cartesian_cutoff_rf' or state.get('numerical_validation') != result['status']
            or type(state.get('individual_ids_complete')) is not bool
            or state['individual_ids_complete'] != result['individual_ids_complete']):
        raise ValueError('planar tracking state differs from the verified correspondence')
    if _snapshot(directory) != before or _load(directory/'job.json') != state or _load(directory/'manifest.json') != manifest:
        raise ValueError('planar tracking changed during verification')
    return result


def read_planar_tracking(directory):
    directory = Path(directory)
    return verify_planar_tracking(directory, _load(directory/'job.json'), _load(directory/'manifest.json'))


def _prepare(previous, current, request, directory):
    if not isinstance(request, PlanarTrackingRequest): raise ValueError('expected PlanarTrackingRequest')
    request = PlanarTrackingRequest.from_dict(request.to_dict())
    sources = [_source(path) for path in (previous, current)]
    cases = [source[1].case for source in sources]
    from .planar_polygon import PlanarPolygonCase
    from .planar_tracking_polygon import PolygonScaleMapping, polygon_scale_overlay
    from .planar_tracking_similarity import PolygonSimilarityMapping, polygon_similarity_overlay
    from .planar_tracking_remesh import PolygonRemeshMapping, polygon_remesh_overlay
    from .planar_tracking_similarity_remesh import PolygonSimilarityRemeshMapping, polygon_similarity_remesh_overlay
    from .planar_tracking_affine_remesh import PolygonAffineRemeshMapping, polygon_affine_remesh_overlay
    from .planar_tracking_exact_mapping import PolygonExactAffineRemeshMapping, polygon_exact_affine_remesh_overlay
    from .planar_affine_shape_mapping import PlanarAffineShapeMapping, affine_shape_overlay
    shape = isinstance(request.mapping, PlanarAffineShapeMapping)
    exact_affine = isinstance(request.mapping, PolygonExactAffineRemeshMapping)
    remesh = isinstance(request.mapping, PolygonRemeshMapping)
    similarity = isinstance(request.mapping, PolygonSimilarityMapping)
    composed = isinstance(request.mapping, PolygonSimilarityRemeshMapping)
    affine = isinstance(request.mapping, PolygonAffineRemeshMapping)
    polygon = isinstance(request.mapping, (PolygonScaleMapping, PolygonSimilarityMapping, PolygonRemeshMapping,
                                           PolygonSimilarityRemeshMapping, PolygonAffineRemeshMapping, PolygonExactAffineRemeshMapping, PlanarAffineShapeMapping))
    required = PlanarPolygonCase if polygon else PlanarCase
    if not all(isinstance(case, required) for case in cases) or cases[0].polarization != cases[1].polarization:
        raise ValueError('planar tracking source Case types and TE/TM polarization must match the declared mapping')
    for count, case in zip((request.previous_mode_count, request.current_mode_count), cases):
        if count >= case.modes: raise ValueError('tracked band requires a computed upper guard mode')
        refined_count = 4*len(case.mesh.triangles) if polygon else 8*case.nx*case.ny
        if refined_count > request.controls.max_refined_triangles:
            raise ValueError('spectral-resolution refinement exceeds max_refined_triangles')
    if shape:
        affine_shape_overlay(cases[0].mesh, cases[1].mesh, request.mapping,
                             max_overlay_triangles=request.controls.max_overlay_triangles)
    elif polygon:
        (polygon_exact_affine_remesh_overlay if exact_affine else polygon_affine_remesh_overlay if affine else polygon_similarity_remesh_overlay if composed else polygon_remesh_overlay if remesh else polygon_similarity_overlay if similarity else polygon_scale_overlay)(cases[0].mesh, cases[1].mesh, request.mapping,
                              max_overlay_triangles=request.controls.max_overlay_triangles)
    else:
        from .planar_tracking_overlap import rectangle_tracking_overlay
        rectangle_tracking_overlay((cases[0].nx, cases[0].ny), (cases[1].nx, cases[1].ny),
                                   max_overlay_triangles=request.controls.max_overlay_triangles)
    source_document = dict(format='superfish_ng_planar_tracking_sources', sources_version=1,
                           previous=sources[0][2], current=sources[1][2])
    raw = json.dumps(request.to_dict(), ensure_ascii=False, indent=2, allow_nan=False)+'\n'
    source_raw = json.dumps(source_document, ensure_ascii=False, indent=2, allow_nan=False)+'\n'
    expected = {'tracking.json': hashlib.sha256(raw.encode()).hexdigest(),
                'sources.json': hashlib.sha256(source_raw.encode()).hexdigest()}
    directory.mkdir(parents=True, exist_ok=False)
    try:
        request.save(directory/'tracking.json'); _write_json(directory/'sources.json', source_document)
        for side, (native, _, descriptor) in zip(('previous', 'current'), sources):
            (directory/side).mkdir()
            for name in sorted(NATIVE): shutil.copyfile(native/name, directory/side/name)
            prefix = 'solution/' if descriptor['kind'] == 'planar_job' else ''
            expected.update({f'{side}/{name}': descriptor['files'][prefix+name] for name in NATIVE})
        for _, _, descriptor in sources:
            path = Path(descriptor['path'])
            if descriptor['files'] != (_job_hashes(path) if descriptor['kind'] == 'planar_job' else _native_hashes(path)):
                raise ValueError('planar tracking source changed during snapshot copy')
        if _input_hashes(directory) != expected: raise ValueError('planar tracking prepared inputs changed during copying')
        _state(directory, 'queued', kind=KIND, input_sha256=expected)
    except Exception as exc:
        _state(directory, 'failed', kind=KIND, error=str(exc)); raise


def execute_prepared_planar_tracking(directory):
    directory = Path(directory); state = _load(directory/'job.json'); started = time.monotonic()
    if directory.is_symlink() or state.get('status') != 'queued' or state.get('kind') != KIND:
        raise ValueError('planar tracking worker requires a fresh queued planar_tracking job')
    with (directory/'worker.claim').open('x') as stream: stream.write(str(os.getpid())+'\n')
    try:
        inputs = _input_hashes(directory); implementation = _implementation_hashes()
        if inputs != state.get('input_sha256'): raise ValueError('queued planar tracking inputs changed')
        _state(directory, 'running', kind=KIND, input_sha256=inputs, stage='integrating electric fields and checking spectral resolution')
        _check_sources(_load(directory/'sources.json'), directory)
        result = track_planar_modes(*(read_planar_run(directory/side) for side in ('previous', 'current')),
                                    PlanarTrackingRequest.load(directory/'tracking.json'))
        if inputs != _input_hashes(directory) or implementation != _implementation_hashes():
            raise ValueError('planar tracking input or implementation changed during execution')
        _write_json(directory/'tracking-results.json', result)
        _write_json(directory/'manifest.json', dict(manifest_version=1, kind=KIND,
            files={**inputs, 'tracking-results.json': _digest(directory/'tracking-results.json')},
            implementation_sha256=implementation, source_changed_during_run=False))
        _state(directory, 'complete', kind=KIND, input_sha256=inputs, stage='saved electric-field correspondence', physics='cartesian_cutoff_rf',
               numerical_validation=result['status'], individual_ids_complete=result['individual_ids_complete'],
               elapsed_seconds=time.monotonic()-started)
        result = read_planar_tracking(directory)
        if inputs != _input_hashes(directory) or implementation != _implementation_hashes():
            raise ValueError('planar tracking input or implementation changed during completion')
        return result
    except Exception as exc:
        _state(directory, 'failed', kind=KIND, error=str(exc), elapsed_seconds=time.monotonic()-started); raise


def execute_planar_tracking(previous, current, request, directory):
    directory = Path(directory); _prepare(previous, current, request, directory)
    return execute_prepared_planar_tracking(directory)


def start_planar_tracking(manager, previous, current, request):
    with manager.lock:
        if manager.closed: raise ValueError('job manager is closed')
        identifier = time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:10]
        directory = manager.directory(identifier); _prepare(previous, current, request, directory)
        try:
            with (directory/'log.txt').open('x') as log:
                manager.processes[identifier] = subprocess.Popen(
                    [sys.executable, '-m', 'superfish_ng.planar_tracking_jobs', str(directory)],
                    stdout=log, stderr=subprocess.STDOUT, env={**os.environ, 'OPENBLAS_NUM_THREADS': '1'})
        except Exception as exc:
            _state(directory, 'failed', kind=KIND, error=str(exc)); raise
        return identifier


if __name__ == '__main__':
    if len(sys.argv) != 2: raise SystemExit('usage: python -m superfish_ng.planar_tracking_jobs PREPARED_DIRECTORY')
    execute_prepared_planar_tracking(sys.argv[1])
