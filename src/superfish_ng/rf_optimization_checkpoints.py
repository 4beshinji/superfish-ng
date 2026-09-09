# SPDX-License-Identifier: Apache-2.0
"""Stopped RF optimization checkpoint discovery and verified ownership."""
import re
from .config import integer
from .project import parse_json
from .rf_optimization import replay_rf_optimization
from .rf_optimization_jobs import _job_input
from .saved_mode_tracking import _canonical


def _checkpoint_directory(manager,identifier):
    directory=manager.directory(identifier)
    state=manager.status(identifier,verify=False)
    if state.get('kind')!='rf_optimization' or state.get('status') not in ('complete','cancelled','interrupted','failed'):
        raise ValueError('select a stopped RF optimization job before opening checkpoints')
    execution=directory/'execution'
    if execution.is_symlink():raise ValueError('RF optimization execution directory must not be a symlink')
    return directory,execution


def open_optimization_checkpoint(manager,identifier,index):
    integer(index,'checkpoint index')
    directory,execution=_checkpoint_directory(manager,identifier)
    path=execution/f'checkpoint-{index:03d}.json'
    if path.is_symlink():raise ValueError('RF optimization checkpoint must not be a symlink')
    request_path=directory/'rf-optimization-request.json'
    if request_path.is_symlink():raise ValueError('RF optimization job request must not be a symlink')
    original=path.read_bytes();submitted=request_path.read_bytes()
    data=parse_json(submitted.decode('utf-8'));result=replay_rf_optimization(parse_json(original.decode('utf-8')))
    _job_input(data)
    previous=data['checkpoint'];offset=0 if previous is None else len(previous['trial_directories'])
    if _canonical(data['request'])!=_canonical(result['request']):
        raise ValueError('checkpoint request differs from selected RF optimization job')
    limit=data['max_new_trials']
    if limit is not None and index-offset>limit:
        raise ValueError('checkpoint exceeds selected RF optimization job trial budget')
    if len(result['trial_directories'])!=index or index<=offset:
        raise ValueError('checkpoint trial count differs from selected RF optimization job')
    if previous is not None and any(_canonical(result[key][:offset])!=_canonical(previous[key])
                                   for key in ('trial_directories','trial_sources_sha256')):
        raise ValueError('checkpoint ancestry differs from selected RF optimization job')
    for i in range(offset,index):
        if result['trial_directories'][i]!=str(execution/f'trial-{i+1:03d}'):
            raise ValueError('checkpoint trial belongs to another RF optimization job')
    if original!=path.read_bytes() or submitted!=request_path.read_bytes():
        raise ValueError('RF optimization checkpoint or job request changed during verification')
    return result



def list_optimization_checkpoints(manager,identifier):
    """List filenames only; opening performs full native replay and ownership checks."""
    _,execution=_checkpoint_directory(manager,identifier)
    indices=sorted(int(p.stem.split('-')[1]) for p in execution.glob('checkpoint-*.json')
        if re.fullmatch(r'checkpoint-[0-9]{3,}\.json',p.name)
        and p.name==f'checkpoint-{int(p.stem.split("-")[1]):03d}.json'
        and not p.is_symlink() and p.is_file())
    return dict(id=identifier,indices=indices,verified=False)
