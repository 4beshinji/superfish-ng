# SPDX-License-Identifier: Apache-2.0
"""Replayable fixed-geometry RF and surface-peak refinement diagnostics."""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import json
import math
from pathlib import Path
from .config import keys
from .constants import MU0
from .curved_corners import classify_curve_joins
from .curved_solution import CurvedSolution
from .mode_tracking_history import replay_mode_history
from .project import parse_json
from .saved import read_solution
from .saved_mode_tracking import _canonical

LIMITS=dict(frequency_hz=1e-4,r_over_q_accelerator_ohm=.005,geometry_factor_ohm=.005,
    epk_over_eacc=.01,bpk_over_eacc_mt_per_mv_per_m=.01)


def _interval_change(previous,current):
    if previous is None or current is None:return None
    if any(not math.isfinite(x) or x<=0 for x in (*previous,*current)):return None
    # Worst relative change over both peak intervals, not just their estimates.
    value=max(abs(Fraction(current[1])/Fraction(previous[0])-1),abs(Fraction(current[0])/Fraction(previous[1])-1))
    return _outward_float(value,upper=True)


def _outward_float(value,*,upper):
    try:result=float(value)
    except OverflowError:return None
    if not math.isfinite(result):return None
    if (Fraction(result)<value if upper else Fraction(result)>value):
        result=math.nextafter(result,math.inf if upper else -math.inf)
    return result if math.isfinite(result) else None


def _ratio_interval(lower,upper,denominator,factor=1.):
    values=[_outward_float(Fraction(v)*Fraction(factor)/Fraction(denominator),upper=side==1)
        for side,v in enumerate((lower,upper))]
    return None if None in values else values


def _evaluate_rows(rows):
    comparisons=[]
    for i in range(1,len(rows)):
        changes={k:_interval_change(rows[i-1]['intervals'][k],rows[i]['intervals'][k]) for k in LIMITS}
        gates={k:v is not None and v<=LIMITS[k] for k,v in changes.items()}
        comparisons.append(dict(previous_row=i-1,current_row=i,relative_change_upper_bounds=changes,gates=gates))
    recent=comparisons[-2:]
    resolved=len(recent)==2 and all(v is not None for c in recent for v in c['relative_change_upper_bounds'].values())
    status='UNVERIFIED' if not resolved else 'TARGETS_MET' if all(all(c['gates'].values()) for c in recent) else 'NOT_CONVERGED'
    return dict(status=status,comparisons=comparisons,acceptance_comparison_indices=list(range(max(0,len(comparisons)-2),len(comparisons))))


def _geometry_assessment(contour):
    joins=classify_curve_joins(contour);tolerance=joins['angle_tolerance_rad'];poles=[];uncertain=False
    for join in joins['joins']:
        category=join['classification']
        if category=='axis_join':
            indices=[(join['incoming_curve_index'],1.),(join['outgoing_curve_index'],0.)]
            walls=[(i,t) for i,t in indices if contour.edge_tags[i]!='axis']
            if not walls:continue  # Internal join of a subdivided axis chain.
            i,t=walls[0];tangent=contour.curves[i].evaluate(t)['tangent_zr']
            smooth=contour.edge_tags[i]=='pec' and abs(float(tangent[0]))<=math.sin(tolerance)
            poles.append(dict(curve_index=i,parameter=t,absolute_axial_tangent_component=abs(float(tangent[0])),orthogonal_to_axis_within_tolerance=smooth))
            uncertain=uncertain or not smooth
        elif category!='tangent_within_tolerance':uncertain=True
    status='SINGULAR_GEOMETRY' if joins['counts']['reentrant_pec_corner'] else 'UNVERIFIED_GEOMETRY' if uncertain else 'SMOOTH_WITHIN_TOLERANCE'
    return dict(status=status,joins=joins,axis_poles=poles,
        scope='native PEC tangents and orthogonal axis poles within an explicit angular tolerance; reentrant corners cannot pass; not an exact regularity proof')


def _target_match(step,mode_id):
    matches=[m for m in step['tracking']['matches'] if mode_id in m['previous_ids']]
    if (step['status']!='PASS' or len(matches)!=1 or matches[0]['kind']!='MODE'
            or matches[0]['previous_ids']!=[mode_id]):
        raise ValueError('mode_id requires a verified individual correspondence at every refinement step')
    return matches[0]


