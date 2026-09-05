# SPDX-License-Identifier: Apache-2.0
"""Optional Matplotlib visualization of an exported run; not required by solver."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.tri as tri


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error('output file already exists')
    result = json.loads((args.run/'results.json').read_text())
    with np.load(args.run/'fields.npz',allow_pickle=False) as data:
        p,t,u = data['points_rz_m'],data['triangles'],data['u_a_per_m2']
    axis = np.loadtxt(args.run/'axis_001.csv',delimiter=',',skiprows=1)
    fig, axes = plt.subplots(1,2,figsize=(11,4.2),layout='constrained')
    mesh = tri.Triangulation(p[:,1]*1000,p[:,0]*1000,t)
    field = p[:,0]*u[:,0]/1000
    cmap = axes[0].tripcolor(mesh,field,shading='gouraud',cmap='viridis',rasterized=True)
    axes[0].set(xlabel='z [mm]',ylabel='r [mm]',title='TM mode 1 | magnetic amplitude')
    axes[0].set_aspect('equal')
    fig.colorbar(cmap,ax=axes[0],label='Signed Hphi [kA/m]')
    axes[1].plot(axis[:,0]*1000,axis[:,1]/1e6,color='#245e94',lw=2)
    axes[1].set(xlabel='z [mm]',ylabel='Ez quadrature [MV/m]',title='On-axis accelerating field')
    axes[1].grid(alpha=.25)
    q = result['modes'][0]
    fig.suptitle(f"{q['frequency_hz']/1e6:.4f} MHz  |  R/Q(acc) = {q['r_over_q_accelerator_ohm']:.3f} ohm  |  U = {q['stored_energy_j']:.3f} J",fontsize=12)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(args.out,dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    main()
