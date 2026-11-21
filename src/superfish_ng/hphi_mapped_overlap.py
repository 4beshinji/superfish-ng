# SPDX-License-Identifier: Apache-2.0
"""Exact intersections of original FEM meshes under a piecewise affine map."""
from dataclasses import dataclass
from fractions import Fraction
import numpy as np
from .config import integer
from .hphi_geometry_mapping import HphiGeometryMapping
from .meridional_overlap import MeridionalOverlay, _domain
from .planar_tracking_exact_affine import _RationalTriangulation
from .planar_tracking_overlap import _clip, _cross
from .planar_tracking_remesh import _candidate_pairs, _rational_points


@dataclass(frozen=True)
class HphiMappedOverlay(MeridionalOverlay):
    mapping_cells: np.ndarray
    previous_vertices_rz_m: np.ndarray
    previous_determinants: np.ndarray


def _triangles(mesh):
    points = _rational_points(mesh.points_rz_m)
    return [[points[int(i)] for i in cell] for cell in mesh.triangles]


def _triangulation(triangles):
    return _RationalTriangulation(np.asarray(triangles, dtype=object).reshape(-1, 2),
                                 np.arange(3*len(triangles)).reshape(-1, 3))


def _children(polygon):
    for k in range(1, len(polygon)-1):
        child = [polygon[0], polygon[k], polygon[k+1]]
        determinant = _cross(*child)
        if determinant < 0:
            raise ValueError('mapped Hphi intersection has negative orientation')
        if determinant:
            yield child, determinant


def _barycentric(points, triangle):
    # The shared quadrature helper converts ratios to float. Keep these exact
    # until both clipping stages and every coverage check have finished.
    a, b, c = triangle
    determinant = _cross(a, b, c)
    rows = []
    for point in points:
        row = (_cross(point, b, c)/determinant,
               _cross(a, point, c)/determinant,
               _cross(a, b, point)/determinant)
        if min(row) < 0 or sum(row) != 1:
            raise ValueError('mapped Hphi intersection escaped its parent triangle')
        rows.append(row)
    return rows


def _compose(barycentric, vertices):
    return [tuple(sum(bary[i]*vertices[i][j] for i in range(3)) for j in range(2))
            for bary in barycentric]


def _check_coverage(covered, triangles, label):
    if covered != [_cross(*tri) for tri in triangles]:
        raise ValueError(f'mapped Hphi intersections do not exactly cover every {label} element')


