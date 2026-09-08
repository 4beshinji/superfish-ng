# SPDX-License-Identifier: Apache-2.0
"""Replayable continuous discrete peak diagnostics for native RF results."""
from fractions import Fraction
import json
from pathlib import Path
from .config import Case,keys,integer
from .constants import MU0
from .project import parse_json
from .saved_mode_tracking import _snapshot,_canonical
from .affine_saved import read_verified_affine_solution
from .affine_extrema import bound_affine_surface_peaks
from .affine_corners import classify_affine_corners
from .saved import read_solution
from .curved_extrema import bound_surface_peaks
from .surface_convergence import _ratio_interval,_geometry_assessment


def assess_rf_peaks(run,*,mode=0):
    run=Path(run).resolve();source=_snapshot(run);case=Case.load(run/'case.json')
    integer(mode,'mode',0)
    if mode>=case.modes:raise ValueError('mode must be an available zero-based frequency rank')
    controls=dict(relative_tolerance=1e-6,max_boxes_per_edge=10000)
    if case.geometry_order==1:
        solution=read_verified_affine_solution(run)
        peaks=bound_affine_surface_peaks(case,solution,mode,**controls)
        geometry=classify_affine_corners(case)
    else:
        solution=read_solution(run)
        peaks=bound_surface_peaks(solution,mode,**controls)
        geometry=_geometry_assessment(solution.case.curved_contour)
    result=parse_json((run/'results.json').read_text());q=result['modes'][mode]
    electric=[peaks['electric_v_per_m'][k] for k in ('lower_bound','upper_bound')]
    magnetic=[peaks['magnetic_a_per_m'][k] for k in ('lower_bound','upper_bound')]
    ratio_rf=q
    if case.geometry_order==2 and 'epk_over_eacc_estimate' not in q:
        # Historical native curved RF omitted peaks, not the accelerating field.
        # Reuse the RF kernel's voltage-significance rule without altering saved RF.
        from .curved_rf import quantities_curved
        ratio_rf=quantities_curved(solution,mode)
    e_ratio=b_ratio=None
    if ratio_rf['epk_over_eacc_estimate'] is not None and ratio_rf['bpk_over_eacc_estimate_mt_per_mv_per_m'] is not None and q['eacc_v_per_m']>0:
        e_ratio=_ratio_interval(*electric,q['eacc_v_per_m'])
        b_ratio=_ratio_interval(*magnetic,q['eacc_v_per_m'],factor=Fraction(MU0)*10**9)
    intervals=dict(epk_v_per_m=electric,hpk_a_per_m=magnetic,bpk_t=_ratio_interval(*magnetic,1.,factor=Fraction(MU0)),
                   epk_over_eacc=e_ratio,bpk_over_eacc_mt_per_mv_per_m=b_ratio)
    if source!=_snapshot(run):raise ValueError('RF peak sources changed during evaluation')
    return dict(schema_version=1,document_type='rf_discrete_surface_peak_assessment',run=str(run),mode_index=mode,
        case_name=case.name,element_order=case.element_order,geometry_order=case.geometry_order,source=source,controls=controls,
        status='DISCRETE_BOUNDS_ONLY',peaks=peaks,intervals=intervals,rf=q,conventions=result['conventions'],geometry_diagnostic=geometry,
        mesh_convergence='UNASSESSED',geometry_approximation_assessed=False,physical_error_bound=None,
        scope='single native RF result; frequency rank is not a persistent mode identity; continuous discrete PEC peak enclosures, not physical peak convergence or a physical error bound; original RF estimates and normalization are preserved')


def save_rf_peaks(run,path,**options):
    result=assess_rf_peaks(run,**options)
    with Path(path).open('x',encoding='utf-8') as stream:stream.write(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    return result


def replay_rf_peaks(document):
    fields=('schema_version','document_type','run','mode_index','case_name','element_order','geometry_order','source','controls',
            'status','peaks','intervals','rf','conventions','geometry_diagnostic','mesh_convergence','geometry_approximation_assessed','physical_error_bound','scope')
    keys(document,fields,fields,'RF discrete peak assessment')
    result=assess_rf_peaks(document['run'],mode=document['mode_index'])
    if _canonical(result)!=_canonical(document):raise ValueError('RF peak replay differs from saved data or sources')
    return result


def read_rf_peaks(path):return replay_rf_peaks(parse_json(Path(path).read_text(encoding='utf-8')))
