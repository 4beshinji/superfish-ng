# SPDX-License-Identifier: Apache-2.0
"""Independent sphere wall-field checks, separate from volume and RF integrals."""
import argparse
from dataclasses import replace
import json
import math
from pathlib import Path
import numpy as np
from superfish_ng import Case, solve
from superfish_ng.conics import LineSegment, EllipseArc
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.mesh_controls import ContourMeshControls
from superfish_ng.analytic_sphere import SphereTM
from superfish_ng.curved_surface import CurvedSurfaceSampler, sampled_surface_summary
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    radius = .08
    case = Case((), name='synthetic_sphere_surface', curved_contour=CurvedContour(
                (LineSegment((0, 0), (2*radius, 0)), EllipseArc((radius, 0), (radius, radius), 0, math.pi)),
                ('axis', 'pec'), 1e-14), curve_chord_tolerance_m=.0008,
                contour_mesh=ContourMeshControls(.02), element_order=2, geometry_order=2, modes=1)
    reference = SphereTM(radius)
    # On a sphere, |E_surface| is proportional to |cos(theta)| and H to sin(theta).
    pole = reference.fields([[0., 0.]])
    equator = reference.fields([[radius, radius]])
    exact_epeak = float(abs(pole['Ez_quadrature_V_per_m'][0]))
    exact_hpeak = float(abs(equator['Hphi_A_per_m'][0]))
    q, w = np.polynomial.legendre.leggauss(8)
    reports = []
    for level in (0, 1):
        current = replace(case, curved_refinement_levels=level)
        target = args.out/f'level-{level}'
        save_run(current, solve(current), target)
        solution = read_solution(target)
        sampler = CurvedSurfaceSampler(solution)
        samples = []
        for edge in np.flatnonzero(solution.space.boundary_tags == 'pec'):
            field = sampler.evaluate(int(edge), (q+1)/2)
            expected = reference.fields(field['points_rz_m'])
            measure = math.pi*w*field['points_rz_m'][:, 0]*field['arc_length_derivative_m']
            samples.append((field, expected, measure))
        sign = 1 if sum(np.dot(weight, a['Hphi_A_per_m']*b['Hphi_A_per_m'])
                        for a, b, weight in samples) >= 0 else -1
        errors = {}
        for name, keys in (('surface_electric', ('Er_quadrature_V_per_m', 'Ez_quadrature_V_per_m')),
                           ('surface_magnetic', ('Hphi_A_per_m',))):
            numerator = sum(np.dot(weight, (sign*a[key]-b[key])**2)
                            for a, b, weight in samples for key in keys)
            denominator = sum(np.dot(weight, b[key]**2) for a, b, weight in samples for key in keys)
            errors[name] = float(math.sqrt(numerator/denominator))
        summary = sampled_surface_summary(solution, samples_per_edge=33)
        errors['sampled_epeak'] = abs(summary['E_abs_V_per_m']['value']/exact_epeak-1)
        errors['sampled_hpeak'] = abs(summary['Hphi_A_per_m']['value']/exact_hpeak-1)
        errors['pec_tangent_over_reference_epeak'] = summary['Et_quadrature_V_per_m']['value']/exact_epeak
        reports.append(dict(refinement_level=level, relative_errors=errors, samples=summary,
                            status='PASS' if all(value < .01 for value in errors.values()) else 'FAIL'))
    report = dict(status='PASS' if all(item['status'] == 'PASS' for item in reports) else 'FAIL',
                  reference_peaks=dict(electric_v_per_m=exact_epeak, magnetic_a_per_m=exact_hpeak),
                  relative_limit=.01, levels=reports,
                  scope='sphere boundary traces, PEC tangent, sampled maxima; independent of volume/RF gates',
                  pending='continuous boundary extrema bounds, general corner policy and peak/RF/GUI integration')
    (args.out/'comparison.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps(report, indent=2), flush=True)
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
