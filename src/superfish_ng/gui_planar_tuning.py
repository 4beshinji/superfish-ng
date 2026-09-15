# SPDX-License-Identifier: Apache-2.0
"""Dedicated planar tuning transport, stopped checkpoints and native trials."""
import json
import re
import hashlib
from .config import keys,integer
from .jobs import read_job
from .project import parse_json
from .planar_tuning import read_planar_tune as read_tune,replay_planar_tune as replay_tune,validate_planar_tune
from .saved_mode_tracking import _canonical


def _checkpoint_directory(manager,identifier):
    directory=manager.directory(identifier)
    state=manager.status(identifier,verify=False)
    if state.get('kind')!='planar_tune' or state.get('status') not in ('complete','cancelled','interrupted','failed'):
        raise ValueError('select a stopped tuning job before opening checkpoints')
    execution=directory/'execution'
    if execution.is_symlink():raise ValueError('tuning execution directory must not be a symlink')
    return directory,execution


def _saved_checkpoint(manager,identifier,index):
    integer(index,'checkpoint index')
    directory,execution=_checkpoint_directory(manager,identifier)
    path=execution/f'checkpoint-{index:03d}.json'
    if path.is_symlink():raise ValueError('tuning checkpoint must not be a symlink')
    request_path=directory/'planar-tune-request.json'
    if request_path.is_symlink():raise ValueError('tuning job request must not be a symlink')
    original=path.read_bytes();submitted=request_path.read_bytes()
    state=manager.status(identifier,verify=False)
    # Completed jobs retain their submitted envelope hash. Cancellation and
    # interruption in the shared manager retain only the stopped status; those
    # checkpoints still require full request, native ancestry and owned paths.
    if 'input_sha256' in state and state['input_sha256']!={'planar-tune-request.json':hashlib.sha256(submitted).hexdigest()}:
        raise ValueError('planar tune submitted input changed before checkpoint verification')
    from .planar_tuning_jobs import _input
    data=_input(parse_json(submitted.decode('utf-8')));result=replay_tune(parse_json(original.decode('utf-8')))
    previous=data['checkpoint'];offset=0 if previous is None else len(previous['trial_runs'])
    if _canonical(data['request'])!=_canonical(result['request']):
        raise ValueError('checkpoint request differs from selected tuning job')
    if len(result['trial_runs'])!=index or index<=offset:
        raise ValueError('checkpoint trial count differs from selected tuning job')
    if previous is not None and any(_canonical(result[key][:offset])!=_canonical(previous[key])
                                   for key in ('trial_runs','trial_sources_sha256','trials')):
        raise ValueError('checkpoint ancestry differs from selected tuning job')
    for i in range(offset,index):
        if result['trial_runs'][i]!=str(execution/f'trial-{i+1:03d}'):
            raise ValueError('checkpoint trial belongs to another tuning job')
    if original!=path.read_bytes() or submitted!=request_path.read_bytes():
        raise ValueError('tuning checkpoint or job request changed during verification')
    return result


def planar_tuning_response(manager,action,data):
    fields={'planar-normalize-tune':(('request',),('request',)),
        'planar-tune-trial':(('document','index'),('document','index')),
        'planar-start-tune':(('request','max_new_trials'),('request',)),
        'planar-resume-tune':(('document','max_new_trials'),('document',)),
        'planar-tune-result':(('id',),('id',)), 'planar-replay-tune':(('document',),('document',)),
        'planar-tune-checkpoints':(('id',),('id',)),
        'planar-open-tune-checkpoint':(('id','index'),('id','index'))}
    if action not in fields:raise ValueError('unknown tuning operation')
    allowed,required=fields[action];keys(data,allowed,required,'GUI tuning')
    if action in ('planar-normalize-tune','planar-start-tune'):
        request=data['request']
        if isinstance(request,str):request=parse_json(request)
        validate_planar_tune(request)
        if action=='planar-normalize-tune':return parse_json(_canonical(request))
        return dict(id=manager.start_planar_tune(request,max_new_trials=data.get('max_new_trials')))
    if action=='planar-tune-checkpoints':
        _,execution=_checkpoint_directory(manager,data['id'])
        indices=sorted(int(p.stem.split('-')[1]) for p in execution.glob('checkpoint-*.json')
                       if re.fullmatch(r'checkpoint-[0-9]{3,}\.json',p.name)
                       and p.name==f'checkpoint-{int(p.stem.split("-")[1]):03d}.json'
                       and not p.is_symlink() and p.is_file())
        return dict(id=data['id'],indices=indices,verified=False)
    if action=='planar-open-tune-checkpoint':
        result=_saved_checkpoint(manager,data['id'],data['index'])
    elif action=='planar-tune-result':
        directory=manager.directory(data['id']);state=read_job(directory)
        if state['status']!='complete' or state.get('kind')!='planar_tune':
            raise ValueError('select a completed tune job; partial checkpoints can be opened separately')
        result=read_tune(directory/'planar-tune-results.json')
    else:
        document=data['document']
        if isinstance(document,str):document=parse_json(document)
        result=replay_tune(document)
        if action=='planar-tune-trial':
            index=integer(data['index'],'trial index')-1
            if index>=len(result['trials']):raise ValueError('planar tune trial index is out of range')
            trial=result['trials'][index];ids=trial['current_mode_ids'];target=result['request']['mode_id']
            if target not in ids:raise ValueError('this trial has no individually confirmed target mode')
            from .planar_jobs import _job_hashes
            from pathlib import Path
            path=Path(result['trial_runs'][index]);before=_job_hashes(path)
            if before!=result['trial_sources_sha256'][index]:raise ValueError('planar tune trial changed before import')
            identifier=manager.import_planar_result(path)
            if before!=_job_hashes(path):raise ValueError('planar tune trial changed during import')
            return dict(id=identifier,mode=ids.index(target)+1)
        if action=='planar-resume-tune':
            return dict(id=manager.start_planar_tune(result['request'],checkpoint=result,max_new_trials=data.get('max_new_trials')))
    return dict(document=result,serialized=json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
