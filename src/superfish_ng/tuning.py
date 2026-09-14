# SPDX-License-Identifier: Apache-2.0
"""Bracketed scalar FEM tuning with replayable identities and a refinement gate."""
from copy import deepcopy
import json
import math
from pathlib import Path
import re
from .config import keys,positive,integer
from .project import Project,parse_json
from .studies import Study
from .jobs import execute_project,_implementation_hashes
from .te_tuning import trial_sources as _point_sources,read_trial_solution
from .saved_mode_tracking import build_saved_mode_tracking,validate_tracking_controls,_canonical
from .mode_tracking import tracked_frequency_hz
from .tuning_identity_recovery import base_request,recover_trial


def _request(request):
    if isinstance(request,dict) and type(request.get('schema_version')) is int and request['schema_version']==6:
        from .tuning_identity_recovery import validate_request
        return validate_request(request)
    fields=('schema_version','project','parameter','bounds','target_hz','frequency_tolerance_hz',
        'parameter_tolerance','max_trials','initial_ids','mode_id','controls','refinement_scale','mesh_frequency_tolerance_hz')
    if isinstance(request,dict) and request.get('schema_version') in (2,3):fields+=('bindings','parameter_unit')
    if isinstance(request,dict) and request.get('schema_version')==4:fields+=('affine_coefficients','parameter_unit','rf_coordinates')
    if isinstance(request,dict) and request.get('schema_version')==5:fields+=('geometry_coefficients','parameter_unit','rf_coordinates','minimum_corner_angle_deg')
    if isinstance(request,dict) and request.get('schema_version') in (7,8):
        fields+=('geometry_kind','bindings','parameter_unit')
        if request.get('geometry_kind')=='curved_harmonic':fields+=('rf_coordinates','minimum_corner_angle_deg')
    if isinstance(request,dict) and request.get('schema_version')==8:fields+=('mesh_schedule',)
    keys(request,fields,fields,'tune request');_canonical(request)
    if type(request['schema_version']) is not int or request['schema_version'] not in (1,2,3,4,5,7,8):raise ValueError('tune requires geometry schema_version 1, 2, 3, 4, 5, 7 or 8')
    for name in ('target_hz','frequency_tolerance_hz','parameter_tolerance','mesh_frequency_tolerance_hz'):positive(request[name],name)
    integer(request['max_trials'],'max_trials',2);integer(request['refinement_scale'],'refinement_scale',2)
    bounds=request['bounds']
    if (type(bounds) is not list or len(bounds)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) for v in bounds)
            or not bounds[0]<bounds[1]):raise ValueError('bounds must be two increasing finite parameter values')
    parameter=request['parameter']
    if request['schema_version']==1:
        if type(parameter) is not str or not re.fullmatch(r'/case/geometry/points_zr_m/[0-9]+/[01]',parameter):
            raise ValueError('tune parameter must be a numeric /case/geometry/points_zr_m/<vertex>/<coordinate> path')
    elif type(parameter) is not str or not parameter.strip() or request['parameter_unit'] not in ('m','1'):
        raise ValueError('coupled tune requires a nonempty parameter name and parameter_unit m or 1')
    project=Project.from_dict(request['project']);case=project.case
    from .te import is_te
    te=is_te(case)
    if te:
        from .te_tuning import validate_te_request
        validate_te_request(request,project)
    curved=request['schema_version'] in (4,5,8) or (request['schema_version']==7 and request['geometry_kind']=='curved_harmonic')
    if request['schema_version']==4:
        from .curved_tuning import validate_request
        validate_request(request,project)
    elif request['schema_version']==5:
        from .curved_harmonic_tuning import validate_request
        validate_request(request,project)
    elif request['schema_version']==7:
        from .expression_tuning import validate_request
        validate_request(request,project)
    elif request['schema_version']==8:
        from .partition_tuning import validate_request
        validate_request(request,project)
    if not curved and project.mesh_data is not None:
        raise ValueError('tuning an explicit project mesh requires a declared per-trial mesh transformation')
    if not curved and (project.sections is not None or (project.reflect_full and not te) or case.geometry_type!='profile' or (not te and (case.z_min!='pec' or case.z_max!='pec'))):
        raise ValueError('tune requires an unassembled continuous positive-radius profile with closed PEC ends')
    ids=request['initial_ids']
    if type(ids) is not list or len(ids)!=case.modes or any(type(x) is not str or not x.strip() for x in ids) or len(set(ids))!=len(ids):
        raise ValueError('initial_ids requires one distinct nonempty string per initial frequency rank')
    if type(request['mode_id']) is not str or request['mode_id'] not in ids:raise ValueError('mode_id must occur in initial_ids')
    if not curved:validate_tracking_controls(request['controls'])
    if not curved and request['controls']['mapping'] not in ('normalized_cylinder','normalized_profile'):
        raise ValueError('tune requires normalized_cylinder or normalized_profile; other geometry mappings need explicit per-trial support')
    endpoint_geometries=[]
    for value in bounds:
        p=_project(request,value,'search')
        if request['controls']['mapping']=='normalized_cylinder' and any(r!=p.case.profile[0][1] for _,r in p.case.profile):
            raise ValueError('normalized_cylinder tune bounds must retain constant radius')
        _project(request,value,'refinement')
        endpoint_geometries.append(p.case.curved_contour if curved else p.case.profile)
    if request['schema_version'] in (2,3,4,5,7,8) and endpoint_geometries[0]==endpoint_geometries[1]:
        raise ValueError('bindings do not change representable geometry across bounds')
    return project


