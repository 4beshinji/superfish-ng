# SPDX-License-Identifier: Apache-2.0
"""Saved Cartesian cutoff-frequency tuning with electric-field identities.

Geometry and native data remain in the dedicated planar contract. Only the
physics-independent bracket decision is shared with axisymmetric tuning.
"""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

from .config import integer, keys, positive
from .project import parse_json
from .planar_project import PlanarProject
from .planar_polygon import PlanarPolygonCase
from .planar_study import PlanarStudy
from .planar_affine_shape import PlanarAffineShapeLaw, explicit_planar_project
from .planar_affine_shape_mapping import PlanarAffineShapeMapping
from .planar_refinement import refine_planar_mesh
from .planar_tracking import PlanarTrackingControls, PlanarTrackingRequest, track_planar_modes
from .planar_tracking_polygon import PolygonScaleMapping
from .planar_jobs import execute_planar_project, _job_hashes, verify_planar_job
from .jobs import _implementation_hashes
from .mode_tracking import tracked_frequency_hz
from .saved_mode_tracking import _canonical
from .tuning import _decision
from .planar_tuning_recovery import validate_planar_recovery_policy, recover_planar_tune_trial


def validate_planar_tune(request):
    names = ('format', 'schema_version', 'project', 'parameter', 'bounds',
             'target_hz', 'frequency_tolerance_hz', 'parameter_tolerance',
             'max_trials', 'initial_ids', 'mode_id', 'controls',
             'refinement_levels', 'max_triangles', 'mesh_frequency_tolerance_hz')
    version = request.get('schema_version') if type(request) is dict else None
    if type(version) is int and (version == 2 or version == 3 and request.get('parameter') == 'deformation'):
        names = (*names, 'shape_law')
    if type(version) is int and version == 3:
        names = (*names, 'identity_recovery')
    keys(request, names, names, 'planar tune')
    if (request['format'] != 'superfish_ng_planar_tune' or
            type(request['schema_version']) is not int or request['schema_version'] not in (1, 2, 3)):
        raise ValueError('expected superfish_ng_planar_tune schema_version 1, 2 or 3')
    project = PlanarProject.from_dict(request['project'])
    polynomial = version == 2 or version == 3 and request['parameter'] == 'deformation'
    if polynomial:
        law = PlanarAffineShapeLaw.from_dict(request['shape_law'])
        if request['parameter'] != 'deformation':
            raise ValueError('planar tune v2 parameter must be dimensionless deformation')
        if list(law.bounds) != request['bounds']:
            raise ValueError('planar tune bounds must equal the shape law interval')
    elif request['parameter'] not in ('uniform_scale', '/case/geometry/width_m', '/case/geometry/height_m'):
        raise ValueError('planar tune parameter must be uniform_scale or rectangle width/height in metres')
    bounds = request['bounds']
    if type(bounds) is not list or len(bounds) != 2:
        raise ValueError('planar tune bounds require two increasing positive values')
    for value in bounds:
        if polynomial:
            law.exact_transform(value)
        else:
            positive(value, 'planar tune bound')
    if not bounds[0] < bounds[1]:
        raise ValueError('planar tune bounds must increase')
    for name in ('target_hz', 'frequency_tolerance_hz', 'parameter_tolerance', 'mesh_frequency_tolerance_hz'):
        positive(request[name], name)
    integer(request['max_trials'], 'max_trials', 2)
    integer(request['max_triangles'], 'max_triangles')
    integer(request['refinement_levels'], 'refinement_levels')
    if request['refinement_levels'] > 8:
        raise ValueError('planar tune supports at most eight final refinement levels')
    ids = request['initial_ids']
    if (type(ids) is not list or not ids or len(ids) >= project.case.modes or
            any(type(i) is not str or not i.strip() for i in ids) or len(set(ids)) != len(ids)):
        raise ValueError('initial_ids require a distinct positive prefix band and at least one computed upper guard mode')
    if type(request['mode_id']) is not str or request['mode_id'] not in ids:
        raise ValueError('mode_id must occur in initial_ids')
    PlanarTrackingControls.from_dict(request['controls'])
    if version == 3:
        validate_planar_recovery_policy(request)
    for value in bounds:
        trial_planar_project(request, value, 'refinement')
    return project


