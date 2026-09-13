# SPDX-License-Identifier: Apache-2.0
"""Verified off-axis nonlinear B-H success and failure publication and replay."""
import copy,hashlib,json,os,tempfile
from pathlib import Path
import numpy as np
from .config import keys
from .project import parse_json
from .coaxial_saved import FILES,_json,_arrays,_snapshot as _file_snapshot
from .off_axis_bh import OffAxisBHCase,OffAxisBHSolution,solve_off_axis_bh,off_axis_bh_quantities
from .off_axis_bh_fem import off_axis_bh_state
from .nonlinear_magnetic import MagneticNonlinearFailure

FAILURE_FILES={'case.json','failure.json'}


def _same_json(a,b):
    return json.dumps(a,sort_keys=True,allow_nan=False)==json.dumps(b,sort_keys=True,allow_nan=False)


def _snapshot(directory):
    directory=Path(directory)
    if directory.is_symlink():raise ValueError('off-axis B-H native directory must not be a symbolic link')
    try:return _file_snapshot(directory)
    except ValueError as exc:raise ValueError(str(exc).replace('coaxial','off-axis B-H')) from exc


def _failure_snapshot(directory):
    directory=Path(directory);names=FAILURE_FILES|{'manifest.json'}
    if directory.is_symlink() or not directory.is_dir() or {p.name for p in directory.iterdir()}!=names:
        raise ValueError('off-axis B-H failure requires exactly case/failure and a completion manifest in a regular directory')
    if any((directory/name).is_symlink() or not (directory/name).is_file() for name in names):raise ValueError('off-axis B-H failure files must be regular files, not symbolic links')
    return {name:(directory/name).read_bytes() for name in names}


def _manifest(raw,files,format_name):
    manifest=parse_json(raw['manifest.json'].decode('utf-8'));names=['format','schema_version','files'];keys(manifest,names,names,'off-axis B-H manifest')
    if manifest['format']!=format_name or type(manifest['schema_version']) is not int or manifest['schema_version']!=1:raise ValueError('unsupported off-axis B-H manifest format')
    if manifest['files']!={name:hashlib.sha256(raw[name]).hexdigest() for name in sorted(files)}:raise ValueError('off-axis B-H native content hash mismatch')


def _mesh_arrays(solution):
    space=solution.space;p=space.partition;mesh=p.mesh;k=solution.tangent.tocsr(copy=True);k.sort_indices()
    arrays=dict(points_rz_m=mesh.points_rz_m,triangles=mesh.triangles,boundary_edges=mesh.boundary_edges,
        boundary_cells=mesh.boundary_cells,boundary_local_vertices=mesh.boundary_local_vertices,boundary_components=mesh.boundary_components,
        dof_points_rz_m=space.dof_points,cell_dofs=space.cell_dofs,boundary_dofs=space.boundary_dofs,
        determinant_m2=space.determinant_m2,gradients_per_m=space.gradients_per_m,
        cell_region_indices=p.cell_region_indices,cell_material_indices=p.cell_material_indices,
        material_table_offsets=np.cumsum([0]+[len(m.b_t) for m in p.materials],dtype=np.int64),
        material_b_t=np.concatenate([m.b_t for m in p.materials]),material_h_a_per_m=np.concatenate([m.h_a_per_m for m in p.materials]),
        interface_edges=p.interface_edges,interface_cells=p.interface_cells,interface_region_indices=p.interface_region_indices,
        interface_material_definition_changes=p.interface_material_definition_changes,boundary_region_indices=p.boundary_region_indices,
        region_area_m2=p.region_area_m2,region_volume_m3=p.region_volume_m3,
        boundary_owner_indices=solution.case.boundary_owner_indices,free_dofs=solution.free_dofs,
        internal_load_a=solution.internal_load_a,current_load_a=solution.current_load_a,boundary_load_a=solution.boundary_load_a,
        tangent_csr_data_per_h=k.data,tangent_csr_indices=k.indices,tangent_csr_indptr=k.indptr,tangent_shape=np.array(k.shape,dtype=np.int64))
    cells=np.repeat(np.arange(len(space.cell_dofs)),3);bary=np.tile(np.eye(3),(len(space.cell_dofs),1))
    state=off_axis_bh_state(space,solution.psi_relative_to_reference_wb,cells,bary)
    psi=state['psi_wb']+solution.reference_psi_wb;state=dict(state,psi_wb=psi,aphi_wb_per_m=psi/state['radius_m'])
    arrays.update({'original_cell_vertex_'+name:value.reshape(len(space.cell_dofs),3,*value.shape[1:]) for name,value in state.items()})
    return arrays


def _field_arrays(solution):
    return dict(psi_relative_to_reference_wb=solution.psi_relative_to_reference_wb,reference_psi_wb=np.asarray(solution.reference_psi_wb),psi_wb=solution.psi_wb)


def _same_arrays(actual,expected):
    return (actual.keys()==expected.keys() and all(isinstance(actual[k],np.ndarray) and actual[k].dtype==v.dtype and np.array_equal(actual[k],v) for k,v in expected.items()))


