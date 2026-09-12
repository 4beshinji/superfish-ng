# SPDX-License-Identifier: Apache-2.0
"""Planar recoil native tensor, remanent/current loads and affine constitutive replay."""
import hashlib,os,tempfile
from pathlib import Path
import numpy as np
from .config import keys
from .project import parse_json
from .coaxial_saved import FILES,_json,_arrays,_snapshot as _file_snapshot
from .planar_recoil import (PlanarRecoilCase,PlanarRecoilSolution,
    solve_planar_recoil,planar_recoil_quantities)


def _snapshot(directory):
    directory=Path(directory)
    if directory.is_symlink():raise ValueError('planar recoil native directory must not be a symbolic link')
    try:return _file_snapshot(directory)
    except ValueError as exc:raise ValueError(str(exc).replace('coaxial','planar recoil')) from exc


def _mesh_arrays(solution):
    space=solution.space;p=space.partition;mesh=p.mesh
    return dict(points_xy_m=mesh.points_xy_m,triangles=mesh.triangles,boundary_edges=mesh.boundary_edges,
        boundary_cells=mesh.boundary_cells,boundary_local_vertices=mesh.boundary_local_vertices,
        dof_points_xy_m=space.dof_points_xy_m,cell_dofs=space.cell_dofs,boundary_dofs=space.boundary_dofs,
        cell_region_indices=p.cell_region_indices,mu_r_tensor=p.mu_r_tensor,reluctivity_tensor_m_per_h=p.reluctivity_tensor_m_per_h,
        remanent_b_t=p.remanent_b_t,remanent_h_a_per_m=p.remanent_h_a_per_m,region_orientation_rad=np.array([v.orientation_rad for v in p.regions]),
        interface_edges=p.interface_edges,interface_cells=p.interface_cells,interface_region_indices=p.interface_region_indices,
        interface_coefficient_jumps=p.interface_coefficient_jumps,boundary_region_indices=p.boundary_region_indices,
        region_area_m2=p.region_area_m2,
        boundary_owner_indices=solution.case.boundary_owner_indices,free_dofs=solution.free_dofs,
        current_load_a=solution.current_load_a,remanent_load_a=solution.remanent_load_a,boundary_load_a=solution.boundary_load_a)


def _field_arrays(solution):
    return dict(az_relative_to_reference_wb_per_m=solution.az_relative_to_reference_wb_per_m,
        reference_az_wb_per_m=np.asarray(solution.reference_az_wb_per_m),az_wb_per_m=solution.az_wb_per_m)


def restore_planar_recoil(case,fields):
    if type(case) is not PlanarRecoilCase:raise ValueError('explicit PlanarRecoilCase required')
    expected={'az_relative_to_reference_wb_per_m','reference_az_wb_per_m','az_wb_per_m'}
    if not isinstance(fields,dict) or fields.keys()!=expected:raise ValueError('unexpected planar recoil field arrays')
    if any(not isinstance(value,np.ndarray) or value.dtype!=np.dtype('float64') or not np.isfinite(value).all() for value in fields.values()):
        raise ValueError('planar recoil native fields require finite float64 arrays')
    # Re-solving the unique anchored system also checks that the stored
    # coefficients belong to this exact recoil tensor/remanence/current/boundary problem.
    fresh=solve_planar_recoil(case);c=fields['az_relative_to_reference_wb_per_m'].copy();reference=fields['reference_az_wb_per_m']
    if c.shape!=fresh.az_wb_per_m.shape or fields['az_wb_per_m'].shape!=c.shape or reference.shape!=() or float(reference)!=fresh.reference_az_wb_per_m:
        raise ValueError('planar recoil native potential dimensions or reference Az boundary disagree')
    absolute=c+fresh.reference_az_wb_per_m
    if not np.array_equal(absolute,fields['az_wb_per_m']):raise ValueError('planar recoil absolute potential disagrees with its stored reference and coefficients')
    fixed=np.unique(np.concatenate(list(fresh.fixed_boundary_dofs.values())))
    if not np.array_equal(c[fixed],fresh.az_relative_to_reference_wb_per_m[fixed]):raise ValueError('planar recoil coefficients violate fixed Az boundary values')
    scale=max(np.linalg.norm(c),np.linalg.norm(fresh.az_relative_to_reference_wb_per_m))
    difference=float(np.linalg.norm(c-fresh.az_relative_to_reference_wb_per_m)/scale) if scale else 0.
    force=fresh.stiffness@c;load=fresh.current_load_a+fresh.remanent_load_a+fresh.boundary_load_a;denominator=np.linalg.norm(force)+np.linalg.norm(load)
    residual=float(np.linalg.norm((force-load)[fresh.free_dofs])/denominator) if denominator else 0.
    if not np.isfinite([difference,residual]).all() or max(difference,residual)>1e-10:
        raise ValueError('planar recoil stored coefficients fail reconstructed magnetic FEM solution or free-DOF residual validation')
    c.setflags(write=False);absolute.setflags(write=False)
    restored=PlanarRecoilSolution(fresh.case,fresh.space,fresh.stiffness,fresh.current_load_a,fresh.remanent_load_a,fresh.boundary_load_a,
        absolute,c,fresh.reference_az_wb_per_m,fresh.free_dofs,fresh.fixed_boundary_dofs,fresh.assembly_report,residual)
    planar_recoil_quantities(restored)
    return restored


