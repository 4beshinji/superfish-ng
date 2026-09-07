# SPDX-License-Identifier: Apache-2.0
"""Distinct real-root isolation with exact rational Sturm arithmetic.

Non-point isolating intervals are OPEN. Endpoint roots are separate points.
Float inputs denote their exact binary rational values, not uncertain data.
"""
from fractions import Fraction
from .rational_bounds import polynomial


def _value(p, x):
    value = Fraction(0)
    for coefficient in reversed(p):
        value = value*x+coefficient
    return value


def _derivative(p):
    return polynomial([i*p[i] for i in range(1, len(p))] or [0])


def _divide(a, b):
    if b == (0,):
        raise ValueError('polynomial division by zero')
    remainder = list(a)
    quotient = [Fraction(0)]*max(1, len(a)-len(b)+1)
    while len(remainder) >= len(b) and remainder != [0]:
        shift = len(remainder)-len(b)
        coefficient = remainder[-1]/b[-1]
        quotient[shift] += coefficient
        for i, value in enumerate(b):
            remainder[shift+i] -= coefficient*value
        remainder = list(polynomial(remainder))
    return polynomial(quotient), polynomial(remainder)


def _square_free(p):
    a, b = p, _derivative(p)
    while b != (0,):
        a, b = b, _divide(a, b)[1]
    gcd = polynomial([c/a[-1] for c in a])
    return _divide(p, gcd)[0], len(gcd)-1


def _sturm(p):
    sequence = [p, _derivative(p)]
    while sequence[-1] != (0,):
        remainder = _divide(sequence[-2], sequence[-1])[1]
        if remainder == (0,):
            break
        # Only positive rescaling preserves the Sturm sign variations.
        scale = abs(remainder[-1])
        sequence.append(polynomial([-c/scale for c in remainder]))
    return sequence


def _variations(sequence, x):
    values = [_value(p, x) for p in sequence]
    signs = [1 if value > 0 else -1 for value in values if value]
    return sum(a != b for a, b in zip(signs, signs[1:]))


def isolate_real_roots(coefficients, lower, upper, *, absolute_width=Fraction(1, 2**40), max_boxes=10000):
    """Count all distinct roots in [lower,upper] and isolate them within a budget.

    PASS means each reported open interval contains exactly one distinct root
    and has width <= absolute_width, or is an exact rational root point.
    UNVERIFIED retains every unfinished interval with its exact root count.
    The budget limits subdivision boxes, not coefficient arithmetic complexity.
    Repeated roots are reduced exactly before endpoint variation counts.
    """
    p = polynomial(coefficients)
    lo, hi, width = (polynomial([v])[0] for v in (lower, upper, absolute_width))
    if lo > hi or width <= 0:
        raise ValueError('root interval requires lower <= upper and positive absolute_width')
    if type(max_boxes) is not int or max_boxes < 1:
        raise ValueError('max_boxes must be a positive integer')
    if p == (0,):
        raise ValueError('identically zero polynomial has infinitely many roots')
    if len(p) == 1:
        return dict(status='PASS', roots=[], unresolved=[], distinct_count=0, boxes=0, gcd_degree=0)
    q, gcd_degree = _square_free(p)
    sequence = _sturm(q)
    def count(a, b):
        return _variations(sequence, a)-_variations(sequence, b)-int(_value(q, b) == 0) if a < b else 0
    roots = [(x, x) for x in sorted({lo, hi}) if _value(q, x) == 0]
    total = count(lo, hi)+len(roots)
    pending = [(lo, hi, count(lo, hi))] if lo < hi else []
    boxes = 0
    while pending and boxes < max_boxes:
        a, b, n = pending.pop()
        boxes += 1
        if n == 0:
            continue
        if n == 1 and b-a <= width:
            roots.append((a, b))
            continue
        mid = (a+b)/2
        if _value(q, mid) == 0:
            roots.append((mid, mid))
        for x, y in ((mid, b), (a, mid)):
            number = count(x, y)
            if number:
                pending.append((x, y, number))
    return dict(status='UNVERIFIED' if pending else 'PASS', roots=sorted(roots),
                unresolved=sorted(pending), distinct_count=total, boxes=boxes, gcd_degree=gcd_degree)
