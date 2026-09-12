# SPDX-License-Identifier: Apache-2.0
"""Positive-radius Hphi workers and verified imports for both native geometries."""
import os
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
from .config import keys
from .project import parse_json
from .hphi_project import HphiProject
from .hphi_native import solve_hphi, FILES, read_hphi_run, save_hphi_run

KIND='hphi_solve'
NATIVE=FILES|{'manifest.json'}
REQUIRED={'project.json',*(f'solution/{name}' for name in NATIVE)}


def _native_hashes(directory):
    from .jobs import _digest
    if directory.is_symlink() or not directory.is_dir() or {p.name for p in directory.iterdir()}!=NATIVE:
        raise ValueError('hphi job requires exactly five native files in a regular solution directory')
    if any((directory/name).is_symlink() or not (directory/name).is_file() for name in NATIVE):
        raise ValueError('hphi native import requires regular files, not links')
    return {name:_digest(directory/name) for name in sorted(NATIVE)}


def _job_hashes(directory):
    from .jobs import _digest
    native=_native_hashes(directory/'solution')
    names=('project.json','manifest.json','job.json')
    if any((directory/name).is_symlink() or not (directory/name).is_file() for name in names):
        raise ValueError('hphi job metadata must be regular files, not links')
    return {**{f'solution/{name}':value for name,value in native.items()},
        **{name:_digest(directory/name) for name in names}}


def is_hphi_job(directory,state,manifest):
    if state.get('kind')==KIND or manifest.get('kind')==KIND:return True
    for relative in ('project.json','solution/case.json','solution/results.json'):
        path=directory/relative
        if path.is_file():
            data=parse_json(path.read_text(encoding='utf-8'))
            if isinstance(data,dict):
                case=data.get('case',data)
                model=case.get('model',{}) if isinstance(case,dict) else {}
                if (data.get('format') in ('superfish_ng_hphi_project','superfish_ng_coaxial_case','superfish_ng_coaxial_result','superfish_ng_hphi_mesh_case','superfish_ng_hphi_mesh_result')
                        or data.get('physics') in ('axisymmetric_coaxial_hphi_rf','positive_radius_axisymmetric_hphi_rf')
                        or isinstance(case,dict) and case.get('format') in ('superfish_ng_coaxial_case','superfish_ng_hphi_mesh_case')
                        or isinstance(model,dict) and model.get('field_family')=='Hphi'):
                    return True
    return False


def verify_hphi_job(directory,state,manifest):
    directory=Path(directory);before=_job_hashes(directory)
    if state.get('status')!='complete' or state.get('kind')!=KIND or manifest.get('kind')!=KIND:
        raise ValueError('hphi job state and completion manifest require kind=hphi_solve')
    fields=['manifest_version','kind','files','implementation_sha256','source_changed_during_run','imported_from']
    keys(manifest,fields,['manifest_version','kind','files'],'hphi job manifest')
    if type(manifest['manifest_version']) is not int or manifest['manifest_version']!=1:
        raise ValueError('hphi job manifest_version must be 1')
    if not isinstance(manifest['files'],dict) or set(manifest['files'])!=REQUIRED:
        raise ValueError('hphi job manifest must list the project and all five native files exactly')
    if manifest['files']!={name:before[name] for name in REQUIRED}:
        raise ValueError('hphi job output integrity failure')
    project=HphiProject.load(directory/'project.json');solution=read_hphi_run(directory/'solution')
    if project.case.to_dict()!=solution.case.to_dict():
        raise ValueError('hphi saved Case or explicit mesh differs from the job Project')
    if (state.get('numerical_validation')!='not_checked' or state.get('physics')!='axisymmetric_hphi_rf'
            or state.get('case_format')!=project.case.to_dict()['format']
            or type(state.get('case_schema_version')) is not int or state['case_schema_version']!=project.case.to_dict()['schema_version']
            or type(state.get('modes')) is not int or state['modes']!=project.case.modes):
        raise ValueError('hphi job summary differs from its verified native result')
    if 'imported_from' in manifest:
        if (not isinstance(manifest['imported_from'],str) or not manifest['imported_from']
                or state.get('origin')!='imported' or state.get('source_completion') not in ('verified hphi native','verified hphi job')):
            raise ValueError('hphi import provenance disagrees with completion state')
        if 'implementation_sha256' in manifest or 'source_changed_during_run' in manifest:
            raise ValueError('hphi import must not claim a new solver execution')
    else:
        hashes=manifest.get('implementation_sha256')
        if (not isinstance(hashes,dict) or not hashes or any(not isinstance(k,str) or not isinstance(v,str) or len(v)!=64 or any(c not in '0123456789abcdef' for c in v) for k,v in hashes.items())
                or manifest.get('source_changed_during_run') is not False or 'origin' in state):
            raise ValueError('hphi execution requires implementation provenance and stable source')
    if (parse_json((directory/'job.json').read_text())!=state
            or parse_json((directory/'manifest.json').read_text())!=manifest
            or _job_hashes(directory)!=before):
        raise ValueError('hphi job files changed during verification')
    return solution


