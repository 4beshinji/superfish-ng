# SPDX-License-Identifier: Apache-2.0
"""Dedicated axis-connected mesh native files with full topology/FEM/RF replay."""
import hashlib
import os
from pathlib import Path
import tempfile
import numpy as np
from .config import integer, keys
from .constants import MU0
from .project import parse_json
from .coaxial_saved import FILES, _json, _arrays, _snapshot as _file_snapshot
from .axis_hphi import AxisHphiCase, AxisHphiSolution, axis_hphi_matrices, restore_axis_hphi, axis_hphi_quantities


def _snapshot(directory):
    try: return _file_snapshot(directory)
    except ValueError as exc: raise ValueError(str(exc).replace('coaxial','axis Hphi')) from exc


def _mesh_arrays(case,space):
    return dict(points_rz_m=space.mesh.points,triangles=space.mesh.triangles,
        boundary_edges=space.mesh.boundary_edges,boundary_cells=space.mesh.boundary_cells,
        boundary_tags=space.mesh.boundary_tags,axis_nodes=space.mesh.axis_nodes,
        dof_points_rz_m=space.dof_points,cell_dofs=space.cell_dofs,boundary_dofs=space.boundary_dofs,
        axis_dofs=space.axis_dofs,axis_edges=case.mesh.axis_edges,
        boundary_local_vertices=case.mesh.boundary_local_vertices,
        boundary_components=case.mesh.boundary_components,boundary_segments=case.mesh.boundary_segments,
        surface_area_m2_by_segment=case.mesh.surface_area_m2_by_segment)


def axis_hphi_result(solution):
    case=solution.case
    return dict(format='superfish_ng_axis_hphi_result',schema_version=1,physics='axis_connected_axisymmetric_hphi_rf',
        case=case.to_dict(),coefficient_field='u_real_A_per_m2 = Hphi_real_A_per_m / r_m; finite axis limit retained',
        conventions=dict(coordinates='r,z in metres; one connected vacuum axis interval',
            volume_measure='2*pi*r dr dz; full 3D vacuum, excluding conductor holes',
            phasor='peak exp(+i omega t); field = real + i*quadrature',
            fields='Hphi=r*u; Er_quadrature=r*u_z/(omega*epsilon0); Ez_quadrature=-(2*u+r*u_r)/(omega*epsilon0)',
            normalization='total time-averaged energy in J; no per-length conversion',
            wall_loss='all PEC contour surfaces including holes with positive area; zero-area axis excluded; W',
            boundary_order='outer first, then holes in declared order; segments follow each contour without a repeated closing vertex',
            acceleration='only the explicitly declared vacuum axis interval; phase exp(+i*omega*(z-origin)/(beta*c))',
            r_over_q_accelerator='abs(Vacc)^2/(omega*U), ohm',
            r_over_q_circuit='abs(Vacc)^2/(2*omega*U), ohm',
            spectrum='lowest positive FEM frequencies in m=0 Hphi family; index is not a mode identity'),
        topology=dict(connected_vacuum=True,holes=len(case.mesh.holes_rz_m),boundary_components=1+len(case.mesh.holes_rz_m),
            axis_interval_m=list(case.mesh.axis_interval_m),euler_characteristic=case.mesh.euler_characteristic,
            area_m2=case.mesh.area_m2,volume_m3=case.mesh.volume_m3),
        excluded_nullspace=dict(dimension=0,reason='nonzero constant q=r*Hphi is not regular on the vacuum axis',
            scope='this regular Hphi space only; not all static Maxwell field families'),
        residuals=solution.residuals.tolist(),orthogonality_error=solution.orthogonality_error,
        matrix_quadrature=dict(rule='canonical polynomial Duffy-Gauss',order=4 if case.element_order==1 else 5,
            rf_triangle_order=5,rf_edge_gauss_points=5,interpretation='exact straight-element polynomial integration; not a discretization error bound'),
        modes=[axis_hphi_quantities(solution,i) for i in range(case.modes)])


