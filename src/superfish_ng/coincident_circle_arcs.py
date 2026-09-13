# SPDX-License-Identifier: Apache-2.0
"""Exact finite-angle intersections for coincident circular offset supports."""
from fractions import Fraction as F


def _atan_reciprocal_bounds(denominator, width, max_terms):
    x = F(1, denominator); power = x; total = F(0)
    for index in range(max_terms):
        total += (-1 if index % 2 else 1) * power / (2 * index + 1)
        following = power * x * x / (2 * index + 3)
        bounds = (total, total + following) if index % 2 else (total - following, total)
        if following <= width: return bounds
        power *= x * x
    raise ValueError('coincident-circle pi enclosure series budget exhausted')


def pi_bounds(width, max_terms):
    """Enclose pi using 16 atan(1/5) - 4 atan(1/239) and alternating remainders.

    tan(4 atan(1/5)) = 120/119, so subtracting atan(1/239) gives
    tangent 1 in the first quadrant. All sums and tail bounds are rational.
    """
    if type(width) not in (int, float, F) or type(max_terms) is not int or max_terms <= 0:
        raise ValueError('positive rational width and integer series budget required')
    width = F(width)
    if width <= 0: raise ValueError('pi enclosure width must be positive')
    a = _atan_reciprocal_bounds(5, width / 20, max_terms)
    b = _atan_reciprocal_bounds(239, width / 20, max_terms)
    return 16 * a[0] - 4 * b[1], 16 * a[1] - 4 * b[0]


def _multiply(value, bounds):
    return tuple(sorted(value * end for end in bounds))


def coincident_circle_intervals(curves, models, domains, *, endpoint_width, max_series_terms):
    """Return an exhaustive periodic interval classification, or None for other phases.

    The caller already proved the same noncollapsed center and support radius.
    Distinct nonzero rational angles cannot differ by a nonzero rational multiple
    of pi; endpoint equality is accepted only for the exact zero phase shift.
    """
    directions = [tuple((1 if m['signed_radius'] > 0 else -1) * value / m['rotation_length']
                        for value in m['rotation']) for m in models]
    first, second = directions
    cosine = sum(a * b for a, b in zip(first, second))
    sine = first[0] * second[1] - first[1] * second[0]
    quarter_turn = {(F(1), F(0)): 0, (F(0), F(1)): 1,
                    (F(-1), F(0)): 2, (F(0), F(-1)): -1}.get((cosine, sine))
    if quarter_turn is None: return None
    ranges = [tuple(sorted(F(curve.start_rad) + F(curve.sweep_rad) * t for t in domain))
              for curve, domain in zip(curves, domains)]
    a, b = ranges
    pi = pi_bounds(F(endpoint_width) / 64, max_series_terms)
    # a-b = (quarter_turn+4*k)*pi/2. Interval division encloses every possible k.
    difference = a[0] - b[1], a[1] - b[0]
    quotients = [2 * value / p for value in difference for p in pi]
    low = (min(quotients) - quarter_turn) / 4
    high = (max(quotients) - quarter_turn) / 4
    first_period = -((-low.numerator) // low.denominator)
    last_period = high.numerator // high.denominator
    records = []
    for period in range(first_period, last_period + 1):
        multiplier = F(quarter_turn + 4 * period, 2)
        shift = _multiply(multiplier, pi)
        lower = b[0] + shift[0], b[0] + shift[1]
        upper = b[1] + shift[0], b[1] + shift[1]
        start = max(a[0], lower[0]), max(a[0], lower[1])
        end = min(a[1], upper[0]), min(a[1], upper[1])
        if start[0] > end[1]: kind = 'DISJOINT'
        elif start[1] < end[0]: kind = 'POSITIVE_INTERVAL'
        elif multiplier == 0 and start[0] == start[1] == end[0] == end[1]: kind = 'SHARED_ENDPOINT'
        else: kind = 'UNVERIFIED'
        records.append(dict(period=period, pi_multiplier=multiplier, shift_bounds=shift,
                            overlap_start_bounds=start, overlap_end_bounds=end, classification=kind))
    positive = [row for row in records if row['classification'] == 'POSITIVE_INTERVAL']
    endpoints = [row for row in records if row['classification'] == 'SHARED_ENDPOINT']
    unknown = [row for row in records if row['classification'] == 'UNVERIFIED']
    complete = not unknown
    if positive: classification, centers, infinite = 'INFINITE_PARAMETER_PAIRS', None, True
    elif unknown: classification, centers, infinite = 'COINCIDENT_SUPPORTING_CIRCLES', None, None
    elif endpoints: classification, centers, infinite = 'SHARED_PARAMETER_ENDPOINT', len(endpoints), False
    else: classification, centers, infinite = 'DISJOINT', 0, False
    return dict(classification=classification, complete=complete, centers=centers, infinite=infinite,
                evidence=dict(angular_ranges=ranges, relative_quarter_turn=quarter_turn,
                              pi_bounds=pi, period_range=(first_period, last_period), periodic_intersections=records,
                              positive_components=len(positive), isolated_endpoints=len(endpoints)),
                reason='all possible periodic interval intersections classified' if complete
                       else 'coincident supports proved; some periodic interval endpoints remain unresolved')
