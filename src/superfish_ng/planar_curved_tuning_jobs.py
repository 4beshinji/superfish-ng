# SPDX-License-Identifier: Apache-2.0
"""Owned curved Cartesian tuning workers and stopped-job checkpoint binding."""
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
from .config import integer,keys
from .jobs import _digest,_state,_write_json,_implementation_hashes
from .saved_mode_tracking import _canonical
from .tuning import _decision
from .planar_tuning_saved import _snapshot_trial,_write
from .planar_curved_tracking_saved import _regular,_load
from .planar_curved_tuning import validate_planar_curved_tune,_json_types
from .planar_curved_tuning_saved import (FORMAT,CHECKPOINT_KEYS,_read_owned,_verified,_copy_verified,_portable,
    read_owned_planar_curved_tune,execute_owned_planar_curved_tune)

KIND='planar_curved_tune'
INPUT='planar-curved-tune-input.json'
RESULT='planar-curved-tune-results.json'
SEAL='submission.json'
START='worker-start.json'


def _provenance(value):
    if type(value) is not dict or not value or any(type(k) is not str or type(v) is not str or len(v)!=64 or any(c not in '0123456789abcdef' for c in v) for k,v in value.items()):
        raise ValueError('curved tune requires a complete implementation hash provenance map')


def _data(data):
    _json_types(data);names=['format','input_version','request','max_new_trials','checkpoint']
    keys(data,names,names,'curved tune job input')
    if data['format']!='superfish_ng_planar_curved_tune_job_input' or type(data['input_version']) is not int or data['input_version']!=1:
        raise ValueError('expected curved tune job input_version 1')
    validate_planar_curved_tune(data['request'])
    if data['max_new_trials'] is not None:integer(data['max_new_trials'],'max_new_trials')
    previous=data['checkpoint']
    if previous is not None:
        keys(previous,CHECKPOINT_KEYS,CHECKPOINT_KEYS,'curved tune submitted checkpoint')
        if previous['format']!=FORMAT or type(previous['schema_version']) is not int or previous['schema_version']!=1:
            raise ValueError('curved worker requires an owned checkpoint schema_version 1')
        runs=previous['trial_runs']
        if type(runs) is not list or runs!=[f'trial-{i+1:03d}' for i in range(len(runs))]:raise ValueError('submitted curved prefix requires ordered portable trial names')
        if previous['status']!='PAUSED' or previous['can_resume'] is not True:raise ValueError('only a verified PAUSED owned curved tune can resume')
        if _canonical(previous['request'])!=_canonical(data['request']):raise ValueError('curved tune resume request differs from checkpoint')
    return data


def _submitted(directory):
    directory=_regular(directory,True);data=_data(_load(directory/INPUT));hashes={INPUT:_digest(directory/INPUT)}
    previous=data['checkpoint'];ancestry=directory/'ancestry'
    if previous is None:
        if ancestry.exists() or ancestry.is_symlink():raise ValueError('curved tune job has undeclared ancestry')
    else:
        ancestry=_regular(ancestry,True);count=len(previous['trial_runs']);checkpoint=f'checkpoint-{count:03d}.json'
        if {p.name for p in ancestry.iterdir()}!={'request.json',checkpoint,*previous['trial_runs']}:
            raise ValueError('curved tune ancestry requires exactly request, checkpoint and ordered original trials')
        if _canonical(_load(ancestry/'request.json'))!=_canonical(data['request']) or _canonical(_load(ancestry/checkpoint))!=_canonical(previous):
            raise ValueError('curved tune ancestry metadata differs from submitted prefix')
        for name in ('request.json',checkpoint):hashes[f'ancestry/{name}']=_digest(ancestry/name)
        snapshots=[]
        for name in previous['trial_runs']:
            files=_snapshot_trial(_regular(ancestry/name,True));snapshots.append(files)
            hashes.update({f'ancestry/{name}/{key}':value for key,value in files.items()})
        if snapshots!=previous['trial_sources_sha256']:raise ValueError('curved tune submitted ancestry differs from original native bytes')
    return data,hashes


def _sealed(directory):
    data,hashes=_submitted(directory);seal=_load(directory/SEAL)
    names=['format','submission_version','files'];keys(seal,names,names,'curved tune submission seal')
    if seal['format']!='superfish_ng_planar_curved_tune_submission' or type(seal['submission_version']) is not int or seal['submission_version']!=1 or seal['files']!=hashes:
        raise ValueError('curved tune submitted input changed from its sealed original snapshot')
    return data,hashes


