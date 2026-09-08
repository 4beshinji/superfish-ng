# SPDX-License-Identifier: Apache-2.0
"""Background tracked Study jobs using the common sequential FEM executor."""
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import uuid
from .jobs import _state, _write_json, _digest, _implementation_hashes
from .project import parse_json
from .tracked_study import _request, execute_tracked_study, replay_tracked_study
from .saved_mode_tracking import _canonical


def start_tracked_study(manager,request,*,max_new_points=None,checkpoint=None):
    with manager.lock:
        if manager.closed:raise ValueError('job manager is closed')
        request=deepcopy(request);_request(request)
        if max_new_points is not None and (type(max_new_points) is not int or max_new_points<1):
            raise ValueError('max_new_points must be a positive integer')
        if checkpoint is not None:
            checkpoint=replay_tracked_study(checkpoint)
            if not checkpoint['can_resume']:raise ValueError('only a verified PAUSED tracked Study can resume')
            if _canonical(request)!=_canonical(checkpoint['request']):raise ValueError('resume request differs from checkpoint')
        identifier=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:10]
        directory=manager.directory(identifier);directory.mkdir()
        _write_json(directory/'tracked-study-request.json',dict(request=request,max_new_points=max_new_points,checkpoint=checkpoint))
        _state(directory,'queued',kind='tracked_study')
        try:
            with (directory/'log.txt').open('x') as log:
                process=subprocess.Popen([sys.executable,'-m','superfish_ng.tracked_study_jobs',str(directory)],
                    stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'OPENBLAS_NUM_THREADS':'1'})
            manager.processes[identifier]=process
        except Exception as exc:
            _state(directory,'failed',kind='tracked_study',error=str(exc));raise
        return identifier


def execute_prepared_tracked_study(directory):
    directory=Path(directory)
    implementation=_implementation_hashes();request_hash=_digest(directory/'tracked-study-request.json')
    started=time.monotonic()
    try:
        data=parse_json((directory/'tracked-study-request.json').read_text(encoding='utf-8'))
        from .config import keys
        keys(data,('request','max_new_points','checkpoint'),('request','max_new_points','checkpoint'),'tracked Study job input')
        _state(directory,'running',kind='tracked_study',stage='sequential FEM solves and saved-field tracking')
        result=execute_tracked_study(data['request'],directory/'execution',max_new_points=data['max_new_points'],checkpoint=data['checkpoint'])
        if implementation!=_implementation_hashes() or request_hash!=_digest(directory/'tracked-study-request.json'):
            raise RuntimeError('implementation or tracked Study request changed during run')
        _write_json(directory/'tracked-study-results.json',result)
        files={name:_digest(directory/name) for name in ('tracked-study-request.json','tracked-study-results.json')}
        files.update({p.relative_to(directory).as_posix():_digest(p) for p in sorted((directory/'execution').rglob('*')) if p.is_file()})
        _write_json(directory/'manifest.json',dict(manifest_version=1,kind='tracked_study',files=files,
            implementation_sha256=implementation,source_changed_during_run=False))
        _state(directory,'complete',kind='tracked_study',tracking_status=result['status'],can_resume=result['can_resume'],
            computed_points=len(result['point_runs']),numerical_validation='not_checked',elapsed_seconds=time.monotonic()-started)
        return result
    except Exception as exc:
        _state(directory,'failed',kind='tracked_study',error=str(exc),elapsed_seconds=time.monotonic()-started)
        raise


if __name__=='__main__':
    try:execute_prepared_tracked_study(Path(sys.argv[1]))
    except Exception:
        traceback.print_exc();sys.exit(2)
