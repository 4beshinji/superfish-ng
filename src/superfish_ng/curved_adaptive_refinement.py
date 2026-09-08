# SPDX-License-Identifier: Apache-2.0
"""Version 4: native curved residual refinement with five-quantity confirmation."""
from copy import deepcopy
from dataclasses import dataclass, replace
from fractions import Fraction
import json
import math
from pathlib import Path
import numpy as np
from .config import Case, keys, integer, positive
from .constants import MU0
from .mesh import make_mesh
from .mesh_input import mesh_from_dict, mesh_to_dict, mesh_digest
from .curved_space import curved_space
from .curved_refinement import refine_curved_space
from .curved_marked_refinement import refine_marked_curved_space, _minimum_corner_angle
from .curved_refinement_steps import CurvedRefinementStep as Step
from .curved_residual_indicator import curved_residual_indicator, _components
from .curved_fem import assemble_curved
from .curved_extrema import bound_surface_peaks
from .curved_saved import geometry_arrays
from .saved import read_solution
from .project import parse_json
from .solver import solve
from .io import save_run
from .jobs import _implementation_hashes
from .saved_mode_tracking import _canonical, _snapshot, validate_tracking_controls, build_saved_mode_tracking
from .residual_indicator import mark_bulk
from .surface_convergence import _geometry_assessment, _ratio_interval
from .adaptive_surface_stopping import QUANTITIES as PEAKS, surface_changes

RF=('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')


@dataclass
class Plan:
    case: object
    source_mesh: dict
    space: object


def validate_request(request):
    fields=('schema_version','case','initial_mesh','initial_ids','mode_id','controls','bulk_fraction','max_levels',
        'max_triangles','minimum_corner_angle_deg','relative_tolerances','confirmation','surface_relative_tolerances',
        'quadrature_check_order','quadrature_relative_tolerance')
    keys(request,fields,fields,'curved adaptive refinement request');_canonical(request)
    if type(request['schema_version']) is not int or request['schema_version']!=4:
        raise ValueError('curved adaptive refinement requires schema_version 4')
    case=Case.from_dict(request['case'])
    if case.geometry_order!=2:raise ValueError('version 4 requires native quadratic curved geometry')
    if set(case.curved_contour.edge_tags)!={'axis','pec'}:
        raise ValueError('version 4 surface confirmation requires a closed PEC/axis contour; symmetry subdomains need a separate surface regularity contract')
    geometry=_geometry_assessment(case.curved_contour)
    if geometry['status']!='SMOOTH_WITHIN_TOLERANCE':
        raise ValueError('version 4 surface confirmation requires verified smooth native PEC joins and axis poles; '+geometry['status'])
    if request['confirmation']!='uniform_two_steps':raise ValueError('version 4 requires uniform_two_steps confirmation')
    integer(request['max_levels'],'max_levels',5);integer(request['max_triangles'],'max_triangles')
    for key in ('bulk_fraction','minimum_corner_angle_deg','quadrature_relative_tolerance'):positive(request[key],key)
    if request['bulk_fraction']>1 or request['minimum_corner_angle_deg']>=60:
        raise ValueError('bulk_fraction must be <=1 and minimum_corner_angle_deg <60')
    order=integer(request['quadrature_check_order'],'quadrature_check_order',2)
    if not case.quadrature_order<order<=32:
        raise ValueError('quadrature_check_order must exceed the Case quadrature_order and be <=32')
    ids=request['initial_ids']
    if type(ids) is not list or len(ids)!=case.modes or any(type(v) is not str or not v.strip() for v in ids) or len(set(ids))!=len(ids):
        raise ValueError('initial_ids requires distinct nonempty strings for every initial frequency rank')
    if type(request['mode_id']) is not str or request['mode_id'] not in ids:raise ValueError('mode_id must occur in initial_ids')
    validate_tracking_controls(request['controls'])
    if request['controls']['mapping']!='nested_curved':raise ValueError('version 4 requires nested_curved tracking')
    # Adaptive continuation requires all individual IDs, without cluster-policy overrides.
    names=('mapping','minimum_overlap','minimum_assignment_margin','relative_cluster_gap','minimum_relative_singular_value')
    keys(request['controls'],names,names,'curved adaptive tracking controls')
    for field,names in (('relative_tolerances',RF),('surface_relative_tolerances',PEAKS)):
        keys(request[field],names,names,field)
        for key,value in request[field].items():positive(value,key)
    if request['initial_mesh'] is not None:mesh_from_dict(case,request['initial_mesh'])
    return case


