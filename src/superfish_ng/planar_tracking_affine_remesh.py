# SPDX-License-Identifier: Apache-2.0
"""Declared invertible affine plus independent remeshing of a planar polygon.

The declaration maps the previous physical polygon onto the current one; the
two meshes may use different interior nodes, diagonals and connectivity. The
boundary vertex cycle of the transformed mesh must equal the current boundary
cycle exactly, as in the similarity case. Coordinates denote their exact
binary64 values. A map that reverses orientation normalizes the polygon order
and triangle vertex order to positive orientation and restores the original
barycentric columns for field evaluation.
"""
from dataclasses import dataclass
from fractions import Fraction
import numpy as np
from .config import integer, keys
from .planar_mesh import PlanarMesh
from .planar_tracking_overlap import PlanarTrackingOverlay
from .planar_tracking_remesh import _same_polygon_overlay


def _finite(value, name):
    if type(value) not in (int, float) or not np.isfinite(value):
        raise ValueError(name+' must be finite')
    return float(value)


@dataclass(frozen=True)
class PolygonAffineRemeshMapping:
    linear_xy: object
    translation_xy_m: tuple = (0., 0.)
    inverse: bool = False
    max_candidate_tests: int = 2000000

    def __post_init__(self):
        linear = self.linear_xy
        if type(linear) not in (list, tuple) or len(linear) != 2:
            raise ValueError('linear_xy must be a 2x2 matrix')
        rows = []
        for row in linear:
            if type(row) not in (list, tuple) or len(row) != 2:
                raise ValueError('linear_xy must be a 2x2 matrix')
            rows.append(tuple(_finite(value, 'linear_xy entry') for value in row))
        object.__setattr__(self, 'linear_xy', tuple(rows))
        if type(self.translation_xy_m) not in (list, tuple) or len(self.translation_xy_m) != 2:
            raise ValueError('translation requires two finite SI coordinates')
        object.__setattr__(self, 'translation_xy_m',
                           tuple(_finite(value, 'translation_xy_m') for value in self.translation_xy_m))
        if type(self.inverse) is not bool:
            raise ValueError('inverse must be boolean')
        integer(self.max_candidate_tests, 'max_candidate_tests')
        if self.determinant_sign() == 0:
            raise ValueError('linear_xy must be invertible')

    @property
    def matrix(self):
        return np.asarray(self.linear_xy, dtype=float)

    def determinant_sign(self):
        (a, b), (c, d) = self.linear_xy
        determinant = Fraction(a)*Fraction(d)-Fraction(b)*Fraction(c)
        return (determinant > 0)-(determinant < 0)

    @property
    def orientation_preserving(self):
        return self.determinant_sign() > 0

    @property
    def signed_determinant(self):
        return float(np.linalg.det(self.matrix))

    def _effective(self, reverse):
        matrix = self.matrix
        translation = np.asarray(self.translation_xy_m, dtype=float)
        if self.inverse:
            matrix = np.linalg.inv(matrix)
            translation = -matrix@translation
        if reverse:
            matrix = np.linalg.inv(matrix)
            translation = -matrix@translation
        return matrix, translation

    def transform_mesh(self, mesh, *, reverse=False):
        if not isinstance(mesh, PlanarMesh):
            raise ValueError('expected PlanarMesh')
        if type(reverse) is not bool:
            raise ValueError('reverse must be boolean')
        matrix, translation = self._effective(reverse)
        def points(values):
            return values@matrix.T+translation
        polygon = points(mesh.polygon_xy_m)
        triangles = mesh.triangles
        if not self.orientation_preserving:
            polygon = polygon[::-1]
            triangles = triangles[:, [0, 2, 1]]
        return PlanarMesh.create(polygon, points(mesh.points_xy_m), triangles)

    def _scalar_transform_mesh(self, mesh, *, reverse=False):
        if not isinstance(mesh, PlanarMesh):
            raise ValueError('expected PlanarMesh')
        if type(reverse) is not bool:
            raise ValueError('reverse must be boolean')
        (a, b), (c, d) = self.linear_xy
        tx, ty = self.translation_xy_m
        determinant = a*d-b*c
        def points(values):
            x, y = values.T
            if self.inverse != reverse:
                return np.column_stack(((d*(x-tx)-b*(y-ty))/determinant,
                                        (-c*(x-tx)+a*(y-ty))/determinant))
            return np.column_stack((a*x+b*y+tx, c*x+d*y+ty))
        polygon = points(mesh.polygon_xy_m)
        triangles = mesh.triangles
        if not self.orientation_preserving:
            polygon = polygon[::-1]
            triangles = triangles[:, [0, 2, 1]]
        return PlanarMesh.create(polygon, points(mesh.points_xy_m), triangles)

    @property
    def current_to_previous_linear(self):
        (a, b), (c, d) = self.linear_xy
        if self.inverse:
            determinant = a*d-b*c
            return np.asarray([[a/determinant, b/determinant], [c/determinant, d/determinant]])
        return np.asarray([[d, -b], [-c, a]])

    def to_dict(self):
        return dict(name='polygon_affine_remesh', linear_xy=[list(row) for row in self.linear_xy],
                    translation_xy_m=list(self.translation_xy_m), inverse=self.inverse,
                    max_candidate_tests=self.max_candidate_tests)

    @classmethod
    def from_dict(cls, data):
        names = ['name', 'linear_xy', 'translation_xy_m', 'inverse', 'max_candidate_tests']
        keys(data, names, names, 'affine-remesh mapping')
        if data['name'] != 'polygon_affine_remesh':
            raise ValueError('expected polygon_affine_remesh mapping')
        if type(data['linear_xy']) is not list or any(type(row) is not list for row in data['linear_xy']):
            raise ValueError('linear_xy must be a JSON list of two lists')
        if type(data['translation_xy_m']) is not list:
            raise ValueError('translation_xy_m must be a JSON list')
        return cls(data['linear_xy'], data['translation_xy_m'], data['inverse'], data['max_candidate_tests'])


