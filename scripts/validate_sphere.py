# SPDX-License-Identifier: Apache-2.0
"""Compare actual curved-contour chord FEM with an independent PEC sphere mode."""
import argparse
import json
import math
from pathlib import Path
import numpy as np
from superfish_ng import Case,solve
from superfish_ng.analytic_sphere import SphereTM
from superfish_ng.conics import LineSegment,EllipseArc
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.mesh_controls import ContourMeshControls
from superfish_ng.io import save_run
from superfish_ng.rf import quantities
from superfish_ng.sampling import FieldSampler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True,exist_ok=False)
    radius = .08
    reference = SphereTM(radius)
    expected = reference.quantities()
    q,w = np.polynomial.legendre.leggauss(16)
    radial = .95*radius*(q+1)/2
    r = radial[:,None]*np.sqrt(1-q**2)
    z = radius+radial[:,None]*q
    positions = np.column_stack((r.ravel(),z.ravel()))
    weights = (radial[:,None]**2*w[:,None]*w).ravel()
    exact = reference.fields(positions)
    axis_q,axis_w = np.polynomial.legendre.leggauss(64)
    axis_positions = np.column_stack((np.zeros_like(axis_q),radius*(axis_q+1)))
    axis_exact = reference.fields(axis_positions)['Ez_quadrature_V_per_m']
    records = []
    for index,tolerance in enumerate((radius/100,radius/400,radius/1600)):
        print(f'Running chord tolerance {tolerance} m',flush=True)
        curve = CurvedContour((LineSegment((0,0),(2*radius,0)),
                               EllipseArc((radius,0),(radius,radius),0,math.pi)),('axis','pec'),1e-14)
        case = Case((),name='synthetic_sphere_chords',curved_contour=curve,
                    curve_chord_tolerance_m=tolerance,contour_mesh=ContourMeshControls(radius/8),
                    element_order=2,modes=1)
        solution = solve(case)
        save_run(case,solution,out/f'point-{index+1:03d}')
        actual = quantities(case,solution)
        sampler = FieldSampler.from_solution(solution)
        field = sampler.evaluate(positions)
        sign = 1 if np.dot(weights,field['Hphi_A_per_m']*exact['Hphi_A_per_m'])>=0 else -1
        errors = {key:abs(actual[key]/expected[key]-1) for key in
                  ('frequency_hz','r_over_q_accelerator_ohm','r_over_q_circuit_ohm',
                   'geometry_factor_ohm','wall_loss_w','transit_time_factor_abs')}
        for name,keys in [('magnetic_field',['Hphi_A_per_m']),
                          ('electric_field',['Er_quadrature_V_per_m','Ez_quadrature_V_per_m'])]:
            numerator = sum(np.dot(weights,(sign*field[k]-exact[k])**2) for k in keys)
            denominator = sum(np.dot(weights,exact[k]**2) for k in keys)
            errors[name] = math.sqrt(numerator/denominator)
        axis = sign*sampler.evaluate(axis_positions)['Ez_quadrature_V_per_m']
        errors['axis_field'] = math.sqrt(np.dot(axis_w,(axis-axis_exact)**2)/np.dot(axis_w,axis_exact**2))
        limits = {key:(.001 if key=='frequency_hz' else .01) for key in errors}
        gates = {key:errors[key]<limits[key] for key in errors}
        records.append(dict(tolerance_m=tolerance,triangles=len(solution.mesh.triangles),
                            actual=actual,relative_errors=errors,limits=limits,gates=gates,
                            status='PASS' if all(gates.values()) else 'FAIL'))
        print(records[-1]['status'],errors,flush=True)
    report = dict(reference=expected,records=records,status=records[-1]['status'],
                  mode='regular spherical l=1 m=0 TM, first radial root',
                  normalization='SI peak phasors, total energy 1 J',
                  field_domain='volume-weighted samples within 0.95R; full axis separately',
                  surface_field='integrated wall loss compared; surface peaks not certified')
    (out/'comparison.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return 0 if report['status']=='PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
