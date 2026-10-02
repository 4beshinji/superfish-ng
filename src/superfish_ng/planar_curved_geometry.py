# SPDX-License-Identifier: Apache-2.0
"""Cartesian quadratic maps and conservative whole-mesh edge checks.

All determinants use exact rational coefficients of the supplied binary64
nodes. No radial coordinate, axis tag or electromagnetic formulation occurs
here. Node order is vertices 0/1/2, then reference midpoints 01/12/20.
"""
from dataclasses import dataclass
from fractions import Fraction
import numpy as np
from .high_order import basis_p2

_GRADIENTS = np.array([[-1., -1.], [1., 0.], [0., 1.]])


def immutable_array(values, dtype):
    array = np.asarray(values, dtype=dtype)
    return np.frombuffer(array.tobytes(), dtype=array.dtype).reshape(array.shape)


def strict_array(values, columns, label, *, indices=False):
    try:
        raw = np.asarray(values, dtype=object)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{label} requires a rectangular array') from exc
    if raw.ndim != 2 or raw.shape[1] != columns or not len(raw):
        raise ValueError(f'{label} requires nonempty N by {columns} values')
    for value in raw.flat:
        valid = isinstance(value, (int, np.integer)) if indices else isinstance(value, (int, float, np.integer, np.floating))
        if isinstance(value, (bool, np.bool_)) or not valid:
            raise ValueError(f'{label} requires integers' if indices else f'{label} requires finite real numbers, without bool')
        if indices and not 0 <= int(value) <= np.iinfo(np.int64).max:
            raise ValueError(f'{label} index is outside the nonnegative int64 range')
    try:
        result = immutable_array(raw.tolist(), np.int64 if indices else float)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f'{label} exceeds finite numeric range') from exc
    if not np.isfinite(result).all():
        raise ValueError(f'{label} requires finite values')
    return result


def _product_linear(a, b):
    return (a[0]*b[0], a[0]*b[1]+a[1]*b[0], a[0]*b[2]+a[2]*b[0],
            a[1]*b[1], a[1]*b[2]+a[2]*b[1], a[2]*b[2])


def _exact_minimum(coefficients):
    """Exact minimum of a quadratic on the closed unit triangle."""
    c, a, b, d, e, f = coefficients
    zero, one = Fraction(0), Fraction(1)
    candidates = [(zero, zero), (one, zero), (zero, one)]
    for x, y, u, v in ((zero, zero, one, zero), (zero, zero, zero, one), (one, zero, -one, one)):
        linear = a*u+b*v+2*d*x*u+e*(x*v+y*u)+2*f*y*v
        square = d*u*u+e*u*v+f*v*v
        if square > 0:
            t = -linear/(2*square)
            if 0 < t < 1:
                candidates.append((x+t*u, y+t*v))
    determinant = 4*d*f-e*e
    if d > 0 and determinant > 0:
        x, y = (e*b-2*f*a)/determinant, (e*a-2*d*b)/determinant
        if x > 0 and y > 0 and x+y < 1:
            candidates.append((x, y))
    return min((c+a*x+b*y+d*x*x+e*x*y+f*y*y, (x, y)) for x, y in candidates)


def _map_coefficients(points):
    p = [[Fraction(float(value)) for value in row] for row in points]
    rel = [[p[i][j]-p[0][j] for j in range(2)] for i in range(6)]
    return tuple(tuple(values) for values in (
        p[0], [-rel[1][j]+4*rel[3][j] for j in range(2)],
        [-rel[2][j]+4*rel[5][j] for j in range(2)],
        [2*rel[1][j]-4*rel[3][j] for j in range(2)],
        [4*(rel[4][j]-rel[3][j]-rel[5][j]) for j in range(2)],
        [2*rel[2][j]-4*rel[5][j] for j in range(2)]))


