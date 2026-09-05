# SPDX-License-Identifier: Apache-2.0
"""Evaluate P1 fields without smoothing, with explicit outside handling."""
from types import SimpleNamespace
import numpy as np
from scipy.spatial import cKDTree
from .constants import EPS0, TAU
from .mesh import element_geometry


class FieldSampler:
    def __init__(self, points, triangles, u, frequencies_hz):
        self.points, self.triangles = np.asarray(points), np.asarray(triangles)
        self.u, self.frequencies_hz = np.asarray(u), np.asarray(frequencies_hz)
        self.vertices, _, self.grad = element_geometry(SimpleNamespace(points=self.points, triangles=self.triangles))
        self.tree = cKDTree(self.vertices.mean(axis=1))
        self.lower, self.upper = self.vertices.min(axis=1), self.vertices.max(axis=1)

    def _weights(self, point, cells):
        delta = point-self.vertices[cells, 0]
        weights = np.einsum('...ij,...j->...i', self.grad[cells], delta)
        weights[..., 0] += 1
        return weights

    def evaluate(self, points_rz_m, mode=0, outside='raise'):
        if isinstance(mode, bool) or not isinstance(mode, (int, np.integer)) or not 0 <= mode < self.u.shape[1]:
            raise ValueError('mode must be a valid zero-based integer')
        if outside not in {'raise', 'nan'}:
            raise ValueError("outside must be 'raise' or 'nan'")
        points = np.asarray(points_rz_m, dtype=float)
        if points.ndim != 2 or points.shape[1] != 2 or not len(points) or not np.isfinite(points).all():
            raise ValueError('probe coordinates must be a nonempty finite N by 2 array in (r,z) metres')
        k = min(16, len(self.triangles))
        candidates = np.asarray(self.tree.query(points, k=k)[1]).reshape(len(points), k)
        weights = self._weights(points[:, None, :], candidates)
        valid = np.all((weights >= -1e-10) & (weights <= 1+1e-10), axis=-1)
        cells = candidates[np.arange(len(points)), np.argmax(valid, axis=1)]
        found = valid.any(axis=1)
        for i in np.flatnonzero(~found):
            # A centroid-nearest search may miss a thin triangle. Check every
            # containing bounding box before declaring the probe outside.
            boxes = np.flatnonzero(np.all((points[i] >= self.lower-1e-14) & (points[i] <= self.upper+1e-14), axis=1))
            w = self._weights(points[i], boxes)
            good = np.flatnonzero(np.all((w >= -1e-10) & (w <= 1+1e-10), axis=1))
            if len(good):
                cells[i], found[i] = boxes[good[0]], True
        if outside == 'raise' and not found.all():
            raise ValueError(f'{np.count_nonzero(~found)} probe points lie outside the mesh')
        nodal = self.u[self.triangles[cells], mode]
        value = np.sum(self._weights(points, cells)*nodal, axis=1)
        du = np.einsum('ni,nij->nj', nodal, self.grad[cells])
        omega, r = TAU*self.frequencies_hz[mode], points[:, 0]
        fields = {'Er_quadrature_V_per_m': -r*du[:, 1]/(omega*EPS0),
                  'Ez_quadrature_V_per_m': (2*value+r*du[:, 0])/(omega*EPS0),
                  'Hphi_A_per_m': r*value}
        for values in fields.values():
            values[~found] = np.nan
        fields['inside'] = found
        return fields


def radial_extent(points, edges, z_m):
    """Outer intersection with a radial line in an axis-connected cavity."""
    radii = []
    for (r0, z0), (r1, z1) in points[edges]:
        if z0 == z1:
            if abs(z_m-z0) <= 1e-14:
                radii.extend([r0, r1])
        elif min(z0, z1)-1e-14 <= z_m <= max(z0, z1)+1e-14:
            radii.append(r0+(z_m-z0)*(r1-r0)/(z1-z0))
    if not radii or max(radii) <= 0:
        raise ValueError('radial probe does not intersect the cavity')
    return max(radii)
