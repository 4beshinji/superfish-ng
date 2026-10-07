# SPDX-License-Identifier: Apache-2.0
"""Fresh N05 native efficiency execution with full reference and field gates.

Original FEM, residual selection, conforming restrictions and individual-mode
tracking are called directly. Native RF stopping remains separately recorded;
N05's additional field/reference gates may require more uniform refinements.
"""
from copy import deepcopy
from dataclasses import replace
import importlib
import json
import math
from pathlib import Path
import time

import numpy as np

from . import adaptive_refinement as affine
from . import curved_adaptive_refinement as curved
from .adaptive_efficiency_accuracy import _error, assess_efficiency_samples
from .adaptive_efficiency_assembly_reuse import reuse_high_order_assembly
from .adaptive_efficiency_domain import _native_files, verify_efficiency_saved_domain
from .adaptive_efficiency_fields import EfficiencyFieldSampler
from .adaptive_efficiency_observation import observe_selected_calls
from .adaptive_efficiency_plan import build_adaptive_efficiency_plan
from .adaptive_efficiency_reference import load_efficiency_reference, verify_reference_bytes
from .adaptive_efficiency_timing import PhaseRecorder
from .adaptive_efficiency_uniform import _confirmation
from .affine_saved import read_verified_affine_solution
from .completion import digest
from .config import integer
from .curved_refinement_steps import CurvedRefinementStep
from .geometry_surface_numerics import mapped_moments, quadrature_check
from .high_order import quadratic_space
from .io import save_run
from .jobs import _implementation_hashes
from .marked_refinement import refine_marked_cells
from .mesh import element_geometry
from .mesh_input import mesh_to_dict
from .project import parse_json
from .saved import read_solution
from .saved_mode_tracking import build_saved_mode_tracking
from .solver import solve


# Explicit native aliases used by this worker and the original direct consumers.
# Inline equilibration/normalization/residual work remains in solve's exclusive
# remainder; it is not reported as a separately observed function.
OBSERVATIONS = {
    'solver': [('eigsh','eigenproblem'),('assemble','assembly')],
    'high_order': [('assemble_p2','assembly')],
    'curved_solution': [('assemble_curved','assembly'),('eigsh','eigenproblem'),('case_curved_space','mesh_and_space')],
    'curved_fem': [('assemble_curved','assembly')],
    'affine_saved': [('assemble_p2','assembly'),('assemble','assembly'),('quantities','rf_quantities')],
    'curved_saved': [('assemble_curved','assembly'),('quantities_curved','rf_quantities')],
    'rf': [('quantities','rf_quantities')],
    'curved_rf': [('quantities_curved','rf_quantities')],
    'io': [('quantities','rf_quantities')],
    'curved_adaptive_refinement': [('assemble_curved','assembly'),('curved_residual_indicator','residual_indicator'),
                                  ('_apply','refinement_and_quality'),('bound_surface_peaks','surface_peak_intervals'),
                                  ('mark_bulk','residual_marking')],
    'adaptive_refinement': [('residual_indicator','residual_indicator'),('refine_marked_cells','refinement_and_quality'),
                            ('mark_bulk','residual_marking')],
    'residual_indicator': [('residual_indicator','residual_indicator'),('mark_bulk','residual_marking')],
    'curved_residual_indicator': [('curved_residual_indicator','residual_indicator')],
    'marked_refinement': [('refine_marked_cells','refinement_and_quality')],
    'nested_affine_tracking': [('assemble_p2','assembly'),('refine_marked_cells','refinement_and_quality')],
    'nested_curved_tracking': [('assemble_curved','assembly')],
    'geometry_surface_numerics': [('assemble_curved','assembly'),('quantities_curved','rf_quantities')],
    'adaptive_surface_stopping': [('bound_affine_surface_peaks','surface_peak_intervals')],
    'curved_extrema': [('bound_surface_peaks','surface_peak_intervals')],
    'saved_mode_tracking': [('read_solution','native_reconstruction')],
}


