# SPDX-License-Identifier: Apache-2.0
"""Planar static native coefficients and complete Poisson replay per unit length."""
import hashlib,os,tempfile
from pathlib import Path
import numpy as np
from .config import keys
from .project import parse_json
from .coaxial_saved import FILES,_json,_arrays,_snapshot as _file_snapshot
from .planar_electrostatic import (PlanarElectrostaticCase,PlanarElectrostaticSolution,
    solve_planar_electrostatic,planar_electrostatic_quantities)


def _snapshot(directory):
    directory=Path(directory)
    if directory.is_symlink():raise ValueError('planar electrostatic native directory must not be a symbolic link')
    try:return _file_snapshot(directory)
    except ValueError as exc:raise ValueError(str(exc).replace('coaxial','planar electrostatic')) from exc


def _mesh_arrays(solution):
    space=solution.space;p=space.partition;mesh=p.mesh
    return dict(points_xy_m=mesh.points_xy_m,triangles=mesh.triangles,boundary_edges=mesh.boundary_edges,
        boundary_cells=mesh.boundary_cells,boundary_local_vertices=mesh.boundary_local_vertices,
        dof_points_xy_m=space.dof_points_xy_m,cell_dofs=space.cell_dofs,boundary_dofs=space.boundary_dofs,
        cell_region_indices=p.cell_region_indices,epsilon_r=p.epsilon_r,
        interface_edges=p.interface_edges,interface_cells=p.interface_cells,interface_region_indices=p.interface_region_indices,
        interface_coefficient_jumps=p.interface_coefficient_jumps,boundary_region_indices=p.boundary_region_indices,
        region_area_m2=p.region_area_m2,
        boundary_owner_indices=solution.case.boundary_owner_indices,free_dofs=solution.free_dofs,
        volume_load_c_per_m=solution.volume_load_c_per_m,boundary_load_c_per_m=solution.boundary_load_c_per_m)


def _field_arrays(solution):
    return dict(potential_relative_to_reference_v=solution.potential_relative_to_reference_v,
        reference_potential_v=np.asarray(solution.reference_potential_v),potential_v=solution.potential_v)


def restore_planar_electrostatic(case,fields):
    if type(case) is not PlanarElectrostaticCase:raise ValueError('explicit PlanarElectrostaticCase required')
    expected={'potential_relative_to_reference_v','reference_potential_v','potential_v'}
    if not isinstance(fields,dict) or fields.keys()!=expected:raise ValueError('unexpected planar electrostatic field arrays')
    if any(not isinstance(value,np.ndarray) or value.dtype!=np.dtype('float64') or not np.isfinite(value).all() for value in fields.values()):
        raise ValueError('planar electrostatic native fields require finite float64 arrays')
    # Re-solving the unique anchored system also checks that the stored
    # coefficients belong to this exact dielectric/charge/boundary problem.
    fresh=solve_planar_electrostatic(case);c=fields['potential_relative_to_reference_v'].copy();reference=fields['reference_potential_v']
    if c.shape!=fresh.potential_v.shape or fields['potential_v'].shape!=c.shape or reference.shape!=() or float(reference)!=fresh.reference_potential_v:
        raise ValueError('planar electrostatic native potential dimensions or reference electrode disagree')
    absolute=c+fresh.reference_potential_v
    if not np.array_equal(absolute,fields['potential_v']):raise ValueError('planar electrostatic absolute potential disagrees with its stored reference and coefficients')
    fixed=np.unique(np.concatenate(list(fresh.electrode_dofs.values())))
    if not np.array_equal(c[fixed],fresh.potential_relative_to_reference_v[fixed]):raise ValueError('planar electrostatic coefficients violate fixed electrode potentials')
    scale=max(np.linalg.norm(c),np.linalg.norm(fresh.potential_relative_to_reference_v))
    difference=float(np.linalg.norm(c-fresh.potential_relative_to_reference_v)/scale) if scale else 0.
    force=fresh.stiffness@c;load=fresh.volume_load_c_per_m+fresh.boundary_load_c_per_m;denominator=np.linalg.norm(force)+np.linalg.norm(load)
    residual=float(np.linalg.norm((force-load)[fresh.free_dofs])/denominator) if denominator else 0.
    if not np.isfinite([difference,residual]).all() or max(difference,residual)>1e-10:
        raise ValueError('planar electrostatic stored coefficients fail reconstructed Poisson solution or free-DOF residual validation')
    c.setflags(write=False);absolute.setflags(write=False)
    restored=PlanarElectrostaticSolution(fresh.case,fresh.space,fresh.stiffness,fresh.volume_load_c_per_m,fresh.boundary_load_c_per_m,
        absolute,c,fresh.reference_potential_v,fresh.free_dofs,fresh.electrode_dofs,fresh.assembly_report,residual)
    planar_electrostatic_quantities(restored)
    return restored


