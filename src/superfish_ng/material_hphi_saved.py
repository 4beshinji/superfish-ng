# SPDX-License-Identifier: Apache-2.0
"""Dedicated material Hphi native files with complete material/geometry/FEM/RF replay."""
import hashlib
import os
from pathlib import Path
import tempfile
import numpy as np
from .config import integer,keys
from .project import parse_json
from .coaxial_saved import FILES,_json,_arrays,_snapshot as _file_snapshot
from .material_hphi import MaterialHphiCase,MaterialHphiSolution,restore_material_hphi
from .material_hphi_rf import material_hphi_quantities


def _snapshot(directory):
    directory=Path(directory)
    if directory.is_symlink():raise ValueError('material Hphi native directory must not be a symbolic link')
    try:return _file_snapshot(directory)
    except ValueError as exc:raise ValueError(str(exc).replace('coaxial','material Hphi')) from exc


def _mesh_arrays(space):
    p=space.partition;mesh=p.mesh
    return dict(points_rz_m=mesh.points_rz_m,triangles=mesh.triangles,boundary_edges=mesh.boundary_edges,
        boundary_cells=mesh.boundary_cells,boundary_local_vertices=mesh.boundary_local_vertices,
        boundary_components=mesh.boundary_components,boundary_segments=mesh.boundary_segments,boundary_tags=space.mesh.boundary_tags,
        dof_points_rz_m=space.dof_points,cell_dofs=space.cell_dofs,boundary_dofs=space.boundary_dofs,axis_dofs=space.axis_dofs,
        cell_region_indices=p.cell_region_indices,epsilon_r=p.epsilon_r,mu_r=p.mu_r,
        interface_edges=p.interface_edges,interface_cells=p.interface_cells,interface_region_indices=p.interface_region_indices,
        interface_coefficient_jumps=p.interface_coefficient_jumps,boundary_region_indices=p.boundary_region_indices,
        region_area_m2=p.region_area_m2,region_volume_m3=p.region_volume_m3)


def material_hphi_result(solution):
    if type(solution) is not MaterialHphiSolution:raise ValueError('material Hphi result requires MaterialHphiSolution')
    case=solution.case;p=case.partition;mesh=p.mesh;axis=case.axis_connected
    return dict(format='superfish_ng_material_hphi_result',schema_version=1,physics='material_axisymmetric_hphi_rf',
        case=case.to_dict(),coefficient_field=('u_real_A_per_m2 = Hphi_real_A_per_m / r_m; finite axis limit retained' if axis
                                           else 'q_real_A = r_m * Hphi_real_A_per_m'),
        conventions=dict(coordinates='r,z in metres; explicit straight material-conforming triangles',
            material='positive real isotropic linear nondispersive lossless epsilon_r/mu_r, constant per declared cell',
            volume_measure='2*pi*r dr dz; full 3D material domain excluding conductor holes',
            phasor='peak exp(+i omega t); field = real + i*quadrature',
            fields=('Hphi=r*u; Er_quadrature=r*u_z/(omega*epsilon0*epsilon_r); Ez_quadrature=-(2*u+r*u_r)/(omega*epsilon0*epsilon_r)' if axis
                    else 'Hphi=q/r; Er_quadrature=q_z/(omega*epsilon0*epsilon_r*r); Ez_quadrature=-q_r/(omega*epsilon0*epsilon_r*r)'),
            magnetic_flux='B=mu0*mu_r(original cell)*H; no vacuum substitution at interfaces',
            normalization='total time-averaged material-weighted energy in J; no per-length conversion',
            wall_loss='all PEC components, W; Rs=sqrt(pi*f*mu0/sigma) for nonmagnetic wall metal; zero volume loss',
            boundary_order='outer first, then holes in declared order; segments follow each source contour',
            acceleration='only explicitly declared vacuum axis interval; phase exp(+i*omega*(z-origin)/(beta*c))',
            r_over_q_accelerator='abs(Vacc)^2/(omega*U), ohm',r_over_q_circuit='abs(Vacc)^2/(2*omega*U), ohm',
            spectrum='lowest positive FEM frequencies in m=0 Hphi family; index is not a mode identity',
            probes='original-cell derivatives and material; lowest original cell at interfaces; no averaging'),
        topology=dict(connected_material_domain=True,holes=len(mesh.holes_rz_m),boundary_components=1+len(mesh.holes_rz_m),
            axis_interval_m=list(mesh.axis_interval_m) if axis else None,euler_characteristic=mesh.euler_characteristic,
            area_m2=mesh.area_m2,volume_m3=mesh.volume_m3),
        material_partition=dict(regions=[r.to_dict() for r in p.regions],materials=[m.to_dict() for m in p.materials],
            interface_edges=p.interface_edges.tolist(),interface_cells=p.interface_cells.tolist(),
            interface_region_indices=p.interface_region_indices.tolist(),interface_coefficient_jumps=p.interface_coefficient_jumps.tolist(),
            region_area_m2=p.region_area_m2.tolist(),region_volume_m3=p.region_volume_m3.tolist()),
        excluded_nullspace=dict(dimension=0 if axis else 1,
            reason='constant q is not regular on the axis' if axis else 'constant q represents static circulating Hphi proportional to 1/r',
            scope='this Hphi space only; not all static Maxwell field families'),
        residuals=solution.residuals.tolist(),orthogonality_error=solution.orthogonality_error,
        nullspace_overlap=solution.nullspace_overlap,matrix_quadrature=solution.quadrature_diagnostic,
        modes=[material_hphi_quantities(solution,i) for i in range(case.modes)])


