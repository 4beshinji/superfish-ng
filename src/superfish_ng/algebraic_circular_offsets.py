# SPDX-License-Identifier: Apache-2.0
"""Finite circular/straight offsets with exact stored binary rotation norms."""
from fractions import Fraction as F

from .certified_arcs import _arc_membership
from .conics import EllipseArc, LineSegment, rotation_cos_sin
from .quadratic_radicals import RadicalTower


def _sum(tower, values):
    result = tower.number(0)
    for value in values:
        result = tower.add(result, value)
    return result


def _dot(tower, vector, rational):
    return _sum(tower, (tower.scale(x, y) for x, y in zip(vector, rational)))


def _point(tower, origin, direction, parameter):
    return tuple(tower.add(x, tower.scale(parameter, y)) for x, y in zip(origin, direction))


def _models(tower, curves, distances):
    models = []
    for curve, distance in zip(curves, distances):
        if isinstance(curve, EllipseArc):
            c, s = map(F, rotation_cos_sin(curve.rotation_rad))
            length = tower.square_root(tower.number(c*c+s*s))
            rho = tower.subtract(tower.scale(length, F(curve.semiaxes_m[0])),
                                 tower.number(F(distance)*(1 if curve.sweep_rad > 0 else -1)))
            models.append(dict(center=tuple(map(F, curve.center_zr_m)), rotation=(c, s),
                               rho=rho, denominator=tower.multiply(rho, length),
                               radius_squared=tower.multiply(rho, rho)))
        else:
            start, end = tuple(map(F, curve.start_zr_m)), tuple(map(F, curve.end_zr_m))
            delta = tuple(b-a for a, b in zip(start, end))
            squared = sum(x*x for x in delta)
            length = tower.square_root(tower.number(squared))
            amount = tower.scale(length, F(distance)/squared)
            origin = _point(tower, tuple(map(tower.number, start)), (-delta[1], delta[0]), amount)
            models.append(dict(origin=origin, delta=delta, squared=squared))
    return models


def _result(tower, classification, count, infinite, *, evidence, complete=True):
    evidence = dict(evidence, radicands=tuple(tower.radicands))
    return dict(classification=classification, centers=count, infinite=infinite, complete=complete,
                evidence=evidence, reason='all algebraic supports and finite memberships classified' if complete
                else 'algebraic supports proved; finite arc membership remains unresolved')


def _parallel(tower, models, domains):
    first, second = models
    delta = tuple(tower.subtract(b, a) for a, b in zip(first['origin'], second['origin']))
    separation = _dot(tower, delta, (-first['delta'][1], first['delta'][0]))
    evidence = dict(identity='parallel straight offset supports', separation=separation,
                    separation_sign=tower.sign(separation))
    if tower.sign(separation):
        return _result(tower, 'DISJOINT', 0, False, evidence=evidence)
    shift = tower.scale(_dot(tower, delta, first['delta']), 1/first['squared'])
    scale = sum(a*b for a, b in zip(first['delta'], second['delta']))/first['squared']
    mapped = [tower.add(shift, tower.number(scale*x)) for x in domains[1]]
    if scale < 0:
        mapped.reverse()
    low, high = map(tower.number, domains[0])
    if tower.sign(tower.subtract(mapped[0], low)) > 0:
        low = mapped[0]
    if tower.sign(tower.subtract(mapped[1], high)) < 0:
        high = mapped[1]
    sign = tower.sign(tower.subtract(high, low))
    evidence.update(first_fraction_overlap=(low, high), overlap_sign=sign, shift=shift, scale=scale)
    classification = 'DISJOINT' if sign < 0 else 'SHARED_PARAMETER_ENDPOINT' if sign == 0 else 'INFINITE_PARAMETER_PAIRS'
    return _result(tower, classification, 0 if sign < 0 else 1 if sign == 0 else None,
                   sign > 0, evidence=evidence)


def _membership(tower, curve, model, point, domain, roots, controls):
    if isinstance(curve, LineSegment):
        delta = tuple(tower.subtract(a, b) for a, b in zip(point, model['origin']))
        fraction = tower.scale(_dot(tower, delta, model['delta']), 1/model['squared'])
        signs = [tower.sign(tower.subtract(fraction, tower.number(endpoint))) for endpoint in domain]
        status = ('EXTERIOR' if signs[0] < 0 or signs[1] > 0 else
                  'START' if signs[0] == 0 else 'END' if signs[1] == 0 else 'INTERIOR')
        return dict(status=status, fraction_coefficients=fraction, endpoint_difference_signs=signs,
                    fraction_bounds=tower.bounds(fraction, roots))
    if tower.sign(model['rho']) == 0:
        return dict(status='COLLAPSED', fraction_interval=domain)
    delta = tuple(tower.subtract(a, tower.number(b)) for a, b in zip(point, model['center']))
    c, s = model['rotation']
    coordinates = tuple(tower.ratio_bounds(_dot(tower, delta, axis), model['denominator'], roots)
                        for axis in ((c, s), (-s, c)))
    endpoints = tuple(F(curve.start_rad)+F(curve.sweep_rad)*t for t in domain)
    return _arc_membership(curve, coordinates, parameter_endpoints=endpoints, **controls)