def mapped_hphi_overlay(previous, current, mapping, *, max_candidate_tests=2000000,
                        max_overlay_triangles=250000):
    """Intersect independent FEM meshes and an explicit geometry partition.

    Coordinates are exact rationals represented by the binary64 inputs. First
    split previous FEM cells at control-cell boundaries, then map those pieces
    exactly and intersect current FEM cells. Check original and control areas
    before and after mapping, and again check both original FEM areas on the
    final partition. Only the returned quadrature data are rounded to float.

    Output cell indices/barycentric columns always index original FEM cells.
    ``vertices_rz_m`` and ``determinants`` measure the current domain; the
    ``previous_*`` arrays give the inverse images and their area determinants.
    No field interpolation, mode association, or eigenvalue calculation occurs.

    Candidate budget is split deterministically: floor(N/2) for the first BVH
    search and the remainder for the second. Both tree and leaf tests count.
    The triangle limit applies separately to each input, intermediate and final
    partition; failure returns no partial partition.
    """
    integer(max_candidate_tests, 'max_candidate_tests', 2)
    integer(max_overlay_triangles, 'max_overlay_triangles')
    if type(mapping) is not HphiGeometryMapping:
        raise ValueError('mapped Hphi overlap requires an explicit HphiGeometryMapping')
    if type(previous) is not type(mapping.previous) or type(current) is not type(mapping.current):
        raise ValueError('FEM and mapping domains must use the same straight vacuum/axis mesh type')
    if max(len(m.triangles) for m in (previous, current, mapping.previous, mapping.current)) > max_overlay_triangles:
        raise ValueError('mapped Hphi input meshes exceed max_overlay_triangles')
    mapping = HphiGeometryMapping(mapping.previous, mapping.current)
    previous, current = (type(m).from_dict(m.to_dict()) for m in (previous, current))
    for actual, declared in ((previous, mapping.previous), (current, mapping.current)):
        if _domain(actual) != _domain(declared):
            raise ValueError('FEM must exactly cover its declared mapping vacuum and all PEC holes')
    old, new = _triangles(previous), _triangles(current)
    control_old, control_new = _triangles(mapping.previous), _triangles(mapping.current)
    covered_old = [Fraction(0) for _ in old]
    covered_control = [Fraction(0) for _ in control_old]
    covered_mapped_control = [Fraction(0) for _ in control_new]
    fragments, old_fragments, owners, control_ids = [], [], [], []
    for i, j in _candidate_pairs(_triangulation(old), _triangulation(control_old), max_candidate_tests//2):
        for child, determinant in _children(_clip(old[i], control_old[j])):
            if len(fragments) >= max_overlay_triangles:
                raise ValueError('mapped Hphi intermediate partition exceeds max_overlay_triangles')
            mapped = _compose(_barycentric(child, control_old[j]), control_new[j])
            mapped_det = _cross(*mapped)
            if mapped_det <= 0:
                raise ValueError('mapped Hphi control map reverses or collapses a fragment')
            covered_old[i] += determinant
            covered_control[j] += determinant
            covered_mapped_control[j] += mapped_det
            fragments.append(mapped)
            old_fragments.append(child)
            owners.append(i)
            control_ids.append(j)
    _check_coverage(covered_old, old, 'previous FEM')
    _check_coverage(covered_control, control_old, 'previous control')
    _check_coverage(covered_mapped_control, control_new, 'current control')

    covered_fragments = [Fraction(0) for _ in fragments]
    covered_new = [Fraction(0) for _ in new]
    covered_old = [Fraction(0) for _ in old]
    parts = [[] for _ in range(9)]
    for i, j in _candidate_pairs(_triangulation(fragments), _triangulation(new),
                                 max_candidate_tests-max_candidate_tests//2):
        for child, determinant in _children(_clip(fragments[i], new[j])):
            if len(parts[0]) >= max_overlay_triangles:
                raise ValueError('mapped Hphi final partition exceeds max_overlay_triangles')
            original = _compose(_barycentric(child, fragments[i]), old_fragments[i])
            original_det = _cross(*original)
            if original_det <= 0:
                raise ValueError('mapped Hphi inverse has nonpositive area')
            owner = owners[i]
            covered_fragments[i] += determinant
            covered_new[j] += determinant
            covered_old[owner] += original_det
            values = (owner, j, _barycentric(original, old[owner]), _barycentric(child, new[j]),
                      child, determinant, control_ids[i], original, original_det)
            for part, value in zip(parts, values):
                part.append(value)
    _check_coverage(covered_fragments, fragments, 'mapped fragment')
    _check_coverage(covered_new, new, 'current FEM')
    _check_coverage(covered_old, old, 'inverse previous FEM')
    try:
        arrays = [np.asarray(part, dtype=np.int64 if i in (0, 1, 6) else float)
                  for i, part in enumerate(parts)]
    except (OverflowError, ValueError) as exc:
        raise ValueError('mapped Hphi partition is unresolved in floating arithmetic') from exc
    if (any(not np.isfinite(a).all() for a in arrays)
            or np.any(arrays[5] <= 0) or np.any(arrays[8] <= 0)):
        raise ValueError('mapped Hphi partition is unresolved in floating arithmetic')
    for array in arrays:
        array.setflags(write=False)
    return HphiMappedOverlay(*arrays)
