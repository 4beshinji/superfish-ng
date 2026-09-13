# SPDX-License-Identifier: Apache-2.0
"""Verified planar nonlinear B-H success and failure publication and replay."""
import copy,hashlib,json,os,tempfile
from pathlib import Path
import numpy as np
from .config import keys
from .project import parse_json
from .coaxial_saved import FILES,_json,_arrays,_snapshot as _file_snapshot
from .planar_bh import PlanarBHCase,PlanarBHSolution,solve_planar_bh,planar_bh_quantities
from .planar_bh_fem import planar_bh_cell_state
from .nonlinear_magnetic import MagneticNonlinearFailure

FAILURE_FILES={'case.json','failure.json'}


def _same_json(a,b):
    return json.dumps(a,sort_keys=True,allow_nan=False)==json.dumps(b,sort_keys=True,allow_nan=False)


def _snapshot(directory):
    directory=Path(directory)
    if directory.is_symlink():raise ValueError('planar B-H native directory must not be a symbolic link')
    try:return _file_snapshot(directory)
    except ValueError as exc:raise ValueError(str(exc).replace('coaxial','planar B-H')) from exc


def _failure_snapshot(directory):
    directory=Path(directory);names=FAILURE_FILES|{'manifest.json'}
    if directory.is_symlink() or not directory.is_dir() or {p.name for p in directory.iterdir()}!=names:
        raise ValueError('planar B-H failure requires exactly case/failure and a completion manifest in a regular directory')
    if any((directory/name).is_symlink() or not (directory/name).is_file() for name in names):raise ValueError('planar B-H failure files must be regular files, not symbolic links')
    return {name:(directory/name).read_bytes() for name in names}


def _manifest(raw,files,format_name):
    manifest=parse_json(raw['manifest.json'].decode('utf-8'));names=['format','schema_version','files'];keys(manifest,names,names,'planar B-H manifest')
    if manifest['format']!=format_name or type(manifest['schema_version']) is not int or manifest['schema_version']!=1:raise ValueError('unsupported planar B-H manifest format')
    if manifest['files']!={name:hashlib.sha256(raw[name]).hexdigest() for name in sorted(files)}:raise ValueError('planar B-H native content hash mismatch')


def _mesh_arrays(solution):
    space=solution.space;p=space.partition;mesh=p.mesh;k=solution.tangent.tocsr(copy=True);k.sort_indices()
    state=planar_bh_cell_state(space,solution.az_relative_to_reference_wb_per_m)
    arrays=dict(points_xy_m=mesh.points_xy_m,triangles=mesh.triangles,boundary_edges=mesh.boundary_edges,
        boundary_cells=mesh.boundary_cells,boundary_local_vertices=mesh.boundary_local_vertices,
        dof_points_xy_m=space.dof_points_xy_m,cell_dofs=space.cell_dofs,boundary_dofs=space.boundary_dofs,
        cell_areas_m2=space.cell_areas_m2,cell_curls_per_m=space.curls,
        cell_region_indices=p.cell_region_indices,cell_material_indices=p.cell_material_indices,
        material_table_offsets=np.cumsum([0]+[len(m.b_t) for m in p.materials],dtype=np.int64),
        material_b_t=np.concatenate([m.b_t for m in p.materials]),material_h_a_per_m=np.concatenate([m.h_a_per_m for m in p.materials]),
        interface_edges=p.interface_edges,interface_cells=p.interface_cells,interface_region_indices=p.interface_region_indices,
        interface_material_definition_changes=p.interface_material_definition_changes,boundary_region_indices=p.boundary_region_indices,
        region_area_m2=p.region_area_m2,boundary_owner_indices=solution.case.boundary_owner_indices,free_dofs=solution.free_dofs,
        internal_load_a=solution.internal_load_a,current_load_a=solution.current_load_a,boundary_load_a=solution.boundary_load_a,
        tangent_csr_data_m_per_h=k.data,tangent_csr_indices=k.indices,tangent_csr_indptr=k.indptr,tangent_shape=np.array(k.shape,dtype=np.int64))
    arrays.update({'cell_'+name:value for name,value in state.items() if name not in ('az_relative_to_reference_wb_per_m','reference_az_wb_per_m')})
    return arrays


def _field_arrays(solution):
    return dict(az_relative_to_reference_wb_per_m=solution.az_relative_to_reference_wb_per_m,
        reference_az_wb_per_m=np.asarray(solution.reference_az_wb_per_m),az_wb_per_m=solution.az_wb_per_m)


def _same_arrays(actual,expected):
    return (actual.keys()==expected.keys() and all(isinstance(actual[k],np.ndarray) and actual[k].dtype==v.dtype and np.array_equal(actual[k],v) for k,v in expected.items()))


