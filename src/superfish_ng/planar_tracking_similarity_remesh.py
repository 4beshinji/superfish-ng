# SPDX-License-Identifier: Apache-2.0
"""Declared proper similarity plus independent remeshing of a planar polygon.

The declaration maps the previous physical polygon onto the current one; the
two meshes may use different nodes, diagonals and boundary subdivisions.
Coordinates denote their exact binary64 values, as in the same-domain case.
"""
from dataclasses import dataclass
import numpy as np
from .config import integer, keys
from .planar_mesh import PlanarMesh
from .planar_tracking_remesh import _same_polygon_overlay
from .planar_tracking_similarity import PolygonSimilarityMapping


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


@dataclass(frozen=True)
class PolygonSimilarityRemeshMapping:
    scale: float
    rotation_radians: float
    translation_xy_m: tuple
    inverse: bool = False
    max_candidate_tests: int = 2000000

    def __post_init__(self):
        checked = PolygonSimilarityMapping(self.scale, self.rotation_radians, self.translation_xy_m,
                                           inverse=self.inverse)
        object.__setattr__(self, 'translation_xy_m', checked.translation_xy_m)
        integer(self.max_candidate_tests, 'max_candidate_tests')

    def to_similarity(self):
        """The declared transform, evaluated by the verified similarity rules."""
        return PolygonSimilarityMapping(self.scale, self.rotation_radians, self.translation_xy_m,
                                        inverse=self.inverse)

    @property
    def rotation(self):
        return self.to_similarity().rotation

    @property
    def current_to_previous_rotation(self):
        return self.to_similarity().current_to_previous_rotation

    def transform_mesh(self, mesh, *, reverse=False):
        return self.to_similarity().transform_mesh(mesh, reverse=reverse)

    def _scalar_transform_mesh(self, mesh, *, reverse=False):
        return self.to_similarity()._scalar_transform_mesh(mesh, reverse=reverse)

    def to_dict(self):
        return dict(name='polygon_similarity_remesh', scale=self.scale, rotation_radians=self.rotation_radians,
                    translation_xy_m=list(self.translation_xy_m), inverse=self.inverse,
                    max_candidate_tests=self.max_candidate_tests)

    @classmethod
    def from_dict(cls, data):
        names = ['name', 'scale', 'rotation_radians', 'translation_xy_m', 'inverse', 'max_candidate_tests']
        keys(data, names, names, 'similarity-remesh mapping')
        if data['name'] != 'polygon_similarity_remesh':
            raise ValueError('expected polygon_similarity_remesh mapping')
        if type(data['translation_xy_m']) is not list:
            raise ValueError('translation_xy_m must be a JSON list')
        return cls(data['scale'], data['rotation_radians'], data['translation_xy_m'],
                   data['inverse'], data['max_candidate_tests'])


def polygon_similarity_remesh_overlay(previous, current, mapping, *, max_overlay_triangles=250000):
    """Integrate original polynomials after the declared similarity and remeshing.

    The declared operation, in either the fixed matrix or explicit component
    evaluation order, must map the previous boundary vertex cycle exactly onto
    the current boundary vertex cycle; the exactly evaluated opposite form can
    also recognize a pair. Interior nodes, diagonals and connectivity are
    independent. The transformed mesh shares the numbering of the mesh it is
    built from; every original triangle on both sides is partitioned into exact
    common elements. No widened coordinate tolerance is used.

    Requiring the exact mapped boundary is what keeps the two element unions
    identical as point sets: a transformed boundary that merely agrees to
    roundoff would leave unverifiable slivers, so it is rejected here.
    """
    if not isinstance(mapping, PolygonSimilarityRemeshMapping):
        raise ValueError('expected PolygonSimilarityRemeshMapping')
    mapping = PolygonSimilarityRemeshMapping.from_dict(mapping.to_dict())
    integer(max_overlay_triangles, 'max_overlay_triangles')
    if any(not isinstance(mesh, PlanarMesh) for mesh in (previous, current)):
        raise ValueError('similarity-remesh comparison requires two PlanarMesh objects')
    if max(len(previous.triangles), len(current.triangles)) > max_overlay_triangles:
        raise ValueError('input meshes already exceed max_overlay_triangles')
    previous, current = [PlanarMesh.create(mesh.polygon_xy_m, mesh.points_xy_m, mesh.triangles)
                         for mesh in (previous, current)]
    previous_boundary, current_boundary = _boundary_cycle(previous), _boundary_cycle(current)
    for candidate in (mapping.transform_mesh(previous), mapping._scalar_transform_mesh(previous)):
        if np.array_equal(_boundary_cycle(candidate), current_boundary):
            return _same_polygon_overlay(candidate, current, mapping.max_candidate_tests, max_overlay_triangles)
    for candidate in (mapping.transform_mesh(current, reverse=True), mapping._scalar_transform_mesh(current, reverse=True)):
        if np.array_equal(_boundary_cycle(candidate), previous_boundary):
            return _same_polygon_overlay(previous, candidate, mapping.max_candidate_tests, max_overlay_triangles)
    raise ValueError('the declared similarity must map the previous boundary cycle onto the current boundary cycle exactly')
