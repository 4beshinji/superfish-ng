# SPDX-License-Identifier: Apache-2.0
"""Re-read saved SFO evidence and plot comparison without re-running Wine."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from compare_superfish import parse_sfo, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--out', type=Path, required=True, help='new summary directory')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    report = json.loads((args.run / 'comparison.json').read_text())
    fig, axes = plt.subplots(3, len(report['cases']), figsize=(14, 10), layout='constrained')
    for column, case in enumerate(report['cases']):
        for row in case['runs']:
            folder = args.run / case['name'] / f'level-{row["ng_nr"]}'
            sf = parse_sfo(folder / 'superfish/CAVITY.SFO')
            sf.pop('axis')
            # Correct metadata only; fail if re-parsing would change any result.
            if sf['quantities'] != row['sf']['quantities']:
                raise ValueError('re-parsing changed numerical evidence')
            row['sf'] = sf
        for solver, label, marker in [('sf', 'SUPERFISH / Wine', 'o'), ('ng', 'Superfish-NG', 's')]:
            nodes = [r[solver]['nodes'] for r in case['runs']]
            freq = [r[solver]['quantities']['frequency_hz']/1e6 for r in case['runs']]
            rq = [r[solver]['quantities']['r_over_q_accelerator_ohm'] for r in case['runs']]
            axes[0, column].plot(nodes, freq, marker=marker, label=label)
            axes[1, column].plot(nodes, rq, marker=marker, label=label)
        axes[0, column].set(title=case['name'], ylabel='Frequency [MHz]', xlabel='Mesh nodes', xscale='log')
        axes[1, column].set(ylabel='R/Q accelerator [ohm]', xlabel='Mesh nodes', xscale='log')
        finest = case['runs'][-1]
        folder = args.run / case['name'] / f'level-{finest["ng_nr"]}'
        sf = parse_sfo(folder / 'superfish/CAVITY.SFO')
        sa = np.asarray(sf['axis'])
        ng = np.loadtxt(folder / 'ng/axis_001.csv', delimiter=',', skiprows=1)
        ea = sa[:, 1] / np.sqrt(sf['quantities']['stored_energy_j'])
        sign = 1 if np.dot(ea, np.interp(sa[:, 0], ng[:, 0], ng[:, 1])) >= 0 else -1
        axes[2, column].plot(sa[:, 0]*1000, ea/1e6, label='SUPERFISH / Wine')
        axes[2, column].plot(ng[:, 0]*1000, sign*ng[:, 1]/1e6, '--', label='Superfish-NG')
        axes[2, column].set(ylabel='Ez [MV/m], U=1 J', xlabel='z [mm]', title=f'Axis relative L2: {finest["axis_relative_l2"]:.3%}')
        for ax in axes[:, column]:
            ax.grid(alpha=.25)
            ax.legend(fontsize=8)
    report['metadata_reparsed_from_sfo'] = True
    report['parser_sha256'] = hashlib.sha256((Path(__file__).parent/'compare_superfish.py').read_bytes()).hexdigest()
    write_json(args.out / 'comparison.json', report)
    fig.suptitle('Independent solvers: closed PEC fundamental modes, beta=1, same copper conductivity')
    fig.savefig(args.out / 'comparison.png', dpi=160)
    plt.close(fig)
    print(f'Wrote verified metadata and plot: {args.out}')


if __name__ == '__main__':
    main()
