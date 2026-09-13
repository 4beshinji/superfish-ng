# SPDX-License-Identifier: Apache-2.0
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import unittest
from superfish_ng.quadratic_radicals import RadicalTower


class QuadraticRadicalTests(unittest.TestCase):
    def test_dependent_roots_nested_roots_and_exact_zero(self):
        t = RadicalTower(); n = t.number
        a, b = t.square_root(n(2)), t.square_root(n(8))
        self.assertEqual(t.sign(t.subtract(b, t.scale(a, 2))), 0)
        self.assertEqual(t.sign(t.subtract(t.multiply(a, b), n(4))), 0)
        c = t.square_root(t.add(n(3), t.scale(a, 2)))
        self.assertEqual(t.sign(t.subtract(c, t.add(n(1), a))), 0)
        self.assertEqual(t.sign(t.subtract(c, t.add(n(F(1)+F(1,2**300)), a))), -1)
        self.assertEqual(t.sign(t.subtract(c, t.add(n(F(1)-F(1,2**300)), a))), 1)
        self.assertEqual(t.ratio_bounds(t.subtract(c, a), n(1), t.root_bounds(F(1,2**100))), (F(1), F(1)))
        self.assertEqual(t.square_root(t.subtract(b, t.scale(a, 2))), n(0))

    def test_independent_decimal_signs_and_intervals_across_scales(self):
        with localcontext() as context:
            context.prec = 180
            for exponent in (-300, 0, 300):
                t = RadicalTower(); scale = F(2)**exponent
                a, b = (t.square_root(t.number(x*scale*scale)) for x in (2, 3))
                root = t.square_root(t.add(t.number(scale*scale), t.multiply(a, b)))
                roots = t.root_bounds(F(1,2**160))
                values = [D(2).sqrt()*D(2)**exponent, D(3).sqrt()*D(2)**exponent,
                          (D(1)+D(6).sqrt()).sqrt()*D(2)**exponent]
                for coefficients in ((1, 1, 1), (3, -2, 1), (-1, -1, -1), (-3, 2, -1)):
                    element = t.number(0)
                    for coefficient, item in zip(coefficients, (a, b, root)):
                        element = t.add(element, t.scale(item, coefficient))
                    expected = sum(D(c)*v for c, v in zip(coefficients, values))
                    self.assertEqual(t.sign(element), (expected>0)-(expected<0))
                    low, high = t.bounds(element, roots)
                    self.assertLessEqual(D(low.numerator)/D(low.denominator), expected)
                    self.assertGreaterEqual(D(high.numerator)/D(high.denominator), expected)

    def test_rational_roots_reuse_and_invalid_arithmetic(self):
        t = RadicalTower(); n = t.number
        self.assertEqual(t.square_root(n(F(400,1681))), n(F(20,41)))
        a = t.square_root(n(2))
        self.assertEqual(t.square_root(n(2)), a)
        with self.assertRaises(ValueError): t.square_root(n(-1))
        with self.assertRaises(ValueError): t.root_bounds(0)
        with self.assertRaises(ValueError): t.ratio_bounds(a, n(0), [])


if __name__ == '__main__': unittest.main()
