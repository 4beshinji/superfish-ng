# SPDX-License-Identifier: Apache-2.0
"""Dedicated positive-radius mesh native files with full topology/FEM/RF replay."""
import hashlib
import os
from pathlib import Path
import tempfile
import numpy as np
from .config import integer, keys
from .constants import MU0
from .project import parse_json
from .coaxial_saved import FILES, _json, _arrays, _mesh_arrays as _space_arrays, _snapshot as _file_snapshot
from .hphi_mesh import HphiMeshCase, HphiMeshSolution, hphi_mesh_matrices, restore_hphi_mesh, hphi_mesh_quantities


def _snapshot(directory):
    try: return _file_snapshot(directory)
    except ValueError as exc: raise ValueError(str(exc).replace('coaxial','Hphi mesh')) from exc


def _mesh_arrays(case,space):
    return dict(**_space_arrays(space),boundary_components=case.mesh.boundary_components,
                boundary_segments=case.mesh.boundary_segments,surface_area_m2_by_segment=case.mesh.surface_area_m2_by_segment)


def hphi_mesh_result(solution):
    case = solution.case
    return dict(format='superfish_ng_hphi_mesh_result',schema_version=1,physics='positive_radius_axisymmetric_hphi_rf',
        case=case.to_dict(),coefficient_field='q_real_A = r_m * Hphi_real_A_per_m',
        conventions=dict(coordinates='r,z in metres; all vacuum strictly outside r=0',
            volume_measure='2*pi*r dr dz; full 3D vacuum, excluding conductor holes',
            phasor='peak exp(+i omega t); field = real + i*quadrature',
            normalization='total time-averaged energy in J; no per-length conversion',
            wall_loss='all PEC contour surfaces, including holes, added with positive area; W',
            boundary_order='outer first, then holes in declared order; segments follow each contour without a repeated closing vertex',
            spectrum='lowest positive FEM frequencies in m=0 Hphi family; index is not a mode identity'),
        topology=dict(connected_vacuum=True,holes=len(case.mesh.holes_rz_m),boundary_components=1+len(case.mesh.holes_rz_m),
                      euler_characteristic=case.mesh.euler_characteristic,area_m2=case.mesh.area_m2,volume_m3=case.mesh.volume_m3),
        excluded_nullspace=dict(dimension=1,coefficient='constant q',field='static Hphi proportional to 1/r',
            scope='one connected positive-radius Hphi space; not all static Maxwell field families'),
        residuals=solution.residuals.tolist(),orthogonality_error=solution.orthogonality_error,
        nullspace_overlap=solution.nullspace_overlap,matrix_quadrature=solution.quadrature_diagnostic,
        modes=[hphi_mesh_quantities(solution,i) for i in range(case.modes)])


def save_hphi_mesh_run(case,solution,directory):
    if (not isinstance(case,HphiMeshCase) or not isinstance(solution,HphiMeshSolution)
        or solution.case.to_dict() != case.to_dict()):
        raise ValueError('Hphi mesh case and solution disagree')
    case = HphiMeshCase.from_dict(case.to_dict())
    space,k,m,diagnostic = hphi_mesh_matrices(case)
    expected = _mesh_arrays(case,space); actual = _mesh_arrays(solution.case,solution.space)
    if any(not np.array_equal(value,actual[name]) for name,value in expected.items()):
        raise ValueError('Hphi solution mesh/boundary components differ from the declared geometry')
    verified = restore_hphi_mesh(case,space,k,m,diagnostic,solution.coefficients,solution.frequencies_hz)
    result = hphi_mesh_result(verified); directory = Path(directory); directory.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='.hphi-mesh-staging-',dir=directory) as temporary:
        stage = Path(temporary); _json(stage/'case.json',case.to_dict()); _json(stage/'results.json',result)
        np.savez_compressed(stage/'mesh.npz',**expected)
        np.savez_compressed(stage/'fields.npz',coefficients=verified.coefficients,frequencies_hz=verified.frequencies_hz)
        _json(stage/'manifest.json',dict(format='superfish_ng_hphi_mesh_manifest',schema_version=1,
            files={name:hashlib.sha256((stage/name).read_bytes()).hexdigest() for name in sorted(FILES)}))
        for name in sorted(FILES): os.link(stage/name,directory/name)
        os.link(stage/'manifest.json',directory/'manifest.json')
    return result


def read_hphi_mesh_run(directory):
    directory = Path(directory); raw = _snapshot(directory)
    manifest = parse_json(raw['manifest.json'].decode('utf-8'))
    names=['format','schema_version','files']; keys(manifest,names,names,'Hphi mesh manifest')
    if (manifest['format'] != 'superfish_ng_hphi_mesh_manifest' or type(manifest['schema_version']) is not int
        or manifest['schema_version'] != 1): raise ValueError('unsupported Hphi mesh manifest format')
    if manifest['files'] != {name:hashlib.sha256(raw[name]).hexdigest() for name in sorted(FILES)}:
        raise ValueError('Hphi mesh native content hash mismatch')
    case = HphiMeshCase.from_dict(parse_json(raw['case.json'].decode('utf-8')))
    space,k,m,diagnostic = hphi_mesh_matrices(case); expected = _mesh_arrays(case,space); actual = _arrays(raw['mesh.npz'])
    if (actual.keys() != expected.keys()
        or any(actual[name].dtype.kind != value.dtype.kind or not np.array_equal(actual[name],value) for name,value in expected.items())):
        raise ValueError('saved Hphi mesh, topology or boundary membership disagrees with declared geometry')
    fields = _arrays(raw['fields.npz'])
    if fields.keys() != {'coefficients','frequencies_hz'}: raise ValueError('unexpected Hphi mesh field arrays')
    solution = restore_hphi_mesh(case,space,k,m,diagnostic,fields['coefficients'],fields['frequencies_hz'])
    if parse_json(raw['results.json'].decode('utf-8')) != hphi_mesh_result(solution):
        raise ValueError('Hphi mesh saved RF, topology, nullspace or conventions disagree with FEM replay')
    if _snapshot(directory) != raw: raise ValueError('Hphi mesh native changed during verification')
    return solution


def export_hphi_mesh_probe(run,out,points_rz_m,mode=1):
    integer(mode,'mode',1); run,out = Path(run),Path(out)
    if out.resolve().is_relative_to(run.resolve()): raise ValueError('Hphi mesh probe output must be outside native directory')
    raw = _snapshot(run); solution = read_hphi_mesh_run(run); fields = solution.fields_at(points_rz_m,mode-1)
    for axis in ('r','phi','z'):
        for phase in ('real','quadrature'): fields[f'B{axis}_{phase}_T'] = MU0*fields[f'H{axis}_{phase}_A_per_m']
    result = dict(format='superfish_ng_hphi_mesh_probe',schema_version=1,mode=mode,
        points_rz_m=np.asarray(points_rz_m,dtype=float).tolist(),fields={k:v.tolist() for k,v in fields.items()},
        conventions=hphi_mesh_result(solution)['conventions'],native_sha256={name:hashlib.sha256(data).hexdigest() for name,data in raw.items()})
    if _snapshot(run) != raw: raise ValueError('Hphi mesh native changed while preparing probe')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.hphi-mesh-probe-',dir=out.parent) as temporary:
        stage = Path(temporary)/'probe.json'; _json(stage,result); os.link(stage,out)
    return result
