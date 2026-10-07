# SPDX-License-Identifier: Apache-2.0
"""Portable owned Cartesian tuning checkpoints and fresh-owner resumption.

The native planar verifier restores the saved fields, FEM spectrum and RF
quantities. Copying a completed trial preserves every byte and does not claim
that the receiving owner executed it.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import tempfile

from .config import integer, keys
from .jobs import _digest, _implementation_hashes
from .project import parse_json
from .saved_mode_tracking import _canonical
from .planar_jobs import REQUIRED, execute_planar_project
from .planar_tuning import _assemble, trial_planar_project, validate_planar_tune

CHECKPOINT_KEYS = ('format', 'schema_version', 'request', 'trial_runs',
                   'trial_sources_sha256', 'trials', 'decision', 'status',
                   'can_resume', 'scope')
TRIAL_FILES = REQUIRED | {'job.json', 'manifest.json', 'worker.claim'}


def _snapshot_trial(directory):
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('owned planar tune trial must be a regular directory')
    found, directories = {}, set()
    for path in directory.rglob('*'):
        if path.is_symlink():
            raise ValueError('owned planar tune trial files must not be symbolic links')
        relative = path.relative_to(directory).as_posix()
        if path.is_dir():
            directories.add(relative)
        elif path.is_file():
            found[relative] = _digest(path)
        else:
            raise ValueError('owned planar tune trial entries must be regular files or directories')
    if directories != {'solution'} or set(found) != TRIAL_FILES:
        raise ValueError('owned planar tune trial must contain exactly Project, completed job metadata, claim and five native files')
    return {key: found[key] for key in sorted(found)}


def _resolve_trial_runs(runs, base_directory=None):
    if type(runs) is not list or any(type(v) is not str or not v for v in runs):
        raise ValueError('owned planar tune trial_runs require nonempty paths')
    if len(set(runs)) != len(runs):
        raise ValueError('owned planar tune trial paths must be distinct')
    base = None
    if base_directory is not None:
        raw_base = Path(base_directory)
        base = raw_base.absolute()
        if base != base.resolve() or raw_base.is_symlink() or not base.is_dir():
            raise ValueError('owned planar tune base directory must be regular without link components')
    resolved = []
    for index, value in enumerate(runs):
        name = f'trial-{index+1:03d}'
        raw = Path(value)
        if raw.is_absolute():
            path = raw
            if value != str(path.resolve()):
                raise ValueError('owned planar tune trial paths must be canonical without link components')
        elif base is not None and value == name:
            path = base/raw
        else:
            raise ValueError('owned planar tune relative trial paths must be ordered direct children of a declared owner')
        if path.is_symlink() or path != path.resolve():
            raise ValueError('owned planar tune trial paths must not contain symbolic-link components')
        if path.name != name or (base is not None and path.parent != base):
            raise ValueError('owned planar tune trial is outside its ordered owning directory')
        resolved.append(str(path))
    if resolved and len({str(Path(v).parent) for v in resolved}) != 1:
        raise ValueError('owned planar tune trials must have one owning directory')
    return resolved


def _request_copy(owner, request):
    if owner is None:
        return
    path = Path(owner)/'request.json'
    if path.is_symlink() or not path.is_file():
        raise ValueError('owned planar tune requires a regular original request copy')
    before = _digest(path)
    if _canonical(parse_json(path.read_text(encoding='utf-8'))) != _canonical(request):
        raise ValueError('owned planar tune request copy differs from checkpoint request')
    if before != _digest(path):
        raise ValueError('owned planar tune request changed during replay')


def _owned_assemble(request, runs):
    validate_planar_tune(request)
    if type(runs) is not list or len(runs) > request['max_trials']+1:
        raise ValueError('owned planar tune trial paths exceed the search plus final trial budget')
    runs = _resolve_trial_runs(runs)
    before = [_snapshot_trial(v) for v in runs]
    result = _assemble(request, runs)
    if any({k: hashes[k] for k in old} != old
           for old, hashes in zip(result['trial_sources_sha256'], before)):
        raise ValueError('owned planar tune native changed during physical replay')
    if before != [_snapshot_trial(v) for v in runs]:
        raise ValueError('owned planar tune sources changed during complete replay')
    result.update(schema_version=2, trial_sources_sha256=before)
    return result


def replay_owned_planar_tune(document, *, base_directory=None):
    keys(document, CHECKPOINT_KEYS, CHECKPOINT_KEYS, 'owned planar tune checkpoint')
    if (document['format'] != 'superfish_ng_planar_tune_checkpoint'
            or type(document['schema_version']) is not int or document['schema_version'] != 2):
        raise ValueError('expected owned planar tune checkpoint schema_version 2')
    validate_planar_tune(document['request'])
    if document['request']['schema_version'] != 4:
        raise ValueError('owned planar checkpoint version 2 requires tune request version 4')
    runs = _resolve_trial_runs(document['trial_runs'], base_directory)
    owner = base_directory if base_directory is not None else (Path(runs[0]).parent if runs else None)
    _request_copy(owner, document['request'])
    normalized = deepcopy(document); normalized['trial_runs'] = runs
    expected = _owned_assemble(document['request'], runs)
    if _canonical(normalized) != _canonical(expected):
        raise ValueError('owned planar tune checkpoint differs from complete native replay')
    _request_copy(owner, document['request'])
    return expected


def read_owned_planar_tune(path, *, base_directory=None):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('owned planar tune checkpoint must be a regular file')
    before = _digest(path)
    document = parse_json(path.read_text(encoding='utf-8'))
    keys(document, CHECKPOINT_KEYS, CHECKPOINT_KEYS, 'owned planar tune checkpoint')
    runs = document['trial_runs']
    if type(runs) is not list or runs != [f'trial-{i+1:03d}' for i in range(len(runs))]:
        raise ValueError('saved owned planar tune paths must be ordered relative trial names')
    result = replay_owned_planar_tune(document, base_directory=path.parent if base_directory is None else base_directory)
    if before != _digest(path):
        raise ValueError('owned planar tune checkpoint changed during replay')
    return result


def _portable(document, owner):
    result = deepcopy(document)
    runs = _resolve_trial_runs(result['trial_runs'], owner)
    result['trial_runs'] = [Path(v).name for v in runs]
    return result


def _write(path, document, *, trailing_newline=True):
    """Publish complete JSON atomically without replacing an existing target.

    An abruptly killed producer may leave a private staging file. It never
    exposes that partial file as a checkpoint or completed owned artifact.
    """
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                prefix='.planar-json-', suffix='.tmp', dir=path.parent,
                delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(document, stream, indent=2, allow_nan=False)
            if trailing_newline:
                stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink()


def _copy_trial(source, target, expected):
    if _snapshot_trial(source) != expected:
        raise ValueError('owned planar tune prior trial changed before copying')
    target = Path(target); target.mkdir(parents=True, exist_ok=False)
    for relative in sorted(TRIAL_FILES):
        destination = target/relative; destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(source)/relative, destination)
    if _snapshot_trial(source) != expected or _snapshot_trial(target) != expected:
        raise ValueError('owned planar tune prior trial changed during copying')


def execute_owned_planar_tune(request, directory, *, max_new_trials=None, checkpoint=None):
    request = parse_json(_canonical(deepcopy(request)))
    validate_planar_tune(request)
    if request['schema_version'] != 4:
        raise ValueError('owned planar tuning currently requires request version 4')
    if max_new_trials is not None:
        integer(max_new_trials, 'max_new_trials')
    if isinstance(checkpoint, (str, Path)):
        checkpoint = read_owned_planar_tune(checkpoint)
    previous = _owned_assemble(request, []) if checkpoint is None else replay_owned_planar_tune(checkpoint)
    if _canonical(previous['request']) != _canonical(request):
        raise ValueError('owned planar tune resume request differs from checkpoint')
    if not previous['can_resume']:
        raise ValueError('only a verified PAUSED owned planar tune can resume')
    implementation = _implementation_hashes()
    directory = Path(directory).resolve(); directory.mkdir(parents=True, exist_ok=False)
    _write(directory/'request.json', request)
    runs = []
    for index, source in enumerate(previous['trial_runs']):
        target = directory/f'trial-{index+1:03d}'
        _copy_trial(source, target, previous['trial_sources_sha256'][index]); runs.append(str(target))
    copied = _owned_assemble(request, runs)
    for key in ('request', 'trial_sources_sha256', 'trials', 'decision', 'status', 'can_resume'):
        if _canonical(copied[key]) != _canonical(previous[key]):
            raise ValueError('owned planar tune prefix changed while preparing resume')
    previous = copied
    _write(directory/f'checkpoint-{len(runs):03d}.json', _portable(previous, directory))
    count = 0
    while previous['can_resume'] and (max_new_trials is None or count < max_new_trials):
        index = len(runs); trial = previous['decision']['next_trial']; run = directory/f'trial-{index+1:03d}'
        try:
            execute_planar_project(trial_planar_project(request, trial['value'], trial['phase']), run)
            result = _owned_assemble(request, runs+[str(run)])
            if (result['trial_sources_sha256'][:index] != previous['trial_sources_sha256']
                    or result['trials'][:index] != previous['trials']):
                raise ValueError('owned planar tune prior sources or decisions changed during execution')
            if implementation != _implementation_hashes():
                raise RuntimeError('implementation changed during owned planar tune execution')
            _write(directory/f'checkpoint-{index+1:03d}.json', _portable(result, directory))
        except Exception as exc:
            _write(directory/f'failure-{index+1:03d}.json', dict(request=request, attempt=trial,
                trial_run=run.name, preceding_trial_runs=[Path(v).name for v in runs], status='FAILED',
                error_type=type(exc).__name__, error=str(exc),
                scope='failed trial is not a frequency evaluation; preceding owned checkpoint remains replayable'))
            raise
        previous = result; runs.append(str(run)); count += 1
    return previous