def observation_bindings():
    result=[]
    for name,bindings in OBSERVATIONS.items():
        module=importlib.import_module('.'+name,__package__)
        result.extend((module,attribute,phase) for attribute,phase in bindings)
    # These aliases were imported directly into this module.
    module=importlib.import_module(__name__)
    result.extend((module,attribute,phase) for attribute,phase in
                  [('refine_marked_cells','refinement_and_quality'),('solve','native_solve_and_normalization'),
                   ('save_run','native_save'),('read_verified_affine_solution','native_reconstruction'),
                   ('read_solution','native_reconstruction'),('build_saved_mode_tracking','individual_mode_tracking')])
    return result


def _moments(solution,geometry_order):
    if geometry_order==2:return mapped_moments(solution.space)
    vertices,det,_=element_geometry(solution.mesh)
    return math.fsum(det/2),math.fsum(np.pi*det*vertices[:,:,0].mean(axis=1))


def _field_change(previous,current,grid):
    n=len(grid['weights']);w=grid['weights']
    a,b=previous[:n],current[:n]
    overlap=float(np.dot(w,a[:,2]*b[:,2]))
    if not math.isfinite(overlap) or overlap==0:
        return dict(passed=False,relative_errors=None,reason='unverified common Hphi sign')
    sign=1 if overlap>0 else -1
    errors=dict(electric_relative_l2=_error(a[:,:2],b[:,:2],w[:,None],sign),
                magnetic_relative_l2=_error(a[:,2],b[:,2],w,sign),
                axis_ez_relative_l2=_error(previous[n:,1],current[n:,1],grid['axis_weights'],sign))
    limits=dict(electric_relative_l2=.005,magnetic_relative_l2=.005,axis_ez_relative_l2=.01)
    return dict(passed=all(errors[k]<=v for k,v in limits.items()),relative_errors=errors,limits=limits,
                common_hphi_sign=sign,denominator='previous original native norm; one sign for E/H/physical axis')


def _prefix_cost(recorder,submission_origin):
    cost=recorder.snapshot()
    phases=[p['inclusive_seconds'] for p in cost['phases'] if p['parent_index'] is None and
            p['name'] in ('initial_mesh_and_quality','native_level','next_refinement_plan')]
    return dict(native_path_cumulative_seconds=None if any(v is None for v in phases) else math.fsum(phases),
                recorder_prefix_wall_seconds=cost['wall_seconds'],
                submission_prefix_wall_seconds=None if submission_origin is None else time.perf_counter()-submission_origin,
                scope='root native/mesh/refinement inclusive intervals counted once; recorder prefix excludes earlier imports; optional Linux shared monotonic origin before supervisor submission includes reservation/startup/imports; full process terminal wall remains separately measured')


def _uniform_plan(case,request,solution):
    if case.geometry_order==2:
        maximum=curved._maximum(case,request)
        step=CurvedRefinementStep('uniform')
        space=curved._apply(solution.space,step,maximum);curved._quality(space,request)
        current=replace(solution.case,curved_refinement_levels=0,
                        curved_refinement_steps=curved._history(solution.case)+(step,))
        if len(space.geometry.points_rz_m)*2*case.modes>8388608:
            raise ValueError('TRACKING_BUDGET: uniform next space exceeds 8388608 feature entries')
        return current,solution.source_mesh_data,[]
    maximum,angle=affine._limits(case,request)
    marked=list(range(len(solution.mesh.triangles)))
    mesh=refine_marked_cells(case,solution.mesh,marked,max_triangles=maximum,minimum_angle_deg=angle).mesh
    if len(quadratic_space(mesh).dof_points)*2*case.modes>8388608:
        raise ValueError('TRACKING_BUDGET: uniform next space exceeds 8388608 feature entries')
    return case,mesh_to_dict(mesh),marked


