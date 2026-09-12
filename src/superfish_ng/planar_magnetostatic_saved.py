# SPDX-License-Identifier: Apache-2.0
"""Planar magnetic native coefficients and complete current-source replay per metre."""
import hashlib,os,tempfile
from pathlib import Path
import numpy as np
from .config import keys
from .project import parse_json
from .coaxial_saved import FILES,_json,_arrays,_snapshot as _file_snapshot
from .planar_magnetostatic import (PlanarMagnetostaticCase,PlanarMagnetostaticSolution,
    solve_planar_magnetostatic,planar_magnetostatic_quantities)


def _snapshot(directory):
    directory=Path(directory)
    if directory.is_symlink():raise ValueError('planar magnetostatic native directory must not be a symbolic link')
    try:return _file_snapshot(directory)
    except ValueError as exc:raise ValueError(str(exc).replace('coaxial','planar magnetostatic')) from exc


def _mesh_arrays(solution):
    space=solution.space;p=space.partition;mesh=p.mesh
    return dict(points_xy_m=mesh.points_xy_m,triangles=mesh.triangles,boundary_edges=mesh.boundary_edges,
        boundary_cells=mesh.boundary_cells,boundary_local_vertices=mesh.boundary_local_vertices,
        dof_points_xy_m=space.dof_points_xy_m,cell_dofs=space.cell_dofs,boundary_dofs=space.boundary_dofs,
        cell_region_indices=p.cell_region_indices,mu_r=p.mu_r,reluctivity_m_per_h=p.reluctivity_m_per_h,
        interface_edges=p.interface_edges,interface_cells=p.interface_cells,interface_region_indices=p.interface_region_indices,
        interface_coefficient_jumps=p.interface_coefficient_jumps,boundary_region_indices=p.boundary_region_indices,
        region_area_m2=p.region_area_m2,
        boundary_owner_indices=solution.case.boundary_owner_indices,free_dofs=solution.free_dofs,
        volume_load_a=solution.volume_load_a,boundary_load_a=solution.boundary_load_a)


def _field_arrays(solution):
    return dict(az_relative_to_reference_wb_per_m=solution.az_relative_to_reference_wb_per_m,
        reference_az_wb_per_m=np.asarray(solution.reference_az_wb_per_m),az_wb_per_m=solution.az_wb_per_m)


def restore_planar_magnetostatic(case,fields):
    if type(case) is not PlanarMagnetostaticCase:raise ValueError('explicit PlanarMagnetostaticCase required')
    expected={'az_relative_to_reference_wb_per_m','reference_az_wb_per_m','az_wb_per_m'}
    if not isinstance(fields,dict) or fields.keys()!=expected:raise ValueError('unexpected planar magnetostatic field arrays')
    if any(not isinstance(value,np.ndarray) or value.dtype!=np.dtype('float64') or not np.isfinite(value).all() for value in fields.values()):
        raise ValueError('planar magnetostatic native fields require finite float64 arrays')
    # Re-solving the unique anchored system also checks that the stored
    # coefficients belong to this exact permeability/current/boundary problem.
    fresh=solve_planar_magnetostatic(case);c=fields['az_relative_to_reference_wb_per_m'].copy();reference=fields['reference_az_wb_per_m']
    if c.shape!=fresh.az_wb_per_m.shape or fields['az_wb_per_m'].shape!=c.shape or reference.shape!=() or float(reference)!=fresh.reference_az_wb_per_m:
        raise ValueError('planar magnetostatic native potential dimensions or reference Az boundary disagree')
    absolute=c+fresh.reference_az_wb_per_m
    if not np.array_equal(absolute,fields['az_wb_per_m']):raise ValueError('planar magnetostatic absolute potential disagrees with its stored reference and coefficients')
    fixed=np.unique(np.concatenate(list(fresh.fixed_boundary_dofs.values())))
    if not np.array_equal(c[fixed],fresh.az_relative_to_reference_wb_per_m[fixed]):raise ValueError('planar magnetostatic coefficients violate fixed Az boundary values')
    scale=max(np.linalg.norm(c),np.linalg.norm(fresh.az_relative_to_reference_wb_per_m))
    difference=float(np.linalg.norm(c-fresh.az_relative_to_reference_wb_per_m)/scale) if scale else 0.
    force=fresh.stiffness@c;load=fresh.volume_load_a+fresh.boundary_load_a;denominator=np.linalg.norm(force)+np.linalg.norm(load)
    residual=float(np.linalg.norm((force-load)[fresh.free_dofs])/denominator) if denominator else 0.
    if not np.isfinite([difference,residual]).all() or max(difference,residual)>1e-10:
        raise ValueError('planar magnetostatic stored coefficients fail reconstructed Poisson solution or free-DOF residual validation')
    c.setflags(write=False);absolute.setflags(write=False)
    restored=PlanarMagnetostaticSolution(fresh.case,fresh.space,fresh.stiffness,fresh.volume_load_a,fresh.boundary_load_a,
        absolute,c,fresh.reference_az_wb_per_m,fresh.free_dofs,fresh.fixed_boundary_dofs,fresh.assembly_report,residual)
    planar_magnetostatic_quantities(restored)
    return restored


