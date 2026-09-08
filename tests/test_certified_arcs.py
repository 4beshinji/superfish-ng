# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from decimal import Decimal, localcontext
from fractions import Fraction as F
import math
import unittest
from superfish_ng.conics import EllipseArc, HyperbolaArc
from superfish_ng.certified_arcs import certified_finite_arc_tangents, _arc_membership, transcendental_interval, _parameter_fraction_enclosure


class CertifiedArcTests(unittest.TestCase):
    def test_series_zero_parity_and_independent_sinh_exp(self):
        for kind, expected in (('sin', 0), ('cos', 1), ('sinh', 0)):
            self.assertEqual(transcendental_interval(kind, 0), (F(expected),)*2)
        for x in (F(1, 10), F(1), F(5), F(20)):
            bound = transcendental_interval('sinh', x)
            with localcontext() as ctx:
                ctx.prec = 100
                decimal = Decimal(x.numerator)/Decimal(x.denominator)
                reference = (decimal.exp()-(-decimal).exp())/2
                # Decimal exp is an independent computation; generous 90-digit
                # uncertainty is far below the requested ~30-digit enclosure.
                uncertainty = F(1, 10**80)
                self.assertLessEqual(bound[0], F(reference)+uncertainty)
                self.assertGreaterEqual(bound[1], F(reference)-uncertainty)
            self.assertEqual(transcendental_interval('sinh', -x), (-bound[1], -bound[0]))
        for kind in ('sin', 'cos'):
            a = transcendental_interval(kind, F(1, 3)); b = transcendental_interval(kind, F(-1, 3))
            self.assertEqual(b, a if kind == 'cos' else (-a[1], -a[0]))

    def test_near_endpoint_membership_without_float_snapping(self):
        point = ((F(1), F(1)), (F(0), F(0)))
        for start, expected in ((F(-1, 10**20), 'INTERIOR'), (F(0), 'START'), (F(1, 10**20), 'EXTERIOR')):
            curve = EllipseArc((0, 0), (1, 1), float(start), 1.)
            self.assertEqual(_arc_membership(curve, point)['status'], expected)
        curve = EllipseArc((0, 0), (1, 1), -1., 1.)
        self.assertEqual(_arc_membership(curve, point)['status'], 'END')

    def test_periodic_large_sweep_reverse_and_internal_sector_join(self):
        point = ((F(1), F(1)), (F(0), F(0)))
        for start, sweep, expected in ((-1., 2., 'INTERIOR'), (-2., 4., 'INTERIOR'), (1., -2., 'INTERIOR'),
                                        (1., 5., 'EXTERIOR'), (1., -5., 'INTERIOR'),
                                        (-3., 6., 'INTERIOR')):
            a = EllipseArc((0, 0), (1, 1), start, sweep)
            self.assertEqual(_arc_membership(a, point)['status'], expected)
        negative = ((F(-1), F(-1)), (F(0), F(0)))
        self.assertEqual(_arc_membership(EllipseArc((0,0),(1,1),1.,5.),negative)['status'], 'INTERIOR')

    def test_hyperbola_finite_interval_endpoint_and_branch(self):
        point = ((F(1), F(1)), (F(0), F(0)))
        for start, end, branch, expected in ((-1.,1.,1,'INTERIOR'), (1.,-1.,1,'INTERIOR'),
                                            (0.,1.,1,'START'), (-1.,0.,1,'END'),
                                            (1e-20,1.,1,'EXTERIOR'), (-1.,1.,-1,'EXTERIOR')):
            a = HyperbolaArc((0,0),(1,1),start,end,branch)
            self.assertEqual(_arc_membership(a,point)['status'],expected)

    def test_circle_and_hyperbola_candidates_and_search_incompleteness(self):
        a = EllipseArc((0,0),(1,1),0.,math.pi)
        b = replace(a,center_zr_m=(4,0))
        result = certified_finite_arc_tangents(a,b)
        self.assertEqual(result['status'],'PASS'); self.assertEqual(len(result['candidates']),1)
        self.assertEqual([r['status'] for r in result['candidates'][0]['arc_memberships']], ['INTERIOR']*2)
        self.assertEqual(certified_finite_arc_tangents(a,b,max_boxes=1)['status'],'UNVERIFIED')
        h = HyperbolaArc((0,0),(1,1),0.,1.)
        result = certified_finite_arc_tangents(h,replace(h,center_zr_m=(0,4)))
        self.assertEqual(result['status'],'PASS'); self.assertEqual(len(result['candidates']),1)
        self.assertEqual([r['status'] for r in result['candidates'][0]['arc_memberships']], ['START']*2)

    def test_uncertain_box_and_series_budget_do_not_become_exterior(self):
        box = ((F(99,100),F(101,100)),(F(-1,100),F(1,100)))
        a = EllipseArc((0,0),(1,1),0.,1.)
        self.assertEqual(_arc_membership(a,box)['status'],'UNVERIFIED')
        with self.assertRaisesRegex(ValueError,'budget'):
            transcendental_interval('sin', 5, max_terms=1)
        result = certified_finite_arc_tangents(a,replace(a,center_zr_m=(4,0)),max_series_terms=1)
        self.assertEqual(result['status'],'UNVERIFIED')
        for kwargs in ({'endpoint_width':0},{'max_terms':True},{'max_terms':0}):
            with self.assertRaises(ValueError): transcendental_interval('sin',1,**kwargs)

    def test_fraction_enclosure_known_rational_inverse_and_budget(self):
        point = ((F(1), F(1)), (F(0), F(0)))
        for curve, expected in ((EllipseArc((0,0),(1,1),-1.,2.),F(1,2)),
                                (HyperbolaArc((0,0),(1,1),-1.,2.),F(1,3)),
                                (HyperbolaArc((0,0),(1,1),2.,-1.),F(2,3))):
            result = _parameter_fraction_enclosure(curve,point)
            self.assertEqual(result['status'],'PASS')
            lo,hi=result['interval']
            self.assertLessEqual(lo,expected);self.assertGreaterEqual(hi,expected)
            self.assertLessEqual(hi-lo,F(1,2**32))
        coarse = _parameter_fraction_enclosure(HyperbolaArc((0,0),(1,1),-1.,2.),point,max_fraction_steps=1)
        self.assertEqual(coarse['status'],'UNVERIFIED')
        lo,hi=coarse['interval'];self.assertLessEqual(lo,F(1,3));self.assertGreaterEqual(hi,F(1,3))

    def test_fraction_near_start_and_unresolved_midpoint_keep_true_parameter(self):
        point = ((F(1), F(1)), (F(0), F(0)))
        curve = EllipseArc((0,0),(1,1),-1e-20,1.)
        result = _parameter_fraction_enclosure(curve,point,fraction_width=F(1,10**25),max_fraction_steps=100)
        expected = -F(curve.start_rad)
        self.assertEqual(result['status'],'PASS')
        self.assertLessEqual(result['interval'][0],expected)
        self.assertGreaterEqual(result['interval'][1],expected)
        wide = ((F(99,100),F(101,100)),(F(-1,100),F(1,100)))
        result = _parameter_fraction_enclosure(EllipseArc((0,0),(1,1),-1.,2.),wide)
        self.assertEqual(result['status'],'UNVERIFIED')
        self.assertLessEqual(result['interval'][0],F(1,2))
        self.assertGreaterEqual(result['interval'][1],F(1,2))
