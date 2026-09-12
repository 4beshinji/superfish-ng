# SPDX-License-Identifier: Apache-2.0
"""Positive linear magnetic materials and explicit planar cell ownership."""
from dataclasses import dataclass,field
import numpy as np
from .config import keys,positive
from .rf_materials import RFMaterialRegion
from .planar_mesh import PlanarMesh
from .constants import MU0


@dataclass(frozen=True)
class LinearMagneticMaterial:
    id: str
    mu_r: float

    def __post_init__(self):
        if type(self.id) is not str or not self.id.strip():raise ValueError('magnetic material id must be a nonempty string')
        try:value=positive(self.mu_r,'magnetic material mu_r')
        except OverflowError as exc:raise ValueError('magnetic material mu_r must be finite and positive') from exc
        object.__setattr__(self,'mu_r',value)

    def to_dict(self):return dict(id=self.id,type='linear_isotropic_magnetic_material',mu_r=self.mu_r)

    @classmethod
    def from_dict(cls,data):
        names=['id','type','mu_r'];keys(data,names,names,'linear magnetic material')
        if data['type']!='linear_isotropic_magnetic_material':raise ValueError('only positive real linear_isotropic_magnetic_material is supported')
        return cls(data['id'],data['mu_r'])


@dataclass(frozen=True)
class MagneticRegion:
    id: str
    material: str
    cell_indices: tuple

    def __post_init__(self):
        # Reuse only identifier and integer ownership validation, with no
        # RF coefficients, matrices, boundary or phasor semantics.
        checked=RFMaterialRegion(self.id,self.material,self.cell_indices)
        object.__setattr__(self,'cell_indices',checked.cell_indices)

    def to_dict(self):return dict(id=self.id,material=self.material,cell_indices=list(self.cell_indices))

    @classmethod
    def from_dict(cls,data):
        names=['id','material','cell_indices'];keys(data,names,names,'magnetic region')
        if type(data['cell_indices']) is not list:raise ValueError('magnetic cell_indices must be a JSON list')
        return cls(**data)


