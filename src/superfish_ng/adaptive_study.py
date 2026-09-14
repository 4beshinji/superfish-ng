# SPDX-License-Identifier: Apache-2.0
"""Bounded interval bisection for real FEM geometry sweeps with retained failures."""
from copy import deepcopy
from dataclasses import replace
import json
import math
from pathlib import Path
from .config import keys
from .project import parse_json
from .studies import Study
from .jobs import execute_project,_implementation_hashes
from .tracked_study import _request as validate_tracking_request,_point_sources
from .saved_mode_tracking import build_saved_mode_tracking,_canonical
from .mode_tracking_history import start_mode_history,extend_mode_history
from .curved_affine_study import pair_controls


def _request(request):
    fields=('schema_version','study','initial_ids','step_controls','adaptive')
    keys(request,fields,fields,'adaptive tracked Study request')
    base={key:request[key] for key in fields if key!='adaptive'}
    study,_=validate_tracking_request(base)
    if study.kind!='curved_affine_sweep' and (study.kind!='sweep' or not study.parameter.startswith('/case/geometry/')):
        raise ValueError('adaptive tracking requires a continuous numeric /case/geometry/ sweep or declared curved_affine_sweep')
    values=study.values
    if not (all(b>a for a,b in zip(values,values[1:])) or all(b<a for a,b in zip(values,values[1:]))):
        raise ValueError('adaptive Study values must be strictly monotone')
    settings=request['adaptive'];names=('max_depth','max_attempts','minimum_parameter_step')
    keys(settings,names,names,'adaptive limits')
    if type(settings['max_depth']) is not int or not 0<=settings['max_depth']<=20:raise ValueError('max_depth must be an integer from 0 to 20')
    if type(settings['max_attempts']) is not int or settings['max_attempts']<1:raise ValueError('max_attempts must be a positive integer')
    step=settings['minimum_parameter_step']
    if type(step) not in (float,int) or not math.isfinite(step) or step<=0:raise ValueError('minimum_parameter_step must be finite and positive')
    # Reject discrete geometry fields before reserving any output.
    for a,b in zip(values,values[1:]):_project(study,_midpoint(a,b))
    return study,settings


def _midpoint(a,b):return .5*a+.5*b


def _project(study,value):
    return replace(study,values=[value,value]).projects()[0]


def _run(request,obtain_point,*,schema_version=1,pause_after_attempts=None,on_checkpoint=None):
    study,limits=_request(request)
    points=[];attempts=[];accepted=[];history=None;reached=[0];stop=None
    def point(value):
        for i,record in enumerate(points):
            if record['value']==value:return i
        project=_project(study,value);run=obtain_point(len(points),value,project)
        if type(run) is not str or not Path(run).is_absolute():raise ValueError('adaptive point run must be absolute')
        if any(record['run']==run for record in points):raise ValueError('adaptive points require distinct native run directories')
        sources=_point_sources(Path(run),project)
        points.append(dict(value=value,run=run,sources_sha256=sources))
        return len(points)-1
    accepted.append(point(study.values[0]))
    pending=[dict(value=study.values[i],target_index=i,depth=0) for i in reversed(range(1,len(study.values)))]
    def snapshot():
        for record in points:
            if record['sources_sha256']!=_point_sources(Path(record['run']),_project(study,record['value'])):
                raise ValueError('adaptive Study point sources changed during execution or replay')
        result=dict(schema_version=schema_version,document_type='adaptive_tracked_study',request=deepcopy(request),points=points,attempts=attempts,
            accepted_point_indices=accepted,reached_target_indices=reached,unreached_target_indices=[i for i in range(len(study.values)) if i not in reached],
            history=history,status='UNVERIFIED' if stop else 'PAUSED' if pending else 'COMPLETE',stop_reason=stop,
            scope='bounded midpoint subdivision of sampled geometry correspondence; rejected comparisons retained; no threshold relaxation, individual branch recovery or physical convergence certificate')

        if schema_version==2:
            result.update(can_resume=result['status']=='PAUSED',pending_targets=list(reversed(pending)))
        return deepcopy(result)

    while pending:
        if len(attempts)>=limits['max_attempts']:
            stop='maximum_attempts';break
        target=pending.pop();previous=accepted[-1];current=point(target['value'])
        controls=pair_controls(study,request['step_controls'][target['target_index']-1],points[previous]['value'],points[current]['value'])
        if history is None:
            pair=build_saved_mode_tracking(dict(schema_version=1,previous_run=str(Path(points[previous]['run'])/'solution'),
                current_run=str(Path(points[current]['run'])/'solution'),previous_ids=request['initial_ids'],controls=controls))
            candidate=start_mode_history(pair)
        else:
            candidate=extend_mode_history(history,dict(current_run=str(Path(points[current]['run'])/'solution'),controls=controls))
            pair=candidate['steps'][-1]
        attempt=dict(previous_point=previous,current_point=current,original_target_index=target['target_index'],depth=target['depth'],
                     correspondence=pair,decision='ACCEPT',midpoint=None,stop_reason=None)
        if candidate['can_extend']:
            history=candidate;accepted.append(current)
            if target['value']==study.values[target['target_index']]:reached.append(target['target_index'])
        else:
            a=points[previous]['value'];b=target['value'];middle=_midpoint(a,b)
            if len(attempts)+1>=limits['max_attempts']:reason='maximum_attempts'
            elif target['depth']>=limits['max_depth']:reason='maximum_depth'
            elif middle in (a,b):reason='floating_point_resolution'
            elif min(abs(middle-a),abs(b-middle))<limits['minimum_parameter_step']:reason='minimum_parameter_step'
            else:reason=None
            if reason:
                attempt.update(decision='STOP',stop_reason=reason);stop=reason
            else:
                attempt.update(decision='BISECT',midpoint=middle)
                pending.append(dict(target,depth=target['depth']+1))
                pending.append(dict(value=middle,target_index=target['target_index'],depth=target['depth']+1))
        attempts.append(attempt)
        if pending and not stop and len(attempts)>=limits['max_attempts']:stop='maximum_attempts'
        if on_checkpoint is not None:on_checkpoint(snapshot())
        if stop or (pause_after_attempts is not None and len(attempts)>=pause_after_attempts):break
    return snapshot()


