# SPDX-License-Identifier: Apache-2.0
"""Native multivariable TM candidates with verified IDs and no RF adoption.

This D06 execution stage uses the existing bounded coordinate poll. Until D07
provides the RF convergence adapter, every assessment is None and the initial
center cannot be improved. A completed poll remains FINAL_UNVERIFIED.
"""
from copy import deepcopy
import json
from pathlib import Path
from .config import keys,integer
from .project import parse_json
from .rf_design import _number
from .rf_optimization_search import decision
from .straight_rf_candidates import validate_straight_candidate_request,straight_candidate_project
from .studies import Study
from .jobs import execute_project,_implementation_hashes
from .tracked_study import _point_sources
from .saved_mode_tracking import build_saved_mode_tracking,_canonical
from .mode_tracking_history import start_mode_history,extend_mode_history


def validate_request(request):
    fields=('schema_version','document_type','candidate_request','poll_variables','max_trials',
            'initial_ids','refinement_scale')
    keys(request,fields,fields,'straight RF candidate search request')
    if (type(request['schema_version']) is not int or request['schema_version']!=1
            or request['document_type']!='straight_rf_candidate_search_request'):
        raise ValueError('straight candidate search requires schema_version 1 and document_type straight_rf_candidate_search_request')
    source,_=validate_straight_candidate_request(request['candidate_request'])
    integer(request['max_trials'],'max_trials',2);integer(request['refinement_scale'],'refinement_scale',2)
    if request['max_trials']>request['candidate_request']['max_candidates']:
        raise ValueError('max_trials must fit the original candidate budget, including initial and final candidates')
    variables=request['poll_variables'];original=request['candidate_request']['variables']
    if type(variables) is not list or len(variables)!=len(original):
        raise ValueError('poll_variables must provide each original variable in declaration order')
    for variable,owner in zip(variables,original):
        fields=('name','initial','step','tolerance');keys(variable,fields,fields,'candidate poll variable')
        if variable['name']!=owner['name']:raise ValueError('poll variable order must match original candidate declarations')
        if (any(not _number(variable[n]) for n in ('initial','step','tolerance'))
                or not owner['lower']<=variable['initial']<=owner['upper']
                or not 0<variable['tolerance']<=variable['step']):
            raise ValueError('poll initial must be in bounds and finite; step/tolerance must be finite positive with tolerance <= step')
    ids=request['initial_ids']
    if (type(ids) is not list or len(ids)!=source.case.modes
            or any(type(x) is not str or not x.strip() for x in ids) or len(set(ids))!=len(ids)):
        raise ValueError('initial_ids must name every original frequency rank with a distinct nonempty string')
    _canonical(request)
    return source


def candidate_decision(request,trials):
    """Poll unevaluated original candidates; never accept a fabricated score."""
    validate_request(request)
    if any(t.get('assessment') is not None for t in trials):
        raise ValueError('D06 candidates have no RF assessment; objective adoption requires the D07 adapter')
    if trials and trials[-1]['status']=='UNVERIFIED':
        return dict(status='UNVERIFIED',next_trial=None,search_stop='INDIVIDUAL_ID_UNVERIFIED')
    poll=dict(max_trials=request['max_trials'],variables=[dict(v,lower=o['lower'],upper=o['upper'])
        for v,o in zip(request['poll_variables'],request['candidate_request']['variables'])])
    return decision(poll,trials)


def candidate_projects(request,trial):
    validate_request(request)
    if trial['phase'] not in ('search','final'):raise ValueError('candidate phase must be search or final')
    project,_=straight_candidate_project(request['candidate_request'],trial['values'])
    start=1 if trial['phase']=='final' else 0
    return Study(project,'mesh_convergence','mesh_scale',
        [request['refinement_scale']**i for i in range(start,start+3)]).projects()


def candidate_pair_controls(request,previous_trial,current_trial,previous_project,current_project):
    """Bind actual source metadata and both full domains before sampling."""
    meshes=[]
    for trial,project in ((previous_trial,previous_project),(current_trial,current_project)):
        if project.to_dict() not in [p.to_dict() for p in candidate_projects(request,trial)]:
            raise ValueError('candidate tracking Project differs from the original law or declared refinement')
        _,mesh=straight_candidate_project(request['candidate_request'],trial['values']);meshes.append(mesh)
    return dict(deepcopy(request['candidate_request']['controls']),comparison_meshes=meshes)


def _resolved(pair):
    return pair['status']=='PASS' and pair['tracking']['individual_ids_complete']


def _sources(run,project):
    path=Path(run)
    if any(p.is_symlink() for p in path.rglob('*')):raise ValueError('candidate native sources must not contain symbolic links')
    return _point_sources(path,project)


