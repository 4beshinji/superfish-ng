# SPDX-License-Identifier: Apache-2.0
"""Isolated planar tuning workers with complete checkpoint and ancestry checks."""
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import uuid

from .config import keys, integer
from .project import parse_json
from .jobs import _state, _write_json, _digest, _implementation_hashes
from .saved_mode_tracking import _canonical
from .planar_tuning import validate_planar_tune, execute_planar_tune, read_planar_tune, replay_planar_tune
from .tuning_decision import decide_next_trial
from .tuning_identity_recovery import base_request
from .planar_tuning_saved import (_copy_trial, _snapshot_trial, _portable,
                                  CHECKPOINT_KEYS)

KIND = 'planar_tune'
INPUT = 'planar-tune-request.json'
RESULT = 'planar-tune-results.json'
ANCESTRY = 'ancestry'


def _load(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('planar tune metadata must be regular files, not links')
    return parse_json(path.read_text(encoding='utf-8'))


def _input(data):
    names = ('request', 'max_new_trials', 'checkpoint')
    keys(data, names, names, 'planar tune job input')
    validate_planar_tune(data['request'])
    if data['max_new_trials'] is not None:
        integer(data['max_new_trials'], 'max_new_trials')
    if data['checkpoint'] is not None:
        if isinstance(data['checkpoint'], (str, Path)):
            data['checkpoint'] = read_planar_tune(data['checkpoint'])
        previous = replay_planar_tune(data['checkpoint'])
        if not previous['can_resume']:
            raise ValueError('only a verified PAUSED planar tune can resume')
        if _canonical(previous['request']) != _canonical(data['request']):
            raise ValueError('planar tune resume request differs from checkpoint')
    return data


def _is_owned(data):
    return data['request']['schema_version'] == 4


def _submitted_hashes(directory, data):
    """Seal queued ancestry together with the immutable submitted envelope."""
    result = {INPUT: _digest(directory/INPUT)}
    if _is_owned(data) and data['checkpoint'] is not None:
        ancestry = directory/ANCESTRY
        _load(ancestry/'request.json')
        result[f'{ANCESTRY}/request.json'] = _digest(ancestry/'request.json')
        runs = data['checkpoint']['trial_runs']
        if type(runs) is not list:
            raise ValueError('planar tune submitted trial paths must be a list')
        expected_children = {'request.json'}
        for index in range(len(runs)):
            name = f'trial-{index+1:03d}'
            expected_children.add(name)
            result.update({f'{ANCESTRY}/{name}/{key}': value
                           for key, value in _snapshot_trial(ancestry/name).items()})
        if ancestry.is_symlink() or not ancestry.is_dir() or {p.name for p in ancestry.iterdir()} != expected_children:
            raise ValueError('planar tune queued ancestry contains missing or undeclared entries')
    elif (directory/ANCESTRY).exists() or (directory/ANCESTRY).is_symlink():
        raise ValueError('planar tune job has undeclared queued ancestry')
    return result


def _owned_input(data, directory):
    """Replay copies without following the provenance paths to original sources."""
    owned = deepcopy(data)
    names = ('request', 'max_new_trials', 'checkpoint')
    keys(owned, names, names, 'planar tune job input')
    validate_planar_tune(owned['request'])
    if _is_owned(owned) and owned['checkpoint'] is not None:
        previous = owned['checkpoint']
        keys(previous, CHECKPOINT_KEYS, CHECKPOINT_KEYS, 'planar tune submitted checkpoint')
        if type(previous['schema_version']) is not int or previous['schema_version'] != 2:
            raise ValueError('owned planar worker requires submitted checkpoint version 2')
        runs = previous['trial_runs']
        if type(runs) is not list or any(type(run) is not str or not run for run in runs):
            raise ValueError('planar tune submitted trial paths must be nonempty absolute paths')
        paths = [Path(run) for run in runs]
        if (any(not p.is_absolute() or '..' in p.parts or run != str(p)
                or p.name != f'trial-{i+1:03d}' for i, (p, run) in enumerate(zip(paths, runs)))
                or len({p.parent for p in paths}) > 1):
            raise ValueError('planar tune submitted trials require ordered canonical paths with one owner')
        previous['trial_runs'] = [str((directory/ANCESTRY/p.name).resolve()) for p in paths]
    return _input(owned)


def read_planar_tune_job_checkpoint(directory, index):
    """Select a stopped job's checkpoint using its bound request and ancestry."""
    integer(index, 'checkpoint index', minimum=0)
    directory = Path(directory).resolve()
    state = _load(directory/'job.json')
    if state.get('kind') != KIND or state.get('status') not in ('complete', 'cancelled', 'interrupted', 'failed'):
        raise ValueError('select a stopped planar tuning job before opening checkpoints')
    original = _load(directory/INPUT)
    submitted = _submitted_hashes(directory, original)
    if 'input_sha256' in state and state['input_sha256'] != submitted:
        raise ValueError('planar tune submitted input changed before checkpoint verification')
    data = _owned_input(original, directory)
    execution = directory/'execution'
    path = execution/f'checkpoint-{index:03d}.json'
    before = _digest(path)
    result = read_planar_tune(path)
    previous = data['checkpoint']
    offset = 0 if previous is None else len(previous['trials'])
    if (len(result['trials']) != index or index < offset
            or _canonical(result['request']) != _canonical(data['request'])):
        raise ValueError('planar tune checkpoint differs from its selected job or submitted prefix')
    comparison_keys = ('trials', 'trial_sources_sha256') if _is_owned(data) else ('trial_runs', 'trials', 'trial_sources_sha256')
    if previous is not None and any(_canonical(result[key][:offset]) != _canonical(previous[key]) for key in comparison_keys):
        raise ValueError('planar tune checkpoint ancestry differs from its selected job')
    for i in range(0 if _is_owned(data) else offset, index):
        if result['trial_runs'][i] != str(execution/f'trial-{i+1:03d}'):
            raise ValueError('planar tune checkpoint trial belongs to another tuning job')
    if before != _digest(path) or submitted != _submitted_hashes(directory, _load(directory/INPUT)):
        raise ValueError('planar tune checkpoint or submitted input changed during verification')
    return result


def is_planar_tune(directory, state, manifest):
    return (KIND in (state.get('kind'), manifest.get('kind')) or
            (directory/INPUT).exists() or (directory/RESULT).exists())


def _snapshot(directory):
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('planar tune job directory must be regular')
    result = {}
    for name in (INPUT, RESULT, 'job.json', 'manifest.json'):
        _load(directory/name); result[name] = _digest(directory/name)
    claim = directory/'worker.claim'
    if claim.is_symlink() or not claim.is_file():
        raise ValueError('planar tune worker claim must be a regular file')
    result['worker.claim'] = _digest(claim)
    for name in ('execution', ANCESTRY):
        owner = directory/name
        if name == ANCESTRY and not owner.exists() and not owner.is_symlink():
            continue
        if owner.is_symlink() or not owner.is_dir():
            raise ValueError('planar tune owned directories must be regular')
        for path in owner.rglob('*'):
            if path.is_symlink():
                raise ValueError('planar tune owned files must not be linked')
            if path.is_file():
                result[path.relative_to(directory).as_posix()] = _digest(path)
            elif not path.is_dir():
                raise ValueError('planar tune owned entries must be regular')
    return result


def verify_planar_tune_job(directory, state, manifest):
    directory = Path(directory)
    before = _snapshot(directory)
    if state.get('status') != 'complete' or state.get('kind') != KIND or manifest.get('kind') != KIND:
        raise ValueError('planar tune state and manifest require complete kind=planar_tune')
    names = ('manifest_version', 'kind', 'files', 'implementation_sha256', 'source_changed_during_run')
    keys(manifest, names, names, 'planar tune manifest')
    if type(manifest['manifest_version']) is not int or manifest['manifest_version'] != 1:
        raise ValueError('planar tune manifest_version must be 1')
    expected_files = {k: v for k, v in before.items() if k not in ('job.json', 'manifest.json')}
    if manifest['files'] != expected_files:
        raise ValueError('planar tune manifest must bind all request, result, checkpoint and native files exactly')
    implementation = manifest['implementation_sha256']
    if (not isinstance(implementation, dict) or not implementation or
            any(type(k) is not str or type(v) is not str or len(v) != 64 or
                any(c not in '0123456789abcdef' for c in v) for k, v in implementation.items()) or
            manifest['source_changed_during_run'] is not False):
        raise ValueError('planar tune requires stable implementation provenance')
    submitted_data = _load(directory/INPUT)
    submitted = _submitted_hashes(directory, submitted_data)
    data = _owned_input(submitted_data, directory)
    result = read_planar_tune(directory/RESULT)
    if (_canonical(data['request']) != _canonical(result['request']) or
            state.get('tuning_status') != result['status'] or
            state.get('can_resume') is not result['can_resume'] or
            type(state.get('computed_trials')) is not int or state['computed_trials'] != len(result['trials']) or
            state.get('numerical_validation') != 'not_checked' or
            state.get('physics') != 'cartesian_cutoff_rf' or
            state.get('input_sha256') != submitted):
        raise ValueError('planar tune job summary or submitted input differs from verified result')
    previous = data['checkpoint']
    offset = 0 if previous is None else len(previous['trial_runs'])
    ancestry_keys = ('trial_sources_sha256', 'trials') if _is_owned(data) else ('trial_runs', 'trial_sources_sha256', 'trials')
    if previous is not None and any(_canonical(result[k][:offset]) != _canonical(previous[k])
            for k in ancestry_keys):
        raise ValueError('planar tune resume ancestry differs from its submitted checkpoint')
    count = len(result['trials'])-offset
    limit = data['max_new_trials']
    if count < 1 or (limit is not None and count > limit) or (result['can_resume'] and (limit is None or count != limit)):
        raise ValueError('planar tune trial budget differs from the verified result')
    required = set(submitted) | {RESULT, 'worker.claim'}
    owned = _is_owned(data)
    if owned:
        if _canonical(_load(directory/'execution/request.json')) != _canonical(result['request']):
            raise ValueError('planar tune owned request differs from submitted request')
        required.add('execution/request.json')
    for index in range(0 if owned else offset, len(result['trials'])):
        relative = f'execution/trial-{index+1:03d}'
        if result['trial_runs'][index] != str(directory.resolve()/relative):
            raise ValueError('planar tune new trial is outside its owned execution directory')
        native_manifest = _load(directory/relative/'manifest.json')
        if index >= offset and (native_manifest.get('implementation_sha256') != implementation or 'imported_from' in native_manifest):
            raise ValueError('planar tune new trial must be executed with the worker implementation')
        required.update(relative+'/'+name for name in result['trial_sources_sha256'][index])
        required.add(relative+'/worker.claim')
    for number in range(offset if owned else offset+1, len(result['trials'])+1):
        checkpoint = f'execution/checkpoint-{number:03d}.json'
        required.add(checkpoint)
        # Full final replay already verified each pair. Reconstruct its prefix
        # decision without re-running all previous field comparisons again.
        prefix = deepcopy(result)
        for key in ('trial_runs', 'trial_sources_sha256', 'trials'):
            prefix[key] = prefix[key][:number]
        prefix['decision'] = decide_next_trial(base_request(prefix['request']), prefix['trials'])
        prefix['status'] = prefix['decision']['status']
        prefix['can_resume'] = prefix['status'] == 'PAUSED'
        expected_prefix = _portable(prefix, directory/'execution') if owned else prefix
        if _canonical(_load(directory/checkpoint)) != _canonical(expected_prefix):
            raise ValueError('planar tune saved checkpoint differs from its fully verified prefix')
    if set(expected_files) != required:
        raise ValueError('planar tune execution contains missing or undeclared trial files')
    if (_load(directory/'job.json') != state or _load(directory/'manifest.json') != manifest or
            before != _snapshot(directory)):
        raise ValueError('planar tune files changed during verification')
    return result


def start_planar_tune(manager, request, *, max_new_trials=None, checkpoint=None):
    with manager.lock:
        if manager.closed:
            raise ValueError('job manager is closed')
        data = _input(deepcopy(dict(request=request, max_new_trials=max_new_trials, checkpoint=checkpoint)))
        identifier = time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:10]
        directory = manager.directory(identifier); directory.mkdir()
        _write_json(directory/INPUT, data)
        try:
            if _is_owned(data) and data['checkpoint'] is not None:
                ancestry = directory/ANCESTRY; ancestry.mkdir()
                _write_json(ancestry/'request.json', data['request'])
                previous = data['checkpoint']
                for index, source in enumerate(previous['trial_runs']):
                    _copy_trial(source, ancestry/f'trial-{index+1:03d}', previous['trial_sources_sha256'][index])
                # Physical replay also checks every copied hash and decision.
                _owned_input(data, directory)
            submitted = _submitted_hashes(directory, data)
            _state(directory, 'queued', kind=KIND, input_sha256=submitted)
            with (directory/'log.txt').open('x') as log:
                process = subprocess.Popen([sys.executable, '-m', 'superfish_ng.planar_tuning_jobs', str(directory)],
                    stdout=log, stderr=subprocess.STDOUT, env={**os.environ, 'OPENBLAS_NUM_THREADS': '1'})
            manager.processes[identifier] = process
        except Exception as exc:
            _state(directory, 'failed', kind=KIND, error=str(exc))
            raise
        return identifier


