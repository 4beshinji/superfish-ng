# SPDX-License-Identifier: Apache-2.0
"""Regular axis recoil native tensors, remanence and complete source replay."""
import hashlib,os,tempfile
from pathlib import Path
import numpy as np
from .config import keys
from .project import parse_json
from .coaxial_saved import FILES,_json,_arrays,_snapshot as _file_snapshot
from .axis_recoil import (AxisRecoilCase,AxisRecoilSolution,
    solve_axis_recoil,axis_recoil_quantities)


def _snapshot(directory):
    directory=Path(directory)
    if directory.is_symlink():raise ValueError('axis recoil native directory must not be a symbolic link')
    try:return _file_snapshot(directory)
    except ValueError as exc:raise ValueError(str(exc).replace('coaxial','axis recoil')) from exc


def _mesh_arrays(solution):
    space=solution.space;p=space.partition;mesh=p.mesh
    return dict(points_rz_m=mesh.points_rz_m,triangles=mesh.triangles,boundary_edges=mesh.boundary_edges,
        boundary_cells=mesh.boundary_cells,boundary_local_vertices=mesh.boundary_local_vertices,
        boundary_components=mesh.boundary_components,boundary_segments=mesh.boundary_segments,
        axis_nodes=mesh.axis_nodes,axis_edges=mesh.axis_edges,axis_dofs=space.axis_dofs,
        dof_points_rz_m=space.dof_points,cell_dofs=space.cell_dofs,boundary_dofs=space.boundary_dofs,
        cell_region_indices=p.cell_region_indices,mu_r_tensor=p.mu_r_tensor,reluctivity_tensor_m_per_h=p.reluctivity_tensor_m_per_h,
        remanent_b_t=p.remanent_b_t,remanent_h_a_per_m=p.remanent_h_a_per_m,region_orientation_rad=np.array([v.orientation_rad for v in p.regions]),
        azimuthal_mu_r=p.azimuthal_mu_r,region_axis_contact=p.region_axis_contact,
        interface_edges=p.interface_edges,interface_cells=p.interface_cells,interface_region_indices=p.interface_region_indices,
        interface_coefficient_jumps=p.interface_coefficient_jumps,boundary_region_indices=p.boundary_region_indices,
        region_area_m2=p.region_area_m2,region_volume_m3=p.region_volume_m3,
        boundary_owner_indices=solution.case.boundary_owner_indices,free_dofs=solution.free_dofs,
        current_load_a_m2=solution.current_load_a_m2,remanent_load_a_m2=solution.remanent_load_a_m2,boundary_load_a_m2=solution.boundary_load_a_m2)


def _field_arrays(solution):return dict(aphi_over_r_t=solution.aphi_over_r_t)


def restore_axis_recoil(case,fields):
    if type(case) is not AxisRecoilCase:raise ValueError('explicit AxisRecoilCase required')
    if not isinstance(fields,dict) or fields.keys()!={'aphi_over_r_t'}:raise ValueError('unexpected axis magnetic field arrays')
    if any(not isinstance(value,np.ndarray) or value.dtype!=np.dtype('float64') or not np.isfinite(value).all() for value in fields.values()):
        raise ValueError('axis magnetic native fields require finite float64 arrays')
    fresh=solve_axis_recoil(case);c=fields['aphi_over_r_t'].copy()
    if c.shape!=fresh.aphi_over_r_t.shape:raise ValueError('axis magnetic native coefficient dimensions disagree')
    fixed=np.unique(np.concatenate(list(fresh.fixed_boundary_dofs.values()))) if fresh.fixed_boundary_dofs else np.array([],dtype=np.int64)
    if not np.array_equal(c[fixed],fresh.aphi_over_r_t[fixed]):raise ValueError('axis magnetic coefficients violate fixed Aphi/r boundary values')
    scale=max(np.linalg.norm(c),np.linalg.norm(fresh.aphi_over_r_t));difference=float(np.linalg.norm(c-fresh.aphi_over_r_t)/scale) if scale else 0.
    force=fresh.stiffness@c;load=fresh.current_load_a_m2+fresh.remanent_load_a_m2+fresh.boundary_load_a_m2;denominator=np.linalg.norm(force)+np.linalg.norm(load)
    residual=float(np.linalg.norm((force-load)[fresh.free_dofs])/denominator) if denominator else 0.
    if not np.isfinite([difference,residual]).all() or max(difference,residual)>1e-10:
        raise ValueError('axis magnetic stored coefficients fail reconstructed current-source solution or free-DOF residual validation')
    c.setflags(write=False)
    restored=AxisRecoilSolution(fresh.case,fresh.space,fresh.stiffness,fresh.current_load_a_m2,fresh.remanent_load_a_m2,fresh.boundary_load_a_m2,
        c,fresh.free_dofs,fresh.fixed_boundary_dofs,fresh.assembly_report,residual)
    axis_recoil_quantities(restored)
    return restored


