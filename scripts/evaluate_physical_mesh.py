# SPDX-License-Identifier: Apache-2.0
"""Compare original, boundary-sized and locally refined meshes at fixed wall points."""
import argparse
from dataclasses import replace
from pathlib import Path
import sys
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from superfish_ng import Case, make_mesh
from evaluate_surface_fields import run_case, sharp_probes, source_hashes, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    base = replace(Case.load(ROOT/'examples/shaped_cell.json'), modes=1)
    probes = [p for p in sharp_probes(base) if p['corner_index'] in (1, 4)]
    report = {'source_sha256': source_hashes(), 'runs': {},
              'note': 'Exact one-sided wall traces; fixed 1 J, singular peak is not an accuracy target.'}
    for n in (48, 96, 192):
        for method in ('original', 'boundary', 'local'):
            case = replace(base, nr=n, nz=round(n*base.length/.105))
            if method != 'original':
                case = replace(case, boundary_max_edge_m=.105/n)
            if method == 'local':
                case = replace(case, corner_max_edge_m=.105/n/4, corner_radius_m=.01)
            key = f'{method}-{n}'
            report['runs'][key] = run_case(case, args.out/key, probes)
            mesh = make_mesh(case)
            points = mesh.points[mesh.triangles]
            sides = np.linalg.norm(points-np.roll(points, 1, axis=1), axis=2)
            angles = np.arccos(np.clip((sides**2+np.roll(sides, 1, axis=1)**2-np.roll(sides, 2, axis=1)**2)
                                      /(2*sides*np.roll(sides, 1, axis=1)), -1, 1))
            report['runs'][key]['minimum_triangle_angle_deg'] = float(np.rad2deg(angles.min()))
            report['runs'][key]['maximum_triangle_edge_ratio'] = float(np.max(sides.max(axis=1)/sides.min(axis=1)))
            write_json(args.out/key/'result.json', report['runs'][key])
            write_json(args.out/'report.json', report)
    summary = {}
    for method in ('original', 'boundary', 'local'):
        coarse = report['runs'][f'{method}-96']
        fine = report['runs'][f'{method}-192']
        rows = []
        for distance in (.0005, .001, .002, .004, .008):
            pairs = [(a, b) for a, b in zip(coarse['probes'], fine['probes']) if b['distance_m'] == distance]
            rows.append({'distance_m': distance,
                         'max_last_change_percent': 100*max(abs(b['e_max_v_per_m']/a['e_max_v_per_m']-1) for a, b in pairs),
                         'max_tangential_fraction_percent': 100*max(b['tangential_e_max_v_per_m']/b['e_max_v_per_m'] for _, b in pairs)})
        summary[method] = {'nodes': fine['nodes'], 'probes': rows,
                           'rf_last_change_percent': {k: 100*abs(fine['quantities'][k]/coarse['quantities'][k]-1)
                             for k in ('frequency_hz', 'r_over_q_accelerator_ohm')}}
    write_json(args.out/'summary.json', summary)


if __name__ == '__main__':
    main()