def restore_off_axis_bh(case,fields):
    if type(case) is not OffAxisBHCase:raise ValueError('explicit OffAxisBHCase required')
    if not isinstance(fields,dict) or any(not isinstance(v,np.ndarray) or v.dtype!=np.dtype('float64') or not np.isfinite(v).all() for v in fields.values()):raise ValueError('off-axis B-H native fields require finite float64 arrays')
    fresh=solve_off_axis_bh(case)
    # Exact replay preserves the complete deterministic Newton trajectory,
    # including rejected trials. A nearby root is not the stored computation.
    if not _same_arrays(fields,_field_arrays(fresh)):raise ValueError('off-axis B-H stored relative/absolute psi and reference disagree with nonlinear FEM replay')
    return fresh


def off_axis_bh_result(solution):
    if type(solution) is not OffAxisBHSolution or solution.iteration_report.get('status')!='converged':raise ValueError('off-axis B-H result requires a converged OffAxisBHSolution')
    case=solution.case;mesh=case.partition.mesh
    return dict(format='superfish_ng_off_axis_bh_result',schema_version=1,status='converged',physics='nonlinear_isotropic_magnetostatic',case=case.to_dict(),
        coefficient_field='psi[Wb] = reference_psi_wb + psi_relative_to_reference_wb; Aphi=psi/r[Wb/m]',
        conventions=dict(coordinates='r,z in metres; strictly positive-radius straight P1 triangles with optional holes',
            material='reversible isotropic monotone piecewise-linear H(B) table in SI; explicit provenance, no extrapolation',
            azimuthal_model=case.partition.to_dict()['azimuthal_model'],volume_measure='2*pi*r dr dz; full 3D revolution',
            fields='psi[Wb], Aphi=psi/r[Wb/m], Br=-psi_z/r, Bz=psi_r/r[T], original H=h(|B|)*B/|B|[A/m]',
            original_field_representation='P1 psi coefficients and geometry define B proportional to 1/r and nonlinear H; stored cell-vertex states are samples, not a constant-cell approximation',
            volume_current='Jphi[A/m^2], explicit signed free current in every region; curl(H)_phi=d_z(Hr)-d_r(Hz)=Jphi',
            boundaries='every edge fixed psi[Wb] or tangential H[A/m]; at least one fixed-psi boundary; domain-left tangent, outward normal to its right',
            boundary_load='+2*pi*integral tangential_H*Ni ds [A]',fixed_boundary_reaction='+2*pi*integral original Ht ds [A]; discrete reaction separately reported',
            flux='2*pi*integral r*original B dot outward normal ds [Wb]',energy='U=integral h(b) db dV; Ustar=integral b(h) dh dV [J]; U+Ustar=integral B dot H dV',
            nonlinear_equations='g_i=integral B_i dot H [A]; K_ij=integral B_i dot dH/dB dot B_j [1/H]; K@psi is generally not g',
            constant_psi='zero B/H, Aphi=C/r; sum(g)=0 and constant tangent kernel retained; no excluded-axis absolute flux',
            iteration='true tangent damped Newton at declared fixed quadrature; residual convergence separate from objective decrease; complete deterministic accepted/rejected history',
            quadrature='declared q and q+4 diagnostics retained, including the higher-order residual at the same coefficients; not a field-error bound',
            native_replay='same nonlinear FEM with exact coefficient, table, tangent, load, quadrature diagnostics and iteration-history comparison',
            probes='original P1 fields and isotropic H; lowest cell at exactly represented shared points; no averaging',
            accuracy='algebraic convergence and discrete work/current identities do not bound quadrature or original field/circulation error; no hysteresis, force or inductance inferred'),
        topology=dict(connected_magnetic_domain=True,axis_connected=False,holes=len(mesh.holes_rz_m),boundary_components=1+len(mesh.holes_rz_m),area_m2=mesh.area_m2,volume_m3=mesh.volume_m3,euler_characteristic=1-len(mesh.holes_rz_m)),
        reference_psi_wb=solution.reference_psi_wb,fixed_boundary_dofs={name:dofs.tolist() for name,dofs in solution.fixed_boundary_dofs.items()},
        assembly=copy.deepcopy(solution.assembly_report),nonlinear_iteration=copy.deepcopy(solution.iteration_report),quantities=off_axis_bh_quantities(solution))


def _publish(directory,documents,arrays,format_name):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='.off_axis_bh-staging-',dir=directory) as temporary:
        stage=Path(temporary)
        for name,value in documents.items():_json(stage/name,value)
        for name,value in arrays.items():np.savez_compressed(stage/name,**value)
        names=documents.keys()|arrays.keys()
        _json(stage/'manifest.json',dict(format=format_name,schema_version=1,files={name:hashlib.sha256((stage/name).read_bytes()).hexdigest() for name in sorted(names)}))
        for name in sorted(names):os.link(stage/name,directory/name)
        os.link(stage/'manifest.json',directory/'manifest.json')