def _assemble(request,runs,*,allow_partial=False):
    validate_request(request)
    if (type(runs) is not list or len(runs)>request['max_trials']
            or any(type(group) is not list or not 1<=len(group)<=3
                   or any(type(p) is not str for p in group) for group in runs)):
        raise ValueError('candidate runs must be an ordered prefix within the three-level trial budget')
    flat=[p for group in runs for p in group]
    if len(set(flat))!=len(flat):raise ValueError('candidate native runs must be distinct')
    trials=[];sources=[];declared_projects=[]
    for index,group in enumerate(runs):
        state=candidate_decision(request,trials)
        if state['status']!='PAUSED':raise ValueError('candidate history continues after termination')
        trial=state['next_trial'];projects=candidate_projects(request,trial);declared_projects.append(projects)
        sources.append([_sources(run,project) for run,project in zip(group,projects)])
        ids=list(request['initial_ids']);tracking=None;history=None;resolved=True
        parent=trial['parent_index']
        if parent is not None:
            tracking=build_saved_mode_tracking(dict(schema_version=1,
                previous_run=str(Path(runs[parent][0])/'solution'),current_run=str(Path(group[0])/'solution'),
                previous_ids=trials[parent]['current_mode_ids'],controls=candidate_pair_controls(
                    request,trials[parent],trial,declared_projects[parent][0],projects[0])))
            resolved=_resolved(tracking);ids=tracking['tracking']['current_mode_ids']
        if resolved and len(group)>=2:
            controls=candidate_pair_controls(request,trial,trial,projects[0],projects[1])
            pair=build_saved_mode_tracking(dict(schema_version=1,previous_run=str(Path(group[0])/'solution'),
                current_run=str(Path(group[1])/'solution'),previous_ids=ids,controls=controls))
            history=start_mode_history(pair);resolved=_resolved(pair)
            if resolved and len(group)==3:
                history=extend_mode_history(history,dict(current_run=str(Path(group[2])/'solution'),
                    controls=candidate_pair_controls(request,trial,trial,projects[1],projects[2])))
                resolved=all(_resolved(step) for step in history['steps'])
        status='UNVERIFIED' if not resolved else 'IDENTITY_VERIFIED' if len(group)==3 else 'INCOMPLETE'
        if not resolved and len(group)!=(1 if history is None else 1+len(history['steps'])):
            raise ValueError('candidate history contains native solves after an unresolved correspondence')
        if status=='INCOMPLETE' and (not allow_partial or index!=len(runs)-1):
            raise ValueError('candidate trial is incomplete; only a verified three-level trial or identity stop can publish')
        trials.append(dict(index=index,**trial,status=status,current_mode_ids=ids,
            tracking=tracking,refinement_history=history,assessment=None))
    state=(dict(status='INCOMPLETE',next_trial=None,search_stop=None)
           if trials and trials[-1]['status']=='INCOMPLETE' else candidate_decision(request,trials))
    if sources!=[[_sources(run,project) for run,project in zip(group,projects)]
                 for group,projects in zip(runs,declared_projects)]:
        raise ValueError('candidate native sources changed during verification')
    return dict(schema_version=1,document_type='straight_rf_candidate_search_checkpoint',request=deepcopy(request),
        candidate_runs=deepcopy(runs),candidate_sources_sha256=sources,trials=trials,decision=state,
        status=state['status'],can_resume=state['status']=='PAUSED',completed_fem_solves=len(flat),
        max_fem_solves=3*request['max_trials'],rf_assessments=0,
        scope='bounded original straight TM candidate polls with actual native three-level individual tracking; no RF scores or accepted objective; final poll remains unverified until D07')


def replay_straight_rf_candidate_search(document):
    fields=('schema_version','document_type','request','candidate_runs','candidate_sources_sha256','trials',
            'decision','status','can_resume','completed_fem_solves','max_fem_solves','rf_assessments','scope')
    keys(document,fields,fields,'straight candidate search checkpoint')
    expected=_assemble(document['request'],document['candidate_runs'])
    if _canonical(expected)!=_canonical(document):raise ValueError('candidate search replay differs from original request, native sources or decision')
    return expected


def read_straight_rf_candidate_search(path):
    return replay_straight_rf_candidate_search(parse_json(Path(path).read_text(encoding='utf-8')))


def execute_straight_rf_candidate_search(request,directory,*,checkpoint=None,max_new_trials=None):
    request=deepcopy(request);validate_request(request)
    if max_new_trials is not None:integer(max_new_trials,'max_new_trials',0)
    previous=_assemble(request,[]) if checkpoint is None else replay_straight_rf_candidate_search(checkpoint)
    if _canonical(previous['request'])!=_canonical(request):raise ValueError('candidate search resume request differs from checkpoint')
    if checkpoint is not None and not previous['can_resume']:raise ValueError('only a PAUSED candidate search can resume')
    implementation=_implementation_hashes();runs=deepcopy(previous['candidate_runs']);root=Path(directory).resolve()
    root.mkdir(parents=True,exist_ok=False);count=0
    while previous['can_resume'] and (max_new_trials is None or count<max_new_trials):
        index=len(runs);trial=previous['decision']['next_trial'];group=[];calls=0
        try:
            projects=candidate_projects(request,trial)
            for level,project in enumerate(projects):
                run=root/f'trial-{index+1:03d}'/f'level-{level}';calls+=1
                execute_project(project,run);group.append(str(run))
                result=_assemble(request,runs+[group],allow_partial=True)
                if result['candidate_sources_sha256'][:-1]!=previous['candidate_sources_sha256']:
                    raise ValueError('prior candidate checkpoint sources changed during execution')
                if implementation!=_implementation_hashes():raise RuntimeError('implementation changed during candidate search')
                if result['status']=='UNVERIFIED':break
            if result['status']=='INCOMPLETE':raise ValueError('cannot publish an incomplete candidate trial')
        except Exception as exc:
            failure=dict(status='FAILED',request=request,attempt=trial,candidate_index=index,
                completed_candidate_runs=deepcopy(runs),attempted_candidate_runs=group,
                candidates_attempted=index+1,fem_calls_attempted=previous['completed_fem_solves']+calls,
                max_fem_solves=previous['max_fem_solves'],assessment=None,error_type=type(exc).__name__,error=str(exc),
                scope='terminal failure; no objective; prior native checkpoints remain independent fork points')
            with (root/f'failure-{index+1:03d}.json').open('x',encoding='utf-8') as stream:json.dump(failure,stream,indent=2,allow_nan=False)
            raise
        with (root/f'checkpoint-{index+1:03d}.json').open('x',encoding='utf-8') as stream:
            stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
        previous=result;runs.append(group);count+=1
    return previous
