# SPDX-License-Identifier: Apache-2.0
"""Original-element correspondence for polynomial affine tuning trials.

Actual binary64 trial meshes are regenerated and checked exactly. Common
dyadic reference triangles map separately into each original FEM mesh. Thus
coordinate rounding is retained as a piecewise affine geometric map, never
misrepresented as an exact global rational affine image.
"""
from dataclasses import dataclass
import numpy as np
from .config import keys, integer
from .planar_affine_shape import PlanarAffineShapeLaw
from .planar_project import PlanarProject
from .planar_polygon import PlanarPolygonCase
from .planar_refinement import refine_planar_mesh, REFERENCE, SPLIT
from .planar_tracking_overlap import PlanarTrackingOverlay


@dataclass(frozen=True)
class PlanarAffineShapeMapping:
    original_project: PlanarProject
    shape_law: PlanarAffineShapeLaw
    previous_value: float
    current_value: float
    previous_refinements: int = 0
    current_refinements: int = 0

    def __post_init__(self):
        if type(self.original_project) is not PlanarProject or type(self.original_project.case) is not PlanarPolygonCase:
            raise ValueError('affine shape mapping requires the original explicit polygon Project')
        if type(self.shape_law) is not PlanarAffineShapeLaw:
            raise ValueError('affine shape mapping requires PlanarAffineShapeLaw')
        object.__setattr__(self, 'original_project', PlanarProject.from_dict(self.original_project.to_dict()))
        object.__setattr__(self, 'shape_law', PlanarAffineShapeLaw.from_dict(self.shape_law.to_dict()))
        for name in ('previous_value', 'current_value'):
            self.shape_law.exact_transform(getattr(self, name))
        for name in ('previous_refinements', 'current_refinements'):
            integer(getattr(self, name), name, 0)
            if getattr(self, name) > 8:
                raise ValueError('affine shape mapping supports at most eight refinements')

    def to_dict(self):
        return dict(name='polynomial_affine_xy_reference', original_project=self.original_project.to_dict(),
                    shape_law=self.shape_law.to_dict(), previous_value=self.previous_value,
                    current_value=self.current_value, previous_refinements=self.previous_refinements,
                    current_refinements=self.current_refinements)

    @classmethod
    def from_dict(cls, data):
        names = ['name', 'original_project', 'shape_law', 'previous_value', 'current_value',
                 'previous_refinements', 'current_refinements']
        keys(data, names, names, 'planar affine shape mapping')
        if data['name'] != 'polynomial_affine_xy_reference':
            raise ValueError('expected polynomial_affine_xy_reference mapping')
        return cls(PlanarProject.from_dict(data['original_project']), PlanarAffineShapeLaw.from_dict(data['shape_law']),
                   data['previous_value'], data['current_value'], data['previous_refinements'], data['current_refinements'])


def affine_shape_overlay(previous, current, mapping, *, max_overlay_triangles=250000):
    """Return a common partition and adjugate transport for each actual cell pair."""
    if type(mapping) is not PlanarAffineShapeMapping:
        raise ValueError('expected PlanarAffineShapeMapping')
    mapping = PlanarAffineShapeMapping.from_dict(mapping.to_dict())
    integer(max_overlay_triangles, 'max_overlay_triangles')
    levels = (mapping.previous_refinements, mapping.current_refinements)
    maximum = max(levels)
    count = len(mapping.original_project.case.mesh.triangles)*4**maximum
    if count > max_overlay_triangles:
        raise ValueError('affine shape common partition exceeds max_overlay_triangles')
    parents, barycentrics, vertices = [], [], []
    for actual, value, level in zip((previous, current),
                                   (mapping.previous_value, mapping.current_value), levels):
        expected = mapping.shape_law.project(mapping.original_project, value).case.mesh
        for _ in range(level):
            expected = refine_planar_mesh(expected, max_triangles=max_overlay_triangles)
        if any(not np.array_equal(getattr(expected, name), getattr(actual, name))
               for name in ('polygon_xy_m', 'points_xy_m', 'triangles')):
            raise ValueError('affine shape native mesh differs from its original Project, law or refinement')
        indices = np.arange(len(actual.triangles))
        bary = np.tile(np.eye(3), (len(indices), 1, 1))
        for _ in range(maximum-level):
            bary = np.einsum('cij,njk->ncik', REFERENCE[SPLIT], bary).reshape(-1, 3, 3)
            indices = np.repeat(indices, 4)
        parents.append(indices); barycentrics.append(bary)
        vertices.append(np.einsum('nij,njk->nik', bary, actual.points_xy_m[actual.triangles[indices]]))
    # Columns of each J map the common local triangle to an actual physical cell.
    jacobians = [np.swapaxes(v[:, 1:]-v[:, :1], 1, 2) for v in vertices]
    determinants = [j[:, 0, 0]*j[:, 1, 1]-j[:, 0, 1]*j[:, 1, 0] for j in jacobians]
    if any(not np.isfinite(j).all() for j in jacobians) or any(
            not np.isfinite(d).all() or np.any(d <= 0) for d in determinants):
        raise ValueError('affine shape physical comparison triangles are unresolved')
    # adj(J_current * inv(J_previous)) transports transverse cutoff E into
    # the previous frame, consistent with the existing affine-map convention.
    effective = jacobians[1] @ np.linalg.inv(jacobians[0])
    transport = np.empty_like(effective)
    transport[:, 0, 0] = effective[:, 1, 1]; transport[:, 1, 1] = effective[:, 0, 0]
    transport[:, 0, 1] = -effective[:, 0, 1]; transport[:, 1, 0] = -effective[:, 1, 0]
    if not np.isfinite(transport).all() or np.any(np.linalg.det(transport) <= 0):
        raise ValueError('affine shape field transport is unresolved')
    arrays = (*parents, *barycentrics, vertices[0], determinants[0])
    for array in (*arrays, transport):
        array.setflags(write=False)
    return PlanarTrackingOverlay(*arrays), transport
