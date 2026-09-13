# SPDX-License-Identifier: Apache-2.0
from fractions import Fraction as F
import unittest
from superfish_ng.algebraic_root_signs import RootSystem, AlgebraicRoot
from superfish_ng.polynomial_roots import isolate_real_roots
from superfish_ng.rational_bounds import multiply


class AlgebraicRootSignTests(unittest.TestCase):
    def roots(self, p):
        system = RootSystem(p)
        return [AlgebraicRoot(system, interval) for interval in
                isolate_real_roots(p, -4, 4, absolute_width=F(1, 4))['roots']]

    def test_reducible_repeated_polynomial_signs_and_reflected_roots(self):
        p = multiply(multiply((-2, 0, 1), (-2, 0, 1)), (-3, 0, 1))
        roots = self.roots(p)
        self.assertEqual([r.sign((-2, 0, 1)) for r in roots], [1, 0, 0, 1])
        self.assertEqual([r.sign((-3, 0, 1)) for r in roots], [0, -1, -1, 0])
        self.assertTrue(roots[1].equals_transformed(roots[2], -1))
        self.assertFalse(roots[1].equals_transformed(roots[3], -1))
        self.assertFalse(roots[1].equals_transformed(roots[2]))

    def test_dependent_radical_equality_and_sub_float_separation(self):
        negative, positive = self.roots((-2, 0, 1))
        for r in (negative, positive):
            self.assertEqual(r.radical_sign((-2,), (0, 1), (2,)), -1 if r is negative else 0)
        epsilon = F(1, 2**200)
        self.assertEqual(positive.radical_sign((-2-epsilon,), (0, 1), (2,)), -1)
        self.assertEqual(positive.radical_sign((-2+epsilon,), (0, 1), (2,)), 1)
        self.assertEqual(positive.radical_sign((-2,), (1,), (0, 0, 2)), 0)

    def test_open_endpoint_roots_and_budget_never_become_zero(self):
        system = RootSystem((0, -2, 1))
        point = AlgebraicRoot(system, (0, 0))
        other = AlgebraicRoot(system, (0, 3))  # Open interval contains only root 2.
        self.assertEqual(point.sign((0, 1)), 0)
        self.assertEqual(other.sign((0, 1)), 1)
        self.assertEqual(other.sign((-2, 1)), 0)
        root = AlgebraicRoot(RootSystem((-2, 0, 1)), (1, 2), max_refinements=0)
        with self.assertRaisesRegex(ValueError, 'budget'):
            root.sign((F(-7, 5), 1))


if __name__ == '__main__': unittest.main()
