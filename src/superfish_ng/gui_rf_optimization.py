# SPDX-License-Identifier: Apache-2.0
"""Verified GUI transport for RF search requests, checkpoints and selected fields."""
import json
from pathlib import Path
from .config import keys,integer
from .project import parse_json
from .jobs import read_job
from .rf_optimization import validate_optimization_request,read_rf_optimization,replay_rf_optimization
from .rf_optimization_checkpoints import list_optimization_checkpoints,open_optimization_checkpoint


def rf_optimization_response(manager,action,data):
    fields={
        'prepare-rf-optimization':(('request',),('request',)),
        'start-rf-optimization':(('request','max_new_trials'),('request',)),
        'resume-rf-optimization':(('document','max_new_trials'),('document',)),
        'rf-optimization-result':(('id',),('id',)),
        'replay-rf-optimization':(('document',),('document',)),
        'rf-optimization-checkpoints':(('id',),('id',)),
        'open-rf-optimization-checkpoint':(('id','index'),('id','index')),
        'rf-optimization-field':(('document','trial','level'),('document','trial','level'))}
    if action not in fields:raise ValueError('unknown RF optimization operation')
    allowed,required=fields[action];keys(data,allowed,required,'GUI RF optimization')
    if action in ('prepare-rf-optimization','start-rf-optimization'):
        request=data['request'];request=parse_json(request) if isinstance(request,str) else request
        validate_optimization_request(request)
        if action=='start-rf-optimization':return dict(id=manager.start_rf_optimization(request,max_new_trials=data.get('max_new_trials')))
        return dict(request=request,serialized=json.dumps(request,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    if action=='rf-optimization-checkpoints':return list_optimization_checkpoints(manager,data['id'])
    if action=='open-rf-optimization-checkpoint':
        result=open_optimization_checkpoint(manager,data['id'],data['index'])
    elif action=='rf-optimization-result':
        directory=manager.directory(data['id']);state=read_job(directory)
        if state['status']!='complete' or state.get('kind')!='rf_optimization':
            raise ValueError('select a completed RF optimization job; stopped checkpoints are separate')
        result=read_rf_optimization(directory/'rf-optimization-results.json')
    else:
        document=data['document'];document=parse_json(document) if isinstance(document,str) else document
        result=replay_rf_optimization(document)
        if action=='resume-rf-optimization':
            return dict(id=manager.start_rf_optimization(result['request'],checkpoint=result,max_new_trials=data.get('max_new_trials')))
        if action=='rf-optimization-field':
            trial=data['trial'];level=data['level'];integer(trial,'trial',0);integer(level,'level',0)
            if trial>=len(result['trials']) or level>=3:raise ValueError('select an existing trial and a level from 0 to 2')
            assessment=result['trials'][trial]['assessment']
            if assessment is None:raise ValueError('selected trial has no verified individual mode; field selection cannot assume frequency rank')
            rank=assessment['assessment']['rows'][level]['mode_index']
            imported=manager.import_result(Path(result['trial_directories'][trial])/f'level-{level}')
            return dict(id=imported,mode=rank,trial=trial,level=level,mode_id=result['request']['mode_id'])
    return dict(document=result,serialized=json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
