# SPDX-License-Identifier: Apache-2.0
"""Explicit fixed Az and oriented tangential-H boundaries for planar magnetostatics."""
from dataclasses import dataclass
import numpy as np
from .config import keys
from .electrostatic_boundary import finite_signed,static_field_coordinates as _static_coordinates


def magnetic_field_coordinates(cell_indices,barycentric,cell_count):
    try:return _static_coordinates(cell_indices,barycentric,cell_count)
    except ValueError as exc:raise ValueError(str(exc).replace('electrostatic','magnetostatic')) from exc


@dataclass(frozen=True)
class MagnetostaticBoundary:
    id: str
    kind: str
    edge_indices: tuple
    value: float

    def __post_init__(self):
        if type(self.id) is not str or not self.id.strip():raise ValueError('magnetostatic boundary id must be nonempty')
        if type(self.kind) is not str or self.kind not in ('fixed_az','tangential_h'):raise ValueError('magnetostatic boundary kind must be fixed_az or tangential_h')
        edges=self.edge_indices
        if (not isinstance(edges,(list,tuple)) or not edges or any(type(v) is not int or v<0 or v>np.iinfo(np.int64).max for v in edges)
            or any(a>=b for a,b in zip(edges,edges[1:]))):raise ValueError('magnetostatic edge_indices must be nonempty strictly increasing nonnegative integers')
        object.__setattr__(self,'edge_indices',tuple(edges));object.__setattr__(self,'value',finite_signed(self.value,'magnetostatic boundary '+self.id+' value'))

    def to_dict(self):
        name='az_wb_per_m' if self.kind=='fixed_az' else 'tangential_h_a_per_m'
        return dict(id=self.id,kind=self.kind,edge_indices=list(self.edge_indices),**{name:self.value})

    @classmethod
    def from_dict(cls,data):
        if not isinstance(data,dict) or type(data.get('kind')) is not str:raise ValueError('magnetostatic boundary requires an object with a string kind')
        name={'fixed_az':'az_wb_per_m','tangential_h':'tangential_h_a_per_m'}.get(data['kind'])
        if name is None:raise ValueError('magnetostatic boundary kind must be fixed_az or tangential_h')
        names=['id','kind','edge_indices',name];keys(data,names,names,'magnetostatic boundary')
        if type(data['edge_indices']) is not list:raise ValueError('magnetostatic edge_indices must be a JSON list')
        return cls(data['id'],data['kind'],data['edge_indices'],data[name])