def restore_planar_bh(case,fields):
    if type(case) is not PlanarBHCase:raise ValueError('explicit PlanarBHCase required')
    if not isinstance(fields,dict) or any(not isinstance(v,np.ndarray) or v.dtype!=np.dtype('float64') or not np.isfinite(v).all() for v in fields.values()):raise ValueError('planar B-H native fields require finite float64 arrays')
    fresh=solve_planar_bh(case)
    # Exact replay preserves the complete deterministic Newton trajectory,
    # including rejected trials. A nearby root is not the stored computation.
    if not _same_arrays(fields,_field_arrays(fresh)):raise ValueError('planar B-H stored coefficients, reference or absolute Az disagree with nonlinear FEM replay')
    return fresh


def planar_bh_result(solution):
    if type(solution) is not PlanarBHSolution or solution.iteration_report.get('status')!='converged':raise ValueError('planar B-H result requires a converged PlanarBHSolution')
    case=solution.case;mesh=case.partition.mesh
    return dict(format='superfish_ng_planar_bh_result',schema_version=1,status='converged',physics='nonlinear_isotropic_magnetostatic',case=case.to_dict(),
        coefficient_field='Az[Wb/m] = reference_az_wb_per_m + az_relative_to_reference_wb_per_m',
        conventions=dict(coordinates='x,y in metres; straight simple polygon with material-conforming P1 triangles',
            material='reversible isotropic monotone piecewise-linear H(B) table in SI; explicit provenance, no extrapolation',
            volume_measure='dx dy per metre of uniform extrusion; no implicit thickness or rotation axis',
            fields='static real Az[Wb/m], B=(dAz/dy,-dAz/dx)[T], original H=h(|B|)*B/|B|[A/m]',
            volume_current='Jz[A/m^2], explicit signed free current in every region; curl(H)_z=Jz',
            boundaries='every edge fixed Az[Wb/m] or tangential H[A/m]; domain-left tangent, outward normal to its right',
            boundary_load='-integral tangential_H*Ni ds [A]',fixed_boundary_reaction='minus original Ht line integral [A]; discrete reaction separately reported',
            flux='integral original B dot outward normal ds [Wb/m]',energy='U=integral h(b) db dA; Ustar=integral b(h) dh dA [J/m]; U+Ustar=integral B dot H dA',
            nonlinear_equations='g_i=integral curlNi dot H [A]; K_ij=integral curlNi dot dH/dB dot curlNj [m/H]; K@Az is generally not g',
            iteration='true tangent damped Newton; residual convergence separate from objective decrease; complete deterministic accepted/rejected history',
            native_replay='same nonlinear FEM with exact coefficient, table, tangent, load and iteration-history comparison',
            probes='original P1 cell fields; lowest cell at exactly represented shared points; no averaging',
            accuracy='algebraic convergence and discrete work/current identities do not bound original field/circulation error; no hysteresis, force or inductance inferred'),
        topology=dict(connected_magnetic_domain=True,holes=0,boundary_components=1,area_m2=mesh.area_m2,euler_characteristic=1),
        reference_az_wb_per_m=solution.reference_az_wb_per_m,fixed_boundary_dofs={name:dofs.tolist() for name,dofs in solution.fixed_boundary_dofs.items()},
        assembly=copy.deepcopy(solution.assembly_report),nonlinear_iteration=copy.deepcopy(solution.iteration_report),quantities=planar_bh_quantities(solution))


def _publish(directory,documents,arrays,format_name):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='.planar_bh-staging-',dir=directory) as temporary:
        stage=Path(temporary)
        for name,value in documents.items():_json(stage/name,value)
        for name,value in arrays.items():np.savez_compressed(stage/name,**value)
        names=documents.keys()|arrays.keys()
        _json(stage/'manifest.json',dict(format=format_name,schema_version=1,files={name:hashlib.sha256((stage/name).read_bytes()).hexdigest() for name in sorted(names)}))
        for name in sorted(names):os.link(stage/name,directory/name)
        os.link(stage/'manifest.json',directory/'manifest.json')


