# SPDX-License-Identifier: Apache-2.0
"""Strict local GUI transport for owned Cartesian P2 comparison and tuning."""
import json
import re
from pathlib import Path
from .config import integer,keys
from .project import parse_json
from .saved_mode_tracking import _canonical
from .planar_curved_tracking import PlanarCurvedTrackingRequest
from .planar_curved_identity_recovery import PlanarCurvedIdentityRecoveryRequest
from .planar_curved_tracking_history import PlanarCurvedTrackingHistoryRequest
from .planar_curved_tracking_saved import _regular,_load
from .planar_curved_tracking_jobs import KIND as PAIR_KIND,read_planar_curved_tracking,_snapshot as pair_snapshot
from .planar_curved_tracking_history_jobs import KIND as HISTORY_KIND,read_planar_curved_history,_snapshot as history_snapshot
from .planar_curved_tuning import validate_planar_curved_tune
from .planar_curved_tuning_saved import replay_owned_planar_curved_tune
from .planar_curved_tuning_jobs import KIND as TUNE_KIND,read_planar_curved_tune_job,read_planar_curved_tune_job_checkpoint
from .planar_tuning_saved import _snapshot_trial

_FIELDS={
    'normalize-tracking':(('document',),('document',)),
    'start-tracking':(('document','previous_id','current_id'),('document','previous_id','current_id')),
    'tracking-result':(('id',),('id',)),
    'tracking-source':(('id','side'),('id','side')),
    'normalize-history':(('document',),('document',)),
    'start-history':(('document','step_ids'),('document','step_ids')),
    'extend-history':(('id','next_id','recovery'),('id','next_id')),
    'history-result':(('id',),('id',)),
    'history-source':(('id',),('id',)),
    'normalize-recovery':(('request',),('request',)),
    'recover-history':(('id','request'),('id','request')),
    'normalize-tune':(('request',),('request',)),
    'start-tune':(('request','max_new_trials'),('request',)),
    'tune-result':(('id',),('id',)),
    'tune-checkpoints':(('id',),('id',)),
    'open-tune-checkpoint':(('id','index'),('id','index')),
    'replay-tune':(('document',),('document',)),
    'resume-tune':(('document','max_new_trials'),('document',)),
    'tune-trial':(('document','index'),('document','index')),
}
ACTIONS={'planar-curved-'+name:list(fields[0]) for name,fields in _FIELDS.items()}
SELECTION='superfish_ng_planar_curved_tune_selection'


def _document(value):return parse_json(value) if isinstance(value,str) else value


def _job(manager,identifier,kind,*,stopped=False):
    directory=_regular(manager.directory(identifier),True);state=_load(directory/'job.json')
    statuses=('complete','cancelled','interrupted','failed') if stopped else ('complete',)
    if state.get('kind')!=kind or state.get('status') not in statuses:
        raise ValueError('select a stopped curved tuning job' if stopped else f'select a complete {kind} job')
    return directory


def _payload(result):return dict(request=result['request'],result=result)


def _import(manager,parent,snapshot,source,before):
    if before!=snapshot(parent):raise ValueError('curved selected original bytes changed before native import')
    identifier=manager.import_planar_result(source)
    if before!=snapshot(parent):raise ValueError('curved selected original bytes changed during native import')
    return dict(id=identifier)


