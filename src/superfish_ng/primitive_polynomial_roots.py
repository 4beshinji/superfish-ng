# SPDX-License-Identifier: Apache-2.0
"""Sturm isolation with primitive integer remainders and rational endpoints.

Each pseudo-division step uses a positive multiplier and removes only positive
integer content. Sturm signs therefore agree with rational Euclidean division.
Existing rational root-isolation and saved-diagnosis rules are left unchanged.
"""
from fractions import Fraction as F
from math import gcd, lcm

from .rational_bounds import polynomial
from .polynomial_roots import _divide
from .algebraic_root_signs import RootSystem, AlgebraicRoot


def _primitive(values, *, positive_leading=False):
    values = list(values)
    while len(values) > 1 and values[-1] == 0:
        values.pop()
    content = gcd(*values)
    if content == 0:
        return (0,)
    sign = -1 if positive_leading and values[-1] < 0 else 1
    return tuple(sign*value//content for value in values)


def primitive_polynomial(coefficients, *, positive_leading=True):
    """Clear rational denominators and positive content without changing roots."""
    coefficients = polynomial(coefficients)
    denominator = lcm(*(value.denominator for value in coefficients))
    return _primitive([int(value*denominator) for value in coefficients], positive_leading=positive_leading)


def _remainder(first, second):
    """A positive multiple of the rational Euclidean remainder, made primitive."""
    if second == (0,):
        raise ValueError('polynomial division by zero')
    result = first
    while len(result) >= len(second) and result != (0,):
        offset = len(result)-len(second); leading = result[-1]
        multiplier, sign = abs(second[-1]), 1 if second[-1] > 0 else -1
        values = [multiplier*value for value in result]
        for i, value in enumerate(second):
            values[i+offset] -= sign*leading*value
        result = _primitive(values)
    return result


def _gcd(first, second):
    while second != (0,):
        first, second = second, _remainder(first, second)
    return _primitive(first, positive_leading=True)


def _derivative(p):
    return _primitive([i*p[i] for i in range(1, len(p))] or [0])


def _square_free(p):
    common = _gcd(p, _derivative(p))
    quotient, remainder = _divide(polynomial(p), polynomial(common))
    if remainder != (0,):
        raise ArithmeticError('exact polynomial gcd did not divide its input')
    return primitive_polynomial(quotient), len(common)-1


def _sturm(p):
    result = [_primitive(p), _derivative(p)]
    while result[-1] != (0,):
        remainder = _remainder(result[-2], result[-1])
        if remainder == (0,):
            break
        result.append(tuple(-value for value in remainder))
    return result


def _prepare(p):
    sequence = _sturm(p)
    common = _primitive(sequence[-1], positive_leading=True)
    if len(common) == 1:
        return p, 0, sequence
    quotient, remainder = _divide(polynomial(p), polynomial(common))
    if remainder != (0,):
        raise ArithmeticError('exact polynomial gcd did not divide its input')
    q = primitive_polynomial(quotient)
    return q, len(common)-1, _sturm(q)


def _numerator(p, x):
    """Evaluate b^degree p(a/b) as an integer; b is positive."""
    a, b = x.numerator, x.denominator
    result, denominator = p[-1], b
    for coefficient in reversed(p[:-1]):
        result = result*a+coefficient*denominator
        denominator *= b
    return result


def _variations(sequence, x):
    previous = count = 0
    for p in sequence:
        value = _numerator(p, x); sign = (value > 0)-(value < 0)
        if sign:
            count += previous != 0 and previous != sign
            previous = sign
    return count


def isolate_primitive_real_roots(coefficients, lower, upper, *, absolute_width=F(1, 2**40), max_boxes=10000):
    """Same open-interval/point and budget contract as rational Sturm isolation."""
    p = primitive_polynomial(coefficients)
    lo, hi, width = (polynomial([value])[0] for value in (lower, upper, absolute_width))
    if lo > hi or width <= 0:
        raise ValueError('root interval requires lower <= upper and positive absolute_width')
    if type(max_boxes) is not int or max_boxes < 1:
        raise ValueError('max_boxes must be a positive integer')
    if p == (0,):
        raise ValueError('identically zero polynomial has infinitely many roots')
    if len(p) == 1:
        return dict(status='PASS', roots=[], unresolved=[], distinct_count=0, boxes=0, gcd_degree=0)
    q, degree, sequence = _prepare(p)
    return _isolate(q, degree, sequence, lo, hi, width, max_boxes)


def _isolate(q, degree, sequence, lo, hi, width, max_boxes):

    def count(a, b):
        return _variations(sequence, a)-_variations(sequence, b)-int(_numerator(q, b) == 0) if a < b else 0

    roots = [(x, x) for x in sorted({lo, hi}) if _numerator(q, x) == 0]
    total = count(lo, hi)+len(roots); pending = [(lo, hi, count(lo, hi))] if lo < hi else []
    boxes = 0
    while pending and boxes < max_boxes:
        a, b, n = pending.pop(); boxes += 1
        if n == 0:
            continue
        if n == 1 and b-a <= width:
            roots.append((a, b)); continue
        mid = (a+b)/2
        if _numerator(q, mid) == 0:
            roots.append((mid, mid))
        for x, y in ((mid, b), (a, mid)):
            number = count(x, y)
            if number:
                pending.append((x, y, number))
    return dict(status='UNVERIFIED' if pending else 'PASS', roots=sorted(roots), unresolved=sorted(pending),
                distinct_count=total, boxes=boxes, gcd_degree=degree)


class PrimitiveRootSystem(RootSystem):
    """Algebraic sign system using integer gcd/Sturm arithmetic for one polynomial."""
    def __init__(self, coefficients):
        p = primitive_polynomial(coefficients)
        if len(p) < 2:
            raise ValueError('root system requires a nonconstant polynomial')
        p, self.gcd_degree, self.sequence = _prepare(p)
        self.integer_polynomial = p
        self.polynomial = polynomial(p)
        self.remainders = {}; self.zero_sequences = {}

    def isolate(self, lower, upper, *, absolute_width=F(1, 2**40), max_boxes=10000):
        """Reuse this system's square-free polynomial and Sturm sequence."""
        lo, hi, width = (polynomial([value])[0] for value in (lower, upper, absolute_width))
        if lo > hi or width <= 0:
            raise ValueError('root interval requires lower <= upper and positive absolute_width')
        if type(max_boxes) is not int or max_boxes < 1:
            raise ValueError('max_boxes must be a positive integer')
        return _isolate(self.integer_polynomial, self.gcd_degree, self.sequence, lo, hi, width, max_boxes)

    def zero_sequence(self, p):
        if p not in self.zero_sequences:
            common = _gcd(self.integer_polynomial, primitive_polynomial(p))
            self.zero_sequences[p] = _sturm(common) if len(common) > 1 else None
        return self.zero_sequences[p]


class PrimitiveAlgebraicRoot(AlgebraicRoot):
    """Retain exact radical signs while avoiding rational Horner work in refinement."""
    def refine(self):
        lo, hi = self.interval
        if lo == hi:
            return
        if self.refinements >= self.max_refinements:
            raise ValueError('algebraic root refinement budget exhausted')
        self.refinements += 1; mid = (lo+hi)/2
        if _numerator(self.system.integer_polynomial, mid) == 0:
            self.interval = mid, mid
        elif _variations(self.system.sequence, lo)-_variations(self.system.sequence, mid):
            self.interval = lo, mid
        else:
            self.interval = mid, hi
