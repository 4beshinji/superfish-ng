# SPDX-License-Identifier: Apache-2.0
"""Original-reference correspondence between polynomial piecewise trials."""
from dataclasses import dataclass
from .config import keys, integer
from .planar_piecewise_shape import PlanarPiecewiseShapeLaw
from .planar_project import PlanarProject
from .planar_polygon import PlanarPolygonCase
from .planar_reference_partition import reference_shape_overlay


@dataclass(frozen=True)
class PlanarPiecewiseShapeMapping:
    original_project: PlanarProject
    shape_law: PlanarPiecewiseShapeLaw
    previous_value: float
    current_value: float
    previous_refinements: int = 0
    current_refinements: int = 0

    def __post_init__(self):
        if type(self.original_project) is not PlanarProject or type(self.original_project.case) is not PlanarPolygonCase:
            raise ValueError('piecewise shape mapping requires the original explicit polygon Project')
        if type(self.shape_law) is not PlanarPiecewiseShapeLaw:
            raise ValueError('piecewise shape mapping requires PlanarPiecewiseShapeLaw')
        project = PlanarProject.from_dict(self.original_project.to_dict())
        law = PlanarPiecewiseShapeLaw.from_dict(self.shape_law.to_dict())
        for name in ('previous_value', 'current_value'):
            law.project(project, getattr(self, name))
        for name in ('previous_refinements', 'current_refinements'):
            integer(getattr(self, name), name, 0)
            if getattr(self, name) > 8:
                raise ValueError('piecewise shape mapping supports at most eight refinements')
        object.__setattr__(self, 'original_project', project)
        object.__setattr__(self, 'shape_law', law)

    def to_dict(self):
        return dict(name='polynomial_piecewise_xy_reference', original_project=self.original_project.to_dict(),
                    shape_law=self.shape_law.to_dict(), previous_value=self.previous_value,
                    current_value=self.current_value, previous_refinements=self.previous_refinements,
                    current_refinements=self.current_refinements)

    @classmethod
    def from_dict(cls, data):
        names = ['name', 'original_project', 'shape_law', 'previous_value', 'current_value',
                 'previous_refinements', 'current_refinements']
        keys(data, names, names, 'planar piecewise shape mapping')
        if data['name'] != 'polynomial_piecewise_xy_reference':
            raise ValueError('expected polynomial_piecewise_xy_reference mapping')
        return cls(PlanarProject.from_dict(data['original_project']), PlanarPiecewiseShapeLaw.from_dict(data['shape_law']),
                   data['previous_value'], data['current_value'], data['previous_refinements'], data['current_refinements'])


def piecewise_shape_overlay(previous, current, mapping, *, max_overlay_triangles=250000):
    if type(mapping) is not PlanarPiecewiseShapeMapping:
        raise ValueError('expected PlanarPiecewiseShapeMapping')
    mapping = PlanarPiecewiseShapeMapping.from_dict(mapping.to_dict())
    return reference_shape_overlay(previous, current, mapping, max_overlay_triangles=max_overlay_triangles,
                                   label='piecewise shape')
