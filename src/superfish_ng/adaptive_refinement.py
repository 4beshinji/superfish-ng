# SPDX-License-Identifier: Apache-2.0
"""Replayable residual-driven affine refinement with tracked RF diagnostics."""
from copy import deepcopy
import json
import math
from pathlib import Path
from .config import Case,keys,integer,positive
from .project import parse_json
from .solver import solve
from .io import save_run
from .jobs import _implementation_hashes
from .mesh import make_mesh
from .mesh_input import mesh_to_dict,mesh_from_dict
from .contour_mesh import contour_mesh_quality
from .affine_saved import read_verified_affine_solution
from .saved_mode_tracking import _snapshot,_canonical,validate_tracking_controls,build_saved_mode_tracking
from .residual_indicator import residual_indicator,mark_bulk
from .marked_refinement import refine_marked_cells
from .adaptive_surface_stopping import QUANTITIES as SURFACE_QUANTITIES,surface_intervals,surface_changes
from .affine_corners import classify_affine_corners

QUANTITIES=('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')


def _request(request):
    fields=('schema_version','case','initial_mesh','initial_ids','mode_id','controls','bulk_fraction','max_levels',
            'max_triangles','minimum_angle_deg','relative_tolerances')
    if isinstance(request,dict) and request.get('schema_version') in (2,3):fields+=('confirmation',)
    if isinstance(request,dict) and request.get('schema_version')==3:fields+=('surface_relative_tolerances',)
    keys(request,fields,fields,'adaptive refinement request');_canonical(request)
    if type(request['schema_version']) is not int or request['schema_version'] not in (1,2,3):raise ValueError('adaptive refinement requires schema_version 1, 2 or 3')
    confirmed=request['schema_version']>=2
    if confirmed and request['confirmation']!='uniform_two_steps':raise ValueError('versions 2 and 3 require explicit uniform_two_steps confirmation')
    case=Case.from_dict(request['case'])
    if case.geometry_order!=1:raise ValueError('adaptive refinement requires straight P1/P2 geometry')
    integer(request['max_levels'],'max_levels',5 if confirmed else 3);integer(request['max_triangles'],'max_triangles')
    for key in ('bulk_fraction','minimum_angle_deg'):positive(request[key],key)
    if request['bulk_fraction']>1 or request['minimum_angle_deg']>=60:raise ValueError('bulk_fraction must be <=1 and minimum_angle_deg <60')
    ids=request['initial_ids']
    if type(ids) is not list or len(ids)!=case.modes or any(type(v) is not str or not v.strip() for v in ids) or len(set(ids))!=len(ids):
        raise ValueError('initial_ids requires distinct nonempty strings for every initial frequency rank')
    if type(request['mode_id']) is not str or request['mode_id'] not in ids:raise ValueError('mode_id must occur in initial_ids')
    if confirmed:
        names=('mapping','minimum_overlap','minimum_assignment_margin','relative_cluster_gap','minimum_relative_singular_value')
        keys(request['controls'],names,names,'uniform-confirmed tracking controls')
        if request['controls']['mapping']!='nested_affine':raise ValueError('versions 2 and 3 require explicit nested_affine tracking')
        validate_tracking_controls(dict(request['controls'],marked_cells=[0]))
    else:
        validate_tracking_controls(request['controls'])
        if request['controls']['mapping']!='same_domain':raise ValueError('adaptive refinement requires explicit same_domain tracking')
    keys(request['relative_tolerances'],QUANTITIES,QUANTITIES,'adaptive relative tolerances')
    for key,value in request['relative_tolerances'].items():positive(value,key)
    if request['schema_version']==3:
        keys(request['surface_relative_tolerances'],SURFACE_QUANTITIES,SURFACE_QUANTITIES,'surface relative tolerances')
        for key,value in request['surface_relative_tolerances'].items():positive(value,key)
        geometry=classify_affine_corners(case)
        if geometry['status']!='NO_REENTRANT_CORNERS':
            raise ValueError('version 3 surface stopping requires an exact polygon without reentrant corners and with verified boundary joins; '+geometry['status']+'; use version 2 with separate surface diagnostics')
    if request['initial_mesh'] is not None:mesh_from_dict(case,request['initial_mesh'])
    return case


def _limits(case,request):
    maximum=request['max_triangles'];angle=request['minimum_angle_deg']
    if case.contour_mesh:
        maximum=min(maximum,case.contour_mesh.max_triangles);angle=max(angle,case.contour_mesh.min_angle_deg)
    return maximum,angle