def _selection(result,directory=None,index=None):
    selection=dict(format=SELECTION,selection_version=1,checkpoint=result,
        owner_job_directory=None if directory is None else str(directory),checkpoint_index=index)
    return dict(document=result,serialized=json.dumps(selection,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def _read_selection(value):
    """Bind a saved GUI selection to its actual stopped job, including zero trials."""
    data=_document(value)
    if type(data) is not dict:raise ValueError('curved tuning selection must be a JSON object')
    if data.get('format')!=SELECTION:
        result=replay_owned_planar_curved_tune(data)
        return result,None,None
    names=['format','selection_version','checkpoint','owner_job_directory','checkpoint_index']
    keys(data,names,names,'curved GUI tuning selection')
    if type(data['selection_version']) is not int or data['selection_version']!=1:
        raise ValueError('expected curved GUI selection_version 1')
    owner=data['owner_job_directory'];index=data['checkpoint_index']
    if owner is None:
        if index is not None:raise ValueError('unbound curved selection cannot declare a checkpoint index')
        return replay_owned_planar_curved_tune(data['checkpoint']),None,None
    if type(owner) is not str or not owner:raise ValueError('curved selection requires its original stopped job directory')
    integer(index,'checkpoint index',0);directory=_regular(owner,True)
    result=read_planar_curved_tune_job_checkpoint(directory,index)
    if _canonical(result)!=_canonical(data['checkpoint']):raise ValueError('curved saved selection differs from its bound original checkpoint')
    return result,directory,index


def planar_curved_response(manager,action,data):
    if action not in ACTIONS:raise ValueError('unknown curved planar operation')
    operation=action.removeprefix('planar-curved-');allowed,required=_FIELDS[operation]
    keys(data,allowed,required,'curved planar GUI request')
    if operation in ('normalize-tracking','start-tracking'):
        request=PlanarCurvedTrackingRequest.from_dict(_document(data['document']))
        if operation=='normalize-tracking':return request.to_dict()
        paths=[_job(manager,data[key],'planar_solve') for key in ('previous_id','current_id')]
        return dict(id=manager.start_planar_curved_tracking(*paths,request))
    if operation in ('tracking-result','tracking-source'):
        directory=_job(manager,data['id'],PAIR_KIND);before=pair_snapshot(directory)
        result=read_planar_curved_tracking(directory)
        if before!=pair_snapshot(directory):raise ValueError('curved comparison changed during GUI replay')
        if operation=='tracking-result':return _payload(result)
        side=data['side']
        if side not in ('previous','current'):raise ValueError('curved comparison side must be previous or current')
        return _import(manager,directory,pair_snapshot,directory/'execution'/side,before)
    if operation in ('normalize-recovery','recover-history'):
        recovery=PlanarCurvedIdentityRecoveryRequest.from_dict(_document(data['request']))
        if operation=='normalize-recovery':return recovery.to_dict()
        return dict(id=manager.recover_planar_curved_history(_job(manager,data['id'],HISTORY_KIND),recovery))
    if operation in ('normalize-history','start-history'):
        request=PlanarCurvedTrackingHistoryRequest.from_dict(_document(data['document']))
        if operation=='normalize-history':return request.to_dict()
        identifiers=data['step_ids']
        if type(identifiers) is not list or len(identifiers)!=request.step_count:
            raise ValueError('step_ids must contain exactly step_count curved comparison job IDs')
        return dict(id=manager.start_planar_curved_history([_job(manager,i,PAIR_KIND) for i in identifiers],request))
    if operation=='extend-history':
        recovery=None if data.get('recovery') is None else PlanarCurvedIdentityRecoveryRequest.from_dict(_document(data['recovery']))
        return dict(id=manager.extend_planar_curved_history(_job(manager,data['id'],HISTORY_KIND),
            _job(manager,data['next_id'],PAIR_KIND),recovery=recovery))
    if operation in ('history-result','history-source'):
        directory=_job(manager,data['id'],HISTORY_KIND);before=history_snapshot(directory)
        result=read_planar_curved_history(directory)
        if before!=history_snapshot(directory):raise ValueError('curved history changed during GUI replay')
        if operation=='history-result':return _payload(result)
        return _import(manager,directory,history_snapshot,directory/'execution'/f"step-{len(result['steps'])-1:04d}"/'current',before)
    if operation in ('normalize-tune','start-tune'):
        request=_document(data['request']);validate_planar_curved_tune(request)
        if operation=='normalize-tune':return parse_json(_canonical(request))
        return dict(id=manager.start_planar_curved_tune(request,max_new_trials=data.get('max_new_trials')))
    if operation=='tune-checkpoints':
        directory=_job(manager,data['id'],TUNE_KIND,stopped=True);execution=_regular(directory/'execution',True)
        indices=sorted(int(p.stem.split('-')[1]) for p in execution.glob('checkpoint-*.json')
            if re.fullmatch(r'checkpoint-[0-9]{3,}\.json',p.name) and p.name==f'checkpoint-{int(p.stem.split("-")[1]):03d}.json'
            and p.is_file() and not p.is_symlink())
        return dict(id=data['id'],indices=indices,verified=False)
    if operation in ('tune-result','open-tune-checkpoint'):
        directory=_job(manager,data['id'],TUNE_KIND,stopped=operation=='open-tune-checkpoint')
        if operation=='tune-result':result=read_planar_curved_tune_job(directory);index=len(result['trials'])
        else:index=integer(data['index'],'checkpoint index',0);result=read_planar_curved_tune_job_checkpoint(directory,index)
        return _selection(result,directory,index)
    result,directory,index=_read_selection(data['document'])
    if operation=='replay-tune':return _selection(result,directory,index)
    if operation=='resume-tune':
        if not result['can_resume']:raise ValueError('only a verified PAUSED curved checkpoint can resume')
        checkpoint=result if directory is None else directory/'execution'/f'checkpoint-{index:03d}.json'
        return dict(id=manager.start_planar_curved_tune(result['request'],checkpoint=checkpoint,max_new_trials=data.get('max_new_trials')))
    trial_index=integer(data['index'],'trial index')-1
    if trial_index>=len(result['trials']):raise ValueError('curved tune trial index is out of range')
    ids=result['trials'][trial_index]['current_mode_ids'];target=result['request']['mode_id']
    if target not in ids:raise ValueError('this curved trial has no individually confirmed target mode')
    path=_regular(result['trial_runs'][trial_index],True);before=_snapshot_trial(path)
    if before!=result['trial_sources_sha256'][trial_index]:raise ValueError('curved tune trial changed before import')
    _stable_tune(result)
    identifier=manager.import_planar_result(path)
    _stable_tune(result)
    return dict(id=identifier,mode=ids.index(target)+1)


def _stable_tune(result):
    for run,files in zip(result['trial_runs'],result['trial_sources_sha256']):
        if _snapshot_trial(_regular(run,True))!=files:raise ValueError('curved tune selected prefix changed during native import')
    if result['trial_runs']:
        from .planar_tuning_saved import _request_copy
        _request_copy(Path(result['trial_runs'][0]).parent,result['request'])
