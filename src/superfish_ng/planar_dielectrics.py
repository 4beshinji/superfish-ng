# SPDX-License-Identifier: Apache-2.0
"""Explicit planar dielectrics and geometric interfaces, with no boundary physics."""
from dataclasses import dataclass,field
import numpy as np
from .config import keys
from .dielectrics import LinearDielectric,DielectricRegion
from .planar_mesh import PlanarMesh


@dataclass(frozen=True,eq=False)
class PlanarDielectricPartition:
    mesh: PlanarMesh
    materials: tuple
    regions: tuple
    cell_region_indices: np.ndarray=field(init=False)
    epsilon_r: np.ndarray=field(init=False)
    interface_edges: np.ndarray=field(init=False)
    interface_cells: np.ndarray=field(init=False)
    interface_region_indices: np.ndarray=field(init=False)
    interface_coefficient_jumps: np.ndarray=field(init=False)
    boundary_region_indices: np.ndarray=field(init=False)
    region_area_m2: np.ndarray=field(init=False)

    def __post_init__(self):
        if type(self.mesh) is not PlanarMesh:raise ValueError('planar dielectrics require an explicit simple-polygon PlanarMesh; curved cells and holes are unsupported')
        mesh=PlanarMesh.create(self.mesh.polygon_xy_m,self.mesh.points_xy_m,self.mesh.triangles);object.__setattr__(self,'mesh',mesh)
        for name,cls in (('materials',LinearDielectric),('regions',DielectricRegion)):
            values=getattr(self,name)
            if not isinstance(values,(list,tuple)) or not values or any(type(v) is not cls for v in values):raise ValueError('planar '+name+' requires explicit '+cls.__name__+' values')
            values=tuple(cls.from_dict(v.to_dict()) for v in values)
            if len({v.id for v in values})!=len(values):raise ValueError('planar '+name+' IDs must be unique')
            object.__setattr__(self,name,values)
        materials={m.id:m.epsilon_r for m in self.materials}
        if {r.material for r in self.regions}!=set(materials):raise ValueError('every planar region must reference a declared material and every material must be used')
        count=len(mesh.triangles);owners=np.full(count,-1,dtype=np.int64);epsilon=np.empty(count)
        for index,region in enumerate(self.regions):
            if region.cell_indices[-1]>=count:raise ValueError('planar dielectric cell index is outside the mesh')
            cells=np.asarray(region.cell_indices,dtype=np.int64)
            if np.any(owners[cells]!=-1):raise ValueError('planar dielectric regions overlap')
            owners[cells]=index;epsilon[cells]=materials[region.material]
        if np.any(owners<0):raise ValueError('planar dielectric regions must cover every cell exactly once; no implicit vacuum')
        incidence={}
        for index,triangle in enumerate(mesh.triangles):
            for a,b in ((0,1),(1,2),(2,0)):
                edge=tuple(sorted((int(triangle[a]),int(triangle[b]))));incidence.setdefault(edge,[]).append(index)
        edges=[];cells=[];regions=[];jumps=[]
        for edge,adjacent in sorted(incidence.items()):
            if len(adjacent)==2 and owners[adjacent[0]]!=owners[adjacent[1]]:
                edges.append(edge);cells.append(adjacent);regions.append(owners[adjacent]);jumps.append(epsilon[adjacent[0]]!=epsilon[adjacent[1]])
        vertices=mesh.points_xy_m[mesh.triangles];a=vertices[:,1]-vertices[:,0];b=vertices[:,2]-vertices[:,0]
        area=(a[:,0]*b[:,1]-a[:,1]*b[:,0])/2;region_area=np.bincount(owners,weights=area,minlength=len(self.regions))
        if not np.isfinite(region_area).all() or np.any(region_area<=0):raise ValueError('planar dielectric region areas must remain finite and positive')
        values=dict(cell_region_indices=owners,epsilon_r=epsilon,interface_edges=np.asarray(edges,dtype=np.int64).reshape(-1,2),
            interface_cells=np.asarray(cells,dtype=np.int64).reshape(-1,2),interface_region_indices=np.asarray(regions,dtype=np.int64).reshape(-1,2),
            interface_coefficient_jumps=np.asarray(jumps,dtype=bool),boundary_region_indices=owners[mesh.boundary_cells].copy(),region_area_m2=region_area)
        for name,value in values.items():value.setflags(write=False);object.__setattr__(self,name,value)

    def to_dict(self):
        # PlanarMesh supplies topology only. Its RF serialization carries a
        # PEC declaration, so this static geometry has a neutral contract.
        return dict(format='superfish_ng_planar_dielectric_partition',schema_version=1,coordinates='cartesian_xy',
            geometry=dict(type='explicit_straight_simple_polygon',polygon_xy_m=self.mesh.polygon_xy_m.tolist(),
                points_xy_m=self.mesh.points_xy_m.tolist(),triangles=self.mesh.triangles.tolist()),
            materials=[m.to_dict() for m in self.materials],regions=[r.to_dict() for r in self.regions])

    @classmethod
    def from_dict(cls,data):
        names=['format','schema_version','coordinates','geometry','materials','regions'];keys(data,names,names,'planar dielectric partition')
        if data['format']!='superfish_ng_planar_dielectric_partition' or type(data['schema_version']) is not int or data['schema_version']!=1 or data['coordinates']!='cartesian_xy':
            raise ValueError('expected superfish_ng_planar_dielectric_partition version 1, cartesian_xy coordinates')
        geometry=data['geometry'];names=['type','polygon_xy_m','points_xy_m','triangles'];keys(geometry,names,names,'planar dielectric geometry')
        if geometry['type']!='explicit_straight_simple_polygon':raise ValueError('planar dielectrics require explicit straight simple-polygon geometry')
        if type(data['materials']) is not list or type(data['regions']) is not list:raise ValueError('planar materials and regions must be JSON lists')
        mesh=PlanarMesh.create(geometry['polygon_xy_m'],geometry['points_xy_m'],geometry['triangles'])
        return cls(mesh,[LinearDielectric.from_dict(m) for m in data['materials']],[DielectricRegion.from_dict(r) for r in data['regions']])
