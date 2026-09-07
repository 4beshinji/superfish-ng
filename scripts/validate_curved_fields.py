# SPDX-License-Identifier: Apache-2.0
"""Experimental curved sphere solve, normalization and independent volume fields."""
import argparse
import json
import math
from pathlib import Path
import numpy as np
from superfish_ng import Case
from superfish_ng.conics import LineSegment,EllipseArc
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.mesh_controls import ContourMeshControls
from superfish_ng.curved_solution import solve_curved
from superfish_ng.analytic_sphere import SphereTM
from superfish_ng.curved_rf import quantities_curved
from superfish_ng.curved_sampling import CurvedFieldSampler
from superfish_ng.fem import triangle_quadrature
from superfish_ng.constants import MU0,EPS0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True)
    args=parser.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    radius=.08
    contour=CurvedContour((LineSegment((0,0),(2*radius,0)),
                          EllipseArc((radius,0),(radius,radius),0,math.pi)),('axis','pec'),1e-14)
    case=Case((),name='synthetic_curved_sphere',curved_contour=contour,curve_chord_tolerance_m=.0008,
              contour_mesh=ContourMeshControls(.02),element_order=2,modes=1)
    solution=solve_curved(case,quadrature_order=8)
    reference=SphereTM(radius)
    rule=list(triangle_quadrature(order=8))
    positions=[b[1:] for b,w in rule]
    weights=np.array([w for b,w in rule])
    samples=[]
    signed=0.
    for i,mapping in enumerate(solution.space.geometry.local_maps):
        mapped=mapping.evaluate(positions)
        measure=2*math.pi*weights*mapped['determinant_m2']*mapped['points_rz_m'][:,0]
        actual=solution.fields_in_cell(i,positions)
        exact=reference.fields(actual['points_rz_m'])
        signed+=np.dot(measure,actual['Hphi_A_per_m']*exact['Hphi_A_per_m'])
        samples.append((measure,actual,exact))
    sign=1 if signed>=0 else -1
    numerator=dict(magnetic=0.,electric=0.)
    denominator=dict(magnetic=0.,electric=0.)
    energies=dict(magnetic=0.,electric=0.)
    for measure,actual,exact in samples:
        for name,keys,constant in (('magnetic',['Hphi_A_per_m'],MU0),
                                  ('electric',['Er_quadrature_V_per_m','Ez_quadrature_V_per_m'],EPS0)):
            for key in keys:
                numerator[name]+=np.dot(measure,(sign*actual[key]-exact[key])**2)
                denominator[name]+=np.dot(measure,exact[key]**2)
                energies[name]+=constant/4*np.dot(measure,actual[key]**2)
    errors={name:math.sqrt(numerator[name]/denominator[name]) for name in numerator}
    errors['frequency']=abs(solution.frequencies_hz[0]/reference.frequency_hz-1)
    gates=dict(frequency=errors['frequency']<.001,magnetic=errors['magnetic']<.01,
               electric=errors['electric']<.01,
               normalization=all(abs(v-.5)<1e-8 for v in energies.values()))
    sampler=CurvedFieldSampler(solution)
    axis_q,axis_w=np.polynomial.legendre.leggauss(64)
    axis_points=np.column_stack((np.zeros_like(axis_q),radius*(axis_q+1)))
    axis_actual=sign*sampler.evaluate(axis_points)['Ez_quadrature_V_per_m']
    axis_exact=reference.fields(axis_points)['Ez_quadrature_V_per_m']
    errors['axis_field']=math.sqrt(np.dot(axis_w,(axis_actual-axis_exact)**2)/np.dot(axis_w,axis_exact**2))
    # Physical probe points independent of the mesh; no reference coordinates supplied.
    pq,pw=np.polynomial.legendre.leggauss(8)
    rho=.9*radius*(pq+1)/2
    rr=rho[:,None]*np.sqrt(1-pq**2)
    zz=radius+rho[:,None]*pq
    probe_points=np.column_stack((rr.ravel(),zz.ravel()))
    probe_weights=(rho[:,None]**2*pw[:,None]*pw).ravel()
    probe_actual=sampler.evaluate(probe_points)
    probe_exact=reference.fields(probe_points)
    for name,keys in (('probe_magnetic',['Hphi_A_per_m']),
                      ('probe_electric',['Er_quadrature_V_per_m','Ez_quadrature_V_per_m'])):
        numerator=sum(np.dot(probe_weights,(sign*probe_actual[k]-probe_exact[k])**2) for k in keys)
        denominator=sum(np.dot(probe_weights,probe_exact[k]**2) for k in keys)
        errors[name]=math.sqrt(numerator/denominator)
    gates.update({key:errors[key]<.01 for key in ('axis_field','probe_magnetic','probe_electric')})
    rf=quantities_curved(solution,wall_quadrature_order=8)
    finer_rf=quantities_curved(solution,wall_quadrature_order=12)
    expected_rf=reference.quantities()
    rf_errors={key:abs(rf[key]/expected_rf[key]-1) for key in
               ('r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm',
                'wall_loss_w','q0','transit_time_factor_abs')}
    wall_change=abs(finer_rf['wall_loss_w']/rf['wall_loss_w']-1)
    gates.update({key:value<.01 for key,value in rf_errors.items()})
    gates['wall_quadrature']=wall_change<1e-8
    gates={key:bool(value) for key,value in gates.items()}
    report=dict(scope='experimental curved sphere frequency, volume fields and RF integrals',
                quadrature_order=8,geometry_order=2,element_order=2,
                probe_domain=dict(interior_radius_fraction=.9,interior_points=64,axis_points=64),
                relative_errors=errors,rf_relative_errors=rf_errors,rf=rf,
                wall_quadrature_relative_change=wall_change,energy_j=energies,frequency_hz=float(solution.frequencies_hz[0]),
                residual=float(solution.residuals[0]),gates=gates,
                status='PASS' if all(gates.values()) else 'FAIL',
                pending='surface peaks, native input/save/reload')
    (out/'comparison.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(report,indent=2),flush=True)
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__':
    raise SystemExit(main())
