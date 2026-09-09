# SPDX-License-Identifier: Apache-2.0
"""Isolated local RF optimization jobs with verified completion and ancestry."""
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import uuid
from .config import keys,integer
from .jobs import _state,_write_json,_digest,_implementation_hashes
from .project import parse_json
from .rf_optimization import validate_optimization_request,execute_rf_optimization,replay_rf_optimization,read_rf_optimization
from .saved_mode_tracking import _canonical


def _job_input(data):
    fields=('request','max_new_trials','checkpoint');keys(data,fields,fields,'RF optimization job input')
    validate_optimization_request(data['request'])
    if data['max_new_trials'] is not None:integer(data['max_new_trials'],'max_new_trials')
    if data['checkpoint'] is not None:
        checked=replay_rf_optimization(data['checkpoint'])
        if not checked['can_resume']:raise ValueError('only a verified PAUSED RF optimization can resume')
        if _canonical(checked['request'])!=_canonical(data['request']):raise ValueError('resume request differs from checkpoint')
    return data


def start_rf_optimization(manager,request,*,max_new_trials=None,checkpoint=None):
    with manager.lock:
        if manager.closed:raise ValueError('job manager is closed')
        data=_job_input(deepcopy(dict(request=request,max_new_trials=max_new_trials,checkpoint=checkpoint)))
        identifier=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:10]
        directory=manager.directory(identifier);directory.mkdir()
        _write_json(directory/'rf-optimization-request.json',data);_state(directory,'queued',kind='rf_optimization')
        try:
            with (directory/'log.txt').open('x') as log:
                process=subprocess.Popen([sys.executable,'-m','superfish_ng.rf_optimization_jobs',str(directory)],
                    stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'OPENBLAS_NUM_THREADS':'1'})
            manager.processes[identifier]=process
        except Exception as exc:
            _state(directory,'failed',kind='rf_optimization',error=str(exc));raise
        return identifier


def verify_rf_optimization_job(directory,state,manifest):
    """Recheck saved fields, job summary, resume ancestry and the worker budget."""
    directory=Path(directory).resolve()
    data=_job_input(parse_json((directory/'rf-optimization-request.json').read_text(encoding='utf-8')))
    result=read_rf_optimization(directory/'rf-optimization-results.json')
    if (_canonical(data['request'])!=_canonical(result['request'])
            or state.get('optimization_status')!=result['status']
            or state.get('can_resume') is not result['can_resume']
            or type(state.get('computed_trials')) is not int
            or state['computed_trials']!=len(result['trials'])
            or type(state.get('computed_fem_solves')) is not int
            or state['computed_fem_solves']!=result['completed_fem_solves']
            or state.get('numerical_validation')!='not_checked'):
        raise ValueError('RF optimization job summary differs from verified checkpoint')
    previous=data['checkpoint'];offset=0 if previous is None else len(previous['trial_directories'])
    if previous is not None and (_canonical(result['trial_directories'][:offset])!=_canonical(previous['trial_directories'])
            or _canonical(result['trial_sources_sha256'][:offset])!=_canonical(previous['trial_sources_sha256'])):
        raise ValueError('RF optimization job resume ancestry differs from submitted checkpoint')
    count=len(result['trial_directories'])-offset;limit=data['max_new_trials']
    if count<1 or (limit is not None and count>limit) or (result['can_resume'] and (limit is None or count!=limit)):
        raise ValueError('RF optimization job trial budget differs from verified result')
    required={'rf-optimization-request.json','rf-optimization-results.json'}
    for index in range(offset,len(result['trial_directories'])):
        relative=f'execution/trial-{index+1:03d}'
        if result['trial_directories'][index]!=str(directory/relative):raise ValueError('RF optimization job newly computed trial is outside its execution directory')
        required.add(f'execution/checkpoint-{index+1:03d}.json')
        for level,files in enumerate(result['trial_sources_sha256'][index]):
            required.update(f'{relative}/level-{level}/'+name for name in files)
    if not required.issubset(manifest['files']):raise ValueError('RF optimization completion manifest omits trial or checkpoint files')
    return result


def execute_prepared_rf_optimization(directory):
    directory=Path(directory);started=time.monotonic()
    try:
        implementation=_implementation_hashes();request_hash=_digest(directory/'rf-optimization-request.json')
        data=_job_input(parse_json((directory/'rf-optimization-request.json').read_text(encoding='utf-8')))
        _state(directory,'running',kind='rf_optimization',stage='constrained RF coordinate search and final three-level refinement')
        result=execute_rf_optimization(data['request'],directory/'execution',max_new_trials=data['max_new_trials'],checkpoint=data['checkpoint'])
        if implementation!=_implementation_hashes() or request_hash!=_digest(directory/'rf-optimization-request.json'):
            raise RuntimeError('implementation or RF optimization request changed during run')
        _write_json(directory/'rf-optimization-results.json',result)
        files={name:_digest(directory/name) for name in ('rf-optimization-request.json','rf-optimization-results.json')}
        files.update({p.relative_to(directory).as_posix():_digest(p) for p in sorted((directory/'execution').rglob('*')) if p.is_file()})
        _write_json(directory/'manifest.json',dict(manifest_version=1,kind='rf_optimization',files=files,
            implementation_sha256=implementation,source_changed_during_run=False))
        _state(directory,'complete',kind='rf_optimization',optimization_status=result['status'],can_resume=result['can_resume'],
            computed_trials=len(result['trials']),computed_fem_solves=result['completed_fem_solves'],numerical_validation='not_checked',elapsed_seconds=time.monotonic()-started)
        return result
    except Exception as exc:
        _state(directory,'failed',kind='rf_optimization',error=str(exc),elapsed_seconds=time.monotonic()-started)
        raise


if __name__=='__main__':
    try:execute_prepared_rf_optimization(Path(sys.argv[1]))
    except Exception:
        traceback.print_exc();sys.exit(2)
