# SPDX-License-Identifier: Apache-2.0
"""Polynomial pairs A(q)+B(q)*sqrt(S(q)) at one isolated real root.

No division in an algebraic number field is needed: coordinate ratios retain
their nonzero denominators. A further square root of a nonnegative rational
is used only for the two target feet of a rank-one conic/circle pencil.
"""
from fractions import Fraction as F

from .rational_bounds import polynomial, add, multiply
from .algebraic_root_signs import scale
from .certified_arcs import _multiply
from .contact_enclosures import _interval_add, _interval_divide
from .quadratic_radicals import _sqrt_rational


class RootRadicalArithmetic:
    def __init__(self, root, positive_radicand):
        self.root = root
        self.radicand = polynomial(positive_radicand)
        if root.sign(self.radicand) <= 0:
            raise ValueError('positive source radicand required')

    @staticmethod
    def rational(coefficients):
        return polynomial(coefficients), (F(0),)

    @staticmethod
    def add(left, right):
        return tuple(add(a, b) for a, b in zip(left, right))

    @staticmethod
    def scale(value, coefficient):
        return tuple(scale(p, coefficient) for p in value)

    def subtract(self, left, right):
        return self.add(left, self.scale(right, -1))

    def multiply(self, left, right):
        a, b = left; c, d = right
        return (add(multiply(a, c), multiply(self.radicand, multiply(b, d))),
                add(multiply(a, d), multiply(b, c)))

    def sign(self, value):
        return self.root.radical_sign(*value, self.radicand)

    def nested_sign(self, rational_part, radical_part, radicand):
        """Sign of U+V*sqrt(k), where U,V belong to the source radical field."""
        k = F(radicand)
        if k < 0:
            raise ValueError('nonnegative additional radicand required')
        first = self.sign(rational_part)
        if k == 0:
            return first
        second = self.sign(radical_part)
        if first == 0:
            return second
        if second == 0 or first == second:
            return first
        norm = self.subtract(self.multiply(rational_part, rational_part),
                             self.scale(self.multiply(radical_part, radical_part), k))
        return first*self.sign(norm)

    def bounds(self, value, sqrt_width):
        s = self.root.bounds(self.radicand)
        while s[0] <= 0:
            self.root.refine()
            s = self.root.bounds(self.radicand)
        radical = (_sqrt_rational(s[0], sqrt_width)[0], _sqrt_rational(s[1], sqrt_width)[1])
        return _interval_add(self.root.bounds(value[0]), _multiply(self.root.bounds(value[1]), radical))

    def ratio_bounds(self, numerator, denominator, width):
        """Enclose a ratio, preserving exact normalized vertices 0 and ±1."""
        if self.sign(denominator) == 0:
            raise ValueError('nonzero coordinate denominator required')
        for value in (0, -1, 1):
            if self.sign(self.subtract(numerator, self.scale(denominator, value))) == 0:
                return F(value), F(value)
        precision = F(width)/16
        while True:
            low, high = self.bounds(denominator, precision)
            if low > 0 or high < 0:
                result = _interval_divide(self.bounds(numerator, precision), (low, high))
                if result[1]-result[0] <= width/2:
                    # Short outward rational endpoints prevent high-degree
                    # intermediate denominators from bloating saved evidence.
                    step = F(width)/4
                    return (result[0]//step)*step, -((-result[1])//step)*step
            # Tightening the rational sqrt enclosure is necessary even when q
            # is rational and its root interval cannot shrink further.
            if precision < F(width)/2**self.root.max_refinements:
                raise ValueError('coordinate enclosure precision budget exhausted')
            precision /= 2
            self.root.refine()