def _project(request,value,phase):
    project=_geometry_project(request,value,phase)
    from .te import is_te
    if is_te(project.case):
        from .te_tuning import validate_te_request
        validate_te_request(base_request(request),project)
    return project


def _geometry_project(request,value,phase):
    request=base_request(request)
    project=Project.from_dict(request['project'])
    if request['schema_version']==4:
        from .curved_tuning import trial_project
        return trial_project(request,project,value,phase)
    if request['schema_version']==5:
        from .curved_harmonic_tuning import trial_project
        return trial_project(request,project,value,phase)
    if request['schema_version']==7:
        from .expression_tuning import trial_project
        return trial_project(request,project,value,phase)
    if request['schema_version']==8:
        from .partition_tuning import trial_project
        return trial_project(request,project,value,phase)
    if request['schema_version']==1:
        project=Study(project,'sweep',request['parameter'],[value,value]).projects()[0]
    else:
        raw=project.to_dict();points=raw['case']['geometry']['points_zr_m']
        bindings=request['bindings'];seen=set();active=False
        if type(bindings) is not list or not bindings:raise ValueError('bindings must be a nonempty list')
        for binding in bindings:
            polynomial=request['schema_version']==3
            names=('path','coefficients') if polynomial else ('path','multiplier','offset_m')
            keys(binding,names,names,'tune binding')
            path=binding['path']
            match=re.fullmatch(r'/case/geometry/points_zr_m/(0|[1-9][0-9]*)/([01])',path) if type(path) is str else None
            if match is None:raise ValueError('binding path must name a canonical profile vertex coordinate')
            index,coordinate=map(int,match.groups());target=(index,coordinate)
            if target in seen:raise ValueError('duplicate binding target coordinate')
            if index>=len(points):raise ValueError('binding vertex does not exist in the project')
            seen.add(target)
            coefficients=binding['coefficients'] if polynomial else [binding['offset_m'],binding['multiplier']]
            if type(coefficients) is not list or not coefficients:raise ValueError('binding coefficients must be a nonempty list in ascending power order')
            for coefficient in coefficients:
                try:finite=type(coefficient) in (int,float) and math.isfinite(coefficient)
                except OverflowError:finite=False
                if not finite:raise ValueError('binding coefficients, multiplier and offset must be finite numbers')
            active=active or any(c!=0 for c in coefficients[1:])
            if polynomial:
                mapped=coefficients[-1]
                for coefficient in reversed(coefficients[:-1]):mapped=mapped*value+coefficient
            else:mapped=binding['multiplier']*value+binding['offset_m']
            if not math.isfinite(mapped):raise ValueError('binding produces a nonfinite coordinate')
            points[index][coordinate]=mapped
        if not active:raise ValueError('at least one binding must have a nonzero nonconstant coefficient or multiplier')
        # Validate the combined shape once, never an arbitrary intermediate order.
        project=Project.from_dict(raw)
    if phase=='refinement':project=Study(project,'mesh_convergence','mesh_scale',[1,request['refinement_scale']]).projects()[1]
    return project


