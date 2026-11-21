# SPDX-License-Identifier: Apache-2.0
"""Real Cartesian P2 cutoff tuning with original E/H IDs and native replay.

Only the physics-independent bracket decision is shared with other tuning.
All geometry, fields, energy conventions, guards and native runs remain xy.
"""
from copy import deepcopy
from dataclasses import dataclass
import json
import math
from pathlib import Path
from .config import integer, keys, positive
from .project import parse_json
from .planar_project import PlanarProject
from .planar_curved import PlanarCurvedCase
from .planar_curved_shape import PlanarCurvedAffineShapeLaw
from .planar_curved_tuning_trials import generate_planar_curved_trial, planar_curved_trial_comparison
from .planar_curved_tracking import PlanarCurvedTrackingControls, PlanarCurvedTrackingRequest, track_planar_curved_modes
from .planar_curved_identity_recovery import PlanarCurvedIdentityRecoveryRequest, recover_planar_curved_modes
from .planar_curved_comparison import PlanarCurvedComparisonBudgetExceeded
from .planar_jobs import execute_planar_project, _job_hashes, verify_planar_job
from .jobs import _implementation_hashes
from .mode_tracking import tracked_frequency_hz
from .saved_mode_tracking import _canonical
from .tuning import _decision


def _json_types(value):
    if type(value) is dict:
        if any(type(k) is not str for k in value):raise ValueError('curved tune requires string JSON keys')
        for item in value.values():_json_types(item)
    elif type(value) is list:
        for item in value:_json_types(item)
    elif type(value) not in (str,int,float,bool,type(None)) or type(value) is float and not math.isfinite(value):
        raise ValueError('curved tune requires finite plain JSON values')


def _recovery_controls(request):
    policy=request['identity_recovery']
    if policy is None:return None
    names=['anchor_selection','controls']
    if type(policy) is dict and policy.get('anchor_selection')=='fixed_trial':names.append('anchor_trial_index')
    keys(policy,names,names,'curved planar tune identity recovery')
    if policy['anchor_selection'] not in ('fixed_trial','latest_resolved_trial'):
        raise ValueError('curved recovery anchor_selection must be fixed_trial or latest_resolved_trial')
    if policy['anchor_selection']=='fixed_trial':
        index=integer(policy['anchor_trial_index'],'anchor_trial_index',0)
        if index>=request['max_trials']:raise ValueError('curved recovery anchor must precede the last possible final trial')
    return PlanarCurvedTrackingControls.from_dict(policy['controls'])


def _budget(project,request,controls):
    """Complete final field/guard costs, before any trial FEM or partial output."""
    g=project.case.domain
    count=len(g.cell_nodes)
    edges={tuple(sorted((int(cell[a]),int(cell[b])))) for cell in g.cell_nodes for a,b in ((0,1),(1,2),(2,0))}
    dofs,edge_count=len(g.points_xy_m),len(edges)
    for _ in range(request['refinement_levels']):
        dofs+=2*edge_count+3*count;edge_count=2*edge_count+3*count;count*=4
    guard_dofs=dofs+2*edge_count+3*count
    children=4**request['refinement_levels']
    pairs=len(g.cell_nodes)*children*(children+1)//2
    order=controls.quadrature_order
    checks=[(project.case.modes,controls.max_gram_modes,'max_gram_modes'),
        (count,request['max_triangles'],'max_triangles'),(dofs,request['max_dofs'],'max_dofs'),
        (count,controls.max_comparison_triangles,'max_comparison_triangles'),
        (4*count,controls.max_refined_triangles_per_side,'max_refined_triangles_per_side'),
        (guard_dofs,controls.max_dofs_per_side,'max_dofs_per_side'),
        (max(pairs,10*count),controls.max_pair_tests_per_comparison,'max_pair_tests_per_comparison'),
        (2*count*(order**2+(order+4)**2),controls.max_field_sample_points,'max_field_sample_points'),
        (4*count*order**2,controls.max_enrichment_sample_points_per_side,'max_enrichment_sample_points_per_side')]
    for actual,limit,name in checks:
        if actual>limit:raise PlanarCurvedComparisonBudgetExceeded(f'complete curved tune final field/guard preflight exceeds {name}')


