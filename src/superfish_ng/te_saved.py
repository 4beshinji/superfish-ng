# SPDX-License-Identifier: Apache-2.0
"""Explicit TE native format: electric coefficients, labels, and FEM replay."""
import csv,hashlib,json,math,os,platform,tempfile
import scipy
from . import __version__
from pathlib import Path
import numpy as np
from .config import Case,keys
from .constants import EPS0,TAU,C0
from .completion import digest
from .project import parse_json
from .saved_mode_tracking import _canonical
from .te import TESolution,TEFieldSampler,validate_te_case,te_matrices,te_quantities
from .mesh_input import mesh_from_dict


def _conventions(curved=False):
    return dict(time_phasor='exp(+i*omega*t)',electric_phasor='real peak',magnetic_phasor='+i times quadrature amplitude',
                stored_energy='time averaged total electric plus magnetic energy in J',
                accelerating_quantities='not applicable; Ez is identically zero',surface_loss='PEC boundary only; symmetry planes excluded',
                vtk_sampling=('one mapped cell-centre value per quadratic triangle; no smoothing or peak certificate' if curved else 'one cell-centre value per original triangle; no smoothing or peak certificate'))


def _finite_number(value):
    try:return type(value) in (int,float) and math.isfinite(value)
    except OverflowError:return False


def _json(path,data):
    with Path(path).open('x',encoding='utf-8') as stream:json.dump(data,stream,indent=2,allow_nan=False)


def _names(case):
    return ({'geometry.npz'} if case.geometry_order==2 else set()) | {'case.json','mesh.json','fields.npz','results.json','modes.csv',*(f'axis_{i:03d}.csv' for i in range(1,case.modes+1)),*(f'mode_{i:03d}.vtk' for i in range(1,case.modes+1))}


def _vtk(path,solution,mode):
    curved=solution.case.geometry_order==2
    points=solution.space.geometry.points_rz_m if curved else solution.mesh.points
    cells=solution.space.geometry.cell_nodes if curved else solution.mesh.triangles
    fields=solution.fields_in_cells(np.arange(len(cells)),np.tile([1/3]*3,(len(cells),1)),mode)
    with path.open('x',encoding='ascii') as f:
        f.write('# vtk DataFile Version 3.0\nSuperfish-NG TE: x=r y=z, E real and H=+i quadrature\nASCII\nDATASET UNSTRUCTURED_GRID\n')
        f.write(f'POINTS {len(points)} double\n');np.savetxt(f,np.column_stack((points,np.zeros(len(points)))),fmt='%.16e')
        f.write(f'CELLS {len(cells)} {(cells.shape[1]+1)*len(cells)}\n');np.savetxt(f,np.column_stack((np.full(len(cells),cells.shape[1]),cells)),fmt='%d')
        f.write(f'CELL_TYPES {len(cells)}\n');np.savetxt(f,np.full(len(cells),22 if curved else 5),fmt='%d')
        f.write(f'CELL_DATA {len(cells)}\n')
        for name,values in fields.items():
            f.write(f'SCALARS {name} double 1\nLOOKUP_TABLE default\n');np.savetxt(f,values,fmt='%.16e')


def _geometry_arrays(space):
    geometry=space.geometry
    return dict(points_rz_m=geometry.points_rz_m,cell_nodes=geometry.cell_nodes,
                boundary_nodes=geometry.boundary_nodes,boundary_tags=space.boundary_tags)


