# SPDX-License-Identifier: Apache-2.0
"""GUI transport for sequential/adaptive Study jobs and exact checkpoint replay."""
import json
from .config import keys
from .jobs import read_job
from .project import parse_json
from .tracked_study import read_tracked_study,replay_tracked_study
from .adaptive_study import read_adaptive_study,replay_adaptive_study


def tracked_study_response(manager,action,data):
    adaptive=action in ('start-adaptive-study','resume-adaptive-study','adaptive-study-result','replay-adaptive-study')
    prefix='adaptive' if adaptive else 'tracked'
    limit='max_new_attempts' if adaptive else 'max_new_points'
    fields={f'start-{prefix}-study':(('request',limit),('request',)),
            f'resume-{prefix}-study':(('document',limit),('document',)),
            f'{prefix}-study-result':(('id',),('id',)),
            f'replay-{prefix}-study':(('document',),('document',))}
    if action not in fields:raise ValueError('unknown tracked Study operation')
    allowed,required=fields[action];keys(data,allowed,required,'GUI tracked Study')
    start=manager.start_adaptive_study if adaptive else manager.start_tracked_study
    replay=replay_adaptive_study if adaptive else replay_tracked_study
    if action==f'start-{prefix}-study':
        request=parse_json(data['request']) if isinstance(data['request'],str) else data['request']
        return dict(id=start(request,**{limit:data.get(limit)}))
    if action==f'{prefix}-study-result':
        directory=manager.directory(data['id']);state=read_job(directory)
        if state['status']!='complete' or state.get('kind')!=prefix+'_study':
            raise ValueError(f'select a completed {prefix} Study job; partial checkpoints can be opened separately')
        reader=read_adaptive_study if adaptive else read_tracked_study
        result=reader(directory/f'{prefix}-study-results.json')
    else:
        document=data['document']
        if isinstance(document,str):document=parse_json(document)
        result=replay(document)
        if action==f'resume-{prefix}-study':
            return dict(id=start(result['request'],checkpoint=result,**{limit:data.get(limit)}))
    return dict(document=result,serialized=json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