def classify_algebraic_circular_offsets(curves, distances, domains, *, endpoint_width, max_series_terms):
    """Inputs are validated by the public classifier; unsupported conics return None."""
    if not all(isinstance(c, LineSegment) or isinstance(c, EllipseArc) and c.semiaxes_m[0] == c.semiaxes_m[1]
               for c in curves):
        return None
    tower = RadicalTower()
    models = _models(tower, curves, distances)
    domains = [tuple(map(F, domain)) for domain in domains]
    circles = ['rho' in model for model in models]
    evidence = {}
    if all(circles):
        first, second = models
        delta = tuple(b-a for a, b in zip(first['center'], second['center']))
        squared = sum(x*x for x in delta)
        difference = tower.subtract(first['radius_squared'], second['radius_squared'])
        if squared == 0:
            # Equal noncollapsed support and periodic membership belong to the
            # preceding coincident-arc classifier, including its unknowns.
            if tower.sign(difference) == 0:
                return None
            return _result(tower, 'DISJOINT', 0, False,
                           evidence=dict(identity='concentric unequal squared radii', difference=difference,
                                         difference_sign=tower.sign(difference)))
        alpha = tower.scale(tower.add(difference, tower.number(squared)), 1/(2*squared))
        base = _point(tower, tuple(map(tower.number, first['center'])), delta, alpha)
        radicand = tower.subtract(tower.scale(first['radius_squared'], 1/squared), tower.multiply(alpha, alpha))
        direction = (-delta[1], delta[0])
        evidence['identity'] = 'two circular supports with exact binary rotations and signed distances'
    elif any(circles):
        circle, line = (models[0], models[1]) if circles[0] else (models[1], models[0])
        delta = tuple(tower.subtract(tower.number(a), b) for a, b in zip(circle['center'], line['origin']))
        projection = tower.scale(_dot(tower, delta, line['delta']), 1/line['squared'])
        base = _point(tower, line['origin'], line['delta'], projection)
        gap = tuple(tower.subtract(a, tower.number(b)) for a, b in zip(base, circle['center']))
        gap_squared = _sum(tower, (tower.multiply(x, x) for x in gap))
        radicand = tower.scale(tower.subtract(circle['radius_squared'], gap_squared), 1/line['squared'])
        direction = line['delta']
        evidence['identity'] = 'circular and straight supports with exact binary rotation and line length'
    else:
        first, second = models
        determinant = first['delta'][0]*second['delta'][1]-first['delta'][1]*second['delta'][0]
        if determinant == 0:
            return _parallel(tower, models, domains)
        delta = tuple(tower.subtract(b, a) for a, b in zip(first['origin'], second['origin']))
        fraction = tower.scale(_dot(tower, delta, (second['delta'][1], -second['delta'][0])), 1/determinant)
        base = _point(tower, first['origin'], first['delta'], fraction)
        direction, radicand = (F(0), F(0)), tower.number(0)
        evidence['identity'] = 'nonparallel straight supports with exact line lengths'
    sign = tower.sign(radicand)
    evidence.update(radicand=radicand, discriminant_sign=sign)
    if sign < 0:
        return _result(tower, 'DISJOINT', 0, False, evidence=evidence)
    root = tower.square_root(radicand)
    points = [_point(tower, base, direction, tower.scale(root, side)) for side in ((-1, 1) if sign > 0 else (1,))]
    controls = dict(endpoint_width=endpoint_width, max_series_terms=max_series_terms)
    # Refine algebraic bounds only. Endpoint Taylor budgets remain explicit.
    for refinement in range(3):
        roots = tower.root_bounds(F(endpoint_width)/2**(8+64*refinement))
        records = []
        for point in points:
            memberships = []
            for curve, model, domain in zip(curves, models, domains):
                try:
                    memberships.append(_membership(tower, curve, model, point, domain, roots, controls))
                except ValueError as error:
                    memberships.append(dict(status='UNVERIFIED', reason=str(error)))
            statuses = [row['status'] for row in memberships]
            exists = False if 'EXTERIOR' in statuses else None if 'UNVERIFIED' in statuses else True
            records.append(dict(center_coefficients=point, center_box_zr_m=tuple(tower.bounds(x, roots) for x in point),
                                membership=memberships, parameter_pair_in_domain=exists))
        if all(row['parameter_pair_in_domain'] is not None for row in records):
            break
    complete = all(row['parameter_pair_in_domain'] is not None for row in records)
    count = sum(row['parameter_pair_in_domain'] is True for row in records)
    collapsed = any('rho' in model and tower.sign(model['rho']) == 0 for model in models)
    classification = ('UNVERIFIED' if not complete else 'DISJOINT' if count == 0 else
                      'INFINITE_PARAMETER_PAIRS' if collapsed else 'SINGLE_TANGENCY' if sign == 0 and any(circles)
                      else 'FINITE_CENTERS')
    evidence.update(root_bounds=roots, algebraic_refinement=refinement, supporting_center_count=len(points),
                    candidates=records, certified_in_domain_count=count)
    return _result(tower, classification, count if complete else None,
                   (bool(count) if complete else None) if collapsed else False,
                   evidence=evidence, complete=complete)
