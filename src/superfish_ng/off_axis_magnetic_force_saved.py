# SPDX-License-Identifier: Apache-2.0
"""Source-bound full-ring axial-force and optional actual-FEM virtual-work reports."""
import hashlib,os,tempfile
from pathlib import Path
import numpy as np
from .config import keys
from .bh_curve import _real_array
from .project import parse_json
from .coaxial_saved import _json
from .off_axis_magnetostatic_saved import _snapshot,read_off_axis_magnetostatic_run
from .planar_magnetic_multipole_saved import _canonical,_report_bytes
from .off_axis_magnetic_force import off_axis_magnetic_force,off_axis_magnetic_virtual_work


def axial_force_request(data):
    names=['format','schema_version','body_region_ids','weights','virtual_work'];keys(data,names,names,'off-axis magnetic force request')
    if data['format']!='superfish_ng_off_axis_magnetic_force_request' or type(data['schema_version']) is not int or data['schema_version']!=1:raise ValueError('unsupported off-axis magnetic force request format/version')
    body=data['body_region_ids']
    if type(body) is not list or not body or any(type(v) is not str for v in body) or len(set(body))!=len(body):raise ValueError('axial-force body_region_ids requires a nonempty distinct JSON string array')
    if type(data['weights']) is not list:raise ValueError('axial-force weights require a JSON array')
    w=_real_array(data['weights'],'axial-force P1 weights')
    if w.ndim!=1 or not len(w) or np.any(w<0.) or np.any(w>1.):raise ValueError('axial-force weights must be a nonempty finite one-dimensional array in [0,1]')
    virtual=data['virtual_work'];steps=None
    if virtual is not None:
        keys(virtual,['translation_steps_m'],['translation_steps_m'],'axial-force virtual_work')
        if type(virtual['translation_steps_m']) is not list:raise ValueError('axial translation_steps_m requires a JSON array')
        values=_real_array(virtual['translation_steps_m'],'axial translation_steps_m')
        if values.ndim!=1 or not 2<=len(values)<=8 or np.any(values<=0.) or np.any(values[1:]>=values[:-1]):raise ValueError('axial virtual work requires 2..8 strictly decreasing positive finite steps [m]')
        steps=dict(translation_steps_m=values.tolist())
    return dict(format=data['format'],schema_version=1,body_region_ids=list(body),weights=w.tolist(),virtual_work=steps)


def _outside(run,path):
    if path.resolve().is_relative_to(run.resolve()):raise ValueError('axial-force report must be outside its source native directory')


def _regular_report(path):
    try:return _report_bytes(path)
    except ValueError as exc:raise ValueError(str(exc).replace('multipole','axial force')) from exc


def _compute(run,request):
    raw=_snapshot(run);solution=read_off_axis_magnetostatic_run(run);body=request['body_region_ids'];weights=request['weights'];force=off_axis_magnetic_force(solution,body,weights);work=None;comparison=None
    if request['virtual_work'] is not None:
        work=off_axis_magnetic_virtual_work(solution.case,body,weights,**request['virtual_work']);comparison=[dict(step_m=row['step_m'],stress_force_z_n=force['force_z_n'],virtual_force_z_n=row['negative_potential_derivative_n'],difference_n=row['negative_potential_derivative_n']-force['force_z_n']) for row in work['records']]
    result=dict(format='superfish_ng_off_axis_magnetic_force_report',schema_version=1,request=request,source_native_sha256={name:hashlib.sha256(value).hexdigest() for name,value in sorted(raw.items())},force=force,virtual_work=work,stress_virtual_work_comparison=comparison,
        interpretation='Verified positive-radius linear scalar P1/P2 original FEM source and vacuum P1 weights; full-ring axial force [N]. Optional actual +/- z-displacement work keeps radial positions, exterior boundaries and integrated azimuthal currents fixed, retaining full Cases and stationary potentials [J]. Null means work was not performed; differences are not a continuum accuracy certificate. Explicit unchanged five-file source native required; no planar N/m conversion, radial net force, meridional torque, axis-connected/BH/recoil/curved source or GUI.')
    if _snapshot(run)!=raw:raise ValueError('axial-force source native changed during analysis')
    return result,raw


def export_off_axis_magnetic_force(run,out,request):
    run,out=Path(run),Path(out);_outside(run,out);validated=axial_force_request(request);result,raw=_compute(run,validated)
    if axial_force_request(request)!=validated:raise ValueError('axial-force request changed during analysis')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.axial-force-report-',dir=out.parent) as temporary:
        staged=Path(temporary)/'report.json';_json(staged,result)
        if _snapshot(run)!=raw:raise ValueError('axial-force source native changed during publication')
        os.link(staged,out)
    return result


def replay_off_axis_magnetic_force(run,report):
    run,report=Path(run),Path(report);_outside(run,report);raw_report=_regular_report(report);stored=parse_json(raw_report.decode('utf-8'));names=['format','schema_version','request','source_native_sha256','force','virtual_work','stress_virtual_work_comparison','interpretation'];keys(stored,names,names,'off-axis magnetic force report')
    if stored['format']!='superfish_ng_off_axis_magnetic_force_report' or type(stored['schema_version']) is not int or stored['schema_version']!=1:raise ValueError('unsupported off-axis magnetic force report format/version')
    request=axial_force_request(stored['request']);raw=_snapshot(run)
    if stored['source_native_sha256']!={name:hashlib.sha256(value).hexdigest() for name,value in sorted(raw.items())}:raise ValueError('axial-force source native hashes disagree')
    expected,verified_raw=_compute(run,request)
    if verified_raw!=raw or _snapshot(run)!=raw:raise ValueError('axial-force source native changed during replay')
    if _canonical(stored)!=_canonical(expected):raise ValueError('saved axial-force body, weights, fields, units, quadrature, displaced Case or potential disagrees with actual FEM replay')
    if _regular_report(report)!=raw_report:raise ValueError('axial-force report changed during replay')
    return expected
