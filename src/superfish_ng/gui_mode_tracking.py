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
    if state['status']!='complete' or state.get('kind') in ('study','tracked_study','adaptive_study'):
        raise ValueError('mode tracking requires a completed individual saved result; import a Study point first')
    return str((directory/'solution').resolve())


def tracking_response(manager,action,data):
    fields={'compare-modes':('previous_id','current_id','previous_ids','controls'),
            'start-mode-history':('document',),'extend-mode-history':('document','current_id','controls'),
            'replay-mode-tracking':('document',)}
    if action=='track-study-modes':fields[action]=('study_id','initial_ids','step_controls' if 'step_controls' in data else 'controls')
    if action not in fields:raise ValueError('unknown mode tracking operation')
    keys(data,fields[action],fields[action],'GUI mode tracking')
    document=data.get('document')
    if isinstance(document,str):document=parse_json(document)
    if action=='track-study-modes':
        from .study_mode_tracking import build_study_mode_tracking
        from .studies import Study
        directory=manager.directory(data['study_id']);state=read_job(directory)
        if state['status']!='complete' or state.get('kind')!='study':raise ValueError('select a completed Study for ordered tracking')
        controls=data.get('step_controls')
        if 'controls' in data:
            study=Study.from_dict(parse_json((directory/'study.json').read_text()))
            controls=[data['controls'] for _ in range(len(study.values)-1)]
        result=build_study_mode_tracking(dict(schema_version=1,study_run=str(directory.resolve()),initial_ids=data['initial_ids'],step_controls=controls))
    elif action=='compare-modes':
        result=build_saved_mode_tracking(dict(schema_version=1,previous_run=_solution(manager,data['previous_id']),
            current_run=_solution(manager,data['current_id']),previous_ids=data['previous_ids'],controls=data['controls']))
    elif action=='start-mode-history':result=start_mode_history(document)
    elif action=='extend-mode-history':
        result=extend_mode_history(document,dict(current_run=_solution(manager,data['current_id']),controls=data['controls']))
    elif isinstance(document,dict) and document.get('document_type')=='study_mode_tracking':
        from .study_mode_tracking import replay_study_mode_tracking
        result=replay_study_mode_tracking(document)
    elif isinstance(document,dict) and document.get('document_type')=='mode_tracking_history':result=replay_mode_history(document)
    else:result=replay_mode_tracking(document)
    return dict(document=result,serialized=json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
