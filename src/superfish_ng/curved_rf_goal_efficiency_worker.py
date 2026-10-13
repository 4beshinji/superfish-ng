# SPDX-License-Identifier: Apache-2.0
"""Fresh fixed RF-goal executions, retaining the original public event branch.

The benchmark's full-field confirmation is separate from native RF stopping.
Process limits belong to the measured supervisor, not to these serial helpers.
"""
from copy import deepcopy
import importlib
import json
import math
from pathlib import Path
import time

import numpy as np
from scipy.optimize import linear_sum_assignment

from . import curved_adaptive_refinement as curved
from . import curved_rf_adaptive_refinement as native
from .adaptive_efficiency_accuracy import LIMITS, assess_efficiency_samples
from .adaptive_efficiency_domain import _native_files, verify_efficiency_saved_domain
from .adaptive_efficiency_fields import EfficiencyFieldSampler
from .adaptive_efficiency_observation import observe_selected_calls
from .adaptive_efficiency_reference import verify_reference_bytes
from .adaptive_efficiency_timing import PhaseRecorder
from .adaptive_efficiency_worker import observation_bindings as old_observation_bindings, _uniform_plan
from .adaptive_refinement import replay_adaptive_refinement
from .completion import digest
from .config import Case, integer
from .curved_fem import assemble_curved
from .curved_rf import quantities_curved
from .curved_rf_goal_efficiency_metrics import assess_rf_goal_history, assess_rf_goal_pair
from .curved_rf_goal_efficiency_plan import request_for_curved_rf_goal_efficiency_execution, _same
from .curved_rf_goal_efficiency_reference import load_curved_rf_goal_efficiency_reference
from .curved_rf_goal_efficiency_io import publish_rf_goal_json
from .curved_rf_goal_efficiency_observation import observe_adjoint_linear_solves, C_CALLS
from .geometry_surface_numerics import mapped_moments
from .jobs import _implementation_hashes
from .project import parse_json
from .saved import read_solution
from .saved_mode_tracking import build_saved_mode_tracking


def _write(path, value):
    publish_rf_goal_json(path,value)


def observation_bindings():
    selected=old_observation_bindings()
    mapping={
        'curved_rf_adaptive_refinement': [('solve','native_solve_and_normalization'),('save_run','native_save'),
            ('read_solution','native_reconstruction'),('assemble','public_event_reconstruction'),
            ('next_plan','public_next_plan'),('_apply','refinement_and_quality'),('_quality','mesh_quality'),
            ('_quadrature','native_quadrature'),('_surface','native_surface'),
            ('build_saved_mode_tracking','individual_mode_tracking'),('curved_rf_goal_indicator','rf_goal_indicator'),
            ('curved_residual_indicator','residual_indicator')],
        'curved_rf_goal_indicator': [('curved_rf_goal_indicator','rf_goal_indicator'),('r_over_q_adjoint','rf_adjoint'),
            ('r_over_q_frequency_derivative','rf_frequency_derivative'),('mapped_element_matrices','rf_element_contributions')],
        'curved_rf_adjoint': [('r_over_q_adjoint','rf_adjoint'),('splu','adjoint_factorization')],
        'curved_rf_frequency_sensitivity': [('r_over_q_frequency_derivative','rf_frequency_derivative')],
    }
    for name,bindings in mapping.items():
        module=importlib.import_module('.'+name,__package__)
        selected.extend((module,attribute,phase) for attribute,phase in bindings)
    module=importlib.import_module(__name__)
    selected.extend((module,attribute,phase) for attribute,phase in
                    [('read_solution','native_reconstruction'),('build_saved_mode_tracking','individual_mode_tracking'),
                     ('assemble_curved','assembly'),('quantities_curved','rf_quantities'),
                     ('_write','journal_write'),('replay_adaptive_refinement','complete_public_replay')])
    return selected


def _unverified(reason):
    return dict(status='UNVERIFIED',relative_errors={k:None for k in LIMITS},gates={k:False for k in LIMITS},
                limits=dict(LIMITS),common_hphi_sign=None,unverified_reason=reason,physical_error_bound=None)


