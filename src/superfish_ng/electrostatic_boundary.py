# SPDX-License-Identifier: Apache-2.0
"""Explicit static electrode, displacement and axis boundary assignments."""
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
class ElectrostaticBoundary:
    id: str
    kind: str
    edge_indices: tuple
    value: float | None = None

    def __post_init__(self):
        if type(self.id) is not str or not self.id.strip():raise ValueError('electrostatic boundary id must be nonempty')
        kinds=('electrode_potential','outward_displacement','axis_symmetry')
        if self.kind not in kinds:raise ValueError('electrostatic boundary kind must be '+', '.join(kinds))
        edges=self.edge_indices
        if (not isinstance(edges,(list,tuple)) or not edges or any(type(v) is not int or v<0 or v>np.iinfo(np.int64).max for v in edges)
            or any(a>=b for a,b in zip(edges,edges[1:]))):
            raise ValueError('electrostatic edge_indices must be nonempty strictly increasing nonnegative integers')
        object.__setattr__(self,'edge_indices',tuple(edges))
        if self.kind=='axis_symmetry':
            if self.value is not None:raise ValueError('axis_symmetry has no electrode potential or surface displacement')
        else:object.__setattr__(self,'value',finite_signed(self.value,'boundary '+self.id+' value'))

    def to_dict(self):
        data=dict(id=self.id,kind=self.kind,edge_indices=list(self.edge_indices))
        if self.kind=='electrode_potential':data['potential_v']=self.value
        elif self.kind=='outward_displacement':data['outward_displacement_c_per_m2']=self.value
        return data

    @classmethod
    def from_dict(cls,data):
        if not isinstance(data,dict):raise ValueError('electrostatic boundary must be an object')
        if type(data.get('kind')) is not str:raise ValueError('electrostatic boundary kind must be a string')
        name={'electrode_potential':'potential_v','outward_displacement':'outward_displacement_c_per_m2','axis_symmetry':None}.get(data.get('kind'))
        fields=['id','kind','edge_indices']+([name] if name else [])
        keys(data,fields,fields,'electrostatic boundary')
        if type(data['edge_indices']) is not list:raise ValueError('electrostatic edge_indices must be a JSON list')
        return cls(data['id'],data['kind'],data['edge_indices'],data.get(name) if name else None)


def validate_boundaries(mesh,boundaries):
    if not isinstance(boundaries,(list,tuple)) or not boundaries or any(type(b) is not ElectrostaticBoundary for b in boundaries):
        raise ValueError('explicit ElectrostaticBoundary values are required for every boundary edge')
    boundaries=tuple(ElectrostaticBoundary.from_dict(b.to_dict()) for b in boundaries)
    if len({b.id for b in boundaries})!=len(boundaries):raise ValueError('electrostatic boundary ids must be unique')
    count=len(mesh.boundary_edges);owners=np.full(count,-1,dtype=np.int64)
    is_axis=np.all(mesh.points_rz_m[mesh.boundary_edges,0]==0.,axis=1)
    electrode_nodes={};electrodes=0
    for i,boundary in enumerate(boundaries):
        edges=np.asarray(boundary.edge_indices,dtype=np.int64)
        if np.any(edges>=count) or np.any(owners[edges]!=-1):raise ValueError('electrostatic boundary edges must be in range and assigned exactly once')
        owners[edges]=i
        if np.any(is_axis[edges]!=(boundary.kind=='axis_symmetry')):
            raise ValueError('axis edges require axis_symmetry; electrode and displacement boundaries require non-axis edges')
        if boundary.kind=='electrode_potential':
            electrodes+=1
            for node in np.unique(mesh.boundary_edges[edges]):
                if node in electrode_nodes:raise ValueError('electrodes share a node; merge connected conductor edges under one electrode id')
                electrode_nodes[node]=boundary.id
    if np.any(owners<0):raise ValueError('every electrostatic boundary edge must be explicit; no implicit ground or external boundary')
    if not electrodes:raise ValueError('at least one fixed-potential electrode is required; pure Neumann/gauge is unsupported')
    owners.setflags(write=False)
    return boundaries,owners
