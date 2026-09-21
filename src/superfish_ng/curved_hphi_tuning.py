# SPDX-License-Identifier: Apache-2.0
"""Bracketed original curved Hphi FEM tuning with explicit identity recovery."""
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from .config import keys,integer,positive
from .project import parse_json
from .hphi_project import HphiProject
from .curved_hphi import CurvedHphiCase,solve_curved_hphi
from .curved_hphi_field_overlap import verified_curved_hphi_solution
from .curved_hphi_shape_tuning import CurvedHphiShapeLaw
from .curved_hphi_tune_trials import build_curved_hphi_tune_trial,curved_hphi_trial_comparison,_budget
from .curved_hphi_tracking import track_curved_hphi_modes
from .curved_hphi_comparison import CurvedHphiComparisonBudgetExceeded
from .hphi_tracking import HphiTrackingControls
from .hphi_tuning import _json_types
from .hphi_tuning_identity_recovery import validate_recovery_policy
from .hphi_identity_recovery import _assess
from .mode_tracking import tracked_frequency_hz
from .fem import triangle_quadrature
from .tuning import _decision


def validate_curved_hphi_tune(request):
    """Reject unsupported inputs and final/comparison budgets before any solve."""
    _json_types(request)
    names=('format','schema_version','project','parameter','shape_law','bounds','target_hz',
        'frequency_tolerance_hz','parameter_tolerance','max_trials','initial_ids','mode_id','controls',
        'refinement_levels','max_triangles','max_dofs','mesh_frequency_tolerance_hz','max_sample_points','identity_recovery')
    keys(request,names,names,'curved Hphi tune')
    if (request['format']!='superfish_ng_curved_hphi_tune' or type(request['schema_version']) is not int
            or request['schema_version']!=1 or request['parameter']!='deformation'):
        raise ValueError('expected curved Hphi tune schema_version 1 with dimensionless deformation')
    project=HphiProject.from_dict(request['project'])
    if type(project.case) is not CurvedHphiCase:raise ValueError('curved tune requires original vacuum CurvedHphiCase Project')
    law=CurvedHphiShapeLaw.from_dict(request['shape_law'])
    bounds=request['bounds']
    if type(bounds) is not list or len(bounds)!=2:raise ValueError('curved tune bounds require two increasing positive values')
    for value in bounds:positive(value,'curved tune bound')
    if not bounds[0]<bounds[1]:raise ValueError('curved tune bounds must increase')
    for name in ('target_hz','frequency_tolerance_hz','parameter_tolerance','mesh_frequency_tolerance_hz'):
        positive(request[name],name)
    if request['parameter_tolerance']>bounds[1]-bounds[0]:raise ValueError('parameter_tolerance must not exceed bounds width')
    integer(request['max_trials'],'max_trials',2)
    for name in ('refinement_levels','max_triangles','max_dofs','max_sample_points'):integer(request[name],name)
    if request['refinement_levels']>8:raise ValueError('refinement_levels must be from 1 to 8')
    ids=request['initial_ids']
    if (type(ids) is not list or not ids or len(ids)>=project.case.modes
            or any(type(v) is not str or not v.strip() for v in ids) or len(set(ids))!=len(ids)):
        raise ValueError('initial_ids require a distinct positive prefix and a computed upper guard mode')
    if type(request['mode_id']) is not str or request['mode_id'] not in ids:raise ValueError('mode_id must occur in initial_ids')
    controls=[HphiTrackingControls.from_dict(request['controls'])]
    if request['identity_recovery'] is not None:controls.append(validate_recovery_policy(request))
    geometry=project.case.geometry;levels=request['refinement_levels']
    for control in controls:
        if project.case.modes>min(control.max_gram_modes,256):
            raise ValueError('curved tune spectrum exceeds max_gram_modes or scalar projection column budget 256')
        _budget(geometry,project.case.element_order,levels,request['max_triangles'],request['max_dofs'],control.max_candidate_tests)
        _budget(geometry,2,levels+1,control.max_overlay_triangles,control.max_dofs,control.max_candidate_tests)
        samples=len(list(triangle_quadrature(control.quadrature_order+10)))
        if samples*len(geometry.cell_nodes)*4**(levels+1)>request['max_sample_points']:
            raise CurvedHphiComparisonBudgetExceeded('curved tune final comparison exceeds max_sample_points')
    for value in bounds:law.apply(project,value)
    return project


