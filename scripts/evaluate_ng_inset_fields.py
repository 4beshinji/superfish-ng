# SPDX-License-Identifier: Apache-2.0
"""Evaluate identical near-wall vacuum coordinates used by Wine/SF7."""
import argparse
from dataclasses import replace
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
import numpy as np
from superfish_ng import Case, solve
from superfish_ng.rf import quantities
from superfish_ng.sampling import FieldSampler
from evaluate_surface_fields import write_json
from evaluate_wine_surface_fields import inset_probes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    base = replace(Case.load(ROOT/'examples/shaped_cell.json'), modes=1, conductivity_s_per_m=1/1.7241e-8)
    probes = [p for inset in [1e-7, 1e-6] for p in inset_probes(base, inset)]
    report = {'insets_m': [1e-7, 1e-6], 'normalization_j': 1., 'runs': {},
              'note': 'Vacuum-side fields, not exact surface traces; compare only identical coordinates.',
              'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in [Path(__file__).resolve(), ROOT/'scripts/evaluate_wine_surface_fields.py',
                                         *sorted((ROOT/'src/superfish_ng').glob('*.py'))]}}
    for triangulation in ['diagonal', 'crossed']:
        series = 'sharp_'+triangulation
        report['runs'][series] = []
        for n in [96, 192, 384]:
            case = replace(base, nr=n, nz=round(n*base.length/.105), triangulation=triangulation)
            solution = solve(case)
            sampler = FieldSampler(solution.mesh.points, solution.mesh.triangles, solution.u, solution.frequencies_hz)
            fields = sampler.evaluate([p['point_rz_m'] for p in probes])
            magnitude = np.hypot(fields['Er_quadrature_V_per_m'], fields['Ez_quadrature_V_per_m'])
            row = {'nr': n, 'quantities': quantities(case, solution),
                   'probes': [dict(p, e_v_per_m=float(e)) for p, e in zip(probes, magnitude)]}
            folder = out/f'{series}-{n}'
            folder.mkdir()
            write_json(folder/'case.json', case.to_dict())
            write_json(folder/'result.json', row)
            np.savez_compressed(folder/'field.npz', points=solution.mesh.points, triangles=solution.mesh.triangles,
                                u=solution.u, frequencies_hz=solution.frequencies_hz)
            report['runs'][series].append(row)
            write_json(out/'report.json', report)
            print(f'{series} nr={n}: {len(probes)} common vacuum-side probes', flush=True)


if __name__ == '__main__':
    main()