def save_te_run(case,solution,directory):
    validate_te_case(case)
    if not isinstance(solution,TESolution) or solution.case!=case:raise ValueError('TE case and solution disagree')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='.te-staging-',dir=directory) as temporary:
        stage=Path(temporary);modes=[te_quantities(solution,i) for i in range(case.modes)]
        result=dict(schema_version=3 if case.geometry_order==2 else 2,physics='axisymmetric_m0_te',case=case.to_dict(),
            software=dict(name='Superfish-NG',version=__version__),
            environment=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,platform=platform.platform()),
            field_space=dict(element_order=case.element_order,geometry_order=case.geometry_order,basis='Lagrange v=Ephi/r',coefficient_unit='V/m^2'),
            conventions=_conventions(case.geometry_order==2),modes=modes,
            normalization_j=case.normalization_j,algebraic_residuals=solution.residuals.tolist(),orthogonality_error=solution.orthogonality_error)
        _json(stage/'case.json',case.to_dict());_json(stage/'mesh.json',solution.source_mesh_data);_json(stage/'results.json',result)
        if case.geometry_order==2:
            np.savez_compressed(stage/'geometry.npz',**_geometry_arrays(solution.space))
        np.savez_compressed(stage/'fields.npz',coefficients_v_per_m2=solution.coefficients_v_per_m2,frequencies_hz=solution.frequencies_hz)
        with (stage/'modes.csv').open('x',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(modes[0]));writer.writeheader();writer.writerows(modes)
        sampler=TEFieldSampler(solution)
        axis=(solution.space.geometry.points_rz_m[solution.space.axis_dofs] if case.geometry_order==2 else solution.mesh.points[solution.mesh.axis_nodes])
        axis=axis[np.argsort(axis[:,1])]
        for i in range(case.modes):
            fields=sampler.evaluate(axis,i)
            with (stage/f'axis_{i+1:03d}.csv').open('x',newline='') as f:
                writer=csv.writer(f);writer.writerow(['z_m','Ephi_V_per_m','Hr_quadrature_A_per_m','Hz_quadrature_A_per_m'])
                writer.writerows(zip(axis[:,1],fields['Ephi_V_per_m'],fields['Hr_quadrature_A_per_m'],fields['Hz_quadrature_A_per_m']))
            _vtk(stage/f'mode_{i+1:03d}.vtk',solution,i)
        names=_names(case)
        for name in sorted(names):os.link(stage/name,directory/name)
        _json(stage/'te_complete.json',dict(te_completion_version=1,files={name:digest(directory/name) for name in sorted(names)}))
        os.link(stage/'te_complete.json',directory/'te_complete.json')
    return result