def trial_planar_project(request, value, phase):
    """Derive each candidate from the original declaration, including its mesh."""
    if phase not in ('search', 'refinement'):
        raise ValueError('planar tune phase must be search or refinement')
    project = PlanarProject.from_dict(request['project'])
    if request['schema_version'] in (2, 3) and request['parameter'] == 'deformation':
        project = PlanarAffineShapeLaw.from_dict(request['shape_law']).project(explicit_planar_project(project), value)
    else:
        project = PlanarStudy(project, request['parameter'], [value, value]).projects()[0]
    case = project.case
    polygon = isinstance(case, PlanarPolygonCase)
    count = len(case.mesh.triangles) if polygon else 2 * case.nx * case.ny
    levels = request['refinement_levels'] if phase == 'refinement' else 0
    for _ in range(levels):
        if count > request['max_triangles'] // 4:
            raise ValueError('planar tune final mesh exceeds max_triangles')
        count *= 4
    if count > request['max_triangles']:
        raise ValueError('planar tune initial mesh exceeds max_triangles')
    for _ in range(levels):
        case = (replace(case, mesh=refine_planar_mesh(case.mesh, max_triangles=request['max_triangles']))
                if polygon else replace(case, nx=2*case.nx, ny=2*case.ny))
    return replace(project, case=case)


def planar_tune_mapping(request, previous, current):
    """Derive a complete comparison from original geometry and both trial phases."""
    project = PlanarProject.from_dict(request['project'])
    levels = [request['refinement_levels'] if trial['phase']=='refinement' else 0
              for trial in (previous, current)]
    if request['schema_version'] in (2, 3) and request['parameter'] == 'deformation':
        return PlanarAffineShapeMapping(explicit_planar_project(project),
            PlanarAffineShapeLaw.from_dict(request['shape_law']), previous['value'], current['value'], *levels)
    if isinstance(project.case, PlanarPolygonCase):
        return PolygonScaleMapping(current['value']/previous['value'], *levels)
    return 'normalized_rectangle'


def _native(directory, expected):
    directory = Path(directory)
    if not directory.is_absolute() or directory.is_symlink():
        raise ValueError('planar tune requires absolute non-symlink native job paths')
    before = _job_hashes(directory)
    state = parse_json((directory/'job.json').read_text())
    manifest = parse_json((directory/'manifest.json').read_text())
    solution = verify_planar_job(directory, state, manifest)
    if PlanarProject.load(directory/'project.json').to_dict() != expected.to_dict():
        raise ValueError('planar tune native Project differs from its declared trial')
    if before != _job_hashes(directory):
        raise ValueError('planar tune native files changed during verification')
    return solution, before


def _assemble(request, runs):
    project = validate_planar_tune(request)
    request = parse_json(_canonical(request))
    if (type(runs) is not list or any(type(p) is not str for p in runs) or
            len(set(runs)) != len(runs) or len(runs) > request['max_trials']+1):
        raise ValueError('planar tune trial paths must be distinct and within the search plus final trial budget')
    trials, sources, solutions = [], [], []
    controls = PlanarTrackingControls.from_dict(request['controls'])
    for index, run in enumerate(runs):
        decision = _decision(request, trials)
        if decision['status'] != 'PAUSED':
            raise ValueError('planar tune contains trials after a terminal decision')
        trial = decision['next_trial']
        native_project = trial_planar_project(request, trial['value'], trial['phase'])
        solution, hashes = _native(run, native_project)
        solutions.append(solution); sources.append(hashes)
        tracking = None; initial_tracking = None; recovery = None
        if index == 0:
            ids = list(request['initial_ids'])
            frequency = float(solution.frequencies_hz[ids.index(request['mode_id'])])
            status = 'INITIAL'
            if request['schema_version'] == 3:
                initial_tracking = track_planar_modes(solution, solution, PlanarTrackingRequest(
                    len(ids), len(ids), ids, mapping=planar_tune_mapping(request, trial, trial), controls=controls))
                if initial_tracking['status'] != 'PASS' or not initial_tracking['individual_ids_complete']:
                    status = 'UNVERIFIED'; frequency = None; ids = initial_tracking['current_mode_ids']
        else:
            parent = trial['parent_index']
            mapping = planar_tune_mapping(request, trials[parent], trial)
            comparison_request = PlanarTrackingRequest(
                len(request['initial_ids']), len(request['initial_ids']),
                trials[parent]['current_mode_ids'], mapping=mapping, controls=controls)
            tracking = track_planar_modes(solutions[parent], solution, comparison_request)
            ids = tracking['current_mode_ids']
            passed = tracking['status']=='PASS' and tracking['individual_ids_complete']
            status = 'PASS' if passed else 'UNVERIFIED'
            frequency = tracked_frequency_hz(tracking, request['mode_id']) if passed else None
            if request['schema_version'] == 3 and tracking['status'] == 'PASS' and not passed:
                recovery = recover_planar_tune_trial(request, trials, solutions, solution, trial, comparison_request)
                if recovery['status'] == 'PASS':
                    recovered = recovery['recovery']
                    ids = recovered['assessment']['current_mode_ids']
                    frequency = recovered['recovered_frequencies_hz'][request['mode_id']]
                    status = 'PASS'
        trials.append(dict(index=index, **trial, status=status, current_mode_ids=ids,
            frequency_hz=frequency, target_error_hz=None if frequency is None else frequency-request['target_hz'],
            tracking=tracking))
        if request['schema_version'] == 3:
            trials[-1].update(initial_tracking=initial_tracking, identity_recovery=recovery)
    if sources != [_job_hashes(Path(run)) for run in runs]:
        raise ValueError('planar tune sources changed during complete replay')
    decision = _decision(request, trials)
    return dict(format='superfish_ng_planar_tune_checkpoint', schema_version=1,
        request=deepcopy(request), trial_runs=list(runs), trial_sources_sha256=sources,
        trials=trials, decision=decision, status=decision['status'], can_resume=decision['status']=='PAUSED',
        scope='Cartesian cutoff FEM with physical electric-field identities, computed upper guard modes and a separate final frequency-difference gate; J/m normalization; no accelerating R/Q, continuum-error or global-root certificate')