def validate_planar_curved_tune(request):
    _json_types(request)
    names=['format','schema_version','project','parameter','shape_law','bounds','target_hz',
        'frequency_tolerance_hz','parameter_tolerance','max_trials','initial_ids','mode_id','controls',
        'refinement_levels','max_triangles','max_dofs','mesh_frequency_tolerance_hz','identity_recovery']
    keys(request,names,names,'curved planar tune')
    if (request['format']!='superfish_ng_planar_curved_tune' or type(request['schema_version']) is not int
            or request['schema_version']!=1 or request['parameter']!='deformation'):
        raise ValueError('expected curved planar tune schema_version 1 and dimensionless deformation')
    project=PlanarProject.from_dict(request['project'])
    if type(project.case) is not PlanarCurvedCase:raise ValueError('curved planar tune requires an original complete quadratic Project')
    law=PlanarCurvedAffineShapeLaw.from_dict(request['shape_law'])
    bounds=request['bounds']
    if type(bounds) is not list or len(bounds)!=2 or list(law.bounds)!=bounds:
        raise ValueError('curved tune bounds must equal the complete shape law closed interval')
    for value in bounds:law.exact_transform(value)
    for name in ('target_hz','frequency_tolerance_hz','parameter_tolerance','mesh_frequency_tolerance_hz'):positive(request[name],name)
    if request['parameter_tolerance']>bounds[1]-bounds[0]:raise ValueError('parameter_tolerance must not exceed bounds width')
    integer(request['max_trials'],'max_trials',2)
    for name in ('refinement_levels','max_triangles','max_dofs'):integer(request[name],name)
    if request['refinement_levels']>8:raise ValueError('curved tune supports one through eight final refinement levels')
    ids=request['initial_ids']
    if (type(ids) is not list or not ids or len(ids)>=project.case.modes
            or any(type(v) is not str or not v.strip() for v in ids) or len(set(ids))!=len(ids)):
        raise ValueError('initial_ids require a distinct positive prefix and a computed upper guard mode')
    if type(request['mode_id']) is not str or request['mode_id'] not in ids:raise ValueError('mode_id must occur in initial_ids')
    controls=[PlanarCurvedTrackingControls.from_dict(request['controls'])]
    recovery=_recovery_controls(request)
    if recovery is not None:controls.append(recovery)
    for control in controls:_budget(project,request,control)
    for value in bounds:
        generate_planar_curved_trial(project,law,value,refinement_levels=request['refinement_levels'],
            max_triangles=request['max_triangles'],max_dofs=request['max_dofs'],
            max_pair_tests=min(c.max_pair_tests_per_comparison for c in controls))
    return project


def _trial(request,value,phase):
    if phase not in ('search','refinement'):raise ValueError('curved tune phase must be search or refinement')
    return generate_planar_curved_trial(PlanarProject.from_dict(request['project']),
        PlanarCurvedAffineShapeLaw.from_dict(request['shape_law']),value,
        refinement_levels=request['refinement_levels'] if phase=='refinement' else 0,
        max_triangles=request['max_triangles'],max_dofs=request['max_dofs'],
        max_pair_tests=request['controls']['max_pair_tests_per_comparison'])


def trial_planar_curved_project(request,value,phase):
    validate_planar_curved_tune(request)
    return _trial(request,value,phase).project


def _comparison(previous,current,ids,controls):
    return PlanarCurvedTrackingRequest(planar_curved_trial_comparison(previous,current),
        previous_mode_count=len(ids),current_mode_count=len(ids),previous_mode_ids=ids,
        previous_cells=previous.native_cells,current_cells=current.native_cells,controls=controls)


def _recover_trial(request,trials,records,solutions,current,solution,trial,inherited):
    policy=request['identity_recovery']
    resolved=[i for i,t in enumerate(trials) if t['status'] in ('INITIAL','PASS')
              and all(type(v) is str for v in t['current_mode_ids'])]
    anchor=policy['anchor_trial_index'] if policy['anchor_selection']=='fixed_trial' else resolved[-1] if resolved else None
    event=dict(format='superfish_ng_planar_curved_tune_identity_recovery',recovery_version=1,
        anchor_trial_index=anchor,parent_trial_index=trial['parent_index'],current_trial_index=len(trials),
        phase=trial['phase'],status='UNVERIFIED',recovery=None,stop_reason=None)
    if anchor is None or anchor not in resolved:
        event['stop_reason']='recovery requires an earlier completed trial with verified individual IDs';return event
    comparison=_comparison(records[anchor],current,trials[anchor]['current_mode_ids'],PlanarCurvedTrackingControls.from_dict(policy['controls']))
    recovery=recover_planar_curved_modes(solutions[anchor],solutions[trial['parent_index']],solution,inherited,
        PlanarCurvedIdentityRecoveryRequest(anchor,comparison),current_snapshot_index=len(trials))
    event.update(recovery=recovery,status=recovery['status'],stop_reason=recovery['stop_reason'])
    return event


