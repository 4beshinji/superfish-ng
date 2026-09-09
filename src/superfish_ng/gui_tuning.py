# SPDX-License-Identifier: Apache-2.0
"""GUI transport for managed tuning and exact checkpoint replay."""
import json
import re
from .config import keys,integer
from .jobs import read_job
from .project import parse_json
from .tuning import read_tune,replay_tune
from .saved_mode_tracking import _canonical


def _checkpoint_directory(manager,identifier):
    directory=manager.directory(identifier)
    state=manager.status(identifier,verify=False)
    if state.get('kind')!='tune' or state.get('status') not in ('complete','cancelled','interrupted','failed'):
        raise ValueError('select a stopped tuning job before opening checkpoints')
    execution=directory/'execution'
    if execution.is_symlink():raise ValueError('tuning execution directory must not be a symlink')
    return directory,execution


def _saved_checkpoint(manager,identifier,index):
    integer(index,'checkpoint index')
    directory,execution=_checkpoint_directory(manager,identifier)
    path=execution/f'checkpoint-{index:03d}.json'
    if path.is_symlink():raise ValueError('tuning checkpoint must not be a symlink')
    request_path=directory/'tune-request.json'
    if request_path.is_symlink():raise ValueError('tuning job request must not be a symlink')
    original=path.read_bytes();submitted=request_path.read_bytes()
    data=parse_json(submitted.decode('utf-8'));result=replay_tune(parse_json(original.decode('utf-8')))
    previous=data['checkpoint'];offset=0 if previous is None else len(previous['trial_runs'])
    if _canonical(data['request'])!=_canonical(result['request']):
        raise ValueError('checkpoint request differs from selected tuning job')
    if len(result['trial_runs'])!=index or index<=offset:
        raise ValueError('checkpoint trial count differs from selected tuning job')
    if previous is not None and any(_canonical(result[key][:offset])!=_canonical(previous[key])
                                   for key in ('trial_runs','trial_sources_sha256')):
        raise ValueError('checkpoint ancestry differs from selected tuning job')
    for i in range(offset,index):
        if result['trial_runs'][i]!=str(execution/f'trial-{i+1:03d}'):
            raise ValueError('checkpoint trial belongs to another tuning job')
    if original!=path.read_bytes() or submitted!=request_path.read_bytes():
        raise ValueError('tuning checkpoint or job request changed during verification')
    return result


def tuning_response(manager,action,data):
    fields={'start-tune':(('request','max_new_trials'),('request',)),
        'resume-tune':(('document','max_new_trials'),('document',)),
        'tune-result':(('id',),('id',)), 'replay-tune':(('document',),('document',)),
        'tune-checkpoints':(('id',),('id',)),
        'open-tune-checkpoint':(('id','index'),('id','index'))}
    if action not in fields:raise ValueError('unknown tuning operation')
    allowed,required=fields[action];keys(data,allowed,required,'GUI tuning')
    if action=='start-tune':return dict(id=manager.start_tune(data['request'],max_new_trials=data.get('max_new_trials')))
    if action=='tune-checkpoints':
        _,execution=_checkpoint_directory(manager,data['id'])
        indices=sorted(int(p.stem.split('-')[1]) for p in execution.glob('checkpoint-*.json')
                       if re.fullmatch(r'checkpoint-[0-9]{3,}\.json',p.name)
                       and p.name==f'checkpoint-{int(p.stem.split("-")[1]):03d}.json'
                       and not p.is_symlink() and p.is_file())
        return dict(id=data['id'],indices=indices,verified=False)
    if action=='open-tune-checkpoint':
        result=_saved_checkpoint(manager,data['id'],data['index'])
    elif action=='tune-result':
        directory=manager.directory(data['id']);state=read_job(directory)
        if state['status']!='complete' or state.get('kind')!='tune':
            raise ValueError('select a completed tune job; partial checkpoints can be opened separately')
        result=read_tune(directory/'tune-results.json')
    else:
        document=data['document']
        if isinstance(document,str):document=parse_json(document)
        result=replay_tune(document)
        if action=='resume-tune':
            return dict(id=manager.start_tune(result['request'],checkpoint=result,max_new_trials=data.get('max_new_trials')))
    return dict(document=result,serialized=json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
