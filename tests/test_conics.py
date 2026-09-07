# SPDX-License-Identifier: Apache-2.0
import math
import unittest
import numpy as np
from superfish_ng.conics import EllipseArc


class EllipseArcTests(unittest.TestCase):
    def test_ellipse_equation_tangent_and_curvature(self):
        arc = EllipseArc((0,0),(3,2),0,math.pi)
        result = arc.evaluate(np.linspace(0,1,101))
        z,r = result['points_zr_m'].T
        np.testing.assert_allclose((z/3)**2+(r/2)**2,1,atol=1e-14)
        tangent = result['tangent_zr']
        np.testing.assert_allclose(tangent[:,0]*z/9+tangent[:,1]*r/4,0,atol=1e-14)
        np.testing.assert_allclose(np.linalg.norm(tangent,axis=1),1,atol=1e-14)
        np.testing.assert_allclose(result['curvature_per_m'][[0,50]],[3/4,2/9],atol=1e-14)
        self.assertAlmostEqual(arc.minimum_radius_m,4/3)
        circle = EllipseArc((2,3),(5,5),.2,-4)
        np.testing.assert_allclose(circle.evaluate([0,.3,1])['curvature_per_m'],.2)
        self.assertAlmostEqual(circle.minimum_radius_m,5)

    def test_rotation_translation_reverse_and_area(self):
        arc = EllipseArc((1,2),(3,2),.2,2.1,.7)
        back = EllipseArc((1,2),(3,2),2.3,-2.1,.7)
        t = np.linspace(0,1,71)
        np.testing.assert_allclose(arc.evaluate(t)['points_zr_m'],back.evaluate(1-t)['points_zr_m'],atol=2e-14)
        np.testing.assert_allclose(arc.evaluate(t)['tangent_zr'],-back.evaluate(1-t)['tangent_zr'],atol=2e-14)
        self.assertAlmostEqual(arc.signed_line_area_m2,-back.signed_line_area_m2)
        quarter = EllipseArc((0,0),(3,2),0,math.pi/2,.7)
        self.assertAlmostEqual(quarter.signed_line_area_m2,6*math.pi/4)
        # Independent polygon shoelace approaches the sector area from below.
        p = quarter.linearize(1e-5)
        area = np.sum(p[:-1,0]*p[1:,1]-p[1:,0]*p[:-1,1])/2
        self.assertLess(area,6*math.pi/4)
        self.assertLess(6*math.pi/4-area,5e-5)

    def test_chord_bound_and_scaling(self):
        for scale in (1e-6,1.,1e6):
            arc = EllipseArc((scale,2*scale),(3*scale,.2*scale),-.3,4.5,.4)
            tol = .001*scale
            p = arc.linearize(tol)
            n = len(p)-1
            for fraction in (.1,.3,.5,.7,.9):
                exact = arc.evaluate((np.arange(n)+fraction)/n)['points_zr_m']
                chord = p[:-1]*(1-fraction)+p[1:]*fraction
                self.assertLessEqual(np.linalg.norm(exact-chord,axis=1).max(),tol*(1+1e-10))
            self.assertAlmostEqual(arc.minimum_radius_m/scale,.04/3)

    def test_invalid_values_and_resource_limit(self):
        for axes in ((0,1),(-1,1),(True,1),(float('inf'),1)):
            with self.assertRaises(ValueError):EllipseArc((0,0),axes,0,1)
        for sweep in (0,2*math.pi,float('nan'),True):
            with self.assertRaises(ValueError):EllipseArc((0,0),(1,1),0,sweep)
        arc = EllipseArc((0,0),(1,1),0,1)
        for value in (-.1,1.1,float('nan'),True,'x'):
            with self.assertRaises(ValueError):arc.evaluate(value)
        with self.assertRaisesRegex(ValueError,'max_segments'):arc.linearize(1e-10,max_segments=10)
