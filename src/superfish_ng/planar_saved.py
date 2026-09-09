# SPDX-License-Identifier: Apache-2.0
"""Dedicated Cartesian cutoff native format; never reinterpret J/m as J."""
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
from zipfile import BadZipFile
import numpy as np
from .config import keys
from .planar import PlanarCase, PlanarSolution, planar_matrices, _restore, planar_quantities
from .project import parse_json
from .planar_polygon import planar_case_from_dict

FILES={'case.json','mesh.npz','fields.npz','results.json'}


def _json(path,value):
    with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2,allow_nan=False)


def _mesh_arrays(space):
    return {name:getattr(space,name) for name in ('points_xy_m','triangles','dof_points_xy_m','cell_dofs','boundary_edges','boundary_cells','boundary_local_vertices','boundary_dofs')}


def planar_result(solution):
    return dict(format='superfish_ng_planar_result',schema_version=solution.case.to_dict()['schema_version'],physics='cartesian_cutoff_rf',case=solution.case.to_dict(),
        conventions=dict(coordinates='x,y in metres; uniform longitudinal z; beta_z=0',volume_measure='dx dy; per unit z length',
            phasor='peak exp(+i omega t); real and +i quadrature fields explicitly named',
            normalization='total time-averaged energy in J/m',wall_loss='PEC side walls only, W/m; no finite-length end plates',
            spectrum='lowest positive FEM cutoff frequencies; TE constant nullspace excluded; index is not a mode label'),
        coefficient_field='Ez_real_V_per_m' if solution.case.polarization=='tm' else 'Hz_real_A_per_m',
        residuals=solution.residuals.tolist(),orthogonality_error=solution.orthogonality_error,
        modes=[planar_quantities(solution,i) for i in range(solution.case.modes)])


def save_planar_run(case,solution,directory):
    if not isinstance(solution,PlanarSolution) or solution.case!=case:raise ValueError('planar case and solution disagree')
    space,k,m,free=planar_matrices(case)
    for name,array in _mesh_arrays(space).items():
        if not np.array_equal(array,getattr(solution.space,name)):raise ValueError('planar solution mesh differs from its declared geometry')
    verified=_restore(case,space,k,m,free,solution.coefficients,solution.frequencies_hz,verify_spectrum=True)
    result=planar_result(verified);directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='.planar-staging-',dir=directory) as temporary:
        stage=Path(temporary);_json(stage/'case.json',case.to_dict());_json(stage/'results.json',result)
        np.savez_compressed(stage/'mesh.npz',**_mesh_arrays(space))
        np.savez_compressed(stage/'fields.npz',coefficients=verified.coefficients,frequencies_hz=verified.frequencies_hz)
        manifest=dict(format='superfish_ng_planar_manifest',schema_version=case.to_dict()['schema_version'],
            files={name:hashlib.sha256((stage/name).read_bytes()).hexdigest() for name in sorted(FILES)})
        _json(stage/'manifest.json',manifest)
        for name in sorted(FILES):os.replace(stage/name,directory/name)
        os.replace(stage/'manifest.json',directory/'manifest.json')
    return result


def _snapshot(directory):
    if not directory.is_dir() or {p.name for p in directory.iterdir()}!=FILES|{'manifest.json'}:
        raise ValueError('planar native requires exactly case/mesh/fields/results and a completion manifest')
    if any((directory/name).is_symlink() or not (directory/name).is_file() for name in FILES|{'manifest.json'}):
        raise ValueError('planar native files must be regular files, not symbolic links')
    return {name:(directory/name).read_bytes() for name in FILES|{'manifest.json'}}


def _arrays(raw):
    try:
        with np.load(io.BytesIO(raw),allow_pickle=False) as archive:
            if len(archive.files)!=len(set(archive.files)):raise ValueError('duplicate planar array members')
            return {name:archive[name] for name in archive.files}
    except (ValueError,OSError,KeyError,TypeError,EOFError,BadZipFile) as exc:
        raise ValueError('invalid planar numeric archive') from exc


def read_planar_run(directory):
    directory=Path(directory);raw=_snapshot(directory)
    manifest=parse_json(raw['manifest.json'].decode('utf-8'))
    keys(manifest,['format','schema_version','files'],['format','schema_version','files'],'planar manifest')
    if manifest['format']!='superfish_ng_planar_manifest' or type(manifest['schema_version']) is not int or manifest['schema_version'] not in (1,2):
        raise ValueError('unsupported planar manifest format')
    if manifest['files']!={name:hashlib.sha256(raw[name]).hexdigest() for name in sorted(FILES)}:
        raise ValueError('planar native content hash mismatch')
    case=planar_case_from_dict(parse_json(raw['case.json'].decode('utf-8')))
    if manifest['schema_version']!=case.to_dict()['schema_version']:raise ValueError('planar manifest and case versions disagree')
    space,k,m,free=planar_matrices(case);mesh=_arrays(raw['mesh.npz']);expected=_mesh_arrays(space)
    if mesh.keys()!=expected.keys() or any(mesh[name].dtype.kind!=value.dtype.kind or not np.array_equal(mesh[name],value) for name,value in expected.items()):
        raise ValueError('saved planar mesh does not match declared Cartesian geometry and FEM space')
    fields=_arrays(raw['fields.npz'])
    if fields.keys()!={'coefficients','frequencies_hz'}:raise ValueError('unexpected planar field arrays')
    solution=_restore(case,space,k,m,free,fields['coefficients'],fields['frequencies_hz'],verify_spectrum=True)
    result=parse_json(raw['results.json'].decode('utf-8'));expected_result=planar_result(solution)
    if result!=expected_result:raise ValueError('planar saved RF quantities, units, case or numerical metadata disagree with FEM replay')
    if _snapshot(directory)!=raw:raise ValueError('planar native files changed during verification')
    return solution
