# SPDX-License-Identifier: Apache-2.0
"""Local adaptive FEM workers with verified completion and resume ancestry."""
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
from .adaptive_refinement import _request,_assemble,execute_adaptive_refinement,replay_adaptive_refinement,read_adaptive_refinement
from .saved_mode_tracking import _canonical


PREFIX='adaptive-refinement'
KIND='adaptive_refinement'


def _job_input(data):
    fields=('request','max_new_levels','checkpoint');keys(data,fields,fields,'adaptive refinement job input')
    _request(data['request'])
    if data['max_new_levels'] is not None:integer(data['max_new_levels'],'max_new_levels')
    if data['checkpoint'] is None:
        _assemble(data['request'],[])  # Check initial mesh quality/budget before reserving a job.
    else:
        checked=replay_adaptive_refinement(data['checkpoint'])
        if not checked['can_resume']:raise ValueError('only a verified PAUSED adaptive refinement can resume')
        if _canonical(checked['request'])!=_canonical(data['request']):raise ValueError('resume request differs from checkpoint')
    return data


def start_adaptive_refinement(manager,request,*,max_new_levels=None,checkpoint=None):
    with manager.lock:
        if manager.closed:raise ValueError('job manager is closed')
        data=_job_input(deepcopy(dict(request=request,max_new_levels=max_new_levels,checkpoint=checkpoint)))
        identifier=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:10]
        directory=manager.directory(identifier);directory.mkdir()
        _write_json(directory/f'{PREFIX}-request.json',data);_state(directory,'queued',kind=KIND)
        try:
            with (directory/'log.txt').open('x') as log:
                process=subprocess.Popen([sys.executable,'-m','superfish_ng.adaptive_refinement_jobs',str(directory)],
                    stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'OPENBLAS_NUM_THREADS':'1'})
            manager.processes[identifier]=process
        except Exception as exc:
            _state(directory,'failed',kind=KIND,error=str(exc));raise
        return identifier


def verify_adaptive_refinement_job(directory,state,manifest):
    directory=Path(directory).resolve()
    if type(manifest.get('manifest_version')) is not int or manifest['manifest_version']!=1 or manifest.get('source_changed_during_run') is not False:
        raise ValueError('invalid adaptive refinement completion manifest version or source-change declaration')
    data=_job_input(parse_json((directory/f'{PREFIX}-request.json').read_text(encoding='utf-8')))
    result=read_adaptive_refinement(directory/f'{PREFIX}-results.json')
    if (_canonical(data['request'])!=_canonical(result['request'])
            or state.get('refinement_status')!=result['status']
            or state.get('can_resume') is not result['can_resume']
            or type(state.get('computed_levels')) is not int
            or state['computed_levels']!=len(result['levels'])
            or state.get('surface_status')!=result['surface_status']
            or state.get('physical_error_bound') is not None
            or state.get('numerical_validation')!='not_checked'):
        raise ValueError('adaptive refinement job summary differs from verified checkpoint')
    previous=data['checkpoint'];offset=0 if previous is None else len(previous['level_runs'])
    if previous is not None and (_canonical(result['level_runs'][:offset])!=_canonical(previous['level_runs'])
            or _canonical(result['sources'][:offset])!=_canonical(previous['sources'])):
        raise ValueError('adaptive refinement job resume ancestry differs from submitted checkpoint')
    count=len(result['level_runs'])-offset;limit=data['max_new_levels']
    if count<1 or (limit is not None and count>limit) or (result['can_resume'] and (limit is None or count!=limit)):
        raise ValueError('adaptive refinement job level budget differs from verified result')
    required={f'{PREFIX}-request.json',f'{PREFIX}-results.json'}
    for index in range(offset,len(result['level_runs'])):
        relative=f'execution/level-{index+1:03d}'
        if result['level_runs'][index]!=str(directory/relative):raise ValueError('adaptive refinement newly computed level is outside its execution directory')
        required.add(f'execution/checkpoint-{index+1:03d}.json')
        required.update(relative+'/'+name for name in result['sources'][index]['sha256'])
    if not required.issubset(manifest['files']):raise ValueError('adaptive refinement completion manifest omits level or checkpoint files')
    return result


def execute_prepared_adaptive_refinement(directory):
    directory=Path(directory);started=time.monotonic()
    try:
        implementation=_implementation_hashes();request_hash=_digest(directory/f'{PREFIX}-request.json')
        data=_job_input(parse_json((directory/f'{PREFIX}-request.json').read_text(encoding='utf-8')))
        _state(directory,'running',kind=KIND,stage='tracked adaptive FEM refinement and RF confirmation')
        result=execute_adaptive_refinement(data['request'],directory/'execution',max_new_levels=data['max_new_levels'],checkpoint=data['checkpoint'])
        if implementation!=_implementation_hashes() or request_hash!=_digest(directory/f'{PREFIX}-request.json'):
            raise RuntimeError('implementation or adaptive refinement request changed during run')
        _write_json(directory/f'{PREFIX}-results.json',result)
        files={name:_digest(directory/name) for name in (f'{PREFIX}-request.json',f'{PREFIX}-results.json')}
        files.update({p.relative_to(directory).as_posix():_digest(p) for p in sorted((directory/'execution').rglob('*')) if p.is_file()})
        _write_json(directory/'manifest.json',dict(manifest_version=1,kind=KIND,files=files,
            implementation_sha256=implementation,source_changed_during_run=False))
        _state(directory,'complete',kind=KIND,refinement_status=result['status'],can_resume=result['can_resume'],
            computed_levels=len(result['levels']),surface_status=result['surface_status'],physical_error_bound=None,
            numerical_validation='not_checked',elapsed_seconds=time.monotonic()-started)
        return result
    except Exception as exc:
        _state(directory,'failed',kind=KIND,error=str(exc),elapsed_seconds=time.monotonic()-started)
        raise


if __name__=='__main__':
    try:execute_prepared_adaptive_refinement(Path(sys.argv[1]))
    except Exception:
        traceback.print_exc();sys.exit(2)
