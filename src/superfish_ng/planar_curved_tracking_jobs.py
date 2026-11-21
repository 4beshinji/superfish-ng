# SPDX-License-Identifier: Apache-2.0
"""Local workers owning exact curved operands and fully replayed correspondence."""
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
from .planar_curved_tracking import PlanarCurvedTrackingRequest
from .planar_curved_tracking_saved import (_regular,_load,_source,_source_snapshot,
    execute_owned_planar_curved_tracking,read_owned_planar_curved_tracking,curved_tracking_snapshot)

KIND='planar_curved_tracking'
INPUT='planar-curved-tracking-input.json'


def _submitted(directory):
    directory=_regular(directory,True);data=_load(directory/INPUT)
    names=['format','input_version','request','sources'];keys(data,names,names,'curved tracking job input')
    if data['format']!='superfish_ng_planar_curved_tracking_job_input' or type(data['input_version']) is not int or data['input_version']!=1:
        raise ValueError('expected curved tracking job input_version 1')
    PlanarCurvedTrackingRequest.from_dict(data['request'])
    keys(data['sources'],['previous','current'],['previous','current'],'curved tracking job sources')
    operands=_regular(directory/'operands',True)
    if {p.name for p in operands.iterdir()}!={'previous','current'}:raise ValueError('curved job requires exactly both submitted operands')
    hashes={INPUT:_digest(directory/INPUT)}
    for side in ('previous','current'):
        source=data['sources'][side];keys(source,['path','kind','files'],['path','kind','files'],'curved tracking job source')
        if type(source['path']) is not str or not source['path']:raise ValueError('curved job source needs an informational origin')
        actual=_source_snapshot(operands/side,source['kind'],strict=True)
        if actual!=source['files']:raise ValueError('curved job submitted operand differs from original bytes')
        hashes.update({f'operands/{side}/{name}':value for name,value in actual.items()})
    return data,hashes


def _snapshot(directory):
    directory=_regular(directory,True)
    expected={INPUT,'operands','execution','job.json','manifest.json','worker.claim'}
    entries={p.name for p in directory.iterdir()}
    if entries not in (expected,expected|{'log.txt'}):raise ValueError('complete curved job has missing or undeclared entries')
    if 'log.txt' in entries:_regular(directory/'log.txt')
    _,result=_submitted(directory)
    for name in ('job.json','manifest.json','worker.claim'):result[name]=_digest(_regular(directory/name))
    result.update({f'execution/{name}':sha for name,sha in curved_tracking_snapshot(directory/'execution').items()})
    return result


def is_planar_curved_tracking(directory,state,manifest):
    return KIND in (state.get('kind'),manifest.get('kind')) or (directory/INPUT).exists() or (directory/INPUT).is_symlink()


def verify_planar_curved_tracking(directory,state,manifest):
    directory=_regular(directory,True);before=_snapshot(directory);implementation=_implementation_hashes()
    if state.get('status')!='complete' or state.get('kind')!=KIND or manifest.get('kind')!=KIND:
        raise ValueError('curved tracking state and manifest require complete kind=planar_curved_tracking')
    names=['manifest_version','kind','files','implementation_sha256','source_changed_during_run']
    keys(manifest,names,names,'curved tracking job manifest')
    creation=manifest['implementation_sha256']
    if (type(manifest['manifest_version']) is not int or manifest['manifest_version']!=1
            or manifest['source_changed_during_run'] is not False or type(creation) is not dict or not creation
            or any(type(k) is not str or type(v) is not str or len(v)!=64 or any(c not in '0123456789abcdef' for c in v) for k,v in creation.items())):
        raise ValueError('curved job requires stable implementation provenance version 1')
    if manifest['files']!={k:v for k,v in before.items() if k not in ('job.json','manifest.json')}:
        raise ValueError('curved job manifest must bind all submitted and executed bytes')
    data,submitted=_submitted(directory);result=read_owned_planar_curved_tracking(directory/'execution')
    if _canonical(result['request'])!=_canonical(data['request']):raise ValueError('curved job execution request differs from submission')
    execution_sources=_load(directory/'execution/sources.json')
    for side in ('previous','current'):
        original=data['sources'][side];executed=execution_sources[side]
        if original['kind']!=executed['kind'] or original['files']!=executed['files']:
            raise ValueError('curved execution operands differ from submitted original bytes')
    if _load(directory/'execution/manifest.json')['implementation_sha256']!=creation:
        raise ValueError('curved execution creator differs from the tracking worker')
    if (state.get('input_sha256')!=submitted or state.get('physics')!='cartesian_cutoff_rf'
            or state.get('numerical_validation')!='not_checked' or state.get('tracking_status')!=result['status']
            or type(state.get('individual_ids_complete')) is not bool or state['individual_ids_complete']!=result['individual_ids_complete']):
        raise ValueError('curved job summary differs from fully replayed correspondence')
    if before!=_snapshot(directory) or _load(directory/'job.json')!=state or _load(directory/'manifest.json')!=manifest:
        raise ValueError('curved tracking job changed during complete replay')
    if implementation!=_implementation_hashes():raise RuntimeError('implementation changed during curved job replay')
    return result