def _decision(request,trials):
    request=base_request(request)
    def stop(status,**data):return dict(status=status,next_trial=None,**data)
    def next_trial(value,phase='search',parent=None):
        return dict(status='PAUSED',next_trial=dict(value=value,phase=phase,parent_index=parent))
    if not trials:return next_trial(request['bounds'][0])
    if trials[-1]['status']=='UNVERIFIED':
        reason=('explicit individual identity recovery is unverified' if trials[-1].get('identity_recovery')
                else 'sampled correspondence does not resolve all individual identities')
        return stop('UNVERIFIED',reason=reason)
    if len(trials)==1:return next_trial(request['bounds'][1],parent=0)
    last=trials[-1]
    if last['phase']=='refinement':
        difference=abs(last['frequency_hz']-trials[last['parent_index']]['frequency_hz'])
        target=abs(last['target_error_hz'])<=request['frequency_tolerance_hz']
        mesh=difference<=request['mesh_frequency_tolerance_hz']
        return stop('TUNED' if target and mesh else 'REFINEMENT_FAILED',value=last['value'],
            refined_target_met=target,mesh_difference_met=mesh,mesh_frequency_difference_hz=difference,
            reason='two-mesh frequency difference is a diagnostic, not a discretization-error bound')
    best=min(range(len(trials)),key=lambda i:abs(trials[i]['target_error_hz']))
    if abs(trials[best]['target_error_hz'])<=request['frequency_tolerance_hz']:
        return next_trial(trials[best]['value'],'refinement',best)
    lower,upper=0,1
    if math.copysign(1.,trials[0]['target_error_hz'])==math.copysign(1.,trials[1]['target_error_hz']):
        return stop('UNBRACKETED',reason='endpoint frequencies do not bracket the target on the sampled identified mode')
    for i in range(2,len(trials)):
        if math.copysign(1.,trials[i]['target_error_hz'])==math.copysign(1.,trials[lower]['target_error_hz']):lower=i
        else:upper=i
    bracket=[trials[lower]['value'],trials[upper]['value']]
    if len(trials)>=request['max_trials']:return stop('ITERATION_LIMIT',bracket=bracket)
    middle=bracket[0]/2+bracket[1]/2
    if bracket[1]-bracket[0]<=request['parameter_tolerance'] or not bracket[0]<middle<bracket[1]:
        return stop('PARAMETER_LIMIT',bracket=bracket,reason='parameter interval exhausted without frequency tolerance acceptance')
    return next_trial(middle,parent=len(trials)-1)


def pair_controls(request,previous_value,current_value,previous_project,current_project):
    """Derive a comparison from its actual two trials, including refinement."""
    request=base_request(request)
    if request['schema_version']==4:
        from .curved_tuning import pair_controls as affine_controls
        return affine_controls(request,previous_value,current_value)
    if request['schema_version']==5 or (request['schema_version']==7 and request['geometry_kind']=='curved_harmonic'):
        from .curved_harmonic_tuning import pair_controls as harmonic_controls
        return harmonic_controls(request,previous_project,current_project)
    if request['schema_version']==8:
        from .partition_tuning import pair_controls as partition_controls
        return partition_controls(request,previous_value,current_value,previous_project,current_project)
    return deepcopy(request['controls'])


