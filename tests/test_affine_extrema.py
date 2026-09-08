# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from fractions import Fraction
import math
import unittest
import numpy as np
from superfish_ng import Case,solve
from superfish_ng.constants import EPS0,TAU
from superfish_ng.affine_extrema import AffineSurfaceTrace,bound_affine_surface_peaks


def evaluate(coefficients,t):return sum(c*Fraction(float(t))**i for i,c in enumerate(coefficients))


class AffineExtremaTests(unittest.TestCase):
    def test_polynomial_fields_match_independent_physical_derivatives(self):
        for order in (1,2):
            case=Case(profile=((0.,1.),(.75,1.25)),nr=2,nz=2,modes=1,element_order=order)
            sol=solve(case);points=sol.space.dof_points if order==2 else sol.mesh.points;r,z=points.T
            sol.u[:,0]=1+2*r+3*z+(4*r*r+5*r*z+6*z*z if order==2 else 0)
            trace=AffineSurfaceTrace(case,sol);factor=TAU*sol.frequencies_hz[0]*EPS0
            for edge,ends in enumerate(sol.mesh.boundary_edges):
                functions=trace.edge_polynomials(edge)
                for t in (0.,.125,.3,.75,1.):
                    r,z=(1-t)*sol.mesh.points[ends[0]]+t*sol.mesh.points[ends[1]]
                    u=1+2*r+3*z+(4*r*r+5*r*z+6*z*z if order==2 else 0)
                    dr=2+(8*r+5*z if order==2 else 0);dz=3+(5*r+12*z if order==2 else 0)
                    actual=[float(evaluate(n,t)/evaluate(functions['denominator'],t)) for n in functions['electric']]
                    np.testing.assert_allclose(actual,[-r*dz/factor,(2*u+r*dr)/factor],rtol=4e-13,atol=1e-12)
                    self.assertAlmostEqual(float(evaluate(functions['magnetic'],t)),r*u,places=11)

    def test_known_interior_maximum_and_budget_failure(self):
        for order in (1,2):
            case=Case(profile=((0.,1.),(1.,1.)),nr=2,nz=2,modes=1,element_order=order)
            sol=solve(case);r=(sol.space.dof_points if order==2 else sol.mesh.points)[:,0]
            sol.u[:,0]=(1.5 if order==1 else 1)-r**order
            report=bound_affine_surface_peaks(case,sol,relative_tolerance=1e-8)
            exact=.5625 if order==1 else 2/(3*math.sqrt(3))
            bounds=report['magnetic_a_per_m'];self.assertLessEqual(bounds['lower_bound'],exact);self.assertGreaterEqual(bounds['upper_bound'],exact)
            self.assertLessEqual(bounds['upper_bound']/bounds['lower_bound']-1,1e-8)
            self.assertEqual(sol.mesh.boundary_tags[bounds['boundary_index']],'pec')
            self.assertTrue(0<bounds['parameter']<1)
            self.assertIsNone(report['physical_error_bound'])
            with self.assertRaisesRegex(ValueError,'UNVERIFIED'):bound_affine_surface_peaks(case,sol,max_boxes_per_edge=1,relative_tolerance=1e-12)

    def test_amplitude_sign_zero_and_symmetry_exclusion(self):
        for order in (1,2):
            case=Case(profile=((0.,1.),(1.,1.)),nr=2,nz=2,modes=1,element_order=order,z_min='electric_symmetry')
            sol=solve(case);sol.u[:]=1
            initial=bound_affine_surface_peaks(case,sol)
            for scale in (-1e100,1e-100):
                changed=bound_affine_surface_peaks(case,replace(sol,u=sol.u*scale))
                for key in ('electric_v_per_m','magnetic_a_per_m'):
                    for side in ('lower_bound','upper_bound'):self.assertAlmostEqual(changed[key][side]/abs(scale)/initial[key][side],1.,places=13)
            self.assertEqual(initial['pec_edges'],int(np.sum(sol.mesh.boundary_tags=='pec')))
            zero=bound_affine_surface_peaks(case,replace(sol,u=sol.u*0))
            self.assertEqual(zero['electric_v_per_m']['upper_bound'],0.)
            self.assertEqual(zero['magnetic_a_per_m']['upper_bound'],0.)

    def test_strict_inputs_and_canonical_space(self):
        case=Case(profile=((0.,.1),(.2,.1)),nr=2,nz=2,modes=1,element_order=2);sol=solve(case)
        for kwargs in (dict(mode=True),dict(mode=-1),dict(relative_tolerance=True),dict(max_boxes_per_edge=0)):
            with self.assertRaises(ValueError):bound_affine_surface_peaks(case,sol,**kwargs)
        for bad in (replace(sol,u=sol.u.astype(complex)),replace(sol,u=sol.u*np.nan),replace(sol,frequencies_hz=np.array([0.])),replace(sol,space=None)):
            with self.assertRaises(ValueError):bound_affine_surface_peaks(case,bad)
        trace=AffineSurfaceTrace(case,sol)
        with self.assertRaises(ValueError):trace.edge_polynomials(True)

    def test_native_save_cli_replay_and_source_tamper(self):
        from pathlib import Path
        import tempfile,json
        from superfish_ng.io import save_run
        from superfish_ng.affine_extrema import save_affine_peaks,read_affine_peaks,replay_affine_peaks
        from superfish_ng.cli import main
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);case=Case(profile=((0.,.1),(.2,.1)),nr=3,nz=3,modes=1,element_order=2);sol=solve(case)
            save_run(case,sol,root/'native');out=root/'peaks.json'
            result=save_affine_peaks(root/'native',out)
            self.assertEqual(read_affine_peaks(out),result)
            changed=json.loads(out.read_text());changed['peaks']['magnetic_a_per_m']['upper_bound']*=1.01
            with self.assertRaisesRegex(ValueError,'replay'):replay_affine_peaks(changed)
            self.assertEqual(main(['bound-affine-peaks',str(root/'native'),'--out',str(root/'cli.json')]),0)
            self.assertEqual(main(['replay-affine-peaks',str(root/'cli.json')]),0)
            self.assertEqual(read_affine_peaks(root/'cli.json'),result)
            self.assertNotEqual(main(['bound-affine-peaks',str(root/'native'),'--mode','0','--out',str(root/'invalid.json')]),0)
            self.assertFalse((root/'invalid.json').exists())
            source=root/'native/case.json';source.write_text(source.read_text()+'\n')
            with self.assertRaisesRegex(ValueError,'completion manifest'):read_affine_peaks(out)