def _assess(request,trials,records,solutions,current,solution):
    decision=_decision(request,trials)
    if decision['status']!='PAUSED':raise ValueError('curved tune contains trials after a terminal decision')
    trial=decision['next_trial'];index=len(trials);parent=trial['parent_index']
    if solution.case.to_dict()!=current.project.case.to_dict():raise ValueError('curved tune solution differs from regenerated trial Project')
    previous=current if index==0 else records[parent]
    source=solution if index==0 else solutions[parent]
    ids=request['initial_ids'] if index==0 else trials[parent]['current_mode_ids']
    declaration=_comparison(previous,current,ids,PlanarCurvedTrackingControls.from_dict(request['controls']))
    recovery=None
    try:
        tracking=track_planar_curved_modes(source,solution,declaration)
        ids=tracking['current_mode_ids'];passed=tracking['status']=='PASS' and tracking['individual_ids_complete']
        frequency=tracked_frequency_hz(tracking,request['mode_id']) if passed else None
        if index and request['identity_recovery'] is not None and tracking['status']=='PASS' and not passed:
            recovery=_recover_trial(request,trials,records,solutions,current,solution,trial,declaration)
            if recovery['status']=='PASS':
                ids=recovery['recovery']['assessment']['current_mode_ids']
                frequency=recovery['recovery']['recovered_frequencies_hz'][request['mode_id']];passed=True
        status=('INITIAL' if index==0 else 'PASS') if passed else 'UNVERIFIED'
    except ValueError as error:
        # All raw native fields remain saved. No uncertain frequency reaches
        # the bracket controller, including unresolved dynamic area/guard work.
        tracking=dict(status='UNVERIFIED',individual_ids_complete=False,current_mode_ids=[None]*len(request['initial_ids']),
            verification_reasons=[str(error)],budget_exhausted=isinstance(error,PlanarCurvedComparisonBudgetExceeded))
        ids=tracking['current_mode_ids'];frequency=None;status='UNVERIFIED'
    return dict(index=index,**trial,status=status,current_mode_ids=ids,frequency_hz=frequency,
        target_error_hz=None if frequency is None else frequency-request['target_hz'],tracking=tracking,
        identity_recovery=recovery,geometry=current.diagnostic)


def _native(directory,expected):
    directory=Path(directory)
    if not directory.is_absolute() or directory.is_symlink():raise ValueError('curved tune requires absolute non-symlink native job paths')
    before=_job_hashes(directory)
    state=parse_json((directory/'job.json').read_text());manifest=parse_json((directory/'manifest.json').read_text())
    solution=verify_planar_job(directory,state,manifest)
    if PlanarProject.load(directory/'project.json').to_dict()!=expected.to_dict():raise ValueError('curved tune native Project differs from regenerated trial')
    if before!=_job_hashes(directory):raise ValueError('curved tune native files changed during physical verification')
    return solution,before


@dataclass
class _TuneState:
    trials: list
    records: list
    solutions: list
    runs: list
    hashes: list


def _result(request,state):
    decision=_decision(request,state.trials)
    return dict(format='superfish_ng_planar_curved_tune_checkpoint',schema_version=1,request=deepcopy(request),
        trial_runs=list(state.runs),trial_sources_sha256=deepcopy(state.hashes),trials=deepcopy(state.trials),
        decision=decision,status=decision['status'],can_resume=decision['status']=='PAUSED',
        parameter_unit='dimensionless',frequency_unit='Hz',
        scope='real Cartesian cutoff P2 FEM with confirmed original E/H IDs and optional earlier-anchor recovery; separate target/two-mesh frequency gates; no RF convergence, surface or continuum error certificate')


