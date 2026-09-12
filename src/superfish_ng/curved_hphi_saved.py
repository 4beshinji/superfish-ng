# SPDX-License-Identifier: Apache-2.0
"""Dedicated curved Hphi native files with complete geometry/FEM/RF replay."""
import hashlib
import os
from pathlib import Path
import tempfile
import numpy as np
from .config import integer,keys
from .constants import MU0
from .project import parse_json
from .coaxial_saved import FILES,_json,_arrays,_snapshot as _file_snapshot
from .curved_hphi import CurvedHphiCase,CurvedHphiSolution,restore_curved_hphi
from .curved_hphi_rf import curved_hphi_quantities


def _snapshot(directory):
    directory=Path(directory)
    if directory.is_symlink():raise ValueError('curved Hphi native directory must not be a symbolic link')
    try:return _file_snapshot(directory)
    except ValueError as exc:raise ValueError(str(exc).replace('coaxial','curved Hphi')) from exc


def _mesh_arrays(space):
    g=space.geometry;base=g.base_mesh
    return dict(base_points_rz_m=base.points_rz_m,base_triangles=base.triangles,
        base_boundary_edges=base.boundary_edges,boundary_cells=base.boundary_cells,
        boundary_local_vertices=base.boundary_local_vertices,boundary_components=base.boundary_components,
        boundary_segments=base.boundary_segments,geometry_points_rz_m=g.points_rz_m,
        geometry_cell_nodes=g.cell_nodes,geometry_boundary_nodes=g.boundary_nodes,boundary_tags=g.boundary_tags,
        edge_vertices=g.edge_vertices,edge_midpoints_rz_m=g.edge_midpoints_rz_m,
        dof_points_rz_m=space.dof_points,cell_dofs=space.cell_dofs,boundary_dofs=space.boundary_dofs,axis_dofs=space.axis_dofs)


def curved_hphi_result(solution):
    if type(solution) is not CurvedHphiSolution:raise ValueError('curved Hphi result requires a CurvedHphiSolution')
    case=solution.case;g=case.geometry;base=g.base_mesh;axis=case.axis_connected
    return dict(format='superfish_ng_curved_hphi_result',schema_version=1,physics='curved_axisymmetric_hphi_rf',
        case=case.to_dict(),coefficient_field=('u_real_A_per_m2 = Hphi_real_A_per_m / r_m; finite axis limit retained' if axis
                                           else 'q_real_A = r_m * Hphi_real_A_per_m'),
        conventions=dict(coordinates='r,z in metres; explicitly mapped quadratic polynomial geometry',
            geometry='all vertices, edge midpoint nodes and connectivity retained; not an exact conic representation',
            volume_measure='2*pi*r dr dz; full 3D vacuum excluding conductor holes',
            phasor='peak exp(+i omega t); field = real + i*quadrature',
            fields=('Hphi=r*u; Er_quadrature=r*u_z/(omega*epsilon0); Ez_quadrature=-(2*u+r*u_r)/(omega*epsilon0)' if axis
                    else 'Hphi=q/r; Er_quadrature=q_z/(omega*epsilon0*r); Ez_quadrature=-q_r/(omega*epsilon0*r)'),
            normalization='total time-averaged energy in J; no per-length conversion',
            wall_loss='all PEC components with actual quadratic arc length, W; holes add loss and the axis has zero area',
            boundary_order='outer first, then holes in declared order; segments follow each source contour',
            acceleration='only the explicitly declared vacuum axis interval; phase exp(+i*omega*(z-origin)/(beta*c))',
            r_over_q_accelerator='abs(Vacc)^2/(omega*U), ohm',r_over_q_circuit='abs(Vacc)^2/(2*omega*U), ohm',
            spectrum='lowest positive FEM frequencies in m=0 Hphi family; index is not a mode identity',
            probes='original-cell physical derivatives; first accepted cell at shared boundaries; no smoothing'),
        topology=dict(connected_vacuum=True,holes=len(base.holes_rz_m),boundary_components=1+len(base.holes_rz_m),
            axis_interval_m=list(base.axis_interval_m) if axis else None,euler_characteristic=base.euler_characteristic,
            area_m2=g.area_m2,volume_m3=g.volume_m3,bounds_rz_m=[list(p) for p in case.bounds_rz_m]),
        geometry_validation=dict(g.validation),
        excluded_nullspace=dict(dimension=0 if axis else 1,
            reason='constant q is not regular on the vacuum axis' if axis else 'constant q represents static circulating Hphi proportional to 1/r',
            scope='this Hphi space only; not all static Maxwell field families'),
        residuals=solution.residuals.tolist(),orthogonality_error=solution.orthogonality_error,
        nullspace_overlap=solution.nullspace_overlap,matrix_quadrature=solution.quadrature_diagnostic,
        modes=[curved_hphi_quantities(solution,i) for i in range(case.modes)])


