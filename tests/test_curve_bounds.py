# SPDX-License-Identifier: Apache-2.0
import math
import unittest
import numpy as np
from superfish_ng.conics import EllipseArc,HyperbolaArc,LineSegment
from superfish_ng.curve_bounds import curve_bounds,certify_curve_separation


class CurveBoundsTests(unittest.TestCase):
    def test_internal_extrema_and_axis_excursion(self):
        curve = EllipseArc((0,0),(3,2),-.2,math.pi+.4)
        low,high = curve_bounds(curve)
        self.assertLessEqual(low[0],-3)
        self.assertGreaterEqual(high[0],3)
        self.assertGreaterEqual(high[1],2)
        # Both endpoints above the axis do not prove the arc stays above it.
        crossing = EllipseArc((2,.5),(1,1),0,-math.pi)
        self.assertTrue(np.all(crossing.evaluate([0,1])['points_zr_m'][:,1]>0))
        self.assertLess(curve_bounds(crossing)[0][1],0)

    def test_rotated_reversed_intervals_contain_dense_points(self):
        for curve in (EllipseArc((1,2),(3,.2),2,-4,.7),
                      HyperbolaArc((2,3),(3,2),1,-1,-1,.9),
                      LineSegment((1,2),(-3,4))):
            for a,b in ((0.,1.),(.17,.83),(.49,.51)):
                low,high = curve_bounds(curve,a,b)
                p = curve.evaluate(np.linspace(a,b,501))['points_zr_m']
                self.assertTrue(np.all(p>=low))
                self.assertTrue(np.all(p<=high))

    def test_separation_crossing_contact_and_unresolved_budget(self):
        first = LineSegment((0,0),(1,0))
        second = LineSegment((0,.01),(1,.01))
        report = certify_curve_separation(first,second,.009)
        self.assertGreater(report['lower_bound_m'],.009)
        self.assertLessEqual(report['lower_bound_m'],.01)
        with self.assertRaisesRegex(ValueError,'FAIL'):
            certify_curve_separation(first,LineSegment((.5,-1),(.5,1)))
        with self.assertRaisesRegex(ValueError,'FAIL'):
            certify_curve_separation(first,LineSegment((1,0),(2,1)))
        a = EllipseArc((0,0),(1,1),0,math.pi)
        b = EllipseArc((0,0),(2,2),0,math.pi)
        with self.assertRaisesRegex(ValueError,'UNVERIFIED'):
            certify_curve_separation(a,b,.1,max_boxes=1)
        self.assertTrue(certify_curve_separation(a,b,.1)['separated'])
        for args in ((-1,1),(0,0),(False,1)):
            with self.assertRaises(ValueError):curve_bounds(first,*args)