def _initial_identity(solution, sampled, grid, request):
    n=len(grid['weights']);w=grid['weights'];own=sampled[:n,:,2]
    arrays=grid['all_reference_arrays']
    if 'reference_fields_levels' in arrays:
        candidates=arrays['reference_fields_levels'][-1,:n,:,2]
        indices=arrays['reference_selected_indices'][-1].tolist()
        labels=['target','guard-2','guard-3']
        expected=dict(zip(labels,indices))
        expected_indices=[expected['target' if label=='fundamental' else label] for label in request['initial_ids']]
    else:
        candidates=grid['reference_fields'][:,2,None];expected_indices=[0]
    # All original candidates remain in the package. Zero-Hphi TE candidates
    # cannot define a TM magnetic overlap; retain their null columns explicitly.
    own_norm=np.sum(w[:,None]*own*own,axis=0);ref_norm=np.sum(w[:,None]*candidates*candidates,axis=0)
    eligible=np.flatnonzero(np.isfinite(ref_norm)&(ref_norm>0))
    if (not np.isfinite(own_norm).all() or np.any(own_norm<=0) or len(eligible)<len(own_norm)):
        return dict(passed=False,reason='insufficient nonzero finite magnetic candidate norms',order=grid['order'])
    matrix=(own.T@(w[:,None]*candidates[:,eligible]))/np.sqrt(own_norm[:,None]*ref_norm[eligible][None,:])
    if not np.isfinite(matrix).all():return dict(passed=False,reason='nonfinite full-field overlap',order=grid['order'])
    rows,columns=linear_sum_assignment(-abs(matrix));assigned={int(r):int(eligible[c]) for r,c in zip(rows,columns)}
    records=[]
    for m,expected in enumerate(expected_indices):
        column=next((c for c,j in enumerate(eligible) if j==expected),None)
        score=None if column is None else float(abs(matrix[m,column]))
        alternatives=[abs(v) for c,v in enumerate(matrix[m]) if c!=column]
        margin=None if score is None or not alternatives else float(score-max(alternatives))
        passed=(assigned.get(m)==expected and score is not None and score>=request['controls']['minimum_overlap'] and
                (margin is None or margin>=request['controls']['minimum_assignment_margin']))
        records.append(dict(native_mode_index=m,native_id=request['initial_ids'][m],expected_reference_index=expected,
                            assigned_reference_index=assigned.get(m),absolute_overlap=score,assignment_margin=margin,passed=bool(passed)))
    full=[[None]*candidates.shape[1] for _ in own_norm]
    for i,row in enumerate(matrix):
        for j,value in zip(eligible,row):full[i][int(j)]=float(value)
    return dict(passed=all(row['passed'] for row in records),order=grid['order'],matches=records,signed_overlaps=full,
                excluded_zero_magnetic_candidate_indices=[int(i) for i in range(len(ref_norm)) if i not in eligible],
                scope='actual full-volume magnetic fields of every native ID versus all nonzero independent candidates; no frequency-rank assignment')


def _uniform_quadrature(solution, request, mode):
    """Native base/high forms and RF on unchanged coefficients, no indicator."""
    from dataclasses import replace
    order=request['quadrature_check_order'];limit=request['quadrature_relative_tolerance']
    k,m=assemble_curved(solution.space,quadrature_order=order)
    u=solution.u[:,mode];u=u/np.max(abs(u))
    kl,ml=float(u@(solution.stiffness@u)),float(u@(solution.mass@u));kh,mh=float(u@(k@u)),float(u@(m@u))
    differences=dict(rayleigh_frequency=abs(math.sqrt(kh/mh/(kl/ml))-1),mass_form=abs(mh/ml-1))
    low=quantities_curved(solution,mode,include_surface_peaks=False)
    high=quantities_curved(replace(solution,stiffness=k,mass=m,quadrature_order=order),mode,include_surface_peaks=False)
    for key in ('stored_energy_j','r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm'):
        differences[key]=abs(high[key]/low[key]-1) if low[key]>0 else None
    return dict(passed=all(v is not None and math.isfinite(v) and v<=limit for v in differences.values()),
                base_order=solution.case.quadrature_order,check_order=order,relative_tolerance=limit,relative_differences=differences,
                scope='original uniform field Rayleigh/mass and RF base/high quadrature; no residual selection or adjoint')


