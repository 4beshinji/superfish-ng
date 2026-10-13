# SPDX-License-Identifier: Apache-2.0
"""Owned Hphi tuning worker files and lifecycle, with explicit physical callbacks.

The caller declares file names, kind, physics, and the exact worker entry point.
Submission validation and native trials remain in each physical adapter. This
module changes no checkpoint schema, decision, FEM, or JobManager policy.
"""
from copy import deepcopy
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

from .artifact_provenance import atomic_write_json, sha256_file
from .input_validation import keys
from .json_codec import canonical_json, parse_json


@dataclass(frozen=True)
class OwnedTuningContract:
    """Trusted declaration by an adapter; no kind-to-physics discovery."""
    kind: str
    input_file: str
    result_file: str
    physics: str
    worker_module: str



def load_metadata(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('Hphi tune worker metadata must be regular files, not links')
    return parse_json(path.read_text(encoding='utf-8'))


def snapshot_owned_files(directory, contract):
    """Hash the owned worker files while rejecting links and undeclared roots."""
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('Hphi tune job directory must be regular')
    result = {}
    for name in (contract.input_file, contract.result_file, 'job.json', 'manifest.json'):
        result[name] = sha256_file(directory / name)
        load_metadata(directory / name)
    claim = directory / 'worker.claim'
    if claim.is_symlink() or not claim.is_file():
        raise ValueError('Hphi tune worker claim must be a regular file')
    result['worker.claim'] = sha256_file(claim)
    execution = directory / 'execution'
    if execution.is_symlink() or not execution.is_dir():
        raise ValueError('Hphi tune execution must be a regular directory')
    for path in execution.rglob('*'):
        if path.is_symlink():
            raise ValueError('Hphi tune execution files must not be linked')
        if path.is_file():
            result[path.relative_to(directory).as_posix()] = sha256_file(path)
    return result


def check_manifest_shape(manifest):
    names = ('manifest_version', 'kind', 'files', 'implementation_sha256', 'source_changed_during_run')
    keys(manifest, names, names, 'Hphi tune manifest')
    if type(manifest['manifest_version']) is not int or manifest['manifest_version'] != 1:
        raise ValueError('Hphi tune manifest_version must be 1')
    implementation = manifest['implementation_sha256']
    if not isinstance(implementation, dict) or not implementation or any((type(key) is not str or type(value) is not str or len(value) != 64 or any((char not in '0123456789abcdef' for char in value)) for key, value in implementation.items())) or (manifest['source_changed_during_run'] is not False):
        raise ValueError('Hphi tune requires stable implementation provenance')


def is_owned_tuning_job(directory, state, manifest, contract):
    return contract.kind in (state.get('kind'), manifest.get('kind')) or (directory / contract.input_file).is_file() or (directory / contract.result_file).is_file()


def start_tuning_worker(manager, request, *, max_new_trials=None, checkpoint=None, contract, validate_submission, write_state):
    """Submit a dedicated Hphi tuning worker after strict preflight."""
    with manager.lock:
        if manager.closed:
            raise ValueError('job manager is closed')
        data = validate_submission(deepcopy(dict(request=request, max_new_trials=max_new_trials, checkpoint=checkpoint)))
        identifier = time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:10]
        directory = manager.directory(identifier)
        directory.mkdir()
        atomic_write_json(directory / contract.input_file, data)
        submitted = {contract.input_file: sha256_file(directory / contract.input_file)}
        write_state(directory, 'queued', kind=contract.kind, input_sha256=submitted)
        try:
            with (directory / 'log.txt').open('x') as log:
                process = subprocess.Popen([sys.executable, '-m', contract.worker_module, str(directory)], stdout=log, stderr=subprocess.STDOUT, env={**os.environ, 'OPENBLAS_NUM_THREADS': '1'})
            manager.processes[identifier] = process
        except Exception as exc:
            write_state(directory, 'failed', kind=contract.kind, error=str(exc))
            raise
        return identifier


