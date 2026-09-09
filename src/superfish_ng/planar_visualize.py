# SPDX-License-Identifier: Apache-2.0
"""Signed Cartesian cutoff fields sampled from verified FEM coefficients."""
import io
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.tri import Triangulation
from matplotlib.collections import LineCollection
from .planar_display import display_planar_fields, verified_planar_view, publish_planar_view


def plot_planar_mode(run, out, mode=1, show_mesh=False, length_unit='mm', mode_label=None):
    if type(show_mesh) is not bool:
        raise ValueError('show_mesh must be boolean')
    if length_unit not in ('m', 'mm'):
        raise ValueError('display length unit must be m or mm')
    if mode_label is not None and not isinstance(mode_label, str):
        raise ValueError('mode label must be a string')
    if Path(out).suffix.lower() != '.png':
        raise ValueError('planar plot output must have a .png suffix')
    solution, metadata = verified_planar_view(run, mode)
    display = display_planar_fields(solution, mode-1)
    scale = 1000 if length_unit == 'mm' else 1
    points = display['points_xy_m'] * scale
    tri = Triangulation(points[:, 0], points[:, 1], display['triangles'])
    components = ([('Ez_real_V_per_m', 1e-6, 'Ez real [MV/m]'),
                   ('Bx_quadrature_T', 1000, 'Bx quadrature [mT]'),
                   ('By_quadrature_T', 1000, 'By quadrature [mT]')]
                  if solution.case.polarization == 'tm' else
                  [('Bz_real_T', 1000, 'Bz real [mT]'),
                   ('Ex_quadrature_V_per_m', 1e-6, 'Ex quadrature [MV/m]'),
                   ('Ey_quadrature_V_per_m', 1e-6, 'Ey quadrature [MV/m]')])
    fig, axes = plt.subplots(1, 3, figsize=(14, 5), layout='constrained')
    try:
        boundary = solution.space.points_xy_m[solution.space.boundary_edges] * scale
        for ax, (key, factor, label) in zip(axes, components):
            values = display['fields'][key] * factor
            limit = max(float(np.max(np.abs(values))), 1e-30)
            artist = ax.tripcolor(tri, facecolors=values, shading='flat',
                                  cmap='coolwarm', vmin=-limit, vmax=limit)
            fig.colorbar(artist, ax=ax, label=label)
            ax.add_collection(LineCollection(boundary, colors='#222222', linewidths=1.1, label='PEC'))
            if show_mesh:
                ax.triplot(tri, color='#555555', lw=.25, alpha=.5)
            ax.set(xlabel=f'x [{length_unit}]', ylabel=f'y [{length_unit}]', aspect='equal', title=label)
            ax.legend(loc='upper right', fontsize=7)
        from matplotlib.font_manager import fontManager, FontProperties
        available = {font.name for font in fontManager.ttflist}
        families = [name for name in ('Noto Sans CJK JP', 'Noto Serif CJK JP', 'IPAexGothic') if name in available]
        label = f'{mode_label} (mode {mode})' if mode_label else f'Mode {mode}'
        q = metadata['quantities']
        fig.suptitle(f'{solution.case.name} | {solution.case.polarization.upper()} {label} | {q["frequency_hz"]/1e6:.6f} MHz\n'
                     f'U\N{PRIME}={q["stored_energy_j_per_m"]:.6g} J/m; P\N{PRIME}={q["wall_loss_w_per_m"]:.6g} W/m; Q0={q["q0"]:.6g}; G={q["geometry_factor_ohm"]:.6g} ohm\n'
                     'Peak exp(+i omega t); quadrature is +i component; R/Q: N/A (cutoff cross-section)\n'
                     'Flat centre samples in original cells; display subdivisions are not an accuracy certificate',
                     fontproperties=FontProperties(family=families+['DejaVu Sans']), fontsize=10)
        stream = io.BytesIO()
        fig.savefig(stream, format='png', dpi=160)
    finally:
        plt.close(fig)
    metadata.update(view='signed_cartesian_fields', length_unit=length_unit,
                    show_mesh=show_mesh, mode_label=mode_label,
                    components=[key for key, _, _ in components],
                    sampling='flat display-cell centres evaluated in original FEM parent cells')
    return publish_planar_view(run, out, stream.getvalue(), metadata)
