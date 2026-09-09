# SPDX-License-Identifier: Apache-2.0
"""Exact common-element partitions of two meshes on the same planar polygon.

Coordinates denote their exact binary64 values. Independent numbering and
boundary subdivisions are allowed; a different physical polygon is not.
"""
from dataclasses import dataclass
from fractions import Fraction
import numpy as np
from .config import integer, keys
from .planar_mesh import PlanarMesh
from .planar_tracking_overlap import PlanarTrackingOverlay, _clip, _cross, _barycentric


@dataclass(frozen=True)
class PolygonRemeshMapping:
    max_candidate_tests: int = 2000000

    def __post_init__(self):
        integer(self.max_candidate_tests, 'max_candidate_tests')

    def to_dict(self):
        return dict(name='polygon_same_domain', max_candidate_tests=self.max_candidate_tests)

    @classmethod
    def from_dict(cls, data):
        names = ['name', 'max_candidate_tests']
        keys(data, names, names, 'same-domain polygon mapping')
        if data['name'] != 'polygon_same_domain':
            raise ValueError('expected polygon_same_domain mapping')
        return cls(data['max_candidate_tests'])


def _rational_points(points):
    return [tuple(Fraction(float(value)) for value in point) for point in points]


def _polygon_corners(mesh):
    polygon = _rational_points(mesh.polygon_xy_m)
    corners = [p for i, p in enumerate(polygon)
               if _cross(polygon[i-1], p, polygon[(i+1) % len(polygon)]) != 0]
    start = min(range(len(corners)), key=corners.__getitem__)
    return corners[start:] + corners[:start]


def _candidate_pairs(previous, current, budget):
    """Conservative positive-area AABB candidates with a bounded BVH query.

    Charge both tree-node comparisons and individual leaf comparisons before
    performing them. Tree leaves and traversal have deterministic ordering.
    """
    vertices = current.points_xy_m[current.triangles]
    low, high = vertices.min(axis=1), vertices.max(axis=1)
    centers = low + (high-low)/2

    def build(indices):
        lo, hi = low[indices].min(axis=0), high[indices].max(axis=0)
        if len(indices) <= 8:
            return lo, hi, indices, None, None
        axis = int(np.argmax(hi-lo))
        order = indices[np.argsort(centers[indices, axis], kind='stable')]
        mid = len(order)//2
        return lo, hi, None, build(order[:mid]), build(order[mid:])

    tree = build(np.arange(len(current.triangles)))
    tests = 0
    for i, tri in enumerate(previous.triangles):
        vertices = previous.points_xy_m[tri]
        lo, hi = vertices.min(axis=0), vertices.max(axis=0)
        stack = [tree]
        while stack:
            node = stack.pop()
            tests += 1
            if tests > budget:
                raise ValueError('same-domain candidate search exceeds max_candidate_tests')
            nlo, nhi, indices, left, right = node
            if np.any(nlo >= hi) or np.any(nhi <= lo):
                continue
            if indices is None:
                stack.extend((right, left))
                continue
            for j in indices:
                tests += 1
                if tests > budget:
                    raise ValueError('same-domain candidate search exceeds max_candidate_tests')
                if np.all(low[j] < hi) and np.all(high[j] > lo):
                    yield i, int(j)


def polygon_remesh_overlay(previous, current, mapping, *, max_overlay_triangles=250000):
    """Integrate original element polynomials over exact triangle intersections."""
    if not isinstance(mapping, PolygonRemeshMapping):
        raise ValueError('expected PolygonRemeshMapping')
    mapping = PolygonRemeshMapping.from_dict(mapping.to_dict())
    integer(max_overlay_triangles, 'max_overlay_triangles')
    if any(not isinstance(mesh, PlanarMesh) for mesh in (previous, current)):
        raise ValueError('same-domain comparison requires two PlanarMesh objects')
    if max(len(previous.triangles), len(current.triangles)) > max_overlay_triangles:
        raise ValueError('input meshes already exceed max_overlay_triangles')
    previous, current = [PlanarMesh.create(mesh.polygon_xy_m, mesh.points_xy_m, mesh.triangles)
                         for mesh in (previous, current)]
    if _polygon_corners(previous) != _polygon_corners(current):
        raise ValueError('same-domain tracking requires exactly the same physical polygon')
    points = [_rational_points(mesh.points_xy_m) for mesh in (previous, current)]
    triangles = [[[p[int(index)] for index in tri] for tri in mesh.triangles]
                 for p, mesh in zip(points, (previous, current))]
    covered = [[Fraction(0) for _ in ts] for ts in triangles]
    parts = [[], [], [], [], [], []]
    for i, j in _candidate_pairs(previous, current, mapping.max_candidate_tests):
        a, b = triangles[0][i], triangles[1][j]
        polygon = _clip(a, b)
        for k in range(1, len(polygon)-1):
            child = [polygon[0], polygon[k], polygon[k+1]]
            determinant = _cross(*child)
            if determinant < 0:
                raise ValueError('same-domain intersection orientation is invalid')
            if determinant == 0:
                continue
            if len(parts[0]) >= max_overlay_triangles:
                raise ValueError('same-domain intersections exceed max_overlay_triangles')
            covered[0][i] += determinant
            covered[1][j] += determinant
            values = (i, j, _barycentric(child, a), _barycentric(child, b),
                      [[float(x) for x in point] for point in child], float(determinant))
            for part, value in zip(parts, values):
                part.append(value)
    for actual, ts in zip(covered, triangles):
        if actual != [_cross(*tri) for tri in ts]:
            raise ValueError('intersections do not exactly cover every original element')
    arrays = [np.asarray(part, dtype=np.int64 if i < 2 else float) for i, part in enumerate(parts)]
    if any(not np.isfinite(array).all() for array in arrays) or np.any(arrays[-1] <= 0):
        raise ValueError('same-domain partition is unresolved in floating arithmetic')
    for array in arrays:
        array.setflags(write=False)
    return PlanarTrackingOverlay(*arrays)