def planar_magnetostatic_result(solution):
    if type(solution) is not PlanarMagnetostaticSolution:raise ValueError('planar magnetostatic result requires PlanarMagnetostaticSolution')
    case=solution.case;p=case.partition;mesh=p.mesh
    return dict(format='superfish_ng_planar_magnetostatic_result',schema_version=1,physics='linear_magnetostatic',
        case=case.to_dict(),coefficient_field='az_relative_to_reference_wb_per_m; Az[Wb/m] = reference_az_wb_per_m + coefficient',
        conventions=dict(coordinates='x,y in metres; explicit straight magnetic-material-conforming triangles',
            material='positive real isotropic linear mu_r, constant per explicitly assigned cell; reluctivity=(1/mu0)/mu_r [m/H]',
            volume_measure='dx dy per metre of uniform extrusion; no implicit thickness or rotation axis',
            fields='static real Az[Wb/m], B=(dAz/dy,-dAz/dx)[T], H=reluctivity(original cell)*B[A/m]',
            volume_current='Jz[A/m^2]; curl(H)_z=Jz; explicit signed value in every region',
            boundaries='every edge is fixed Az[Wb/m] or tangential H[A/m]; counterclockwise tangent, outward normal to its right',
            boundary_load='-integral tangential_H*Ni ds [A]',
            fixed_boundary_reaction='minus counterclockwise H line integral on fixed-Az boundary [A]; discrete reaction and original H integral reported separately',
            flux='integral original B dot outward normal ds [Wb/m]',
            energy='integral |B|^2/(2*mu0*mu_r) dxdy [J/m]; static per unit length, no RF phasor factor',
            probes='original-cell derivatives; lowest original cell at interfaces, no averaging',
            accuracy='discrete residual and reaction conservation do not bound original B/H or boundary-circulation error; no winding inductance is inferred'),
        topology=dict(connected_magnetic_domain=True,holes=0,boundary_components=1,area_m2=mesh.area_m2,euler_characteristic=1),
        reference_az_wb_per_m=solution.reference_az_wb_per_m,
        fixed_boundary_dofs={name:dofs.tolist() for name,dofs in solution.fixed_boundary_dofs.items()},
        assembly=solution.assembly_report,quantities=planar_magnetostatic_quantities(solution))


