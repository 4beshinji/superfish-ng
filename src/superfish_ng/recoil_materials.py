# SPDX-License-Identifier: Apache-2.0
"""Explicit linear recoil tensors, remanent induction and planar orientation."""
from dataclasses import dataclass,field
import math
import numpy as np
from .config import keys,positive
from .magnetostatic_boundary import finite_signed
from .magnetic_materials import LinearMagneticMaterial,MagneticRegion,PlanarMagneticPartition
from .planar_mesh import PlanarMesh
from .constants import MU0


def _pair(values,name,positive_values=False):
    if not isinstance(values,(list,tuple)) or len(values)!=2:raise ValueError(name+' requires two explicit real components')
    result=tuple(finite_signed(v,name) for v in values)
    if positive_values:
        for v in result:positive(v,name)
    return result


@dataclass(frozen=True)
class LinearRecoilMaterial:
    id: str
    mu_r_principal: tuple
    remanent_b_local_t: tuple

    def __post_init__(self):
        if type(self.id) is not str or not self.id.strip():raise ValueError('recoil material id must be nonempty')
        object.__setattr__(self,'mu_r_principal',_pair(self.mu_r_principal,'principal recoil mu_r',True))
        object.__setattr__(self,'remanent_b_local_t',_pair(self.remanent_b_local_t,'local remanent B [T]'))

    def to_dict(self):
        return dict(id=self.id,type='linear_recoil_magnetic_material',mu_r_principal=list(self.mu_r_principal),remanent_b_local_t=list(self.remanent_b_local_t))

    @classmethod
    def from_dict(cls,data):
        names=['id','type','mu_r_principal','remanent_b_local_t'];keys(data,names,names,'linear recoil material')
        if data['type']!='linear_recoil_magnetic_material':raise ValueError('only linear_recoil_magnetic_material is supported')
        if type(data['mu_r_principal']) is not list or type(data['remanent_b_local_t']) is not list:raise ValueError('recoil principal values and remanent induction must be JSON lists')
        return cls(data['id'],data['mu_r_principal'],data['remanent_b_local_t'])


@dataclass(frozen=True)
class OrientedMagneticRegion:
    id: str
    material: str
    cell_indices: tuple
    orientation_rad: float

    def __post_init__(self):
        checked=MagneticRegion(self.id,self.material,self.cell_indices)
        object.__setattr__(self,'cell_indices',checked.cell_indices)
        object.__setattr__(self,'orientation_rad',finite_signed(self.orientation_rad,'recoil material orientation [rad]'))

    def to_dict(self):return dict(id=self.id,material=self.material,cell_indices=list(self.cell_indices),orientation_rad=self.orientation_rad)

    @classmethod
    def from_dict(cls,data):
        names=['id','material','cell_indices','orientation_rad'];keys(data,names,names,'oriented magnetic region')
        if type(data['cell_indices']) is not list:raise ValueError('oriented magnetic cell_indices must be a JSON list')
        return cls(**data)


