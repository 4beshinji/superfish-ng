# SPDX-License-Identifier: Apache-2.0
"""Exact-rational Bernstein bounds for a vector rational function on [0,1]."""
from fractions import Fraction
import heapq
import math


def polynomial(values):
    """Ascending power coefficients; floats mean their exact binary values."""
    result = []
    for value in values:
        if type(value) not in (int, float, Fraction) or (type(value) is float and not math.isfinite(value)):
            raise ValueError('polynomial coefficients must be finite int, float or Fraction values')
        result.append(Fraction(value))
    if not result:
        raise ValueError('polynomial coefficients cannot be empty')
    while len(result) > 1 and result[-1] == 0:
        result.pop()
    return tuple(result)


def add(a, b):
    return polynomial([(a[i] if i < len(a) else 0)+(b[i] if i < len(b) else 0)
                       for i in range(max(len(a), len(b)))])


def multiply(a, b):
    result = [Fraction(0)]*(len(a)+len(b)-1)
    for i, first in enumerate(a):
        for j, second in enumerate(b):
            result[i+j] += first*second
    return polynomial(result)


def bernstein(coefficients, degree=None):
    degree = len(coefficients)-1 if degree is None else degree
    return tuple(sum((coefficients[k]*Fraction(math.comb(i, k), math.comb(degree, k))
                      for k in range(min(i+1, len(coefficients)))), Fraction(0)) for i in range(degree+1))


def split(coefficients):
    row = list(coefficients)
    left, right = [row[0]], [row[-1]]
    while len(row) > 1:
        row = [(a+b)/2 for a, b in zip(row[:-1], row[1:])]
        left.append(row[0]); right.append(row[-1])
    return tuple(left), tuple(reversed(right))


def _sqrt_bound(value, upper):
    try:
        if value == 0:
            return 0.
        exponent = value.numerator.bit_length()-value.denominator.bit_length()
        exponent -= exponent % 2
        scaled = value/Fraction(2)**exponent
        result = math.ldexp(math.sqrt(float(scaled)), exponent//2)
    except (OverflowError, ValueError) as exc:
        raise ValueError('rational norm bound exceeds floating-point output range') from exc
    if not math.isfinite(result):
        raise ValueError('rational norm bound exceeds floating-point output range')
    while (Fraction(result)**2 < value if upper else Fraction(result)**2 > value):
        result = math.nextafter(result, math.inf if upper else 0.)
        if not math.isfinite(result):
            raise ValueError('rational norm bound exceeds floating-point output range')
    return result


def bound_rational_norm(numerators, denominator, *, relative_tolerance=1e-6, max_boxes=10000):
    """Bracket max sqrt(sum(N_i(t)^2))/D(t), requiring D(t)>0 throughout.

    Every polynomial operation and subdivision bound uses Fraction. Returned
    float bounds are rounded outward by exact squared-value comparisons.
    Exhausted work or output precision yields UNVERIFIED, never a sample-only
    success. This bounds the supplied polynomials, not physical FEM accuracy.
    """
    if type(relative_tolerance) not in (int, float) or not math.isfinite(relative_tolerance) or relative_tolerance <= 0:
        raise ValueError('relative_tolerance must be a positive finite number')
    if type(max_boxes) is not int or max_boxes < 1:
        raise ValueError('max_boxes must be a positive integer')
    numerator = (Fraction(0),)
    count = 0
    for values in numerators:
        p = polynomial(values)
        numerator = add(numerator, multiply(p, p))
        count += 1
    if not count:
        raise ValueError('at least one numerator is required')
    den = polynomial(denominator)
    factor = (1+Fraction(relative_tolerance))**2
    heap = []
    best, parameter = Fraction(0), Fraction(0)
    boxes = 0

    def push(n, d, squared_denominator, lo, hi):
        nonlocal best, parameter, boxes
        nl, _ = split(n)
        dl, _ = split(d)
        for x, y, t in ((n[0], d[0], lo), (nl[-1], dl[-1], (lo+hi)/2), (n[-1], d[-1], hi)):
            if y <= 0:
                raise ValueError('rational denominator is not strictly positive')
            value = x/(y*y)
            if value > best:
                best, parameter = value, t
        upper = max(a/b for a, b in zip(n, squared_denominator)) if min(squared_denominator) > 0 else None
        boxes += 1
        heapq.heappush(heap, (0 if upper is None else 1, -upper if upper is not None else Fraction(0),
                              boxes, n, d, squared_denominator, lo, hi))

    squared_denominator = multiply(den, den)
    degree = max(len(numerator), len(squared_denominator))-1
    push(bernstein(numerator, degree), bernstein(den), bernstein(squared_denominator, degree), Fraction(0), Fraction(1))
    while True:
        finite_upper, negative_upper, _, n, d, squared_denominator, lo, hi = heap[0]
        if finite_upper and -negative_upper <= best*factor:
            lower = _sqrt_bound(best, False)
            upper = _sqrt_bound(-negative_upper, True)
            target = Fraction(lower)*(1+Fraction(relative_tolerance))
            if Fraction(upper) <= target:
                return dict(status='PASS', lower_bound=lower, upper_bound=upper,
                            parameter=float(parameter), parameter_fraction=[parameter.numerator, parameter.denominator],
                            boxes=boxes, relative_tolerance=relative_tolerance,
                            scope='exact supplied rational polynomials; not a discretization error bound')
            if -negative_upper == best and Fraction(_sqrt_bound(best, True)) > target:
                raise ValueError('rational maximum UNVERIFIED: requested tolerance exceeds output precision')
            # Outward rounding alone can cross the requested gap; subdivide
            # further when a tighter float bracket is still representable.
        if boxes+2 > max_boxes:
            raise ValueError('rational maximum UNVERIFIED: subdivision budget exhausted')
        heapq.heappop(heap)
        nl, nr = split(n); dl, dr = split(d)
        sl, sr = split(squared_denominator)
        middle = (lo+hi)/2
        push(nl, dl, sl, lo, middle)
        push(nr, dr, sr, middle, hi)