def save_axis_hphi_run(case,solution,directory):
    if (not isinstance(case,AxisHphiCase) or not isinstance(solution,AxisHphiSolution)
        or solution.case.to_dict() != case.to_dict()):
        raise ValueError('axis Hphi case and solution disagree')
    case = AxisHphiCase.from_dict(case.to_dict())
    space,k,m = axis_hphi_matrices(case)
    expected = _mesh_arrays(case,space); actual = _mesh_arrays(solution.case,solution.space)
    if any(not np.array_equal(value,actual[name]) for name,value in expected.items()):
        raise ValueError('Hphi solution mesh/boundary components differ from the declared geometry')
    verified = restore_axis_hphi(case,space,k,m,solution.coefficients,solution.frequencies_hz)
    result = axis_hphi_result(verified); directory = Path(directory); directory.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='.axis-hphi-staging-',dir=directory) as temporary:
        stage = Path(temporary); _json(stage/'case.json',case.to_dict()); _json(stage/'results.json',result)
        np.savez_compressed(stage/'mesh.npz',**expected)
        np.savez_compressed(stage/'fields.npz',coefficients=verified.coefficients,frequencies_hz=verified.frequencies_hz)
        _json(stage/'manifest.json',dict(format='superfish_ng_axis_hphi_manifest',schema_version=1,
            files={name:hashlib.sha256((stage/name).read_bytes()).hexdigest() for name in sorted(FILES)}))
        for name in sorted(FILES): os.link(stage/name,directory/name)
        os.link(stage/'manifest.json',directory/'manifest.json')
    return result


def read_axis_hphi_run(directory):
    directory = Path(directory); raw = _snapshot(directory)
    manifest = parse_json(raw['manifest.json'].decode('utf-8'))
    names=['format','schema_version','files']; keys(manifest,names,names,'axis Hphi manifest')
    if (manifest['format'] != 'superfish_ng_axis_hphi_manifest' or type(manifest['schema_version']) is not int
        or manifest['schema_version'] != 1): raise ValueError('unsupported axis Hphi manifest format')
    if manifest['files'] != {name:hashlib.sha256(raw[name]).hexdigest() for name in sorted(FILES)}:
        raise ValueError('axis Hphi native content hash mismatch')
    case = AxisHphiCase.from_dict(parse_json(raw['case.json'].decode('utf-8')))
    space,k,m = axis_hphi_matrices(case); expected = _mesh_arrays(case,space); actual = _arrays(raw['mesh.npz'])
    if (actual.keys() != expected.keys()
        or any(actual[name].dtype.kind != value.dtype.kind or not np.array_equal(actual[name],value) for name,value in expected.items())):
        raise ValueError('saved axis Hphi, topology or boundary membership disagrees with declared geometry')
    fields = _arrays(raw['fields.npz'])
    if fields.keys() != {'coefficients','frequencies_hz'}: raise ValueError('unexpected axis Hphi field arrays')
    solution = restore_axis_hphi(case,space,k,m,fields['coefficients'],fields['frequencies_hz'])
    if parse_json(raw['results.json'].decode('utf-8')) != axis_hphi_result(solution):
        raise ValueError('axis Hphi saved RF, topology, axis or conventions disagree with FEM replay')
    if _snapshot(directory) != raw: raise ValueError('axis Hphi native changed during verification')
    return solution


def export_axis_hphi_probe(run,out,points_rz_m,mode=1):
    integer(mode,'mode',1); run,out = Path(run),Path(out)
    if out.resolve().is_relative_to(run.resolve()): raise ValueError('axis Hphi probe output must be outside native directory')
    raw = _snapshot(run); solution = read_axis_hphi_run(run); fields = solution.fields_at(points_rz_m,mode-1)
    for axis in ('r','phi','z'):
        for phase in ('real','quadrature'): fields[f'B{axis}_{phase}_T'] = MU0*fields[f'H{axis}_{phase}_A_per_m']
    result = dict(format='superfish_ng_axis_hphi_probe',schema_version=1,mode=mode,
        points_rz_m=np.asarray(points_rz_m,dtype=float).tolist(),fields={k:v.tolist() for k,v in fields.items()},
        conventions=axis_hphi_result(solution)['conventions'],native_sha256={name:hashlib.sha256(data).hexdigest() for name,data in raw.items()})
    if _snapshot(run) != raw: raise ValueError('axis Hphi native changed while preparing probe')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.axis-hphi-probe-',dir=out.parent) as temporary:
        stage = Path(temporary)/'probe.json'; _json(stage,result); os.link(stage,out)
    return result
