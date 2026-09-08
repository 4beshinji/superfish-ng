# SPDX-License-Identifier: Apache-2.0
"""Version 5: replayable RF confirmation branches and local refinement events."""
from copy import deepcopy
from dataclasses import replace
import json
import math
from pathlib import Path
import numpy as np
from .config import integer
from .curved_adaptive_refinement import (validate_request as validate_v4,next_plan as initial_plan,
    Plan,_history,_maximum,_apply,_quality,_quadrature,_surface,_VerifiedPrefix,RF)
from .curved_refinement_steps import CurvedRefinementStep as Step
from .curved_rf_goal_indicator import curved_rf_goal_indicator
from .curved_residual_indicator import curved_residual_indicator
from .curved_saved import geometry_arrays
from .surface_convergence import _interval_change
from .adaptive_surface_stopping import QUANTITIES as PEAKS
from .saved_mode_tracking import _canonical,_snapshot,build_saved_mode_tracking
from .mesh_input import mesh_digest
from .saved import read_solution
from .project import parse_json
from .solver import solve
from .io import save_run
from .jobs import _implementation_hashes


def validate_request(request):
    if not isinstance(request,dict) or type(request.get('schema_version')) is not int or request['schema_version']!=5:
        raise ValueError('RF adaptive refinement requires schema_version 5')
    original=deepcopy(request);original['schema_version']=4
    return validate_v4(original)


def _comparison(parent,current,request):
    changes={};peaks={}
    for key in RF:
        x,y=parent['quantities'][key],current['quantities'][key]
        valid=all(type(v) in (int,float) and math.isfinite(v) and v>0 for v in (x,y))
        change=abs(y/x-1) if valid else None
        changes[key]=dict(relative_change=change,limit=request['relative_tolerances'][key],
                          passed=change is not None and math.isfinite(change) and change<=request['relative_tolerances'][key])
    for key in PEAKS:
        change=_interval_change(parent['surface']['intervals'][key],current['surface']['intervals'][key])
        peaks[key]=dict(relative_change_upper_bound=change,limit=request['surface_relative_tolerances'][key],
                        passed=change is not None and change<=request['surface_relative_tolerances'][key])
    verified=all(v['relative_change'] is not None and math.isfinite(v['relative_change']) for v in changes.values()) and all(v['relative_change_upper_bound'] is not None for v in peaks.values())
    passed=verified and all(v['passed'] for v in [*changes.values(),*peaks.values()])
    return dict(verified=verified,passed=passed,changes=changes,surface_changes=peaks)


def next_plan(case,request,events,solutions):
    accepted=[i for i,row in enumerate(events) if row['accepted']]
    common=dict(accepted_event_indices=accepted,completed_solve_events=len(events),changes=[],surface_changes=[])
    def stop(status,**data):return dict(status=status,**common,**data),None
    if not events:
        v4=deepcopy(request);v4['schema_version']=4
        decision,plan=initial_plan(case,v4,[],None)
        return dict(decision,**common,parent_event_index=None),plan
    last=events[-1]
    if last['status']=='UNVERIFIED':return stop('UNVERIFIED',reason='individual mode identities are unresolved')
    if not last['quadrature_check']['passed']:return stop('QUADRATURE_UNVERIFIED',reason='higher-order integration comparison failed')
    comparison=last['confirmation_comparison']
    if comparison is not None:
        common.update(changes=[comparison['changes']],surface_changes=[comparison['surface_changes']])
        if not comparison['verified']:return stop('QUANTITY_UNVERIFIED',reason='five-quantity comparison is unresolved')
    if last['accepted'] and last['uniform_confirmations']>=2:return stop('TARGETS_MET')
    if len(events)>=request['max_levels']:return stop('LEVEL_LIMIT')
    indicator=None;marked=[]
    if last['refinement_kind']=='uniform_probe' and not last['accepted']:
        parent_index=last['parent_event_index'];kind='rf_local'
        parent=solutions[parent_index]
        indicator=curved_rf_goal_indicator(parent,solutions[-1],mode=events[parent_index]['mode_index'],bulk_fraction=request['bulk_fraction'])
        marked=indicator['marked_parent_cells']
        if not marked:return stop('ZERO_INDICATOR',reason='zero RF priority does not certify convergence')
        step=Step('marked',tuple(marked),request['minimum_corner_angle_deg'])
    else:
        parent_index=accepted[-1];parent=solutions[parent_index];kind='uniform_probe';step=Step('uniform')
    try:
        space=_apply(parent.space,step,_maximum(case,request));_quality(space,request)
    except ValueError as exc:
        if 'max_triangles' not in str(exc) and 'minimum_corner_angle_deg' not in str(exc):raise
        return stop('REFINEMENT_LIMIT',reason=str(exc),marked_cells=marked)
    from .nested_curved_tracking import MAX_FEATURE_ENTRIES
    if len(space.geometry.points_rz_m)*2*case.modes>MAX_FEATURE_ENTRIES:
        return stop('TRACKING_BUDGET',reason='nested_curved coefficient feature budget exceeded')
    current=replace(parent.case,curved_refinement_levels=0,curved_refinement_steps=_history(parent.case)+(step,))
    return dict(status='PAUSED',**common,parent_event_index=parent_index,next_refinement_kind=kind,
                next_triangles=len(space.geometry.cell_nodes),marked_cells=marked,rf_indicator=indicator),Plan(current,parent.source_mesh_data,space)