def save_material_hphi_run(case,solution,directory):
    if type(case) is not MaterialHphiCase or type(solution) is not MaterialHphiSolution or solution.case.to_dict()!=case.to_dict():
        raise ValueError('material Hphi case and solution disagree')
    request=case.to_dict();actual={k:v.copy() for k,v in _mesh_arrays(solution.space).items()}
    coefficients=solution.coefficients.copy();frequencies=solution.frequencies_hz.copy()
    verified=restore_material_hphi(MaterialHphiCase.from_dict(request),coefficients,frequencies)
    expected=_mesh_arrays(verified.space)
    if actual.keys()!=expected.keys() or any(not np.array_equal(actual[k],v) for k,v in expected.items()):
        raise ValueError('material Hphi solution material, geometry, topology or DOFs differ from the declared input')
    result=material_hphi_result(verified)
    if (case.to_dict()!=request or solution.case.to_dict()!=request
        or not np.array_equal(solution.coefficients,coefficients) or not np.array_equal(solution.frequencies_hz,frequencies)
        or any(not np.array_equal(_mesh_arrays(solution.space)[k],v) for k,v in actual.items())):
        raise ValueError('material Hphi input changed during publication verification')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='.material-hphi-staging-',dir=directory) as temporary:
        stage=Path(temporary);_json(stage/'case.json',request);_json(stage/'results.json',result)
        np.savez_compressed(stage/'mesh.npz',**expected)
        np.savez_compressed(stage/'fields.npz',coefficients=verified.coefficients,frequencies_hz=verified.frequencies_hz)
        _json(stage/'manifest.json',dict(format='superfish_ng_material_hphi_manifest',schema_version=1,
            files={name:hashlib.sha256((stage/name).read_bytes()).hexdigest() for name in sorted(FILES)}))
        for name in sorted(FILES):os.link(stage/name,directory/name)
        os.link(stage/'manifest.json',directory/'manifest.json')
    return result


def read_material_hphi_run(directory):
    directory=Path(directory);raw=_snapshot(directory)
    manifest=parse_json(raw['manifest.json'].decode('utf-8'));names=['format','schema_version','files'];keys(manifest,names,names,'material Hphi manifest')
    if (manifest['format']!='superfish_ng_material_hphi_manifest' or type(manifest['schema_version']) is not int
        or manifest['schema_version']!=1):raise ValueError('unsupported material Hphi manifest format')
    if manifest['files']!={name:hashlib.sha256(raw[name]).hexdigest() for name in sorted(FILES)}:
        raise ValueError('material Hphi native content hash mismatch')
    case=MaterialHphiCase.from_dict(parse_json(raw['case.json'].decode('utf-8')))
    fields=_arrays(raw['fields.npz'])
    if fields.keys()!={'coefficients','frequencies_hz'}:raise ValueError('unexpected material Hphi field arrays')
    solution=restore_material_hphi(case,fields['coefficients'],fields['frequencies_hz'])
    expected=_mesh_arrays(solution.space);actual=_arrays(raw['mesh.npz'])
    if (actual.keys()!=expected.keys() or any(actual[k].dtype.kind!=v.dtype.kind or not np.array_equal(actual[k],v) for k,v in expected.items())):
        raise ValueError('saved material Hphi mesh, material partition, topology or DOFs disagree with the declared input')
    if parse_json(raw['results.json'].decode('utf-8'))!=material_hphi_result(solution):
        raise ValueError('material Hphi saved RF, material, geometry, nullspace or conventions disagree with FEM replay')
    if _snapshot(directory)!=raw:raise ValueError('material Hphi native changed during verification')
    return solution


def export_material_hphi_probe(run,out,points_rz_m,mode=1):
    integer(mode,'mode',1);run,out=Path(run),Path(out)
    if out.resolve().is_relative_to(run.resolve()):raise ValueError('material Hphi probe output must be outside the native directory')
    raw=_snapshot(run);solution=read_material_hphi_run(run);probe=solution.probe_at(points_rz_m,mode-1)
    result=dict(format='superfish_ng_material_hphi_probe',schema_version=1,mode=mode,**probe,
        conventions=material_hphi_result(solution)['conventions'],native_sha256={name:hashlib.sha256(data).hexdigest() for name,data in raw.items()})
    if _snapshot(run)!=raw:raise ValueError('material Hphi native changed while preparing probe')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.material-hphi-probe-',dir=out.parent) as temporary:
        stage=Path(temporary)/'probe.json';_json(stage,result);os.link(stage,out)
    return result
