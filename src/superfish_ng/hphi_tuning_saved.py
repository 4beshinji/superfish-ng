# SPDX-License-Identifier: Apache-2.0
"""Owned checkpoints, replay and resume for vacuum Hphi tuning.

Every completed trial owns a portable Hphi Project and the complete dedicated
native result.  Replay reconstructs the bracket decision and tracking report
from those files; it never calls the FEM solver.
"""
from copy import deepcopy
import hashlib
from pathlib import Path
import shutil

from .config import integer, keys
from .hphi_shape_tuning import tune_scope
from . import hphi_native
from .hphi_project import HphiProject
from .hphi_tuning import (
    _assess_trial,
    _tune_decision,
    trial_hphi_project,
    validate_hphi_tune,
)
from .jobs import _implementation_hashes, _write_json
from .project import parse_json
from .saved_mode_tracking import _canonical


FILES = hphi_native.FILES
read_hphi_run = hphi_native.read_hphi_run
save_hphi_run = hphi_native.save_hphi_run


def solve_hphi(case):
    """Keep the solve seam patchable while resolving the native dispatcher dynamically."""
    return hphi_native.solve_hphi(case)


CHECKPOINT_KEYS = (
    'format', 'schema_version', 'request', 'trial_runs',
    'trial_sources_sha256', 'trials', 'decision', 'status', 'can_resume',
    'scope',
)
NATIVE_FILES = FILES | {'manifest.json'}
TRIAL_FILES = {'project.json'} | {f'solution/{name}' for name in NATIVE_FILES}
SCOPE = 'vacuum_uniform_scale'