def _start_record(directory,submitted):
    record=_load(directory/START);names=['format','start_version','kind','input_sha256','implementation_sha256','worker_claim_sha256']
    keys(record,names,names,'curved tune worker start')
    if (record['format']!='superfish_ng_planar_curved_tune_worker_start' or type(record['start_version']) is not int or record['start_version']!=1
            or record['kind']!=KIND or record['input_sha256']!=submitted or record['worker_claim_sha256']!=_digest(_regular(directory/'worker.claim'))):
        raise ValueError('curved tune worker start differs from submitted input or exclusive claim')
    _provenance(record['implementation_sha256']);return record


def _tree(directory):
    directory=_regular(directory,True);files={}
    for path in directory.rglob('*'):
        if path.is_symlink() or (not path.is_file() and not path.is_dir()):raise ValueError('curved tune owned entries must be regular, not linked')
        if path.is_file():files[path.relative_to(directory).as_posix()]=_digest(path)
    return files


def _snapshot(directory):
    directory=_regular(directory,True);data,_=_sealed(directory)
    expected={INPUT,RESULT,SEAL,START,'execution','job.json','manifest.json','worker.claim'}
    if data['checkpoint'] is not None:expected.add('ancestry')
    entries={p.name for p in directory.iterdir()}
    if entries not in (expected,expected|{'log.txt'}):raise ValueError('complete curved tune job has missing or undeclared entries')
    if 'log.txt' in entries:_regular(directory/'log.txt')
    result={name:_digest(_regular(directory/name)) for name in expected if name not in ('execution','ancestry')}
    for name in ('execution','ancestry'):
        if name in expected:result.update({f'{name}/{key}':value for key,value in _tree(directory/name).items()})
    return result


def _prefix(result,count):
    prefix=deepcopy(result)
    for key in ('trial_runs','trial_sources_sha256','trials'):prefix[key]=prefix[key][:count]
    prefix['decision']=_decision(prefix['request'],prefix['trials']);prefix['status']=prefix['decision']['status']
    prefix['can_resume']=prefix['status']=='PAUSED';return _portable(prefix)


def _ancestry(result,data):
    previous=data['checkpoint'];offset=0 if previous is None else len(previous['trial_runs'])
    if previous is not None and _canonical(_prefix(result,offset))!=_canonical(previous):raise ValueError('curved tune execution prefix differs from submitted ancestry')
    return offset


def _new_creators(directory,result,offset,implementation):
    for i in range(offset,len(result['trials'])):
        trial=directory/'execution'/f'trial-{i+1:03d}';manifest=_load(trial/'manifest.json')
        if manifest.get('implementation_sha256')!=implementation or 'imported_from' in manifest:
            raise ValueError('curved tune new trial creator differs from its actual worker')
        if (trial/'worker.claim').read_bytes()!=(directory/'worker.claim').read_bytes():raise ValueError('curved tune new trial claim differs from its worker process')


def is_planar_curved_tune(directory,state,manifest):
    return KIND in (state.get('kind'),manifest.get('kind')) or (directory/INPUT).exists() or (directory/INPUT).is_symlink() or (directory/RESULT).exists()


