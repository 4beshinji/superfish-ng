# SPDX-License-Identifier: Apache-2.0
"""Reproducible curved sphere mesh Study with independent frequency and RF gates."""
import argparse
import json
import math
from pathlib import Path
from superfish_ng import Case
from superfish_ng.conics import LineSegment, EllipseArc
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.mesh_controls import ContourMeshControls
from superfish_ng.project import Project
from superfish_ng.studies import Study, execute_study
from superfish_ng.analytic_sphere import SphereTM


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    radius = .08
    case = Case((), name='synthetic_curved_sphere_study',
                curved_contour=CurvedContour((LineSegment((0, 0), (2*radius, 0)),
                    EllipseArc((radius, 0), (radius, radius), 0, math.pi)), ('axis', 'pec'), 1e-14),
                curve_chord_tolerance_m=.0008, contour_mesh=ContourMeshControls(.02),
                element_order=2, geometry_order=2, modes=1)
    args.out.mkdir(parents=True, exist_ok=False)
    study = Study(Project.from_dict(case.to_dict()), 'mesh_convergence', 'mesh_scale', [1, 2])
    report = execute_study(study, args.out/'study')
    reference = SphereTM(radius)
    expected = reference.quantities()
    errors = []
    for point in report['points']:
        actual = point['modes'][0]
        errors.append({key: abs(actual[key]/expected[key]-1) for key in
                       ('frequency_hz', 'r_over_q_accelerator_ohm', 'r_over_q_circuit_ohm',
                        'q0', 'geometry_factor_ohm', 'wall_loss_w', 'transit_time_factor_abs')})
    passed = report['numerical_status'] == 'PASS' and all(
        value < (.001 if key == 'frequency_hz' else .01) for error in errors for key, value in error.items())
    result = dict(status='PASS' if passed else 'FAIL', relative_errors=errors,
                  refinement=report['comparisons'], geometry_refinement=report['geometry_refinement'],
                  pending='fixed discrete geometry h-refinement, curved surface peaks, reflection and GUI acceptance')
    (args.out/'comparison.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps(result, indent=2), flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