def read_curved_hphi_tune_request(path):
    request=parse_json(Path(path).read_text(encoding='utf-8'));validate_curved_hphi_tune(request)
    return deepcopy(request)


def _trial(request,project,law,value,phase):
    return build_curved_hphi_tune_trial(project,law,value,phase=phase,refinement_levels=request['refinement_levels'],
        max_triangles=request['max_triangles'],max_dofs=request['max_dofs'],max_pair_tests=request['controls']['max_candidate_tests'])


def trial_curved_hphi_project(request,value,phase):
    project=validate_curved_hphi_tune(request);_json_types(value);positive(value,'curved tune trial value')
    if not request['bounds'][0]<=value<=request['bounds'][1]:raise ValueError('curved tune trial value is outside bounds')
    return _trial(request,project,CurvedHphiShapeLaw.from_dict(request['shape_law']),value,phase).project


def curved_hphi_tune_decision(request,trials):
    """Decision on internally verified trials; this does not certify input reports."""
    if trials and trials[-1]['status']=='MESH_LIMIT':
        return dict(status='MESH_LIMIT',next_trial=None,reason=trials[-1]['tracking']['verification_reasons'][0])
    decision=_decision(request,trials)
    if trials and decision['status']=='PAUSED' and decision['next_trial']['phase']=='search':
        decision['next_trial']['parent_index']=0
    return decision


def _compare(request,previous,current,previous_solution,current_solution,ids,controls):
    declaration=curved_hphi_trial_comparison(previous,current,previous_mode_ids=ids,
        previous_mode_count=len(ids),current_mode_count=len(request['initial_ids']),
        controls=controls,max_sample_points=request['max_sample_points'])
    return track_curved_hphi_modes(previous_solution,current_solution,declaration)


def _recover_trial(request,trials,records,solutions,current,solution,trial,inherited):
    """Fresh anchor comparison, only after verified unresolved E/H subspace continuity."""
    if inherited['status']!='PASS' or inherited['individual_ids_complete']:
        raise ValueError('curved recovery requires a verified unresolved individual ID set')
    policy=request['identity_recovery'];index=len(trials)
    resolved=[i for i,t in enumerate(trials) if t['status'] in ('INITIAL','PASS')
              and all(type(v) is str for v in t['current_mode_ids'])]
    anchor=policy['anchor_trial_index'] if policy['anchor_selection']=='fixed_trial' else resolved[-1] if resolved else None
    event=dict(format='superfish_ng_curved_hphi_tune_identity_recovery',recovery_version=1,
        anchor_trial_index=anchor,current_trial_index=index,parent_trial_index=trial['parent_index'],phase=trial['phase'],
        status='UNVERIFIED',comparison=None,assessment=None,stop_reason=None,
        scope='earlier original curved E/H reidentification inside inherited ID sets; anchor differs from search/refinement parent; no continuous-branch certificate')
    if anchor is None or not 0<=anchor<index:
        event['stop_reason']='recovery requires an earlier completed anchor trial';return event
    if anchor not in resolved:
        event['stop_reason']='selected earlier anchor lacks confirmed individual IDs';return event
    try:
        comparison=_compare(request,records[anchor],current,solutions[anchor],solution,trials[anchor]['current_mode_ids'],
            HphiTrackingControls.from_dict(policy['controls']))
        groups=[dict(indices=m['current_indices'],ids=m['previous_ids']) for m in inherited['matches']]
        assessment=_assess(comparison,groups,len(request['initial_ids']))
        event.update(comparison=comparison,assessment=assessment,status=assessment['status'],
            stop_reason=None if assessment['status']=='PASS' else '; '.join(assessment['reasons']))
    except ValueError as error:event['stop_reason']=str(error)
    return event