def _uniform_event(request, run, events, runs, *, origin):
    current=read_solution(run);index=len(events);parent=index-1 if index else None
    tracking=None;ids=deepcopy(request['initial_ids']);status='INITIAL'
    if parent is not None:
        tracking=build_saved_mode_tracking(dict(schema_version=1,previous_run=runs[parent],current_run=str(run),
            previous_ids=events[parent]['current_mode_ids'],controls=request['controls']))
        result=tracking['tracking'];ids=result['current_mode_ids']
        status='PASS' if result['status']=='PASS' and result['individual_ids_complete'] else 'UNVERIFIED'
    mode=None if status=='UNVERIFIED' else ids.index(request['mode_id'])
    q=None if mode is None else parse_json((Path(run)/'results.json').read_text())['modes'][mode]
    quad=None if mode is None else _uniform_quadrature(current,request,mode)
    event=dict(index=index,status=status,parent_event_index=parent,refinement_kind='initial' if not index else 'uniform_confirmation',
               marked_cells=[],triangles=len(current.space.geometry.cell_nodes),dofs=len(current.u),quality=native._quality(current.space,request),
               current_mode_ids=ids,mode_index=mode,tracking=tracking,indicator=None,quantities=q,quadrature_check=quad,
               surface=None if mode is None else native._surface(current,mode,q),accepted=mode is not None and quad['passed'],
               uniform_confirmations=0,confirmation_comparison=None,selection=None,origin=origin)
    if parent is not None and mode is not None:
        event['confirmation_comparison']=native._comparison(events[parent],event,request)
        if event['confirmation_comparison']['passed']:
            event['uniform_confirmations']=events[parent]['uniform_confirmations']+1
    return event,current


def _sample_event(request, reference, current, event, directory, previous_records, parent_event, initial_identity_passed, recorder, *, verify_samples=None):
    if verify_samples is not None and (type(verify_samples) is not list or
            len(verify_samples)!=len(reference['grids']) or
            [r.get('order') for r in verify_samples]!=[g['order'] for g in reference['grids']]):
        raise ValueError('saved RF samples require every original quadrature order')
    index=event['index'];mode=event['mode_index'];sampler=EfficiencyFieldSampler(current)
    records=[];reference_orders=[];changes=[];identity=[]
    for grid in reference['grids']:
        order=grid['order'];n=len(grid['weights'])
        with recorder.phase('full_native_field_sampling'):
            sampled=sampler.evaluate(np.vstack((grid['points'],grid['axis'])))['fields']
            sampled[:n]*=np.sqrt(grid['density'])[:,None,None]
        if index==0:identity.append(_initial_identity(current,sampled,grid,request))
        if mode is None:
            accuracy=_unverified('native individual target identity UNVERIFIED')
        else:
            accuracy=assess_efficiency_samples(sampled[:n,mode],grid['reference_fields'],grid['weights'],
                sampled[n:,mode,1],grid['reference_axis_ez'],grid['axis_weights'],event['quantities'],grid['quantities'],event['surface']['intervals'])
        reference_orders.append(dict(order=order,accuracy=accuracy))
        parent_index=event['parent_event_index']
        if parent_index is not None:
            previous=next(r for r in previous_records if r['order']==order)
            file=Path(previous['sample_path'])
            if digest(file)!=previous['sample_sha256']:raise ValueError('original parent sample bytes changed')
            with np.load(file,allow_pickle=False) as data:parent_samples=data['fields']
            parent_mode=parent_event['mode_index']
            if mode is None or parent_mode is None:change=_unverified('unresolved parent/child native identity')
            else:
                a=dict(fields=parent_samples[:n,parent_mode],axis_ez=parent_samples[n:,parent_mode,1],weights=grid['weights'],
                       axis_weights=grid['axis_weights'],quantities=parent_event['quantities'],peak_intervals=parent_event['surface']['intervals'])
                b=dict(fields=sampled[:n,mode],axis_ez=sampled[n:,mode,1],weights=grid['weights'],axis_weights=grid['axis_weights'],
                       quantities=event['quantities'],peak_intervals=event['surface']['intervals'])
                change=assess_rf_goal_pair(a,b)
            changes.append(dict(order=order,accuracy=change))
        path=directory/f'samples-event-{index+1:03d}-gauss-{order}.npz'
        if verify_samples is None:
            with recorder.phase('full_native_sample_save'):
                with path.open('xb') as stream:np.savez_compressed(stream,fields=sampled,mode_ids_json=np.array(json.dumps(event['current_mode_ids'])))
        else:
            from .adaptive_efficiency_reference import _bound_file
            saved=verify_samples[len(records)]
            if str(path)!=saved['sample_path']:
                raise ValueError('saved RF sample path differs from its original native event')
            with recorder.phase('full_native_sample_verification'):
                _bound_file(path,saved['sample_sha256'],{})
                with np.load(path,allow_pickle=False) as data:
                    if (set(data.files)!={'fields','mode_ids_json'} or data['fields'].dtype!=sampled.dtype or
                            not np.array_equal(data['fields'],sampled) or data['mode_ids_json'].shape!=() or
                            data['mode_ids_json'].dtype.kind!='U' or
                            parse_json(str(data['mode_ids_json']))!=event['current_mode_ids']):
                        raise ValueError('saved RF full fields or individual IDs differ from original native coefficients')
                _bound_file(path,saved['sample_sha256'],{})
        records.append(dict(order=order,sample_path=str(path),sample_sha256=digest(path),volume_sample_count=n,
                            axis_sample_count=len(grid['axis_weights']),native_mode_count=sampled.shape[1],
                            reference_path=grid['reference_field_path'],reference_sha256=grid['reference_field_sha256']))
    if verify_samples is not None:_same(records,verify_samples,'saved RF full sample records')
    if index==0:initial_identity_passed=all(row['passed'] for row in identity)
    observation=dict(index=index,source_domain_identity_status='PASS' if initial_identity_passed and mode is not None else 'UNVERIFIED',
                     reference_orders=reference_orders,parent_change=None if event['parent_event_index'] is None else
                     dict(parent_event_index=event['parent_event_index'],orders=changes))
    return observation,records,identity,initial_identity_passed


