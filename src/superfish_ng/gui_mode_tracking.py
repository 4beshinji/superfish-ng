# SPDX-License-Identifier: Apache-2.0
"""Local GUI operations reuse native saved-field tracking and replay contracts."""
import json
from .config import keys
from .jobs import read_job
from .project import parse_json
from .saved_mode_tracking import build_saved_mode_tracking,replay_mode_tracking
from .mode_tracking_history import start_mode_history,extend_mode_history,replay_mode_history


def _solution(manager,identifier):
    directory=manager.directory(identifier);state=read_job(directory)
    if state['status']!='complete' or state.get('kind')=='study':
        raise ValueError('mode tracking requires a completed individual saved result; import a Study point first')
    return str((directory/'solution').resolve())


def tracking_response(manager,action,data):
    fields={'compare-modes':('previous_id','current_id','previous_ids','controls'),
            'start-mode-history':('document',),'extend-mode-history':('document','current_id','controls'),
            'replay-mode-tracking':('document',)}
    if action not in fields:raise ValueError('unknown mode tracking operation')
    keys(data,fields[action],fields[action],'GUI mode tracking')
    document=data.get('document')
    if isinstance(document,str):document=parse_json(document)
    if action=='compare-modes':
        result=build_saved_mode_tracking(dict(schema_version=1,previous_run=_solution(manager,data['previous_id']),
            current_run=_solution(manager,data['current_id']),previous_ids=data['previous_ids'],controls=data['controls']))
    elif action=='start-mode-history':result=start_mode_history(document)
    elif action=='extend-mode-history':
        result=extend_mode_history(document,dict(current_run=_solution(manager,data['current_id']),controls=data['controls']))
    elif isinstance(document,dict) and document.get('document_type')=='mode_tracking_history':result=replay_mode_history(document)
    else:result=replay_mode_tracking(document)
    return dict(document=result,serialized=json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
