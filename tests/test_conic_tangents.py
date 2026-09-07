# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import math
import unittest
import numpy as np
from superfish_ng.conics import EllipseArc, HyperbolaArc
from superfish_ng.conic_tangents import supporting_conic_tangents


class ConicTangentTests(unittest.TestCase):
    def circle(self, centre, radius=1):
        return EllipseArc(centre,(radius,radius),0.,math.pi)

    def test_separated_equal_circles_have_four_tangents(self):
        result = supporting_conic_tangents(self.circle((0,0)),self.circle((4,0)))
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(len(result['candidates']),4)
        lengths = sorted(c['contact_distance_m'] for c in result['candidates'])
        np.testing.assert_allclose(lengths,[math.sqrt(12),math.sqrt(12),4,4],rtol=1e-11)
        for candidate in result['candidates']:
            n=np.array(candidate['normal_zr']);p,q=map(np.array,candidate['contacts_zr_m'])
            self.assertAlmostEqual(np.linalg.norm(p),1,places=10)
            self.assertAlmostEqual(np.linalg.norm(q-[4,0]),1,places=10)
            self.assertLess(abs(n@(q-p)),1e-10)

    def test_touching_intersecting_nested_and_coincident_circles(self):
        for distance,count in ((2,3),(1,2)):
            r=supporting_conic_tangents(self.circle((0,0)),self.circle((distance,0)))
            self.assertEqual(r['status'],'PASS');self.assertEqual(len(r['candidates']),count)
            self.assertEqual(sum(c['coincident_contacts_at_output_precision'] for c in r['candidates']),int(distance==2))
        nested=supporting_conic_tangents(self.circle((0,0),3),self.circle((.1,0),1))
        self.assertEqual(nested['status'],'PASS');self.assertFalse(nested['candidates'])
        same=supporting_conic_tangents(self.circle((0,0)),self.circle((0,0)))
        self.assertEqual(same['status'],'UNVERIFIED');self.assertTrue(same['unresolved'])

    def test_rotated_translated_scaled_ellipses(self):
        angle=.37
        rotation=np.array([[math.cos(angle),-math.sin(angle)],[math.sin(angle),math.cos(angle)]])
        for scale in (1e-5,1.,1e5):
            centre=np.array([2.,3.])*scale
            first=EllipseArc(tuple(map(float,centre)),(2*scale,scale),0,math.pi,angle)
            second=replace(first,center_zr_m=tuple(map(float,centre+rotation@[8*scale,0])))
            result=supporting_conic_tangents(first,second)
            self.assertEqual(result['status'],'PASS');self.assertEqual(len(result['candidates']),4)
            for item in result['candidates']:
                for point,curve in zip(item['contacts_zr_m'],(first,second)):
                    local=rotation.T@(np.array(point)-curve.center_zr_m)/curve.semiaxes_m
                    self.assertAlmostEqual(float(local@local),1.,places=9)

    def test_hyperbola_whole_conics_not_silently_arc_filtered(self):
        first=HyperbolaArc((0,0),(1,1),-.2,.2)
        second=replace(first,center_zr_m=(0,4))
        result=supporting_conic_tangents(first,second)
        self.assertEqual(result['status'],'PASS')
        self.assertTrue(result['candidates'])
        self.assertEqual(result['arc_filter_status'],'NOT_APPLIED')
        for item in result['candidates']:
            for p,c in zip(item['contacts_zr_m'],(first,second)):
                z,r=np.array(p)-c.center_zr_m
                self.assertAlmostEqual(z*z-r*r,1,places=9)

    def test_budget_and_invalid_inputs(self):
        a,b=self.circle((0,0)),self.circle((4,0))
        self.assertEqual(supporting_conic_tangents(a,b,max_boxes=1)['status'],'UNVERIFIED')
        for kwargs in ({'normal_width':0},{'max_boxes':True},{'residual_tolerance':True}):
            with self.assertRaises(ValueError): supporting_conic_tangents(a,b,**kwargs)
        with self.assertRaises(ValueError): supporting_conic_tangents(None,b)

    def test_common_asymptote_is_not_a_finite_contact(self):
        first=HyperbolaArc((0,0),(1,1),-.2,.2)
        second=replace(first,center_zr_m=(2.,2.))
        result=supporting_conic_tangents(first,second)
        self.assertTrue(any('infinity' in c['reason'] for c in result['excluded']))
        for c in result['candidates']:
            self.assertTrue(np.isfinite(c['contacts_zr_m']).all())

    def test_unrepresentable_translated_contacts_remain_unverified(self):
        result=supporting_conic_tangents(self.circle((1e20,1e20)),self.circle((1e20+1e10,1e20)))
        self.assertEqual(result['status'],'UNVERIFIED')
        self.assertTrue(result['unresolved'])

    def test_unequal_conics_and_concentric_direction_chart_boundaries(self):
        first=EllipseArc((0,0),(2,1),0,math.pi)
        for second in (EllipseArc((0,0),(1,2),0,math.pi), EllipseArc((5,2),(1,2),0,math.pi,.3)):
            result=supporting_conic_tangents(first,second)
            self.assertEqual(result['status'],'PASS')
            self.assertEqual(len(result['candidates']),4)
            for item in result['candidates']:
                n=np.array(item['normal_zr'])
                for point,curve in zip(item['contacts_zr_m'],(first,second)):
                    c,s=math.cos(curve.rotation_rad),math.sin(curve.rotation_rad)
                    rotation=np.array([[c,-s],[s,c]])
                    local=rotation.T@(np.array(point)-curve.center_zr_m)
                    gradient=rotation@(local/np.array(curve.semiaxes_m)**2)
                    gradient/=np.linalg.norm(gradient)
                    self.assertLess(abs(gradient[0]*n[1]-gradient[1]*n[0]),1e-10)
                    self.assertAlmostEqual(float(n@(np.array(point)-item['origin_zr_m'])),item['offset_from_origin_m'],places=10)
