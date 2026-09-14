# SPDX-License-Identifier: Apache-2.0
"""Exact integration partitions of two explicitly declared reference meshes.

This layer checks area coverage and overlap. Physical maps, reference boundary
correspondence, and native-domain validation belong to the caller.
"""
from fractions import Fraction as F
from math import isfinite
from .config import integer
from .planar_tracking_overlap import _clip, _cross


def _encode(value):
    return [value.numerator, value.denominator]


def _area(polygon):
    if len(polygon) < 3:
        return F(0)
    return sum((_cross(polygon[0], polygon[i], polygon[i+1])
                for i in range(1, len(polygon)-1)), F(0)) / 2


def _triangles(value):
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError('reference triangulation must be a nonempty triangle sequence')
    result = []
    for triangle in value:
        if not isinstance(triangle, (list, tuple)) or len(triangle) != 3:
            raise ValueError('reference triangle must have three vertices')
        points = []
        for point in triangle:
            if not isinstance(point, (list, tuple)) or len(point) != 2:
                raise ValueError('reference vertex must have two coordinates')
            if any(type(x) not in (int, float, F) or (type(x) is float and not isfinite(x)) for x in point):
                raise ValueError('reference coordinates must be finite real numbers')
            points.append(tuple(F(x) for x in point))
        if _cross(*points) <= 0:
            raise ValueError('reference triangle must have positive orientation and area')
        result.append(tuple(points))
    return result


def _canonical_polygon(polygon):
    polygon = [p for i, p in enumerate(polygon)
               if _cross(polygon[i-1], p, polygon[(i+1) % len(polygon)]) != 0]
    first = min(range(len(polygon)), key=lambda i: polygon[i])
    return polygon[first:] + polygon[:first]


def _barycentric(point, parent):
    a, b, c = parent
    det = _cross(a, b, c)
    row = (_cross(point, b, c)/det, _cross(a, point, c)/det, _cross(a, b, point)/det)
    if min(row) < 0 or sum(row) != 1:
        raise ValueError('reference intersection escaped its parent triangle')
    return [_encode(x) for x in row]


def intersect_reference_triangulations(previous, current, *, max_pair_tests, max_triangles):
    """Cover both meshes with the same rational triangles and two parent maps.

    Input coordinates are dimensionless declared coordinates, not inferred
    physical correspondence. Finite floats retain their exact binary values.
    Every parent must be covered exactly; positive-area self-overlap is refused.
    Edge/point contacts do not create integration triangles.
    """
    integer(max_pair_tests, 'max_pair_tests')
    integer(max_triangles, 'max_triangles')
    meshes = [_triangles(previous), _triangles(current)]
    n, m = map(len, meshes)
    pair_tests = n*m + n*(n-1)//2 + m*(m-1)//2
    if pair_tests > max_pair_tests:
        raise ValueError(f'reference partition requires {pair_tests} pair tests, exceeding max_pair_tests')
    if max(n, m) > max_triangles:
        raise ValueError('reference parents already exceed max_triangles')
    for mesh in meshes:
        for i, triangle in enumerate(mesh):
            for other in mesh[i+1:]:
                if _area(_clip(triangle, other)) > 0:
                    raise ValueError('reference triangulation contains overlapping interiors')
    covered = [[F(0)]*len(mesh) for mesh in meshes]
    rows = []
    for i, a in enumerate(meshes[0]):
        for j, b in enumerate(meshes[1]):
            polygon = _clip(a, b)
            if _area(polygon) == 0:
                continue
            polygon = _canonical_polygon(polygon)
            for k in range(1, len(polygon)-1):
                points = (polygon[0], polygon[k], polygon[k+1])
                det = _cross(*points)
                if det <= 0:
                    raise ValueError('reference intersection has nonpositive orientation')
                if len(rows) >= max_triangles:
                    raise ValueError('reference intersections exceed max_triangles')
                covered[0][i] += det/2
                covered[1][j] += det/2
                rows.append((points, i, j, det))
    areas = [[_cross(*t)/2 for t in mesh] for mesh in meshes]
    if covered != areas:
        raise ValueError('reference intersections do not exactly cover every parent; declared domains differ')
    rows.sort(key=lambda row: row[0])
    result = dict(method='exact_rational_intersection_of_declared_reference_triangulations',
                  pair_tests=pair_tests, total_area=_encode(sum(areas[0], F(0))), triangles=[])
    for name, values, actual in zip(('previous', 'current'), areas, covered):
        result[name+'_areas'] = [_encode(x) for x in values]
        result[name+'_covered_areas'] = [_encode(x) for x in actual]
    for points, i, j, det in rows:
        result['triangles'].append(dict(previous_cell=i, current_cell=j,
            reference_vertices=[[_encode(x) for x in p] for p in points], determinant=_encode(det),
            previous_barycentric=[_barycentric(p, meshes[0][i]) for p in points],
            current_barycentric=[_barycentric(p, meshes[1][j]) for p in points]))
    return result
