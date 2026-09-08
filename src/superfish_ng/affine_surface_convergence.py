# SPDX-License-Identifier: Apache-2.0
"""Separate surface convergence assessment of a verified adaptive checkpoint."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
from .config import Case,keys
from .constants import MU0
from .adaptive_refinement import replay_adaptive_refinement
from .affine_saved import read_verified_affine_solution
from .affine_extrema import bound_affine_surface_peaks
from .affine_corners import classify_affine_corners
from .surface_convergence import LIMITS,_ratio_interval,_evaluate_rows
from .saved_mode_tracking import _canonical
from .project import parse_json


def assess_affine_surface_convergence(checkpoint,mode_id):
    checkpoint=replay_adaptive_refinement(checkpoint)
    if type(mode_id) is not str or not mode_id.strip():raise ValueError('mode_id must be a nonempty individual identity')
    levels=checkpoint['levels']
    if len(levels)<3:raise ValueError('affine surface convergence requires at least three verified refinement levels')
    if any(l['status'] not in ('INITIAL','PASS') or l['current_mode_ids'].count(mode_id)!=1 for l in levels):
        raise ValueError('mode_id requires verified individual correspondence at every refinement level')
    case=Case.from_dict(checkpoint['request']['case']);geometry=classify_affine_corners(case);rows=[]
    for level,run in zip(levels,checkpoint['level_runs']):
        index=level['current_mode_ids'].index(mode_id);solution=read_verified_affine_solution(run);q=solution.results['modes'][index]
        peaks=bound_affine_surface_peaks(case,solution,index)
        intervals={k:[q[k],q[k]] for k in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')}
        electric=magnetic=None
        if q['epk_over_eacc_estimate'] is not None and q['bpk_over_eacc_estimate_mt_per_mv_per_m'] is not None and q['eacc_v_per_m']>0:
            electric=_ratio_interval(peaks['electric_v_per_m']['lower_bound'],peaks['electric_v_per_m']['upper_bound'],q['eacc_v_per_m'])
            magnetic=_ratio_interval(peaks['magnetic_a_per_m']['lower_bound'],peaks['magnetic_a_per_m']['upper_bound'],q['eacc_v_per_m'],factor=Fraction(MU0)*10**9)
        intervals.update(epk_over_eacc=electric,bpk_over_eacc_mt_per_mv_per_m=magnetic)
        rows.append(dict(run=run,mode_index=index,refinement_level=level['index'],refinement_kind=level.get('refinement_kind','initial' if level['index']==0 else 'residual'),
            triangles=level['triangles'],degrees_of_freedom=level['dofs'],intervals=intervals,peaks=peaks))
    diagnostic=_evaluate_rows(rows)
    confirmation_required=checkpoint['request']['schema_version']==2
    confirmed=not confirmation_required or all(l['refinement_kind']=='uniform_confirmation' for l in levels[-2:])
    status=diagnostic['status']
    if status=='TARGETS_MET' and not confirmed:status='CONFIRMATION_PENDING'
    if geometry['status']!='NO_REENTRANT_CORNERS':status=geometry['status']
    if _canonical(replay_adaptive_refinement(checkpoint))!=_canonical(checkpoint):raise ValueError('affine surface sources changed during evaluation')
    return dict(schema_version=1,document_type='affine_surface_convergence_assessment',checkpoint=deepcopy(checkpoint),mode_id=mode_id,
        status=status,limits=dict(LIMITS),rows=rows,refinement_diagnostic=diagnostic,geometry_diagnostic=geometry,
        uniform_confirmation_required=confirmation_required,two_uniform_steps_present=confirmed if confirmation_required else None,
        geometry_approximation_assessed=False,physical_error_bound=None,
        scope='last two tracked affine refinement changes; f/RQ/G and continuous discrete peak intervals assessed separately; polygon diagnostics are necessary checks, not a physical regularity or error-bound proof; original adaptive stopping decision is unchanged')


def save_affine_surface_convergence(checkpoint,mode_id,path):
    result=assess_affine_surface_convergence(checkpoint,mode_id)
    with Path(path).open('x',encoding='utf-8') as stream:stream.write(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result


def replay_affine_surface_convergence(document):
    fields=('schema_version','document_type','checkpoint','mode_id','status','limits','rows','refinement_diagnostic','geometry_diagnostic',
        'uniform_confirmation_required','two_uniform_steps_present','geometry_approximation_assessed','physical_error_bound','scope')
    keys(document,fields,fields,'affine surface convergence assessment')
    result=assess_affine_surface_convergence(document['checkpoint'],document['mode_id'])
    if _canonical(document)!=_canonical(result):raise ValueError('affine surface convergence replay differs from saved data or sources')
    return result


def read_affine_surface_convergence(path):return replay_affine_surface_convergence(parse_json(Path(path).read_text(encoding='utf-8')))