def axis_recoil_result(solution):
    if type(solution) is not AxisRecoilSolution:raise ValueError('axis recoil result requires AxisRecoilSolution')
    case=solution.case;p=case.partition;mesh=p.mesh
    return dict(format='superfish_ng_axis_recoil_result',schema_version=1,physics='linear_recoil_magnetostatic',
        case=case.to_dict(),coefficient_field='aphi_over_r_t; a=Aphi/r[T], Aphi=r*a[Wb/m]; no constant gauge subtraction',
        conventions=dict(coordinates='r,z in metres; explicit straight axis-connected magnetic domain with optional holes',
            material='positive principal recoil mu_r and local remanent B[T], explicit meridional region orientation; nu=(mu0*mu_rec)^-1[m/H]',
            volume_measure='2*pi*r dr dz; full surface of revolution, no extrusion thickness',
            fields='a=Aphi/r[T], Aphi=r*a[Wb/m], Br=-r*d_z(a)[T], Bz=2*a+r*d_r(a)[T], H=nu(original cell)*(B-Brem)[A/m]',
            volume_current='Jphi[A/m^2]; (curl H)_phi=d_z(Hr)-d_r(Hz)=Jphi; source current integral Jphi dr dz [A]',
            boundaries='axis_regularity only at r=0; all other edges fixed Aphi/r[T] or tangential H[A/m]; tangent keeps domain on left in r,z',
            axis='all a DOFs retained; Aphi=Br=Hr=0 and finite Bz on axis; axis-touching materials have orientation=0 and radial Brem=0; constant a is uniform Bz, not a gauge kernel',
            remanent_load='integral B_i dot nu*Brem dV [A m^2], separate from current and boundary loads',
            azimuthal_model=p.to_dict()['azimuthal_model'],
            boundary_load='+2*pi*integral r^2*Ht*Ni ds [A m^2]',
            fixed_boundary_reaction='positive 2*pi*integral r^2*Ht ds [A m^2], conjugate to a[T]; discrete reaction and original H integral separate',
            ampere='original H circulation in r,z plus source Jphi cross-section current [A]; axis H is included',
            flux='2*pi*integral r*original B dot outward normal ds [Wb]; normal to right of tangent',
            constitutive_potentials='W0=integral(.5*B.nu.B-B.nu.Brem) references B=0; Ws=integral(.5*(B-Brem).nu.(B-Brem)) references H=0; full 3D [J]; both B derivatives are H',
            potential_constant='.5 integral Brem.nu.Brem dV [J]; Ws=W0+constant; no absolute magnet internal energy',
            probes='original-cell derivatives; lowest cell at exactly represented shared edges/vertices; rounded coordinates may lie in either cell; no averaging',
            accuracy='discrete work identities do not bound original B/H, flux or circulation error; no winding inductance is inferred'),
        topology=dict(connected_magnetic_domain=True,holes=len(mesh.holes_rz_m),boundary_components=1+len(mesh.holes_rz_m),
            area_m2=mesh.area_m2,volume_m3=mesh.volume_m3,euler_characteristic=mesh.euler_characteristic,axis_interval_m=list(mesh.axis_interval_m)),
        fixed_boundary_dofs={name:dofs.tolist() for name,dofs in solution.fixed_boundary_dofs.items()},
        assembly=solution.assembly_report,quantities=axis_recoil_quantities(solution))


