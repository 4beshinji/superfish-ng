# SPDX-License-Identifier: Apache-2.0
"""Evaluate P1/P2 fields without smoothing, with explicit outside handling."""
from types import SimpleNamespace
import numpy as np
from scipy.spatial import cKDTree
from .constants import EPS0, TAU
from .mesh import element_geometry


class FieldSampler:
    def __init__(self, points, triangles, u, frequencies_hz, *, space=None):
        self.points, self.triangles = np.asarray(points), np.asarray(triangles)
        self.u, self.frequencies_hz = np.asarray(u), np.asarray(frequencies_hz)
        self.space = space
        count = len(self.points)
        if space is not None:
            from .high_order import quadratic_space
            if not np.array_equal(space.mesh.points, self.points) or not np.array_equal(space.mesh.triangles, self.triangles):
                raise ValueError('quadratic space must belong to the sampling mesh')
            expected = quadratic_space(space.mesh)
            if not np.array_equal(space.cell_dofs, expected.cell_dofs) or not np.array_equal(space.dof_points, expected.dof_points):
                raise ValueError('quadratic space has inconsistent midpoint connectivity')
            count = len(space.dof_points)
        if self.u.ndim != 2 or self.u.shape != (count, len(self.frequencies_hz)):
            raise ValueError('P1 sampling requires one coefficient per mesh vertex and mode; P2 requires an explicit matching space')
        self.vertices, _, self.grad = element_geometry(SimpleNamespace(points=self.points, triangles=self.triangles))
        self.tree = cKDTree(self.vertices.mean(axis=1))
        self.lower, self.upper = self.vertices.min(axis=1), self.vertices.max(axis=1)

    @classmethod
    def from_solution(cls, solution):
        from .te import TESolution,TEFieldSampler
        if isinstance(solution,TESolution):return TEFieldSampler(solution)
        from .curved_solution import CurvedSolution
        if isinstance(solution,CurvedSolution):
            from .curved_sampling import CurvedFieldSampler
            return CurvedFieldSampler(solution)
        order = getattr(solution, 'element_order', 1)
        space = getattr(solution, 'space', None)
        if order not in (1, 2) or (order == 2) != (space is not None):
            raise ValueError('solution element order and field space are inconsistent')
        return cls(solution.mesh.points, solution.mesh.triangles, solution.u,
                   solution.frequencies_hz, space=space)

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
        bary = self._weights(points, cells)
        if self.space is None:
            nodal = self.u[self.triangles[cells], mode]
            value = np.sum(bary*nodal, axis=1)
            du = np.einsum('ni,nij->nj', nodal, self.grad[cells])
        else:
            nodal = self.u[self.space.cell_dofs[cells], mode]
            values = [bary[:, i]*(2*bary[:, i]-1) for i in range(3)]
            derivatives = [(4*bary[:, i]-1)[:, None]*self.grad[cells, i] for i in range(3)]
            for i, j in [(0, 1), (1, 2), (2, 0)]:
                values.append(4*bary[:, i]*bary[:, j])
                derivatives.append(4*(bary[:, i, None]*self.grad[cells, j]+bary[:, j, None]*self.grad[cells, i]))
            value = np.sum(np.stack(values, axis=1)*nodal, axis=1)
            du = np.einsum('ni,nij->nj', nodal, np.stack(derivatives, axis=1))
        omega, r = TAU*self.frequencies_hz[mode], points[:, 0]
        fields = {'Er_quadrature_V_per_m': -r*du[:, 1]/(omega*EPS0),
                  'Ez_quadrature_V_per_m': (2*value+r*du[:, 0])/(omega*EPS0),
                  'Hphi_A_per_m': r*value}
        for values in fields.values():
            values[~found] = np.nan
        fields['inside'] = found
        return fields


def solution_radial_extent(solution, z_m):
    if solution.case.geometry_order == 2:
        from .curved_queries import quadratic_radial_extent
        geometry = solution.space.geometry
        return quadratic_radial_extent(geometry.points_rz_m, geometry.boundary_nodes, z_m)
    return radial_extent(solution.mesh.points, solution.mesh.boundary_edges, z_m)


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