def verify_planar_curved_tune_job(directory,state,manifest):
    directory=_regular(directory,True);before=_snapshot(directory);implementation=_implementation_hashes()
    if state.get('status')!='complete' or state.get('kind')!=KIND or manifest.get('kind')!=KIND:raise ValueError('curved tune state and manifest require complete kind=planar_curved_tune')
    names=['manifest_version','kind','files','implementation_sha256','source_changed_during_run'];keys(manifest,names,names,'curved tune job manifest')
    if type(manifest['manifest_version']) is not int or manifest['manifest_version']!=1 or manifest['source_changed_during_run'] is not False:
        raise ValueError('curved tune completion requires stable manifest_version 1')
    creation=manifest['implementation_sha256'];_provenance(creation)
    if manifest['files']!={k:v for k,v in before.items() if k not in ('job.json','manifest.json')}:raise ValueError('curved tune manifest must bind all request, prefix, trial and result bytes')
    data,submitted=_sealed(directory);record=_start_record(directory,submitted)
    if record['implementation_sha256']!=creation:raise ValueError('curved tune completion creator differs from worker start')
    result=read_owned_planar_curved_tune(directory/RESULT,base_directory=directory/'execution')
    if _canonical(result['request'])!=_canonical(data['request']):raise ValueError('curved tune result request differs from submission')
    offset=_ancestry(result,data);count=len(result['trials']);limit=data['max_new_trials'];new=count-offset
    if new<1 or (limit is not None and new>limit) or (result['can_resume'] and (limit is None or new!=limit)):
        raise ValueError('curved tune completed trial budget differs from submission')
    expected={INPUT,RESULT,SEAL,START,'worker.claim',*submitted}
    expected.add('execution/request.json')
    for i,files in enumerate(result['trial_sources_sha256']):expected.update(f'execution/trial-{i+1:03d}/{name}' for name in files)
    for i in range(offset,count+1):
        name=f'execution/checkpoint-{i:03d}.json';expected.add(name)
        if _canonical(_load(directory/name))!=_canonical(_prefix(result,i)):raise ValueError('curved tune saved checkpoint differs from its fully replayed prefix')
    if set(manifest['files'])!=expected:raise ValueError('curved tune completion has missing or undeclared checkpoint/trial files')
    _new_creators(directory,result,offset,creation)
    if (state.get('input_sha256')!=submitted or state.get('physics')!='cartesian_cutoff_rf' or state.get('numerical_validation')!='not_checked'
            or state.get('tuning_status')!=result['status'] or type(state.get('can_resume')) is not bool or state['can_resume']!=result['can_resume']
            or type(state.get('computed_trials')) is not int or state['computed_trials']!=count):raise ValueError('curved tune job summary differs from complete original replay')
    if before!=_snapshot(directory) or _load(directory/'job.json')!=state or _load(directory/'manifest.json')!=manifest:raise ValueError('curved tune job changed during complete replay')
    if implementation!=_implementation_hashes():raise RuntimeError('implementation changed during curved tune job replay')
    return result


def read_planar_curved_tune_job(directory):
    directory=_regular(directory,True);return verify_planar_curved_tune_job(directory,_load(directory/'job.json'),_load(directory/'manifest.json'))


def read_planar_curved_tune_job_checkpoint(directory,index):
    integer(index,'checkpoint index',0);directory=_regular(directory,True);state=_load(directory/'job.json')
    if state.get('kind')!=KIND or state.get('status') not in ('complete','cancelled','interrupted','failed'):
        raise ValueError('select a stopped planar_curved_tune job before opening checkpoints')
    data,submitted=_sealed(directory);record=_start_record(directory,submitted)
    path=directory/'execution'/f'checkpoint-{index:03d}.json';before={name:_digest(_regular(directory/name)) for name in (INPUT,SEAL,START,'job.json','worker.claim')}
    result=read_owned_planar_curved_tune(path)
    if len(result['trials'])!=index or _canonical(result['request'])!=_canonical(data['request']):raise ValueError('curved tune checkpoint differs from its selected job or index')
    offset=_ancestry(result,data)
    if index<offset:raise ValueError('curved tune checkpoint precedes its submitted prefix')
    _new_creators(directory,result,offset,record['implementation_sha256'])
    if before!={name:_digest(_regular(directory/name)) for name in before} or submitted!=_sealed(directory)[1]:raise ValueError('curved selected checkpoint or submitted input changed during replay')
    return result


def _prepare(request,directory,*,max_new_trials=None,checkpoint=None):
    request=deepcopy(request);validate_planar_curved_tune(request)
    if max_new_trials is not None:integer(max_new_trials,'max_new_trials')
    source_path=source_hash=None;state=sources=None
    if checkpoint is not None:
        if isinstance(checkpoint,(str,Path)):
            source_path=_regular(checkpoint);source_hash=_digest(source_path);old_request,state,sources=_read_owned(source_path)
        else:state,sources=_verified(checkpoint);old_request=checkpoint['request']
        if _canonical(old_request)!=_canonical(request):raise ValueError('curved tune resume request differs from checkpoint')
        from .planar_curved_tuning import _result
        if _result(request,state)['status']!='PAUSED':raise ValueError('only a verified PAUSED owned curved tune can resume')
    directory=Path(directory).absolute()
    if directory!=directory.resolve():raise ValueError('curved tune job output must have no symbolic-link components')
    directory.mkdir(parents=True,exist_ok=False)
    try:
        previous=None
        if state is not None:
            _,copied=_copy_verified(request,state,sources,directory/'ancestry')
            from .planar_curved_tuning_saved import _checkpoint
            previous=_portable(_checkpoint(request,copied,sources))
        data=dict(format='superfish_ng_planar_curved_tune_job_input',input_version=1,request=request,max_new_trials=max_new_trials,checkpoint=previous)
        _write_json(directory/INPUT,data);_,submitted=_submitted(directory)
        _write(directory/SEAL,dict(format='superfish_ng_planar_curved_tune_submission',submission_version=1,files=submitted))
        _state(directory,'queued',kind=KIND,input_sha256=submitted)
        if state is not None:
            from .planar_curved_tuning_saved import _stable
            _stable(state.runs,sources)
        if source_path is not None and source_hash!=_digest(source_path):raise ValueError('curved source checkpoint changed during submission')
        if submitted!=_sealed(directory)[1]:raise ValueError('curved submitted input changed during queue publication')
    except Exception as exc:
        _state(directory,'failed',kind=KIND,error=str(exc));raise