@dataclass(frozen=True,eq=False)
class PlanarRecoilPartition:
    mesh: PlanarMesh
    materials: tuple
    regions: tuple
    cell_region_indices: np.ndarray=field(init=False)
    mu_r_tensor: np.ndarray=field(init=False)
    reluctivity_tensor_m_per_h: np.ndarray=field(init=False)
    remanent_b_t: np.ndarray=field(init=False)
    remanent_h_a_per_m: np.ndarray=field(init=False)
    interface_edges: np.ndarray=field(init=False)
    interface_cells: np.ndarray=field(init=False)
    interface_region_indices: np.ndarray=field(init=False)
    interface_coefficient_jumps: np.ndarray=field(init=False)
    boundary_region_indices: np.ndarray=field(init=False)
    region_area_m2: np.ndarray=field(init=False)

    def __post_init__(self):
        if type(self.mesh) is not PlanarMesh:raise ValueError('planar recoil materials require a straight simple-polygon PlanarMesh; axisymmetric and curved domains are unsupported')
        for name,cls in (('materials',LinearRecoilMaterial),('regions',OrientedMagneticRegion)):
            values=getattr(self,name)
            if not isinstance(values,(list,tuple)) or not values or any(type(v) is not cls for v in values):raise ValueError('recoil '+name+' requires explicit '+cls.__name__+' values')
            object.__setattr__(self,name,tuple(cls.from_dict(v.to_dict()) for v in values))
        # Reuse only neutral geometry, coverage and ownership checks. The
        # temporary unit coefficients are never used in a physical operator.
        checked=PlanarMagneticPartition(self.mesh,[LinearMagneticMaterial(m.id,1.) for m in self.materials],
            [MagneticRegion(v.id,v.material,v.cell_indices) for v in self.regions])
        object.__setattr__(self,'mesh',checked.mesh)
        for name in ('cell_region_indices','interface_edges','interface_cells','interface_region_indices','boundary_region_indices','region_area_m2'):
            object.__setattr__(self,name,getattr(checked,name))
        materials={m.id:m for m in self.materials};mu=[];nu=[];remanent=[]
        for region in self.regions:
            material=materials[region.material];c=math.cos(region.orientation_rad);s=math.sin(region.orientation_rad);rotation=np.array([[c,-s],[s,c]])
            with np.errstate(over='ignore',under='ignore',divide='ignore',invalid='ignore'):
                permeability=rotation@np.diag(material.mu_r_principal)@rotation.T
                reluctivity=rotation@np.diag((1./MU0)/np.array(material.mu_r_principal))@rotation.T
                induction=rotation@np.array(material.remanent_b_local_t)
                inverse_product=reluctivity@(MU0*permeability)
            if not all(np.isfinite(v).all() for v in (permeability,reluctivity,induction,inverse_product)):
                raise ValueError('recoil tensor and remanence exceed finite SI arithmetic')
            try:np.linalg.cholesky(permeability);np.linalg.cholesky(reluctivity)
            except np.linalg.LinAlgError as exc:raise ValueError('recoil tensor is not numerically positive definite; reduce principal-value contrast') from exc
            if np.linalg.norm(inverse_product-np.eye(2))>1e-10:raise ValueError('recoil tensor inverse is unresolved; reduce principal-value contrast')
            mu.append(permeability);nu.append(reluctivity);remanent.append(induction)
        owners=self.cell_region_indices;mu=np.array(mu)[owners];nu=np.array(nu)[owners];remanent=np.array(remanent)[owners]
        with np.errstate(over='ignore',invalid='ignore'):h=np.einsum('tij,tj->ti',nu,remanent)
        if not np.isfinite(h).all():raise ValueError('remanent source nu*B_rem exceeds finite SI arithmetic')
        pairs=self.interface_cells
        jumps=np.any(mu[pairs[:,0]]!=mu[pairs[:,1]],axis=(1,2))|np.any(remanent[pairs[:,0]]!=remanent[pairs[:,1]],axis=1)
        for name,value in dict(mu_r_tensor=mu,reluctivity_tensor_m_per_h=nu,remanent_b_t=remanent,remanent_h_a_per_m=h,interface_coefficient_jumps=jumps).items():
            value.setflags(write=False);object.__setattr__(self,name,value)

    def to_dict(self):
        return dict(format='superfish_ng_planar_recoil_partition',schema_version=1,coordinates='cartesian_xy',
            geometry=dict(type='explicit_straight_simple_polygon',polygon_xy_m=self.mesh.polygon_xy_m.tolist(),points_xy_m=self.mesh.points_xy_m.tolist(),triangles=self.mesh.triangles.tolist()),
            materials=[m.to_dict() for m in self.materials],regions=[v.to_dict() for v in self.regions])

    @classmethod
    def from_dict(cls,data):
        names=['format','schema_version','coordinates','geometry','materials','regions'];keys(data,names,names,'planar recoil partition')
        if data['format']!='superfish_ng_planar_recoil_partition' or type(data['schema_version']) is not int or data['schema_version']!=1 or data['coordinates']!='cartesian_xy':
            raise ValueError('expected superfish_ng_planar_recoil_partition version 1, cartesian_xy')
        g=data['geometry'];names=['type','polygon_xy_m','points_xy_m','triangles'];keys(g,names,names,'planar recoil geometry')
        if g['type']!='explicit_straight_simple_polygon':raise ValueError('recoil partition requires a straight simple polygon')
        if type(data['materials']) is not list or type(data['regions']) is not list:raise ValueError('recoil materials/regions require JSON lists')
        mesh=PlanarMesh.create(g['polygon_xy_m'],g['points_xy_m'],g['triangles'])
        return cls(mesh,[LinearRecoilMaterial.from_dict(v) for v in data['materials']],[OrientedMagneticRegion.from_dict(v) for v in data['regions']])
