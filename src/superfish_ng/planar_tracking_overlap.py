# SPDX-License-Identifier: Apache-2.0
"""Exact reference triangle intersections for two declared rectangle grids.

Rational clipping partitions the unit square at both FEM meshes' interfaces.
Floating barycentric maps are produced only after the partition is verified.
"""
from dataclasses import dataclass
from fractions import Fraction
from math import gcd
import numpy as np
from .config import integer


def _cross(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def _clip(subject, triangle):
    polygon = list(subject)
    for a, b in zip(triangle, triangle[1:] + triangle[:1]):
        if not polygon:
            break
        result = []
        previous = polygon[-1]
        dp = _cross(a, b, previous)
        for current in polygon:
            dc = _cross(a, b, current)
            if (dp < 0) != (dc < 0):
                t = dp/(dp-dc)
                result.append(tuple(previous[k]+t*(current[k]-previous[k]) for k in (0, 1)))
            if dc >= 0:
                result.append(current)
            previous, dp = current, dc
        polygon = []
        for point in result:
            if not polygon or point != polygon[-1]:
                polygon.append(point)
        if len(polygon) > 1 and polygon[0] == polygon[-1]:
            polygon.pop()
    return polygon


def _triangles(nx, ny, i, j):
    a = (Fraction(i, nx), Fraction(j, ny))
    b = (Fraction(i+1, nx), Fraction(j, ny))
    c = (Fraction(i+1, nx), Fraction(j+1, ny))
    d = (Fraction(i, nx), Fraction(j+1, ny))
    return [(a, b, c), (a, c, d)]


def _barycentric(points, triangle):
    a, b, c = triangle
    determinant = _cross(a, b, c)
    rows = []
    for point in points:
        row = (_cross(point, b, c)/determinant,
               _cross(a, point, c)/determinant,
               _cross(a, b, point)/determinant)
        if min(row) < 0 or sum(row) != 1:
            raise ValueError('reference intersection escaped a parent FEM triangle')
        rows.append([float(value) for value in row])
    return rows


@dataclass(frozen=True)
class PlanarTrackingOverlay:
    previous_cells: np.ndarray
    current_cells: np.ndarray
    previous_vertex_barycentric: np.ndarray
    current_vertex_barycentric: np.ndarray
    reference_vertices: np.ndarray
    reference_determinants: np.ndarray


def rectangle_tracking_overlay(previous_grid, current_grid, *, max_overlay_triangles=250000):
    """Intersect the declared southwest-to-northeast diagonal rectangle meshes.

    Cell numbers follow PlanarCase: 2*(j*nx+i), then its upper-left triangle.
    The caller must verify that both solutions actually use those meshes.
    """
    integer(max_overlay_triangles, 'max_overlay_triangles')
    for grid in (previous_grid, current_grid):
        if not isinstance(grid, (tuple, list)) or len(grid) != 2:
            raise ValueError('rectangle grid must declare [nx, ny]')
        for value in grid:
            integer(value, 'rectangle grid count', 2)
    ax, ay = previous_grid
    bx, by = current_grid
    # Every full grid line remains an interface of the intersection partition.
    if 2*(ax+bx-gcd(ax, bx))*(ay+by-gcd(ay, by)) > max_overlay_triangles:
        raise ValueError('rectangle reference partition exceeds max_overlay_triangles')
    old_cells, new_cells, old_bary, new_bary, vertices, determinants = [], [], [], [], [], []
    total = Fraction(0)
    for j in range(ay):
        for i in range(ax):
            # These half-open ranges omit triangles that can only touch an edge.
            first_x, last_x = i*bx//ax, ((i+1)*bx+ax-1)//ax
            first_y, last_y = j*by//ay, ((j+1)*by+ay-1)//ay
            for old_local, old_triangle in enumerate(_triangles(ax, ay, i, j)):
                for jj in range(first_y, last_y):
                    for ii in range(first_x, last_x):
                        for new_local, new_triangle in enumerate(_triangles(bx, by, ii, jj)):
                            polygon = _clip(old_triangle, new_triangle)
                            for k in range(1, len(polygon)-1):
                                child = (polygon[0], polygon[k], polygon[k+1])
                                determinant = _cross(*child)
                                if determinant < 0:
                                    raise ValueError('reference intersection orientation is invalid')
                                if determinant == 0:
                                    continue
                                if len(vertices) >= max_overlay_triangles:
                                    raise ValueError('rectangle triangle intersections exceed max_overlay_triangles')
                                old_cells.append(2*(j*ax+i)+old_local)
                                new_cells.append(2*(jj*bx+ii)+new_local)
                                old_bary.append(_barycentric(child, old_triangle))
                                new_bary.append(_barycentric(child, new_triangle))
                                vertices.append([[float(v) for v in point] for point in child])
                                determinants.append(float(determinant))
                                total += determinant
    if total != 2:
        raise ValueError('reference intersections do not exactly cover the unit square')
    arrays = [np.asarray(values, dtype=dtype) for values, dtype in (
        (old_cells, np.int64), (new_cells, np.int64), (old_bary, float),
        (new_bary, float), (vertices, float), (determinants, float))]
    if not np.isfinite(arrays[-1]).all() or np.any(arrays[-1] <= 0):
        raise ValueError('reference intersection is unresolved in floating arithmetic')
    for array in arrays:
        array.setflags(write=False)
    return PlanarTrackingOverlay(*arrays)
