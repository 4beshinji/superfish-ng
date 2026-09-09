# SPDX-License-Identifier: Apache-2.0
"""Scientific TE plots from verified native fields; no additional eigensolve."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.tri import Triangulation
from .constants import MU0
from .te_saved import read_te_run
from .te import TEFieldSampler, te_quantities
from .sampling import solution_radial_extent
from .te_display import display_te_fields


def plot_te_mode(run, out, mode=1, probe_z_m=None, show_mesh=False, mode_label=None):
    out = Path(out)
    if out.exists(): raise ValueError(f'output already exists: {out}')
    solution = read_te_run(run)
    if type(mode) is not int or not 1 <= mode <= solution.case.modes:
        raise ValueError('mode must be a valid one-based mode number')
    if mode_label is not None and not isinstance(mode_label, str):
        raise ValueError('mode label must be a string')
    label = f'{mode_label} (mode {mode})' if mode_label else f'Mode {mode}'
    mode -= 1
    p, triangles, ephi, fields = display_te_fields(solution, mode)
    tri = Triangulation(p[:,1]*1000, p[:,0]*1000, triangles)
    hr, hz = fields['Hr_quadrature_A_per_m'], fields['Hz_quadrature_A_per_m']
    sampler=TEFieldSampler(solution);z0,z1=p[:,1].min(),p[:,1].max();probe=float((z0+z1)/2) if probe_z_m is None else probe_z_m
    if type(probe) not in (int,float) or not np.isfinite(probe) or not z0 <= probe <= z1:
        raise ValueError("probe z must lie within the cavity in metres")
    radial_points=np.column_stack((np.linspace(0,solution_radial_extent(solution,probe),201),np.full(201,probe)))
    radial=sampler.evaluate(radial_points,mode,outside='nan')
    z=np.linspace(z0,z1,201);axis=sampler.evaluate(np.column_stack((np.zeros_like(z),z)),mode)
    fig,axes=plt.subplots(2,2,figsize=(13,8),layout='constrained')
    plot=axes[0,0].tripcolor(tri,ephi/1e6,shading='gouraud',cmap='coolwarm',vmin=-max(float(np.max(abs(ephi/1e6))),1e-30),vmax=max(float(np.max(abs(ephi/1e6))),1e-30));fig.colorbar(plot,ax=axes[0,0],label='Signed Ephi [MV/m]')
    axes[0,0].set_title('Azimuthal electric field: real peak phasor')
    plot=axes[0,1].tripcolor(tri,facecolors=MU0*np.hypot(hr,hz)*1000,shading='flat',cmap='magma');fig.colorbar(plot,ax=axes[0,1],label='Peak |B(r,z)| [mT]')
    axes[0,1].tricontour(tri,p[:,0]*ephi,levels=18,colors='white',linewidths=.5)
    axes[0,1].set_title('Poloidal magnetic field magnitude and field lines')
    from matplotlib.collections import LineCollection
    if solution.case.geometry_order == 2:
        from .curved_queries import boundary_polylines
        boundary = boundary_polylines(solution.space)[:, :, [1, 0]]*1000
        tags = solution.space.boundary_tags
    else:
        boundary = solution.mesh.points[solution.mesh.boundary_edges][:, :, [1, 0]]*1000
        tags = solution.mesh.boundary_tags
    for ax in axes[0]:
        if show_mesh: ax.triplot(tri,color='gray',lw=.2,alpha=.35)
        for tag,color,style in [('pec','#444444','-'),('axis','#777777',':'),
                                ('electric_symmetry','#00a66c','--'),('magnetic_symmetry','#d68a00','--')]:
            if np.any(tags == tag):
                ax.add_collection(LineCollection(boundary[tags == tag],colors=color,linestyles=style,
                                                 linewidths=1.2,label=tag.replace('_',' ')))
        if np.any(np.isin(tags,['electric_symmetry','magnetic_symmetry'])):
            ax.legend(fontsize=7,loc='upper right')
        ax.set(xlabel='z [mm]',ylabel='r [mm]',aspect='equal')
    axes[1,0].plot(z*1000,MU0*axis['Hz_quadrature_A_per_m']*1000,label='Bz quadrature')
    axes[1,0].plot(z*1000,MU0*axis['Hr_quadrature_A_per_m']*1000,'--',label='Br quadrature')
    axes[1,0].set(xlabel='z [mm]',ylabel='B quadrature [mT]',title='Axis: Ephi = Br = 0; Ez identically zero')
    axes[1,0].legend()
    axes[1,1].plot(radial_points[:,0]*1000,radial['Ephi_V_per_m']/1e6,label='Ephi [MV/m]')
    right=axes[1,1].twinx()
    for key,component_label in [('Hr_quadrature_A_per_m','Br'),('Hz_quadrature_A_per_m','Bz')]:right.plot(radial_points[:,0]*1000,MU0*radial[key]*1000,'--',label=component_label+' quadrature [mT]')
    axes[1,1].set(xlabel='r [mm]',ylabel='Ephi [MV/m]',title=f'Radial probe: z={probe*1000:g} mm');right.set_ylabel('B quadrature [mT]')
    axes[1,1].legend(loc='upper left');right.legend(loc='upper right')
    for ax in axes[1]:ax.grid(alpha=.25)
    q=te_quantities(solution,mode)
    from matplotlib.font_manager import fontManager, FontProperties
    available = {font.name for font in fontManager.ttflist}
    families = [name for name in ('Noto Sans CJK JP','Noto Serif CJK JP','IPAexGothic','IPAPGothic','IPAPMincho') if name in available]
    title_font = FontProperties(family=families+['DejaVu Sans'])
    fig.suptitle(f'{solution.case.name} | TE {label} | {q["frequency_hz"]/1e6:.6f} MHz\nR/Q and axial accelerating quantities: N/A | E real, H = +i quadrature, exp(+i omega t)\nDisplay subdivisions; input domain only; no peak or convergence certificate',fontproperties=title_font)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        fig.savefig(out, dpi=160)
    finally:
        plt.close(fig)
    return {'probe_z_m': probe, 'radial_points_rz_m': radial_points, 'radial_fields': radial}
