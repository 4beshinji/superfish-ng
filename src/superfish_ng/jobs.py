# SPDX-License-Identifier: Apache-2.0
"""Local jobs with exclusive destinations and verified completion manifests."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import traceback
import uuid

from .project import Project
from .solver import solve
from .io import save_run


def _write_json(path, data):
    temporary = path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    with temporary.open('x',encoding='utf-8') as stream:
        json.dump(data,stream,ensure_ascii=False,indent=2,allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    temporary.replace(path)


def _digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def _state(directory,status,**extra):
    data={'status':status,'updated_unix':time.time(),**extra}
    _write_json(directory/'job.json',data)
    return data


def read_job(directory, verify=True):
    directory=Path(directory)
    state=json.loads((directory/'job.json').read_text(encoding='utf-8'))
    if state.get('status')=='complete' and verify:
        manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
        files=manifest.get('files',{})
        required={'project.json','solution/case.json','solution/results.json','solution/fields.npz','solution/modes.csv'}
        if not required.issubset(files): raise ValueError('completion manifest missing required output')
        for name,digest in files.items():
            path=directory/name
            if Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink():
                raise ValueError('invalid completion manifest path')
            if not path.is_file() or _digest(path)!=digest:
                raise ValueError(f'output integrity failure or missing file: {name}')
    return state


def _prepare(project,directory):
    # Serialize and revalidate also for callers using the dataclass constructor.
    project=Project.from_dict(project.to_dict())
    directory.mkdir(parents=True,exist_ok=False)
    project.save(directory/'project.json')
    _state(directory,'queued')


def _implementation_hashes():
    root=Path(__file__).parent
    return {p.relative_to(root).as_posix():_digest(p) for p in sorted(root.rglob('*'))
            if p.is_file() and p.suffix in ('.py','.html','.js','.css')}


def _execute_prepared(directory):
    start=time.monotonic()
    implementation=_implementation_hashes()
    try:
        project=Project.load(directory/'project.json')
        _state(directory,'running',stage='finite element solve')
        solution=solve(project.case)
        case=project.case
        if project.reflect_full:
            from .symmetry import reflect_solution
            case,solution=reflect_solution(case,solution)
        _state(directory,'running',stage='saving fields and RF quantities')
        save_run(case,solution,directory/'solution')
        files={'project.json':_digest(directory/'project.json')}
        files.update({p.relative_to(directory).as_posix():_digest(p)
                      for p in sorted((directory/'solution').iterdir()) if p.is_file()})
        if implementation != _implementation_hashes():
            raise RuntimeError('implementation changed during run; retry with stable source')
        _write_json(directory/'manifest.json',{'manifest_version':1,'files':files,
                                               'implementation_sha256':implementation,
                                               'source_changed_during_run':False})
        _state(directory,'complete',elapsed_seconds=time.monotonic()-start,
               numerical_validation='not_checked',stage='saved')
        return read_job(directory)
    except Exception as exc:
        _state(directory,'failed',error=str(exc),elapsed_seconds=time.monotonic()-start)
        raise


def execute_project(project,directory):
    """Synchronously solve a project into a new directory; never overwrite."""
    directory=Path(directory)
    _prepare(project,directory)
    return _execute_prepared(directory)


class JobManager:
    """One local application's jobs; subprocesses isolate solves from the UI.

    The application owns the workspace exclusively. An advisory file lock
    prevents a second manager from reclassifying live work after a restart.
    """
    def __init__(self,root):
        import fcntl
        self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True)
        self._workspace_lock=(self.root/'.manager.lock').open('a+')
        try: fcntl.flock(self._workspace_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self._workspace_lock.close()
            raise ValueError('workspace already has a running application; choose another workspace')
        self.processes={};self.lock=threading.RLock();self.closed=False
        for p in self.root.iterdir():
            if p.is_dir() and not p.is_symlink() and (p/'job.json').is_file():
                state=read_job(p,verify=False)
                if state.get('status') in ('queued','running'):
                    _state(p,'interrupted',error='application stopped before completion; start a new run')

    def directory(self,identifier):
        if not isinstance(identifier,str) or not identifier or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in identifier):
            raise ValueError('invalid job identifier')
        path=self.root/identifier
        if path.is_symlink(): raise ValueError('job directory must not be a symlink')
        return path

    def start(self,project):
        with self.lock:
            if self.closed: raise ValueError('job manager is closed')
            identifier=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:10]
            directory=self.directory(identifier);_prepare(project,directory)
            try:
                with (directory/'log.txt').open('x') as log:
                    proc=subprocess.Popen([sys.executable,'-m','superfish_ng.jobs',str(directory)],
                                          stdout=log,stderr=subprocess.STDOUT,
                                          env={**os.environ,'OPENBLAS_NUM_THREADS':'1'})
                self.processes[identifier]=proc
            except Exception as exc:
                _state(directory,'failed',error=str(exc));raise
            return identifier

    def status(self,identifier,verify=False):
        with self.lock:
            directory=self.directory(identifier)
            state=read_job(directory,verify=verify)
            process=self.processes.get(identifier)
            if process is not None and process.poll() is not None and state['status'] in ('queued','running'):
                state=_state(directory,'failed',error=f'worker exited {process.returncode} before completion')
            return {'id':identifier,**state}

    def cancel(self,identifier):
        with self.lock:
            state=self.status(identifier)
            if state['status'] not in ('queued','running'):return state
            process=self.processes.get(identifier)
            if process is not None:
                process.terminate()
                try: process.wait(timeout=3)
                except subprocess.TimeoutExpired: process.kill();process.wait()
            # A complete save that won the race stays complete.
            if read_job(self.directory(identifier),verify=False)['status']!='complete':
                _state(self.directory(identifier),'cancelled',error='cancelled by user; start a new run to retry')
            return self.status(identifier)

    def list(self):
        with self.lock:
            return [self.status(p.name) for p in sorted(self.root.iterdir(),reverse=True)
                    if p.is_dir() and not p.is_symlink() and (p/'job.json').is_file()]

    def close(self):
        with self.lock:
            if self.closed:return
            for identifier in self.processes:self.cancel(identifier)
            self.closed=True;self._workspace_lock.close()


if __name__=='__main__':
    try:_execute_prepared(Path(sys.argv[1]))
    except Exception:traceback.print_exc();sys.exit(2)