def execute_prepared_planar_curved_tune(directory):
    directory=_regular(directory,True);state=_load(directory/'job.json')
    if state.get('status')!='queued' or state.get('kind')!=KIND:raise ValueError('curved tune worker requires a fresh queued planar_curved_tune job')
    with (directory/'worker.claim').open('x') as stream:stream.write(str(os.getpid())+'\n')
    started=time.monotonic()
    try:
        implementation=_implementation_hashes();data,submitted=_sealed(directory)
        if state.get('input_sha256')!=submitted:raise ValueError('queued curved tune input changed')
        _write(directory/START,dict(format='superfish_ng_planar_curved_tune_worker_start',start_version=1,kind=KIND,
            input_sha256=submitted,implementation_sha256=implementation,worker_claim_sha256=_digest(directory/'worker.claim')))
        _state(directory,'running',kind=KIND,input_sha256=submitted,stage='original Cartesian P2 FEM tuning, ID recovery and final fixed-boundary refinement')
        previous=data['checkpoint'];path=None if previous is None else directory/'ancestry'/f"checkpoint-{len(previous['trial_runs']):03d}.json"
        result=execute_owned_planar_curved_tune(data['request'],directory/'execution',max_new_trials=data['max_new_trials'],checkpoint=path)
        if submitted!=_sealed(directory)[1] or implementation!=_implementation_hashes():raise ValueError('curved tune input or implementation changed during execution')
        _write_json(directory/RESULT,_portable(result));files={**submitted,SEAL:_digest(directory/SEAL),START:_digest(directory/START),'worker.claim':_digest(directory/'worker.claim'),RESULT:_digest(directory/RESULT)}
        files.update({f'execution/{name}':sha for name,sha in _tree(directory/'execution').items()})
        _write_json(directory/'manifest.json',dict(manifest_version=1,kind=KIND,files=files,implementation_sha256=implementation,source_changed_during_run=False))
        _state(directory,'complete',kind=KIND,input_sha256=submitted,physics='cartesian_cutoff_rf',numerical_validation='not_checked',
            tuning_status=result['status'],can_resume=result['can_resume'],computed_trials=len(result['trials']),elapsed_seconds=time.monotonic()-started)
        verified=read_planar_curved_tune_job(directory)
        if submitted!=_sealed(directory)[1] or implementation!=_implementation_hashes():raise ValueError('curved tune input or implementation changed during completion')
        return verified
    except Exception as exc:
        _state(directory,'failed',kind=KIND,error=str(exc),elapsed_seconds=time.monotonic()-started);raise


def execute_planar_curved_tune_job(request,directory,*,max_new_trials=None,checkpoint=None):
    _prepare(request,directory,max_new_trials=max_new_trials,checkpoint=checkpoint);return execute_prepared_planar_curved_tune(directory)


def start_planar_curved_tune(manager,request,*,max_new_trials=None,checkpoint=None):
    with manager.lock:
        if manager.closed:raise ValueError('job manager is closed')
        identifier=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:10];directory=manager.directory(identifier)
        _prepare(request,directory,max_new_trials=max_new_trials,checkpoint=checkpoint)
        try:
            with (directory/'log.txt').open('x') as log:
                manager.processes[identifier]=subprocess.Popen([sys.executable,'-m','superfish_ng.planar_curved_tuning_jobs',str(directory)],
                    stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'OPENBLAS_NUM_THREADS':'1'})
        except Exception as exc:
            _state(directory,'failed',kind=KIND,error=str(exc));raise
        return identifier


if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('usage: python -m superfish_ng.planar_curved_tuning_jobs PREPARED_DIRECTORY')
    execute_prepared_planar_curved_tune(sys.argv[1])
