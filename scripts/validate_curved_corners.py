# SPDX-License-Identifier: Apache-2.0
"""Record a sharp reentrant PEC corner without certifying a finite physical peak."""
import argparse
from dataclasses import replace
import json
import math
from pathlib import Path
from superfish_ng import Case, solve
from superfish_ng.conics import LineSegment
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.mesh_controls import ContourMeshControls
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    vertices = ((0., 0.), (.2, 0.), (.2, .1), (.1, .1), (.1, .05), (0., .05))
    contour = CurvedContour(tuple(LineSegment(vertices[i], vertices[(i+1)%6]) for i in range(6)),
                            ('axis', 'pec', 'pec', 'pec', 'pec', 'pec'), 0.)
    case = Case((), name='synthetic_reentrant_corner', curved_contour=contour, curve_chord_tolerance_m=.001,
                contour_mesh=ContourMeshControls(.04), geometry_order=2, element_order=2, modes=1)
    records = []
    for level in (0, 1):
        current = replace(case, curved_refinement_levels=level)
        target = args.out/f'level-{level}'
        save_run(current, solve(current), target)
        result = read_solution(target).results
        diagnosis = result['surface_corner_diagnostics']
        corners = [j for j in diagnosis['joins'] if j['classification'] == 'reentrant_pec_corner']
        passed = len(corners) == 1 and abs(corners[0]['vacuum_interior_angle_rad']-1.5*math.pi) < 1e-12
        records.append(dict(level=level, diagnostic_status='PASS' if passed else 'FAIL',
                            diagnostic=diagnosis, mode=result['modes'][0]))
    report = dict(status='PASS' if all(r['diagnostic_status'] == 'PASS' for r in records) else 'FAIL',
                  scope='geometric corner identification and portable diagnostic integrity only',
                  physical_peak_status='UNVERIFIED', levels=records,
                  frequency_relative_change=abs(records[1]['mode']['frequency_hz']/records[0]['mode']['frequency_hz']-1),
                  discrete_epeak_ratio=records[1]['mode']['epk_surface_estimate_v_per_m']/records[0]['mode']['epk_surface_estimate_v_per_m'])
    (args.out/'comparison.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps(report, indent=2), flush=True)
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
