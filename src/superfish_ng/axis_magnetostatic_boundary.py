# SPDX-License-Identifier: Apache-2.0
"""Explicit fixed Aphi/r, oriented tangential H and axis regularity boundaries."""
from dataclasses import dataclass
import math
import numpy as np
from .config import keys


def finite_signed(value,name):
    try: valid=not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value)
    except OverflowError: valid=False
    if not valid: raise ValueError(name+' must be a finite signed real number')
    return float(value)


@dataclass(frozen=True)
class AxisMagnetostaticBoundary:
    id: str
    kind: str
    edge_indices: tuple
    value: float | None = None

    def __post_init__(self):
        if type(self.id) is not str or not self.id.strip():raise ValueError('axis magnetostatic boundary id must be nonempty')
        kinds=('fixed_aphi_over_r','tangential_h','axis_regularity')
        if self.kind not in kinds:raise ValueError('axis magnetostatic boundary kind must be '+', '.join(kinds))
        edges=self.edge_indices
        if (not isinstance(edges,(list,tuple)) or not edges or any(type(v) is not int or v<0 or v>np.iinfo(np.int64).max for v in edges)
            or any(a>=b for a,b in zip(edges,edges[1:]))):
            raise ValueError('axis magnetostatic edge_indices must be nonempty strictly increasing nonnegative integers')
        object.__setattr__(self,'edge_indices',tuple(edges))
        if self.kind=='axis_regularity':
            if self.value is not None:raise ValueError('axis_regularity has no prescribed Aphi/r or tangential H')
        else:object.__setattr__(self,'value',finite_signed(self.value,'boundary '+self.id+' value'))

    def to_dict(self):
        data=dict(id=self.id,kind=self.kind,edge_indices=list(self.edge_indices))
        if self.kind=='fixed_aphi_over_r':data['aphi_over_r_t']=self.value
        elif self.kind=='tangential_h':data['tangential_h_a_per_m']=self.value
        return data

    @classmethod
    def from_dict(cls,data):
        if not isinstance(data,dict):raise ValueError('axis magnetostatic boundary must be an object')
        if type(data.get('kind')) is not str:raise ValueError('axis magnetostatic boundary kind must be a string')
        name={'fixed_aphi_over_r':'aphi_over_r_t','tangential_h':'tangential_h_a_per_m','axis_regularity':None}.get(data.get('kind'))
        fields=['id','kind','edge_indices']+([name] if name else [])
        keys(data,fields,fields,'axis magnetostatic boundary')
        if type(data['edge_indices']) is not list:raise ValueError('axis magnetostatic edge_indices must be a JSON list')
        return cls(data['id'],data['kind'],data['edge_indices'],data.get(name) if name else None)


def validate_axis_magnetic_boundaries(mesh,boundaries):
    if not isinstance(boundaries,(list,tuple)) or not boundaries or any(type(b) is not AxisMagnetostaticBoundary for b in boundaries):
        raise ValueError('explicit AxisMagnetostaticBoundary values are required for every boundary edge')
    boundaries=tuple(AxisMagnetostaticBoundary.from_dict(b.to_dict()) for b in boundaries)
    if len({b.id for b in boundaries})!=len(boundaries):raise ValueError('axis magnetostatic boundary ids must be unique')
    count=len(mesh.boundary_edges);owners=np.full(count,-1,dtype=np.int64)
    is_axis=np.all(mesh.points_rz_m[mesh.boundary_edges,0]==0.,axis=1)
    fixed_nodes={}
    for i,boundary in enumerate(boundaries):
        edges=np.asarray(boundary.edge_indices,dtype=np.int64)
        if np.any(edges>=count) or np.any(owners[edges]!=-1):raise ValueError('axis magnetostatic boundary edges must be in range and assigned exactly once')
        owners[edges]=i
        if np.any(is_axis[edges]!=(boundary.kind=='axis_regularity')):
            raise ValueError('axis edges require axis_regularity; fixed Aphi/r and tangential H boundaries require non-axis edges')
        if boundary.kind=='fixed_aphi_over_r':
            for node in np.unique(mesh.boundary_edges[edges]):
                if node in fixed_nodes:raise ValueError('fixed Aphi/r boundaries share a node; merge connected fixed edges under one boundary id')
                fixed_nodes[node]=boundary.id
    if np.any(owners<0):raise ValueError('every axis magnetostatic boundary edge must be explicit; no implicit ground or external boundary')
    owners.setflags(write=False)
    return boundaries,owners
