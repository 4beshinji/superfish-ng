# SPDX-License-Identifier: Apache-2.0
"""Exact original-element intersections through a continuous piecewise map."""
from dataclasses import dataclass
from fractions import Fraction
import numpy as np
from .config import integer
from .planar_piecewise_mapping import (
    PlanarPiecewiseMapping, verify_planar_piecewise_domains, _binary64)
from .planar_tracking_exact_affine import _RationalTriangulation
from .planar_tracking_overlap import PlanarTrackingOverlay, _clip, _cross, _barycentric
from .planar_tracking_remesh import _rational_points, _candidate_pairs


def _map_exact(points, previous, current):
    a, b, c = previous
    determinant = _cross(a, b, c)
    result = []
    for point in points:
        bary = (_cross(point, b, c)/determinant, _cross(a, point, c)/determinant,
                _cross(a, b, point)/determinant)
        if min(bary) < 0:
            raise ValueError('piecewise intersection escaped its comparison cell')
        result.append(tuple(sum((v*p[k] for v, p in zip(bary, current)), Fraction(0))
                            for k in (0, 1)))
    return result


def _fan(polygon):
    for k in range(1, len(polygon)-1):
        child = [polygon[0], polygon[k], polygon[k+1]]
        determinant = _cross(*child)
        if determinant < 0:
            raise ValueError('piecewise intersection orientation is invalid')
        if determinant:
            yield child, determinant


@dataclass(frozen=True)
class PlanarPiecewiseOverlay:
    overlay: PlanarTrackingOverlay
    mapping_cells: np.ndarray
    current_to_previous_linear: np.ndarray


def planar_piecewise_overlay(previous, current, mapping, *, max_overlay_triangles=250000):
    """Joint native partition in previous physical xy area, with cell adj(A).

    Clip native previous cells against the previous comparison partition;
    map each intersection exactly to current coordinates; then clip against
    current native cells. Rational coverage is checked for every native and
    comparison cell before quadrature conversion. No field is interpolated.
    Candidate limits apply separately to each bounded BVH search.
    """
    if not isinstance(mapping, PlanarPiecewiseMapping):
        raise ValueError('expected PlanarPiecewiseMapping')
    integer(max_overlay_triangles, 'max_overlay_triangles')
    mapping = PlanarPiecewiseMapping.from_dict(mapping.to_dict())
    verify_planar_piecewise_domains(previous, current, mapping,
                                   max_overlay_triangles=max_overlay_triangles)
    meshes = (previous, current, mapping.previous_partition, mapping.current_partition)
    points = [_rational_points(mesh.points_xy_m) for mesh in meshes]
    triangles = [[[p[int(i)] for i in cell] for cell in mesh.triangles]
                 for p, mesh in zip(points, meshes)]
    rational = [_RationalTriangulation(np.asarray(p, dtype=object), mesh.triangles)
                for p, mesh in zip(points, meshes)]
    # The intermediate mesh is a bounded collection of exact triangle pieces.
    # It need not share vertex indices: only the candidate BVH consumes it.
    mapped_pieces, parents, comparison = [], [], []
    for native_cell, mapping_cell in _candidate_pairs(rational[0], rational[2], mapping.max_candidate_tests):
        for child, _ in _fan(_clip(triangles[0][native_cell], triangles[2][mapping_cell])):
            if len(mapped_pieces) >= max_overlay_triangles:
                raise ValueError('piecewise intermediate partition exceeds max_overlay_triangles')
            mapped_pieces.append(_map_exact(child, triangles[2][mapping_cell], triangles[3][mapping_cell]))
            parents.append(native_cell)
            comparison.append(mapping_cell)
    if not mapped_pieces:
        raise ValueError('piecewise intermediate partition is empty')
    intermediate = _RationalTriangulation(
        np.asarray(mapped_pieces, dtype=object).reshape(-1, 2),
        np.arange(3*len(mapped_pieces)).reshape(-1, 3))
    covered = [[Fraction(0) for _ in ts] for ts in triangles]
    parts = [[], [], [], [], [], []]
    mapping_cells = []
    for piece, current_cell in _candidate_pairs(intermediate, rational[1], mapping.max_candidate_tests):
        previous_cell, mapping_cell = parents[piece], comparison[piece]
        for current_child, current_det in _fan(_clip(mapped_pieces[piece], triangles[1][current_cell])):
            if len(parts[0]) >= max_overlay_triangles:
                raise ValueError('piecewise joint partition exceeds max_overlay_triangles')
            previous_child = _map_exact(current_child, triangles[3][mapping_cell], triangles[2][mapping_cell])
            previous_det = _cross(*previous_child)
            if previous_det <= 0:
                raise ValueError('piecewise inverse intersection orientation is invalid')
            for side, cell, determinant in ((0, previous_cell, previous_det), (1, current_cell, current_det),
                                            (2, mapping_cell, previous_det), (3, mapping_cell, current_det)):
                covered[side][cell] += determinant
            values = (previous_cell, current_cell,
                      _barycentric(previous_child, triangles[0][previous_cell]),
                      _barycentric(current_child, triangles[1][current_cell]),
                      previous_child, previous_det)
            for part, value in zip(parts, values):
                part.append(value)
            mapping_cells.append(mapping_cell)
    for actual, ts in zip(covered, triangles):
        if actual != [_cross(*tri) for tri in ts]:
            raise ValueError('piecewise intersections do not exactly cover every native and comparison cell')
    arrays = [np.asarray(part, dtype=np.int64) if i < 2 else
              _binary64(part, 'piecewise joint partition', positive=i == 5)
              for i, part in enumerate(parts)]
    cells = np.asarray(mapping_cells, dtype=np.int64)
    transport = mapping.current_to_previous_linear[cells].copy()
    for array in (*arrays, cells, transport):
        array.setflags(write=False)
    return PlanarPiecewiseOverlay(PlanarTrackingOverlay(*arrays), cells, transport)