def planar_electrostatic_result(solution):
    if type(solution) is not PlanarElectrostaticSolution:raise ValueError('planar electrostatic result requires PlanarElectrostaticSolution')
    case=solution.case;p=case.partition;mesh=p.mesh
    return dict(format='superfish_ng_planar_electrostatic_result',schema_version=1,physics='linear_electrostatic',
        case=case.to_dict(),coefficient_field='potential_relative_to_reference_v; Phi[V] = reference_potential_v + coefficient',
        conventions=dict(coordinates='x,y in metres; explicit straight dielectric-conforming triangles',
            material='positive real isotropic linear epsilon_r, constant per explicitly assigned cell',
            volume_measure='dx dy per metre of uniform extrusion; no implicit thickness or rotation axis',
            fields='static real Phi[V], E=-grad(Phi)[V/m], D=epsilon0*epsilon_r(original cell)*E[C/m^2]',
            volume_charge='rho[C/m^3]; div(D)=rho; explicit signed value in every region',
            boundaries='every edge is an electrode potential[V] or outward Dn[C/m^2]',
            boundary_load='-integral outward_Dn*Ni ds [C/m]',electrode_charge='minus outward D flux from dielectric into electrode [C/m]',
            energy='integral epsilon*|E|^2/2 dxdy [J/m]; static per unit length, no RF phasor factor',
            capacitance='only two unequal fixed electrodes with rho=0 and other Dn=0; Q/deltaV and 2U/deltaV^2 [F/m]',
            probes='original-cell derivatives; lowest original cell at interfaces, no averaging',
            accuracy='discrete residual and reaction conservation do not bound original E/D or surface-flux error'),
        topology=dict(connected_dielectric_domain=True,holes=0,boundary_components=1,area_m2=mesh.area_m2,euler_characteristic=1),
        reference_potential_v=solution.reference_potential_v,
        electrode_dofs={name:dofs.tolist() for name,dofs in solution.electrode_dofs.items()},
        assembly=solution.assembly_report,quantities=planar_electrostatic_quantities(solution))


def save_planar_electrostatic_run(case,solution,directory):
    if type(case) is not PlanarElectrostaticCase or type(solution) is not PlanarElectrostaticSolution or solution.case.to_dict()!=case.to_dict():
        raise ValueError('planar electrostatic case and solution disagree')
    request=case.to_dict();actual={k:v.copy() for k,v in _mesh_arrays(solution).items()};fields={k:v.copy() for k,v in _field_arrays(solution).items()}
    verified=restore_planar_electrostatic(PlanarElectrostaticCase.from_dict(request),fields);expected=_mesh_arrays(verified)
    if actual.keys()!=expected.keys() or any(not np.array_equal(actual[k],v) for k,v in expected.items()):
        raise ValueError('planar electrostatic solution geometry, material, boundary loads or DOFs disagree with the Case')
    if not np.array_equal(solution.space.mesh.points,verified.space.mesh.points) or not np.array_equal(solution.space.mesh.triangles,verified.space.mesh.triangles):
        raise ValueError('planar electrostatic FEM geometry disagrees with its material partition')
    result=planar_electrostatic_result(verified)
    if (case.to_dict()!=request or solution.case.to_dict()!=request or any(not np.array_equal(_field_arrays(solution)[k],v) for k,v in fields.items())
        or any(not np.array_equal(_mesh_arrays(solution)[k],v) for k,v in actual.items())):
        raise ValueError('planar electrostatic input changed during publication verification')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='.planar_electrostatic-staging-',dir=directory) as temporary:
        stage=Path(temporary);_json(stage/'case.json',request);_json(stage/'results.json',result)
        np.savez_compressed(stage/'mesh.npz',**expected);np.savez_compressed(stage/'fields.npz',**_field_arrays(verified))
        _json(stage/'manifest.json',dict(format='superfish_ng_planar_electrostatic_manifest',schema_version=1,
            files={name:hashlib.sha256((stage/name).read_bytes()).hexdigest() for name in sorted(FILES)}))
        for name in sorted(FILES):os.link(stage/name,directory/name)
        os.link(stage/'manifest.json',directory/'manifest.json')
    return result


def read_planar_electrostatic_run(directory):
    directory=Path(directory);raw=_snapshot(directory);manifest=parse_json(raw['manifest.json'].decode('utf-8'))
    names=['format','schema_version','files'];keys(manifest,names,names,'planar electrostatic manifest')
    if (manifest['format']!='superfish_ng_planar_electrostatic_manifest' or type(manifest['schema_version']) is not int or manifest['schema_version']!=1):
        raise ValueError('unsupported planar electrostatic manifest format')
    if manifest['files']!={name:hashlib.sha256(raw[name]).hexdigest() for name in sorted(FILES)}:raise ValueError('planar electrostatic native content hash mismatch')
    case=PlanarElectrostaticCase.from_dict(parse_json(raw['case.json'].decode('utf-8')))
    solution=restore_planar_electrostatic(case,_arrays(raw['fields.npz']));expected=_mesh_arrays(solution);actual=_arrays(raw['mesh.npz'])
    if (actual.keys()!=expected.keys() or any(actual[k].dtype!=v.dtype or not np.array_equal(actual[k],v) for k,v in expected.items())):
        raise ValueError('saved planar electrostatic geometry, material, boundary loads or DOFs disagree with the Case')
    if parse_json(raw['results.json'].decode('utf-8'))!=planar_electrostatic_result(solution):
        raise ValueError('saved planar electrostatic charge, energy, capacitance or conventions disagree with Poisson replay')
    if _snapshot(directory)!=raw:raise ValueError('planar electrostatic native changed during verification')
    return solution


def export_planar_electrostatic_probe(run,out,points_xy_m):
    run,out=Path(run),Path(out)
    if out.resolve().is_relative_to(run.resolve()):raise ValueError('planar electrostatic probe output must be outside the native directory')
    raw=_snapshot(run);solution=read_planar_electrostatic_run(run)
    result=dict(format='superfish_ng_planar_electrostatic_probe',schema_version=1,**solution.probe_at(points_xy_m),
        conventions=planar_electrostatic_result(solution)['conventions'],native_sha256={name:hashlib.sha256(data).hexdigest() for name,data in raw.items()})
    if _snapshot(run)!=raw:raise ValueError('planar electrostatic native changed while preparing probe')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.planar_electrostatic-probe-',dir=out.parent) as temporary:
        stage=Path(temporary)/'probe.json';_json(stage,result);os.link(stage,out)
    return result
