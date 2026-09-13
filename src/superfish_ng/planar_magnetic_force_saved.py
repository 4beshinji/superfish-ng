# SPDX-License-Identifier: Apache-2.0
"""Source-bound Maxwell force and optional actual-FEM virtual-work reports."""
import hashlib,os,tempfile
from pathlib import Path
import numpy as np
from .config import keys
from .bh_curve import _real_array
from .project import parse_json
from .coaxial_saved import _json
from .planar_magnetostatic_saved import _snapshot,read_planar_magnetostatic_run
from .planar_magnetic_multipole_saved import _canonical,_report_bytes
from .planar_magnetic_force import planar_magnetic_force,planar_magnetic_virtual_work
from .planar_bh_saved import read_planar_bh_run
from .planar_recoil_saved import read_planar_recoil_run
from .planar_magnetic_material_virtual_work import material_planar_magnetic_virtual_work,PlanarMagneticVirtualWorkFailure


def magnetic_force_request(data):
    names=['format','schema_version','body_region_ids','weights','origin_xy_m','virtual_work'];keys(data,names,names,'planar magnetic force request')
    if data['format']!='superfish_ng_planar_magnetic_force_request' or type(data['schema_version']) is not int or data['schema_version']!=1:raise ValueError('unsupported planar magnetic force request format/version')
    body=data['body_region_ids']
    if type(body) is not list or not body or any(type(v) is not str for v in body) or len(set(body))!=len(body):raise ValueError('force request body_region_ids must be a nonempty distinct JSON string array')
    if type(data['weights']) is not list or type(data['origin_xy_m']) is not list:raise ValueError('force weights and origin require explicit JSON arrays')
    w=_real_array(data['weights'],'force weights');origin=_real_array(data['origin_xy_m'],'force torque origin [m]')
    if w.ndim!=1 or not len(w) or np.any(w<0.) or np.any(w>1.) or origin.shape!=(2,):raise ValueError('force requires one-dimensional weights in [0,1] and [x_m,y_m] origin')
    virtual=data['virtual_work'];steps=None
    if virtual is not None:
        names=['translation_steps_m','rotation_steps_rad'];keys(virtual,names,names,'force virtual_work');steps={}
        for name in names:
            if type(virtual[name]) is not list:raise ValueError('virtual_work '+name+' requires a JSON array')
            values=_real_array(virtual[name],name)
            if values.ndim!=1 or not 2<=len(values)<=8 or np.any(values<=0.) or np.any(values[1:]>=values[:-1]):raise ValueError('virtual_work '+name+' requires 2..8 strictly decreasing positive finite steps')
            steps[name]=values.tolist()
    return dict(format=data['format'],schema_version=1,body_region_ids=list(body),weights=w.tolist(),origin_xy_m=origin.tolist(),virtual_work=steps)


def _outside(run,path):
    if path.resolve().is_relative_to(run.resolve()):raise ValueError('magnetic force report must be outside its source native directory')


def _regular_report(path):
    try:return _report_bytes(path)
    except ValueError as exc:raise ValueError(str(exc).replace('multipole','magnetic force')) from exc


