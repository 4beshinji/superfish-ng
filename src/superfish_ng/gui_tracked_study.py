# SPDX-License-Identifier: Apache-2.0
"""GUI transport for sequential tracked Study jobs and exact checkpoint replay."""
import json
from .config import keys
from .jobs import read_job
from .project import parse_json
from .tracked_study import read_tracked_study,replay_tracked_study


def tracked_study_response(manager,action,data):
    fields={'start-tracked-study':(('request','max_new_points'),('request',)),
            'resume-tracked-study':(('document','max_new_points'),('document',)),
            'tracked-study-result':(('id',),('id',)),
            'replay-tracked-study':(('document',),('document',))}
    if action not in fields:raise ValueError('unknown tracked Study operation')
    allowed,required=fields[action];keys(data,allowed,required,'GUI tracked Study')
    if action=='start-tracked-study':
        return dict(id=manager.start_tracked_study(data['request'],max_new_points=data.get('max_new_points')))
    if action=='tracked-study-result':
        directory=manager.directory(data['id']);state=read_job(directory)
        if state['status']!='complete' or state.get('kind')!='tracked_study':
            raise ValueError('select a completed tracked Study job; partial checkpoints can be opened separately')
        result=read_tracked_study(directory/'tracked-study-results.json')
    else:
        document=data['document']
        if isinstance(document,str):document=parse_json(document)
        result=replay_tracked_study(document)
        if action=='resume-tracked-study':
            return dict(id=manager.start_tracked_study(result['request'],max_new_points=data.get('max_new_points'),checkpoint=result))
    return dict(document=result,serialized=json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
