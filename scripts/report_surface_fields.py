# SPDX-License-Identifier: Apache-2.0
"""Create tables and a standalone scientific figure from surface diagnostics."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.report.read_text())
    args.out.mkdir(parents=True, exist_ok=False)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    summary = {'status': data['status'],
               'input_report_sha256': hashlib.sha256(args.report.read_bytes()).hexdigest(),
               'last_mesh_changes_percent': {}, 'sharp_probe_changes_percent': {}}
    keys = ['frequency_hz', 'r_over_q_accelerator_ohm', 'epk_surface_estimate_v_per_m', 'epk_over_eacc_estimate']
    with (args.out/'mesh_results.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['series', 'nr', 'nz', 'nodes', 'peak_edge_h_m', 'peak_cell_diameter_m']+keys)
        for series, rows in data['runs'].items():
            for row in rows:
                writer.writerow([series]+[row[k] for k in ['nr', 'nz', 'nodes', 'peak_edge_h_m', 'peak_cell_diameter_m']]
                                +[row['quantities'][k] for k in keys])
            a, b = [row['quantities'] for row in rows[-2:]]
            summary['last_mesh_changes_percent'][series] = {k: 100*abs(b[k]/a[k]-1) for k in keys}
    with (args.out/'fixed_distance_probes.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['series', 'nr', 'corner_index', 'side', 'distance_m', 'r_m', 'z_m',
                         'e_min_v_per_m', 'e_max_v_per_m', 'tangential_e_max_v_per_m',
                         'trace_count', 'edge_h_max_m', 'cell_diameter_max_m'])
        for series in ['sharp_diagonal', 'sharp_crossed']:
            rows = data['runs'][series]
            for row in rows:
                for p in row['probes']:
                    writer.writerow([series, row['nr'], p['corner_index'], p['side'], p['distance_m']]
                                    +p['point_rz_m']+[p[k] for k in ['e_min_v_per_m', 'e_max_v_per_m',
                                      'tangential_e_max_v_per_m', 'trace_count', 'edge_h_max_m', 'cell_diameter_max_m']])
            summary['sharp_probe_changes_percent'][series] = {}
            for distance in [.0005, .001, .002, .004, .008]:
                changes = [100*abs(b['e_max_v_per_m']/a['e_max_v_per_m']-1)
                           for a, b in zip(rows[-2]['probes'], rows[-1]['probes'])
                           if a['corner_index'] in [1, 4] and a['distance_m'] == distance]
                summary['sharp_probe_changes_percent'][series][str(distance)] = max(changes)
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), constrained_layout=True)
    for series in ['sharp_diagonal', 'sharp_crossed']:
        rows = data['runs'][series]
        n = [r['nr'] for r in rows]
        axes[0, 0].plot(n, [r['quantities']['epk_over_eacc_estimate'] for r in rows], 'o-', label=series)
        for side, style in [('before', '-'), ('after', '--')]:
            values = [next(p['e_max_v_per_m']/1e6 for p in r['probes']
                           if p['corner_index'] == 1 and p['side'] == side and p['distance_m'] == .004)
                      for r in rows]
            axes[0, 1].plot(n, values, style, marker='o', label=f'{series}, {side}')
    # Historical Wine number is documentary only, not new or converged evidence.
    axes[0, 0].axhline(2.42008, color='gray', linestyle=':', label='historical Wine DX=0.1 cm (unverified here)')
    axes[0, 0].set(title='Sharp corners: peak keeps increasing', ylabel='Epk / Eacc')
    axes[0, 1].set(title='Fixed surface distance: 4 mm from left neck corner', ylabel='|E| at U=1 J [MV/m]')
    for series, rows in data['runs'].items():
        if series.startswith('rounded-'):
            axes[1, 0].plot([r['nr'] for r in rows], [r['quantities']['epk_over_eacc_estimate'] for r in rows],
                            'o-', label=series)
    axes[1, 0].set(title='New control geometry: tangent 3 mm fillets', ylabel='Epk / Eacc')
    rows = data['runs']['pillbox']
    for key in ['peak_relative_error', 'surface_max_absolute_error_over_e0']:
        axes[1, 1].plot([r['nr'] for r in rows], [100*r['analytic'][key] for r in rows], 'o-', label=key)
    axes[1, 1].set(title='Pillbox: independent Bessel-field control', ylabel='Error [%]', yscale='log')
    for axis in axes.flat:
        axis.set_xscale('log', base=2)
        axis.set_xlabel('Radial divisions nr (not a cross-code mesh-size measure)')
        axis.grid(True, alpha=.3)
        axis.legend(fontsize=7)
    fig.suptitle('NG surface-field diagnostics — Wine accuracy ranking remains unverified')
    fig.savefig(args.out/'surface_convergence.png', dpi=180)
    fig.savefig(args.out/'surface_convergence.pdf')
    plt.close(fig)
    (args.out/'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False)+'\n')


if __name__ == '__main__':
    main()
