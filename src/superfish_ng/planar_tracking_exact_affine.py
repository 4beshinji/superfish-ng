# SPDX-License-Identifier: Apache-2.0
"""Exact affine intersections with independent polygon boundary subdivisions.

This geometry API evaluates the declared affine map over rational numbers,
including its inverse. It does not round a transformed mesh into binary64.
Both input meshes retain their original element polynomials. This is a
separate contract from the rounded boundary-cycle maps in tracking versions
5/6. Version 7 dispatch is provided by planar_tracking_exact_mapping.
"""
from dataclasses import dataclass
from fractions import Fraction
import numpy as np
from .config import integer
from .planar_mesh import PlanarMesh
from .planar_tracking_affine_remesh import PolygonAffineRemeshMapping, _boundary_cycle
from .planar_tracking_overlap import PlanarTrackingOverlay, _barycentric, _clip, _cross
from .planar_tracking_remesh import _candidate_pairs, _rational_points


@dataclass(frozen=True)
class _RationalTriangulation:
    # The existing BVH only uses coordinates/connectivity. Object arrays keep
    # its bounds, center ordering and comparisons rational, without rounding
    # an AABB inward and losing a narrow intersection.
    points_xy_m: np.ndarray
    triangles: np.ndarray


def _corners(cycle):
    corners = [p for i, p in enumerate(cycle)
               if _cross(cycle[i-1], p, cycle[(i+1) % len(cycle)]) != 0]
    start = min(range(len(corners)), key=corners.__getitem__)
    return corners[start:]+corners[:start]


def _exact_map(mapping):
    (a, b), (c, d) = [[Fraction(value) for value in row] for row in mapping.linear_xy]
    tx, ty = map(Fraction, mapping.translation_xy_m)
    determinant = a*d-b*c

    def transform(point):
        x, y = point
        if mapping.inverse:
            return ((d*(x-tx)-b*(y-ty))/determinant,
                    (-c*(x-tx)+a*(y-ty))/determinant)
        return a*x+b*y+tx, c*x+d*y+ty
    return transform


def exact_affine_polygon_overlay(previous, current, *, linear_xy,
                                 translation_xy_m=(0., 0.), inverse=False,
                                 max_candidate_tests=2000000,
                                 max_overlay_triangles=250000):
    """Partition two original meshes under an exactly evaluated affine map.

    ``x_current = A*x_previous+t`` (or its exact inverse when requested).
    Binary64 inputs denote exact rational numbers. Actual boundary edges must
    lie exactly on their declared polygon, and the polygons must be exact
    affine images. Boundary and interior subdivisions are independent.

    Each original element's area is checked by rational arithmetic before
    returning floating quadrature vertices, determinants and barycentric
    coordinates. Cell IDs and barycentric columns always refer to the input
    meshes, including reflections. The integration measure is current xy
    area, for both forward and inverse declarations. No field is interpolated
    and no eigenproblem is solved here. Resource limits raise ValueError.
    """
    mapping = PolygonAffineRemeshMapping(linear_xy, translation_xy_m, inverse,
                                         max_candidate_tests)
    integer(max_overlay_triangles, 'max_overlay_triangles')
    if any(not isinstance(mesh, PlanarMesh) for mesh in (previous, current)):
        raise ValueError('exact affine overlay requires two PlanarMesh objects')
    if max(len(previous.triangles), len(current.triangles)) > max_overlay_triangles:
        raise ValueError('input meshes already exceed max_overlay_triangles')
    meshes = [PlanarMesh.create(mesh.polygon_xy_m, mesh.points_xy_m, mesh.triangles)
              for mesh in (previous, current)]
    boundaries = []
    for mesh in meshes:
        boundary = _corners(_rational_points(_boundary_cycle(mesh)))
        if boundary != _corners(_rational_points(mesh.polygon_xy_m)):
            raise ValueError('exact affine overlay requires boundary edges exactly on the declared polygon; rounded boundary deviations are unsupported')
        boundaries.append(boundary)
    transform = _exact_map(mapping)
    mapped_boundary = [transform(point) for point in boundaries[0]]
    if not mapping.orientation_preserving:
        mapped_boundary.reverse()
    if _corners(mapped_boundary) != boundaries[1]:
        raise ValueError('declared polygons are not exact rational affine images; rounded corner matches are unsupported')

    points = [_rational_points(mesh.points_xy_m) for mesh in meshes]
    points[0] = [transform(point) for point in points[0]]
    rational = [_RationalTriangulation(np.asarray(p, dtype=object), mesh.triangles)
                for p, mesh in zip(points, meshes)]
    triangles = [[[p[int(index)] for index in cell] for cell in mesh.triangles]
                 for p, mesh in zip(points, meshes)]
    covered = [[Fraction(0) for _ in ts] for ts in triangles]
    parts = [[], [], [], [], [], []]
    for i, j in _candidate_pairs(*rational, max_candidate_tests):
        original_a, b = triangles[0][i], triangles[1][j]
        a = original_a if mapping.orientation_preserving else original_a[::-1]
        polygon = _clip(a, b)
        for k in range(1, len(polygon)-1):
            child = [polygon[0], polygon[k], polygon[k+1]]
            determinant = _cross(*child)
            if determinant < 0:
                raise ValueError('exact affine intersection orientation is invalid')
            if determinant == 0:
                continue
            if len(parts[0]) >= max_overlay_triangles:
                raise ValueError('exact affine intersections exceed max_overlay_triangles')
            covered[0][i] += determinant
            covered[1][j] += determinant
            # Signed barycentric ratios also work on the original clockwise
            # transformed cell, preserving input columns without renumbering.
            values = (i, j, _barycentric(child, original_a), _barycentric(child, b),
                      child, determinant)
            for part, value in zip(parts, values):
                part.append(value)
    for actual, ts in zip(covered, triangles):
        if actual != [abs(_cross(*tri)) for tri in ts]:
            raise ValueError('exact affine intersections do not exactly cover every original element')
    try:
        arrays = [np.asarray(part, dtype=np.int64 if i < 2 else float)
                  for i, part in enumerate(parts)]
    except (OverflowError, ValueError) as exc:
        raise ValueError('exact affine partition is unresolved in floating arithmetic') from exc
    if any(not np.isfinite(array).all() for array in arrays) or np.any(arrays[-1] <= 0):
        raise ValueError('exact affine partition is unresolved in floating arithmetic')
    for array in arrays:
        array.setflags(write=False)
    return PlanarTrackingOverlay(*arrays)