def save_planar_bh_run(case,solution,directory):
    if type(case) is not PlanarBHCase or type(solution) is not PlanarBHSolution or not _same_json(solution.case.to_dict(),case.to_dict()):raise ValueError('planar B-H Case and solution disagree')
    request=case.to_dict();actual={k:v.copy() for k,v in _mesh_arrays(solution).items()};fields={k:v.copy() for k,v in _field_arrays(solution).items()};source_result=planar_bh_result(solution)
    verified=restore_planar_bh(PlanarBHCase.from_dict(request),fields);expected=_mesh_arrays(verified);result=planar_bh_result(verified)
    if not _same_arrays(actual,expected) or not _same_json(source_result,result):raise ValueError('planar B-H geometry, material, tangent, loads or iteration history disagree with the Case')
    if not np.array_equal(solution.space.mesh.points,verified.space.mesh.points) or not np.array_equal(solution.space.mesh.triangles,verified.space.mesh.triangles):raise ValueError('planar B-H FEM geometry disagrees with its material partition')
    if (not _same_json(case.to_dict(),request) or not _same_json(solution.case.to_dict(),request) or not _same_arrays(_field_arrays(solution),fields)
        or not _same_arrays(_mesh_arrays(solution),actual) or not _same_json(planar_bh_result(solution),source_result)):raise ValueError('planar B-H input changed during publication verification')
    _publish(directory,{'case.json':request,'results.json':result},{'mesh.npz':expected,'fields.npz':_field_arrays(verified)},'superfish_ng_planar_bh_manifest')
    return result


def read_planar_bh_run(directory):
    raw=_snapshot(directory);_manifest(raw,FILES,'superfish_ng_planar_bh_manifest')
    case=PlanarBHCase.from_dict(parse_json(raw['case.json'].decode('utf-8')));solution=restore_planar_bh(case,_arrays(raw['fields.npz']))
    if not _same_arrays(_arrays(raw['mesh.npz']),_mesh_arrays(solution)):raise ValueError('saved planar B-H geometry, materials, cell state, tangent or loads disagree with the Case')
    if not _same_json(parse_json(raw['results.json'].decode('utf-8')),planar_bh_result(solution)):raise ValueError('saved planar B-H quantities, conventions or iteration history disagree with nonlinear FEM replay')
    if _snapshot(directory)!=raw:raise ValueError('planar B-H native changed during verification')
    return solution


def _reproduce_failure(case):
    try:solve_planar_bh(case)
    except MagneticNonlinearFailure as exc:return copy.deepcopy(exc.report)
    raise ValueError('planar B-H saved failure Case converges; failure report cannot be published or replayed')


def save_planar_bh_failure(case,failure,directory):
    if type(case) is not PlanarBHCase or type(failure) is not MagneticNonlinearFailure:raise ValueError('explicit PlanarBHCase and MagneticNonlinearFailure required')
    request=case.to_dict();report=copy.deepcopy(failure.report);expected=_reproduce_failure(PlanarBHCase.from_dict(request))
    if not _same_json(report,expected):raise ValueError('planar B-H failure context, reason, history or last valid coefficients disagree with nonlinear FEM replay')
    if not _same_json(case.to_dict(),request) or not _same_json(failure.report,report):raise ValueError('planar B-H failure changed during publication verification')
    _publish(directory,{'case.json':request,'failure.json':expected},{},'superfish_ng_planar_bh_failure_manifest')
    return expected


def read_planar_bh_failure(directory):
    raw=_failure_snapshot(directory);_manifest(raw,FAILURE_FILES,'superfish_ng_planar_bh_failure_manifest')
    case=PlanarBHCase.from_dict(parse_json(raw['case.json'].decode('utf-8')));expected=_reproduce_failure(case)
    if not _same_json(parse_json(raw['failure.json'].decode('utf-8')),expected):raise ValueError('saved planar B-H failure context, reason, history or last valid coefficients disagree with nonlinear FEM replay')
    if _failure_snapshot(directory)!=raw:raise ValueError('planar B-H failure native changed during verification')
    return expected


def read_planar_bh_outcome(directory):
    directory=Path(directory)
    if (directory/'failure.json').exists():return read_planar_bh_failure(directory)
    return planar_bh_result(read_planar_bh_run(directory))


def export_planar_bh_probe(run,out,points_xy_m):
    run,out=Path(run),Path(out)
    if out.resolve().is_relative_to(run.resolve()):raise ValueError('planar B-H probe output must be outside the native directory')
    raw=_snapshot(run);solution=read_planar_bh_run(run)
    result=dict(format='superfish_ng_planar_bh_probe',schema_version=1,**solution.probe_at(points_xy_m),conventions=planar_bh_result(solution)['conventions'],native_sha256={name:hashlib.sha256(data).hexdigest() for name,data in raw.items()})
    if _snapshot(run)!=raw:raise ValueError('planar B-H native changed while preparing probe')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.planar_bh-probe-',dir=out.parent) as temporary:
        stage=Path(temporary)/'probe.json';_json(stage,result);os.link(stage,out)
    return result