@dataclass(frozen=True, eq=False)
class PlanarQuadraticTriangle:
    points_xy_m: object

    def __post_init__(self):
        points = strict_array(self.points_xy_m, 2, 'planar quadratic triangle')
        if points.shape != (6, 2):
            raise ValueError('planar quadratic triangle requires exactly six xy nodes')
        with np.errstate(over='ignore', invalid='ignore'):
            scale = float(np.max(np.ptp(points, axis=0)))
        if not np.isfinite(scale) or scale <= 0 or not np.isfinite(scale*scale) or scale*scale < np.finfo(float).tiny:
            raise ValueError('planar quadratic triangle scale exceeds finite SI resolution')
        coefficients = _map_coefficients(points)
        dx = [coefficients[1], tuple(2*v for v in coefficients[3]), coefficients[4]]
        dy = [coefficients[2], coefficients[4], tuple(2*v for v in coefficients[5])]
        first = _product_linear([v[0] for v in dx], [v[1] for v in dy])
        second = _product_linear([v[1] for v in dx], [v[0] for v in dy])
        determinant = tuple(a-b for a, b in zip(first, second))
        minimum, location = _exact_minimum(determinant)
        norm = np.array([float(value/Fraction(scale)**2) for value in determinant])
        padding = 512*np.finfo(float).eps*max(1., float(np.sum(abs(norm))))*scale*scale
        # Absolute coordinate arithmetic must also resolve the local feature.
        coordinate_error = 8*np.finfo(float).eps*float(np.max(abs(points))) / scale
        if not np.isfinite(norm).all() or coordinate_error > 1e-8:
            raise ValueError('planar quadratic Jacobian UNVERIFIED: local coordinate resolution')
        if minimum <= 0 or float(minimum) <= padding:
            raise ValueError('planar quadratic Jacobian nonpositive or UNVERIFIED over the whole reference triangle')
        c, a, b, d, e, f = determinant
        area = c/2+(a+b)/6+(d+f)/12+e/24
        object.__setattr__(self, 'points_xy_m', points)
        object.__setattr__(self, 'exact_determinant_coefficients', determinant)
        object.__setattr__(self, 'exact_area_m2', area)
        object.__setattr__(self, 'area_m2', float(area))
        object.__setattr__(self, 'determinant_lower_bound_m2', float(minimum)-padding)
        object.__setattr__(self, 'minimum_reference_point', tuple(float(v) for v in location))
        object.__setattr__(self, 'roundoff_padding_m2', padding)

    def evaluate(self, reference_points):
        ref = strict_array(reference_points, 2, 'planar reference points')
        if np.any(ref < 0) or np.any(ref.sum(axis=1) > 1):
            raise ValueError('planar reference points must lie in the closed unit triangle')
        basis = [basis_p2([1-x-y, x, y], _GRADIENTS) for x, y in ref]
        values = np.array([pair[0] for pair in basis])
        gradients = np.array([pair[1] for pair in basis])
        relative = self.points_xy_m-self.points_xy_m[0]
        jacobian = np.einsum('ia,qib->qab', relative, gradients)
        determinant = np.linalg.det(jacobian)
        if not np.isfinite(jacobian).all() or np.any(determinant <= 0):
            raise ValueError('planar mapped Jacobian arithmetic is nonpositive or unresolved')
        physical = np.einsum('qia,qab->qib', gradients, np.linalg.inv(jacobian))
        return dict(points_xy_m=self.points_xy_m[0]+values@relative,
                    jacobian=jacobian, determinant_m2=determinant,
                    basis_values=values, basis_gradients=physical)


@dataclass(frozen=True, eq=False)
class PlanarQuadraticEdge:
    """Coordinate-neutral xy Bezier controls, ordered start/control/end."""
    control_points: object

    def __post_init__(self):
        controls = strict_array(self.control_points, 2, 'planar quadratic edge controls')
        if controls.shape != (3, 2):
            raise ValueError('planar quadratic edge requires exactly three xy controls')
        object.__setattr__(self, 'control_points', controls)

    @classmethod
    def from_nodes(cls, start, end, midpoint):
        start, end, midpoint = map(np.asarray, (start, end, midpoint))
        return cls(immutable_array([start, start+2*(midpoint-start)-(end-start)/2, end], float))

    def reversed(self):
        return PlanarQuadraticEdge(self.control_points[::-1])

    def bounds(self, padding):
        return self.control_points.min(axis=0)-padding, self.control_points.max(axis=0)+padding

    def derivatives(self):
        return 2*np.diff(self.control_points, axis=0)

    def split(self, t=.5):
        p = self.control_points
        a, b = p[0]+t*(p[1]-p[0]), p[1]+t*(p[2]-p[1])
        middle = a+t*(b-a)
        return PlanarQuadraticEdge(np.array([p[0], a, middle])), PlanarQuadraticEdge(np.array([middle, b, p[2]]))


class GeometryBudget:
    def __init__(self, maximum):
        self.maximum = maximum
        self.checked = 0

    def consume(self, pair):
        if self.checked >= self.maximum:
            raise ValueError(f'planar geometry UNVERIFIED: max_geometry_boxes={self.maximum} exhausted after {self.checked} checks, edge pair {pair}; increase the explicit budget or repair geometry')
        self.checked += 1


