# SPDX-License-Identifier: Apache-2.0
from fractions import Fraction as F
import unittest

from superfish_ng.algebraic_root_signs import AlgebraicRoot, RootSystem
from superfish_ng.root_radical_arithmetic import RootRadicalArithmetic


class RootRadicalArithmeticTests(unittest.TestCase):
    def test_dependent_nested_radicals_cancel_and_signs_survive(self):
        root = AlgebraicRoot(RootSystem((-2, 0, 1)), (1, 2))
        arithmetic = RootRadicalArithmetic(root, (3,))
        # (sqrt(2)+sqrt(3))*sqrt(2) = 2+sqrt(6), with sqrt(2)=q.
        left = ((F(2),), (F(0), F(1)))
        right = ((F(0), F(-1)), (F(-1),))
        self.assertEqual(arithmetic.nested_sign(left, right, 2), 0)
        for perturbation in (F(1, 2**120), F(-1, 2**120)):
            changed = arithmetic.add(left, arithmetic.rational((perturbation,)))
            self.assertEqual(arithmetic.nested_sign(changed, right, 2), 1 if perturbation > 0 else -1)
        with self.assertRaises(ValueError): arithmetic.nested_sign(left, right, -1)

    def test_coordinate_ratio_and_exact_vertices(self):
        root = AlgebraicRoot(RootSystem((-2, 0, 1)), (1, 2))
        arithmetic = RootRadicalArithmetic(root, (3,))
        denominator = ((F(0), F(1)), (F(-1),))  # sqrt(2)-sqrt(3) < 0
        for value in (0, -1, 1):
            self.assertEqual(arithmetic.ratio_bounds(arithmetic.scale(denominator, value), denominator, F(1, 2**100)),
                             (value, value))
        result = arithmetic.ratio_bounds(arithmetic.rational((-1,)), denominator, F(1, 2**100))
        # 1/(sqrt(3)-sqrt(2)) = sqrt(3)+sqrt(2), independently bounded by squares.
        low, high = result
        self.assertLessEqual(high-low, F(1, 2**100))
        self.assertLess((low*low-5)**2, 24); self.assertGreater((high*high-5)**2, 24)
        with self.assertRaises(ValueError): arithmetic.ratio_bounds(denominator, arithmetic.rational((0,)), F(1, 2**100))