def _restored(overlay, mapping, side):
    if mapping.orientation_preserving:
        return overlay
    column = [0, 2, 1]
    previous = (overlay.previous_vertex_barycentric[:, :, column]
                if side == 'previous' else overlay.previous_vertex_barycentric)
    current = (overlay.current_vertex_barycentric[:, :, column]
               if side == 'current' else overlay.current_vertex_barycentric)
    previous, current = np.ascontiguousarray(previous), np.ascontiguousarray(current)
    previous.setflags(write=False)
    current.setflags(write=False)
    return PlanarTrackingOverlay(overlay.previous_cells, overlay.current_cells, previous, current,
                                 overlay.reference_vertices, overlay.reference_determinants)


def polygon_affine_remesh_overlay(previous, current, mapping, *, max_overlay_triangles=250000):
    """Integrate original polynomials after a declared affine map and remeshing.

    The declared operation, in either the fixed matrix or explicit component
    evaluation order, must map the previous boundary vertex cycle exactly onto
    the current boundary vertex cycle; the exactly evaluated opposite form can
    also recognize a pair. Interior nodes, diagonals and connectivity are
    independent. Orientation-reversing maps must reverse the current boundary
    traversal and use positive-orientation triangles; the overlay restores the
    original barycentric columns for field evaluation. No widened coordinate
    tolerance is used.
    """
    if not isinstance(mapping, PolygonAffineRemeshMapping):
        raise ValueError('expected PolygonAffineRemeshMapping')
    mapping = PolygonAffineRemeshMapping.from_dict(mapping.to_dict())
    integer(max_overlay_triangles, 'max_overlay_triangles')
    if any(not isinstance(mesh, PlanarMesh) for mesh in (previous, current)):
        raise ValueError('affine-remesh comparison requires two PlanarMesh objects')
    if max(len(previous.triangles), len(current.triangles)) > max_overlay_triangles:
        raise ValueError('input meshes already exceed max_overlay_triangles')
    previous, current = [PlanarMesh.create(mesh.polygon_xy_m, mesh.points_xy_m, mesh.triangles)
                         for mesh in (previous, current)]
    previous_boundary, current_boundary = _boundary_cycle(previous), _boundary_cycle(current)
    for transform in (mapping.transform_mesh, mapping._scalar_transform_mesh):
        candidate = transform(previous)
        if np.array_equal(_boundary_cycle(candidate), current_boundary):
            return _restored(_same_polygon_overlay(candidate, current, mapping.max_candidate_tests,
                                                   max_overlay_triangles), mapping, 'previous')
    for transform in (mapping.transform_mesh, mapping._scalar_transform_mesh):
        candidate = transform(current, reverse=True)
        if np.array_equal(_boundary_cycle(candidate), previous_boundary):
            return _restored(_same_polygon_overlay(previous, candidate, mapping.max_candidate_tests,
                                                   max_overlay_triangles), mapping, 'current')
    raise ValueError('the declared affine map must map the previous boundary cycle onto the current boundary cycle exactly')


def _boundary_cycle(mesh):
    """Ordered boundary vertex coordinates, normalized to the lexicographic start."""
    successors = {int(a): int(b) for a, b in mesh.boundary_edges}
    start = min(successors, key=lambda index: tuple(mesh.points_xy_m[index]))
    order = [start]
    current = successors[start]
    while current != start:
        order.append(current)
        current = successors[current]
    return mesh.points_xy_m[order]