def _initial_identity(solution,reference,samples,request):
    anchor=reference['rounded_anchor']
    if anchor is not None:
        same_frequency=np.array_equal(solution.frequencies_hz,anchor.frequencies_hz)
        signs=[1 if np.array_equal(solution.u[:,m],anchor.u[:,m]) else
               -1 if np.array_equal(solution.u[:,m],-anchor.u[:,m]) else None for m in range(request['case']['solver']['modes'])]
        return dict(passed=same_frequency and all(s is not None for s in signs),
                    method='whole original native coefficients/frequency equal up to individual common signs; actual N03 anchor IDs',
                    signs=signs,anchor_case=anchor.case.to_dict())
    grid=reference['grids'][0];n=len(grid['weights']);w=grid['weights'];target=grid['reference_fields'][:,2]
    h=samples[0][:n,:,2]
    overlaps=(h.T@(w*target))/np.sqrt(np.sum(w[:,None]*h*h,axis=0)*np.dot(w,target*target))
    declared=request['initial_ids'].index(request['mode_id'])
    others=[abs(v) for i,v in enumerate(overlaps) if i!=declared]
    margin=None if not others else float(abs(overlaps[declared])-max(others))
    return dict(passed=bool(np.isfinite(overlaps).all() and abs(overlaps[declared])>=request['controls']['minimum_overlap'] and
                           (margin is None or margin>=request['controls']['minimum_assignment_margin'])),
                method='actual full-volume native Hphi versus independent analytical target; native guards retained',
                signed_overlaps=overlaps.tolist(),assignment_margin=margin)