def planar_recoil_result(solution):
    if type(solution) is not PlanarRecoilSolution:raise ValueError('planar recoil result requires PlanarRecoilSolution')
    case=solution.case;p=case.partition;mesh=p.mesh
    return dict(format='superfish_ng_planar_recoil_result',schema_version=1,physics='linear_recoil_magnetostatic',
        case=case.to_dict(),coefficient_field='az_relative_to_reference_wb_per_m; Az[Wb/m] = reference_az_wb_per_m + coefficient',
        conventions=dict(coordinates='x,y in metres; straight simple polygon with material-conforming triangles',
            material='positive principal recoil mu_r; each region orientation rotates both tensor and remanent B_local[T]; nu=(mu0*mu_rec)^-1[m/H]',
            volume_measure='dx dy per metre of uniform extrusion; no implicit thickness or rotation axis',
            fields='static real Az[Wb/m], B=(dAz/dy,-dAz/dx)[T], original H=nu*(B-Brem)[A/m]',
            volume_current='Jz[A/m^2], explicit signed free current in every region; curl(H)_z=Jz',
            remanent_load='integral curl(Ni ez) dot nu*Brem dxdy [A], separate from free current and boundary loads',
            boundaries='every edge fixed Az[Wb/m] or tangential H[A/m]; domain-left tangent, outward normal to its right',
            boundary_load='-integral tangential_H*Ni ds [A]',
            fixed_boundary_reaction='minus original Ht line integral on fixed-Az boundary [A]; discrete reaction separately reported',
            flux='integral original B dot outward normal ds [Wb/m]',
            constitutive_potentials='w0=.5*B.nu.B-B.nu.Brem with B=0 reference; ws=.5*(B-Brem).nu.(B-Brem) with H=0 reference; integrated [J/m]; both gradients are H',
            potential_constant='.5 integral Brem.nu.Brem dxdy [J/m]; ws=w0+constant; no absolute magnet internal energy',
            probes='original cell derivatives; lowest cell at exactly represented shared edges/vertices; rounded points may lie in either cell; no averaging',
            accuracy='discrete residual and identities do not bound field/circulation error; no irreversible demagnetization, force or winding inductance is inferred'),
        topology=dict(connected_magnetic_domain=True,holes=0,boundary_components=1,area_m2=mesh.area_m2,euler_characteristic=1),
        reference_az_wb_per_m=solution.reference_az_wb_per_m,
        fixed_boundary_dofs={name:dofs.tolist() for name,dofs in solution.fixed_boundary_dofs.items()},
        assembly=solution.assembly_report,quantities=planar_recoil_quantities(solution))


