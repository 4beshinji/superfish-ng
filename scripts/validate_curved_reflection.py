# SPDX-License-Identifier: Apache-2.0
"""Validate fixed curved mirror maps against parity and energy invariants."""
import argparse
from dataclasses import replace
import json
import math
from pathlib import Path
import numpy as np
from superfish_ng import Case
from superfish_ng.conics import LineSegment, EllipseArc
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.mesh_controls import ContourMeshControls
from superfish_ng.curved_solution import CurvedSolution, solve_curved
from superfish_ng.curved_reflection import reflect_curved_space
from superfish_ng.curved_fem import assemble_curved
from superfish_ng.curved_rf import quantities_curved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    records = []
    for side in ('z_min', 'z_max'):
        for tag in ('electric_symmetry', 'magnetic_symmetry'):
            axis = LineSegment((0., 0.), (.08, 0.))
            if side == 'z_min':
                curves = (axis, EllipseArc((0., 0.), (.08, .08), 0., math.pi/2), LineSegment((0., .08), (0., 0.)))
                tags = ('axis', 'pec', tag)
            else:
                curves = (axis, LineSegment((.08, 0.), (.08, .08)), EllipseArc((.08, 0.), (.08, .08), math.pi/2, math.pi/2))
                tags = ('axis', tag, 'pec')
            case = Case((), name='synthetic_half_sphere', curved_contour=CurvedContour(curves, tags, 1e-14),
                        curve_chord_tolerance_m=.002, contour_mesh=ContourMeshControls(.03),
                        element_order=2, geometry_order=2, quadrature_order=12, curved_refinement_levels=1, modes=1)
            half = solve_curved(case)
            reflection = reflect_curved_space(case, half.space)
            full_case = replace(case, contour=None, curved_contour=reflection.reflected_contour,
                                z_min='pec', z_max='pec', normalization_j=2*case.normalization_j,
                                **case.reflected_acceleration_parameters(side))
            u = reflection.apply(half.u)
            k, m = assemble_curved(reflection.space, quadrature_order=12)
            ku, mu = k@u, m@u
            residual = float(np.linalg.norm(ku-mu*half.eigenvalues)/(np.linalg.norm(ku)+half.eigenvalues[0]*np.linalg.norm(mu)))
            full = CurvedSolution(full_case, reflection.space, k, m, half.eigenvalues, half.frequencies_hz,
                                  u, np.array([residual]), 0., 12, None)
            a, b = quantities_curved(half, include_surface_peaks=False), quantities_curved(full, include_surface_peaks=False)
            ratios = {key: b[key]/a[key] for key in ('stored_energy_j', 'electric_energy_j', 'magnetic_energy_j', 'wall_loss_w')}
            field_error = 0.
            for cell in range(len(half.space.geometry.cell_nodes)):
                original = half.fields_in_cell(cell, [[.2, .3]])
                mirrored = full.fields_in_cell(cell+len(half.space.geometry.cell_nodes), [[.3, .2]])
                for key, sign in (('Hphi_A_per_m', reflection.parity), ('Er_quadrature_V_per_m', -reflection.parity), ('Ez_quadrature_V_per_m', reflection.parity)):
                    # Compare each component relative to its magnitude, with a unit floor near zero.
                    field_error = max(field_error, float(np.max(abs(mirrored[key]-sign*original[key])))/max(1., float(np.max(abs(original[key])))))
            passed = residual < 1e-7 and field_error < 1e-8 and all(abs(v/2-1) < 1e-10 for v in ratios.values())
            records.append(dict(side=side, tag=tag, status='PASS' if passed else 'FAIL',
                                frequency_hz=float(half.frequencies_hz[0]), residual=residual,
                                energy_and_loss_ratios=ratios, field_parity_relative_error=field_error,
                                half_cells=len(half.space.geometry.cell_nodes), full_cells=len(reflection.space.geometry.cell_nodes)))
    report = dict(status='PASS' if all(r['status']=='PASS' for r in records) else 'FAIL', records=records,
                  scope='fixed curved space reflection and field/RF invariants; public solve/save/CLI reflection integration pending')
    (args.out/'comparison.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps(report, indent=2), flush=True)
    return 0 if report['status']=='PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
