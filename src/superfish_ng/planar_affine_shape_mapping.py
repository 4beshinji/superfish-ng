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
    from .planar_reference_partition import reference_shape_overlay
    return reference_shape_overlay(previous, current, mapping, max_overlay_triangles=max_overlay_triangles,
                                   label='affine shape')
