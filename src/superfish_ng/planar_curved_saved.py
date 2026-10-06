# SPDX-License-Identifier: Apache-2.0
"""Version 3 native replay of the original curved Cartesian FEM solution.

The completion manifest binds five regular files. Hashes detect accidental
damage; actual geometry, lowest-positive-band and RF replay detect rehashed
changes. No field normalization or coefficient conversion occurs on replay.
"""
import hashlib
import os
from pathlib import Path
import tempfile
import numpy as np
from .config import keys
from .project import parse_json
from .planar_curved import PlanarCurvedCase
from .planar_curved_solver import (PlanarCurvedSolution,
    restore_planar_curved_solution, planar_curved_quantities)
from .planar_saved import FILES, _json, _snapshot, _arrays


def _mesh_arrays(space):
    return {name: getattr(space, name) for name in (
        'points_xy_m', 'cell_nodes', 'boundary_nodes', 'boundary_cells',
        'boundary_local_edges', 'free_dofs')}


def _same_array(first, second):
    return (first.dtype == second.dtype and first.shape == second.shape
            and first.tobytes() == second.tobytes())


def _check_field_arrays(fields):
    if fields.keys() != {'coefficients', 'frequencies_hz'}:
        raise ValueError('unexpected curved planar field arrays')
    if any(value.dtype != np.dtype(float) for value in fields.values()):
        raise ValueError('curved planar fields require original float64 arrays without conversion')


def planar_curved_result(solution):
    """Full per-length RF quantities and conventions from the actual map."""
    if not isinstance(solution, PlanarCurvedSolution):
        raise ValueError('curved planar result requires a PlanarCurvedSolution')
    return dict(format='superfish_ng_planar_result', schema_version=3,
        physics='cartesian_cutoff_rf', case=solution.case.to_dict(),
        conventions=dict(coordinates='x,y in metres; uniform longitudinal z; beta_z=0',
            volume_measure='dx dy; per unit z length',
            phasor='peak exp(+i omega t); real and +i quadrature fields explicitly named',
            normalization='total time-averaged energy in J/m',
            wall_loss='PEC side walls only, W/m; no finite-length end plates',
            spectrum='lowest positive FEM cutoff frequencies; TE constant nullspace excluded; index is not a mode label'),
        coefficient_field='Ez_real_V_per_m' if solution.case.polarization == 'tm' else 'Hz_real_A_per_m',
        residuals=solution.residuals.tolist(), orthogonality_error=solution.orthogonality_error,
        modes=[planar_curved_quantities(solution, i) for i in range(solution.case.modes)])


def save_planar_curved_run(case, solution, directory):
    """Verify before creating a new output; publish the manifest last."""
    if (not isinstance(case, PlanarCurvedCase) or not isinstance(solution, PlanarCurvedSolution)
            or solution.case != case):
        raise ValueError('curved planar case and solution disagree')
    fields = dict(coefficients=solution.coefficients, frequencies_hz=solution.frequencies_hz)
    _check_field_arrays(fields)
    verified = restore_planar_curved_solution(case, **fields, verify_spectrum=True)
    if any(not _same_array(value, getattr(solution.space, name))
           for name, value in _mesh_arrays(verified.space).items()):
        raise ValueError('curved planar solution mesh differs from its declared quadratic geometry')
    if any(not _same_array(value, getattr(verified, name)) for name, value in fields.items()):
        raise ValueError('curved planar replay changed the original field arrays')
    result = planar_curved_result(verified)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='.planar-curved-staging-', dir=directory) as temporary:
        stage = Path(temporary)
        _json(stage/'case.json', case.to_dict())
        _json(stage/'results.json', result)
        np.savez_compressed(stage/'mesh.npz', **_mesh_arrays(verified.space))
        np.savez_compressed(stage/'fields.npz', **fields)
        manifest = dict(format='superfish_ng_planar_manifest', schema_version=3,
            files={name: hashlib.sha256((stage/name).read_bytes()).hexdigest() for name in sorted(FILES)})
        _json(stage/'manifest.json', manifest)
        for name in sorted(FILES):
            os.replace(stage/name, directory/name)
        os.replace(stage/'manifest.json', directory/'manifest.json')
    return result


def read_planar_curved_run(directory):
    """Reassemble K/M/free, verify all requested modes and reproduce all RF."""
    directory = Path(directory)
    if directory.is_symlink():
        raise ValueError('curved planar native directory must not be a symbolic link')
    raw = _snapshot(directory)
    manifest = parse_json(raw['manifest.json'].decode('utf-8'))
    names = ['format', 'schema_version', 'files']
    keys(manifest, names, names, 'curved planar manifest')
    if (manifest['format'] != 'superfish_ng_planar_manifest'
            or type(manifest['schema_version']) is not int or manifest['schema_version'] != 3):
        raise ValueError('expected curved planar manifest schema_version 3')
    if manifest['files'] != {name: hashlib.sha256(raw[name]).hexdigest() for name in sorted(FILES)}:
        raise ValueError('curved planar native content hash mismatch')
    case = PlanarCurvedCase.from_dict(parse_json(raw['case.json'].decode('utf-8')))
    fields = _arrays(raw['fields.npz'])
    _check_field_arrays(fields)
    solution = restore_planar_curved_solution(case, **fields, verify_spectrum=True)
    mesh = _arrays(raw['mesh.npz'])
    expected = _mesh_arrays(solution.space)
    if mesh.keys() != expected.keys() or any(not _same_array(mesh[name], value) for name, value in expected.items()):
        raise ValueError('saved curved planar mesh does not match declared quadratic geometry and FEM space')
    if any(not _same_array(value, getattr(solution, name)) for name, value in fields.items()):
        raise ValueError('curved planar replay changed the original field arrays')
    result = parse_json(raw['results.json'].decode('utf-8'))
    if result != planar_curved_result(solution):
        raise ValueError('curved planar saved RF quantities, units, case or numerical metadata disagree with FEM replay')
    if directory.is_symlink() or _snapshot(directory) != raw:
        raise ValueError('curved planar native files changed during verification')
    return solution