def assemble(request,runs,*,_cache=None):
    case=validate_request(request)
    if type(runs) is not list or any(type(p) is not str or not Path(p).is_absolute() for p in runs) or len(set(runs))!=len(runs):
        raise ValueError('level_runs requires distinct absolute native event directories')
    if len(runs)>request['max_levels']:raise ValueError('level_runs exceeds max_levels including probes')
    events,sources,solutions=([],[],[]) if _cache is None else _cache.load(request,runs)
    solutions=list(solutions or [])
    for index in range(len(events),len(runs)):
        run=runs[index];decision,plan=next_plan(case,request,events,solutions)
        if decision['status']!='PAUSED':raise ValueError('RF adaptive event follows a terminal decision')
        source=_snapshot(Path(run));current=read_solution(run)
        if current.case!=plan.case or mesh_digest(current.source_mesh_data)!=mesh_digest(plan.source_mesh):
            raise ValueError('saved RF adaptive Case or mesh differs from prescribed parent event')
        a,b=geometry_arrays(plan.space),geometry_arrays(current.space)
        if set(a)!=set(b) or any(not np.array_equal(a[k],b[k]) for k in a):raise ValueError('RF adaptive geometry differs from prescribed branch')
        parent_index=decision['parent_event_index'];kind=decision['next_refinement_kind']
        pair=None;ids=request['initial_ids'];status='INITIAL'
        if parent_index is not None:
            pair=build_saved_mode_tracking(dict(schema_version=1,previous_run=runs[parent_index],current_run=run,
                previous_ids=events[parent_index]['current_mode_ids'],controls=request['controls']))
            tracking=pair['tracking'];ids=tracking['current_mode_ids']
            status='PASS' if tracking['status']=='PASS' and tracking['individual_ids_complete'] else 'UNVERIFIED'
        mode=ids.index(request['mode_id']) if status!='UNVERIFIED' else None
        q=None if mode is None else parse_json((Path(run)/'results.json').read_text())['modes'][mode]
        indicator=None if mode is None else curved_residual_indicator(current.case,current,mode=mode,quadrature_order=current.case.quadrature_order)
        row=dict(index=index,status=status,parent_event_index=parent_index,refinement_kind=kind,
            marked_cells=decision['marked_cells'],triangles=len(current.space.geometry.cell_nodes),dofs=len(current.u),
            quality=_quality(current.space,request),current_mode_ids=ids,mode_index=mode,tracking=pair,
            indicator=indicator,quantities=q,quadrature_check=None if mode is None else _quadrature(current,request,mode,indicator),
            surface=None if mode is None else _surface(current,mode,q),accepted=False,uniform_confirmations=0,
            confirmation_comparison=None,selection=decision.get('rf_indicator'))
        if mode is not None and row['quadrature_check']['passed']:
            if kind=='uniform_probe':
                comparison=_comparison(events[parent_index],row,request);row['confirmation_comparison']=comparison
                if comparison['passed']:
                    row['accepted']=True;row['uniform_confirmations']=events[parent_index]['uniform_confirmations']+1
            else:row['accepted']=True
        events.append(row);sources.append(source);solutions.append(current)
    if sources!=[_snapshot(Path(run)) for run in runs]:raise ValueError('RF adaptive sources changed during verification')
    decision,plan=next_plan(case,request,events,solutions);status=decision['status']
    result=dict(schema_version=1,document_type='adaptive_refinement_checkpoint',request=deepcopy(request),level_runs=list(runs),
        sources=sources,levels=events,decision=decision,status=status,can_resume=status=='PAUSED',physical_error_bound=None,
        surface_status='TARGETS_MET' if status=='TARGETS_MET' else 'UNVERIFIED' if status in ('UNVERIFIED','QUANTITY_UNVERIFIED','QUADRATURE_UNVERIFIED') else 'NOT_CONFIRMED',
        scope='version 5: native solve events including uniform probes; accepted branch indices; RF goal marking from original parent; two consecutive accepted uniform five-quantity comparisons; no physical error bound or geometry-approximation acceptance')
    if _cache is not None:
        if sources!=[_snapshot(Path(run)) for run in runs]:raise ValueError('RF adaptive sources changed during verification')
        _cache.store(request,runs,events,sources,solutions)
    return result,plan


def execute(request,directory,*,max_new_levels=None,checkpoint=None):
    from .adaptive_refinement import _replay
    request=deepcopy(request);validate_request(request)
    if max_new_levels is not None:integer(max_new_levels,'max_new_levels')
    cache=_VerifiedPrefix()
    previous,plan=assemble(request,[],_cache=cache)
    if checkpoint is not None:
        previous,plan=_replay(checkpoint,lambda saved_request,saved_runs:assemble(saved_request,saved_runs,_cache=cache))
        if _canonical(previous['request'])!=_canonical(request):raise ValueError('resume request differs from checkpoint')
        if not previous['can_resume']:raise ValueError('only PAUSED curved adaptive refinement can resume')
    implementation=_implementation_hashes();runs=list(previous['level_runs'])
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=False);count=0
    while previous['can_resume'] and (max_new_levels is None or count<max_new_levels):
        index=len(runs);run=directory/f'event-{index+1:03d}'
        try:
            solution=solve(plan.case,mesh_data=plan.source_mesh);save_run(plan.case,solution,run)
            result,next_=assemble(request,runs+[str(run)],_cache=cache)
            if result['sources'][:len(runs)]!=previous['sources']:raise ValueError('prior curved adaptive sources changed during execution')
            if implementation!=_implementation_hashes():raise RuntimeError('implementation changed during curved adaptive refinement')
        except Exception as exc:
            failure=dict(status='FAILED',level_index=index,run=str(run),error_type=type(exc).__name__,error=str(exc),preceding_level_runs=runs)
            with (directory/f'failure-{index+1:03d}.json').open('x') as stream:json.dump(failure,stream,indent=2,allow_nan=False)
            raise
        with (directory/f'checkpoint-{index+1:03d}.json').open('x') as stream:stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
        previous=result;plan=next_;runs.append(str(run));count+=1
    return previous
