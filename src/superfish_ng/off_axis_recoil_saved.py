# SPDX-License-Identifier: Apache-2.0
"""Off-axis reduced-flux coefficients, explicit reference and full 3D replay."""
import hashlib,os,tempfile
from pathlib import Path
import numpy as np
from .config import keys
from .project import parse_json
from .coaxial_saved import FILES,_json,_arrays,_snapshot as _file_snapshot
from .off_axis_recoil import (OffAxisRecoilCase,OffAxisRecoilSolution,
    solve_off_axis_recoil,off_axis_recoil_quantities)


def _snapshot(directory):
    directory=Path(directory)
    if directory.is_symlink():raise ValueError('off-axis recoil native directory must not be a symbolic link')
    try:return _file_snapshot(directory)
    except ValueError as exc:raise ValueError(str(exc).replace('coaxial','off-axis recoil')) from exc


def _mesh_arrays(solution):
    space=solution.space;p=space.partition;mesh=p.mesh
    return dict(points_rz_m=mesh.points_rz_m,triangles=mesh.triangles,boundary_edges=mesh.boundary_edges,
        boundary_cells=mesh.boundary_cells,boundary_local_vertices=mesh.boundary_local_vertices,
        dof_points_rz_m=space.dof_points,cell_dofs=space.cell_dofs,boundary_dofs=space.boundary_dofs,
        cell_region_indices=p.cell_region_indices,mu_r_tensor=p.mu_r_tensor,reluctivity_tensor_m_per_h=p.reluctivity_tensor_m_per_h,
        remanent_b_t=p.remanent_b_t,remanent_h_a_per_m=p.remanent_h_a_per_m,region_orientation_rad=np.array([v.orientation_rad for v in p.regions]),azimuthal_mu_r=p.azimuthal_mu_r,
        interface_edges=p.interface_edges,interface_cells=p.interface_cells,interface_region_indices=p.interface_region_indices,
        interface_coefficient_jumps=p.interface_coefficient_jumps,boundary_region_indices=p.boundary_region_indices,
        region_area_m2=p.region_area_m2,region_volume_m3=p.region_volume_m3,
        boundary_components=mesh.boundary_components,boundary_segments=mesh.boundary_segments,
        boundary_owner_indices=solution.case.boundary_owner_indices,free_dofs=solution.free_dofs,
        current_load_a=solution.current_load_a,remanent_load_a=solution.remanent_load_a,boundary_load_a=solution.boundary_load_a)


def _field_arrays(solution):
    return dict(psi_relative_to_reference_wb=solution.psi_relative_to_reference_wb,
        reference_psi_wb=np.asarray(solution.reference_psi_wb),psi_wb=solution.psi_wb)


def restore_off_axis_recoil(case,fields):
    if type(case) is not OffAxisRecoilCase:raise ValueError('explicit OffAxisRecoilCase required')
    expected={'psi_relative_to_reference_wb','reference_psi_wb','psi_wb'}
    if not isinstance(fields,dict) or fields.keys()!=expected:raise ValueError('unexpected off-axis recoil field arrays')
    if any(not isinstance(value,np.ndarray) or value.dtype!=np.dtype('float64') or not np.isfinite(value).all() for value in fields.values()):
        raise ValueError('off-axis recoil native fields require finite float64 arrays')
    # Re-solving the unique anchored system also checks that the stored
    # coefficients belong to this exact permeability/current/boundary problem.
    fresh=solve_off_axis_recoil(case);c=fields['psi_relative_to_reference_wb'].copy();reference=fields['reference_psi_wb']
    if c.shape!=fresh.psi_wb.shape or fields['psi_wb'].shape!=c.shape or reference.shape!=() or float(reference)!=fresh.reference_psi_wb:
        raise ValueError('off-axis recoil native potential dimensions or reference psi boundary disagree')
    absolute=c+fresh.reference_psi_wb
    if not np.array_equal(absolute,fields['psi_wb']):raise ValueError('off-axis recoil absolute potential disagrees with its stored reference and coefficients')
    fixed=np.unique(np.concatenate(list(fresh.fixed_boundary_dofs.values())))
    if not np.array_equal(c[fixed],fresh.psi_relative_to_reference_wb[fixed]):raise ValueError('off-axis recoil coefficients violate fixed psi boundary values')
    scale=max(np.linalg.norm(c),np.linalg.norm(fresh.psi_relative_to_reference_wb))
    difference=float(np.linalg.norm(c-fresh.psi_relative_to_reference_wb)/scale) if scale else 0.
    force=fresh.stiffness@c;load=fresh.current_load_a+fresh.remanent_load_a+fresh.boundary_load_a;denominator=np.linalg.norm(force)+np.linalg.norm(load)
    residual=float(np.linalg.norm((force-load)[fresh.free_dofs])/denominator) if denominator else 0.
    if not np.isfinite([difference,residual]).all() or max(difference,residual)>1e-10:
        raise ValueError('off-axis recoil stored coefficients fail reconstructed Poisson solution or free-DOF residual validation')
    c.setflags(write=False);absolute.setflags(write=False)
    restored=OffAxisRecoilSolution(fresh.case,fresh.space,fresh.stiffness,fresh.current_load_a,fresh.remanent_load_a,fresh.boundary_load_a,
        absolute,c,fresh.reference_psi_wb,fresh.free_dofs,fresh.fixed_boundary_dofs,fresh.assembly_report,residual)
    off_axis_recoil_quantities(restored)
    return restored