def execute_efficiency_worker(execution,bindings,directory,*,max_new_levels=None,submission_origin=None):
    """Execute a fixed N05 row; a development limit can only produce PAUSED.

    Resource caps are enforced by the fresh-process supervisor. This worker
    records actual native and full reference work, never a synthetic timing.
    Exceptions retain their original identity and all preceding artifacts.
    """
    fixed=build_adaptive_efficiency_plan()
    if execution not in fixed['executions']:
        raise ValueError('efficiency worker execution differs from the complete fixed N05 row')
    execution=deepcopy(execution);request=execution['request'];case=affine._request(request)
    if max_new_levels is not None:integer(max_new_levels,'max_new_levels')
    if submission_origin is not None and (type(submission_origin) not in (int,float) or
            not math.isfinite(submission_origin) or not 0<submission_origin<=time.perf_counter()):
        raise ValueError('submission_origin requires a finite past shared monotonic timestamp')
    directory=Path(directory).absolute()
    if directory.exists():raise FileExistsError(directory)
    recorder=PhaseRecorder();implementation=_implementation_hashes()
    with recorder.phase('shared_reference_verification'):
        reference=load_efficiency_reference(execution['case_id'],bindings)
    selected=observation_bindings()
    directory.mkdir(parents=True,exist_ok=False)
    levels=[];runs=[];sources=[];sample_history=[];first_hit=None;confirmed_hit=None;status='PAUSED'
    result=None;index=-1
    try:
        with observe_selected_calls(recorder,selected):
            with recorder.phase('initial_mesh_and_quality'):
                if case.geometry_order==2:
                    decision,plan=curved.next_plan(case,request,[],None)
                    current_case,mesh_data=plan.case,plan.source_mesh
                else:
                    decision,mesh=affine._next(case,request,[],None)
                    current_case,mesh_data=case,mesh_to_dict(mesh)
                marked=[];kind='initial'
            count=min(request['max_levels'],max_new_levels or request['max_levels'])
            for index in range(count):
                run=directory/f'level-{index+1:03d}'
                with recorder.phase('native_level'):
                    solution=solve(current_case,mesh_data=mesh_data)
                    save_run(current_case,solution,run)
                    current=read_solution(run) if case.geometry_order==2 else read_verified_affine_solution(run)
                    domain=verify_efficiency_saved_domain(request,run)
                    if index==0 and case.geometry_order==1 and not domain['native_mesh_exact_initial_match']:
                        raise ValueError('initial affine source mesh differs from fixed reference')
                    ids=request['initial_ids'];pair=None
                    if index:
                        controls=dict(request['controls'],marked_cells=marked) if case.geometry_order==1 else request['controls']
                        pair=build_saved_mode_tracking(dict(schema_version=1,previous_run=runs[-1],current_run=str(run),
                                                          previous_ids=levels[-1]['current_mode_ids'],controls=controls))
                        ids=pair['tracking']['current_mode_ids']
                        if pair['status']!='PASS' or not pair['tracking']['individual_ids_complete']:
                            status='IDENTITY_UNVERIFIED'
                    assembly_reuse=None
                    if status=='IDENTITY_UNVERIFIED':
                        mode=None;q=None;surface=None;indicator=None;quad=None;rf_quad=None
                    else:
                        mode=ids.index(request['mode_id']);q=parse_json((run/'results.json').read_text())['modes'][mode]
                        with recorder.phase('residual_indicator_or_quadrature_base'):
                            indicator=(curved.curved_residual_indicator(current.case,current,mode=mode,quadrature_order=current.case.quadrature_order)
                                       if case.geometry_order==2 else affine.residual_indicator(case,current,mode=mode)
                                       if execution['method']=='adaptive' else None)
                        with recorder.phase('higher_quadrature_and_rf_integrals'):
                            if case.geometry_order==2:
                                with reuse_high_order_assembly(recorder,current.space,request['quadrature_check_order']) as assembly_reuse:
                                    quad=curved._quadrature(current,request,mode,indicator)
                                    rf_quad=quadrature_check(current,mode)
                            else:
                                quad=dict(passed=True,scope='exact affine P2 polynomial forms')
                                rf_quad=dict(status='PASS',scope='original exact affine P2 volume/wall polynomial and phase integrals')
                        surface=curved._surface(current,mode,q) if case.geometry_order==2 else affine.surface_intervals(case,current,mode)
                    moments=_moments(current,case.geometry_order)
                    moment_pass=not levels or all(abs(v/levels[0]['moments'][k]-1)<2e-12 for k,v in enumerate(moments))
                    ritz_pass=not levels or bool(np.all(current.frequencies_hz<=np.asarray(levels[-1]['all_frequencies_hz'])*(1+1e-10)))
                    native_status='INITIAL' if not index else 'PASS' if mode is not None else 'UNVERIFIED'
                    row=dict(index=index,status=native_status,refinement_kind=kind,marked_cells=marked,run=str(run),
                             current_mode_ids=deepcopy(ids),mode_index=mode,tracking=pair,quantities=q,indicator=indicator,
                             surface=surface,quadrature_check=quad,rf_quadrature_check=rf_quad,domain=domain,
                             high_order_assembly_reuse=assembly_reuse,
                             moments=list(moments),fixed_moments_passed=moment_pass,ritz_passed=ritz_pass,
                             all_frequencies_hz=current.frequencies_hz.tolist(),triangles=len(current.space.geometry.cell_nodes) if case.geometry_order==2 else len(current.mesh.triangles),
                             dofs=len(current.u))
                    runs.append(str(run));levels.append(row);sources.append(_native_files(run))
                if not moment_pass:status='GEOMETRY_MOMENTS_UNVERIFIED'
                if not ritz_pass:status='RITZ_UNVERIFIED'
                if quad is not None and (not quad['passed'] or rf_quad['status']!='PASS'):status='QUADRATURE_UNVERIFIED'
                evaluations=[];full_samples=[];changes=[]
                if mode is not None and status=='PAUSED':
                    with recorder.phase('full_native_reference_metrics'):
                        sampler=EfficiencyFieldSampler(current)
                        for g,grid in enumerate(reference['grids']):
                            n=len(grid['weights'])
                            sampled=sampler.evaluate(np.vstack((grid['points'],grid['axis'])))['fields']
                            sampled[:n]*=np.sqrt(grid['density'])[:,None,None]
                            full_samples.append(sampled)
                            target=sampled[:,mode]
                            accuracy=assess_efficiency_samples(target[:n],grid['reference_fields'],grid['weights'],target[n:,1],
                                                               grid['reference_axis_ez'],grid['axis_weights'],q,grid['quantities'],surface['intervals'])
                            if sample_history:
                                previous=sample_history[-1][g][:,levels[-2]['mode_index']]
                                changes.append(_field_change(previous,target,grid))
                            sampled_path=directory/f'samples-level-{index+1:03d}-gauss-{grid["order"]}.npz'
                            np.savez_compressed(sampled_path,fields=sampled,mode_ids=np.array(ids))
                            evaluations.append(dict(order=grid['order'],accuracy=accuracy,volume_sample_count=n,
                                                    axis_sample_count=len(grid['axis_weights']),sample_path=str(sampled_path),
                                                    native_sample_sha256=digest(sampled_path),reference_path=grid['reference_field_path'],
                                                    reference_sha256=grid['reference_field_sha256']))
                        if not index:
                            row['initial_independent_identity']=_initial_identity(current,reference,full_samples,request)
                            if not row['initial_independent_identity']['passed']:status='INITIAL_IDENTITY_UNVERIFIED'
                        row['reference_accuracy']=evaluations;row['consecutive_field_changes']=changes
                        sample_history.append(full_samples)
                accurate=bool(evaluations and all(e['accuracy']['status']=='PASS' for e in evaluations) and status=='PAUSED')
                if accurate and first_hit is None:first_hit=index
                confirmation=_confirmation(levels,request) if mode is not None else dict(passed=False,changes=[])
                uniform_twice=len(levels)>=3 and all(r['refinement_kind']=='uniform_confirmation' for r in levels[-2:])
                field_confirmed=len(levels)>=3 and all(len(r.get('consecutive_field_changes',[]))==2 and
                                                     all(c['passed'] for c in r['consecutive_field_changes']) for r in levels[-2:])
                row['native_quantity_confirmation']=confirmation
                row['physical_reference_targets_met']=accurate
                if status=='PAUSED' and accurate and confirmation['passed'] and uniform_twice and field_confirmed:
                    status='TARGETS_MET';confirmed_hit=index
                elif status=='PAUSED' and len(levels)>=request['max_levels']:status='LEVEL_LIMIT'
                row['end_of_level_status']=status
                row['observed_prefix_cost']=_prefix_cost(recorder,submission_origin)
                result=dict(schema_version=1,document_type='adaptive_efficiency_worker_checkpoint',execution=execution,status=status,
                            levels=levels,level_runs=runs,native_sources=sources,first_accuracy_hit_index=first_hit,
                            confirmed_accuracy_hit_index=confirmed_hit,physical_error_bound=None,
                            physical_acceptance_status='FINITE_N05_TARGETS_AND_TWO_UNIFORM_INTERVALS_MET' if confirmed_hit is not None else 'NOT_CONFIRMED',
                            reference_bound_inputs=reference['bound_inputs'],scope='fixed N05 original fields and full domain; separate RF, original field/reference, two uniform intervals, actual IDs, moments/Ritz/quadrature; empirical finite samples/independent reference peak scope')
                with recorder.phase('checkpoint_save'):
                    with (directory/f'checkpoint-{index+1:03d}.json').open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
                if status!='PAUSED' or index+1>=count:break
                with recorder.phase('next_refinement_plan'):
                    if execution['method']=='adaptive':
                        decision,plan=curved.next_plan(case,request,levels,current) if case.geometry_order==2 else affine._next(case,request,levels,current)
                        row['original_native_next_decision']=decision
                    else:decision,plan=dict(status='TARGETS_MET' if confirmation['passed'] else 'PAUSED'),None
                    if execution['method']=='uniform' or decision['status']=='TARGETS_MET':
                        try:current_case,mesh_data,marked=_uniform_plan(case,request,current)
                        except ValueError as error:
                            if not any(word in str(error) for word in ('max_triangles','minimum angle','minimum_corner_angle_deg','TRACKING_BUDGET')):raise
                            status='TRACKING_BUDGET' if 'TRACKING_BUDGET' in str(error) else 'REFINEMENT_LIMIT'
                            result['stop_reason']=str(error);break
                        kind='uniform_confirmation'
                    elif decision['status']!='PAUSED':
                        status=decision['status'];result['stop_reason']=decision;break
                    else:
                        marked=decision['marked_cells'];kind=decision['next_refinement_kind']
                        current_case,mesh_data=(plan.case,plan.source_mesh) if case.geometry_order==2 else (case,mesh_to_dict(plan))
            verify_reference_bytes(reference)
            if implementation!=_implementation_hashes():raise RuntimeError('efficiency implementation changed during execution')
            if sources!=[_native_files(Path(run)) for run in runs]:raise ValueError('efficiency native bytes changed during execution')
    except BaseException as error:
        failure=dict(status='FAILED',error_type=type(error).__name__,error=str(error),level_index=index,
                     preceding_level_runs=runs,observed_cost=recorder.finish())
        with (directory/'failure.json').open('x') as stream:json.dump(failure,stream,indent=2,allow_nan=False);stream.write('\n')
        raise
    result['status']=status;result['observed_cost']=recorder.finish()
    result['development_level_limit']=max_new_levels
    result['observed_bindings']=[dict(module=m.__name__,attribute=a,phase=p) for m,a,p in selected]
    with (directory/'result.json').open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    return result