def read_planar_curved_tracking(directory):
    directory=_regular(directory,True)
    return verify_planar_curved_tracking(directory,_load(directory/'job.json'),_load(directory/'manifest.json'))


def _prepare(previous,current,request,directory):
    if type(request) is not PlanarCurvedTrackingRequest:raise ValueError('expected PlanarCurvedTrackingRequest')
    request=PlanarCurvedTrackingRequest.from_dict(request.to_dict());operands=[_source(p) for p in (previous,current)]
    if any(count>=solution.case.modes for count,(solution,_) in zip((request.previous_mode_count,request.current_mode_count),operands)):
        raise ValueError('each tracked prefix needs an original upper guard mode')
    directory=Path(directory).absolute()
    if directory!=directory.resolve():raise ValueError('curved job output must have no symbolic-link components')
    directory.mkdir(parents=True,exist_ok=False)
    data=dict(format='superfish_ng_planar_curved_tracking_job_input',input_version=1,request=request.to_dict(),
        sources=dict(previous=operands[0][1],current=operands[1][1]))
    try:
        _write_json(directory/INPUT,data);(directory/'operands').mkdir()
        for side,(_,source) in zip(('previous','current'),operands):
            target=directory/'operands'/side;target.mkdir()
            if _source_snapshot(source['path'],source['kind'])!=source['files']:raise ValueError('curved job source changed before copying')
            for name in source['files']:
                destination=target/name;destination.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(Path(source['path'])/name,destination)
            if _source_snapshot(target,source['kind'],strict=True)!=source['files']:raise ValueError('curved job source changed during copying')
        for _,source in operands:
            if _source_snapshot(source['path'],source['kind'])!=source['files']:raise ValueError('curved job source changed during complete copying')
        _,submitted=_submitted(directory)
        _state(directory,'queued',kind=KIND,input_sha256=submitted)
        for _,source in operands:
            if _source_snapshot(source['path'],source['kind'])!=source['files']:raise ValueError('curved job source changed during queue publication')
        if submitted!=_submitted(directory)[1]:raise ValueError('curved submitted input changed during queue publication')
    except Exception as exc:
        _state(directory,'failed',kind=KIND,error=str(exc));raise


def execute_prepared_planar_curved_tracking(directory):
    directory=_regular(directory,True);state=_load(directory/'job.json')
    if state.get('status')!='queued' or state.get('kind')!=KIND:raise ValueError('curved tracking worker requires a fresh queued planar_curved_tracking job')
    with (directory/'worker.claim').open('x') as stream:stream.write(str(os.getpid())+'\n')
    started=time.monotonic()
    try:
        implementation=_implementation_hashes();data,submitted=_submitted(directory)
        if state.get('input_sha256')!=submitted:raise ValueError('queued curved tracking input changed')
        _state(directory,'running',kind=KIND,input_sha256=submitted,stage='original Cartesian E/H comparison and finite spectral guards')
        result=execute_owned_planar_curved_tracking(directory/'operands/previous',directory/'operands/current',
            PlanarCurvedTrackingRequest.from_dict(data['request']),directory/'execution')
        if submitted!=_submitted(directory)[1] or implementation!=_implementation_hashes():raise ValueError('curved job input or implementation changed during execution')
        files={**submitted,'worker.claim':_digest(directory/'worker.claim')}
        files.update({f'execution/{name}':sha for name,sha in curved_tracking_snapshot(directory/'execution').items()})
        _write_json(directory/'manifest.json',dict(manifest_version=1,kind=KIND,files=files,
            implementation_sha256=implementation,source_changed_during_run=False))
        _state(directory,'complete',kind=KIND,input_sha256=submitted,physics='cartesian_cutoff_rf',
            numerical_validation='not_checked',tracking_status=result['status'],individual_ids_complete=result['individual_ids_complete'],
            elapsed_seconds=time.monotonic()-started)
        verified=read_planar_curved_tracking(directory)
        if submitted!=_submitted(directory)[1] or implementation!=_implementation_hashes():raise ValueError('curved job input or implementation changed during completion')
        return verified
    except Exception as exc:
        _state(directory,'failed',kind=KIND,error=str(exc),elapsed_seconds=time.monotonic()-started);raise


def execute_planar_curved_tracking(previous,current,request,directory):
    _prepare(previous,current,request,directory)
    return execute_prepared_planar_curved_tracking(directory)


def start_planar_curved_tracking(manager,previous,current,request):
    with manager.lock:
        if manager.closed:raise ValueError('job manager is closed')
        identifier=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:10]
        directory=manager.directory(identifier);_prepare(previous,current,request,directory)
        try:
            with (directory/'log.txt').open('x') as log:
                manager.processes[identifier]=subprocess.Popen([sys.executable,'-m','superfish_ng.planar_curved_tracking_jobs',str(directory)],
                    stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'OPENBLAS_NUM_THREADS':'1'})
        except Exception as exc:
            _state(directory,'failed',kind=KIND,error=str(exc));raise
        return identifier


if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('usage: python -m superfish_ng.planar_curved_tracking_jobs PREPARED_DIRECTORY')
    execute_prepared_planar_curved_tracking(sys.argv[1])
