# SPDX-License-Identifier: Apache-2.0
from decimal import Decimal,localcontext
import math
import unittest
import warnings
import numpy as np
from superfish_ng.conics import EllipseArc,HyperbolaArc

class ConicScaleTests(unittest.TestCase):
    def test_ellipse_radius_at_extreme_uniform_scales(self):
        with warnings.catch_warnings():
            warnings.simplefilter('error',RuntimeWarning)
            for scale in (1e-200,1.,1e200):
                curve=EllipseArc((0,0),(2*scale,scale),0.,1.)
                self.assertAlmostEqual(curve.minimum_radius_m/scale,.5,places=14)
                self.assertAlmostEqual(float(curve.evaluate(0.)['curvature_per_m'])*scale,2.,places=14)

    def test_hyperbola_representable_result_after_extreme_intermediates(self):
        a=1e-300;start=460.;curve=HyperbolaArc((0,0),(a,a),start,start+1)
        with localcontext() as ctx:
            ctx.prec=80
            u=Decimal(start);x=Decimal(a);speed=x*((2*u).exp()/2+(-2*u).exp()/2).sqrt()
            radius=speed**3/x**2
            expected_radius=float(radius);expected_curvature=float(1/radius)
        with warnings.catch_warnings():
            warnings.simplefilter('error',RuntimeWarning)
            r=curve.minimum_radius_m;result=curve.evaluate(np.array([0.,.5,1.]))
        self.assertAlmostEqual(r/expected_radius,1.,places=13)
        self.assertAlmostEqual(result['curvature_per_m'][0]/expected_curvature,1.,places=13)
        self.assertTrue(np.all(np.isfinite(result['curvature_per_m'])))
        self.assertTrue(np.all(result['curvature_per_m']>0))
        np.testing.assert_allclose(np.linalg.norm(result['tangent_zr'],axis=1),1.,atol=1e-14)

    def test_nonspherical_extreme_aspect_vertex_and_scale(self):
        # At u/theta=0 the exact radius is b^2/a, independent of a fitted formula.
        for cls in (EllipseArc,HyperbolaArc):
            curve=cls((0,0),(1e200,1.),0.,.5)
            self.assertAlmostEqual(curve.minimum_radius_m/1e-200,1.,places=14)
            self.assertAlmostEqual(float(curve.evaluate(0.)['curvature_per_m'])/1e200,1.,places=14)

    def test_unrepresentable_radius_and_curvature_are_actionable(self):
        for cls in (EllipseArc,HyperbolaArc):
            curve=cls((0,0),(1e-200,1e200),0.,.1)
            with self.assertRaisesRegex(ValueError,'floating-point range'):curve.minimum_radius_m
            with self.assertRaisesRegex(ValueError,'floating-point range'):curve.evaluate(0.)
        smallest=float(np.nextafter(0.,1.))
        self.assertEqual(EllipseArc((0,0),(smallest,smallest),0.,1.).minimum_radius_m,smallest)

if __name__=='__main__':unittest.main()
