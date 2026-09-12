# SPDX-License-Identifier: Apache-2.0
"""Coaxial native coefficients, static-nullspace checks and full FEM/RF replay."""
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
from zipfile import BadZipFile
import numpy as np
from .config import keys, integer
from .constants import MU0
from .project import parse_json
from .coaxial import CoaxialCase, CoaxialSolution, coaxial_matrices, _restore_coaxial, coaxial_quantities

FILES={'case.json','mesh.npz','fields.npz','results.json'}


def _json(path,value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


def _mesh_arrays(space):
    return dict(points_rz_m=space.mesh.points,triangles=space.mesh.triangles,
        boundary_edges=space.mesh.boundary_edges,boundary_cells=space.mesh.boundary_cells,
        boundary_tags=space.mesh.boundary_tags,axis_nodes=space.mesh.axis_nodes,
        dof_points_rz_m=space.dof_points,cell_dofs=space.cell_dofs,boundary_dofs=space.boundary_dofs,
        boundary_local_vertices=space.boundary_local_vertices)


def coaxial_result(solution):
    return dict(format='superfish_ng_coaxial_result',schema_version=1,physics='axisymmetric_coaxial_hphi_rf',
        case=solution.case.to_dict(),coefficient_field='q_real_A = r_m * Hphi_real_A_per_m',
        conventions=dict(coordinates='r,z in metres; vacuum strictly outside r=0',
            volume_measure='2*pi*r dr dz; full 3D coaxial cavity',
            phasor='peak exp(+i omega t); field = real + i*quadrature',
            normalization='total time-averaged energy in J; no per-length conversion',
            wall_loss='both cylindrical conductors and both shorting end plates, W',
            spectrum='lowest positive FEM frequencies in the m=0 Hphi family; index is not a TEM/TM label'),
        excluded_nullspace=dict(dimension=1,coefficient='constant q',field='static Hphi proportional to 1/r',
            reason='zero-frequency circulating magnetic field has no time-harmonic RF energy balance'),
        residuals=solution.residuals.tolist(),orthogonality_error=solution.orthogonality_error,
        nullspace_overlap=solution.nullspace_overlap,matrix_quadrature=solution.quadrature_diagnostic,
        modes=[coaxial_quantities(solution,i) for i in range(solution.case.modes)])


def save_coaxial_run(case,solution,directory):
    if not isinstance(solution,CoaxialSolution) or solution.case!=case:
        raise ValueError('coaxial case and solution disagree')
    space,k,m,diagnostic=coaxial_matrices(case)
    actual=_mesh_arrays(solution.space)
    if any(not np.array_equal(array,actual[name]) for name,array in _mesh_arrays(space).items()):
        raise ValueError('coaxial solution mesh differs from its declared geometry')
    verified=_restore_coaxial(case,space,k,m,diagnostic,solution.coefficients,solution.frequencies_hz,verify_spectrum=True)
    result=coaxial_result(verified);directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='.coaxial-staging-',dir=directory) as temporary:
        stage=Path(temporary);_json(stage/'case.json',case.to_dict());_json(stage/'results.json',result)
        np.savez_compressed(stage/'mesh.npz',**_mesh_arrays(space))
        np.savez_compressed(stage/'fields.npz',coefficients=verified.coefficients,frequencies_hz=verified.frequencies_hz)
        manifest=dict(format='superfish_ng_coaxial_manifest',schema_version=1,
            files={name:hashlib.sha256((stage/name).read_bytes()).hexdigest() for name in sorted(FILES)})
        _json(stage/'manifest.json',manifest)
        for name in sorted(FILES):os.link(stage/name,directory/name)
        os.link(stage/'manifest.json',directory/'manifest.json')
    return result


def _snapshot(directory):
    if not directory.is_dir() or {p.name for p in directory.iterdir()}!=FILES|{'manifest.json'}:
        raise ValueError('coaxial native requires exactly case/mesh/fields/results and a completion manifest')
    if any((directory/name).is_symlink() or not (directory/name).is_file() for name in FILES|{'manifest.json'}):
        raise ValueError('coaxial native files must be regular files, not symbolic links')
    return {name:(directory/name).read_bytes() for name in FILES|{'manifest.json'}}


def _arrays(raw):
    try:
        with np.load(io.BytesIO(raw),allow_pickle=False) as archive:
            if len(archive.files)!=len(set(archive.files)):raise ValueError('duplicate coaxial array members')
            return {name:archive[name] for name in archive.files}
    except (ValueError,OSError,KeyError,TypeError,EOFError,BadZipFile) as exc:
        raise ValueError('invalid coaxial numeric archive') from exc


def read_coaxial_run(directory):
    directory=Path(directory);raw=_snapshot(directory)
    manifest=parse_json(raw['manifest.json'].decode('utf-8'))
    keys(manifest,['format','schema_version','files'],['format','schema_version','files'],'coaxial manifest')
    if manifest['format']!='superfish_ng_coaxial_manifest' or type(manifest['schema_version']) is not int or manifest['schema_version']!=1:
        raise ValueError('unsupported coaxial manifest format')
    if manifest['files']!={name:hashlib.sha256(raw[name]).hexdigest() for name in sorted(FILES)}:
        raise ValueError('coaxial native content hash mismatch')
    case=CoaxialCase.from_dict(parse_json(raw['case.json'].decode('utf-8')))
    space,k,m,diagnostic=coaxial_matrices(case);mesh=_arrays(raw['mesh.npz']);expected=_mesh_arrays(space)
    if mesh.keys()!=expected.keys() or any(mesh[name].dtype.kind!=value.dtype.kind or not np.array_equal(mesh[name],value) for name,value in expected.items()):
        raise ValueError('saved coaxial mesh does not match declared geometry and FEM space')
    fields=_arrays(raw['fields.npz'])
    if fields.keys()!={'coefficients','frequencies_hz'}:raise ValueError('unexpected coaxial field arrays')
    solution=_restore_coaxial(case,space,k,m,diagnostic,fields['coefficients'],fields['frequencies_hz'],verify_spectrum=True)
    result=parse_json(raw['results.json'].decode('utf-8'))
    if result!=coaxial_result(solution):raise ValueError('coaxial saved RF, units, nullspace or metadata disagree with FEM replay')
    if _snapshot(directory)!=raw:raise ValueError('coaxial native files changed during verification')
    return solution


def export_coaxial_probe(run,out,points_rz_m,mode=1):
    integer(mode,'mode',1);run,out=Path(run),Path(out)
    if out.resolve().is_relative_to(run.resolve()):raise ValueError('coaxial probe output must be outside the native directory')
    raw=_snapshot(run);solution=read_coaxial_run(run)
    fields=solution.fields_at(points_rz_m,mode-1)
    for axis in ('r','phi','z'):
        for phase in ('real','quadrature'):
            fields[f'B{axis}_{phase}_T']=MU0*fields[f'H{axis}_{phase}_A_per_m']
    result=dict(format='superfish_ng_coaxial_probe',schema_version=1,mode=mode,
        points_rz_m=np.asarray(points_rz_m,dtype=float).tolist(),fields={k:v.tolist() for k,v in fields.items()},
        conventions=coaxial_result(solution)['conventions'],
        native_sha256={name:hashlib.sha256(data).hexdigest() for name,data in raw.items()})
    if _snapshot(run)!=raw:raise ValueError('coaxial native changed while preparing probe')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.coaxial-probe-',dir=out.parent) as temporary:
        stage=Path(temporary)/'probe.json';_json(stage,result);os.link(stage,out)
    return result