def _prepare(project,directory):
    from .jobs import _state
    if not isinstance(project,HphiProject):raise ValueError('expected a dedicated HphiProject')
    project=HphiProject.from_dict(project.to_dict())
    directory.mkdir(parents=True,exist_ok=False);project.save(directory/'project.json')
    _state(directory,'queued',kind=KIND,project_sha256=hashlib.sha256(project.dumps().encode('utf-8')).hexdigest())
    return project


def _complete(directory,project,*,project_hash,started,implementation=None,imported_from=None,source_completion=None):
    from .jobs import _digest,_write_json,_state,read_job,_implementation_hashes
    # Verify physical coefficients and geometry before publishing complete.
    solution=read_hphi_run(directory/'solution')
    if solution.case.to_dict()!=project.case.to_dict():raise ValueError('hphi output does not match prepared project')
    if _digest(directory/'project.json')!=project_hash:raise ValueError('hphi project changed during completion')
    if implementation is not None and implementation!=_implementation_hashes():raise ValueError('implementation changed during hphi completion')
    files={'project.json':project_hash,**{f'solution/{k}':v for k,v in _native_hashes(directory/'solution').items()}}
    manifest=dict(manifest_version=1,kind=KIND,files=files)
    extra={}
    if imported_from is None:manifest.update(implementation_sha256=implementation,source_changed_during_run=False)
    else:
        manifest['imported_from']=str(imported_from)
        extra.update(origin='imported',source_completion=source_completion)
    _write_json(directory/'manifest.json',manifest)
    _state(directory,'complete',kind=KIND,stage='saved' if imported_from is None else 'imported saved result',
        numerical_validation='not_checked',physics='axisymmetric_hphi_rf',case_format=project.case.to_dict()['format'],case_schema_version=project.case.to_dict()['schema_version'],modes=project.case.modes,elapsed_seconds=time.monotonic()-started,**extra)
    result=read_job(directory)
    if _digest(directory/'project.json')!=project_hash:raise ValueError('hphi project changed during final verification')
    if implementation is not None and implementation!=_implementation_hashes():raise ValueError('implementation changed during hphi final verification')
    return result


