# SPDX-License-Identifier: Apache-2.0
import math
import unittest
import numpy as np
from superfish_ng.conics import EllipseArc, HyperbolaArc
from superfish_ng.conics import LineSegment, check_curve_join


class CurveJoinTests(unittest.TestCase):
    def test_line_ellipse_and_hyperbola_oriented_tangency(self):
        ellipse = EllipseArc((0,0),(3,2),0,math.pi/2)
        incoming = LineSegment((3,-1),(3,0))
        outgoing = LineSegment((0,2),(-1,2))
        for first,second in ((incoming,ellipse),(ellipse,outgoing)):
            result = check_curve_join(first,second,position_tolerance_m=1e-14)
            self.assertTrue(result['tangent_continuous'])
            self.assertLess(result['endpoint_gap_m'],1e-14)
        hyperbola = HyperbolaArc((0,-1),(3,2),0,1,rotation_rad=math.pi/2)
        self.assertTrue(check_curve_join(ellipse,hyperbola,position_tolerance_m=1e-14)['tangent_continuous'])
        # Tangent continuity does not require matching curvature with a line.
        self.assertTrue(math.isinf(incoming.minimum_radius_m))
        self.assertEqual(incoming.evaluate(.5)['curvature_per_m'],0)

    def test_gap_reversal_and_corner_are_distinct_without_repair(self):
        first = LineSegment((0,0),(1,0))
        reverse = LineSegment((1,0),(0,0))
        with self.assertRaisesRegex(ValueError,'tangent angle'):
            check_curve_join(first,reverse,position_tolerance_m=0)
        gap = LineSegment((1.001,0),(2,0))
        before = gap.start_zr_m
        with self.assertRaisesRegex(ValueError,'endpoint gap'):
            check_curve_join(first,gap,position_tolerance_m=1e-4)
        check_curve_join(first,gap,position_tolerance_m=.002)
        self.assertEqual(gap.start_zr_m,before)
        corner = LineSegment((1,0),(1,1))
        report = check_curve_join(first,corner,position_tolerance_m=0,require_tangent=False)
        self.assertFalse(report['tangent_continuous'])
        self.assertAlmostEqual(report['tangent_angle_rad'],math.pi/2)

    def test_line_area_and_strict_join_controls(self):
        points = ((0,0),(3,0),(3,2),(0,2))
        edges = [LineSegment(a,b) for a,b in zip(points,points[1:]+points[:1])]
        self.assertEqual(sum(e.signed_line_area_m2 for e in edges),6)
        for bad in ((0,0),(float('nan'),1),(True,1)):
            with self.assertRaises(ValueError):LineSegment((0,0),bad)
        for kwargs in ({'position_tolerance_m':True},{'position_tolerance_m':-1},
                       {'position_tolerance_m':0,'angle_tolerance_rad':math.pi},
                       {'position_tolerance_m':0,'require_tangent':1}):
            with self.assertRaises(ValueError):check_curve_join(edges[0],edges[1],**kwargs)


class HyperbolaArcTests(unittest.TestCase):
    def test_branches_implicit_equation_tangents_and_vertex_radius(self):
        for branch in (-1,1):
            arc = HyperbolaArc((0,0),(3,2),-1,1,branch)
            result = arc.evaluate(np.linspace(0,1,101))
            z,r = result['points_zr_m'].T
            np.testing.assert_allclose((z/3)**2-(r/2)**2,1,atol=1e-14)
            tangent = result['tangent_zr']
            np.testing.assert_allclose(tangent[:,0]*z/9-tangent[:,1]*r/4,0,atol=1e-14)
            np.testing.assert_allclose(np.linalg.norm(tangent,axis=1),1,atol=1e-14)
            self.assertAlmostEqual(arc.minimum_radius_m,4/3)
            self.assertAlmostEqual(result['curvature_per_m'][50],3/4)
            self.assertAlmostEqual(arc.signed_line_area_m2,branch*6.)

    def test_rotation_reversal_area_and_chord_bound(self):
        arc = HyperbolaArc((1,2),(3,2),-.7,1.2,-1,.4)
        back = HyperbolaArc((1,2),(3,2),1.2,-.7,-1,.4)
        t = np.linspace(0,1,101)
        np.testing.assert_allclose(arc.evaluate(t)['points_zr_m'],back.evaluate(1-t)['points_zr_m'],atol=1e-14)
        np.testing.assert_allclose(arc.evaluate(t)['tangent_zr'],-back.evaluate(1-t)['tangent_zr'],atol=1e-14)
        self.assertAlmostEqual(arc.signed_line_area_m2,-back.signed_line_area_m2)
        p = arc.linearize(1e-4)
        n = len(p)-1
        for fraction in (.2,.5,.8):
            exact = arc.evaluate((np.arange(n)+fraction)/n)['points_zr_m']
            chord = (1-fraction)*p[:-1]+fraction*p[1:]
            self.assertLessEqual(np.linalg.norm(exact-chord,axis=1).max(),1e-4)
        polygon_integral = np.sum(p[:-1,0]*p[1:,1]-p[1:,0]*p[:-1,1])/2
        self.assertLess(abs(polygon_integral-arc.signed_line_area_m2),.001)

    def test_scaling_and_explicit_rejection(self):
        base = HyperbolaArc((0,0),(3,2),.2,1.)
        for scale in (1e-6,1e6):
            arc = HyperbolaArc((0,0),(3*scale,2*scale),.2,1.)
            self.assertAlmostEqual(arc.minimum_radius_m/(scale*base.minimum_radius_m),1)
            self.assertAlmostEqual(arc.signed_line_area_m2/(scale**2*base.signed_line_area_m2),1)
        for branch in (0,True,1.):
            with self.assertRaises(ValueError):HyperbolaArc((0,0),(1,1),0,1,branch)
        for end in (0,float('inf'),1000):
            with self.assertRaises(ValueError):HyperbolaArc((0,0),(1,1),0,end)
        with self.assertRaisesRegex(ValueError,'max_segments'):base.linearize(1e-12,max_segments=10)
        with self.assertRaises(ValueError):base.evaluate(True)
        with self.assertRaisesRegex(ValueError,'floating-point'):
            HyperbolaArc((0,0),(1,1),399,400).evaluate(1.)


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
