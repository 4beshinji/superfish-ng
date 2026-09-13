# SPDX-License-Identifier: Apache-2.0
from fractions import Fraction as F
import random
import unittest

from superfish_ng.rational_bounds import multiply, polynomial
from superfish_ng.polynomial_roots import isolate_real_roots, _divide
from superfish_ng.algebraic_root_signs import RootSystem, AlgebraicRoot
from superfish_ng.primitive_polynomial_roots import (isolate_primitive_real_roots, primitive_polynomial,
    PrimitiveRootSystem, PrimitiveAlgebraicRoot, _remainder, _numerator)


class PrimitivePolynomialRootTests(unittest.TestCase):
    def test_positive_remainder_scaling_and_exact_homogeneous_evaluation(self):
        rng = random.Random(2471)
        for _ in range(80):
            a = primitive_polynomial([rng.randrange(-9, 10) for i in range(rng.randrange(2, 10))], positive_leading=False)
            b = primitive_polynomial([rng.randrange(-9, 10) for i in range(rng.randrange(1, 6))], positive_leading=False)
            if b == (0,): continue
            expected = _divide(polynomial(a), polynomial(b))[1]
            observed = _remainder(a, b)
            if expected == (0,): self.assertEqual(observed, (0,))
            else:
                factor = F(observed[-1])/expected[-1]
                self.assertGreater(factor, 0)
                self.assertEqual(tuple(factor*c for c in expected), observed)
            x = F(rng.randrange(-10, 11), rng.randrange(1, 11))
            expected_value = sum(c*x**i for i, c in enumerate(a))
            self.assertEqual(_numerator(a, x), expected_value*x.denominator**(len(a)-1))

    def test_rational_and_integer_isolation_agree_including_budgets(self):
        rng = random.Random(3214)
        for _ in range(24):
            p = [F(rng.randrange(-9, 10), rng.randrange(1, 10)) for i in range(rng.randrange(2, 8))]
            for budget in (1, 300):
                settings = dict(absolute_width=F(1, 2**12), max_boxes=budget)
                self.assertEqual(isolate_primitive_real_roots(p, -2, 2, **settings), isolate_real_roots(p, -2, 2, **settings))
        for p, lo, hi, settings in (([0], 0, 1, {}), ([True], 0, 1, {}), ([1], 2, 1, {}),
                ([1], 0, 1, {'max_boxes': True}), ([1], 0, 1, {'absolute_width': 0})):
            with self.assertRaises(ValueError): isolate_primitive_real_roots(p, lo, hi, **settings)
        self.assertEqual(isolate_primitive_real_roots([1, -2, 1], 1, 1)['roots'], [(F(1), F(1))])

    def test_known_degree_56_roots_repetitions_and_sub_float_separation(self):
        roots = [F(-1), F(-2, 3), F(0), F(1, 3), F(1, 3)+F(1, 2**120), F(1)]
        p = (F(1),)
        for root in roots:
            for _ in range(6): p = multiply(p, (-root, 1))
        for _ in range(10): p = multiply(p, (1, 0, 1))
        self.assertEqual(len(p)-1, 56)
        for factor in (F(1), F(-7, 2**200)):
            report = isolate_primitive_real_roots([factor*c for c in p], -1, 1, absolute_width=F(1, 2**124))
            self.assertEqual(report['status'], 'PASS'); self.assertEqual(report['distinct_count'], 6)
            self.assertEqual(report['gcd_degree'], 48)
            for (lo, hi), root in zip(report['roots'], roots):
                self.assertTrue(lo == hi == root or lo < root < hi)
                self.assertLessEqual(hi-lo, F(1, 2**124))

    def test_root_signs_zero_factors_radicals_reflection_and_reuse(self):
        p = multiply(multiply((-2, 0, 1), (-2, 0, 1)), (-3, 0, 1))
        system = PrimitiveRootSystem(p); old = RootSystem(p)
        self.assertEqual(system.isolate(-4, 4, absolute_width=F(1, 4)), isolate_real_roots(p, -4, 4, absolute_width=F(1, 4)))
        roots = [PrimitiveAlgebraicRoot(system, interval) for interval in system.isolate(-4, 4, absolute_width=F(1, 4))['roots']]
        for root in roots:
            other = AlgebraicRoot(old, root.interval)
            for q in ((-2, 0, 1), (-3, 0, 1), (0, 1)):
                self.assertEqual(root.sign(q), other.sign(q))
            self.assertEqual(root.radical_sign((-2,), (0, 1), (2,)), other.radical_sign((-2,), (0, 1), (2,)))
        self.assertTrue(roots[1].equals_transformed(roots[2], -1))
        root = PrimitiveAlgebraicRoot(PrimitiveRootSystem((-2, 0, 1)), (1, 2), max_refinements=0)
        with self.assertRaisesRegex(ValueError, 'budget'): root.sign((F(-7, 5), 1))
        positive = roots[2]; epsilon = F(1, 2**200)
        self.assertEqual(positive.radical_sign((-2-epsilon,), (0, 1), (2,)), -1)
        self.assertEqual(positive.radical_sign((-2+epsilon,), (0, 1), (2,)), 1)


if __name__ == '__main__': unittest.main()
