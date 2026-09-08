# SPDX-License-Identifier: Apache-2.0
"""Strong TM operator and natural flux checked against global polynomials."""
from dataclasses import replace
import unittest
import numpy as np
from superfish_ng import Case, solve
from superfish_ng.mesh import make_mesh
from superfish_ng.high_order import quadratic_space
from superfish_ng.residual_indicator import residual_indicator, mark_bulk, _components


class ResidualIndicatorTests(unittest.TestCase):
    def test_piecewise_linear_jump_counts_each_interface_once(self):
        radius,length=.1,.2
        case=Case(((0.,radius),(length,radius)),nr=4,nz=5,modes=1)
        mesh=make_mesh(case);u=np.maximum(mesh.points[:,0]-radius/2,0.)
        volume,jump,_=_components(mesh,1,u,0.)
        h2=(radius/4)**2+(length/5)**2
        self.assertAlmostEqual(float(sum(volume))/(9*h2*length*(radius**2-(radius/2)**2)/2),1.,places=12)
        self.assertAlmostEqual(float(sum(jump))/((length/5)*length*(radius/2)**3),1.,places=12)

    def test_global_polynomial_volume_and_continuous_flux(self):
        radius,length=.1,.2
        for order in (1,2):
            case=Case(((0.,radius),(length,radius)),nr=4,nz=5,modes=1,element_order=order)
            mesh=make_mesh(case)
            points=quadratic_space(mesh).dof_points if order==2 else mesh.points
            r,z=points.T
            u=r if order==1 else r*r+z*z
            volume,jump,boundary=_components(mesh,order,u,0.)
            h2=(radius/4)**2+(length/5)**2
            expected=9*h2*length*radius**2/2 if order==1 else 100*h2*length*radius**4/4
            self.assertAlmostEqual(float(sum(volume))/expected,1.,places=12)
            self.assertLess(float(sum(jump)),1e-25)
            # On r=R: r*u_r+2*u = 3R (P1), 4R²+2z² (P2).
            # On z=L: P1 has zero flux; P2 has 2*r*L.
            side=9*radius**3*length*(length/5) if order==1 else (length/5)*radius*(16*radius**4*length+16*radius**2*length**3/3+4*length**5/5)
            end=0 if order==1 else (radius/4)*length**2*radius**4
            self.assertAlmostEqual(float(sum(boundary))/(side+end),1.,places=12)

    def test_normalization_scaling_and_native_nonzero_residual(self):
        for order in (1,2):
            case=Case(((0.,.1),(.2,.1)),nr=4,nz=5,modes=1,element_order=order)
            solution=solve(case);a=residual_indicator(case,solution)
            self.assertGreater(a['relative_indicator'],1e-6)
            self.assertLess(float(solution.residuals[0]),1e-9)
            b=residual_indicator(case,replace(solution,u=-7*solution.u))
            np.testing.assert_allclose(a['cell_relative_squared'],b['cell_relative_squared'],rtol=2e-11,atol=1e-16)
            for factor in (1e-200,1e200):
                b=residual_indicator(case,replace(solution,u=factor*solution.u))
                np.testing.assert_allclose(a['cell_relative_squared'],b['cell_relative_squared'],rtol=2e-11,atol=1e-16)
            scaled=replace(case,profile=((0.,.2),(.4,.2)),normalization_j=4.)
            c=residual_indicator(scaled,solve(scaled))
            np.testing.assert_allclose(a['cell_relative_squared'],c['cell_relative_squared'],rtol=2e-9,atol=1e-15)
            self.assertIsNone(a['physical_error_bound'])

    def test_axis_and_symmetry_conditions(self):
        for order in (1,2):
            for tag in ('electric_symmetry','magnetic_symmetry'):
                case=Case(((0.,.1),(.2,.1)),nr=4,nz=5,modes=1,element_order=order,z_min=tag)
                solution=solve(case);report=residual_indicator(case,solution)
                self.assertTrue(np.isfinite(report['relative_indicator']))
                if tag=='magnetic_symmetry':
                    u=solution.u.copy();u[0,0]=1.
                    with self.assertRaisesRegex(ValueError,'magnetic'):residual_indicator(case,replace(solution,u=u))

    def test_bulk_minimal_prefix_ties_extremes_and_strict_input(self):
        self.assertEqual(mark_bulk([1.,4.,4.,0.],.5),[1,2])
        self.assertEqual(mark_bulk([1.,4.,4.,0.],1.),[1,2,0])
        self.assertEqual(mark_bulk([0.,0.],.5),[])
        self.assertEqual(mark_bulk([1e308,1e308],.5),[0])
        self.assertEqual(mark_bulk([1e308,1e-308],1.),[0,1])
        for values,fraction in (([True],.5),([-1],.5),([float('nan')],.5),([1],True),([1],0),([1],1.1),([], .5),(np.array(1.),.5),(np.array([[1.]]),.5)):
            with self.assertRaises(ValueError):mark_bulk(values,fraction)
        case=Case(((0.,.1),(.2,.1)),nr=3,nz=4,modes=1);solution=solve(case)
        for mode in (True,-1,1,.0):
            with self.assertRaises(ValueError):residual_indicator(case,solution,mode=mode)
        with self.assertRaises(ValueError):residual_indicator(replace(case,element_order=2),solution)
        with self.assertRaises(ValueError):residual_indicator(case,replace(solution,u=solution.u*float('nan')))