def off_axis_recoil_result(solution):
    if type(solution) is not OffAxisRecoilSolution:raise ValueError('off-axis recoil result requires OffAxisRecoilSolution')
    case=solution.case;p=case.partition;mesh=p.mesh
    return dict(format='superfish_ng_off_axis_recoil_result',schema_version=1,physics='linear_recoil_magnetostatic',
        case=case.to_dict(),coefficient_field='psi_relative_to_reference_wb; psi=r*Aphi[Wb] = reference_psi_wb + coefficient',
        conventions=dict(coordinates='r,z in metres; strictly positive-radius straight magnetic domain with optional holes',
            material='positive principal recoil mu_r and local remanent B[T], explicit meridional region orientation; nu=(mu0*mu_rec)^-1[m/H]',
            azimuthal_model=p.to_dict()['azimuthal_model'],volume_measure='2*pi*r dr dz; full surface of revolution',
            fields='psi=r*Aphi[Wb], Aphi=psi/r[Wb/m], Br=-psi_z/r, Bz=psi_r/r[T], original H=nu*(B-Brem)[A/m]',
            volume_current='free Jphi[A/m^2], explicit in every region; cross-section integral Jphi dr dz is current[A]',
            remanent_load='integral B_i dot nu*Brem dV [A], separate from free current and boundary loads; constant-psi work is zero',
            boundaries='every edge fixed psi[Wb] or tangential H[A/m]; at least one fixed psi; domain-left tangent in r,z',
            boundary_load='+2*pi*integral Ht*Ni ds [A]',fixed_boundary_reaction='+2*pi*integral original Ht ds [A]; original and discrete reaction separate',
            flux='2*pi*integral r*original B dot outward normal ds [Wb]; no excluded-axis absolute flux',
            reference='first fixed-psi reference, relative and absolute psi retained; a constant psi shift adds C/r to Aphi and preserves B/H/potentials',
            constitutive_potentials='W0=integral(.5*B.nu.B-B.nu.Brem) references B=0; Ws=integral(.5*(B-Brem).nu.(B-Brem)) references H=0; full 3D [J]; both B derivatives are H',
            potential_constant='.5 integral Brem.nu.Brem dV [J]; Ws=W0+constant; no absolute magnet internal energy',
            probes='original cell derivatives; lowest cell at exactly represented shared edges/vertices; rounded coordinates may lie in either cell; no averaging',
            accuracy='discrete work and current identities do not bound original field/circulation error; no irreversible demagnetization, force or winding inductance is inferred'),
        topology=dict(connected_magnetic_domain=True,axis_present=False,holes=len(mesh.holes_rz_m),boundary_components=len(mesh.holes_rz_m)+1,
            volume_m3=mesh.volume_m3,euler_characteristic=1-len(mesh.holes_rz_m)),
        reference_psi_wb=solution.reference_psi_wb,
        fixed_boundary_dofs={name:dofs.tolist() for name,dofs in solution.fixed_boundary_dofs.items()},
        assembly=solution.assembly_report,quantities=off_axis_recoil_quantities(solution))


