# SPDX-License-Identifier: Apache-2.0
"""Explicit linear isotropic dielectrics on an axisymmetric material partition."""
from dataclasses import dataclass,field
import numpy as np
from .config import keys,positive
from .rf_materials import LinearRFMaterial,RFMaterialRegion,RFMaterialPartition


@dataclass(frozen=True)
class LinearDielectric:
    id: str
    epsilon_r: float

    def __post_init__(self):
        if type(self.id) is not str or not self.id.strip():raise ValueError('dielectric id must be a nonempty string')
        try: value=positive(self.epsilon_r,'dielectric epsilon_r')
        except OverflowError as exc: raise ValueError('dielectric epsilon_r must be a finite positive number') from exc
        object.__setattr__(self,'epsilon_r',value)

    def to_dict(self):return dict(id=self.id,type='linear_isotropic_dielectric',epsilon_r=self.epsilon_r)

    @classmethod
    def from_dict(cls,data):
        names=['id','type','epsilon_r'];keys(data,names,names,'linear dielectric')
        if data['type']!='linear_isotropic_dielectric':raise ValueError('only positive real linear_isotropic_dielectric is supported')
        return cls(data['id'],data['epsilon_r'])


@dataclass(frozen=True)
class DielectricRegion:
    id: str
    material: str
    cell_indices: tuple

    def __post_init__(self):
        # Region IDs and cell ownership are geometric data, independent of
        # the equation. Reuse their strict validation without exposing RF.
        checked=RFMaterialRegion(self.id,self.material,self.cell_indices)
        object.__setattr__(self,'cell_indices',checked.cell_indices)

    def to_dict(self):return dict(id=self.id,material=self.material,cell_indices=list(self.cell_indices))

    @classmethod
    def from_dict(cls,data):
        names=['id','material','cell_indices'];keys(data,names,names,'dielectric region')
        if type(data['cell_indices']) is not list:raise ValueError('dielectric cell_indices must be a JSON list')
        return cls(**data)


@dataclass(frozen=True,eq=False)
class AxisymmetricDielectricPartition:
    mesh: object
    materials: tuple
    regions: tuple
    epsilon_r: np.ndarray=field(init=False)
    cell_region_indices: np.ndarray=field(init=False)
    interface_edges: np.ndarray=field(init=False)
    interface_cells: np.ndarray=field(init=False)
    interface_region_indices: np.ndarray=field(init=False)
    interface_coefficient_jumps: np.ndarray=field(init=False)
    boundary_region_indices: np.ndarray=field(init=False)
    region_area_m2: np.ndarray=field(init=False)
    region_volume_m3: np.ndarray=field(init=False)

    def __post_init__(self):
        for name,cls in (('materials',LinearDielectric),('regions',DielectricRegion)):
            values=getattr(self,name)
            if not isinstance(values,(list,tuple)) or not values or any(type(v) is not cls for v in values):
                raise ValueError('dielectric '+name+' requires explicit '+cls.__name__+' values')
            object.__setattr__(self,name,tuple(cls.from_dict(v.to_dict()) for v in values))
        # This existing validator supplies only mesh/region topology, SI
        # measures and real coefficients. No RF matrix, solver or convention
        # is used. Permeability is an internal constant, absent from the API.
        try:
            checked=RFMaterialPartition(self.mesh,[LinearRFMaterial(m.id,m.epsilon_r,1.) for m in self.materials],
                [RFMaterialRegion(r.id,r.material,r.cell_indices) for r in self.regions])
        except ValueError as exc:raise ValueError(str(exc).replace('RF material','dielectric').replace('RF materials','dielectrics')) from exc
        object.__setattr__(self,'mesh',checked.mesh)
        for name in ('epsilon_r','cell_region_indices','interface_edges','interface_cells','interface_region_indices',
                     'interface_coefficient_jumps','boundary_region_indices','region_area_m2','region_volume_m3'):
            object.__setattr__(self,name,getattr(checked,name))

    def to_dict(self):
        return dict(format='superfish_ng_axisymmetric_dielectric_partition',schema_version=1,coordinates='axisymmetric_rz',
            mesh=self.mesh.to_dict(),materials=[m.to_dict() for m in self.materials],regions=[r.to_dict() for r in self.regions])

    @classmethod
    def from_dict(cls,data):
        names=['format','schema_version','coordinates','mesh','materials','regions'];keys(data,names,names,'axisymmetric dielectric partition')
        if (data['format']!='superfish_ng_axisymmetric_dielectric_partition' or type(data['schema_version']) is not int
            or data['schema_version']!=1 or data['coordinates']!='axisymmetric_rz'):
            raise ValueError('expected superfish_ng_axisymmetric_dielectric_partition schema_version 1, axisymmetric_rz coordinates')
        from .meridional_mesh import MeridionalMesh
        from .axis_connected_mesh import AxisConnectedMesh
        if not isinstance(data['mesh'],dict) or data['mesh'].get('format') not in ('superfish_ng_meridional_mesh','superfish_ng_axis_connected_mesh'):
            raise ValueError('axisymmetric dielectrics require an explicit straight meridional mesh; planar/curved geometry is unsupported')
        cls_mesh=AxisConnectedMesh if data['mesh']['format']=='superfish_ng_axis_connected_mesh' else MeridionalMesh
        if type(data['materials']) is not list or type(data['regions']) is not list:raise ValueError('dielectric materials and regions must be JSON lists')
        return cls(cls_mesh.from_dict(data['mesh']),[LinearDielectric.from_dict(m) for m in data['materials']],
                   [DielectricRegion.from_dict(r) for r in data['regions']])