def _prefix_cost(recorder, origin):
    value=recorder.snapshot();phases=value['phases']
    names={'initial_plan','native_event','next_uniform_plan','complete_public_replay'}
    roots=[p['inclusive_seconds'] for p in phases if p['parent_index'] is None and p['name'] in names]
    return dict(native_path_cumulative_seconds=None if any(v is None for v in roots) else math.fsum(roots),
                recorder_prefix_wall_seconds=value['wall_seconds'],
                submission_prefix_wall_seconds=None if origin is None else time.perf_counter()-origin,
                scope='root native paths counted once including rejected probes and RF adjoints; field/reference/journal costs in recorder wall; process terminal wall measured separately')


def _stop_status(event, assessment, *, initial_identity, same_moments, ritz, native_status, completed_events, max_events):
    if not initial_identity:return 'INITIAL_IDENTITY_UNVERIFIED'
    if not same_moments:return 'GEOMETRY_MOMENTS_UNVERIFIED'
    if not ritz:return 'RITZ_UNVERIFIED'
    if event['status']=='UNVERIFIED':return 'IDENTITY_UNVERIFIED'
    if not event['quadrature_check']['passed']:return 'QUADRATURE_UNVERIFIED'
    comparison=event.get('confirmation_comparison')
    if comparison is not None and not comparison['verified']:return 'QUANTITY_UNVERIFIED'
    if assessment['status']=='CONFIRMED':return 'TARGETS_MET'
    if native_status not in (None,'PAUSED','TARGETS_MET'):return native_status
    if completed_events>=max_events:return 'LEVEL_LIMIT'
    return 'PAUSED'


def _verify_fixed_request(execution, request):
    # Re-read the pinned plan and all original request/source bytes after work.
    _same(request_for_curved_rf_goal_efficiency_execution(execution),request,'RF goal original request')


def execute_curved_rf_goal_efficiency_worker(execution, directory, *, bindings=None, max_new_events=None, submission_origin=None):
    """Execute one immutable fixed row in a new directory; a cap gives PAUSED.

    This fresh worker does not resume or accept caller-supplied numerical state.
    The frozen public checkpoint and separate continuation events are retained.
    Full benchmark replay/resume is a separate required acceptance stage.
    """
    request=request_for_curved_rf_goal_efficiency_execution(execution);execution=deepcopy(execution)
    if max_new_events is not None:integer(max_new_events,'max_new_events')
    if submission_origin is not None and (type(submission_origin) not in (int,float) or not math.isfinite(submission_origin) or
                                         not 0<submission_origin<=time.perf_counter()):
        raise ValueError('submission_origin requires a finite past shared monotonic timestamp')
    directory=Path(directory).absolute()
    if directory.exists():raise FileExistsError(directory)
    if any(p.is_symlink() for p in (directory,*directory.parents)):
        raise ValueError('RF goal output requires a new directory without symlinks')
    recorder=PhaseRecorder();implementation=_implementation_hashes();case=Case.from_dict(request['case'])
    with recorder.phase('reference_verification'):reference=load_curved_rf_goal_efficiency_reference(execution['case_id'],bindings=bindings)
    return _execute_worker_events(execution,request,directory,reference,recorder,implementation,
                                  max_new_events=max_new_events,submission_origin=submission_origin)


