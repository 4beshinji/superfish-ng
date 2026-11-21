# SPDX-License-Identifier: Apache-2.0
"""Owned immutable hphi tracking histories with complete ancestry replay."""
import hashlib
import json
from pathlib import Path
import shutil
import os
import subprocess
import sys
import time
import uuid
from .config import keys
from .jobs import _state, _write_json, _implementation_hashes, _digest
from .material_hphi_tracking_jobs import _load, _snapshot as pair_snapshot
from .material_hphi_tracking_history import MaterialHphiTrackingHistoryRequest, verify_material_hphi_history_steps

KIND='material_hphi_tracking_history'


def _paths(directory, request):
    expected=[f'step-{index:04d}' for index in range(request.step_count)]
    if {path.name for path in directory.iterdir() if path.name.startswith('step-')}!=set(expected):
        raise ValueError('hphi history requires exactly its declared numbered step directories')
    return [directory/name for name in expected]


def _inputs(directory):
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('hphi history requires a regular directory, not a link')
    request=MaterialHphiTrackingHistoryRequest.from_dict(_load(directory/'history.json'))
    sources=_load(directory/'sources.json')
    keys(sources,['format','sources_version','steps'],['format','sources_version','steps'],'hphi history sources')
    if (sources['format']!='superfish_ng_material_hphi_tracking_history_sources'
            or type(sources['sources_version']) is not int or sources['sources_version']!=1
            or type(sources['steps']) is not list or len(sources['steps'])!=request.step_count):
        raise ValueError('hphi history sources differ from the requested steps')
    result={name:_digest(directory/name) for name in ('history.json','sources.json')}
    for path,source in zip(_paths(directory,request),sources['steps']):
        keys(source,['path','files'],['path','files'],'hphi history step source')
        if type(source['path']) is not str or not source['path'].strip():
            raise ValueError('hphi history source path must be a nonempty string')
        snapshot=pair_snapshot(path)
        if source['files']!=snapshot:raise ValueError('owned hphi history step differs from its source snapshot')
        result.update({f'{path.name}/{name}':digest for name,digest in snapshot.items()})
    return result


def history_snapshot(directory):
    directory=Path(directory);result=_inputs(directory)
    for name in ('history-results.json','manifest.json','job.json'):
        _load(directory/name);result[name]=_digest(directory/name)
    return result


def verify_material_hphi_history(directory, state, manifest):
    directory=Path(directory);before=history_snapshot(directory)
    if state.get('status')!='complete' or state.get('kind')!=KIND or manifest.get('kind')!=KIND:
        raise ValueError('hphi history requires complete state and kind=material_hphi_tracking_history')
    names=['manifest_version','kind','files','implementation_sha256','source_changed_during_run']
    keys(manifest,names,names,'hphi history manifest');implementation=manifest['implementation_sha256']
    if (type(manifest['manifest_version']) is not int or manifest['manifest_version']!=1
            or manifest['source_changed_during_run'] is not False
            or type(implementation) is not dict or not implementation
            or any(type(k) is not str or type(v) is not str or len(v)!=64
                   or any(c not in '0123456789abcdef' for c in v) for k,v in implementation.items())):
        raise ValueError('hphi history requires stable implementation provenance')
    if manifest['files']!={k:v for k,v in before.items() if k not in ('manifest.json','job.json')}:
        raise ValueError('hphi history manifest must bind the whole owned ancestry')
    request=MaterialHphiTrackingHistoryRequest.from_dict(_load(directory/'history.json'))
    expected=verify_material_hphi_history_steps(_paths(directory,request),request)
    actual=_load(directory/'history-results.json')
    if json.dumps(actual,sort_keys=True,allow_nan=False)!=json.dumps(expected,sort_keys=True,allow_nan=False):
        raise ValueError('hphi history result differs from full ancestry replay')
    if (state.get('input_sha256')!=_inputs(directory) or state.get('physics')!='axisymmetric_hphi_rf'
            or state.get('numerical_validation')!=expected['status']
            or type(state.get('can_extend')) is not bool or state['can_extend']!=expected['can_extend']
            or type(state.get('individual_ids_complete')) is not bool
            or state['individual_ids_complete']!=expected['individual_ids_complete']):
        raise ValueError('hphi history state differs from the replayed ancestry')
    if (before!=history_snapshot(directory) or state!=_load(directory/'job.json')
            or manifest!=_load(directory/'manifest.json')):
        raise ValueError('hphi history changed during full replay')
    return expected


def read_material_hphi_history(directory):
    directory=Path(directory)
    return verify_material_hphi_history(directory,_load(directory/'job.json'),_load(directory/'manifest.json'))


def _prepare(paths, request, directory):
    """Copy verified pairs into a fresh history; never mutate a prior history."""
    implementation=_implementation_hashes()
    verified=verify_material_hphi_history_steps(paths,request)
    if implementation!=_implementation_hashes():raise ValueError('hphi history implementation changed during source replay')
    request=MaterialHphiTrackingHistoryRequest.from_dict(request.to_dict());paths=[Path(p) for p in paths]
    sources=dict(format='superfish_ng_material_hphi_tracking_history_sources',sources_version=1,
                 steps=[dict(path=str(path.resolve()),files=snapshot) for path,snapshot in zip(paths,verified['step_sha256'])])
    def digest_document(value):
        return hashlib.sha256((json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()).hexdigest()
    expected={'history.json':digest_document(request.to_dict()),'sources.json':digest_document(sources)}
    for index,snapshot in enumerate(verified['step_sha256']):expected.update({f'step-{index:04d}/{k}':v for k,v in snapshot.items()})
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    try:
        request.save(directory/'history.json');_write_json(directory/'sources.json',sources)
        for index,(path,snapshot) in enumerate(zip(paths,verified['step_sha256'])):
            target=directory/f'step-{index:04d}';target.mkdir()
            for name in snapshot:
                destination=target/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path/name,destination)
        if [pair_snapshot(path) for path in paths]!=verified['step_sha256']:
            raise ValueError('source hphi history ancestry changed during copying')
        if _inputs(directory)!=expected:raise ValueError('prepared hphi history inputs changed during copying')
        if implementation!=_implementation_hashes():raise ValueError('history implementation changed during preparation')
        _state(directory,'queued',kind=KIND,input_sha256=expected)
    except Exception as error:
        _state(directory,'failed',kind=KIND,error=str(error));raise


