# SPDX-License-Identifier: Apache-2.0
"""Isolated local jobs for bounded adaptive FEM tracking and checkpoint resume."""
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import uuid
from .jobs import _state,_write_json,_digest,_implementation_hashes
from .project import parse_json
from .adaptive_study import _request,execute_adaptive_study,replay_adaptive_study
from .saved_mode_tracking import _canonical


def start_adaptive_study(manager,request,*,max_new_attempts=None,checkpoint=None):
    with manager.lock:
        if manager.closed:raise ValueError('job manager is closed')
        request=deepcopy(request);_request(request)
        if max_new_attempts is not None and (type(max_new_attempts) is not int or max_new_attempts<1):
            raise ValueError('max_new_attempts must be a positive integer')
        if checkpoint is not None:
            checkpoint=replay_adaptive_study(checkpoint)
            if not checkpoint.get('can_resume',False):raise ValueError('only a verified PAUSED adaptive Study can resume')
            if _canonical(request)!=_canonical(checkpoint['request']):raise ValueError('adaptive resume request differs from checkpoint')
        identifier=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:10]
        directory=manager.directory(identifier);directory.mkdir()
        _write_json(directory/'adaptive-study-request.json',dict(request=request,max_new_attempts=max_new_attempts,checkpoint=checkpoint))
        _state(directory,'queued',kind='adaptive_study')
        try:
            with (directory/'log.txt').open('x') as log:
                process=subprocess.Popen([sys.executable,'-m','superfish_ng.adaptive_study_jobs',str(directory)],
                    stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'OPENBLAS_NUM_THREADS':'1'})
            manager.processes[identifier]=process
        except Exception as exc:
            _state(directory,'failed',kind='adaptive_study',error=str(exc));raise
        return identifier


def execute_prepared_adaptive_study(directory):
    directory=Path(directory);started=time.monotonic()
    implementation=_implementation_hashes();request_hash=_digest(directory/'adaptive-study-request.json')
    try:
        data=parse_json((directory/'adaptive-study-request.json').read_text(encoding='utf-8'))
        from .config import keys
        fields=('request','max_new_attempts','checkpoint');keys(data,fields,fields,'adaptive Study job input')
        _state(directory,'running',kind='adaptive_study',stage='adaptive FEM solves and saved-field tracking')
        result=execute_adaptive_study(data['request'],directory/'execution',max_new_attempts=data['max_new_attempts'],checkpoint=data['checkpoint'])
        if implementation!=_implementation_hashes() or request_hash!=_digest(directory/'adaptive-study-request.json'):
            raise RuntimeError('implementation or adaptive Study request changed during run')
        _write_json(directory/'adaptive-study-results.json',result)
        files={name:_digest(directory/name) for name in ('adaptive-study-request.json','adaptive-study-results.json')}
        files.update({p.relative_to(directory).as_posix():_digest(p) for p in sorted((directory/'execution').rglob('*')) if p.is_file()})
        _write_json(directory/'manifest.json',dict(manifest_version=1,kind='adaptive_study',files=files,
            implementation_sha256=implementation,source_changed_during_run=False))
        _state(directory,'complete',kind='adaptive_study',tracking_status=result['status'],can_resume=result['can_resume'],
            computed_points=len(result['points']),accepted_points=len(result['accepted_point_indices']),completed_attempts=len(result['attempts']),
            unreached_target_indices=result['unreached_target_indices'],numerical_validation='not_checked',elapsed_seconds=time.monotonic()-started)
        return result
    except Exception as exc:
        _state(directory,'failed',kind='adaptive_study',error=str(exc),elapsed_seconds=time.monotonic()-started)
        raise


if __name__=='__main__':
    try:execute_prepared_adaptive_study(Path(sys.argv[1]))
    except Exception:
        traceback.print_exc();sys.exit(2)