def execute_prepared_planar_tune(directory):
    directory = Path(directory)
    state = _load(directory/'job.json')
    if state.get('status') != 'queued' or state.get('kind') != KIND:
        raise ValueError('planar tune worker requires a fresh queued planar_tune job')
    # This exclusive file prevents two workers consuming one queued request;
    # its PID is provenance, never evidence that a process is still running.
    with (directory/'worker.claim').open('x', encoding='utf-8') as stream:
        stream.write(str(os.getpid())+'\n')
    started = time.monotonic()
    try:
        implementation = _implementation_hashes()
        submitted_data = _load(directory/INPUT)
        submitted = _submitted_hashes(directory, submitted_data)
        if state.get('input_sha256') != submitted:
            raise ValueError('queued planar tune input changed before execution')
        data = _owned_input(submitted_data, directory)
        _state(directory, 'running', kind=KIND, input_sha256=submitted, stage='Cartesian tracked frequency tuning')
        result = execute_planar_tune(data['request'], directory/'execution',
            max_new_trials=data['max_new_trials'], checkpoint=data['checkpoint'])
        if implementation != _implementation_hashes() or submitted != _submitted_hashes(directory, _load(directory/INPUT)):
            raise RuntimeError('implementation or planar tune input changed during execution')
        _write_json(directory/RESULT, _portable(result, directory/'execution') if _is_owned(data) else result)
        files = {name: _digest(directory/name) for name in (INPUT, RESULT, 'worker.claim')}
        files.update({p.relative_to(directory).as_posix(): _digest(p) for p in (directory/'execution').rglob('*') if p.is_file()})
        files.update(submitted)
        _write_json(directory/'manifest.json', dict(manifest_version=1, kind=KIND, files=files,
            implementation_sha256=implementation, source_changed_during_run=False))
        _state(directory, 'complete', kind=KIND, physics='cartesian_cutoff_rf', input_sha256=submitted,
            tuning_status=result['status'], can_resume=result['can_resume'], computed_trials=len(result['trials']),
            numerical_validation='not_checked', elapsed_seconds=time.monotonic()-started)
        return result
    except Exception as exc:
        _state(directory, 'failed', kind=KIND, error=str(exc), elapsed_seconds=time.monotonic()-started)
        raise


if __name__ == '__main__':
    try:
        execute_prepared_planar_tune(Path(sys.argv[1]))
    except Exception:
        traceback.print_exc(); sys.exit(2)