def execute_prepared_material_hphi_history(directory):
    directory=Path(directory);state=_load(directory/'job.json')
    if directory.is_symlink() or state.get('status')!='queued' or state.get('kind')!=KIND:
        raise ValueError('hphi history worker requires a fresh queued history job')
    with (directory/'worker.claim').open('x') as stream:stream.write(str(os.getpid())+'\n')
    try:
        expected=_inputs(directory);implementation=_implementation_hashes()
        if expected!=state.get('input_sha256'):raise ValueError('queued hphi history inputs changed')
        request=MaterialHphiTrackingHistoryRequest.from_dict(_load(directory/'history.json'))
        _state(directory,'running',kind=KIND,input_sha256=expected,stage='verifying full hphi ancestry')
        result=verify_material_hphi_history_steps(_paths(directory,request),request)
        if _inputs(directory)!=expected or implementation!=_implementation_hashes():
            raise ValueError('hphi history input or implementation changed during execution')
        _write_json(directory/'history-results.json',result)
        _write_json(directory/'manifest.json',dict(manifest_version=1,kind=KIND,
            files={**expected,'history-results.json':_digest(directory/'history-results.json')},
            implementation_sha256=implementation,source_changed_during_run=False))
        _state(directory,'complete',kind=KIND,input_sha256=expected,physics='axisymmetric_hphi_rf',
               numerical_validation=result['status'],can_extend=result['can_extend'],
               individual_ids_complete=result['individual_ids_complete'])
        result=read_material_hphi_history(directory)
        if _inputs(directory)!=expected or implementation!=_implementation_hashes():
            raise ValueError('hphi history input or implementation changed during completion')
        return result
    except Exception as error:
        _state(directory,'failed',kind=KIND,error=str(error));raise


def execute_material_hphi_history(paths, request, directory):
    _prepare(paths,request,directory)
    return execute_prepared_material_hphi_history(directory)


def start_material_hphi_history(manager, paths, request):
    with manager.lock:
        if manager.closed:raise ValueError('job manager is closed')
        identifier=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:10]
        directory=manager.directory(identifier);_prepare(paths,request,directory)
        return _spawn_history(manager,identifier,directory)


def _spawn_history(manager, identifier, directory):
    try:
        with (directory/'log.txt').open('x') as log:
            manager.processes[identifier]=subprocess.Popen(
                [sys.executable,'-m','superfish_ng.material_hphi_tracking_history_saved',str(directory)],
                stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'OPENBLAS_NUM_THREADS':'1'})
    except Exception as error:
        _state(directory,'failed',kind=KIND,error=str(error));raise
    return identifier


def start_extended_material_hphi_history(manager, history, next_pair):
    """Freeze the validated ancestry before starting a new extension worker."""
    with manager.lock:
        if manager.closed:raise ValueError('job manager is closed')
        history=Path(history);before=history_snapshot(history);previous=read_material_hphi_history(history)
        if not previous['can_extend']:raise ValueError(previous['stop_reason'])
        old=MaterialHphiTrackingHistoryRequest.from_dict(previous['request'])
        request=MaterialHphiTrackingHistoryRequest(old.step_count+1,old.max_steps,old.recoveries)
        if before!=history_snapshot(history):raise ValueError('source hphi history changed before extension')
        identifier=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:10]
        directory=manager.directory(identifier)
        _prepare([*_paths(history,old),Path(next_pair)],request,directory)
        try:
            if before!=history_snapshot(history):raise ValueError('source hphi history changed while preparing extension')
        except Exception as error:
            _state(directory,'failed',kind=KIND,error=str(error));raise
        return _spawn_history(manager,identifier,directory)


def is_material_hphi_history(directory, state, manifest):
    if KIND in (state.get('kind'),manifest.get('kind')):return True
    for name in ('history.json','history-results.json'):
        path=directory/name
        if path.is_file():
            data=_load(path)
            if isinstance(data,dict) and data.get('format') in (
                    'superfish_ng_material_hphi_tracking_history_request','superfish_ng_material_hphi_tracking_history_result'):
                return True
    return False


def extend_material_hphi_history(history, next_pair, directory):
    """Create a new owned history after checking every existing ancestor."""
    history=Path(history);before=history_snapshot(history);previous=read_material_hphi_history(history)
    if not previous['can_extend']:raise ValueError(previous['stop_reason'])
    old_request=MaterialHphiTrackingHistoryRequest.from_dict(previous['request'])
    request=MaterialHphiTrackingHistoryRequest(old_request.step_count+1,old_request.max_steps,old_request.recoveries)
    if before!=history_snapshot(history):raise ValueError('source hphi history changed before extension')
    target=Path(directory)
    result=execute_material_hphi_history([*_paths(history,old_request),Path(next_pair)],request,target)
    try:
        if before!=history_snapshot(history):raise ValueError('source hphi history changed during extension')
    except Exception as error:
        _state(target,'failed',kind=KIND,error=str(error));raise
    return result


if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('usage: python -m superfish_ng.material_hphi_tracking_history_saved PREPARED_DIRECTORY')
    execute_prepared_material_hphi_history(sys.argv[1])
