# SPDX-License-Identifier: Apache-2.0
"""Small exact towers of positive quadratic radicals with certified signs.

Elements are coefficient tuples in successive square-root generators. The
representation need not be irreducible: sign/zero use recursive real norms,
so dependent radicals are valid. Division is only by a rational scalar.
"""
from fractions import Fraction as F
from math import isqrt


def _trim(values):
    values = tuple(values)
    while len(values) > 1 and not any(values[len(values)//2:]):
        values = values[:len(values)//2]
    return values


def _pad(value, size):
    return value + (F(0),) * (size-len(value))


def _add(left, right):
    size = max(len(left), len(right))
    return _trim(a+b for a, b in zip(_pad(left, size), _pad(right, size)))


def _scale(value, factor):
    return _trim(x*factor for x in value)


def _product_bounds(a, b):
    values = [x*y for x in a for y in b]
    return min(values), max(values)


def _sqrt_rational(value, relative_width):
    if value == 0:
        return F(0), F(0)
    n, d = isqrt(value.numerator), isqrt(value.denominator)
    if n*n == value.numerator and d*d == value.denominator:
        return F(n, d), F(n, d)
    exponent = (value.numerator.bit_length()-value.denominator.bit_length())//2
    scale = F(2)**exponent
    normalized = value/(scale*scale)
    bits = max(0, relative_width.denominator.bit_length()-relative_width.numerator.bit_length()+1)
    denominator = 2**bits
    lower = isqrt(normalized.numerator*denominator*denominator//normalized.denominator)
    return scale*F(lower, denominator), scale*F(lower+1, denominator)


class RadicalTower:
    """Private geometry arithmetic, bounded to at most three radical stages."""
    def __init__(self):
        self.radicands = []

    def number(self, value):
        return (F(value),)

    add = staticmethod(_add)
    scale = staticmethod(_scale)

    def subtract(self, left, right):
        return _add(left, _scale(right, -1))

    def multiply(self, left, right):
        size = max(len(left), len(right))
        if size == 1:
            return (left[0]*right[0],)
        half = size//2
        left, right = _pad(left, size), _pad(right, size)
        a, b, c, d = left[:half], left[half:], right[:half], right[half:]
        low = _add(self.multiply(a, c),
                   self.multiply(self.multiply(b, d), self.radicands[size.bit_length()-2]))
        high = _add(self.multiply(a, d), self.multiply(b, c))
        return _trim(_pad(low, half) + _pad(high, half))

    def sign(self, value):
        value = _trim(value)
        if len(value) == 1:
            return (value[0] > 0)-(value[0] < 0)
        half = len(value)//2
        a, b = _trim(value[:half]), _trim(value[half:])
        first, second = self.sign(a), self.sign(b)
        if first == 0:
            return second
        if second == 0 or first == second:
            return first
        radicand = self.radicands[len(value).bit_length()-2]
        norm = self.subtract(self.multiply(a, a), self.multiply(radicand, self.multiply(b, b)))
        return first*self.sign(norm)

    def square_root(self, value):
        value = _trim(value)
        sign = self.sign(value)
        if sign < 0:
            raise ValueError('real radical requires a nonnegative radicand')
        if sign == 0:
            return self.number(0)
        if len(value) == 1:
            low, high = _sqrt_rational(value[0], F(1, 2))
            if low == high:
                return self.number(low)
        for index, previous in enumerate(self.radicands):
            if self.sign(self.subtract(value, previous)) == 0:
                return (F(0),)*(2**index) + (F(1),) + (F(0),)*(2**index-1)
        if len(self.radicands) >= 3:
            raise ValueError('geometry radical tower exceeds three stages')
        index = len(self.radicands)
        self.radicands.append(value)
        return (F(0),)*(2**index) + (F(1),) + (F(0),)*(2**index-1)

    def root_bounds(self, relative_width):
        width = F(relative_width)
        if width <= 0:
            raise ValueError('radical enclosure width must be positive')
        roots = []
        for radicand in self.radicands:
            low, high = self.bounds(radicand, roots)
            if high < 0:
                raise ArithmeticError('positive radicand has an invalid enclosure')
            roots.append((_sqrt_rational(max(F(0), low), width)[0],
                          _sqrt_rational(high, width)[1]))
        return roots

    def bounds(self, value, roots):
        result = (F(0), F(0))
        for mask, coefficient in enumerate(value):
            if coefficient == 0:
                continue
            term = (coefficient, coefficient)
            for index, root in enumerate(roots):
                if mask & (1 << index):
                    term = _product_bounds(term, root)
            result = tuple(a+b for a, b in zip(result, term))
        return result

    def ratio_bounds(self, numerator, denominator, roots):
        """Preserve algebraically exact axis endpoints before interval division."""
        if self.sign(denominator) == 0:
            raise ValueError('zero radical denominator')
        for exact in (0, 1, -1):
            if self.sign(self.subtract(numerator, self.scale(denominator, exact))) == 0:
                return F(exact), F(exact)
        low, high = self.bounds(denominator, roots)
        if low <= 0 <= high:
            raise ValueError('radical denominator sign is not separated by the enclosure')
        return _product_bounds(self.bounds(numerator, roots), (1/high, 1/low))