def _digest(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _snapshot_trial(directory):
    """Return hashes for exactly one owned Project/native trial."""
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('Hphi tune trial must be a regular directory')
    expected = set(TRIAL_FILES)
    found = {}
    directories = set()
    for path in directory.rglob('*'):
        if path.is_symlink():
            raise ValueError('Hphi tune owned trial files must not be symbolic links')
        if path.is_dir():
            directories.add(path.relative_to(directory).as_posix())
        if path.is_file():
            relative = path.relative_to(directory).as_posix()
            found[relative] = _digest(path)
    if directories != {'solution'} or set(found) != expected:
        raise ValueError(
            'Hphi tune trial must contain exactly project.json and five native solution files'
        )
    return {name: found[name] for name in sorted(found)}


def _resolve_trial_runs(runs, base_directory=None):
    if type(runs) is not list or any(type(value) is not str or not value.strip() for value in runs):
        raise ValueError('Hphi tune trial_runs must be a list of nonempty paths')
    if len(set(runs)) != len(runs):
        raise ValueError('Hphi tune trial paths must be distinct')
    base = None if base_directory is None else Path(base_directory).resolve()
    resolved = []
    for index, value in enumerate(runs):
        raw = Path(value)
        if raw.is_symlink():
            raise ValueError('Hphi tune trial paths must not be symbolic links')
        path = raw if raw.is_absolute() else (base / raw if base is not None else None)
        if path is None:
            raise ValueError('Hphi tune replay requires absolute owned trial paths')
        if path.is_symlink():
            raise ValueError('Hphi tune trial paths must not be symbolic links')
        canonical = path.resolve()
        if path != canonical:
            raise ValueError('Hphi tune trial paths must not contain symbolic-link components')
        if base is not None and not canonical.is_relative_to(base):
            raise ValueError('Hphi tune trial must be owned below the checkpoint directory')
        if base is not None and canonical.parent != base:
            raise ValueError('Hphi tune trial must be a direct child of the checkpoint directory')
        expected_name = f'trial-{index + 1:03d}'
        if canonical.name != expected_name:
            raise ValueError('Hphi tune trial paths must retain their ordered trial names')
        resolved.append(str(canonical))
    if resolved and len({str(Path(value).parent) for value in resolved}) != 1:
        raise ValueError('Hphi tune trial paths must have one owning output directory')
    return resolved


def _checkpoint(request, runs, sources, trials):
    decision = _tune_decision(request, trials)
    return dict(
        format='superfish_ng_hphi_tune_checkpoint',
        schema_version=1,
        request=deepcopy(request),
        trial_runs=list(runs),
        trial_sources_sha256=deepcopy(sources),
        trials=deepcopy(trials),
        decision=decision,
        status=decision['status'],
        can_resume=decision['status'] == 'PAUSED',
        scope=tune_scope(request),
    )


def _empty_checkpoint(request):
    return _checkpoint(request, [], [], [])


def _recompute(request, runs):
    """Rebuild a checkpoint from owned trial directories."""
    request = deepcopy(request)
    validate_hphi_tune(request)
    request = parse_json(_canonical(request))
    runs = _resolve_trial_runs(list(runs))
    if len(runs) > request['max_trials'] + 1:
        raise ValueError('Hphi tune trial paths exceed the search plus final trial budget')

    trials, sources, solutions = [], [], []
    for index, run in enumerate(runs):
        decision = _tune_decision(request, trials)
        if decision['status'] != 'PAUSED':
            raise ValueError('Hphi tune contains trials after a terminal decision')
        candidate = decision['next_trial']
        expected_project = trial_hphi_project(request, candidate['value'], candidate['phase'])
        source = _snapshot_trial(run)
        project = HphiProject.load(Path(run) / 'project.json')
        if project.to_dict() != expected_project.to_dict():
            raise ValueError('Hphi tune owned Project differs from its declared trial')
        solution = read_hphi_run(Path(run) / 'solution')
        if solution.case.to_dict() != expected_project.case.to_dict():
            raise ValueError('Hphi tune native Case differs from its declared trial Project')
        trial, recomputed_project = _assess_trial(request, trials, solutions, solution)
        if recomputed_project.to_dict() != project.to_dict():
            raise ValueError('Hphi tune trial Project changed during replay')
        trials.append(trial)
        sources.append(source)
        solutions.append(solution)
        if _snapshot_trial(run) != source:
            raise ValueError('Hphi tune owned trial changed during replay')

    result = _checkpoint(request, runs, sources, trials)
    return result


def _validate_checkpoint_shape(document):
    keys(document, CHECKPOINT_KEYS, CHECKPOINT_KEYS, 'Hphi tune checkpoint')
    if (document['format'] != 'superfish_ng_hphi_tune_checkpoint'
            or type(document['schema_version']) is not int
            or document['schema_version'] != 1):
        raise ValueError('expected superfish_ng_hphi_tune_checkpoint schema_version 1')
    validate_hphi_tune(document['request'])
    if document['scope'] != tune_scope(document['request']):
        raise ValueError('Hphi tune checkpoint scope must match the declared shape law')
    if type(document['trial_sources_sha256']) is not list:
        raise ValueError('Hphi tune trial_sources_sha256 must be a list')
    if type(document['trials']) is not list:
        raise ValueError('Hphi tune trials must be a list')
    if type(document['can_resume']) is not bool:
        raise ValueError('Hphi tune can_resume must be boolean')


def _check_request_copy(base_directory, request):
    if base_directory is None:
        return
    path = Path(base_directory) / 'request.json'
    if not path.exists():
        return
    if path.is_symlink() or not path.is_file():
        raise ValueError('Hphi tune request copy must be a regular file')
    before = _digest(path)
    copied = parse_json(path.read_text(encoding='utf-8'))
    if _canonical(copied) != _canonical(request):
        raise ValueError('Hphi tune request copy differs from checkpoint request')
    if _digest(path) != before:
        raise ValueError('Hphi tune request changed during replay')


def replay_hphi_tune(document, *, base_directory=None):
    """Replay all owned FEM/RF sources and return the verified checkpoint."""
    _validate_checkpoint_shape(document)
    request = deepcopy(document['request'])
    validate_hphi_tune(request)
    if base_directory is None and document['trial_runs']:
        first = Path(document['trial_runs'][0])
        if first.is_absolute():
            base_directory = first.parent
    runs = _resolve_trial_runs(document['trial_runs'], base_directory)
    normalized = deepcopy(document)
    normalized['trial_runs'] = runs
    _check_request_copy(base_directory, request)
    expected = _recompute(request, runs)
    if _canonical(normalized) != _canonical(expected):
        raise ValueError('Hphi tune checkpoint differs from owned native replay')
    return expected


def read_hphi_tune(path):
    """Read and fully replay a saved Hphi tune checkpoint."""
    path = Path(path)
    document = parse_json(path.read_text(encoding='utf-8'))
    # H06 workers keep the public result/checkpoint envelope at the job root
    # while owning trial directories below ``execution``.  H05 standalone
    # output keeps both at the same level.  Select the owning directory before
    # resolving absolute trial paths so both layouts replay identically.
    base_directory = path.parent
    if (base_directory / 'execution').is_dir():
        base_directory = base_directory / 'execution'
    return replay_hphi_tune(document, base_directory=base_directory)


def _copy_trial(source, target, expected_hashes):
    source = Path(source)
    target = Path(target)
    if _snapshot_trial(source) != expected_hashes:
        raise ValueError('Hphi tune prior owned trial changed before resume')
    target.mkdir(parents=True, exist_ok=False)
    for relative in sorted(TRIAL_FILES):
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / relative, destination)
    if _snapshot_trial(source) != expected_hashes or _snapshot_trial(target) != expected_hashes:
        raise ValueError('Hphi tune prior owned trial changed during copying')