def _history(case):return (Step('uniform'),)*case.curved_refinement_levels+case.curved_refinement_steps


def _maximum(case,request):
    return min(request['max_triangles'],case.contour_mesh.max_triangles if case.contour_mesh else 250000)


def _quality(space,request):
    angle=_minimum_corner_angle(space.geometry.local_maps)
    if angle<request['minimum_corner_angle_deg']:
        raise ValueError(f'curved minimum_corner_angle_deg={angle:.9g} is below requested {request["minimum_corner_angle_deg"]}')
    return dict(minimum_corner_angle_deg=angle,required_minimum_corner_angle_deg=request['minimum_corner_angle_deg'],
                scope='mapped corner tangents only; no whole-element conditioning or physical-error bound')


def _apply(space,step,maximum):
    if step.kind=='uniform':
        if 4*len(space.geometry.cell_nodes)>maximum:raise ValueError(f'uniform refinement exceeds max_triangles={maximum}')
        return refine_curved_space(space).space
    return refine_marked_curved_space(space,list(step.marked_cells),max_triangles=maximum,
                                     minimum_corner_angle_deg=step.minimum_corner_angle_deg).space


def next_plan(case,request,levels,solution):
    changes=[];peak_changes=[]
    def stop(status,**data):return dict(status=status,changes=changes,surface_changes=peak_changes,**data),None
    maximum=_maximum(case,request)
    if not levels:
        mesh=make_mesh(case) if request['initial_mesh'] is None else mesh_from_dict(case,request['initial_mesh'])
        if len(mesh.triangles)>maximum:raise ValueError('initial chord mesh exceeds max_triangles')
        space=curved_space(case,mesh)
        for step in _history(case):space=_apply(space,step,maximum)
        _quality(space,request)
        return dict(status='PAUSED',marked_cells=[],next_triangles=len(space.geometry.cell_nodes),next_refinement_kind='initial'),Plan(case,mesh_to_dict(mesh),space)
    if levels[-1]['status']=='UNVERIFIED':return stop('UNVERIFIED',reason='individual mode identities are unresolved')
    if not levels[-1]['quadrature_check']['passed']:
        return stop('QUADRATURE_UNVERIFIED',reason='higher-order indicator or field-form integration comparison failed')
    for a,b in zip(levels[-3:],levels[-2:]) if len(levels)>=3 else []:
        row={}
        for key in RF:
            x,y=a['quantities'][key],b['quantities'][key]
            if not all(type(v) in (int,float) and math.isfinite(v) and v>0 for v in (x,y)):
                return stop('QUANTITY_UNVERIFIED',quantity=key)
            value=abs(y/x-1)
            if not math.isfinite(value):return stop('QUANTITY_UNVERIFIED',quantity=key)
            row[key]=dict(relative_change=value,limit=request['relative_tolerances'][key],passed=value<=request['relative_tolerances'][key])
        changes.append(row)
    peak_changes=surface_changes(levels,request['surface_relative_tolerances'])
    if any(item['relative_change_upper_bound'] is None for row in peak_changes for item in row.values()):
        return stop('QUANTITY_UNVERIFIED',reason='continuous peak ratios are unresolved')
    rf_met=len(changes)==2 and all(item['passed'] for row in changes for item in row.values())
    peaks_met=len(peak_changes)==2 and all(item['passed'] for row in peak_changes for item in row.values())
    uniform_twice=all(row['refinement_kind']=='uniform_confirmation' for row in levels[-2:]) and len(levels)>=2
    if rf_met and peaks_met and uniform_twice:return stop('TARGETS_MET')
    if len(levels)>=request['max_levels']:return stop('LEVEL_LIMIT')
    uniform=rf_met or levels[-1]['refinement_kind']=='uniform_confirmation'
    marked=[] if uniform else mark_bulk(levels[-1]['indicator']['cell_relative_squared'],request['bulk_fraction'])
    if not uniform and not marked:return stop('ZERO_INDICATOR',reason='zero priority is not physical convergence')
    step=Step('uniform') if uniform else Step('marked',tuple(marked),request['minimum_corner_angle_deg'])
    try:
        space=_apply(solution.space,step,maximum);_quality(space,request)
    except ValueError as exc:
        if 'max_triangles' not in str(exc) and 'minimum_corner_angle_deg' not in str(exc):raise
        return stop('REFINEMENT_LIMIT',reason=str(exc),marked_cells=marked)
    from .nested_curved_tracking import MAX_FEATURE_ENTRIES
    if len(space.geometry.points_rz_m)*2*case.modes>MAX_FEATURE_ENTRIES:
        return stop('TRACKING_BUDGET',reason='nested_curved would exceed 8388608 coefficient feature entries',marked_cells=marked)
    current=replace(solution.case,curved_refinement_levels=0,curved_refinement_steps=_history(solution.case)+(step,))
    return dict(status='PAUSED',changes=changes,surface_changes=peak_changes,marked_cells=marked,next_triangles=len(space.geometry.cell_nodes),
        next_refinement_kind='uniform_confirmation' if uniform else 'residual'),Plan(current,solution.source_mesh_data,space)