@dataclass(frozen=True,eq=False)
class PlanarMagneticPartition:
    mesh: PlanarMesh
    materials: tuple
    regions: tuple
    cell_region_indices: np.ndarray=field(init=False)
    mu_r: np.ndarray=field(init=False)
    reluctivity_m_per_h: np.ndarray=field(init=False)
    interface_edges: np.ndarray=field(init=False)
    interface_cells: np.ndarray=field(init=False)
    interface_region_indices: np.ndarray=field(init=False)
    interface_coefficient_jumps: np.ndarray=field(init=False)
    boundary_region_indices: np.ndarray=field(init=False)
    region_area_m2: np.ndarray=field(init=False)

    def __post_init__(self):
        if type(self.mesh) is not PlanarMesh:raise ValueError('planar magnetic materials require an explicit simple-polygon PlanarMesh; curved cells and holes are unsupported')
        mesh=PlanarMesh.create(self.mesh.polygon_xy_m,self.mesh.points_xy_m,self.mesh.triangles);object.__setattr__(self,'mesh',mesh)
        for name,cls in (('materials',LinearMagneticMaterial),('regions',MagneticRegion)):
            values=getattr(self,name)
            if not isinstance(values,(list,tuple)) or not values or any(type(v) is not cls for v in values):raise ValueError('planar '+name+' requires explicit '+cls.__name__+' values')
            values=tuple(cls.from_dict(v.to_dict()) for v in values)
            if len({v.id for v in values})!=len(values):raise ValueError('planar '+name+' IDs must be unique')
            object.__setattr__(self,name,values)
        materials={m.id:m.mu_r for m in self.materials}
        if {r.material for r in self.regions}!=set(materials):raise ValueError('every planar region must reference a declared material and every material must be used')
        count=len(mesh.triangles);owners=np.full(count,-1,dtype=np.int64);permeability=np.empty(count)
        for index,region in enumerate(self.regions):
            if region.cell_indices[-1]>=count:raise ValueError('planar magnetic cell index is outside the mesh')
            cells=np.asarray(region.cell_indices,dtype=np.int64)
            if np.any(owners[cells]!=-1):raise ValueError('planar magnetic regions overlap')
            owners[cells]=index;permeability[cells]=materials[region.material]
        if np.any(owners<0):raise ValueError('planar magnetic regions must cover every cell exactly once; no implicit vacuum')
        incidence={}
        for index,triangle in enumerate(mesh.triangles):
            for a,b in ((0,1),(1,2),(2,0)):
                edge=tuple(sorted((int(triangle[a]),int(triangle[b]))));incidence.setdefault(edge,[]).append(index)
        edges=[];cells=[];regions=[];jumps=[]
        for edge,adjacent in sorted(incidence.items()):
            if len(adjacent)==2 and owners[adjacent[0]]!=owners[adjacent[1]]:
                edges.append(edge);cells.append(adjacent);regions.append(owners[adjacent]);jumps.append(permeability[adjacent[0]]!=permeability[adjacent[1]])
        vertices=mesh.points_xy_m[mesh.triangles];a=vertices[:,1]-vertices[:,0];b=vertices[:,2]-vertices[:,0]
        area=(a[:,0]*b[:,1]-a[:,1]*b[:,0])/2;region_area=np.bincount(owners,weights=area,minlength=len(self.regions))
        if not np.isfinite(region_area).all() or np.any(region_area<=0):raise ValueError('planar magnetic region areas must remain finite and positive')
        with np.errstate(over='ignore',under='ignore',divide='ignore',invalid='ignore'):reluctivity=(1./MU0)/permeability
        if not np.isfinite(reluctivity).all() or np.any(reluctivity<=0):raise ValueError('magnetic reluctivity 1/(mu0*mu_r) must remain finite and positive in SI')
        values=dict(cell_region_indices=owners,mu_r=permeability,reluctivity_m_per_h=reluctivity,interface_edges=np.asarray(edges,dtype=np.int64).reshape(-1,2),
            interface_cells=np.asarray(cells,dtype=np.int64).reshape(-1,2),interface_region_indices=np.asarray(regions,dtype=np.int64).reshape(-1,2),
            interface_coefficient_jumps=np.asarray(jumps,dtype=bool),boundary_region_indices=owners[mesh.boundary_cells].copy(),region_area_m2=region_area)
        for name,value in values.items():value.setflags(write=False);object.__setattr__(self,name,value)

    def to_dict(self):
        # PlanarMesh supplies topology only. Its RF serialization carries a
        # PEC declaration, so this static geometry has a neutral contract.
        return dict(format='superfish_ng_planar_magnetic_partition',schema_version=1,coordinates='cartesian_xy',
            geometry=dict(type='explicit_straight_simple_polygon',polygon_xy_m=self.mesh.polygon_xy_m.tolist(),
                points_xy_m=self.mesh.points_xy_m.tolist(),triangles=self.mesh.triangles.tolist()),
            materials=[m.to_dict() for m in self.materials],regions=[r.to_dict() for r in self.regions])

    @classmethod
    def from_dict(cls,data):
        names=['format','schema_version','coordinates','geometry','materials','regions'];keys(data,names,names,'planar magnetic partition')
        if data['format']!='superfish_ng_planar_magnetic_partition' or type(data['schema_version']) is not int or data['schema_version']!=1 or data['coordinates']!='cartesian_xy':
            raise ValueError('expected superfish_ng_planar_magnetic_partition version 1, cartesian_xy coordinates')
        geometry=data['geometry'];names=['type','polygon_xy_m','points_xy_m','triangles'];keys(geometry,names,names,'planar magnetic geometry')
        if geometry['type']!='explicit_straight_simple_polygon':raise ValueError('planar magnetic materials require explicit straight simple-polygon geometry')
        if type(data['materials']) is not list or type(data['regions']) is not list:raise ValueError('planar materials and regions must be JSON lists')
        mesh=PlanarMesh.create(geometry['polygon_xy_m'],geometry['points_xy_m'],geometry['triangles'])
        return cls(mesh,[LinearMagneticMaterial.from_dict(m) for m in data['materials']],[MagneticRegion.from_dict(r) for r in data['regions']])
