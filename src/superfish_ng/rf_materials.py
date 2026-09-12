# SPDX-License-Identifier: Apache-2.0
"""Explicit positive, lossless isotropic RF materials on straight meridional cells."""
from dataclasses import dataclass,field
import numpy as np
from .config import keys,positive,integer
from .meridional_mesh import MeridionalMesh
from .axis_connected_mesh import AxisConnectedMesh


def _identifier(value,label):
    if type(value) is not str or not value.strip():raise ValueError(label+' must be a nonempty string')
    return value


@dataclass(frozen=True)
class LinearRFMaterial:
    id: str
    epsilon_r: float
    mu_r: float

    def __post_init__(self):
        _identifier(self.id,'material id')
        for name in ('epsilon_r','mu_r'):object.__setattr__(self,name,positive(getattr(self,name),name))

    def to_dict(self):
        return dict(id=self.id,type='lossless_linear_isotropic',epsilon_r=self.epsilon_r,mu_r=self.mu_r)

    @classmethod
    def from_dict(cls,data):
        names=['id','type','epsilon_r','mu_r'];keys(data,names,names,'RF material')
        if data['type']!='lossless_linear_isotropic':
            raise ValueError('RF materials support only positive real lossless_linear_isotropic epsilon_r/mu_r; dispersion, loss and tensors are unsupported')
        return cls(data['id'],data['epsilon_r'],data['mu_r'])


@dataclass(frozen=True)
class RFMaterialRegion:
    id: str
    material: str
    cell_indices: tuple

    def __post_init__(self):
        _identifier(self.id,'region id');_identifier(self.material,'region material reference')
        if not isinstance(self.cell_indices,(list,tuple)) or not self.cell_indices:
            raise ValueError('RF material region requires a nonempty explicit cell_indices list')
        indices=tuple(integer(i,'region cell index',0) for i in self.cell_indices)
        if any(a>=b for a,b in zip(indices,indices[1:])):
            raise ValueError('region cell_indices must be strictly increasing with no duplicates')
        object.__setattr__(self,'cell_indices',indices)

    def to_dict(self):return dict(id=self.id,material=self.material,cell_indices=list(self.cell_indices))

    @classmethod
    def from_dict(cls,data):
        names=['id','material','cell_indices'];keys(data,names,names,'RF material region')
        if type(data['cell_indices']) is not list:raise ValueError('region cell_indices must be a JSON list')
        return cls(**data)