def save_off_axis_recoil_run(case,solution,directory):
    if type(case) is not OffAxisRecoilCase or type(solution) is not OffAxisRecoilSolution or solution.case.to_dict()!=case.to_dict():
        raise ValueError('off-axis recoil case and solution disagree')
    request=case.to_dict();actual={k:v.copy() for k,v in _mesh_arrays(solution).items()};fields={k:v.copy() for k,v in _field_arrays(solution).items()}
    verified=restore_off_axis_recoil(OffAxisRecoilCase.from_dict(request),fields);expected=_mesh_arrays(verified)
    if actual.keys()!=expected.keys() or any(not np.array_equal(actual[k],v) for k,v in expected.items()):
        raise ValueError('off-axis recoil solution geometry, material, boundary loads or DOFs disagree with the Case')
    if not np.array_equal(solution.space.mesh.points,verified.space.mesh.points) or not np.array_equal(solution.space.mesh.triangles,verified.space.mesh.triangles):
        raise ValueError('off-axis recoil FEM geometry disagrees with its material partition')
    result=off_axis_recoil_result(verified)
    if (case.to_dict()!=request or solution.case.to_dict()!=request or any(not np.array_equal(_field_arrays(solution)[k],v) for k,v in fields.items())
        or any(not np.array_equal(_mesh_arrays(solution)[k],v) for k,v in actual.items())):
        raise ValueError('off-axis recoil input changed during publication verification')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='.off_axis_recoil-staging-',dir=directory) as temporary:
        stage=Path(temporary);_json(stage/'case.json',request);_json(stage/'results.json',result)
        np.savez_compressed(stage/'mesh.npz',**expected);np.savez_compressed(stage/'fields.npz',**_field_arrays(verified))
        _json(stage/'manifest.json',dict(format='superfish_ng_off_axis_recoil_manifest',schema_version=1,
            files={name:hashlib.sha256((stage/name).read_bytes()).hexdigest() for name in sorted(FILES)}))
        for name in sorted(FILES):os.link(stage/name,directory/name)
        os.link(stage/'manifest.json',directory/'manifest.json')
    return result


def read_off_axis_recoil_run(directory):
    directory=Path(directory);raw=_snapshot(directory);manifest=parse_json(raw['manifest.json'].decode('utf-8'))
    names=['format','schema_version','files'];keys(manifest,names,names,'off-axis recoil manifest')
    if (manifest['format']!='superfish_ng_off_axis_recoil_manifest' or type(manifest['schema_version']) is not int or manifest['schema_version']!=1):
        raise ValueError('unsupported off-axis recoil manifest format')
    if manifest['files']!={name:hashlib.sha256(raw[name]).hexdigest() for name in sorted(FILES)}:raise ValueError('off-axis recoil native content hash mismatch')
    case=OffAxisRecoilCase.from_dict(parse_json(raw['case.json'].decode('utf-8')))
    solution=restore_off_axis_recoil(case,_arrays(raw['fields.npz']));expected=_mesh_arrays(solution);actual=_arrays(raw['mesh.npz'])
    if (actual.keys()!=expected.keys() or any(actual[k].dtype!=v.dtype or not np.array_equal(actual[k],v) for k,v in expected.items())):
        raise ValueError('saved off-axis recoil geometry, material, boundary loads or DOFs disagree with the Case')
    if parse_json(raw['results.json'].decode('utf-8'))!=off_axis_recoil_result(solution):
        raise ValueError('saved off-axis recoil current, energy, flux or conventions disagree with Poisson replay')
    if _snapshot(directory)!=raw:raise ValueError('off-axis recoil native changed during verification')
    return solution


def export_off_axis_recoil_probe(run,out,points_rz_m):
    run,out=Path(run),Path(out)
    if out.resolve().is_relative_to(run.resolve()):raise ValueError('off-axis recoil probe output must be outside the native directory')
    raw=_snapshot(run);solution=read_off_axis_recoil_run(run)
    result=dict(format='superfish_ng_off_axis_recoil_probe',schema_version=1,**solution.probe_at(points_rz_m),
        conventions=off_axis_recoil_result(solution)['conventions'],native_sha256={name:hashlib.sha256(data).hexdigest() for name,data in raw.items()})
    if _snapshot(run)!=raw:raise ValueError('off-axis recoil native changed while preparing probe')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.off_axis_recoil-probe-',dir=out.parent) as temporary:
        stage=Path(temporary)/'probe.json';_json(stage,result);os.link(stage,out)
    return result
