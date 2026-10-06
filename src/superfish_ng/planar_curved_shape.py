# SPDX-License-Identifier: Apache-2.0
"""Proper finite polynomial affine laws on original complete curved xy nodes."""
from dataclasses import dataclass, replace
from fractions import Fraction
import numpy as np
from .config import keys
from .planar_affine_shape import PlanarAffineShapeLaw
from .planar_project import PlanarProject
from .planar_curved import PlanarCurvedCase, PlanarCurvedDomain
from .planar_curved_comparison import PlanarCurvedComparisonDomain


@dataclass(frozen=True)
class PlanarCurvedAffineShapeLaw:
    law: PlanarAffineShapeLaw

    def __post_init__(self):
        if type(self.law) is not PlanarAffineShapeLaw:
            raise ValueError('curved planar shape requires a complete PlanarAffineShapeLaw')
        law = PlanarAffineShapeLaw.from_dict(self.law.to_dict())
        # The shared exact root count has already excluded determinant zeros
        # over the closed interval. Its sign therefore stays constant there.
        matrix,_ = law.exact_transform(law.to_dict()['bounds'][0])
        if matrix[0][0]*matrix[1][1]-matrix[0][1]*matrix[1][0] <= 0:
            raise ValueError('curved planar shape requires positive determinant throughout the closed interval; reversed orientation needs a separate quadratic chart contract')
        object.__setattr__(self,'law',law)

    @property
    def bounds(self):return self.law.bounds

    def exact_transform(self,value):return self.law.exact_transform(value)

    def to_dict(self):
        return dict(kind='polynomial_affine_curved_xy',schema_version=1,
                    orientation='preserving',shape_law=self.law.to_dict())

    @classmethod
    def from_dict(cls,data):
        names=['kind','schema_version','orientation','shape_law']
        keys(data,names,names,'curved planar shape law')
        if (data['kind']!='polynomial_affine_curved_xy' or type(data['schema_version']) is not int
                or data['schema_version']!=1 or data['orientation']!='preserving'):
            raise ValueError('expected preserving curved planar polynomial affine shape schema_version 1')
        return cls(PlanarAffineShapeLaw.from_dict(data['shape_law']))

    def project(self,original,value):
        """Regenerate every original P2 coordinate, rounding once into binary64.

        No cumulative deformation, field transport, analytic projection or
        eigensolve occurs here. All original topology/PEC nodes are retained.
        Exact interval nonsingularity does not guarantee floating resolution;
        the complete mapped Domain validates that separately before any FEM.
        """
        if type(original) is not PlanarProject or type(original.case) is not PlanarCurvedCase:
            raise ValueError('curved planar shape requires an original complete quadratic PlanarProject')
        original=PlanarProject.from_dict(original.to_dict())
        matrix,translation=self.exact_transform(value)
        points=original.case.domain.points_xy_m
        try:
            mapped=np.asarray([[float(sum(matrix[axis][j]*Fraction(float(p[j])) for j in (0,1))+translation[axis])
                                for axis in (0,1)] for p in points])
        except (ValueError,OverflowError) as exc:
            raise ValueError('curved planar shape coordinates are outside finite binary64 range') from exc
        if not np.isfinite(mapped).all():
            raise ValueError('curved planar shape coordinates are outside finite binary64 range')
        domain=PlanarCurvedDomain(mapped,original.case.domain.cell_nodes,original.case.domain.boundary_nodes,
                                 original.case.max_geometry_boxes)
        return replace(original,case=replace(original.case,domain=domain))

    def comparison(self,original,previous_value,current_value):
        """Full regenerated quadratic correspondence, without frequency rules."""
        a,b=(self.project(original,value).case for value in (previous_value,current_value))
        return PlanarCurvedComparisonDomain(a.domain,b.domain,'declared_quadratic','binary64_roundoff',
                                           original.case.max_geometry_boxes)
