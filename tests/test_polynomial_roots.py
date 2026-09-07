# SPDX-License-Identifier: Apache-2.0
from fractions import Fraction as F
import unittest
from superfish_ng.rational_bounds import multiply
from superfish_ng.polynomial_roots import isolate_real_roots


class PolynomialRootTests(unittest.TestCase):
    def assert_isolation(self, report, expected, width):
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['distinct_count'], len(expected))
        self.assertEqual(len(report['roots']), len(expected))
        self.assertFalse(report['unresolved'])
        for (a,b), x in zip(report['roots'], sorted(expected)):
            self.assertTrue(a == b == x or a < x < b)
            self.assertLessEqual(b-a, width)

    def test_repeated_endpoint_roots_and_complex_factor(self):
        p = (F(1),)
        expected = [F(-1), F(0), F(1,3), F(1)]
        for root in expected:
            for _ in range(3):
                p = multiply(p, (-root, F(1)))
        p = multiply(p, (F(1), F(0), F(1)))
        report = isolate_real_roots(p, -1, 1, absolute_width=F(1,10000))
        self.assert_isolation(report, expected, F(1,10000))
        self.assertEqual(report['gcd_degree'], 8)
        self.assertIn((F(-1),F(-1)),report['roots'])
        self.assertIn((F(1),F(1)),report['roots'])

    def test_close_roots_below_float_resolution_and_sign_scale(self):
        a, b = F(1,3), F(1,3)+F(1,10**40)
        p = multiply((-a,F(1)),(-b,F(1)))
        width = F(1,10**42)
        for scale in (F(1), F(-7,11), F(10)**200):
            report = isolate_real_roots([scale*c for c in p], 0, 1, absolute_width=width)
            self.assert_isolation(report,[a,b],width)

    def test_irrational_roots_and_exact_root_count(self):
        report = isolate_real_roots([-2,0,1], -2,2)
        self.assertEqual(report['status'],'PASS')
        self.assertEqual(report['distinct_count'],2)
        (a,b),(c,d) = report['roots']
        self.assertTrue(a*a > 2 > b*b)
        self.assertTrue(c*c < 2 < d*d)
        self.assertEqual(isolate_real_roots([1,0,1], -10,10)['distinct_count'],0)

    def test_budget_keeps_all_unresolved_roots(self):
        report = isolate_real_roots([-1,0,1], -2,2, max_boxes=1)
        self.assertEqual(report['status'],'UNVERIFIED')
        self.assertEqual(len(report['roots'])+sum(n for a,b,n in report['unresolved']),report['distinct_count'])
        self.assertEqual(report['distinct_count'],2)

    def test_single_point_constant_and_strict_inputs(self):
        self.assert_isolation(isolate_real_roots([1,-2,1],1,1),[F(1)],F(1))
        self.assertEqual(isolate_real_roots([5],-1,1)['roots'],[])
        for p,lo,hi,kw in (([0],0,1,{}),([True],0,1,{}),([1],2,1,{}),([1],0,1,{'absolute_width':0}),([1],0,1,{'max_boxes':True}),([1],float('nan'),1,{})):
            with self.assertRaises(ValueError):
                isolate_real_roots(p,lo,hi,**kw)
