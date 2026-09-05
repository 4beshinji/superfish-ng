# SPDX-License-Identifier: Apache-2.0
"""Optional scientific plots from saved runs; no second field solver."""
import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.tri import Triangulation
from .constants import MU0
from .rf import cell_fields
from .sampling import FieldSampler, radial_extent


def plot_mode(run, out, mode=1, probe_z_m=None, show_mesh=False):
    run, out = Path(run), Path(out)
    if out.exists():
        raise ValueError(f'output already exists: {out}')
    results = json.loads((run/'results.json').read_text())
    if isinstance(mode, bool) or not isinstance(mode, int) or not 1 <= mode <= len(results['modes']):
        raise ValueError('mode must be a valid one-based mode number')
    q = results['modes'][mode-1]
    with np.load(run/'fields.npz', allow_pickle=False) as data:
        p, t, u = data['points_rz_m'], data['triangles'], data['u_a_per_m2']
        edges, freqs = data['boundary_edges'], data['frequencies_hz']
    zmin, zmax = p[:, 1].min(), p[:, 1].max()
    probe_z = zmin+(zmax-zmin)/4 if probe_z_m is None else float(probe_z_m)
    if not np.isfinite(probe_z) or not zmin <= probe_z <= zmax:
        raise ValueError('probe z must lie within the cavity in metres')
    sampler = FieldSampler(p, t, u, freqs)
    radial_points = np.column_stack((np.linspace(0, radial_extent(p, edges, probe_z), 401), np.full(401, probe_z)))
    radial = sampler.evaluate(radial_points, mode-1)
    axis = np.loadtxt(run/f'axis_{mode:03d}.csv', delimiter=',', skiprows=1)
    solution = SimpleNamespace(mesh=SimpleNamespace(points=p, triangles=t), u=u, frequencies_hz=freqs)
    er, ez, _ = cell_fields(solution, mode-1)
    mesh = Triangulation(p[:, 1]*1000, p[:, 0]*1000, t)
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), layout='constrained')
    electric = axes[0, 0].tripcolor(mesh, facecolors=np.hypot(er, ez)/1e6, shading='flat', cmap='magma', rasterized=True)
    # Electric field lines are contours of r*Hphi (poloidal flux function).
    flux = p[:, 0]**2*u[:, mode-1]
    if np.ptp(flux) > 0:
        axes[0, 0].tricontour(mesh, flux, levels=18, colors='white', linewidths=.4, alpha=.5)
    rr, zz = np.meshgrid(np.linspace(0, p[:, 0].max(), 15), np.linspace(zmin, zmax, 25))
    samples = sampler.evaluate(np.column_stack((rr.ravel(), zz.ravel())), mode-1, outside='nan')
    erq, ezq = samples['Er_quadrature_V_per_m'], samples['Ez_quadrature_V_per_m']
    magnitude = np.hypot(erq, ezq)
    nonzero = samples['inside'] & (magnitude > np.nanmax(magnitude)*1e-8)
    axes[0, 0].quiver(zz.ravel()[nonzero]*1000, rr.ravel()[nonzero]*1000,
                      ezq[nonzero]/magnitude[nonzero], erq[nonzero]/magnitude[nonzero], color='#69d7ff', scale=35, width=.003)
    axes[0, 0].set_title(f'Mode {mode}: |E|, field lines and direction')
    fig.colorbar(electric, ax=axes[0, 0], label='Peak |E| [MV/m]')
    magnetic = axes[0, 1].tripcolor(mesh, MU0*p[:, 0]*u[:, mode-1]*1000, shading='gouraud', cmap='coolwarm', rasterized=True)
    axes[0, 1].set_title('Signed azimuthal magnetic field')
    fig.colorbar(magnetic, ax=axes[0, 1], label='Bphi [mT]')
    for ax in axes[0]:
        if show_mesh:
            ax.triplot(mesh, color='gray', lw=.2, alpha=.35)
        # One polyline collection is substantially faster than per-edge artists.
        boundary = p[edges][:, :, [1, 0]]*1000
        from matplotlib.collections import LineCollection
        ax.add_collection(LineCollection(boundary, colors='#444444', linewidths=.65))
        ax.set(xlabel='z [mm]', ylabel='r [mm]', aspect='equal')
    axes[1, 0].plot(axis[:, 0]*1000, axis[:, 1]/1e6)
    axes[1, 0].axhline(0, color='gray', lw=.6)
    axes[1, 0].set(xlabel='z [mm]', ylabel='Ez quadrature [MV/m]', title='On-axis accelerating field')
    axes[1, 1].plot(radial_points[:, 0]*1000, radial['Ez_quadrature_V_per_m']/1e6, label='Ez [MV/m]')
    axes[1, 1].plot(radial_points[:, 0]*1000, radial['Er_quadrature_V_per_m']/1e6, label='Er [MV/m]')
    second = axes[1, 1].twinx()
    second.plot(radial_points[:, 0]*1000, MU0*radial['Hphi_A_per_m']*1000, '--', color='#bc5090', label='Bphi [mT]')
    second.set_ylabel('Bphi [mT]')
    axes[1, 1].set(xlabel='r [mm]', ylabel='E quadrature [MV/m]', title=f'Radial probe: z={probe_z*1000:.3f} mm')
    axes[1, 1].legend(loc='upper left', fontsize=8)
    second.legend(loc='upper right', fontsize=8)
    for ax in axes[1]:
        ax.grid(alpha=.25)
    fig.suptitle(f"{results['case']['name']} | mode {mode} | {q['frequency_hz']/1e6:.6f} MHz\n"
                 f"Q0={q['q0']:.2f} | R/Q(acc)={q['r_over_q_accelerator_ohm']:.4f} ohm | U={q['stored_energy_j']:.4g} J | peak phasors, closed PEC")
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=160)
    plt.close(fig)
    return {'probe_z_m': probe_z, 'radial_points_rz_m': radial_points, 'radial_fields': radial}
