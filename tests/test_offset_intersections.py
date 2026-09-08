# SPDX-License-Identifier: Apache-2.0
from fractions import Fraction as F
from decimal import Decimal,localcontext
import math
import unittest
from superfish_ng.conics import EllipseArc,HyperbolaArc
from superfish_ng.offset_intersections import intersect_normal_offsets


class OffsetIntersectionTests(unittest.TestCase):
    def controls(self,**extra):
        return dict(first_distance_m=1.,second_distance_m=1.,fraction_width=F(1,2**24),max_boxes=2000,**extra)

    def circles(self,separation=1.):
        return (EllipseArc((0,0),(2,2),-2.7,5.4),EllipseArc((separation,0),(2,2),-2.7,5.4))

    def test_two_circle_intersections_are_existent_unique_and_complete(self):
        report=intersect_normal_offsets(*self.circles(),**self.controls())
        self.assertEqual(report['status'],'PASS');self.assertEqual(len(report['roots']),2)
        with localcontext() as ctx:
            ctx.prec=100;h=F(Decimal(3).sqrt()/2)
        for sign in (-1,1):
            point=(F(1,2),sign*h)
            matches=[r for r in report['roots'] if all(lo<=x<=hi for x,(lo,hi) in zip(point,r['center_box_zr_m']))]
            self.assertEqual(len(matches),1)
            root=matches[0]
            self.assertTrue(all(hi-lo<=F(1,2**24) for lo,hi in root['parameter_box']))
            certificate=root['certificate']
            self.assertLess(certificate['contraction_bound'],1)
            for (lo,hi),(a,b) in zip(certificate['krawczyk_box'],certificate['domain_box']):self.assertTrue(a<lo<=hi<b)

    def test_separation_and_arc_restriction(self):
        report=intersect_normal_offsets(*self.circles(4.),**self.controls())
        self.assertEqual(report['status'],'PASS');self.assertEqual(report['roots'],[])
        a,b=self.circles()
        report=intersect_normal_offsets(a,b,first_interval=(.5,1.),second_interval=(.5,1.),**self.controls())
        self.assertEqual(report['status'],'PASS');self.assertEqual(len(report['roots']),1)

    def test_tangent_coincident_and_collapsed_are_not_empty_success(self):
        for separation in (0.,2.):
            controls=self.controls();controls['max_boxes']=40
            a,b=self.circles(separation)
            if separation==2.:b=EllipseArc((2.,0),(2,2),0.,4.)
            report=intersect_normal_offsets(a,b,**controls)
            self.assertEqual(report['status'],'UNVERIFIED');self.assertTrue(report['unresolved'])
        controls=self.controls();controls.update(first_distance_m=2.,second_distance_m=2.,max_boxes=4)
        report=intersect_normal_offsets(*self.circles(0.),**controls)
        self.assertEqual(report['status'],'UNVERIFIED');self.assertTrue(report['unresolved'])

    def test_budget_and_strict_controls(self):
        controls=self.controls();controls['max_boxes']=1
        result=intersect_normal_offsets(*self.circles(),**controls)
        self.assertEqual(result['status'],'UNVERIFIED');self.assertEqual(result['boxes_checked'],1)
        self.assertTrue(result['unresolved'])
        for key,value in (('max_boxes',True),('fraction_width',0),('first_distance_m',True)):
            controls=self.controls();controls[key]=value
            with self.assertRaises(ValueError):intersect_normal_offsets(*self.circles(),**controls)

    def test_four_ellipse_intersections_against_implicit_equations(self):
        a=EllipseArc((0,0),(2,1),-2.9,5.8)
        b=EllipseArc((0,0),(1,2),-2.9,5.8)
        report=intersect_normal_offsets(a,b,first_distance_m=0.,second_distance_m=0.,fraction_width=F(1,2**24),max_boxes=3000)
        self.assertEqual(report['status'],'PASS');self.assertEqual(len(report['roots']),4)
        with localcontext() as ctx:
            ctx.prec=100;value=F(2/Decimal(5).sqrt())
        for sx in (-1,1):
            for sy in (-1,1):
                point=(sx*value,sy*value)
                self.assertEqual(sum(all(lo<=x<=hi for x,(lo,hi) in zip(point,r['center_box_zr_m'])) for r in report['roots']),1)

    def test_nonzero_ellipse_hyperbola_offsets_have_known_vertex_crossing(self):
        ellipse=EllipseArc((0,0),(2,1),-.2,.5)
        hyperbola=HyperbolaArc((1.75,-2.25),(2,1),-.2,.3,1,math.pi/2)
        report=intersect_normal_offsets(ellipse,hyperbola,first_distance_m=.25,second_distance_m=-.25)
        self.assertEqual(report['status'],'PASS');self.assertEqual(len(report['roots']),1)
        for x,(lo,hi) in zip((F(7,4),F(0)),report['roots'][0]['center_box_zr_m']):self.assertTrue(lo<=x<=hi)
        # The same root on the requested domain boundary cannot be proved by
        # strict interior inclusion; retain it rather than drop it.
        endpoint=EllipseArc((0,0),(2,1),0.,.5)
        result=intersect_normal_offsets(endpoint,hyperbola,first_distance_m=.25,second_distance_m=-.25,max_boxes=40)
        self.assertEqual(result['status'],'UNVERIFIED');self.assertTrue(result['unresolved'])

    def test_scale_swap_and_arithmetic_precision_budget(self):
        a,b=self.circles()
        original=intersect_normal_offsets(a,b,**self.controls())
        swapped=intersect_normal_offsets(b,a,**self.controls())
        large=intersect_normal_offsets(EllipseArc((0,0),(4,4),-2.7,5.4),EllipseArc((2,0),(4,4),-2.7,5.4),first_distance_m=2.,second_distance_m=2.)
        self.assertEqual(swapped['status'],'PASS');self.assertEqual(large['status'],'PASS')
        self.assertEqual(len(swapped['roots']),2);self.assertEqual(len(large['roots']),2)
        for row in original['roots']:
            self.assertEqual(sum(all(max(x[0],y[0])<=min(x[1],y[1]) for x,y in zip(row['parameter_box'],r['parameter_box'][::-1])) for r in swapped['roots']),1)
            point=row['center_box_zr_m']
            self.assertEqual(sum(all(max(2*x[0],y[0])<=min(2*x[1],y[1]) for x,y in zip(point,r['center_box_zr_m'])) for r in large['roots']),1)
        limited=intersect_normal_offsets(a,b,precision_bits=8,max_boxes=80,**{k:v for k,v in self.controls().items() if k!='max_boxes'})
        self.assertEqual(limited['status'],'UNVERIFIED');self.assertTrue(limited['unresolved'])
        with self.assertRaises(ValueError):intersect_normal_offsets(a,b,precision_bits=True,**self.controls())
        limited=intersect_normal_offsets(a,b,max_series_terms=1,**self.controls())
        self.assertEqual(limited['status'],'UNVERIFIED')


if __name__=='__main__':unittest.main()