def save_curved_hphi_run(case,solution,directory):
    if type(case) is not CurvedHphiCase or type(solution) is not CurvedHphiSolution or solution.case.to_dict()!=case.to_dict():
        raise ValueError('curved Hphi case and solution disagree')
    request=case.to_dict();actual={k:v.copy() for k,v in _mesh_arrays(solution.space).items()}
    coefficients=solution.coefficients.copy();frequencies=solution.frequencies_hz.copy()
    verified=restore_curved_hphi(CurvedHphiCase.from_dict(request),coefficients,frequencies)
    expected=_mesh_arrays(verified.space)
    if actual.keys()!=expected.keys() or any(not np.array_equal(actual[k],v) for k,v in expected.items()):
        raise ValueError('curved Hphi solution geometry, topology or DOFs differ from the declared input')
    result=curved_hphi_result(verified)
    if (case.to_dict()!=request or solution.case.to_dict()!=request
        or not np.array_equal(solution.coefficients,coefficients) or not np.array_equal(solution.frequencies_hz,frequencies)
        or any(not np.array_equal(_mesh_arrays(solution.space)[k],v) for k,v in actual.items())):
        raise ValueError('curved Hphi input changed during publication verification')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='.curved-hphi-staging-',dir=directory) as temporary:
        stage=Path(temporary);_json(stage/'case.json',request);_json(stage/'results.json',result)
        np.savez_compressed(stage/'mesh.npz',**expected)
        np.savez_compressed(stage/'fields.npz',coefficients=verified.coefficients,frequencies_hz=verified.frequencies_hz)
        _json(stage/'manifest.json',dict(format='superfish_ng_curved_hphi_manifest',schema_version=1,
            files={name:hashlib.sha256((stage/name).read_bytes()).hexdigest() for name in sorted(FILES)}))
        for name in sorted(FILES):os.link(stage/name,directory/name)
        os.link(stage/'manifest.json',directory/'manifest.json')
    return result


def read_curved_hphi_run(directory):
    directory=Path(directory);raw=_snapshot(directory)
    manifest=parse_json(raw['manifest.json'].decode('utf-8'));names=['format','schema_version','files'];keys(manifest,names,names,'curved Hphi manifest')
    if (manifest['format']!='superfish_ng_curved_hphi_manifest' or type(manifest['schema_version']) is not int
        or manifest['schema_version']!=1):raise ValueError('unsupported curved Hphi manifest format')
    if manifest['files']!={name:hashlib.sha256(raw[name]).hexdigest() for name in sorted(FILES)}:
        raise ValueError('curved Hphi native content hash mismatch')
    case=CurvedHphiCase.from_dict(parse_json(raw['case.json'].decode('utf-8')))
    fields=_arrays(raw['fields.npz'])
    if fields.keys()!={'coefficients','frequencies_hz'}:raise ValueError('unexpected curved Hphi field arrays')
    solution=restore_curved_hphi(case,fields['coefficients'],fields['frequencies_hz'])
    expected=_mesh_arrays(solution.space);actual=_arrays(raw['mesh.npz'])
    if (actual.keys()!=expected.keys() or any(actual[k].dtype.kind!=v.dtype.kind or not np.array_equal(actual[k],v) for k,v in expected.items())):
        raise ValueError('saved curved Hphi mesh, topology or DOFs disagree with the declared geometry')
    if parse_json(raw['results.json'].decode('utf-8'))!=curved_hphi_result(solution):
        raise ValueError('curved Hphi saved RF, geometry, nullspace or conventions disagree with FEM replay')
    if _snapshot(directory)!=raw:raise ValueError('curved Hphi native changed during verification')
    return solution


def export_curved_hphi_probe(run,out,points_rz_m,mode=1):
    integer(mode,'mode',1);run,out=Path(run),Path(out)
    if out.resolve().is_relative_to(run.resolve()):raise ValueError('curved Hphi probe output must be outside the native directory')
    raw=_snapshot(run);solution=read_curved_hphi_run(run);fields=solution.fields_at(points_rz_m,mode-1)
    for axis in ('r','phi','z'):
        for phase in ('real','quadrature'):fields[f'B{axis}_{phase}_T']=MU0*fields[f'H{axis}_{phase}_A_per_m']
    result=dict(format='superfish_ng_curved_hphi_probe',schema_version=1,mode=mode,
        points_rz_m=np.asarray(points_rz_m,dtype=float).tolist(),fields={k:v.tolist() for k,v in fields.items()},
        conventions=curved_hphi_result(solution)['conventions'],native_sha256={name:hashlib.sha256(data).hexdigest() for name,data in raw.items()})
    if _snapshot(run)!=raw:raise ValueError('curved Hphi native changed while preparing probe')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.curved-hphi-probe-',dir=out.parent) as temporary:
        stage=Path(temporary)/'probe.json';_json(stage,result);os.link(stage,out)
    return result
