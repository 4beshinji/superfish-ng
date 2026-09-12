# SPDX-License-Identifier: Apache-2.0
"""Independent hphi sweep workers with complete point/native replay."""
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
from .hphi_study import HphiStudy
from .hphi_jobs import execute_hphi_project, _job_hashes
from .hphi_project import HphiProject
from .hphi_native import read_hphi_run, hphi_result
from .jobs import _digest, _implementation_hashes, _state, _write_json

KIND = 'hphi_study'


def _load(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('hphi Study metadata must be regular files, not links')
    return parse_json(path.read_text(encoding='utf-8'))


def is_hphi_study(directory, state, manifest):
    if KIND in (state.get('kind'), manifest.get('kind')): return True
    for name in ('study.json', 'study-results.json'):
        path=directory/name
        if path.is_file():
            data=_load(path)
            if isinstance(data,dict) and data.get('format') in ('superfish_ng_hphi_study', 'superfish_ng_hphi_study_result'):
                return True
    return False


def _point_name(index):
    return f'point-{index:04d}'


def _snapshot(directory, study):
    if directory.is_symlink(): raise ValueError('hphi Study directory must not be linked')
    names=('study.json', 'study-results.json', 'job.json', 'manifest.json')
    result={}
    for name in names:
        _load(directory/name);result[name]=_digest(directory/name)
    expected={_point_name(i) for i in range(len(study.values))}
    if {p.name for p in directory.iterdir() if p.name.startswith('point-')}!=expected:
        raise ValueError('hphi Study point directories differ from requested points')
    for name in sorted(expected):
        point=directory/name
        if point.is_symlink() or not point.is_dir():raise ValueError('hphi Study points must be regular directories')
        result.update({f'{name}/{key}':value for key,value in _job_hashes(point).items()})
    return result


def _summary(study, points):
    return dict(format='superfish_ng_hphi_study_result',schema_version=1,
        physics='axisymmetric_hphi_rf',kind='sweep',parameter=study.parameter,values=list(study.values),
        mode_tracking='not_performed',numerical_validation='not_checked',points=points)


def _point(index, value, modes):
    return dict(index=index,value=value,directory=_point_name(index),modes=modes)


def verify_hphi_study(directory, state, manifest):
    from .jobs import read_job
    directory=Path(directory);study=HphiStudy.from_dict(_load(directory/'study.json'))
    before=_snapshot(directory,study)
    if state.get('status')!='complete' or state.get('kind')!=KIND or manifest.get('kind')!=KIND:
        raise ValueError('hphi Study state and manifest require complete kind=hphi_study')
    fields=['manifest_version','kind','files','implementation_sha256','source_changed_during_run']
    keys(manifest,fields,fields,'hphi Study completion manifest')
    if type(manifest['manifest_version']) is not int or manifest['manifest_version']!=1:
        raise ValueError('hphi Study manifest_version must be 1')
    expected={k:v for k,v in before.items() if k not in ('job.json','manifest.json')}
    if manifest['files']!=expected:raise ValueError('hphi Study manifest must bind every requested point and native file exactly')
    implementation=manifest['implementation_sha256']
    if (not isinstance(implementation,dict) or not implementation
        or any(not isinstance(k,str) or not isinstance(v,str) or len(v)!=64 or any(c not in '0123456789abcdef' for c in v) for k,v in implementation.items())
        or manifest['source_changed_during_run'] is not False):
        raise ValueError('hphi Study requires stable execution provenance')
    rows=[]
    for index,(value,project) in enumerate(zip(study.values,study.projects())):
        point=directory/_point_name(index);point_state=read_job(point)
        if point_state.get('status')!='complete' or point_state.get('kind')!='hphi_solve':
            raise ValueError('hphi Study point is not a complete hphi solve')
        point_manifest=_load(point/'manifest.json')
        if point_state.get('origin') is not None or point_manifest.get('implementation_sha256')!=implementation:
            raise ValueError('hphi Study point must be executed with the recorded Study implementation')
        if HphiProject.load(point/'project.json')!=project:
            raise ValueError('hphi Study point Project differs from the requested parameter value')
        solution=read_hphi_run(point/'solution')
        rows.append(_point(index,value,hphi_result(solution)['modes']))
    result=_load(directory/'study-results.json')
    if json.dumps(result,sort_keys=True,allow_nan=False)!=json.dumps(_summary(study,rows),sort_keys=True,allow_nan=False):
        raise ValueError('hphi Study summary differs from fully verified point spectra/RF; ranks are not tracked identities')
    if (state.get('physics')!='axisymmetric_hphi_rf' or state.get('mode_tracking')!='not_performed'
        or state.get('numerical_validation')!='not_checked' or type(state.get('computed_points')) is not int
        or state['computed_points']!=len(study.values)):
        raise ValueError('hphi Study state differs from verified independent sweep')
    if _load(directory/'job.json')!=state or _load(directory/'manifest.json')!=manifest or _snapshot(directory,study)!=before:
        raise ValueError('hphi Study changed during verification')
    return result


def read_hphi_study(directory):
    directory=Path(directory)
    return verify_hphi_study(directory,_load(directory/'job.json'),_load(directory/'manifest.json'))


def _prepare(study, directory):
    if not isinstance(study,HphiStudy):raise ValueError('expected a dedicated HphiStudy')
    study=HphiStudy.from_dict(study.to_dict())
    raw=json.dumps(study.to_dict(),indent=2,ensure_ascii=False,allow_nan=False)+'\n'
    directory.mkdir(parents=True,exist_ok=False);study.save(directory/'study.json')
    _state(directory,'queued',kind=KIND,study_sha256=hashlib.sha256(raw.encode('utf-8')).hexdigest())


def execute_prepared_hphi_study(directory):
    directory=Path(directory);started=time.monotonic();state=_load(directory/'job.json')
    if directory.is_symlink() or state.get('status')!='queued' or state.get('kind')!=KIND:
        raise ValueError('prepared hphi Study worker requires a queued hphi_study; rerun in a new directory')
    with (directory/'worker.claim').open('x') as stream:stream.write(str(os.getpid())+'\n')
    try:
        implementation=_implementation_hashes();raw=(directory/'study.json').read_bytes();request_hash=hashlib.sha256(raw).hexdigest()
        if (directory/'study.json').is_symlink() or request_hash!=state.get('study_sha256'):
            raise ValueError('queued hphi Study input changed after submission')
        study=HphiStudy.from_dict(parse_json(raw.decode('utf-8')));projects=study.projects();rows=[]
        for index,(value,project) in enumerate(zip(study.values,projects)):
            _state(directory,'running',kind=KIND,stage=f'point {index+1}/{len(projects)}',computed_points=index)
            point=directory/_point_name(index);execute_hphi_project(project,point)
            rows.append(_point(index,value,_load(point/'solution/results.json')['modes']))
        if request_hash!=_digest(directory/'study.json') or implementation!=_implementation_hashes():
            raise ValueError('hphi Study input or implementation changed during execution')
        _write_json(directory/'study-results.json',_summary(study,rows))
        files={name:_digest(directory/name) for name in ('study.json','study-results.json')}
        for index in range(len(projects)):
            name=_point_name(index);files.update({f'{name}/{k}':v for k,v in _job_hashes(directory/name).items()})
        _write_json(directory/'manifest.json',dict(manifest_version=1,kind=KIND,files=files,implementation_sha256=implementation,source_changed_during_run=False))
        _state(directory,'complete',kind=KIND,stage='saved independent spectra',computed_points=len(projects),
            physics='axisymmetric_hphi_rf',mode_tracking='not_performed',numerical_validation='not_checked',elapsed_seconds=time.monotonic()-started)
        result=read_hphi_study(directory)
        if request_hash!=_digest(directory/'study.json') or implementation!=_implementation_hashes():
            raise ValueError('hphi Study input or implementation changed during completion')
        return result
    except Exception as exc:
        _state(directory,'failed',kind=KIND,error=str(exc),elapsed_seconds=time.monotonic()-started)
        raise


def execute_hphi_study(study, directory):
    directory=Path(directory);_prepare(study,directory)
    return execute_prepared_hphi_study(directory)


def start_hphi_study(manager, study):
    with manager.lock:
        if manager.closed:raise ValueError('job manager is closed')
        identifier=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:10];directory=manager.directory(identifier)
        _prepare(study,directory)
        try:
            with (directory/'log.txt').open('x') as log:
                manager.processes[identifier]=subprocess.Popen([sys.executable,'-m','superfish_ng.hphi_study_jobs',str(directory)],
                    stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'OPENBLAS_NUM_THREADS':'1'})
        except Exception as exc:
            _state(directory,'failed',kind=KIND,error=str(exc));raise
        return identifier


if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('usage: python -m superfish_ng.hphi_study_jobs PREPARED_DIRECTORY')
    execute_prepared_hphi_study(Path(sys.argv[1]))