def execute_hphi_tune(request, directory, *, max_new_trials=None, checkpoint=None):
    """Execute owned Hphi trials; resume always creates a fresh output tree."""
    request = deepcopy(request)
    validate_hphi_tune(request)
    request = parse_json(_canonical(request))
    if max_new_trials is not None:
        integer(max_new_trials, 'max_new_trials')

    if checkpoint is None:
        previous = _empty_checkpoint(request)
    else:
        if isinstance(checkpoint, (str, Path)):
            checkpoint = read_hphi_tune(checkpoint)
        previous = replay_hphi_tune(checkpoint)
        if _canonical(previous['request']) != _canonical(request):
            raise ValueError('Hphi tune resume request differs from checkpoint')
        if previous['status'] != 'PAUSED' or not previous['can_resume']:
            raise ValueError('only a verified PAUSED Hphi tune can resume')

    implementation = _implementation_hashes()
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    _write_json(directory / 'request.json', request)

    runs = []
    if checkpoint is not None:
        for index, source in enumerate(previous['trial_runs']):
            target = directory / f'trial-{index + 1:03d}'
            _copy_trial(source, target, previous['trial_sources_sha256'][index])
            runs.append(str(target.resolve()))
        previous = _recompute(request, runs)
        if previous['trials'] != replay_hphi_tune(checkpoint)['trials']:
            raise ValueError('Hphi tune prior trials changed while preparing resume')
        if runs:
            _write_json(directory / f'checkpoint-{len(runs):03d}.json', previous)

    count = 0
    while previous['status'] == 'PAUSED' and (max_new_trials is None or count < max_new_trials):
        index = len(runs)
        trial = previous['decision']['next_trial']
        run = directory / f'trial-{index + 1:03d}'
        try:
            project = trial_hphi_project(request, trial['value'], trial['phase'])
            run.mkdir(parents=True, exist_ok=False)
            project.save(run / 'project.json')
            solution = solve_hphi(project.case)
            save_hphi_run(project.case, solution, run / 'solution')
            result = _recompute(request, runs + [str(run.resolve())])
            if result['trials'][:len(previous['trials'])] != previous['trials']:
                raise ValueError('Hphi tune prior trials changed during execution')
            if result['trial_sources_sha256'][:len(previous['trial_sources_sha256'])] != previous['trial_sources_sha256']:
                raise ValueError('Hphi tune prior sources changed during execution')
            if implementation != _implementation_hashes():
                raise RuntimeError('implementation changed during Hphi tune execution')
            _write_json(directory / f'checkpoint-{index + 1:03d}.json', result)
        except Exception as exc:
            failure = dict(
                document_type='hphi_tune_failure',
                request=request,
                attempt=trial,
                trial_run=str(run.resolve()),
                preceding_trial_runs=runs,
                status='FAILED',
                error_type=type(exc).__name__,
                error=str(exc),
                scope='failed trial is not a frequency evaluation; prior checkpoints remain separate',
            )
            _write_json(directory / f'failure-{index + 1:03d}.json', failure)
            raise
        previous = result
        runs.append(str(run.resolve()))
        count += 1
    return previous