def read_te_run(directory):
    directory=Path(directory)
    if directory.is_symlink() or not (directory/'te_complete.json').is_file() or (directory/'te_complete.json').is_symlink():
        raise ValueError('TE result is incomplete or linked')
    raw=(directory/'te_complete.json').read_bytes();marker=parse_json(raw.decode('utf-8'));keys(marker,('te_completion_version','files'),('te_completion_version','files'),'TE completion')
    if type(marker['te_completion_version']) is not int or marker['te_completion_version']!=1 or not isinstance(marker['files'],dict):raise ValueError('invalid TE completion version or files')
    def snapshot():
        for name,expected in marker['files'].items():
            if Path(name).name!=name or not isinstance(expected,str):raise ValueError('invalid TE completion file entry')
            p=directory/name
            if p.is_symlink() or not p.is_file() or digest(p)!=expected:raise ValueError('TE output bytes differ from completion manifest: '+name)
        return digest(directory/'te_complete.json')
    before=hashlib.sha256(raw).hexdigest()
    if snapshot()!=before:raise ValueError('TE completion changed before verification')
    case=Case.load(directory/'case.json');validate_te_case(case)
    if set(marker['files'])!=_names(case):raise ValueError('TE completion must contain exactly the required files')
    result=parse_json((directory/'results.json').read_text())
    names=('software','environment','schema_version','physics','case','field_space','conventions','modes','normalization_j','algebraic_residuals','orthogonality_error')
    keys(result,names,names,'TE results')
    for name,fields in (('software',('name','version')),('environment',('python','numpy','scipy','platform'))):
        keys(result[name],fields,fields,'TE '+name)
        if any(type(value) is not str or not value for value in result[name].values()):raise ValueError('TE software/environment values must be nonempty strings')
    if result['software']['name']!='Superfish-NG':raise ValueError('unknown TE producer')
    if result['conventions']!=_conventions(case.geometry_order==2):raise ValueError('TE phasor/energy conventions disagree')
    if type(result.get('schema_version')) is not int or result['schema_version']!=(3 if case.geometry_order==2 else 2) or result.get('physics')!='axisymmetric_m0_te' or Case.from_dict(result.get('case'))!=case:raise ValueError('TE result physics, version or case disagrees')
    mesh_data=parse_json((directory/'mesh.json').read_text());mesh=mesh_from_dict(case,mesh_data);space,k,m,free=te_matrices(case,mesh)
    if case.geometry_order==2:
        with np.load(directory/'geometry.npz',allow_pickle=False) as saved_geometry:
            expected_geometry=_geometry_arrays(space)
            if set(saved_geometry.files)!=set(expected_geometry):raise ValueError('TE saved curved geometry arrays disagree')
            for name,expected in expected_geometry.items():
                actual=saved_geometry[name]
                if actual.dtype!=expected.dtype or not np.array_equal(actual,expected):raise ValueError('TE saved curved geometry differs from reconstruction: '+name)
    with np.load(directory/'fields.npz',allow_pickle=False) as data:
        if set(data.files)!={'coefficients_v_per_m2','frequencies_hz'}:raise ValueError('TE requires electric coefficients and frequencies only')
        v=data['coefficients_v_per_m2'];f=data['frequencies_hz']
    if v.dtype.kind!='f' or f.dtype.kind!='f' or v.shape!=(k.shape[0],case.modes) or f.shape!=(case.modes,) or not np.isfinite(v).all() or not np.isfinite(f).all() or np.any(f<=0) or np.any(np.diff(f)<0):raise ValueError('invalid TE saved arrays')
    constrained=np.setdiff1d(np.arange(len(v)),free)
    if np.any(v[constrained]!=0):raise ValueError('TE essential electric-wall coefficients must be zero')
    lam=(TAU*f/C0)**2;res=[]
    for i,value in enumerate(lam):
        kv,mv=(k@v[:,i])[free],(m@v[:,i])[free]
        res.append(np.linalg.norm(kv-value*mv)/(np.linalg.norm(kv)+value*np.linalg.norm(mv)))
    orth=float(np.max(abs(v.T@(m@v)*(EPS0*np.pi/case.normalization_j)-np.eye(case.modes))))
    if not np.isfinite(res).all() or max(res)>1e-7 or orth>1e-8:raise ValueError('TE saved FEM residual or normalization/orthogonality failed')
    reported=np.asarray(result['algebraic_residuals']);reported_orth=result['orthogonality_error']
    if reported.shape!=(case.modes,) or reported.dtype.kind not in 'fi' or not np.isfinite(reported).all() or not np.allclose(reported,res,rtol=0,atol=1e-10):raise ValueError('TE reported residuals disagree')
    if type(reported_orth) not in (int,float) or not np.isfinite(reported_orth) or abs(reported_orth-orth)>1e-10:raise ValueError('TE reported orthogonality disagrees')
    sol=TESolution(case,mesh,space,k,m,lam,f,v,np.asarray(res),orth,mesh_data)
    expected_space=dict(element_order=case.element_order,geometry_order=case.geometry_order,basis='Lagrange v=Ephi/r',coefficient_unit='V/m^2')
    if _canonical(result.get('field_space'))!=_canonical(expected_space) or type(result.get('normalization_j')) not in (int,float) or result.get('normalization_j')!=case.normalization_j:raise ValueError('TE field metadata disagrees')
    modes=[te_quantities(sol,i) for i in range(case.modes)]
    if type(result['modes']) is not list or len(result['modes'])!=len(modes):raise ValueError('TE saved mode count disagrees')
    for saved,expected in zip(result['modes'],modes):
        keys(saved,expected,expected,'TE mode quantities')
        for key,value in expected.items():
            candidate=saved[key]
            if key=='mode_index':ok=type(candidate) is int and candidate==value
            elif value is None or isinstance(value,str):ok=candidate==value
            else:ok=_finite_number(candidate) and math.isclose(candidate,value,rel_tol=1e-10,abs_tol=0.)
            if not ok:raise ValueError('TE RF quantities differ from saved field reconstruction: '+key)
    if snapshot()!=before:raise ValueError('TE completion changed during verification')
    return sol