def _quadrature(solution,request,mode,low):
    high_order=request['quadrature_check_order'];limit=request['quadrature_relative_tolerance']
    # This solution/space has already passed native reconstruction and the low-order
    # indicator validation. Reuse one high-order assembly for both diagnostics.
    u=solution.u[:,mode];u=u/max(abs(u))
    k,m=assemble_curved(solution.space,quadrature_order=high_order)
    kl,ml=float(u@(solution.stiffness@u)),float(u@(solution.mass@u))
    kh,mh=float(u@(k@u)),float(u@(m@u))
    high=[part/kh for part in _components(solution.space,u,float(solution.eigenvalues[mode]),high_order)]
    denominator=math.fsum(sum(high));differences={}
    for key,part in zip(('volume_relative_squared','interior_relative_squared','boundary_relative_squared'),high):
        delta=float(np.sum(abs(np.array(low[key])-part)))
        differences[key]=delta/denominator if denominator>0 else 0. if delta==0 else None
    differences['rayleigh_frequency']=abs(math.sqrt((kh/mh)/(kl/ml))-1)
    differences['mass_form']=abs(mh/ml-1)
    passed=all(v is not None and math.isfinite(v) and v<=limit for v in differences.values())
    return dict(passed=passed,base_order=solution.case.quadrature_order,check_order=high_order,relative_tolerance=limit,
        relative_differences=differences,scope='indicator components and target-field Rayleigh/mass forms at higher quadrature; no physical error bound')


def _surface(solution,mode,q):
    peaks=bound_surface_peaks(solution,mode);electric=magnetic=None
    if q['epk_over_eacc_estimate'] is not None and q['bpk_over_eacc_estimate_mt_per_mv_per_m'] is not None and q['eacc_v_per_m']>0:
        electric=_ratio_interval(peaks['electric_v_per_m']['lower_bound'],peaks['electric_v_per_m']['upper_bound'],q['eacc_v_per_m'])
        magnetic=_ratio_interval(peaks['magnetic_a_per_m']['lower_bound'],peaks['magnetic_a_per_m']['upper_bound'],q['eacc_v_per_m'],factor=Fraction(MU0)*10**9)
    return dict(intervals=dict(zip(PEAKS,(electric,magnetic))),peaks=peaks,geometry_diagnostic=_geometry_assessment(solution.case.curved_contour))


class _VerifiedPrefix:
    """Execution-local reuse; persistent checkpoints never supply trusted state."""
    def __init__(self):
        self.implementation=_implementation_hashes()
        self.request_key=None
        self.runs=[]
        self.sources=[]
        self.levels=[]
        self.solution=None

    def _check_implementation(self):
        if self.implementation!=_implementation_hashes():
            raise RuntimeError('implementation changed during curved adaptive refinement')

    def load(self,request,runs):
        self._check_implementation()
        if self.request_key is not None and self.request_key!=_canonical(request):
            raise ValueError('verified curved prefix request changed')
        if runs[:len(self.runs)]!=self.runs:
            raise ValueError('verified curved prefix ancestry changed')
        if self.sources!=[_snapshot(Path(run)) for run in self.runs]:
            raise ValueError('prior curved adaptive sources changed during execution')
        return deepcopy(self.levels),deepcopy(self.sources),self.solution

    def store(self,request,runs,levels,sources,solution):
        self._check_implementation()
        self.request_key=_canonical(request)
        self.runs=list(runs)
        self.sources=deepcopy(sources)
        self.levels=deepcopy(levels)
        self.solution=solution


