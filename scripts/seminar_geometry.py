# SPDX-License-Identifier: Apache-2.0
"""Vary circular chord tolerance at fixed nominal FEM counts for seminar cases."""
import argparse
from dataclasses import replace
from pathlib import Path
import sys
import json
import hashlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
import numpy as np
from superfish_ng import Case, solve
from superfish_ng.geometry import profile_area
from superfish_ng.io import save_run
from superfish_ng.mesh import element_geometry
from superfish_ng.modes import identify_cell_band
from seminar_multicell import EXERCISES, relative, gates
from compare_superfish import write_json


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=['rounded4', 'rounded7'], required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--nr', type=int, default=128)
    parser.add_argument('--triangulation', choices=['diagonal', 'crossed'], help='explicit P1 quad subdivision')
    parser.add_argument('--tolerances-m', type=float, nargs='+', default=[1.2e-5, 3e-6, 7.5e-7])
    args = parser.parse_args(argv)
    tolerances = args.tolerances_m
    if (len(tolerances) < 3 or any(not np.isfinite(t) or t <= 0 for t in tolerances)
            or any(b >= a for a, b in zip(tolerances, tolerances[1:]))):
        parser.error('at least three strictly decreasing positive chord tolerances are required')
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    sources = sorted((ROOT/'src').rglob('*.py'))+[Path(__file__).resolve(), ROOT/'scripts/seminar_multicell.py']
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    base = Case.load(ROOT/'examples'/EXERCISES[args.case][0])
    if args.triangulation is not None:
        base = replace(base, triangulation=args.triangulation)
    report = {'scope': 'chord tolerance variation at fixed nr/nz; boundary vertices and total DOF also change',
              'case': args.case, 'nr': args.nr, 'nz': round(args.nr*base.nz/base.nr), 'levels': [],
              'limits': {'frequency_relative': .001, 'rf_relative': .01}, 'source_sha256': hashes}
    for i, tolerance in enumerate(tolerances):
        case = replace(base, nr=report['nr'], nz=report['nz'], arc_chord_tolerance_m=tolerance)
        solution = solve(case)
        run = save_run(case, solution, out/f'level{i}')
        _, det, _ = element_geometry(solution.mesh)
        axes = [np.loadtxt(out/f'level{i}'/f'axis_{m+1:03d}.csv', delimiter=',', skiprows=1) for m in range(case.modes)]
        identity = identify_cell_band(axes[0][:, 0], np.column_stack([a[:, 1] for a in axes]), np.linspace(0., case.length, case.modes))
        exact_area, mesh_area = profile_area(case), float(det.sum()/2)
        modes = [dict(mode, quantities=run['modes'][mode['mode_index']-1]) for mode in identity]
        row = {'chord_tolerance_m': tolerance, 'exact_area_m2': exact_area, 'mesh_area_m2': mesh_area,
               'area_absolute_error_m2': abs(mesh_area-exact_area), 'mesh': run['mesh'], 'modes': modes}
        report['levels'].append(row)
        print(f'{args.case} chord={tolerance:g} m, nodes={len(solution.mesh.points)}, area error={row["area_absolute_error_m2"]:.3g} m2', flush=True)
    last, previous = report['levels'][-1], report['levels'][-2]
    checks = []
    for a, b in zip(last['modes'], previous['modes']):
        a['geometry_refinement_errors'] = relative(a['quantities'], b['quantities'])
        a['geometry_refinement_gates'] = gates(a['geometry_refinement_errors'])
        checks.extend(a['geometry_refinement_gates'].values())
    areas = [row['area_absolute_error_m2'] for row in report['levels']]
    report['area_error_decreases'] = all(b < a for a, b in zip(areas, areas[1:]))
    report['source_changed_during_run'] = hashes != {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    report['passed'] = all(checks) and report['area_error_decreases'] and not report['source_changed_during_run']
    report['environment'] = run['environment']
    write_json(out/'comparison.json', report)
    print(f'{"PASS" if report["passed"] else "FAIL"}: {out}/comparison.json', flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
