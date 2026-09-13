# SPDX-License-Identifier: Apache-2.0
"""Certified polynomial and positive-radical signs at isolated real roots.

Root intervals are open unless they are rational points. Gcd/Sturm counts prove
zero; interval separation proves nonzero signs. Refinement exhaustion raises.
No irreducible factorization or floating root approximation is required.
"""
from fractions import Fraction as F
from .rational_bounds import polynomial, add, multiply
from .polynomial_roots import _divide, _square_free, _sturm, _variations, _value
from .certified_arcs import _multiply


def scale(p, factor):
    return polynomial([factor*x for x in p])


def subtract(a, b):
    return add(a, scale(b, -1))


class RootSystem:
    """Shared rational arithmetic for distinct roots of one nonzero polynomial."""
    def __init__(self, coefficients):
        p = polynomial(coefficients)
        if len(p) < 2:
            raise ValueError('root system requires a nonconstant polynomial')
        self.polynomial = _square_free(p)[0]
        self.sequence = _sturm(self.polynomial)
        self.remainders = {}
        self.zero_sequences = {}

    def remainder(self, coefficients):
        p = polynomial(coefficients)
        if p not in self.remainders:
            self.remainders[p] = _divide(p, self.polynomial)[1]
        return self.remainders[p]

    def zero_sequence(self, p):
        if p not in self.zero_sequences:
            a, b = self.polynomial, p
            while b != (0,):
                a, b = b, _divide(a, b)[1]
            self.zero_sequences[p] = _sturm(a) if len(a) > 1 else None
        return self.zero_sequences[p]


class AlgebraicRoot:
    def __init__(self, system, interval, *, max_refinements=512):
        self.system = system
        self.interval = tuple(map(F, interval))
        self.refinements = 0
        self.max_refinements = max_refinements
        self.signs = {}

    def bounds(self, coefficients):
        p = self.system.remainder(coefficients)
        result = (p[-1], p[-1])
        for coefficient in reversed(p[:-1]):
            low, high = _multiply(result, self.interval)
            result = low+coefficient, high+coefficient
        return result

    def refine(self):
        lo, hi = self.interval
        if lo == hi:
            return
        if self.refinements >= self.max_refinements:
            raise ValueError('algebraic root refinement budget exhausted')
        self.refinements += 1
        mid = (lo+hi)/2
        if _value(self.system.polynomial, mid) == 0:
            self.interval = mid, mid
        elif _variations(self.system.sequence, lo)-_variations(self.system.sequence, mid):
            self.interval = lo, mid
        else:
            self.interval = mid, hi

    def narrow(self, width):
        while self.interval[1]-self.interval[0] > width:
            self.refine()

    def sign(self, coefficients):
        p = self.system.remainder(coefficients)
        if p in self.signs:
            return self.signs[p]
        low, high = self.bounds(p)
        if low > 0 or high < 0 or low == high:
            result = (low > 0)-(high < 0)
        else:
            sequence = self.system.zero_sequence(p)
            lo, hi = self.interval
            zero = sequence is not None and (
                _value(sequence[0], lo) == 0 if lo == hi else
                _variations(sequence, lo)-_variations(sequence, hi)-int(_value(sequence[0], hi) == 0) > 0)
            if zero:
                result = 0
            else:
                while low <= 0 <= high:
                    self.refine()
                    low, high = self.bounds(p)
                result = 1 if low > 0 else -1
        self.signs[p] = result
        return result

    def radical_sign(self, a, b, positive_radicand):
        """Sign of a(root)+b(root)*sqrt(r(root)), requiring r(root)>0."""
        if self.sign(positive_radicand) <= 0:
            raise ValueError('positive radicand required for algebraic radical sign')
        first, second = self.sign(a), self.sign(b)
        if first == 0:
            return second
        if second == 0 or first == second:
            return first
        norm = subtract(multiply(a, a), multiply(positive_radicand, multiply(b, b)))
        return first*self.sign(norm)

    def equals_transformed(self, other, sign=1):
        """Prove other.root == sign*self.root for sign in {-1,+1}."""
        if sign not in (-1, 1):
            raise ValueError('root reflection sign must be -1 or +1')
        lo, hi = other.interval
        left = self.sign((-lo, sign))
        right = self.sign((-hi, sign))
        if lo == hi:
            return left == 0
        if left <= 0 or right >= 0:
            return False
        transformed = tuple(c*sign**i for i, c in enumerate(other.system.polynomial))
        return self.sign(transformed) == 0
