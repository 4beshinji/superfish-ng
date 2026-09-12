# SPDX-License-Identifier: Apache-2.0
"""Positive-radius Hphi display samples and SI probes evaluated in the original FEM cells."""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import numpy as np
from .constants import MU0
from .hphi_native import read_hphi_run, hphi_result
from .hphi_jobs import _native_hashes


def display_hphi_fields(solution, mode=0):
    """Return r,z display triangles and exact fields at their centres.

    P2 cells split four ways. Parent indices and barycentric coordinates
    preserve the one-sided FEM derivative without point-location ambiguity.
    Display samples do not estimate RF integrals or continuous field peaks.
    """
    space = solution.space
    reference = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1],
                          [.5, .5, 0], [0, .5, .5], [.5, 0, .5]])
    split = (np.array([[0, 1, 2]]) if solution.case.element_order == 1 else
             np.array([[0, 3, 5], [3, 1, 4], [5, 4, 2], [3, 4, 5]]))
    cells = np.repeat(np.arange(len(space.mesh.triangles)), len(split))
    barycentric = np.tile(reference[split].mean(axis=1), (len(space.mesh.triangles), 1))
    fields = solution.fields_in_cells(cells, barycentric, mode)
    for axis in ('r','phi','z'):
        for phase in ('real', 'quadrature'):
            fields[f'B{axis}_{phase}_T'] = MU0 * fields[f'H{axis}_{phase}_A_per_m']
    return dict(points_rz_m=space.dof_points,
                triangles=space.cell_dofs[:, split].reshape(-1, 3),
                parent_cells=cells, barycentric=barycentric, fields=fields)


def verified_hphi_view(run, mode):
    """Bind a one-based view to all five unchanged, fully replayed native files."""
    run = Path(run)
    before = _native_hashes(run)
    solution = read_hphi_run(run)
    if type(mode) is not int or not 1 <= mode <= solution.case.modes:
        raise ValueError('mode must be a valid one-based mode number')
    if before != _native_hashes(run):
        raise ValueError('hphi native changed while preparing the view')
    result = hphi_result(solution)
    metadata = dict(format='superfish_ng_hphi_view', schema_version=1,
                    native_sha256=before, mode=mode,
                    case=solution.case.to_dict(), conventions=result['conventions'],
                    quantities=result['modes'][mode-1],
                    numerical_validation='not_checked')
    return solution, metadata


def publish_hphi_view(run, out, data, metadata):
    """Publish data last and preserve existing outputs and source native bytes."""
    run, out = Path(run), Path(out)
    sidecar = out.with_suffix(out.suffix + '.json')
    if out.resolve().is_relative_to(run.resolve()):
        raise ValueError('hphi view output must be outside the native directory')
    if out.exists() or out.is_symlink() or sidecar.exists() or sidecar.is_symlink():
        raise ValueError('hphi view output or metadata already exists')
    if metadata['native_sha256'] != _native_hashes(run):
        raise ValueError('hphi native changed before view publication')
    metadata = {**metadata, 'data_sha256': hashlib.sha256(data).hexdigest()}
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.hphi-view-', dir=out.parent) as temp:
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
        raise ValueError('hphi native changed during view publication')
    return metadata


def export_hphi_probe(run, out, points_rz_m, mode=1):
    """Export all real/quadrature E/H components in SI, retaining CSV columns."""
    solution, metadata = verified_hphi_view(run, mode)
    fields = solution.fields_at(points_rz_m, mode-1)
    for axis in ('r','phi','z'):
        for phase in ('real','quadrature'):
            fields[f'B{axis}_{phase}_T'] = MU0 * fields[f'H{axis}_{phase}_A_per_m']
    points = np.asarray(points_rz_m, dtype=float)
    stream = io.StringIO(newline='')
    writer = csv.writer(stream)
    writer.writerow(['r_m', 'z_m', *fields])
    writer.writerows([*point, *(fields[key][i] for key in fields)] for i, point in enumerate(points))
    metadata.update(view='rz_probe', points_rz_m=points.tolist(),
                    magnetic_flux_density='B = mu0 H; same phase; SI tesla',
                    mu0_h_per_m=MU0)
    return publish_hphi_view(run, out, stream.getvalue().encode('utf-8'), metadata)


def plot_hphi_mode(run, out, mode=1, *, mesh=False, length_unit='mm'):
    """Plot signed original-cell Hphi/Er/Ez samples without filling conductor holes."""
    if type(mesh) is not bool or length_unit not in ('m','mm'):
        raise ValueError('Hphi plot requires boolean mesh and length_unit m or mm')
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.tri import Triangulation
    solution,metadata = verified_hphi_view(run,mode)
    samples = display_hphi_fields(solution,mode-1)
    points = samples['points_rz_m'];scale = 1000 if length_unit=='mm' else 1
    # Swapping (r,z) to the plotted (z,r) reverses the triangle orientation.
    triangles = samples['triangles'][:,[0,2,1]]
    triangulation = Triangulation(points[:,1]*scale,points[:,0]*scale,triangles)
    fig = Figure(figsize=(13,4),layout='constrained');canvas=FigureCanvasAgg(fig)
    panels=[('Hphi_real_A_per_m','Hφ real [A/m]'),('Er_quadrature_V_per_m','Er quadrature [V/m]'),
            ('Ez_quadrature_V_per_m','Ez quadrature [V/m]')]
    for axis,(key,label) in zip(fig.subplots(1,3),panels):
        values=samples['fields'][key];maximum=float(np.max(abs(values)))
        if maximum==0:maximum=1.
        artist=axis.tripcolor(triangulation,values,shading='flat',cmap='RdBu_r',vmin=-maximum,vmax=maximum)
        if mesh:axis.triplot(triangulation,color='0.5',linewidth=.25)
        for edge in solution.space.mesh.boundary_edges:
            boundary=solution.space.mesh.points[edge]*scale
            axis.plot(boundary[:,1],boundary[:,0],color='black',linewidth=.7)
        axis.set(xlabel=f'z [{length_unit}]',ylabel=f'r [{length_unit}]',title=label,aspect='equal')
        fig.colorbar(artist,ax=axis,shrink=.8)
    quantities=metadata['quantities']
    fig.suptitle(f"Positive-radius Hφ | mode rank {mode} | {quantities['frequency_hz']/1e6:.6g} MHz | U={quantities['stored_energy_j']:.6g} J\n"
                 'peak exp(+iωt), real + i·quadrature; original FEM samples, not a surface-peak certificate',fontsize=10)
    stream=io.BytesIO();canvas.print_png(stream)
    metadata.update(view='rz_signed_fields',length_unit=length_unit,mesh=mesh,
                    display_samples=len(samples['triangles']),components=[key for key,_ in panels],
                    interpretation='one-sided original FEM samples; conductor interiors omitted; no physical peak convergence claim')
    return publish_hphi_view(run,out,stream.getvalue(),metadata)