def assess_surface_convergence(history,mode_id):
    """Revalidate a saved history and assess its last two fixed-geometry changes.

    TARGETS_MET is an empirical refinement diagnostic. The approximation of
    the analytic boundary and the physical discretization error remain separate.
    """
    history=replay_mode_history(history)
    if type(mode_id) is not str or not mode_id.strip():raise ValueError('mode_id must be a nonempty individual identity')
    steps=history['steps']
    if len(steps)<2:raise ValueError('surface convergence requires at least three mesh levels')
    if any(s['request']['controls']['mapping']!='curved_same_domain' for s in steps):
        raise ValueError('surface convergence requires curved_same_domain tracking of fixed quadratic geometry')
    matches=[_target_match(s,mode_id) for s in steps]
    runs=[steps[0]['request']['previous_run'],*[s['request']['current_run'] for s in steps]]
    indices=[matches[0]['previous_indices'][0],*[m['current_indices'][0] for m in matches]]
    solutions=[read_solution(Path(run)) for run in runs]
    if any(not isinstance(s,CurvedSolution) for s in solutions):raise ValueError('surface convergence requires native curved P2 solutions')
    first=solutions[0];base=replace(first.case,curved_refinement_levels=0).to_dict()
    levels=[s.case.curved_refinement_levels for s in solutions]
    if any(b<=a for a,b in zip(levels,levels[1:])):raise ValueError('surface convergence requires strictly increasing fixed-geometry refinement levels')
    if any(replace(s.case,curved_refinement_levels=0).to_dict()!=base or s.source_mesh_data!=first.source_mesh_data for s in solutions):
        raise ValueError('surface convergence requires one base Case and source mesh; only fixed-geometry refinement levels may change')
    geometry=_geometry_assessment(first.case.curved_contour);rows=[]
    for run,index,solution in zip(runs,indices,solutions):
        # read_solution verified these RF values against the saved native fields.
        q=parse_json((Path(run)/'results.json').read_text(encoding='utf-8'))['modes'][index-1]
        names=('epk_discrete_lower_bound_v_per_m','epk_discrete_upper_bound_v_per_m',
            'hpk_discrete_lower_bound_a_per_m','hpk_discrete_upper_bound_a_per_m')
        if any(k not in q for k in names):raise ValueError('surface convergence requires saved bounded discrete peaks; resave the native result with the current peak contract')
        intervals={k:[q[k],q[k]] for k in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')}
        electric=magnetic=None
        if q['epk_over_eacc_estimate'] is not None and q['bpk_over_eacc_estimate_mt_per_mv_per_m'] is not None and q['eacc_v_per_m']>0:
            electric=_ratio_interval(*[q[k] for k in names[:2]],q['eacc_v_per_m'])
            magnetic=_ratio_interval(*[q[k] for k in names[2:]],q['eacc_v_per_m'],factor=Fraction(MU0)*10**9)
        intervals.update(epk_over_eacc=electric,bpk_over_eacc_mt_per_mv_per_m=magnetic)
        rows.append(dict(run=run,mode_index=index,refinement_level=solution.case.curved_refinement_levels,
            triangles=len(solution.space.geometry.cell_nodes),degrees_of_freedom=len(solution.u),intervals=intervals))
    diagnostic=_evaluate_rows(rows)
    status=diagnostic['status'] if geometry['status']=='SMOOTH_WITHIN_TOLERANCE' else geometry['status']
    if _canonical(replay_mode_history(history))!=_canonical(history):raise ValueError('surface convergence history sources changed during evaluation')
    return dict(schema_version=1,document_type='surface_convergence_assessment',history=deepcopy(history),mode_id=mode_id,
        status=status,limits=dict(LIMITS),rows=rows,refinement_diagnostic=diagnostic,geometry_diagnostic=geometry,
        geometry_approximation_assessed=False,physical_error_bound=None,
        scope='last two fixed-quadratic-geometry mesh changes of a saved tracked individual mode; f, R/Q, G and bounded peak ratios assessed separately; TARGETS_MET is not a physical-error bound, analytic-geometry acceptance or certification')


def save_surface_convergence(history,mode_id,path):
    result=assess_surface_convergence(history,mode_id)
    with Path(path).open('x',encoding='utf-8') as stream:stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result


def read_surface_convergence(path):
    document=parse_json(Path(path).read_text(encoding='utf-8'))
    fields=('schema_version','document_type','history','mode_id','status','limits','rows','refinement_diagnostic',
        'geometry_diagnostic','geometry_approximation_assessed','physical_error_bound','scope')
    keys(document,fields,fields,'surface convergence assessment')
    result=assess_surface_convergence(document['history'],document['mode_id'])
    if _canonical(document)!=_canonical(result):raise ValueError('surface convergence replay differs from saved data or sources')
    return result