@dataclass(frozen=True,eq=False)
class RFMaterialPartition:
    mesh: object
    materials: tuple
    regions: tuple
    cell_region_indices: np.ndarray=field(init=False)
    epsilon_r: np.ndarray=field(init=False)
    mu_r: np.ndarray=field(init=False)
    interface_edges: np.ndarray=field(init=False)
    interface_cells: np.ndarray=field(init=False)
    interface_region_indices: np.ndarray=field(init=False)
    interface_coefficient_jumps: np.ndarray=field(init=False)
    boundary_region_indices: np.ndarray=field(init=False)
    region_area_m2: np.ndarray=field(init=False)
    region_volume_m3: np.ndarray=field(init=False)

    def __post_init__(self):
        if type(self.mesh) not in (MeridionalMesh,AxisConnectedMesh):
            raise ValueError('RF material partition requires an explicit straight MeridionalMesh or AxisConnectedMesh; curved cells are unsupported')
        mesh=type(self.mesh).from_dict(self.mesh.to_dict());object.__setattr__(self,'mesh',mesh)
        for name,cls in (('materials',LinearRFMaterial),('regions',RFMaterialRegion)):
            values=getattr(self,name)
            if not isinstance(values,(list,tuple)) or not values or any(type(v) is not cls for v in values):
                raise ValueError('RF '+name+' requires a nonempty list of explicit '+cls.__name__+' values')
            values=tuple(cls.from_dict(v.to_dict()) for v in values)
            if len({v.id for v in values})!=len(values):raise ValueError('RF '+name+' IDs must be unique')
            object.__setattr__(self,name,values)
        materials={m.id:m for m in self.materials};used={r.material for r in self.regions}
        if used!=set(materials):raise ValueError('each region must reference a declared material, and every declared material must be used')
        count=len(mesh.triangles);owners=np.full(count,-1,dtype=np.int64)
        eps=np.empty(count);mu=np.empty(count)
        for index,region in enumerate(self.regions):
            if region.cell_indices[-1]>=count:raise ValueError('region cell index is outside the declared mesh')
            cells=np.asarray(region.cell_indices,dtype=np.int64)
            if np.any(owners[cells]!=-1):raise ValueError('RF material regions overlap on a mesh cell')
            owners[cells]=index;material=materials[region.material];eps[cells]=material.epsilon_r;mu[cells]=material.mu_r
        if np.any(owners==-1):raise ValueError('RF material regions must cover every cell exactly once; no implicit vacuum is assigned')
        incidence={}
        for cell,tri in enumerate(mesh.triangles):
            for a,b in ((0,1),(1,2),(2,0)):
                edge=tuple(sorted((int(tri[a]),int(tri[b]))));incidence.setdefault(edge,[]).append(cell)
        edges=[];cells=[];regions=[];jumps=[]
        for edge,adjacent in sorted(incidence.items()):
            if len(adjacent)==2:
                a,b=adjacent
                if owners[a]!=owners[b]:
                    edges.append(edge);cells.append([a,b]);regions.append([owners[a],owners[b]])
                    jumps.append(eps[a]!=eps[b] or mu[a]!=mu[b])
        vertices=mesh.points_rz_m[mesh.triangles];a=vertices[:,1]-vertices[:,0];b=vertices[:,2]-vertices[:,0]
        area=(a[:,0]*b[:,1]-a[:,1]*b[:,0])/2
        volume=2*np.pi*area*vertices[:,:,0].mean(axis=1)
        region_area=np.bincount(owners,weights=area,minlength=len(self.regions))
        region_volume=np.bincount(owners,weights=volume,minlength=len(self.regions))
        if not np.isfinite([*region_area,*region_volume]).all() or np.any(region_area<=0) or np.any(region_volume<=0):
            raise ValueError('RF region area and volume must remain finite and positive in SI arithmetic')
        values=dict(cell_region_indices=owners,epsilon_r=eps,mu_r=mu,
            interface_edges=np.asarray(edges,dtype=np.int64).reshape(-1,2),interface_cells=np.asarray(cells,dtype=np.int64).reshape(-1,2),
            interface_region_indices=np.asarray(regions,dtype=np.int64).reshape(-1,2),interface_coefficient_jumps=np.asarray(jumps,dtype=bool),
            boundary_region_indices=owners[mesh.boundary_cells].copy(),region_area_m2=region_area,region_volume_m3=region_volume)
        for name,value in values.items():value.setflags(write=False);object.__setattr__(self,name,value)

    def to_dict(self):
        return dict(format='superfish_ng_rf_material_partition',schema_version=1,mesh=self.mesh.to_dict(),
            materials=[m.to_dict() for m in self.materials],regions=[r.to_dict() for r in self.regions])

    @classmethod
    def from_dict(cls,data):
        names=['format','schema_version','mesh','materials','regions'];keys(data,names,names,'RF material partition')
        if data['format']!='superfish_ng_rf_material_partition' or type(data['schema_version']) is not int or data['schema_version']!=1:
            raise ValueError('expected superfish_ng_rf_material_partition schema_version 1')
        if not isinstance(data['mesh'],dict) or data['mesh'].get('format') not in ('superfish_ng_meridional_mesh','superfish_ng_axis_connected_mesh'):
            raise ValueError('material partition requires a complete straight meridional mesh')
        cls_mesh=AxisConnectedMesh if data['mesh']['format']=='superfish_ng_axis_connected_mesh' else MeridionalMesh
        if type(data['materials']) is not list or type(data['regions']) is not list:raise ValueError('materials and regions must be JSON arrays')
        return cls(cls_mesh.from_dict(data['mesh']),[LinearRFMaterial.from_dict(m) for m in data['materials']],
                   [RFMaterialRegion.from_dict(r) for r in data['regions']])