def save_planar_magnetostatic_run(case,solution,directory):
    if type(case) is not PlanarMagnetostaticCase or type(solution) is not PlanarMagnetostaticSolution or solution.case.to_dict()!=case.to_dict():
        raise ValueError('planar magnetostatic case and solution disagree')
    request=case.to_dict();actual={k:v.copy() for k,v in _mesh_arrays(solution).items()};fields={k:v.copy() for k,v in _field_arrays(solution).items()}
    verified=restore_planar_magnetostatic(PlanarMagnetostaticCase.from_dict(request),fields);expected=_mesh_arrays(verified)
    if actual.keys()!=expected.keys() or any(not np.array_equal(actual[k],v) for k,v in expected.items()):
        raise ValueError('planar magnetostatic solution geometry, material, boundary loads or DOFs disagree with the Case')
    if not np.array_equal(solution.space.mesh.points,verified.space.mesh.points) or not np.array_equal(solution.space.mesh.triangles,verified.space.mesh.triangles):
        raise ValueError('planar magnetostatic FEM geometry disagrees with its material partition')
    result=planar_magnetostatic_result(verified)
    if (case.to_dict()!=request or solution.case.to_dict()!=request or any(not np.array_equal(_field_arrays(solution)[k],v) for k,v in fields.items())
        or any(not np.array_equal(_mesh_arrays(solution)[k],v) for k,v in actual.items())):
        raise ValueError('planar magnetostatic input changed during publication verification')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='.planar_magnetostatic-staging-',dir=directory) as temporary:
        stage=Path(temporary);_json(stage/'case.json',request);_json(stage/'results.json',result)
        np.savez_compressed(stage/'mesh.npz',**expected);np.savez_compressed(stage/'fields.npz',**_field_arrays(verified))
        _json(stage/'manifest.json',dict(format='superfish_ng_planar_magnetostatic_manifest',schema_version=1,
            files={name:hashlib.sha256((stage/name).read_bytes()).hexdigest() for name in sorted(FILES)}))
        for name in sorted(FILES):os.link(stage/name,directory/name)
        os.link(stage/'manifest.json',directory/'manifest.json')
    return result


def read_planar_magnetostatic_run(directory):
    directory=Path(directory);raw=_snapshot(directory);manifest=parse_json(raw['manifest.json'].decode('utf-8'))
    names=['format','schema_version','files'];keys(manifest,names,names,'planar magnetostatic manifest')
    if (manifest['format']!='superfish_ng_planar_magnetostatic_manifest' or type(manifest['schema_version']) is not int or manifest['schema_version']!=1):
        raise ValueError('unsupported planar magnetostatic manifest format')
    if manifest['files']!={name:hashlib.sha256(raw[name]).hexdigest() for name in sorted(FILES)}:raise ValueError('planar magnetostatic native content hash mismatch')
    case=PlanarMagnetostaticCase.from_dict(parse_json(raw['case.json'].decode('utf-8')))
    solution=restore_planar_magnetostatic(case,_arrays(raw['fields.npz']));expected=_mesh_arrays(solution);actual=_arrays(raw['mesh.npz'])
    if (actual.keys()!=expected.keys() or any(actual[k].dtype!=v.dtype or not np.array_equal(actual[k],v) for k,v in expected.items())):
        raise ValueError('saved planar magnetostatic geometry, material, boundary loads or DOFs disagree with the Case')
    if parse_json(raw['results.json'].decode('utf-8'))!=planar_magnetostatic_result(solution):
        raise ValueError('saved planar magnetostatic current, energy, flux or conventions disagree with Poisson replay')
    if _snapshot(directory)!=raw:raise ValueError('planar magnetostatic native changed during verification')
    return solution


def export_planar_magnetostatic_probe(run,out,points_xy_m):
    run,out=Path(run),Path(out)
    if out.resolve().is_relative_to(run.resolve()):raise ValueError('planar magnetostatic probe output must be outside the native directory')
    raw=_snapshot(run);solution=read_planar_magnetostatic_run(run)
    result=dict(format='superfish_ng_planar_magnetostatic_probe',schema_version=1,**solution.probe_at(points_xy_m),
        conventions=planar_magnetostatic_result(solution)['conventions'],native_sha256={name:hashlib.sha256(data).hexdigest() for name,data in raw.items()})
    if _snapshot(run)!=raw:raise ValueError('planar magnetostatic native changed while preparing probe')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.planar_magnetostatic-probe-',dir=out.parent) as temporary:
        stage=Path(temporary)/'probe.json';_json(stage,result);os.link(stage,out)
    return result