def execute_tuning_worker(directory, *, contract, validate_submission, execute_trials, prepare_result_document, write_state, implementation_hashes):
    """Run one queued Hphi tune directory in a separate worker process."""
    directory = Path(directory)
    state = load_metadata(directory / 'job.json')
    if state.get('status') != 'queued' or state.get('kind') != contract.kind:
        raise ValueError(f'Hphi tune worker requires a fresh queued {contract.kind} job')
    with (directory / 'worker.claim').open('x', encoding='utf-8') as stream:
        stream.write(str(os.getpid()) + '\n')
    started = time.monotonic()
    try:
        implementation = implementation_hashes()
        submitted = {contract.input_file: sha256_file(directory / contract.input_file)}
        if state.get('input_sha256') != submitted:
            raise ValueError('queued Hphi tune input changed before execution')
        data = validate_submission(load_metadata(directory / contract.input_file))
        write_state(directory, 'running', kind=contract.kind, input_sha256=submitted, stage='Hphi FEM frequency tuning and final mesh refinement')
        result = execute_trials(data['request'], directory / 'execution', max_new_trials=data['max_new_trials'], checkpoint=data['checkpoint'])
        if implementation != implementation_hashes() or submitted != {contract.input_file: sha256_file(directory / contract.input_file)}:
            raise RuntimeError('implementation or Hphi tune input changed during run')
        atomic_write_json(directory / contract.result_file, prepare_result_document(result))
        files = {name: sha256_file(directory / name) for name in (contract.input_file, contract.result_file, 'worker.claim')}
        files.update({path.relative_to(directory).as_posix(): sha256_file(path) for path in sorted((directory / 'execution').rglob('*')) if path.is_file()})
        atomic_write_json(directory / 'manifest.json', dict(manifest_version=1, kind=contract.kind, files=files, implementation_sha256=implementation, source_changed_during_run=False))
        write_state(directory, 'complete', kind=contract.kind, physics=contract.physics, scope=result['scope'], tuning_status=result['status'], can_resume=result['can_resume'], computed_trials=len(result['trials']), numerical_validation='not_checked', input_sha256=submitted, elapsed_seconds=time.monotonic() - started)
        return result
    except Exception as exc:
        write_state(directory, 'failed', kind=contract.kind, error=str(exc), elapsed_seconds=time.monotonic() - started)
        raise


def verify_tuning_worker(directory, state, manifest, *, contract, validate_owned_submission, read_result, snapshot_trial, validate_checkpoints):
    """Replay an Hphi worker and verify its state, ancestry, budget, and files."""
    directory = Path(directory).resolve()
    before = snapshot_owned_files(directory, contract)
    if state.get('status') != 'complete' or state.get('kind') != contract.kind or manifest.get('kind') != contract.kind:
        raise ValueError(f'Hphi tune state and manifest require complete kind={contract.kind}')
    check_manifest_shape(manifest)
    expected_files = {key: value for key, value in before.items() if key not in ('job.json', 'manifest.json')}
    if manifest['files'] != expected_files:
        raise ValueError('Hphi tune manifest must bind all request, checkpoint, and native files exactly')
    data = validate_owned_submission(load_metadata(directory / contract.input_file), directory / 'execution')
    result = read_result(directory / contract.result_file)
    if canonical_json(data['request']) != canonical_json(result['request']) or state.get('tuning_status') != result['status'] or state.get('can_resume') is not result['can_resume'] or (type(state.get('computed_trials')) is not int) or (state['computed_trials'] != len(result['trials'])) or (state.get('numerical_validation') != 'not_checked') or (state.get('physics') != contract.physics) or (state.get('scope') != result['scope']) or (state.get('input_sha256') != {contract.input_file: before[contract.input_file]}):
        raise ValueError('Hphi tune job summary differs from its verified checkpoint')
    previous = data['checkpoint']
    offset = 0 if previous is None else len(previous['trial_runs'])
    if previous is not None:
        if canonical_json(result['trial_sources_sha256'][:offset]) != canonical_json(previous['trial_sources_sha256']) or canonical_json(result['trials'][:offset]) != canonical_json(previous['trials']):
            raise ValueError('Hphi tune resume ancestry differs from submitted checkpoint')
    count = len(result['trials']) - offset
    limit = data['max_new_trials']
    if count < 1 or (limit is not None and count > limit) or (result['can_resume'] and (limit is None or count != limit)):
        raise ValueError('Hphi tune trial budget differs from the verified result')
    expected = {contract.input_file, contract.result_file, 'worker.claim'}
    for index, run in enumerate(result['trial_runs']):
        relative = f'execution/trial-{index + 1:03d}'
        if run != str(directory / relative):
            raise ValueError('Hphi tune trial is outside its owned execution directory')
        trial_hashes = snapshot_trial(directory / relative)
        if trial_hashes != result['trial_sources_sha256'][index]:
            raise ValueError('Hphi tune trial native hash differs from its checkpoint')
        expected.update((relative + '/' + name for name in trial_hashes))
    validate_checkpoints(directory, result, expected, offset)
    if set(expected_files) != expected:
        raise ValueError('Hphi tune execution contains missing or undeclared trial files')
    if load_metadata(directory / 'job.json') != state or load_metadata(directory / 'manifest.json') != manifest or before != snapshot_owned_files(directory, contract):
        raise ValueError('Hphi tune files changed during verification')
    return result


