# SPDX-License-Identifier: Apache-2.0
"""Explicit controls for bounded general-contour mesh generation."""
from dataclasses import dataclass, asdict
import math


@dataclass(frozen=True)
class ContourMeshControls:
    max_edge_m: float
    min_angle_deg: float = 10.
    max_triangles: int = 250000
    max_rounds: int = 12

    def __post_init__(self):
        if type(self.max_edge_m) not in (int,float) or not math.isfinite(self.max_edge_m) or self.max_edge_m<=0:
            raise ValueError('contour mesh max_edge_m must be finite and positive')
        if (type(self.min_angle_deg) not in (int,float) or not math.isfinite(self.min_angle_deg)
                or not 0<self.min_angle_deg<60):
            raise ValueError('contour mesh min_angle_deg must be finite and strictly between 0 and 60')
        for key in ('max_triangles','max_rounds'):
            value = getattr(self,key)
            if type(value) is not int or value<1:
                raise ValueError(f'contour mesh {key} must be a positive integer')

    @classmethod
    def from_dict(cls,data):
        from .config import keys
        keys(data,('max_edge_m','min_angle_deg','max_triangles','max_rounds'),('max_edge_m',),'mesh.contour_mesh')
        return cls(**data)

    def to_dict(self):
        return asdict(self)