def _reconstruct(request,runs):
    validate_planar_curved_tune(request)
    if (type(runs) is not list or any(type(p) is not str for p in runs)
            or len(set(runs))!=len(runs) or len(runs)>request['max_trials']+1):
        raise ValueError('curved tune trial paths must be distinct within search plus final budget')
    state=_TuneState([],[],[],[],[])
    for run in runs:
        decision=_decision(request,state.trials)
        if decision['status']!='PAUSED':raise ValueError('curved tune contains native trials after a terminal decision')
        recipe=decision['next_trial'];current=_trial(request,recipe['value'],recipe['phase'])
        solution,hashes=_native(run,current.project)
        trial=_assess(request,state.trials,state.records,state.solutions,current,solution)
        state.trials.append(trial);state.records.append(current);state.solutions.append(solution);state.runs.append(run);state.hashes.append(hashes)
    if state.hashes!=[_job_hashes(Path(p)) for p in runs]:raise ValueError('curved tune prefix changed during complete replay')
    return state


def _assemble(request,runs):return _result(request,_reconstruct(request,runs))


def _replay_state(document):
    names=['format','schema_version','request','trial_runs','trial_sources_sha256','trials','decision','status',
        'can_resume','parameter_unit','frequency_unit','scope']
    keys(document,names,names,'curved planar tune checkpoint')
    if (document['format']!='superfish_ng_planar_curved_tune_checkpoint' or type(document['schema_version']) is not int or document['schema_version']!=1):
        raise ValueError('expected curved planar tune checkpoint schema_version 1')
    state=_reconstruct(document['request'],document['trial_runs'])
    expected=_result(document['request'],state)
    if _canonical(document)!=_canonical(expected):raise ValueError('curved tune checkpoint differs from complete original native replay')
    return state


def replay_planar_curved_tune(document):
    state=_replay_state(document)
    return _result(document['request'],state)


def read_planar_curved_tune(path):
    return replay_planar_curved_tune(parse_json(Path(path).read_text(encoding='utf-8')))


def execute_planar_curved_tune(request,directory,*,max_new_trials=None,checkpoint=None):
    """Save each real native trial and verified checkpoint; resume writes anew.

    The accepted prefix is reconstructed once on entry. During execution its
    native hashes are checked at every append, while immutable in-memory fields
    serve only the current comparison. Full replay always reconstructs all
    original fields, charts and decisions rather than trusting these caches.
    Owned relocation, process cancellation and GUI belong to subsequent layers.
    """
    request=deepcopy(request);validate_planar_curved_tune(request);request=parse_json(_canonical(request))
    if max_new_trials is not None:integer(max_new_trials,'max_new_trials')
    if checkpoint is None:state=_TuneState([],[],[],[],[])
    else:
        state=_replay_state(checkpoint)
        if _canonical(checkpoint['request'])!=_canonical(request):raise ValueError('curved tune resume request differs from checkpoint')
        if not checkpoint['can_resume']:raise ValueError('only a verified PAUSED curved tune can resume')
    implementation=_implementation_hashes()
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=False)
    count=0
    while _decision(request,state.trials)['status']=='PAUSED' and (max_new_trials is None or count<max_new_trials):
        index=len(state.trials);recipe=_decision(request,state.trials)['next_trial'];run=directory/f'trial-{index+1:03d}'
        try:
            current=_trial(request,recipe['value'],recipe['phase'])
            execute_planar_project(current.project,run)
            solution,hashes=_native(str(run),current.project)
            trial=_assess(request,state.trials,state.records,state.solutions,current,solution)
            if state.hashes!=[_job_hashes(Path(p)) for p in state.runs]:raise ValueError('prior curved tune prefix changed during execution')
            if implementation!=_implementation_hashes():raise RuntimeError('implementation changed during curved tune execution')
            candidate=_TuneState(state.trials+[trial],state.records+[current],state.solutions+[solution],state.runs+[str(run)],state.hashes+[hashes])
            result=_result(request,candidate)
            with (directory/f'checkpoint-{index+1:03d}.json').open('x',encoding='utf-8') as stream:
                json.dump(result,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
        except Exception as error:
            failure=dict(request=request,attempt=recipe,trial_run=str(run),preceding_trial_runs=list(state.runs),
                status='FAILED',error_type=type(error).__name__,error=str(error),
                scope='failed trial is not a frequency evaluation; prior complete checkpoints remain separate')
            with (directory/f'failure-{index+1:03d}.json').open('x',encoding='utf-8') as stream:
                json.dump(failure,stream,ensure_ascii=False,indent=2,allow_nan=False);stream.write('\n')
            raise
        state=candidate;count+=1
    return _result(request,state)