def _save_document(result,path):
    with Path(path).open('x',encoding='utf-8') as stream:
        stream.write(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n')


def execute_adaptive_study(request,directory,*,max_new_attempts=None,checkpoint=None):
    """Execute into new output, retaining an immutable checkpoint after each attempt."""
    request=deepcopy(request);_request(request)
    if max_new_attempts is not None and (type(max_new_attempts) is not int or max_new_attempts<1):
        raise ValueError('max_new_attempts must be a positive integer')
    previous=None;records=[];completed_attempts=0
    if checkpoint is not None:
        previous=replay_adaptive_study(checkpoint)
        if not previous.get('can_resume',False):raise ValueError('only a verified PAUSED adaptive Study can resume')
        if _canonical(previous['request'])!=_canonical(request):raise ValueError('adaptive resume request differs from checkpoint; limits, thresholds and IDs cannot change')
        records=previous['points'];completed_attempts=len(previous['attempts'])
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=False)
    implementation=_implementation_hashes()
    def obtain(index,value,project):
        if index<len(records):
            record=records[index]
            if _canonical(value)!=_canonical(record['value']) or record['sources_sha256']!=_point_sources(Path(record['run']),project):
                raise ValueError('adaptive resume point sequence or prior sources changed')
            return record['run']
        run=directory/f'point-{index+1:03d}';execute_project(project,run);return str(run)
    def publish(result):
        if implementation!=_implementation_hashes():raise RuntimeError('implementation changed during adaptive Study execution')
        count=len(result['attempts'])
        if previous is not None and count==completed_attempts and _canonical(result)!=_canonical(previous):
            raise ValueError('adaptive resume prefix differs from verified checkpoint')
        if count>completed_attempts:_save_document(result,directory/f'checkpoint-{count:03d}.json')
    limit=None if max_new_attempts is None else completed_attempts+max_new_attempts
    result=_run(request,obtain,schema_version=2,pause_after_attempts=limit,on_checkpoint=publish)
    if implementation!=_implementation_hashes():raise RuntimeError('implementation changed during adaptive Study execution')
    _save_document(result,directory/'adaptive-study-results.json')
    return result


def replay_adaptive_study(document):
    version=document.get('schema_version') if isinstance(document,dict) else None
    if type(version) is not int or version not in (1,2):raise ValueError('adaptive Study document requires schema_version 1 or 2')
    fields=('schema_version','document_type','request','points','attempts','accepted_point_indices','reached_target_indices','unreached_target_indices','history','status','stop_reason','scope')
    if version==2:fields+=('can_resume','pending_targets')
    keys(document,fields,fields,'saved adaptive Study')
    records=document['points']
    if type(records) is not list or not records:raise ValueError('adaptive Study requires saved points')
    def obtain(index,value,project):
        if index>=len(records) or not isinstance(records[index],dict) or _canonical(records[index].get('value'))!=_canonical(value):
            raise ValueError('adaptive point sequence differs from deterministic subdivision')
        return records[index].get('run')
    paused=version==2 and document['status']=='PAUSED'
    if paused and (type(document['attempts']) is not list or not document['attempts']):raise ValueError('paused adaptive Study requires completed comparison attempts')
    expected=_run(document['request'],obtain,schema_version=version,pause_after_attempts=len(document['attempts']) if paused else None)
    if _canonical(expected)!=_canonical(document):raise ValueError('adaptive Study replay differs from saved decisions or sources')
    return expected


def read_adaptive_study(path):return replay_adaptive_study(parse_json(Path(path).read_text(encoding='utf-8')))
