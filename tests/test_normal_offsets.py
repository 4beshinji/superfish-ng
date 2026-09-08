# SPDX-License-Identifier: Apache-2.0
from fractions import Fraction as F
import math
import unittest
import numpy as np
from superfish_ng.conics import EllipseArc,HyperbolaArc
from superfish_ng.normal_offsets import normal_offset_bounds,partition_normal_offset


class NormalOffsetTests(unittest.TestCase):
    def test_circle_radius_and_collapsed_center(self):
        circle=EllipseArc((2.,3.),(1.,1.),0.,math.pi)
        for d,factor in ((.25,.75),(2.,-1.)):
            report=normal_offset_bounds(circle,0.,.1,distance_m=d)
            self.assertEqual(report['speed_factor_interval'],(F(factor),F(factor)))
            self.assertEqual(report['regularity'],'FORWARD' if factor>0 else 'REVERSED')
        report=normal_offset_bounds(circle,0.,1.,distance_m=1.)
        self.assertEqual(report['regularity'],'COLLAPSED')
        self.assertEqual(report['center_box_zr_m'],((F(2),F(2)),(F(3),F(3))))
        self.assertEqual(report['derivative_box_zr_m'],((F(0),F(0)),)*2)
        self.assertEqual(partition_normal_offset(circle,distance_m=1.)['status'],'SINGULAR')

    def test_ellipse_and_hyperbola_vertex_signed_curvature(self):
        ellipse=EllipseArc((0,0),(2,1),0.,1.)
        report=normal_offset_bounds(ellipse,0.,0.,distance_m=.5)
        self.assertEqual(report['signed_curvature_interval_per_m'],(F(2),F(2)))
        self.assertEqual(report['speed_factor_interval'],(F(0),F(0)))
        self.assertEqual(report['regularity'],'UNVERIFIED')
        for branch in (-1,1):
            arc=HyperbolaArc((0,0),(2,1),0.,1.,branch)
            report=normal_offset_bounds(arc,0.,0.,distance_m=-branch*.25)
            self.assertEqual(report['signed_curvature_interval_per_m'],(F(-branch*2),)*2)
            self.assertEqual(report['speed_factor_interval'],(F(.5),)*2)
            self.assertEqual(report['center_box_zr_m'],((F(branch*2.25),)*2,(F(0),)*2))

    def test_bounds_contain_independent_points_and_derivatives(self):
        curves=[EllipseArc((.1,.3),(2,1),-.7,4.8,.37),
                HyperbolaArc((.1,.3),(2,1),-1.2,1.3,-1,.37)]
        for arc in curves:
            for d in (-.2,.2):
                report=normal_offset_bounds(arc,.2,.4,distance_m=d)
                for t in np.linspace(.21,.39,7):
                    def point(f):
                        e=arc.evaluate(float(f));u=e['tangent_zr']
                        return e['points_zr_m']+d*np.array([-u[1],u[0]])
                    p=point(t);derivative=(point(t+1e-6)-point(t-1e-6))/2e-6
                    for values,key in ((p,'center_box_zr_m'),(derivative,'derivative_box_zr_m')):
                        for x,(lo,hi) in zip(values,report[key]):self.assertTrue(float(lo)<=x<=float(hi))

    def test_cusp_intervals_are_retained_and_cover_domain(self):
        arc=EllipseArc((0,0),(2,1),0.,math.pi)
        report=partition_normal_offset(arc,distance_m=1.,fraction_width=F(1,2**10),max_boxes=1000)
        self.assertEqual(report['status'],'UNVERIFIED')
        self.assertTrue(report['unresolved'])
        root=math.asin(math.sqrt((2**(2/3)-1)/3))/math.pi
        for f in (root,1-root):
            self.assertTrue(any(float(r['interval'][0])<=f<=float(r['interval'][1]) for r in report['unresolved']))
        rows=sorted(report['regular']+report['singular']+report['unresolved'],key=lambda r:r['interval'])
        self.assertEqual(rows[0]['interval'][0],0);self.assertEqual(rows[-1]['interval'][1],1)
        for left,right in zip(rows,rows[1:]):self.assertEqual(left['interval'][1],right['interval'][0])
        limited=partition_normal_offset(arc,distance_m=1.,max_boxes=1)
        self.assertEqual(limited['status'],'UNVERIFIED');self.assertEqual(limited['boxes_checked'],1)

    def test_reversal_scale_and_strict_failure(self):
        arc=EllipseArc((0,0),(2,1),0.,1.)
        reversed_arc=EllipseArc((0,0),(2,1),1.,-1.)
        a=normal_offset_bounds(arc,.2,.4,distance_m=.2)
        b=normal_offset_bounds(reversed_arc,.6,.8,distance_m=-.2)
        for x,y in zip(a['center_box_zr_m'],b['center_box_zr_m']):
            np.testing.assert_allclose(list(map(float,x)),list(map(float,y)),atol=1e-14)
        large=EllipseArc((0,0),(4,2),0.,1.)
        scaled=normal_offset_bounds(large,.2,.4,distance_m=.4)
        for key in ('center_box_zr_m','derivative_box_zr_m'):
            self.assertEqual(scaled[key],tuple(tuple(2*x for x in row) for row in a[key]))
        self.assertEqual(scaled['speed_factor_interval'],a['speed_factor_interval'])
        with self.assertRaises(ValueError):normal_offset_bounds(arc,distance_m=True)
        with self.assertRaises(ValueError):normal_offset_bounds(arc,-.1,1.,distance_m=.2)
        with self.assertRaises(ValueError):partition_normal_offset(arc,distance_m=.2,max_boxes=True)
        report=partition_normal_offset(arc,distance_m=.2,max_series_terms=1)
        self.assertEqual(report['status'],'UNVERIFIED')

    def test_rotated_binary_model_against_decimal_vertex(self):
        from decimal import Decimal,localcontext
        from superfish_ng.conics import rotation_cos_sin
        curve=EllipseArc((0,0),(2,1),0.,1.,.37)
        report=normal_offset_bounds(curve,0.,0.,distance_m=.2)
        with localcontext() as ctx:
            ctx.prec=100
            c,s=[Decimal.from_float(x) for x in rotation_cos_sin(.37)]
            length=(c*c+s*s).sqrt();d=Decimal.from_float(.2)
            expected=[x*(2-d/length) for x in (c,s)]
            curvature=2/length
            for x,(lo,hi) in zip(expected,report['center_box_zr_m']):self.assertLessEqual(lo,F(x));self.assertLessEqual(F(x),hi)
            lo,hi=report['signed_curvature_interval_per_m']
            self.assertLessEqual(lo,F(curvature));self.assertLessEqual(F(curvature),hi)


if __name__=='__main__':unittest.main()