def _assess_trial(request,trials,records,solutions,current,solution):
    decision=curved_hphi_tune_decision(request,trials)
    if decision['status']!='PAUSED':raise ValueError('curved tune contains trials after a terminal decision')
    trial=decision['next_trial']
    if not hasattr(solution,'case') or solution.case.to_dict()!=current.project.case.to_dict():
        raise ValueError('curved tune solution differs from the declared trial Project')
    solution=verified_curved_hphi_solution(solution)
    index=len(trials);parent=trial['parent_index'];anchor=index==0
    previous=current if anchor else records[parent];previous_solution=solution if anchor else solutions[parent]
    ids=request['initial_ids'] if anchor else trials[parent]['current_mode_ids'];recovery=None
    try:
        tracking=_compare(request,previous,current,previous_solution,solution,ids,HphiTrackingControls.from_dict(request['controls']))
        evaluation=tracking;effective_ids=tracking['current_mode_ids']
        if request['identity_recovery'] is not None and tracking['status']=='PASS' and not tracking['individual_ids_complete']:
            recovery=_recover_trial(request,trials,records,solutions,current,solution,trial,tracking)
            if recovery['status']=='PASS':evaluation=recovery['comparison'];effective_ids=recovery['assessment']['current_mode_ids']
        passed=evaluation['status']=='PASS' and evaluation['individual_ids_complete']
        status=('INITIAL' if anchor else 'PASS') if passed else 'UNVERIFIED'
        frequency=tracked_frequency_hz(evaluation,request['mode_id']) if passed else None
    except ValueError as error:
        status='MESH_LIMIT' if isinstance(error,CurvedHphiComparisonBudgetExceeded) else 'UNVERIFIED';frequency=None
        tracking=dict(status=status,individual_ids_complete=False,current_mode_ids=[None]*len(ids),verification_reasons=[str(error)])
        effective_ids=tracking['current_mode_ids']
    return dict(index=index,**trial,status=status,current_mode_ids=effective_ids,frequency_hz=frequency,
        target_error_hz=None if frequency is None else frequency-request['target_hz'],tracking=tracking,
        identity_recovery=recovery,geometry=current.diagnostic),solution


@dataclass(frozen=True)
class CurvedHphiTuneRun:
    report: dict
    projects: tuple
    solutions: tuple
    trial_records: tuple


def _result(request,trials,records,solutions):
    decision=curved_hphi_tune_decision(request,trials)
    report=dict(format='superfish_ng_curved_hphi_tune_result',schema_version=1,request=deepcopy(request),
        trials=deepcopy(trials),decision=decision,status=decision['status'],can_resume=decision['status']=='PAUSED',
        parameter_unit='dimensionless',frequency_unit='Hz',
        scope='original curved FEM with individually confirmed E/H IDs and optional explicit earlier-anchor recovery; separate target/two-mesh frequency gates; no RF convergence or continuum error certificate')
    return CurvedHphiTuneRun(report,tuple(r.project for r in records),tuple(solutions),tuple(records))


def assess_curved_hphi_tune(request,solutions):
    """Reconstruct every trial and decision from original FEMs, never saved reports."""
    request=deepcopy(request);project=validate_curved_hphi_tune(request);law=CurvedHphiShapeLaw.from_dict(request['shape_law'])
    if type(solutions) not in (list,tuple) or len(solutions)>request['max_trials']+1:
        raise ValueError('curved tune requires solutions within search plus final trial budget')
    trials=[];records=[];accepted=[]
    for solution in solutions:
        decision=curved_hphi_tune_decision(request,trials)
        if decision['status']!='PAUSED':raise ValueError('curved tune contains trials after a terminal decision')
        next_trial=decision['next_trial'];current=_trial(request,project,law,next_trial['value'],next_trial['phase'])
        trial,restored=_assess_trial(request,trials,records,accepted,current,solution)
        trials.append(trial);records.append(current);accepted.append(restored)
    return _result(request,trials,records,accepted)


def run_curved_hphi_tune(request,*,max_new_trials=None):
    """Run independent FEM trials; stop only between complete in-memory trials.

    Owned checkpoints, process cancellation, persistent resume and GUI belong
    to the subsequent storage/worker layer.
    """
    request=deepcopy(request);project=validate_curved_hphi_tune(request);law=CurvedHphiShapeLaw.from_dict(request['shape_law'])
    if max_new_trials is not None:integer(max_new_trials,'max_new_trials')
    trials=[];records=[];solutions=[]
    while curved_hphi_tune_decision(request,trials)['status']=='PAUSED':
        if max_new_trials is not None and len(trials)>=max_new_trials:break
        next_trial=curved_hphi_tune_decision(request,trials)['next_trial']
        current=_trial(request,project,law,next_trial['value'],next_trial['phase'])
        solution=solve_curved_hphi(current.project.case)
        trial,restored=_assess_trial(request,trials,records,solutions,current,solution)
        trials.append(trial);records.append(current);solutions.append(restored)
    return _result(request,trials,records,solutions)