def save_off_axis_bh_run(case,solution,directory):
    if type(case) is not OffAxisBHCase or type(solution) is not OffAxisBHSolution or not _same_json(solution.case.to_dict(),case.to_dict()):raise ValueError('off-axis B-H Case and solution disagree')
    request=case.to_dict();actual={k:v.copy() for k,v in _mesh_arrays(solution).items()};fields={k:v.copy() for k,v in _field_arrays(solution).items()};source_result=off_axis_bh_result(solution)
    verified=restore_off_axis_bh(OffAxisBHCase.from_dict(request),fields);expected=_mesh_arrays(verified);result=off_axis_bh_result(verified)
    if not _same_arrays(actual,expected) or not _same_json(source_result,result):raise ValueError('off-axis B-H geometry, material, tangent, loads or iteration history disagree with the Case')
    if not np.array_equal(solution.space.mesh.points,verified.space.mesh.points) or not np.array_equal(solution.space.mesh.triangles,verified.space.mesh.triangles):raise ValueError('off-axis B-H FEM geometry disagrees with its material partition')
    if (not _same_json(case.to_dict(),request) or not _same_json(solution.case.to_dict(),request) or not _same_arrays(_field_arrays(solution),fields)
        or not _same_arrays(_mesh_arrays(solution),actual) or not _same_json(off_axis_bh_result(solution),source_result)):raise ValueError('off-axis B-H input changed during publication verification')
    _publish(directory,{'case.json':request,'results.json':result},{'mesh.npz':expected,'fields.npz':_field_arrays(verified)},'superfish_ng_off_axis_bh_manifest')
    return result


def read_off_axis_bh_run(directory):
    raw=_snapshot(directory);_manifest(raw,FILES,'superfish_ng_off_axis_bh_manifest')
    case=OffAxisBHCase.from_dict(parse_json(raw['case.json'].decode('utf-8')));solution=restore_off_axis_bh(case,_arrays(raw['fields.npz']))
    if not _same_arrays(_arrays(raw['mesh.npz']),_mesh_arrays(solution)):raise ValueError('saved off-axis B-H geometry, materials, cell state, tangent or loads disagree with the Case')
    if not _same_json(parse_json(raw['results.json'].decode('utf-8')),off_axis_bh_result(solution)):raise ValueError('saved off-axis B-H quantities, conventions or iteration history disagree with nonlinear FEM replay')
    if _snapshot(directory)!=raw:raise ValueError('off-axis B-H native changed during verification')
    return solution


def _reproduce_failure(case):
    try:solve_off_axis_bh(case)
    except MagneticNonlinearFailure as exc:return copy.deepcopy(exc.report)
    raise ValueError('off-axis B-H saved failure Case converges; failure report cannot be published or replayed')


def save_off_axis_bh_failure(case,failure,directory):
    if type(case) is not OffAxisBHCase or type(failure) is not MagneticNonlinearFailure:raise ValueError('explicit OffAxisBHCase and MagneticNonlinearFailure required')
    request=case.to_dict();report=copy.deepcopy(failure.report);expected=_reproduce_failure(OffAxisBHCase.from_dict(request))
    if not _same_json(report,expected):raise ValueError('off-axis B-H failure context, reason, history or last valid coefficients disagree with nonlinear FEM replay')
    if not _same_json(case.to_dict(),request) or not _same_json(failure.report,report):raise ValueError('off-axis B-H failure changed during publication verification')
    _publish(directory,{'case.json':request,'failure.json':expected},{},'superfish_ng_off_axis_bh_failure_manifest')
    return expected


def read_off_axis_bh_failure(directory):
    raw=_failure_snapshot(directory);_manifest(raw,FAILURE_FILES,'superfish_ng_off_axis_bh_failure_manifest')
    case=OffAxisBHCase.from_dict(parse_json(raw['case.json'].decode('utf-8')));expected=_reproduce_failure(case)
    if not _same_json(parse_json(raw['failure.json'].decode('utf-8')),expected):raise ValueError('saved off-axis B-H failure context, reason, history or last valid coefficients disagree with nonlinear FEM replay')
    if _failure_snapshot(directory)!=raw:raise ValueError('off-axis B-H failure native changed during verification')
    return expected


def read_off_axis_bh_outcome(directory):
    directory=Path(directory)
    if (directory/'failure.json').exists():return read_off_axis_bh_failure(directory)
    return off_axis_bh_result(read_off_axis_bh_run(directory))


def export_off_axis_bh_probe(run,out,points_rz_m):
    run,out=Path(run),Path(out)
    if out.resolve().is_relative_to(run.resolve()):raise ValueError('off-axis B-H probe output must be outside the native directory')
    raw=_snapshot(run);solution=read_off_axis_bh_run(run)
    result=dict(format='superfish_ng_off_axis_bh_probe',schema_version=1,**solution.probe_at(points_rz_m),conventions=off_axis_bh_result(solution)['conventions'],native_sha256={name:hashlib.sha256(data).hexdigest() for name,data in raw.items()})
    if _snapshot(run)!=raw:raise ValueError('off-axis B-H native changed while preparing probe')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.off_axis_bh-probe-',dir=out.parent) as temporary:
        stage=Path(temporary)/'probe.json';_json(stage,result);os.link(stage,out)
    return result
