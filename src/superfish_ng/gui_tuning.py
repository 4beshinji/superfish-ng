# SPDX-License-Identifier: Apache-2.0
"""GUI transport for managed tuning and exact checkpoint replay."""
import json
from .config import keys
from .jobs import read_job
from .project import parse_json
from .tuning import read_tune,replay_tune


def tuning_response(manager,action,data):
    fields={'start-tune':(('request','max_new_trials'),('request',)),
        'resume-tune':(('document','max_new_trials'),('document',)),
        'tune-result':(('id',),('id',)), 'replay-tune':(('document',),('document',))}
    if action not in fields:raise ValueError('unknown tuning operation')
    allowed,required=fields[action];keys(data,allowed,required,'GUI tuning')
    if action=='start-tune':return dict(id=manager.start_tune(data['request'],max_new_trials=data.get('max_new_trials')))
    if action=='tune-result':
        directory=manager.directory(data['id']);state=read_job(directory)
        if state['status']!='complete' or state.get('kind')!='tune':
            raise ValueError('select a completed tune job; partial checkpoints can be opened separately')
        result=read_tune(directory/'tune-results.json')
    else:
        document=data['document']
        if isinstance(document,str):document=parse_json(document)
        result=replay_tune(document)
        if action=='resume-tune':
            return dict(id=manager.start_tune(result['request'],checkpoint=result,max_new_trials=data.get('max_new_trials')))
    return dict(document=result,serialized=json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
