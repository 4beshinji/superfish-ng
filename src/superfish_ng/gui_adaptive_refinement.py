# SPDX-License-Identifier: Apache-2.0
"""GUI transport for managed affine refinement and native checkpoint replay."""
import json
from .config import keys
from .jobs import read_job
from .project import parse_json
from .adaptive_refinement import read_adaptive_refinement,replay_adaptive_refinement
from .adaptive_refinement_cost import refinement_cost_summary


def adaptive_refinement_response(manager,action,data):
    fields={'start-adaptive-refinement':(('request','max_new_levels'),('request',)),
        'resume-adaptive-refinement':(('document','max_new_levels'),('document',)),
        'adaptive-refinement-result':(('id',),('id',)),
        'replay-adaptive-refinement':(('document',),('document',))}
    if action not in fields:raise ValueError('unknown adaptive refinement operation')
    allowed,required=fields[action];keys(data,allowed,required,'GUI adaptive refinement')
    if action=='start-adaptive-refinement':
        request=data['request']
        if isinstance(request,str):request=parse_json(request)
        return dict(id=manager.start_adaptive_refinement(request,max_new_levels=data.get('max_new_levels')))
    if action=='adaptive-refinement-result':
        directory=manager.directory(data['id']);state=read_job(directory)
        if state['status']!='complete' or state.get('kind')!='adaptive_refinement':
            raise ValueError('select a completed adaptive refinement job; partial checkpoints can be opened separately')
        result=read_adaptive_refinement(directory/'adaptive-refinement-results.json')
    else:
        document=data['document']
        if isinstance(document,str):document=parse_json(document)
        result=replay_adaptive_refinement(document)
        if action=='resume-adaptive-refinement':
            return dict(id=manager.start_adaptive_refinement(result['request'],checkpoint=result,max_new_levels=data.get('max_new_levels')))
    return dict(document=result,serialized=json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n',
                execution_cost=refinement_cost_summary(manager,result))