def _next(case,request,levels,solution):
    peaks_required=request['schema_version']==3;peak_changes=[]
    def stop(status,**data):
        if peaks_required:data['surface_changes']=peak_changes
        return dict(status=status,**data),None
    maximum,angle=_limits(case,request)
    confirmed=request['schema_version']>=2
    if not levels:
        mesh=make_mesh(case) if request['initial_mesh'] is None else mesh_from_dict(case,request['initial_mesh'])
        if len(mesh.triangles)>maximum or contour_mesh_quality(mesh)['min_angle_deg']<angle:
            raise ValueError('initial mesh exceeds max_triangles or fails minimum_angle_deg')
        return dict(status='PAUSED',marked_cells=[],next_triangles=len(mesh.triangles),**({'next_refinement_kind':'initial'} if confirmed else {})),mesh
    if levels[-1]['status']=='UNVERIFIED':return stop('UNVERIFIED',reason='individual mode identities are unresolved')
    changes=[]
    for a,b in zip(levels[-3:],levels[-2:]) if len(levels)>=3 else []:
        row={}
        for key in QUANTITIES:
            x,y=a['quantities'][key],b['quantities'][key]
            if not all(math.isfinite(v) and v>0 for v in (x,y)):return stop('QUANTITY_UNVERIFIED',quantity=key)
            value=abs(y/x-1)
            if not math.isfinite(value):return stop('QUANTITY_UNVERIFIED',quantity=key)
            row[key]=dict(relative_change=value,limit=request['relative_tolerances'][key],passed=value<=request['relative_tolerances'][key])
        changes.append(row)
    if peaks_required:
        peak_changes=surface_changes(levels,request['surface_relative_tolerances'])
        for row in peak_changes:
            for key,item in row.items():
                if item['relative_change_upper_bound'] is None:return stop('QUANTITY_UNVERIFIED',quantity=key,changes=changes)
    peaks_met=not peaks_required or (len(peak_changes)==2 and all(item['passed'] for row in peak_changes for item in row.values()))
    targets_met=len(changes)==2 and all(item['passed'] for row in changes for item in row.values())
    two_uniform=confirmed and len(levels)>=2 and all(row['refinement_kind']=='uniform_confirmation' for row in levels[-2:])
    if targets_met and peaks_met and (not confirmed or two_uniform):
        return stop('TARGETS_MET',changes=changes)
    if len(levels)>=request['max_levels']:return stop('LEVEL_LIMIT',changes=changes)
    uniform=confirmed and (targets_met or levels[-1]['refinement_kind']=='uniform_confirmation')
    marked=list(range(len(solution.mesh.triangles))) if uniform else mark_bulk(levels[-1]['indicator']['cell_relative_squared'],request['bulk_fraction'])
    if not marked:return stop('ZERO_INDICATOR',changes=changes,reason='zero priority does not establish physical convergence')
    try:
        refined=refine_marked_cells(case,solution.mesh,marked,max_triangles=maximum,minimum_angle_deg=angle)
    except ValueError as exc:
        if 'max_triangles' not in str(exc) and 'minimum angle' not in str(exc):raise
        return stop('REFINEMENT_LIMIT',changes=changes,reason=str(exc),marked_cells=marked)
    if confirmed:
        from .nested_affine_tracking import MAX_FEATURE_ENTRIES
        from .high_order import quadratic_space
        dofs=len(quadratic_space(refined.mesh).dof_points) if case.element_order==2 else len(refined.mesh.points)
        if dofs*2*case.modes>MAX_FEATURE_ENTRIES:
            return stop('TRACKING_BUDGET',changes=changes,reason='nested_affine would exceed 8388608 coefficient feature entries',marked_cells=marked)
    elif (len(solution.mesh.triangles)+len(refined.mesh.triangles))*request['controls']['sample_order']**2>262144:
        return stop('TRACKING_BUDGET',changes=changes,reason='same_domain sampling would exceed 262144 points',marked_cells=marked)
    return dict(status='PAUSED',changes=changes,marked_cells=marked,next_triangles=len(refined.mesh.triangles),
        **({'surface_changes':peak_changes} if peaks_required else {}),
        **({'next_refinement_kind':'uniform_confirmation' if uniform else 'residual'} if confirmed else {})),refined.mesh