def _compute(run,request):
    raw=_snapshot(run);manifest=parse_json(raw['manifest.json'].decode('utf-8'))
    readers={'superfish_ng_planar_magnetostatic_manifest':read_planar_magnetostatic_run,'superfish_ng_planar_bh_manifest':read_planar_bh_run,'superfish_ng_planar_recoil_manifest':read_planar_recoil_run}
    if not isinstance(manifest,dict) or type(manifest.get('format')) is not str or manifest['format'] not in readers:raise ValueError('magnetic force source requires a successful planar linear, B-H or recoil native manifest')
    source_format=manifest['format'];extended=source_format!='superfish_ng_planar_magnetostatic_manifest';solution=readers[source_format](run);body=request['body_region_ids'];weights=request['weights'];origin=request['origin_xy_m'];force=planar_magnetic_force(solution,body,weights,origin);work=None;comparison=None
    if request['virtual_work'] is not None:
        if extended:
            try:work=material_planar_magnetic_virtual_work(solution.case,body,weights,origin,**request['virtual_work'])
            except PlanarMagneticVirtualWorkFailure as exc:work=exc.report
        else:work=planar_magnetic_virtual_work(solution.case,body,weights,origin,**request['virtual_work'])
        comparison=[]
        quantities=dict(x=('force_xy_n_per_m',0),y=('force_xy_n_per_m',1),rotation=('nodal_rotation_stress_torque_z_nm_per_m',None))
        for row in work['records']:
            name,index=quantities[row['kind']];stress=force[name] if index is None else force[name][index]
            derivative=row['negative_potential_derivative']
            comparison.append(dict(kind=row['kind'],step=row['step'],stress_quantity=name,component_index=index,stress_value=stress,virtual_work_value=derivative,difference=None if derivative is None else derivative-stress,unit=row['unit']))
    result=dict(format='superfish_ng_planar_magnetic_force_report',schema_version=1,request=request,source_native_sha256={name:hashlib.sha256(value).hexdigest() for name,value in sorted(raw.items())},force=force,virtual_work=work,stress_virtual_work_comparison=comparison,
        interpretation='Original verified linear planar FEM source, body and vacuum transition; force [N/m], scalar-weight torque and distinct nodal-rotation stress torque [N m/m]. Optional virtual work uses actual nodal displacements and fixed exterior/source currents; raw differences do not certify continuum accuracy. Explicit unchanged source native required for replay; no implicit length, RF factor, material/axisymmetric force extension or GUI.')
    if extended:
        result.update(schema_version=2,status='virtual_work_failed' if work is not None and work['status']=='failed' else 'complete',source_native_manifest_format=source_format,source_physics=solution.case.to_dict()['physics'],
            interpretation='Original verified planar B-H/recoil FEM source and declared vacuum transition; force [N/m], weighted and nodal stress torques [N m/m]. Explicit null omits material virtual work. Requested actual displacements co-rotate body tensors/remanence and retain true constitutive potentials, source/boundary work and Newton histories. A failed pair has null derivative/comparison while completed trials and the actual failure remain saved; workflow status is not continuum accuracy certification. Explicit unchanged five-file source required; no implicit length, RF factor, axisymmetry or GUI.')
    if _snapshot(run)!=raw:raise ValueError('magnetic force source native changed during analysis')
    return result,raw


def export_planar_magnetic_force(run,out,request):
    run,out=Path(run),Path(out);_outside(run,out);validated=magnetic_force_request(request);result,raw=_compute(run,validated)
    if magnetic_force_request(request)!=validated:raise ValueError('magnetic force request changed during analysis')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.planar-force-report-',dir=out.parent) as temporary:
        staged=Path(temporary)/'report.json';_json(staged,result)
        if _snapshot(run)!=raw:raise ValueError('magnetic force source native changed during publication')
        os.link(staged,out)
    return result


def replay_planar_magnetic_force(run,report):
    run,report=Path(run),Path(report);_outside(run,report);raw_report=_regular_report(report);stored=parse_json(raw_report.decode('utf-8'));names=['format','schema_version','request','source_native_sha256','force','virtual_work','stress_virtual_work_comparison','interpretation']
    if isinstance(stored,dict) and type(stored.get('schema_version')) is int and stored['schema_version']==2:names+=['status','source_native_manifest_format','source_physics']
    keys(stored,names,names,'magnetic force report')
    if stored['format']!='superfish_ng_planar_magnetic_force_report' or type(stored['schema_version']) is not int or stored['schema_version'] not in (1,2):raise ValueError('unsupported planar magnetic force report format/version')
    request=magnetic_force_request(stored['request']);raw=_snapshot(run)
    if stored['source_native_sha256']!={name:hashlib.sha256(value).hexdigest() for name,value in sorted(raw.items())}:raise ValueError('magnetic force report source native hashes disagree')
    expected,verified_raw=_compute(run,request)
    if verified_raw!=raw or _snapshot(run)!=raw:raise ValueError('magnetic force source native changed during replay')
    if _canonical(stored)!=_canonical(expected):raise ValueError('saved magnetic force body, weights, fields, stress, displaced Case, potential, units or diagnostics disagree with actual FEM replay')
    if _regular_report(report)!=raw_report:raise ValueError('magnetic force report changed during replay')
    return expected