def replay_planar_tune(document):
    names = ('format', 'schema_version', 'request', 'trial_runs', 'trial_sources_sha256',
             'trials', 'decision', 'status', 'can_resume', 'scope')
    keys(document, names, names, 'planar tune checkpoint')
    expected = _assemble(document['request'], document['trial_runs'])
    if _canonical(document) != _canonical(expected):
        raise ValueError('planar tune checkpoint differs from native replay')
    return expected


def read_planar_tune(path):
    return replay_planar_tune(parse_json(Path(path).read_text(encoding='utf-8')))


def execute_planar_tune(request, directory, *, max_new_trials=None, checkpoint=None):
    """Save each verified trial; resumption always writes a new directory."""
    request = deepcopy(request)
    validate_planar_tune(request)
    request = parse_json(_canonical(request))
    if max_new_trials is not None:
        integer(max_new_trials, 'max_new_trials')
    previous = _assemble(request, []) if checkpoint is None else replay_planar_tune(checkpoint)
    if _canonical(previous['request']) != _canonical(request):
        raise ValueError('planar tune resume request differs from checkpoint')
    if not previous['can_resume']:
        raise ValueError('only a verified PAUSED planar tune can resume')
    implementation = _implementation_hashes()
    runs = list(previous['trial_runs'])
    directory = Path(directory).resolve(); directory.mkdir(parents=True, exist_ok=False)
    count = 0
    while previous['can_resume'] and (max_new_trials is None or count < max_new_trials):
        index = len(runs); trial = previous['decision']['next_trial']
        run = directory/f'trial-{index+1:03d}'
        try:
            execute_planar_project(trial_planar_project(request, trial['value'], trial['phase']), run)
            result = _assemble(request, runs+[str(run)])
            if result['trial_sources_sha256'][:index] != previous['trial_sources_sha256']:
                raise ValueError('prior planar tune sources changed during execution')
            if implementation != _implementation_hashes():
                raise RuntimeError('implementation changed during planar tune execution')
            serialized = json.dumps(result, indent=2, allow_nan=False)+'\n'
            with (directory/f'checkpoint-{index+1:03d}.json').open('x', encoding='utf-8') as stream:
                stream.write(serialized)
        except Exception as exc:
            failure = dict(request=request, attempt=trial, trial_run=str(run),
                preceding_trial_runs=runs, status='FAILED', error_type=type(exc).__name__, error=str(exc),
                scope='failed trial is not a frequency evaluation; prior checkpoints remain separate')
            with (directory/f'failure-{index+1:03d}.json').open('x', encoding='utf-8') as stream:
                json.dump(failure, stream, indent=2, allow_nan=False)
            raise
        previous = result; runs.append(str(run)); count += 1
    return previous