def _assemble(request,runs):
    case=_request(request)
    if type(runs) is not list or any(type(p) is not str or not Path(p).is_absolute() for p in runs) or len(set(runs))!=len(runs):
        raise ValueError('level_runs requires distinct absolute native result directories')
    if len(runs)>request['max_levels']:raise ValueError('level_runs exceeds max_levels')
    levels=[];sources=[];solution=None
    for index,run in enumerate(runs):
        decision,expected_mesh=_next(case,request,levels,solution)
        if decision['status']!='PAUSED':raise ValueError('adaptive refinement continues after a terminal decision')
        source=_snapshot(Path(run));current=read_verified_affine_solution(run)
        if current.case!=case or _canonical(mesh_to_dict(current.mesh))!=_canonical(mesh_to_dict(expected_mesh)):
            raise ValueError('saved adaptive case or mesh differs from prescribed residual-driven refinement')
        pair=None;ids=request['initial_ids'];status='INITIAL'
        if levels:
            controls=dict(request['controls'],marked_cells=decision['marked_cells']) if request['schema_version']>=2 else request['controls']
            pair=build_saved_mode_tracking(dict(schema_version=1,previous_run=runs[index-1],current_run=run,
                previous_ids=levels[-1]['current_mode_ids'],controls=controls))
            report=pair['tracking'];ids=report['current_mode_ids']
            status='PASS' if report['status']=='PASS' and report['individual_ids_complete'] else 'UNVERIFIED'
        mode=ids.index(request['mode_id']) if status!='UNVERIFIED' else None
        levels.append(dict(index=index,status=status,marked_cells=decision['marked_cells'],triangles=len(current.mesh.triangles),
            dofs=len(current.u),quality=contour_mesh_quality(current.mesh),current_mode_ids=ids,mode_index=mode,tracking=pair,
            indicator=None if mode is None else residual_indicator(case,current,mode=mode),
            quantities=None if mode is None else current.results['modes'][mode]))
        if request['schema_version']>=2:levels[-1]['refinement_kind']=decision['next_refinement_kind']
        if request['schema_version']==3:levels[-1]['surface']=None if mode is None else surface_intervals(case,current,mode)
        sources.append(source);solution=current
    if sources!=[_snapshot(Path(run)) for run in runs]:raise ValueError('adaptive sources changed during verification')
    decision,mesh=_next(case,request,levels,solution)
    result=dict(schema_version=1,document_type='adaptive_refinement_checkpoint',request=deepcopy(request),level_runs=list(runs),
        sources=sources,levels=levels,decision=decision,status=decision['status'],can_resume=decision['status']=='PAUSED',
        physical_error_bound=None,surface_status='UNASSESSED',
        scope='fixed affine TM geometry; residual-driven refinement with sampled individual mode tracking and two consecutive f/RQ/G differences; no physical error bound, peak or geometry-approximation acceptance')
    if request['schema_version']>=2:
        result['scope']='fixed affine TM geometry; nested mass-inner-product individual tracking, local candidate followed by at least two uniform refinements and consecutive f/RQ/G differences; no physical error bound, peak or geometry-approximation acceptance'
    if request['schema_version']==3:
        result['surface_status']='TARGETS_MET' if result['status']=='TARGETS_MET' else 'UNVERIFIED' if result['status'] in ('UNVERIFIED','QUANTITY_UNVERIFIED') else 'NOT_CONFIRMED'
        result['scope']='fixed exact affine polygon with verified corner prerequisites; nested individual tracking; RF candidate followed by at least two uniform refinements; consecutive f/RQ/G changes and continuous discrete Epk/Eacc and Bpk/Eacc interval changes; no physical error bound or geometry-approximation acceptance'
    return result,mesh


def replay_adaptive_refinement(document):
    fields=('schema_version','document_type','request','level_runs','sources','levels','decision','status','can_resume',
            'physical_error_bound','surface_status','scope')
    keys(document,fields,fields,'adaptive refinement checkpoint')
    expected,_=_assemble(document['request'],document['level_runs'])
    if _canonical(expected)!=_canonical(document):raise ValueError('adaptive checkpoint replay differs from saved decisions or sources')
    return expected


def read_adaptive_refinement(path):return replay_adaptive_refinement(parse_json(Path(path).read_text(encoding='utf-8')))


def execute_adaptive_refinement(request,directory,*,max_new_levels=None,checkpoint=None):
    request=deepcopy(request);case=_request(request)
    if max_new_levels is not None:integer(max_new_levels,'max_new_levels')
    previous,mesh=_assemble(request,[])
    if checkpoint is not None:
        previous=replay_adaptive_refinement(checkpoint)
        if _canonical(previous['request'])!=_canonical(request):raise ValueError('resume request differs from checkpoint')
        if not previous['can_resume']:raise ValueError('only PAUSED adaptive refinement can resume')
        _,mesh=_assemble(request,previous['level_runs'])
    implementation=_implementation_hashes();runs=list(previous['level_runs'])
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=False);count=0
    while previous['can_resume'] and (max_new_levels is None or count<max_new_levels):
        index=len(runs);run=directory/f'level-{index+1:03d}'
        try:
            solution=solve(case,mesh_data=mesh_to_dict(mesh));save_run(case,solution,run)
            result,next_mesh=_assemble(request,runs+[str(run)])
            if result['sources'][:len(runs)]!=previous['sources']:raise ValueError('prior adaptive sources changed during execution')
            if implementation!=_implementation_hashes():raise RuntimeError('implementation changed during adaptive refinement')
        except Exception as exc:
            failure=dict(status='FAILED',level_index=index,run=str(run),error_type=type(exc).__name__,error=str(exc),preceding_level_runs=runs)
            with (directory/f'failure-{index+1:03d}.json').open('x') as stream:json.dump(failure,stream,indent=2,allow_nan=False)
            raise
        with (directory/f'checkpoint-{index+1:03d}.json').open('x') as stream:stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
        previous=result;mesh=next_mesh;runs.append(str(run));count+=1
    return previous
