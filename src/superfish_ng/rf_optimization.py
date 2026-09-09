# SPDX-License-Identifier: Apache-2.0
"""Two-variable RF coordinate search with native FEM evidence and replay."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from .config import keys, integer
from .project import Project, parse_json
from .rf_design import validate_design_criteria, assess_rf_design, _number
from .rf_optimization_search import decision
from .curved_project_transform import transform_curved_project, relative_affine_map
from .curved_tuning import IDENTITY
from .saved_mode_tracking import build_saved_mode_tracking, validate_tracking_controls, _canonical
from .mode_tracking_history import start_mode_history, extend_mode_history
from .tracked_study import _point_sources
from .jobs import execute_project, _implementation_hashes


def validate_optimization_request(request):
    fields=('schema_version','project','variables','criteria','constraint_scales',
            'objective_improvement','max_trials','initial_ids','mode_id','controls','rf_coordinates')
    keys(request,fields,fields,'RF optimization request')
    if type(request['schema_version']) is not int or request['schema_version']!=1:
        raise ValueError('RF optimization requires schema_version 1')
    validate_design_criteria(request['criteria'])
    scales=request['constraint_scales'];names=[c['quantity'] for c in request['criteria']['constraints']]
    keys(scales,names,names,'constraint_scales')
    if any(not _number(x) or x<=0 for x in scales.values()):
        raise ValueError('constraint_scales must be finite positive values in each constraint unit')
    gain=request['objective_improvement']
    if not _number(gain) or gain<0:raise ValueError('objective_improvement must be finite and nonnegative in the objective unit')
    integer(request['max_trials'],'max_trials',2)
    variables=request['variables'];seen=set()
    if type(variables) is not list or len(variables)!=2:
        raise ValueError('variables must define radial_scale and axial_scale')
    for variable in variables:
        names=('name','lower','upper','initial','step','tolerance')
        keys(variable,names,names,'optimization variable');name=variable['name']
        if type(name) is not str or name not in ('radial_scale','axial_scale') or name in seen:
            raise ValueError('variables require distinct radial_scale and axial_scale names')
        seen.add(name)
        if any(not _number(variable[n]) or variable[n]<=0 for n in names[1:]):
            raise ValueError('optimization bounds, initial, step and tolerance must be finite and positive')
        if not variable['lower']<variable['upper'] or not variable['lower']<=variable['initial']<=variable['upper']:
            raise ValueError('optimization initial must lie inside increasing bounds')
        if variable['tolerance']>variable['step']:raise ValueError('variable tolerance must not exceed step')
    project=Project.from_dict(request['project']);case=project.case
    if (case.curved_contour is None or case.geometry_order!=2 or case.curved_refinement_steps or
            project.sections is not None or project.reflect_full):
        raise ValueError('RF optimization requires an unassembled full native curved P2 project without marked refinement history')
    if case.z_min!='pec' or case.z_max!='pec':raise ValueError('RF optimization requires full closed PEC geometry')
    if request['rf_coordinates'] not in ('fixed','axial'):raise ValueError('rf_coordinates must be fixed or axial')
    controls=request['controls']
    if not isinstance(controls,dict) or controls.get('mapping')!='affine_remesh' or 'affine_map' in controls:
        raise ValueError('optimization requires affine_remesh controls without affine_map; trial maps are derived')
    validate_tracking_controls(dict(controls,affine_map=IDENTITY))
    ids=request['initial_ids']
    if (type(ids) is not list or len(ids)!=case.modes or any(type(x) is not str or not x.strip() for x in ids)
            or len(set(ids))!=len(ids) or type(request['mode_id']) is not str or request['mode_id'] not in ids):
        raise ValueError('initial_ids must name each initial frequency rank distinctly and contain mode_id')
    _canonical(request)
    return project


def _map(request, values):
    return dict(axial_shear=0.,**{v['name']:x for v,x in zip(request['variables'],values)})


def _projects(request, trial):
    project=transform_curved_project(Project.from_dict(request['project']),_map(request,trial['values']),
                                     rf_coordinates=request['rf_coordinates'])
    first=project.case.curved_refinement_levels+(1 if trial['phase']=='final' else 0)
    return [replace(project,case=replace(project.case,curved_refinement_levels=first+i)) for i in range(3)]


def _resolved(pair):
    return pair['status']=='PASS' and pair['tracking']['individual_ids_complete']


def _assemble(request, directories):
    validate_optimization_request(request)
    if (type(directories) is not list or any(type(x) is not str for x in directories)
            or len(set(directories))!=len(directories) or len(directories)>request['max_trials']):
        raise ValueError('optimization requires distinct trial directories within max_trials')
    trials=[];sources=[];all_projects=[]
    for index,directory in enumerate(directories):
        state=decision(request,trials)
        if state['status']!='PAUSED':raise ValueError('optimization contains a trial after termination')
        trial=state['next_trial'];projects=_projects(request,trial);all_projects.append(projects)
        runs=[Path(directory)/f'level-{i}' for i in range(3)]
        sources.append([_point_sources(run,project) for run,project in zip(runs,projects)])
        ids=list(request['initial_ids']);tracking=None;assessment=None;history=None
        parent=trial['parent_index'];resolved=True
        if parent is not None:
            controls=dict(request['controls'],affine_map=relative_affine_map(
                _map(request,trials[parent]['values']),_map(request,trial['values'])))
            tracking=build_saved_mode_tracking(dict(schema_version=1,
                previous_run=str(Path(directories[parent])/'level-0/solution'),current_run=str(runs[0]/'solution'),
                previous_ids=trials[parent]['current_mode_ids'],controls=controls))
            resolved=_resolved(tracking);ids=tracking['tracking']['current_mode_ids']
        if resolved:
            controls=dict(request['controls'],mapping='curved_same_domain')
            pair=build_saved_mode_tracking(dict(schema_version=1,previous_run=str(runs[0]/'solution'),
                current_run=str(runs[1]/'solution'),previous_ids=ids,controls=controls))
            if _resolved(pair):
                history=extend_mode_history(start_mode_history(pair),dict(current_run=str(runs[2]/'solution'),controls=controls))
                if all(_resolved(step) for step in history['steps']):
                    assessment=assess_rf_design(history,request['mode_id'],request['criteria'])
            else:history=start_mode_history(pair)
        trials.append(dict(index=index,**trial,current_mode_ids=ids,tracking=tracking,
                           refinement_history=history,assessment=assessment))
    after=[[_point_sources(Path(directory)/f'level-{i}',project) for i,project in enumerate(projects)]
           for directory,projects in zip(directories,all_projects)]
    if sources!=after:raise ValueError('optimization sources changed during verification')
    state=decision(request,trials)
    return dict(schema_version=1,document_type='rf_optimization_checkpoint',request=deepcopy(request),
        trial_directories=list(directories),trial_sources_sha256=sources,trials=trials,decision=state,
        status=state['status'],can_resume=state['status']=='PAUSED',completed_fem_solves=3*len(trials),
        max_fem_solves=3*request['max_trials'],
        scope='bounded two-variable coordinate polling with empirical RF constraints, individual sampled identity and a separately solved finer final assessment; budget includes initial and final three-level trials; no global/local optimality or physical-error certificate')


def replay_rf_optimization(document):
    fields=('schema_version','document_type','request','trial_directories','trial_sources_sha256','trials',
            'decision','status','can_resume','completed_fem_solves','max_fem_solves','scope')
    keys(document,fields,fields,'RF optimization checkpoint')
    expected=_assemble(document['request'],document['trial_directories'])
    if _canonical(expected)!=_canonical(document):raise ValueError('RF optimization replay differs from saved data or sources')
    return expected


def read_rf_optimization(path):
    return replay_rf_optimization(parse_json(Path(path).read_text(encoding='utf-8')))


def execute_rf_optimization(request, directory, *, checkpoint=None, max_new_trials=None):
    request=deepcopy(request);validate_optimization_request(request)
    if max_new_trials is not None:integer(max_new_trials,'max_new_trials')
    previous=_assemble(request,[]) if checkpoint is None else replay_rf_optimization(checkpoint)
    if _canonical(previous['request'])!=_canonical(request):raise ValueError('optimization resume request differs from checkpoint')
    if checkpoint is not None and not previous['can_resume']:raise ValueError('only a PAUSED optimization may resume')
    implementation=_implementation_hashes();directories=list(previous['trial_directories'])
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=False);count=0
    while previous['can_resume'] and (max_new_trials is None or count<max_new_trials):
        index=len(directories);trial=previous['decision']['next_trial'];run=directory/f'trial-{index+1:03d}';calls=0
        try:
            projects=_projects(request,trial)
            for i,project in enumerate(projects):
                calls+=1;execute_project(project,run/f'level-{i}')
            result=_assemble(request,directories+[str(run)])
            if result['trial_sources_sha256'][:-1]!=previous['trial_sources_sha256']:
                raise ValueError('prior optimization checkpoint sources changed during execution')
            if implementation!=_implementation_hashes():raise RuntimeError('implementation changed during optimization execution')
        except Exception as exc:
            failure=dict(status='FAILED',request=request,attempt=trial,trial_directory=str(run),
                preceding_trial_directories=directories,fem_calls_attempted=3*len(directories)+calls,
                error_type=type(exc).__name__,error=str(exc),
                scope='terminal failed attempt has no objective value; earlier checkpoints remain distinct fork points')
            with (directory/f'failure-{index+1:03d}.json').open('x',encoding='utf-8') as stream:
                json.dump(failure,stream,indent=2,allow_nan=False)
            raise
        with (directory/f'checkpoint-{index+1:03d}.json').open('x',encoding='utf-8') as stream:
            stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
        previous=result;directories.append(str(run));count+=1
    return previous
