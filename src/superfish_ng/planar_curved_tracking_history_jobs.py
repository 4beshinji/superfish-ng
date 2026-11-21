# SPDX-License-Identifier: Apache-2.0
"""Owned curved history workers with original pairs and earlier-anchor replay."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
from .config import keys
from .jobs import _digest,_state,_write_json,_implementation_hashes
from .saved_mode_tracking import _canonical
from .planar_curved_tracking_saved import _regular,_load,curved_tracking_snapshot,read_owned_planar_curved_tracking
from .planar_curved_tracking_jobs import (INPUT as PAIR_INPUT,_snapshot as pair_job_snapshot,read_planar_curved_tracking)
from .planar_curved_identity_recovery import PlanarCurvedIdentityRecoveryRequest
from .planar_curved_tracking_history import (PlanarCurvedTrackingHistoryRequest,curved_history_snapshot,
    read_owned_planar_curved_history,execute_owned_planar_curved_history)

KIND='planar_curved_tracking_history'
INPUT='planar-curved-history-input.json'


def _pair_snapshot(path,kind):
    if kind=='owned_pair':return curved_tracking_snapshot(path)
    if kind=='comparison_job':return pair_job_snapshot(path)
    raise ValueError('curved history step requires an owned pair or a complete comparison job')


def _pair_path(path,kind):return path/'execution' if kind=='comparison_job' else path


def _source(path):
    path=_regular(path,True)
    kind='comparison_job' if (path/PAIR_INPUT).exists() or (path/PAIR_INPUT).is_symlink() else 'owned_pair'
    before=_pair_snapshot(path,kind)
    (read_planar_curved_tracking if kind=='comparison_job' else read_owned_planar_curved_tracking)(path)
    if before!=_pair_snapshot(path,kind):raise ValueError('curved history step changed during source verification')
    return dict(path=str(path),kind=kind,files=before)


def _submitted(directory):
    directory=_regular(directory,True);data=_load(directory/INPUT)
    names=['format','input_version','request','steps'];keys(data,names,names,'curved history job input')
    if data['format']!='superfish_ng_planar_curved_history_job_input' or type(data['input_version']) is not int or data['input_version']!=1:
        raise ValueError('expected curved history job input_version 1')
    request=PlanarCurvedTrackingHistoryRequest.from_dict(data['request'])
    if type(data['steps']) is not list or len(data['steps'])!=request.step_count:raise ValueError('curved history job requires exactly step_count sources')
    steps=_regular(directory/'steps',True);expected={f'step-{i:04d}' for i in range(request.step_count)}
    if {p.name for p in steps.iterdir()}!=expected:raise ValueError('curved history job requires exactly its ordered submitted steps')
    hashes={INPUT:_digest(directory/INPUT)}
    for index,source in enumerate(data['steps']):
        keys(source,['path','kind','files'],['path','kind','files'],'curved history job step source')
        if type(source['path']) is not str or not source['path']:raise ValueError('curved history step needs an informational origin')
        actual=_pair_snapshot(_regular(steps/f'step-{index:04d}',True),source['kind'])
        if actual!=source['files']:raise ValueError('curved history submitted step differs from original bytes')
        hashes.update({f'steps/step-{index:04d}/{name}':sha for name,sha in actual.items()})
    return data,hashes


def _pairs(directory,data):
    return [_pair_path(directory/'steps'/f'step-{i:04d}',source['kind']) for i,source in enumerate(data['steps'])]


def _snapshot(directory):
    directory=_regular(directory,True);expected={INPUT,'steps','execution','job.json','manifest.json','worker.claim'}
    entries={p.name for p in directory.iterdir()}
    if entries not in (expected,expected|{'log.txt'}):raise ValueError('complete curved history job has missing or undeclared entries')
    if 'log.txt' in entries:_regular(directory/'log.txt')
    _,result=_submitted(directory)
    for name in ('job.json','manifest.json','worker.claim'):result[name]=_digest(_regular(directory/name))
    result.update({f'execution/{name}':sha for name,sha in curved_history_snapshot(directory/'execution').items()})
    return result


def is_planar_curved_history(directory,state,manifest):
    return KIND in (state.get('kind'),manifest.get('kind')) or (directory/INPUT).exists() or (directory/INPUT).is_symlink()


def verify_planar_curved_history(directory,state,manifest):
    directory=_regular(directory,True);before=_snapshot(directory);implementation=_implementation_hashes()
    if state.get('status')!='complete' or state.get('kind')!=KIND or manifest.get('kind')!=KIND:
        raise ValueError('curved history state and manifest require complete kind=planar_curved_tracking_history')
    names=['manifest_version','kind','files','implementation_sha256','source_changed_during_run']
    keys(manifest,names,names,'curved history job manifest');creation=manifest['implementation_sha256']
    if (type(manifest['manifest_version']) is not int or manifest['manifest_version']!=1
            or manifest['source_changed_during_run'] is not False or type(creation) is not dict or not creation
            or any(type(k) is not str or type(v) is not str or len(v)!=64 or any(c not in '0123456789abcdef' for c in v) for k,v in creation.items())):
        raise ValueError('curved history job requires stable implementation provenance version 1')
    if manifest['files']!={k:v for k,v in before.items() if k not in ('job.json','manifest.json')}:
        raise ValueError('curved history job manifest must bind all submitted and executed ancestry bytes')
    data,submitted=_submitted(directory);result=read_owned_planar_curved_history(directory/'execution')
    if _canonical(data['request'])!=_canonical(result['request']):raise ValueError('curved history execution request differs from submission')
    snapshots=[curved_tracking_snapshot(path) for path in _pairs(directory,data)]
    if snapshots!=result['step_sha256']:raise ValueError('curved history execution ancestry differs from submitted original pairs')
    for path,source in zip(_pairs(directory,data),data['steps']):
        if source['kind']=='comparison_job':read_planar_curved_tracking(path.parent)
    if _load(directory/'execution/manifest.json')['implementation_sha256']!=creation:
        raise ValueError('curved history execution creator differs from its worker')
    if (state.get('input_sha256')!=submitted or state.get('physics')!='cartesian_cutoff_rf'
            or state.get('numerical_validation')!='not_checked' or state.get('tracking_status')!=result['status']
            or type(state.get('individual_ids_complete')) is not bool or state['individual_ids_complete']!=result['individual_ids_complete']
            or type(state.get('can_extend')) is not bool or state['can_extend']!=result['can_extend']
            or type(state.get('step_count')) is not int or state['step_count']!=len(result['steps'])):
        raise ValueError('curved history job summary differs from complete native/anchor replay')
    if before!=_snapshot(directory) or _load(directory/'job.json')!=state or _load(directory/'manifest.json')!=manifest:
        raise ValueError('curved history job changed during full replay')
    if implementation!=_implementation_hashes():raise RuntimeError('implementation changed during curved history job replay')
    return result


def read_planar_curved_history(directory):
    directory=_regular(directory,True)
    return verify_planar_curved_history(directory,_load(directory/'job.json'),_load(directory/'manifest.json'))


def _prepare(paths,request,directory):
    if type(request) is not PlanarCurvedTrackingHistoryRequest:raise ValueError('expected PlanarCurvedTrackingHistoryRequest')
    request=PlanarCurvedTrackingHistoryRequest.from_dict(request.to_dict())
    if type(paths) not in (list,tuple) or len(paths)!=request.step_count:raise ValueError('curved history job requires exactly step_count pairs')
    sources=[_source(path) for path in paths]
    if len({_pair_path(Path(s['path']),s['kind']) for s in sources})!=len(sources):raise ValueError('curved history job sources must be distinct original pairs')
    directory=Path(directory).absolute()
    if directory!=directory.resolve():raise ValueError('curved history job output must have no symbolic-link components')
    directory.mkdir(parents=True,exist_ok=False)
    data=dict(format='superfish_ng_planar_curved_history_job_input',input_version=1,request=request.to_dict(),steps=sources)
    try:
        _write_json(directory/INPUT,data);(directory/'steps').mkdir()
        for i,source in enumerate(sources):
            target=directory/'steps'/f'step-{i:04d}';target.mkdir();path=Path(source['path'])
            if _pair_snapshot(path,source['kind'])!=source['files']:raise ValueError('curved history job source changed before copying')
            for name in source['files']:
                destination=target/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path/name,destination)
            if _pair_snapshot(target,source['kind'])!=source['files']:raise ValueError('curved history job step changed during copying')
        for source in sources:
            if _pair_snapshot(Path(source['path']),source['kind'])!=source['files']:raise ValueError('curved history job source changed during complete copying')
        _,submitted=_submitted(directory);_state(directory,'queued',kind=KIND,input_sha256=submitted)
        for source in sources:
            if _pair_snapshot(Path(source['path']),source['kind'])!=source['files']:raise ValueError('curved history job source changed during queue publication')
        if submitted!=_submitted(directory)[1]:raise ValueError('curved history submitted input changed during queue publication')
    except Exception as exc:
        _state(directory,'failed',kind=KIND,error=str(exc));raise


def execute_prepared_planar_curved_history(directory):
    directory=_regular(directory,True);state=_load(directory/'job.json')
    if state.get('status')!='queued' or state.get('kind')!=KIND:raise ValueError('curved history worker requires a fresh queued planar_curved_tracking_history job')
    with (directory/'worker.claim').open('x') as stream:stream.write(str(os.getpid())+'\n')
    started=time.monotonic()
    try:
        implementation=_implementation_hashes();data,submitted=_submitted(directory)
        if state.get('input_sha256')!=submitted:raise ValueError('queued curved history input changed')
        _state(directory,'running',kind=KIND,input_sha256=submitted,stage='complete original Cartesian native chain and earlier-anchor E/H replay')
        result=execute_owned_planar_curved_history(_pairs(directory,data),PlanarCurvedTrackingHistoryRequest.from_dict(data['request']),directory/'execution')
        if submitted!=_submitted(directory)[1] or implementation!=_implementation_hashes():raise ValueError('curved history input or implementation changed during execution')
        files={**submitted,'worker.claim':_digest(directory/'worker.claim')}
        files.update({f'execution/{name}':sha for name,sha in curved_history_snapshot(directory/'execution').items()})
        _write_json(directory/'manifest.json',dict(manifest_version=1,kind=KIND,files=files,implementation_sha256=implementation,source_changed_during_run=False))
        _state(directory,'complete',kind=KIND,input_sha256=submitted,physics='cartesian_cutoff_rf',numerical_validation='not_checked',
            tracking_status=result['status'],individual_ids_complete=result['individual_ids_complete'],can_extend=result['can_extend'],
            step_count=len(result['steps']),elapsed_seconds=time.monotonic()-started)
        verified=read_planar_curved_history(directory)
        if submitted!=_submitted(directory)[1] or implementation!=_implementation_hashes():raise ValueError('curved history input or implementation changed during completion')
        return verified
    except Exception as exc:
        _state(directory,'failed',kind=KIND,error=str(exc),elapsed_seconds=time.monotonic()-started);raise


def execute_planar_curved_history(paths,request,directory):
    _prepare(paths,request,directory);return execute_prepared_planar_curved_history(directory)


def _history_source(history):
    history=_regular(history,True);managed=(history/INPUT).exists() or (history/INPUT).is_symlink()
    snapshot=_snapshot if managed else curved_history_snapshot;before=snapshot(history)
    previous=(read_planar_curved_history if managed else read_owned_planar_curved_history)(history)
    if before!=snapshot(history):raise ValueError('curved source history changed during verification')
    return history,previous,history/'execution' if managed else history,snapshot,before


def _prepare_derived(history,next_pair,recovery,directory):
    history,previous,owner,snapshot,before=_history_source(history)
    old=PlanarCurvedTrackingHistoryRequest.from_dict(previous['request']);events=list(old.identity_recoveries)
    if recovery is not None and type(recovery) is not PlanarCurvedIdentityRecoveryRequest:raise ValueError('expected PlanarCurvedIdentityRecoveryRequest')
    paths=[owner/f'step-{i:04d}' for i in range(old.step_count)]
    if next_pair is None:
        last=previous['steps'][-1]
        if recovery is None or last['status']!='PASS' or last['individual_ids_complete'] or any(e['after_step_index']==old.step_count-1 for e in events):
            raise ValueError('curved history recovery requires an unresolved passed final subspace without an earlier recovery event')
        events.append(dict(after_step_index=old.step_count-1,request=recovery.to_dict()));count=old.step_count
    else:
        if not previous['can_extend']:raise ValueError(previous['stop_reason'])
        if recovery is not None:events.append(dict(after_step_index=old.step_count,request=recovery.to_dict()))
        paths.append(next_pair);count=old.step_count+1
    request=PlanarCurvedTrackingHistoryRequest(count,old.max_steps,events)
    if before!=snapshot(history):raise ValueError('curved source history changed before derived submission')
    _prepare(paths,request,directory)
    if before!=snapshot(history):
        _state(Path(directory),'failed',kind=KIND,error='curved source history changed during derived submission')
        raise ValueError('curved source history changed during derived submission')


def extend_planar_curved_history(history,next_pair,directory,*,recovery=None):
    _prepare_derived(history,next_pair,recovery,directory);return execute_prepared_planar_curved_history(directory)


def recover_planar_curved_history(history,recovery,directory):
    _prepare_derived(history,None,recovery,directory);return execute_prepared_planar_curved_history(directory)


def _start(manager,prepare):
    with manager.lock:
        if manager.closed:raise ValueError('job manager is closed')
        identifier=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:10];directory=manager.directory(identifier)
        prepare(directory)
        try:
            with (directory/'log.txt').open('x') as log:
                manager.processes[identifier]=subprocess.Popen([sys.executable,'-m','superfish_ng.planar_curved_tracking_history_jobs',str(directory)],
                    stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'OPENBLAS_NUM_THREADS':'1'})
        except Exception as exc:
            _state(directory,'failed',kind=KIND,error=str(exc));raise
        return identifier


def start_planar_curved_history(manager,paths,request):return _start(manager,lambda d:_prepare(paths,request,d))


def start_extended_planar_curved_history(manager,history,next_pair,*,recovery=None):
    return _start(manager,lambda d:_prepare_derived(history,next_pair,recovery,d))


def start_recovered_planar_curved_history(manager,history,recovery):return _start(manager,lambda d:_prepare_derived(history,None,recovery,d))


if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('usage: python -m superfish_ng.planar_curved_tracking_history_jobs PREPARED_DIRECTORY')
    execute_prepared_planar_curved_history(sys.argv[1])
