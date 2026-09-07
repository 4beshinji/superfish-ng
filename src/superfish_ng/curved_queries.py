# SPDX-License-Identifier: Apache-2.0
"""Boundary sampling and radial intersections on the actual quadratic geometry."""
import numpy as np
from .quadratic_boundary import QuadraticEdge


def boundary_polylines(space, samples=17):
    if type(samples) is not int or samples < 2:
        raise ValueError('boundary samples must be integer >= 2')
    t = np.linspace(0, 1, samples)
    shape = np.array([(1-t)*(1-2*t), t*(2*t-1), 4*t*(1-t)]).T
    return np.einsum('qi,eia->eqa', shape, space.geometry.points_rz_m[space.geometry.boundary_nodes])


def quadratic_radial_extent(points, boundary_nodes, z_m):
    """Outermost intersection; gaps are subsequently masked by the field sampler.

    Split each quadratic at its axial extremum, then bisect the monotone
    intervals. This includes tangencies and avoids unstable quadratic roots.
    A boundary in the probe plane contributes its radial extremum too.
    """
    if type(z_m) not in (int, float) or not np.isfinite(z_m):
        raise ValueError('probe z must be a finite number')
    radii = []
    for start, end, mid in points[boundary_nodes]:
        p = QuadraticEdge.from_nodes(start, end, mid).control_points
        def at(t):
            return (1-t)**2*p[0]+2*t*(1-t)*p[1]+t*t*p[2]
        delta = np.diff(p, axis=0)
        curvature = delta[1]-delta[0]
        if np.all(p[:, 1] == z_m):
            ts = [0., 1.]
            if curvature[0] != 0:
                t = -delta[0, 0]/curvature[0]
                if 0 < t < 1:
                    ts.append(t)
            radii.extend(at(t)[0] for t in ts)
            continue
        cuts = [0., 1.]
        if curvature[1] != 0:
            t = -delta[0, 1]/curvature[1]
            if 0 < t < 1:
                cuts.insert(1, t)
        for lo, hi in zip(cuts[:-1], cuts[1:]):
            za, zb = at(lo)[1], at(hi)[1]
            if not min(za, zb) <= z_m <= max(za, zb):
                continue
            if z_m == za:
                root = lo
            elif z_m == zb:
                root = hi
            else:
                increasing = zb > za
                for _ in range(64):
                    middle = (lo+hi)/2
                    if middle == lo or middle == hi:
                        break
                    if (at(middle)[1] < z_m) == increasing:
                        lo = middle
                    else:
                        hi = middle
                root = (lo+hi)/2
            radii.append(at(root)[0])
    if not radii or max(radii) <= 0:
        raise ValueError('radial probe does not intersect the cavity')
    return float(max(radii))
