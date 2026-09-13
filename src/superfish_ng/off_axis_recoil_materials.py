# SPDX-License-Identifier: Apache-2.0
"""Meridional recoil tensors on a strictly positive-radius axisymmetric domain."""
from dataclasses import dataclass,field
import math
import numpy as np
from .config import keys
from .recoil_materials import LinearRecoilMaterial,OrientedMagneticRegion
from .magnetic_materials import LinearMagneticMaterial,MagneticRegion
from .off_axis_magnetic_materials import OffAxisMagneticPartition
from .meridional_mesh import MeridionalMesh
from .constants import MU0


@dataclass(frozen=True,eq=False)
class OffAxisRecoilPartition:
    mesh: MeridionalMesh
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
    region_volume_m3: np.ndarray=field(init=False)
    azimuthal_mu_r: np.ndarray=field(init=False)

    def __post_init__(self):
        if type(self.mesh) is not MeridionalMesh:raise ValueError('off-axis recoil materials require a straight positive-radius MeridionalMesh; planar, axis-connected and curved domains are unsupported')
        for name,cls in (('materials',LinearRecoilMaterial),('regions',OrientedMagneticRegion)):
            values=getattr(self,name)
            if not isinstance(values,(list,tuple)) or not values or any(type(v) is not cls for v in values):raise ValueError('recoil '+name+' requires explicit '+cls.__name__+' values')
            object.__setattr__(self,name,tuple(cls.from_dict(v.to_dict()) for v in values))
        # Reuse only neutral geometry, coverage and ownership checks. The
        # temporary unit coefficients are never used in a physical operator.
        checked=OffAxisMagneticPartition(self.mesh,[LinearMagneticMaterial(m.id,1.) for m in self.materials],
            [MagneticRegion(v.id,v.material,v.cell_indices) for v in self.regions])
        object.__setattr__(self,'mesh',checked.mesh)
        for name in ('cell_region_indices','interface_edges','interface_cells','interface_region_indices','boundary_region_indices','region_area_m2','region_volume_m3'):
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
        for name,value in dict(mu_r_tensor=mu,reluctivity_tensor_m_per_h=nu,remanent_b_t=remanent,remanent_h_a_per_m=h,azimuthal_mu_r=mu[:,0,0].copy(),interface_coefficient_jumps=jumps).items():
            value.setflags(write=False);object.__setattr__(self,name,value)

    def to_dict(self):
        return dict(format='superfish_ng_off_axis_recoil_partition',schema_version=1,coordinates='axisymmetric_rz',
            azimuthal_model='decoupled_mu_phi_equals_mu_rr_zero_remanent_phi',
            geometry=dict(type='explicit_straight_off_axis',outer_rz_m=self.mesh.outer_rz_m.tolist(),
                holes_rz_m=[h.tolist() for h in self.mesh.holes_rz_m],points_rz_m=self.mesh.points_rz_m.tolist(),triangles=self.mesh.triangles.tolist()),
            materials=[m.to_dict() for m in self.materials],regions=[v.to_dict() for v in self.regions])

    @classmethod
    def from_dict(cls,data):
        names=['format','schema_version','coordinates','azimuthal_model','geometry','materials','regions'];keys(data,names,names,'off-axis recoil partition')
        if data['format']!='superfish_ng_off_axis_recoil_partition' or type(data['schema_version']) is not int or data['schema_version']!=1 or data['coordinates']!='axisymmetric_rz':
            raise ValueError('expected superfish_ng_off_axis_recoil_partition version 1, axisymmetric_rz')
        if data['azimuthal_model']!='decoupled_mu_phi_equals_mu_rr_zero_remanent_phi':
            raise ValueError('off-axis recoil material requires no phi coupling, mu_phi=mu_rr and zero phi remanence')
        g=data['geometry'];names=['type','outer_rz_m','holes_rz_m','points_rz_m','triangles'];keys(g,names,names,'off-axis recoil geometry')
        if g['type']!='explicit_straight_off_axis':raise ValueError('off-axis recoil partition requires straight positive-radius geometry')
        if type(data['materials']) is not list or type(data['regions']) is not list:raise ValueError('recoil materials/regions require JSON lists')
        mesh=MeridionalMesh(**{name:g[name] for name in names[1:]})
        return cls(mesh,[LinearRecoilMaterial.from_dict(v) for v in data['materials']],[OrientedMagneticRegion.from_dict(v) for v in data['regions']])