def execute_prepared_hphi_project(directory):
    from .jobs import _digest,_implementation_hashes,_state
    directory=Path(directory);started=time.monotonic()
    state_path=directory/'job.json'
    if directory.is_symlink() or state_path.is_symlink():raise ValueError('prepared hphi job must not be linked')
    state=parse_json(state_path.read_text(encoding='utf-8'))
    if state.get('status')!='queued' or state.get('kind')!=KIND:
        raise ValueError('prepared hphi worker requires a queued hphi_solve job; use a new directory to rerun')
    # Exclusive claim prevents duplicate workers from consuming one queued
    # directory. It is not evidence that a process remains alive.
    with (directory/'worker.claim').open('x',encoding='utf-8') as stream:stream.write(str(os.getpid())+'\n')
    try:
        implementation=_implementation_hashes()
        project_path=directory/'project.json'
        if project_path.is_symlink() or not project_path.is_file():raise ValueError('queued hphi Project must be a regular file')
        raw=project_path.read_bytes();project_hash=hashlib.sha256(raw).hexdigest()
        if state.get('project_sha256')!=project_hash:raise ValueError('queued hphi Project changed after submission')
        project=HphiProject.from_dict(parse_json(raw.decode('utf-8')))
        _state(directory,'running',kind=KIND,stage='finite element solve')
        solution=solve_hphi(project.case)
        _state(directory,'running',kind=KIND,stage='saving fields and full-cavity RF')
        save_hphi_run(project.case,solution,directory/'solution')
        if _digest(directory/'project.json')!=project_hash:raise ValueError('hphi project changed during execution')
        if implementation!=_implementation_hashes():raise ValueError('implementation changed during hphi execution')
        return _complete(directory,project,project_hash=project_hash,started=started,implementation=implementation)
    except Exception as exc:
        _state(directory,'failed',kind=KIND,error=str(exc),elapsed_seconds=time.monotonic()-started)
        raise


def execute_hphi_project(project,directory):
    directory=Path(directory);_prepare(project,directory)
    return execute_prepared_hphi_project(directory)


def start_hphi(manager,project):
    from .jobs import _state
    with manager.lock:
        if manager.closed:raise ValueError('job manager is closed')
        identifier=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:10];directory=manager.directory(identifier)
        _prepare(project,directory)
        try:
            with (directory/'log.txt').open('x') as log:
                process=subprocess.Popen([sys.executable,'-m','superfish_ng.hphi_jobs',str(directory)],stdout=log,stderr=subprocess.STDOUT,
                    env={**os.environ,'OPENBLAS_NUM_THREADS':'1'})
            manager.processes[identifier]=process
        except Exception as exc:
            _state(directory,'failed',kind=KIND,error=str(exc));raise
        return identifier


def import_hphi_result(manager,source):
    from .jobs import _state,read_job,_digest
    started=time.monotonic();source=Path(source)
    if source.is_symlink():raise ValueError('hphi import source must not be a symbolic link')
    source=source.resolve();managed=(source/'job.json').is_file();solution_dir=source/'solution' if managed else source
    with manager.lock:
        if manager.closed:raise ValueError('job manager is closed')
        snapshot=(lambda:_job_hashes(source)) if managed else (lambda:_native_hashes(source))
        before=snapshot();solution=read_hphi_run(solution_dir)
        if managed:
            state=read_job(source)
            if state.get('status')!='complete' or state.get('kind')!=KIND:raise ValueError('source is not a complete hphi job')
            project=HphiProject.load(source/'project.json')
        else:project=HphiProject(solution.case)
        if snapshot()!=before:raise ValueError('hphi import source changed during verification')
        identifier=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:10];directory=manager.directory(identifier)
        _prepare(project,directory);project_hash=_digest(directory/'project.json')
        try:
            target=directory/'solution';target.mkdir()
            for name in sorted(NATIVE-{'manifest.json'}):
                if (solution_dir/name).is_symlink():raise ValueError('hphi source became a symbolic link')
                shutil.copyfile(solution_dir/name,target/name)
            if snapshot()!=before:raise ValueError('hphi import source changed during copying')
            temporary=target/'.import-manifest.tmp';shutil.copyfile(solution_dir/'manifest.json',temporary)
            os.link(temporary,target/'manifest.json');temporary.unlink()
            if snapshot()!=before:raise ValueError('hphi import source changed during publication')
            (directory/'log.txt').write_text('Imported verified hphi native; saved coefficients preserved; spectrum recomputed for verification.\n')
            _complete(directory,project,project_hash=project_hash,started=started,imported_from=source,source_completion='verified hphi job' if managed else 'verified hphi native')
            if snapshot()!=before:raise ValueError('hphi import source changed during completion')
            return identifier
        except Exception as exc:
            _state(directory,'failed',kind=KIND,error=str(exc));raise


if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('usage: python -m superfish_ng.hphi_jobs PREPARED_DIRECTORY')
    execute_prepared_hphi_project(Path(sys.argv[1]))