def save_planar_recoil_run(case,solution,directory):
    if type(case) is not PlanarRecoilCase or type(solution) is not PlanarRecoilSolution or solution.case.to_dict()!=case.to_dict():
        raise ValueError('planar recoil case and solution disagree')
    request=case.to_dict();actual={k:v.copy() for k,v in _mesh_arrays(solution).items()};fields={k:v.copy() for k,v in _field_arrays(solution).items()}
    verified=restore_planar_recoil(PlanarRecoilCase.from_dict(request),fields);expected=_mesh_arrays(verified)
    if actual.keys()!=expected.keys() or any(not np.array_equal(actual[k],v) for k,v in expected.items()):
        raise ValueError('planar recoil solution geometry, material, boundary loads or DOFs disagree with the Case')
    if not np.array_equal(solution.space.mesh.points,verified.space.mesh.points) or not np.array_equal(solution.space.mesh.triangles,verified.space.mesh.triangles):
        raise ValueError('planar recoil FEM geometry disagrees with its material partition')
    result=planar_recoil_result(verified)
    if (case.to_dict()!=request or solution.case.to_dict()!=request or any(not np.array_equal(_field_arrays(solution)[k],v) for k,v in fields.items())
        or any(not np.array_equal(_mesh_arrays(solution)[k],v) for k,v in actual.items())):
        raise ValueError('planar recoil input changed during publication verification')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='.planar_recoil-staging-',dir=directory) as temporary:
        stage=Path(temporary);_json(stage/'case.json',request);_json(stage/'results.json',result)
        np.savez_compressed(stage/'mesh.npz',**expected);np.savez_compressed(stage/'fields.npz',**_field_arrays(verified))
        _json(stage/'manifest.json',dict(format='superfish_ng_planar_recoil_manifest',schema_version=1,
            files={name:hashlib.sha256((stage/name).read_bytes()).hexdigest() for name in sorted(FILES)}))
        for name in sorted(FILES):os.link(stage/name,directory/name)
        os.link(stage/'manifest.json',directory/'manifest.json')
    return result


def read_planar_recoil_run(directory):
    directory=Path(directory);raw=_snapshot(directory);manifest=parse_json(raw['manifest.json'].decode('utf-8'))
    names=['format','schema_version','files'];keys(manifest,names,names,'planar recoil manifest')
    if (manifest['format']!='superfish_ng_planar_recoil_manifest' or type(manifest['schema_version']) is not int or manifest['schema_version']!=1):
        raise ValueError('unsupported planar recoil manifest format')
    if manifest['files']!={name:hashlib.sha256(raw[name]).hexdigest() for name in sorted(FILES)}:raise ValueError('planar recoil native content hash mismatch')
    case=PlanarRecoilCase.from_dict(parse_json(raw['case.json'].decode('utf-8')))
    solution=restore_planar_recoil(case,_arrays(raw['fields.npz']));expected=_mesh_arrays(solution);actual=_arrays(raw['mesh.npz'])
    if (actual.keys()!=expected.keys() or any(actual[k].dtype!=v.dtype or not np.array_equal(actual[k],v) for k,v in expected.items())):
        raise ValueError('saved planar recoil geometry, material, boundary loads or DOFs disagree with the Case')
    if parse_json(raw['results.json'].decode('utf-8'))!=planar_recoil_result(solution):
        raise ValueError('saved planar recoil current, energy, flux or conventions disagree with magnetic FEM replay')
    if _snapshot(directory)!=raw:raise ValueError('planar recoil native changed during verification')
    return solution


def export_planar_recoil_probe(run,out,points_xy_m):
    run,out=Path(run),Path(out)
    if out.resolve().is_relative_to(run.resolve()):raise ValueError('planar recoil probe output must be outside the native directory')
    raw=_snapshot(run);solution=read_planar_recoil_run(run)
    result=dict(format='superfish_ng_planar_recoil_probe',schema_version=1,**solution.probe_at(points_xy_m),
        conventions=planar_recoil_result(solution)['conventions'],native_sha256={name:hashlib.sha256(data).hexdigest() for name,data in raw.items()})
    if _snapshot(run)!=raw:raise ValueError('planar recoil native changed while preparing probe')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.planar_recoil-probe-',dir=out.parent) as temporary:
        stage=Path(temporary)/'probe.json';_json(stage,result);os.link(stage,out)
    return result
