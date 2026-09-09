# SPDX-License-Identifier: Apache-2.0
"""Same-domain refinement workers with full native and diagnostic replay."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
from .config import keys
from .project import parse_json
from .planar_convergence import PlanarConvergence
from .planar_jobs import execute_planar_project, _job_hashes
from .planar_project import PlanarProject
from .planar_saved import read_planar_run
from .planar_convergence_compare import compare_planar_convergence
from .jobs import _digest, _implementation_hashes, _state, _write_json

KIND = 'planar_convergence'


def _load(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('planar convergence metadata must be regular files, not links')
    return parse_json(path.read_text(encoding='utf-8'))


def is_planar_convergence(directory, state, manifest):
    if KIND in (state.get('kind'), manifest.get('kind')): return True
    for name in ('convergence.json', 'convergence-results.json'):
        path=directory/name
        if path.is_file():
            data=_load(path)
            if isinstance(data,dict) and data.get('format') in ('superfish_ng_planar_convergence', 'superfish_ng_planar_convergence_result'):
                return True
    return False


def _point_name(index):
    return f'point-{index:04d}'


def _snapshot(directory, convergence):
    if directory.is_symlink(): raise ValueError('planar convergence directory must not be linked')
    names=('convergence.json', 'convergence-results.json', 'job.json', 'manifest.json')
    result={}
    for name in names:
        _load(directory/name);result[name]=_digest(directory/name)
    expected={_point_name(i) for i in range(convergence.levels)}
    if {p.name for p in directory.iterdir() if p.name.startswith('point-')}!=expected:
        raise ValueError('planar convergence point directories differ from requested points')
    for name in sorted(expected):
        point=directory/name
        if point.is_symlink() or not point.is_dir():raise ValueError('planar convergence points must be regular directories')
        result.update({f'{name}/{key}':value for key,value in _job_hashes(point).items()})
    return result


def verify_planar_convergence(directory, state, manifest):
    from .jobs import read_job
    directory=Path(directory);convergence=PlanarConvergence.from_dict(_load(directory/'convergence.json'))
    before=_snapshot(directory,convergence)
    if state.get('status')!='complete' or state.get('kind')!=KIND or manifest.get('kind')!=KIND:
        raise ValueError('planar convergence state and manifest require complete kind=planar_convergence')
    fields=['manifest_version','kind','files','implementation_sha256','source_changed_during_run']
    keys(manifest,fields,fields,'planar convergence completion manifest')
    if type(manifest['manifest_version']) is not int or manifest['manifest_version']!=1:
        raise ValueError('planar convergence manifest_version must be 1')
    expected={k:v for k,v in before.items() if k not in ('job.json','manifest.json')}
    if manifest['files']!=expected:raise ValueError('planar convergence manifest must bind every requested point and native file exactly')
    implementation=manifest['implementation_sha256']
    if (not isinstance(implementation,dict) or not implementation
        or any(not isinstance(k,str) or not isinstance(v,str) or len(v)!=64 or any(c not in '0123456789abcdef' for c in v) for k,v in implementation.items())
        or manifest['source_changed_during_run'] is not False):
        raise ValueError('planar convergence requires stable execution provenance')
    rows=[]
    for index,project in enumerate(convergence.projects()):
        point=directory/_point_name(index);point_state=read_job(point)
        if point_state.get('status')!='complete' or point_state.get('kind')!='planar_solve':
            raise ValueError('planar convergence point is not a complete planar solve')
        point_manifest=_load(point/'manifest.json')
        if point_state.get('origin') is not None or point_manifest.get('implementation_sha256')!=implementation:
            raise ValueError('planar convergence point must be executed with the recorded convergence implementation')
        if PlanarProject.load(point/'project.json')!=project:
            raise ValueError('planar convergence point Project differs from the declared refinement level')
        solution=read_planar_run(point/'solution')
        rows.append(solution)
    result=_load(directory/'convergence-results.json')
    if json.dumps(result,sort_keys=True,allow_nan=False)!=json.dumps(compare_planar_convergence(convergence,rows),sort_keys=True,allow_nan=False):
        raise ValueError('planar convergence summary differs from fully verified point spectra/RF; diagnostics must be recomputed from all original fields')
    if (state.get('physics')!='cartesian_cutoff_rf' or state.get('mode_tracking')!='not_performed'
        or state.get('numerical_validation')!=result.get('status') or type(state.get('computed_points')) is not int
        or state['computed_points']!=convergence.levels):
        raise ValueError('planar convergence state differs from verified same-domain refinement')
    if _load(directory/'job.json')!=state or _load(directory/'manifest.json')!=manifest or _snapshot(directory,convergence)!=before:
        raise ValueError('planar convergence changed during verification')
    return result


def read_planar_convergence(directory):
    directory=Path(directory)
    return verify_planar_convergence(directory,_load(directory/'job.json'),_load(directory/'manifest.json'))


def _prepare(convergence, directory):
    if not isinstance(convergence,PlanarConvergence):raise ValueError('expected a dedicated PlanarConvergence')
    convergence=PlanarConvergence.from_dict(convergence.to_dict())
    convergence.projects()
    raw=json.dumps(convergence.to_dict(),indent=2,ensure_ascii=False,allow_nan=False)+'\n'
    directory.mkdir(parents=True,exist_ok=False);convergence.save(directory/'convergence.json')
    _state(directory,'queued',kind=KIND,convergence_sha256=hashlib.sha256(raw.encode('utf-8')).hexdigest())


def execute_prepared_planar_convergence(directory):
    directory=Path(directory);started=time.monotonic();state=_load(directory/'job.json')
    if directory.is_symlink() or state.get('status')!='queued' or state.get('kind')!=KIND:
        raise ValueError('prepared planar convergence worker requires a queued planar_convergence; rerun in a new directory')
    with (directory/'worker.claim').open('x') as stream:stream.write(str(os.getpid())+'\n')
    try:
        implementation=_implementation_hashes();raw=(directory/'convergence.json').read_bytes();request_hash=hashlib.sha256(raw).hexdigest()
        if (directory/'convergence.json').is_symlink() or request_hash!=state.get('convergence_sha256'):
            raise ValueError('queued planar convergence input changed after submission')
        convergence=PlanarConvergence.from_dict(parse_json(raw.decode('utf-8')));projects=convergence.projects();rows=[]
        for index,project in enumerate(projects):
            _state(directory,'running',kind=KIND,stage=f'point {index+1}/{len(projects)}',computed_points=index)
            point=directory/_point_name(index);execute_planar_project(project,point)
            rows.append(read_planar_run(point/'solution'))
        if request_hash!=_digest(directory/'convergence.json') or implementation!=_implementation_hashes():
            raise ValueError('planar convergence input or implementation changed during execution')
        result=compare_planar_convergence(convergence,rows)
        _write_json(directory/'convergence-results.json',result)
        files={name:_digest(directory/name) for name in ('convergence.json','convergence-results.json')}
        for index in range(len(projects)):
            name=_point_name(index);files.update({f'{name}/{k}':v for k,v in _job_hashes(directory/name).items()})
        _write_json(directory/'manifest.json',dict(manifest_version=1,kind=KIND,files=files,implementation_sha256=implementation,source_changed_during_run=False))
        _state(directory,'complete',kind=KIND,stage='saved refinement diagnostics',computed_points=len(projects),
            physics='cartesian_cutoff_rf',mode_tracking='not_performed',numerical_validation=result['status'],elapsed_seconds=time.monotonic()-started)
        result=read_planar_convergence(directory)
        if request_hash!=_digest(directory/'convergence.json') or implementation!=_implementation_hashes():
            raise ValueError('planar convergence input or implementation changed during completion')
        return result
    except Exception as exc:
        _state(directory,'failed',kind=KIND,error=str(exc),elapsed_seconds=time.monotonic()-started)
        raise


def execute_planar_convergence(convergence, directory):
    directory=Path(directory);_prepare(convergence,directory)
    return execute_prepared_planar_convergence(directory)


def start_planar_convergence(manager, convergence):
    with manager.lock:
        if manager.closed:raise ValueError('job manager is closed')
        identifier=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:10];directory=manager.directory(identifier)
        _prepare(convergence,directory)
        try:
            with (directory/'log.txt').open('x') as log:
                manager.processes[identifier]=subprocess.Popen([sys.executable,'-m','superfish_ng.planar_convergence_jobs',str(directory)],
                    stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'OPENBLAS_NUM_THREADS':'1'})
        except Exception as exc:
            _state(directory,'failed',kind=KIND,error=str(exc));raise
        return identifier


if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('usage: python -m superfish_ng.planar_convergence_jobs PREPARED_DIRECTORY')
    execute_prepared_planar_convergence(Path(sys.argv[1]))