def save_axis_recoil_run(case,solution,directory):
    if type(case) is not AxisRecoilCase or type(solution) is not AxisRecoilSolution or solution.case.to_dict()!=case.to_dict():
        raise ValueError('axis recoil case and solution disagree')
    request=case.to_dict();actual={k:v.copy() for k,v in _mesh_arrays(solution).items()};fields={k:v.copy() for k,v in _field_arrays(solution).items()}
    verified=restore_axis_recoil(AxisRecoilCase.from_dict(request),fields);expected=_mesh_arrays(verified)
    if actual.keys()!=expected.keys() or any(not np.array_equal(actual[k],v) for k,v in expected.items()):
        raise ValueError('axis recoil solution geometry, material, boundary loads or DOFs disagree with the Case')
    if not np.array_equal(solution.space.mesh.points,verified.space.mesh.points) or not np.array_equal(solution.space.mesh.triangles,verified.space.mesh.triangles):
        raise ValueError('axis recoil FEM geometry disagrees with its material partition')
    result=axis_recoil_result(verified)
    if (case.to_dict()!=request or solution.case.to_dict()!=request or any(not np.array_equal(_field_arrays(solution)[k],v) for k,v in fields.items())
        or any(not np.array_equal(_mesh_arrays(solution)[k],v) for k,v in actual.items())):
        raise ValueError('axis recoil input changed during publication verification')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='.axis_recoil-staging-',dir=directory) as temporary:
        stage=Path(temporary);_json(stage/'case.json',request);_json(stage/'results.json',result)
        np.savez_compressed(stage/'mesh.npz',**expected);np.savez_compressed(stage/'fields.npz',**_field_arrays(verified))
        _json(stage/'manifest.json',dict(format='superfish_ng_axis_recoil_manifest',schema_version=1,
            files={name:hashlib.sha256((stage/name).read_bytes()).hexdigest() for name in sorted(FILES)}))
        for name in sorted(FILES):os.link(stage/name,directory/name)
        os.link(stage/'manifest.json',directory/'manifest.json')
    return result


def read_axis_recoil_run(directory):
    directory=Path(directory);raw=_snapshot(directory);manifest=parse_json(raw['manifest.json'].decode('utf-8'))
    names=['format','schema_version','files'];keys(manifest,names,names,'axis recoil manifest')
    if (manifest['format']!='superfish_ng_axis_recoil_manifest' or type(manifest['schema_version']) is not int or manifest['schema_version']!=1):
        raise ValueError('unsupported axis recoil manifest format')
    if manifest['files']!={name:hashlib.sha256(raw[name]).hexdigest() for name in sorted(FILES)}:raise ValueError('axis recoil native content hash mismatch')
    case=AxisRecoilCase.from_dict(parse_json(raw['case.json'].decode('utf-8')))
    solution=restore_axis_recoil(case,_arrays(raw['fields.npz']));expected=_mesh_arrays(solution);actual=_arrays(raw['mesh.npz'])
    if (actual.keys()!=expected.keys() or any(actual[k].dtype!=v.dtype or not np.array_equal(actual[k],v) for k,v in expected.items())):
        raise ValueError('saved axis recoil geometry, material, boundary loads or DOFs disagree with the Case')
    if parse_json(raw['results.json'].decode('utf-8'))!=axis_recoil_result(solution):
        raise ValueError('saved axis recoil current, constitutive potentials, flux or conventions disagree with current-source replay')
    if _snapshot(directory)!=raw:raise ValueError('axis recoil native changed during verification')
    return solution


def export_axis_recoil_probe(run,out,points_rz_m):
    run,out=Path(run),Path(out)
    if out.resolve().is_relative_to(run.resolve()):raise ValueError('axis recoil probe output must be outside the native directory')
    raw=_snapshot(run);solution=read_axis_recoil_run(run)
    result=dict(format='superfish_ng_axis_recoil_probe',schema_version=1,**solution.probe_at(points_rz_m),
        conventions=axis_recoil_result(solution)['conventions'],native_sha256={name:hashlib.sha256(data).hexdigest() for name,data in raw.items()})
    if _snapshot(run)!=raw:raise ValueError('axis recoil native changed while preparing probe')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.axis_recoil-probe-',dir=out.parent) as temporary:
        stage=Path(temporary)/'probe.json';_json(stage,result);os.link(stage,out)
    return result