def assemble(request,runs,*,_cache=None):
    case=validate_request(request)
    if type(runs) is not list or any(type(p) is not str or not Path(p).is_absolute() for p in runs) or len(set(runs))!=len(runs):
        raise ValueError('level_runs requires distinct absolute native result directories')
    if len(runs)>request['max_levels']:raise ValueError('level_runs exceeds max_levels')
    levels,sources,solution=([],[],None) if _cache is None else _cache.load(request,runs)
    for index in range(len(levels),len(runs)):
        run=runs[index]
        decision,plan=next_plan(case,request,levels,solution)
        if decision['status']!='PAUSED':raise ValueError('curved adaptive refinement continues after a terminal decision')
        source=_snapshot(Path(run));current=read_solution(run)
        if current.case!=plan.case or mesh_digest(current.source_mesh_data)!=mesh_digest(plan.source_mesh):
            raise ValueError('saved curved adaptive Case or source mesh differs from prescribed history')
        a,b=geometry_arrays(plan.space),geometry_arrays(current.space)
        if set(a)!=set(b) or any(not np.array_equal(a[k],b[k]) for k in a):raise ValueError('curved adaptive geometry differs from prescribed refinement')
        pair=None;ids=request['initial_ids'];status='INITIAL'
        if levels:
            pair=build_saved_mode_tracking(dict(schema_version=1,previous_run=runs[index-1],current_run=run,
                previous_ids=levels[-1]['current_mode_ids'],controls=request['controls']))
            report=pair['tracking'];ids=report['current_mode_ids']
            status='PASS' if report['status']=='PASS' and report['individual_ids_complete'] else 'UNVERIFIED'
        mode=ids.index(request['mode_id']) if status!='UNVERIFIED' else None
        q=None if mode is None else parse_json((Path(run)/'results.json').read_text())['modes'][mode]
        indicator=None if mode is None else curved_residual_indicator(current.case,current,mode=mode,quadrature_order=current.case.quadrature_order)
        levels.append(dict(index=index,status=status,marked_cells=decision['marked_cells'],refinement_kind=decision['next_refinement_kind'],
            triangles=len(current.space.geometry.cell_nodes),dofs=len(current.u),quality=_quality(current.space,request),
            current_mode_ids=ids,mode_index=mode,tracking=pair,indicator=indicator,quantities=q,
            quadrature_check=None if mode is None else _quadrature(current,request,mode,indicator),
            surface=None if mode is None else _surface(current,mode,q)))
        sources.append(source);solution=current
    if sources!=[_snapshot(Path(run)) for run in runs]:raise ValueError('curved adaptive sources changed during verification')
    decision,plan=next_plan(case,request,levels,solution);status=decision['status']
    result=dict(schema_version=1,document_type='adaptive_refinement_checkpoint',request=deepcopy(request),level_runs=list(runs),
        sources=sources,levels=levels,decision=decision,status=status,can_resume=status=='PAUSED',physical_error_bound=None,
        surface_status='TARGETS_MET' if status=='TARGETS_MET' else 'UNVERIFIED' if status in ('UNVERIFIED','QUANTITY_UNVERIFIED','QUADRATURE_UNVERIFIED') else 'NOT_CONFIRMED',
        scope='fixed quadratic geometry with verified smooth native joins; nested individual tracking, higher-order integration checks, RF candidate and at least two uniform refinements; consecutive f/RQ/G and continuous discrete peak-ratio interval changes; no physical error bound or geometry-approximation acceptance')
    if _cache is not None:
        # Check again after planning: no changed native source may be published.
        if sources!=[_snapshot(Path(run)) for run in runs]:
            raise ValueError('curved adaptive sources changed during verification')
        _cache.store(request,runs,levels,sources,solution)
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
        index=len(runs);run=directory/f'level-{index+1:03d}'
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
