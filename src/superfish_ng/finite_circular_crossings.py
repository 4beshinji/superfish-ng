# SPDX-License-Identifier: Apache-2.0
"""Exhaustive crossings of rational circular and straight offset supports.

Each candidate is base + coefficient * sqrt(radicand), with exact rational
coefficients. Closed finite-domain membership is proved separately. This
diagnostic does not produce fillets or modify the crossing-search algorithm.
"""
from fractions import Fraction as F

from .certified_arcs import _arc_membership
from .conics import LineSegment
from .offset_degeneracies import _circle, _line, _dot, _sub, _cross, _sqrt_exact, _parameters
from .same_conic_offset_intersections import _sqrt_interval


def _affine_bounds(base, coefficient, root):
    return tuple(sorted(base + coefficient * value for value in root))


def _local_coefficients(model, base, coefficient):
    """Transform the algebraic expression before enclosing it (no cancellation)."""
    if 'origin' in model:
        squared = _dot(model['delta'], model['delta'])
        return ((_dot(_sub(base, model['origin']), model['delta']) / squared,
                 _dot(coefficient, model['delta']) / squared),)
    c, s = model['rotation']
    divisor = model['signed_radius'] * model['rotation_length']
    delta = _sub(base, model['center'])
    return tuple((_dot(axis, delta) / divisor, _dot(axis, coefficient) / divisor)
                 for axis in ((c, s), (-s, c)))


def _membership(curve, coordinates, root, domain, controls):
    bounds = tuple(_affine_bounds(a, b, root) for a, b in coordinates)
    if isinstance(curve, LineSegment):
        low, high = bounds[0]
        start, end = domain
        if high < start or low > end:
            status = 'EXTERIOR'
        elif low == high == start:
            status = 'START'
        elif low == high == end:
            status = 'END'
        elif start < low and high < end:
            status = 'INTERIOR'
        else:
            status = 'UNVERIFIED'
        return dict(status=status, fraction_bounds=(low, high))
    start, span = _parameters(curve)
    return _arc_membership(curve, bounds,
                           parameter_endpoints=tuple(start + span * t for t in domain),
                           **controls)


def _candidate(curves, models, domains, base, coefficient, radicand, controls):
    local = [_local_coefficients(model, base, coefficient) for model in models]
    # Bound local coordinates/fractions independently of the physical scale.
    sensitivity = max(F(1), *(abs(b) for coordinates in local for _, b in coordinates))
    width = F(controls['endpoint_width']) / (64 * sensitivity)
    exact = _sqrt_exact(radicand)
    root = (exact, exact) if exact is not None else _sqrt_interval(radicand, width)
    memberships = []
    for curve, coordinates, domain in zip(curves, local, domains):
        try:
            memberships.append(_membership(curve, coordinates, root, domain, controls))
        except ValueError as error:
            memberships.append(dict(status='UNVERIFIED', reason=str(error)))
    statuses = [row['status'] for row in memberships]
    exists = False if 'EXTERIOR' in statuses else None if 'UNVERIFIED' in statuses else True
    return dict(base_zr_m=base, coefficient_zr_m=coefficient, radicand=radicand,
                root_bounds=root,
                center_box_zr_m=tuple(_affine_bounds(a, b, root) for a, b in zip(base, coefficient)),
                membership=memberships, parameter_pair_in_domain=exists)


def classify_finite_circular_crossings(curves, distances, domains, *, endpoint_width, max_series_terms):
    """Caller validates inputs; None means these supports are not handled.

Coincidence, collapse, tangency and supporting disjointness use the preceding
classifier. A positive radicand proves two distinct centers before membership.
"""
    circles = [_circle(curve, F(distance)) for curve, distance in zip(curves, distances)]
    lines = [_line(curve, F(distance)) for curve, distance in zip(curves, distances)]
    models = [line or circle for line, circle in zip(lines, circles)]
    if not all(models) or any(circle and circle['radius'] == 0 for circle in circles):
        return None
    domains = [tuple(map(F, domain)) for domain in domains]
    controls = dict(endpoint_width=endpoint_width, max_series_terms=max_series_terms)
    if all(circles):
        first, second = circles
        delta = _sub(second['center'], first['center'])
        squared = _dot(delta, delta)
        if squared == 0:
            return None
        alpha = (first['radius']**2 - second['radius']**2 + squared) / (2 * squared)
        radicand = first['radius']**2 / squared - alpha**2
        if radicand <= 0:
            return None
        base = tuple(a + alpha * b for a, b in zip(first['center'], delta))
        coefficient = (-delta[1], delta[0])
        identity = 'two distinct circular supports: radical axis and radius equation'
    elif any(circles):
        line = next(model for model in lines if model)
        circle = next(model for model in circles if model)
        delta = line['delta']
        squared = _dot(delta, delta)
        projection = _dot(_sub(circle['center'], line['origin']), delta) / squared
        base = tuple(a + projection * b for a, b in zip(line['origin'], delta))
        gap = _sub(base, circle['center'])
        radicand = (circle['radius']**2 - _dot(gap, gap)) / squared
        if radicand <= 0:
            return None
        coefficient = delta
        identity = 'straight and circular supports: perpendicular projection and radius equation'
    else:
        first, second = lines
        determinant = _cross(first['delta'], second['delta'])
        if determinant == 0:
            return None
        fraction = _cross(_sub(second['origin'], first['origin']), second['delta']) / determinant
        base = tuple(a + fraction * b for a, b in zip(first['origin'], first['delta']))
        coefficient, radicand = (F(0), F(0)), F(0)
        identity = 'nonparallel straight supports: exact two by two linear solve'
    signs = (-1, 1) if radicand > 0 else (1,)
    candidates = [_candidate(curves, models, domains, base,
                             tuple(sign * value for value in coefficient), radicand, controls)
                  for sign in signs]
    complete = all(row['parameter_pair_in_domain'] is not None for row in candidates)
    count = sum(row['parameter_pair_in_domain'] is True for row in candidates)
    classification = 'UNVERIFIED' if not complete else 'FINITE_CENTERS' if count else 'DISJOINT'
    return dict(classification=classification, complete=complete,
                centers=count if complete else None, infinite=False,
                evidence=dict(identity=identity, supporting_center_count=len(candidates),
                              candidates=candidates, certified_in_domain_count=count),
                reason='all supporting crossings and finite memberships classified' if complete
                else 'supporting crossings proved; some finite memberships unresolved')