@dataclass(frozen=True)
class CheckpointPolicy:
    """Existing naming and prefix rules, explicitly declared by each adapter."""
    minimum_number: int
    canonical_names: bool
    complete_prefix: bool
    missing_prefix_message: str


def validate_checkpoint_prefixes(directory, result, expected_files, *,
                                 start_index, replay_checkpoint, policy):
    """Replay all declared checkpoint files under the adapter's existing policy."""
    execution = Path(directory) / "execution"
    request_copy = execution / "request.json"
    if request_copy.is_symlink() or not request_copy.is_file():
        raise ValueError("Hphi tune completion requires its owned request copy")
    expected_files.add(request_copy.relative_to(directory).as_posix())
    checkpoint_paths = sorted(execution.glob("checkpoint-*.json"))
    if not checkpoint_paths:
        raise ValueError("Hphi tune completion requires at least one checkpoint")
    trial_count = len(result["trials"])
    checkpoint_numbers = []
    for path in checkpoint_paths:
        try:
            number = int(path.stem.rsplit("-", 1)[1])
        except (IndexError, ValueError) as exc:
            raise ValueError("Hphi tune checkpoint has an invalid ordered name") from exc
        if ((policy.canonical_names and path.name != f"checkpoint-{number:03d}.json")
                or number < policy.minimum_number or number > trial_count):
            raise ValueError("Hphi tune checkpoint number is outside the verified trial prefix")
        checkpoint_numbers.append(number)
        prefix = replay_checkpoint(load_metadata(path), base_directory=execution)
        if len(prefix["trials"]) != number:
            raise ValueError("Hphi tune checkpoint prefix length differs from its name")
        expected = {key: value for key, value in result.items()}
        for key in ("trial_runs", "trial_sources_sha256", "trials"):
            expected[key] = expected[key][:number]
        expected["decision"] = prefix["decision"]
        expected["status"] = prefix["status"]
        expected["can_resume"] = prefix["can_resume"]
        if canonical_json(prefix) != canonical_json(expected):
            raise ValueError("Hphi tune saved checkpoint differs from its verified prefix")
    if policy.complete_prefix:
        if checkpoint_numbers != list(range(start_index, trial_count + 1)):
            raise ValueError(policy.missing_prefix_message)
    else:
        if checkpoint_numbers != sorted(set(checkpoint_numbers)):
            raise ValueError("Hphi tune checkpoint names must be distinct and ordered")
        if trial_count not in checkpoint_numbers:
            raise ValueError("Hphi tune completion is missing its final checkpoint")
    expected_files.update(path.relative_to(directory).as_posix() for path in checkpoint_paths)