def _separated(first, second, padding, budget, pair):
    pending = [(first, second)]
    while pending:
        budget.consume(pair)
        a, b = pending.pop()
        alo, ahi = a.bounds(padding)
        blo, bhi = b.bounds(padding)
        if np.any(ahi < blo) or np.any(bhi < alo):
            continue
        sa = np.array([a.control_points[0], a.split()[0].control_points[-1], a.control_points[-1]])
        sb = np.array([b.control_points[0], b.split()[0].control_points[-1], b.control_points[-1]])
        if np.min(np.linalg.norm(sa[:, None]-sb, axis=2)) <= padding:
            raise ValueError(f'planar geometry contact/intersection or UNVERIFIED gap below resolution: edge pair {pair}')
        if max(np.max(ahi-alo), np.max(bhi-blo)) <= 4*padding:
            raise ValueError(f'planar geometry UNVERIFIED intersection: edge pair {pair}')
        if np.max(ahi-alo) >= np.max(bhi-blo):
            left, right = a.split()
            pending.extend([(left, b), (right, b)])
        else:
            left, right = b.split()
            pending.extend([(a, left), (a, right)])


def _adjacent(first, second, padding, budget, pair):
    u, v = first.derivatives()[-1], second.derivatives()[0]
    norms = np.linalg.norm([u, v], axis=1)
    if np.any(norms <= padding):
        raise ValueError(f'planar geometry UNVERIFIED zero join tangent: edge pair {pair}')
    direction = u/norms[0]+v/norms[1]
    for depth in range(33):
        budget.consume(pair)
        before, tail = first.split(1-2.**(-depth))
        head, after = second.split(2.**(-depth))
        if min(np.min(tail.derivatives()@direction), np.min(head.derivatives()@direction)) > padding:
            break
    else:
        raise ValueError(f'planar geometry UNVERIFIED shared endpoint neighborhood: edge pair {pair}')
    if depth:
        _separated(before, second, padding, budget, pair)
        _separated(tail, after, padding, budget, pair)


def check_planar_edges(points, incidence, maximum):
    """Every unique mesh edge, with one total budget for broad/narrow phases."""
    scale = float(np.max(np.ptp(points, axis=0)))
    normalized = (points-points[0])/scale
    padding = 512*np.finfo(float).eps
    keys = sorted(incidence)
    edges = [PlanarQuadraticEdge.from_nodes(normalized[a], normalized[b], normalized[incidence[(a, b)][0][3]]) for a, b in keys]
    for i, edge in enumerate(edges):
        derivative = edge.derivatives()
        norms = np.linalg.norm(derivative, axis=1)
        if np.any(norms <= padding):
            raise ValueError(f'planar geometry UNVERIFIED zero edge tangent: {keys[i]}')
        direction = np.sum(derivative/norms[:, None], axis=0)
        if np.min(derivative@direction) <= padding:
            raise ValueError(f'planar geometry cusp/reversal or UNVERIFIED: {keys[i]}')
    bounds = np.array([edge.bounds(padding) for edge in edges])
    budget = GeometryBudget(maximum)
    active = []
    candidates = 0
    for i in np.argsort(bounds[:, 0, 0], kind='stable'):
        active = [j for j in active if bounds[j, 1, 0] >= bounds[i, 0, 0]]
        for j in active:
            pair = (keys[j], keys[i])
            budget.consume(pair)
            if bounds[i, 1, 1] < bounds[j, 0, 1] or bounds[j, 1, 1] < bounds[i, 0, 1]:
                continue
            candidates += 1
            shared = set(keys[i]) & set(keys[j])
            if shared:
                node = next(iter(shared))
                first = edges[j] if keys[j][1] == node else edges[j].reversed()
                second = edges[i] if keys[i][0] == node else edges[i].reversed()
                _adjacent(first, second, padding, budget, pair)
            else:
                _separated(edges[j], edges[i], padding, budget, pair)
        active.append(int(i))
    return dict(status='PASS', edges=len(edges), overlapping_box_pairs=candidates,
                boxes_checked=budget.checked, max_geometry_boxes=maximum,
                roundoff_padding_m=padding*scale, scope='all unique xy quadratic edges')


def exact_boundary_area(points, boundary):
    """Green integral of the supplied oriented quadratic edges, exactly."""
    total = Fraction(0)
    def cross(a, b):
        return a[0]*b[1]-a[1]*b[0]
    for start, end, mid in boundary:
        p, q, r = [[Fraction(float(value)) for value in points[index]] for index in (start, end, mid)]
        a = [4*r[j]-3*p[j]-q[j] for j in range(2)]
        b = [2*p[j]+2*q[j]-4*r[j] for j in range(2)]
        total += (cross(p, a)+cross(p, b)+cross(a, b)/3)/2
    return total
