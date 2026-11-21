# SPDX-License-Identifier: Apache-2.0
"""Exact binary64 membership and checked inverse maps on curved xy cells.

Quadratic edge ray crossings use rational polynomial signs, including exact
boundary contact. Newton residual tolerance never admits an exterior point.
"""
from fractions import Fraction
import numpy as np
from .planar_curved import PlanarCurvedDomain
from .planar_curved_geometry import strict_array, _closed_reference_mask


def _value(poly, t):
    return poly[0]+t*(poly[1]+t*poly[2])


def _edge_polynomials(points):
    start, end, mid = [[Fraction(float(v)) for v in row] for row in points]
    return tuple((start[j], 4*mid[j]-3*start[j]-end[j], 2*start[j]+2*end[j]-4*mid[j]) for j in range(2))


def _range(poly):
    candidates = [_value(poly, Fraction(0)), _value(poly, Fraction(1))]
    if poly[2]:
        t = -poly[1]/(2*poly[2])
        if 0 < t < 1:
            candidates.append(_value(poly, t))
    return min(candidates), max(candidates)


def _touches(x, y):
    """Whether x(t)=y(t)=0 at some real t in [0,1], exactly."""
    if y[2]:
        factor = x[2]/y[2]
        intercept, slope = x[0]-factor*y[0], x[1]-factor*y[1]
        if slope:
            root = -intercept/slope
            return 0 <= root <= 1 and _value(y, root) == 0
        if intercept == 0:
            low, high = _range(y)
            return low <= 0 <= high
        return False
    if y[1]:
        root = -y[0]/y[1]
        return 0 <= root <= 1 and _value(x, root) == 0
    if y[0]:
        return False
    low, high = _range(x)
    return low <= 0 <= high


def _root_x_sign(x, y, start, end):
    """Sign of x at the unique y=0 crossing of a monotonic segment."""
    if not y[2]:
        value = _value(x, -y[0]/y[1])
    else:
        factor = x[2]/y[2]
        intercept, slope = x[0]-factor*y[0], x[1]-factor*y[1]
        if slope == 0:
            value = intercept
        else:
            zero = -intercept/slope
            if zero < start:
                comparison = 1
            elif zero > end:
                comparison = -1
            else:
                # y is strictly monotonic between its stationary cuts.
                increasing = _value(y, end) > _value(y, start)
                v = _value(y, zero)
                comparison = ((v < 0)-(v > 0)) * (1 if increasing else -1)
            value = slope*comparison
    return (value > 0)-(value < 0)


def _membership(edges, point):
    px, py = map(lambda v: Fraction(float(v)), point)
    winding = 0
    for xp, yp in edges:
        x = (xp[0]-px, xp[1], xp[2])
        y = (yp[0]-py, yp[1], yp[2])
        if _touches(x, y):
            return 'boundary'
        cuts = [Fraction(0), Fraction(1)]
        if y[2]:
            stationary = -y[1]/(2*y[2])
            if 0 < stationary < 1:
                cuts.insert(1, stationary)
        for start, end in zip(cuts, cuts[1:]):
            a, b = _value(y, start), _value(y, end)
            if a <= 0 < b:
                if _root_x_sign(x, y, start, end) > 0:
                    winding += 1
            elif b <= 0 < a:
                if _root_x_sign(x, y, start, end) > 0:
                    winding -= 1
    if winding not in (0, 1):
        raise ValueError('curved planar point membership UNVERIFIED: inconsistent winding')
    return 'inside' if winding else 'outside'


class PlanarCurvedLocator:
    def __init__(self, domain):
        if not isinstance(domain, PlanarCurvedDomain):
            raise ValueError('curved point location requires a validated PlanarCurvedDomain')
        self.domain = domain
        edges, lows, highs = [], [], []
        for nodes in domain.cell_nodes:
            points = domain.points_xy_m[nodes]
            edges.append(tuple(_edge_polynomials(points[[i, j, k]]) for i, j, k in ((0, 1, 3), (1, 2, 4), (2, 0, 5))))
            controls = [[Fraction(float(v)) for v in row] for row in points[:3]]
            for i, j, k in ((0, 1, 3), (1, 2, 4), (2, 0, 5)):
                controls.append([2*Fraction(float(points[k, a]))-(Fraction(float(points[i, a]))+Fraction(float(points[j, a])))/2 for a in range(2)])
            lows.append([np.nextafter(float(min(p[a] for p in controls)), -np.inf) for a in range(2)])
            highs.append([np.nextafter(float(max(p[a] for p in controls)), np.inf) for a in range(2)])
        self.edges = tuple(edges)
        self.low, self.high = np.array(lows), np.array(highs)

    def _inverse(self, cell, point):
        element = self.domain.elements[cell]
        reference_nodes = np.array([[0., 0.], [1., 0.], [0., 1.], [.5, 0.], [.5, .5], [0., .5]])
        matching = np.flatnonzero(np.all(element.points_xy_m == point, axis=1))
        if len(matching):
            return reference_nodes[matching[0]].copy()
        ref = np.array([1/3, 1/3])
        scale = float(np.max(np.ptp(element.points_xy_m, axis=0)))
        tolerance = 64*np.finfo(float).eps*max(scale, float(np.max(abs(element.points_xy_m))))
        for _ in range(100):
            mapped = element.evaluate([ref])
            residual = mapped['points_xy_m'][0]-point
            norm = float(np.linalg.norm(residual))
            if norm <= tolerance:
                return ref
            step = -np.linalg.solve(mapped['jacobian'][0], residual)
            fraction = 1.
            for coordinate, delta in zip(ref, step):
                if delta < 0:
                    fraction = min(fraction, .95*coordinate/(-delta))
            if step.sum() > 0:
                fraction = min(fraction, .95*(1-ref.sum())/step.sum())
            for _ in range(40):
                candidate = ref+fraction*step
                if not _closed_reference_mask(candidate[None, :])[0]:
                    fraction *= .5
                    continue
                trial = element.evaluate([candidate])['points_xy_m'][0]
                if np.linalg.norm(trial-point) < norm:
                    ref = candidate
                    break
                fraction *= .5
            else:
                break
        raise ValueError(f'curved planar inverse map UNVERIFIED in cell {cell}; use explicit cell/reference coordinates for a boundary probe')

    def locate(self, points_xy_m):
        points = strict_array(points_xy_m, 2, 'curved planar probe points')
        cells, refs = [], []
        for point in points:
            candidates = np.flatnonzero(np.all(point >= self.low, axis=1) & np.all(point <= self.high, axis=1))
            for cell in candidates:
                if _membership(self.edges[cell], point) == 'outside':
                    continue
                refs.append(self._inverse(int(cell), point))
                cells.append(int(cell))
                break
            else:
                raise ValueError('curved planar probe point is outside the original quadratic domain')
        return np.array(cells, dtype=np.int64), np.array(refs)