def _execute_worker_events(execution, request, directory, reference, recorder, implementation, *,
                           max_new_events=None, submission_origin=None, prefix=None, resume_origin=None, retained_inputs=None):
    """Shared numerical loop; callers must fully validate any original prefix."""
    case=Case.from_dict(request['case'])
    selected=observation_bindings();directory.mkdir(parents=True,exist_ok=False)
    events=[];runs=[];observations=[];samples=[];records=[];sources=[];public=None;native_runs=[]
    status='PAUSED';initial_identity=False;solves_attempted=0;solves_completed=0;index=0;report=None
    is_uniform=execution['method']=='uniform';cache=None if is_uniform else native._VerifiedRFPrefix()
    if prefix is not None:
        events=deepcopy(prefix['events']);runs=list(prefix['level_runs']);observations=deepcopy(prefix['observations'])
        records=deepcopy(prefix['event_records']);samples=[r['samples'] for r in records];sources=deepcopy(prefix['native_sources'])
        public=deepcopy(prefix['public_checkpoint']);native_runs=[] if public is None else list(public['level_runs'])
        initial_identity=all(r['passed'] for r in records[0]['initial_independent_identity'])
        solves_attempted=solves_completed=len(events)
    start=len(events);index=start;active_stage='initial_plan'
    last_checkpoint=None if prefix is None else dict(path=resume_origin['journal_path'],sha256=resume_origin['journal_sha256'])
    checkpoint_runs=list(runs)
    try:
        with observe_adjoint_linear_solves(recorder),observe_selected_calls(recorder,selected):
            with recorder.phase('initial_plan'):
                if prefix is not None and (is_uniform or public['status']=='TARGETS_MET'):
                    current=read_solution(runs[-1]);next_case,source,_=_uniform_plan(case,request,current)
                    plan=curved.Plan(next_case,source,None)
                elif is_uniform:
                    _,plan=curved.next_plan(case,request,[],None)
                else:public,plan=native.assemble(request,native_runs,_cache=cache)
            limit=min(request['max_levels'],start+(max_new_events or request['max_levels']))
            for index in range(start,limit):
                run=directory/f'event-{index+1:03d}';continuation=not is_uniform and public['status']=='TARGETS_MET'
                with recorder.phase('native_event'):
                    active_stage='native_solve'
                    solves_attempted+=1
                    solution=native.solve(plan.case,mesh_data=plan.source_mesh);solves_completed+=1
                    active_stage='native_save'
                    native.save_run(plan.case,solution,run)
                    active_stage='native_event_reconstruction'
                    if not is_uniform and not continuation:
                        native_runs.append(str(run));public,following=native.assemble(request,native_runs,_cache=cache)
                        event=deepcopy(public['levels'][-1]);current=cache.solution[-1]
                        _write(directory/f'public-checkpoint-{index+1:03d}.json',public)
                    else:
                        event,current=_uniform_event(request,run,events,runs,origin='uniform_control' if is_uniform else 'benchmark_confirmation')
                        following=None
                    domain=verify_efficiency_saved_domain(request,run)
                    moments=mapped_moments(current.space)
                    same_moments=not records or all(abs(v/records[0]['moments'][k]-1)<2e-12 for k,v in enumerate(moments))
                    parent=event['parent_event_index']
                    ritz=parent is None or bool(np.all(current.frequencies_hz<=np.asarray(records[parent]['all_frequencies_hz'])*(1+1e-10)))
                    all_quantities=parse_json((run/'results.json').read_text())['modes']
                events.append(event);runs.append(str(run));sources.append(_native_files(run))
                with recorder.phase('independent_accuracy_and_parent_changes'):
                    active_stage='full_fields_and_accuracy'
                    observation,sample_rows,identity,initial_identity=_sample_event(request,reference,current,event,directory,
                        [] if parent is None else samples[parent],None if parent is None else events[parent],initial_identity,recorder)
                    if not same_moments or not ritz:observation['source_domain_identity_status']='UNVERIFIED'
                    observations.append(observation);samples.append(sample_rows)
                    assessment=assess_rf_goal_history(events,observations)
                record=dict(index=index,origin='uniform_control' if is_uniform else 'benchmark_confirmation' if continuation else 'public_native',
                            run=str(run),domain=domain,moments=list(moments),fixed_moments_passed=same_moments,ritz_passed=ritz,
                            all_frequencies_hz=current.frequencies_hz.tolist(),all_quantities=all_quantities,
                            initial_independent_identity=identity if index==0 else None,samples=sample_rows)
                records.append(record)
                status=_stop_status(event,assessment,initial_identity=initial_identity,same_moments=same_moments,ritz=ritz,
                                    native_status=None if is_uniform else public['status'],completed_events=len(events),max_events=request['max_levels'])
                record['observed_prefix_cost']=_prefix_cost(recorder,submission_origin)
                report=dict(schema_version=1,document_type='curved_rf_goal_efficiency_worker_checkpoint',execution=execution,request=request,
                            status=status,native_status='UNIFORM_CONTROL' if is_uniform else public['status'],public_checkpoint=deepcopy(public),
                            events=events,level_runs=runs,native_sources=sources,event_records=records,observations=observations,
                            assessment=assessment,reference_bound_inputs=reference['bound_inputs'],implementation_sha256=implementation,
                            native_solves_attempted=solves_attempted,native_solves_completed=solves_completed,
                            physical_error_bound=None,development_event_limit=max_new_events,
                            observation_schema_version=2,
                            observed_c_calls=deepcopy(C_CALLS),
                            scope='fresh fixed RF-goal native branch and full-grid finite metrics; public checkpoint frozen before benchmark continuation; full journal replay/resume remains required')
                if prefix is not None:
                    report.update(schema_version=2,resume_origin=deepcopy(resume_origin),
                                  scope='resumed fixed RF-goal branch; immutable original prefix and separate measured continuation segment')
                active_stage='checkpoint_publication';checkpoint=directory/f'checkpoint-{index+1:03d}.json'
                _write(checkpoint,report)
                last_checkpoint=dict(path=str(checkpoint),sha256=digest(checkpoint));checkpoint_runs=list(runs)
                if status!='PAUSED' or index+1==limit:break
                if is_uniform or public['status']=='TARGETS_MET':
                    active_stage='next_uniform_plan'
                    try:
                        with recorder.phase('next_uniform_plan'):
                            next_case,source,_=_uniform_plan(case,request,current)
                            plan=curved.Plan(next_case,source,None)
                    except ValueError as error:
                        if not any(word in str(error) for word in ('max_triangles','minimum_corner_angle_deg','TRACKING_BUDGET')):raise
                        status='TRACKING_BUDGET' if 'TRACKING_BUDGET' in str(error) else 'REFINEMENT_LIMIT'
                        report['stop_reason']=str(error);break
                else:plan=following
            if public is not None:
                active_stage='complete_public_replay'
                # A full public reconstruction does not use the execution-local
                # prefix cache. It verifies all accepted/rejected native events.
                replayed=replay_adaptive_refinement(public)
                if replayed!=public:raise ValueError('original public RF checkpoint differs after complete replay')
            with recorder.phase('final_source_verification'):
                active_stage='final_source_verification'
                if retained_inputs is not None:
                    from .adaptive_efficiency_reference import _bound_file
                    for path,sha in retained_inputs.items():_bound_file(path,sha,{})
                _verify_fixed_request(execution,request)
                verify_reference_bytes(reference)
                if implementation!=_implementation_hashes():raise RuntimeError('RF goal worker implementation changed')
                if sources!=[_native_files(Path(run)) for run in runs]:raise ValueError('RF goal native bytes changed')
                for group in samples:
                    for row in group:
                        if digest(Path(row['sample_path']))!=row['sample_sha256']:raise ValueError('RF goal full field samples changed')
        active_stage='result_publication'
        report['status']=status;report['observed_cost']=recorder.finish()
        report['observed_bindings']=[dict(module=m.__name__,attribute=a,phase=p) for m,a,p in selected]
        _write(directory/'result.json',report)
    except BaseException as error:
        try:
            failure=dict(status='FAILED',error_type=type(error).__name__,error=str(error),event_index=index,active_stage=active_stage,
                         preceding_level_runs=runs,checkpoint_level_runs=checkpoint_runs,last_complete_checkpoint=last_checkpoint,
                         native_solves_attempted=solves_attempted,native_solves_completed=solves_completed,
                         public_checkpoint=public,observation_schema_version=2,observed_cost=recorder.finish())
            _write(directory/'failure.json',failure)
        except BaseException as recording_error:
            if hasattr(error,'add_note'):error.add_note('RF failure recording also failed: '+type(recording_error).__name__+': '+str(recording_error))
        raise
    return report
