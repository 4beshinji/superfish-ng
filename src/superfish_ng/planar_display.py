# SPDX-License-Identifier: Apache-2.0
"""Cartesian display samples and SI probes evaluated in the original FEM cells."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import numpy as np
from .constants import MU0
from .planar import PlanarFieldSampler
from .planar_saved import read_planar_run, planar_result
from .planar_jobs import _native_hashes


def display_planar_fields(solution, mode=0):
    """Return xy display triangles and exact fields at their centres.

    P2 cells split four ways. Parent indices and barycentric coordinates
    preserve the one-sided FEM derivative without point-location ambiguity.
    Display samples do not estimate RF integrals or continuous field peaks.
    """
    space = solution.space
    reference = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1],
                          [.5, .5, 0], [0, .5, .5], [.5, 0, .5]])
    split = (np.array([[0, 1, 2]]) if solution.case.element_order == 1 else
             np.array([[0, 3, 5], [3, 1, 4], [5, 4, 2], [3, 4, 5]]))
    cells = np.repeat(np.arange(len(space.triangles)), len(split))
    barycentric = np.tile(reference[split].mean(axis=1), (len(space.triangles), 1))
    fields = solution.fields_in_cells(cells, barycentric, mode)
    for axis in 'xyz':
        for phase in ('real', 'quadrature'):
            fields[f'B{axis}_{phase}_T'] = MU0 * fields[f'H{axis}_{phase}_A_per_m']
    return dict(points_xy_m=space.dof_points_xy_m,
                triangles=space.cell_dofs[:, split].reshape(-1, 3),
                parent_cells=cells, barycentric=barycentric, fields=fields)


def verified_planar_view(run, mode):
    """Bind a one-based view to all five unchanged, fully replayed native files."""
    run = Path(run)
    before = _native_hashes(run)
    solution = read_planar_run(run)
    if type(mode) is not int or not 1 <= mode <= solution.case.modes:
        raise ValueError('mode must be a valid one-based mode number')
    if before != _native_hashes(run):
        raise ValueError('planar native changed while preparing the view')
    result = planar_result(solution)
    metadata = dict(format='superfish_ng_planar_view', schema_version=1,
                    native_sha256=before, mode=mode,
                    case=solution.case.to_dict(), conventions=result['conventions'],
                    quantities=result['modes'][mode-1],
                    numerical_validation='not_checked')
    return solution, metadata


def publish_planar_view(run, out, data, metadata):
    """Publish data last and preserve existing outputs and source native bytes."""
    run, out = Path(run), Path(out)
    sidecar = out.with_suffix(out.suffix + '.json')
    if out.resolve().is_relative_to(run.resolve()):
        raise ValueError('planar view output must be outside the native directory')
    if out.exists() or out.is_symlink() or sidecar.exists() or sidecar.is_symlink():
        raise ValueError('planar view output or metadata already exists')
    if metadata['native_sha256'] != _native_hashes(run):
        raise ValueError('planar native changed before view publication')
    metadata = {**metadata, 'data_sha256': hashlib.sha256(data).hexdigest()}
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.planar-view-', dir=out.parent) as temp:
        stage = Path(temp)
        (stage/'data').write_bytes(data)
        (stage/'metadata').write_text(json.dumps(metadata, indent=2, allow_nan=False)+'\n', encoding='utf-8')
        os.link(stage/'metadata', sidecar)
        try:
            os.link(stage/'data', out)
        except Exception:
            sidecar.unlink()
            raise
    if metadata['native_sha256'] != _native_hashes(run):
        raise ValueError('planar native changed during view publication')
    return metadata


def export_planar_probe(run, out, points_xy_m, mode=1):
    """Export all real/quadrature E/H components in SI, retaining CSV columns."""
    solution, metadata = verified_planar_view(run, mode)
    fields = PlanarFieldSampler(solution).evaluate(points_xy_m, mode-1)
    points = np.asarray(points_xy_m, dtype=float)
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(['x_m', 'y_m', *fields])
    writer.writerows([*point, *(fields[key][i] for key in fields)] for i, point in enumerate(points))
    metadata.update(view='xy_probe', points_xy_m=points.tolist(),
                    magnetic_flux_density='B = mu0 H; same phase; SI tesla',
                    mu0_h_per_m=MU0)
    return publish_planar_view(run, out, stream.getvalue().encode('utf-8'), metadata)