def _assemble(request,runs):
    initial_project=_request(request)
    original=request;request=base_request(original);recovery_enabled=original['schema_version']==6
    if type(runs) is not list or any(type(p) is not str for p in runs) or len(set(runs))!=len(runs):
        raise ValueError('tune trial_runs must be distinct native Job directory strings')
    if len(runs)>request['max_trials']+1:raise ValueError('tune trial count exceeds declared search and refinement budget')
    trials=[];sources=[];projects=[]
    for i,run in enumerate(runs):
        decision=_decision(request,trials)
        if decision['status']!='PAUSED':raise ValueError('tune contains trials after a terminal decision')
        trial=decision['next_trial'];project=_project(request,trial['value'],trial['phase']);projects.append(project)
        directory=Path(run);sources.append(_point_sources(directory,project));pair=None;frequency=None;recovery=None
        if i==0:
            ids=list(request['initial_ids']);frequency=float(read_trial_solution(directory/'solution',project).frequencies_hz[ids.index(request['mode_id'])]);status='INITIAL'
        else:
            parent=trial['parent_index']
            controls=pair_controls(request,trials[parent]['value'],trial['value'],projects[parent],project)
            pair=build_saved_mode_tracking(dict(schema_version=1,previous_run=str(Path(runs[parent])/'solution'),
                current_run=str(directory/'solution'),previous_ids=trials[parent]['current_mode_ids'],controls=controls))
            report=pair['tracking'];ids=report['current_mode_ids'];status='PASS'
            if recovery_enabled and report['status']=='PASS' and not report['individual_ids_complete']:
                recovery=recover_trial(original,trials,projects,runs,trial,pair)
                ids=recovery['assessment']['current_mode_ids']
                if recovery['status']=='PASS':
                    frequency=tracked_frequency_hz(recovery['comparison']['tracking'],request['mode_id'])
                else:status='UNVERIFIED'
            elif report['status']!='PASS' or not report['individual_ids_complete']:status='UNVERIFIED'
            else:frequency=tracked_frequency_hz(report,request['mode_id'])
        trials.append(dict(index=i,**trial,status=status,current_mode_ids=ids,frequency_hz=frequency,
            target_error_hz=None if frequency is None else frequency-request['target_hz'],tracking=pair))
        if recovery_enabled:trials[-1]['identity_recovery']=recovery
    if sources!=[_point_sources(Path(run),project) for run,project in zip(runs,projects)]:
        raise ValueError('tune trial sources changed during verification')
    decision=_decision(request,trials)
    result=dict(schema_version=2 if recovery_enabled else 1,document_type='tune_checkpoint',request=deepcopy(original),trial_runs=list(runs),
        trial_sources_sha256=sources,trials=trials,decision=decision,status=decision['status'],can_resume=decision['status']=='PAUSED',
        scope=('bracketed scalar native FEM search with explicit earlier-trial identity recovery and a separate two-mesh frequency gate; no continuous-branch, discretization-error, RF-convergence or global-root certificate'
               if recovery_enabled else 'bracketed scalar native FEM search with sampled individual identity and a separate two-mesh frequency gate; no continuous-branch, discretization-error, RF-convergence or global-root certificate'))
    from .te_tuning import scope_note
    result['scope']+=scope_note(initial_project)
    return result


def replay_tune(document):
    fields=('schema_version','document_type','request','trial_runs','trial_sources_sha256','trials','decision','status','can_resume','scope')
    keys(document,fields,fields,'tune checkpoint')
    expected=_assemble(document['request'],document['trial_runs'])
    if _canonical(document)!=_canonical(expected):raise ValueError('tune checkpoint replay differs from saved data or sources')
    return expected


def read_tune(path):return replay_tune(parse_json(Path(path).read_text(encoding='utf-8')))


def execute_tune(request,directory,*,max_new_trials=None,checkpoint=None):
    """Run into new output, publishing a checkpoint after each verified native job.

    Solves are never replaced by cylinder formulas. A failure preserves the last
    checkpoint and an explicit failure record; resumption uses a new directory.
    """
    request=deepcopy(request);_request(request)
    if max_new_trials is not None:integer(max_new_trials,'max_new_trials')
    previous=_assemble(request,[])
    if checkpoint is not None:
        previous=replay_tune(checkpoint)
        if _canonical(previous['request'])!=_canonical(request):raise ValueError('resume request differs from checkpoint')
        if not previous['can_resume']:raise ValueError('only a verified PAUSED tune can resume')
    implementation=_implementation_hashes();runs=list(previous['trial_runs'])
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=False)
    count=0
    while previous['can_resume'] and (max_new_trials is None or count<max_new_trials):
        index=len(runs);trial=previous['decision']['next_trial'];run=directory/f'trial-{index+1:03d}'
        try:
            project=_project(request,trial['value'],trial['phase']);execute_project(project,run)
            result=_assemble(request,runs+[str(run)])
            if result['trial_sources_sha256'][:len(runs)]!=previous['trial_sources_sha256']:
                raise ValueError('prior checkpoint sources changed during tune execution')
            if implementation!=_implementation_hashes():raise RuntimeError('implementation changed during tune execution')
        except Exception as exc:
            failure=dict(request=request,attempt=trial,trial_run=str(run),error_type=type(exc).__name__,error=str(exc),
                preceding_trial_runs=runs,status='FAILED',scope='failed trial is not a frequency evaluation; prior checkpoints remain separate')
            with (directory/f'failure-{index+1:03d}.json').open('x',encoding='utf-8') as stream:json.dump(failure,stream,indent=2,allow_nan=False)
            raise
        with (directory/f'checkpoint-{index+1:03d}.json').open('x',encoding='utf-8') as stream:
            stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
        runs.append(str(run));previous=result;count+=1
    return previous
