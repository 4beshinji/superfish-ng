# SPDX-License-Identifier: Apache-2.0
"""Experimental global curved-P2 eigenvalue and quadrature check, not RF acceptance."""
import argparse
import json
import math
from pathlib import Path
import numpy as np
from scipy.sparse import diags
from scipy.sparse.linalg import eigsh
from superfish_ng import Case
from superfish_ng.analytic_sphere import SphereTM
from superfish_ng.conics import LineSegment,EllipseArc
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.curved_space import curved_space
from superfish_ng.curved_fem import assemble_curved
from superfish_ng.mesh import make_mesh
from superfish_ng.mesh_controls import ContourMeshControls
from superfish_ng.constants import C0,TAU


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True,exist_ok=False)
    radius = .08
    contour = CurvedContour((LineSegment((0,0),(2*radius,0)),
                             EllipseArc((radius,0),(radius,radius),0,math.pi)),('axis','pec'),1e-14)
    case = Case((),name='synthetic_curved_sphere',curved_contour=contour,curve_chord_tolerance_m=.0008,
                contour_mesh=ContourMeshControls(.02),element_order=2,modes=1)
    mesh = make_mesh(case)
    space = curved_space(case,mesh)
    (out/'source-chord-case.json').write_text(json.dumps(case.to_dict(),indent=2)+'\n')
    reference = SphereTM(radius).frequency_hz
    records = []
    for order in (4,8,12):
        print(f'Assembling quadrature order {order}',flush=True)
        k,m = assemble_curved(space,quadrature_order=order)
        free = np.setdiff1d(np.arange(k.shape[0]),space.constrained_dofs)
        kr,mr = k[free][:,free],m[free][:,free]
        scale = diags(1/np.sqrt(mr.diagonal()))
        a,b = scale@kr@scale,scale@mr@scale
        value,vector = eigsh(a,k=1,M=b,sigma=0.,which='LM',tol=1e-11,
                            v0=np.random.default_rng(20260905).normal(size=len(free)))
        u = scale@vector[:,0]
        ku,mu = kr@u,mr@u
        residual = float(np.linalg.norm(ku-value[0]*mu)/(np.linalg.norm(ku)+value[0]*np.linalg.norm(mu)))
        frequency = C0*math.sqrt(value[0])/TAU
        error = abs(frequency/reference-1)
        records.append(dict(quadrature_order=order,frequency_hz=frequency,
                            relative_frequency_error=error,algebraic_residual=residual))
        print(records[-1],flush=True)
    change = abs(records[-1]['frequency_hz']/records[-2]['frequency_hz']-1)
    gates = dict(frequency=records[-1]['relative_frequency_error']<.001,
                 quadrature=change<1e-8,
                 algebraic_residual=all(r['algebraic_residual']<1e-7 for r in records))
    report = dict(scope='experimental curved-P2 sphere frequency only; field/RF/storage not accepted',
                  geometry_order=2,element_order=2,
                  cells=len(space.geometry.cell_nodes),nodes=len(space.geometry.points_rz_m),
                  edge_check=dict(space.edge_check),boundary_check=dict(space.geometry.boundary_check),
                  reference_frequency_hz=reference,records=records,
                  last_quadrature_relative_change=change,gates=gates,
                  status='PASS' if all(gates.values()) else 'FAIL')
    (out/'comparison.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__':
    raise SystemExit(main())
