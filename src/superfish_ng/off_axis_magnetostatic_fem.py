# SPDX-License-Identifier: Apache-2.0
"""Reduced-flux psi=r*Aphi magnetic forms on strictly positive-radius domains."""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import coo_matrix
from .off_axis_magnetic_materials import OffAxisMagneticPartition
from .magnetostatic_boundary import finite_signed
from .mesh import Mesh,element_geometry
from .high_order import quadratic_space,basis_p2
from .fem import triangle_quadrature
from .constants import TAU
from .config import integer,keys


@dataclass(frozen=True)
class OffAxisMagnetostaticSpace:
    partition: OffAxisMagneticPartition
    mesh: Mesh
    element_order: int
    dof_points: np.ndarray
    cell_dofs: np.ndarray
    boundary_dofs: np.ndarray


def _assemble(space,densities,order):
    _,det,grad=element_geometry(space.mesh);vertices=space.mesh.points[space.mesh.triangles]
    dofs=space.cell_dofs;size=dofs.shape[1];local_k=np.zeros((len(dofs),size,size));local_f=np.zeros((len(dofs),size))
    p=space.partition;current=densities[p.cell_region_indices]
    for bary,weight in triangle_quadrature(order):
        values,derivatives=(bary,grad) if space.element_order==1 else basis_p2(bary,grad)
        radius=vertices[:,:,0]@bary;measure=TAU*weight*det
        local_k+=(p.reluctivity_m_per_h*measure/radius)[:,None,None]*np.einsum('tij,tkj->tik',derivatives,derivatives)
        local_f+=(current*measure)[:,None]*values[None,:]
    rows=np.repeat(dofs,size,axis=1).ravel();columns=np.tile(dofs,(1,size)).ravel()
    stiffness=coo_matrix((local_k.ravel(),(rows,columns)),shape=(len(space.dof_points),)*2).tocsr()
    load=np.bincount(dofs.ravel(),weights=local_f.ravel(),minlength=len(space.dof_points))
    if not np.isfinite(stiffness.data).all() or not np.isfinite(load).all() or np.any(stiffness.diagonal()<=0):
        raise ValueError('off-axis magnetic stiffness/load exceed finite positive SI arithmetic')
    return stiffness,load


def off_axis_magnetostatic_forms(partition,current_density_phi_a_per_m2,element_order=2,*,quadrature_order=16):
    """Assemble reduced flux psi=r*Aphi[Wb] K[1/H] and current load[A].

    Br=-d_z(psi)/r, Bz=d_r(psi)/r. K=2*pi*integral nu/r gradNi.gradNj
    dr dz and f=2*pi*integral Jphi*Ni dr dz. Constant psi remains a
    zero-B kernel; the excluded-axis absolute flux reference is undetermined.
    No boundary constraint or source solve is imposed by these forms.
    """
    if type(partition) is not OffAxisMagneticPartition:raise ValueError('explicit OffAxisMagneticPartition required')
    partition=OffAxisMagneticPartition.from_dict(partition.to_dict())
    names=[r.id for r in partition.regions];keys(current_density_phi_a_per_m2,names,names,'off-axis current_density_phi_a_per_m2 by region')
    densities=np.array([finite_signed(current_density_phi_a_per_m2[name],'azimuthal current density Jphi for '+name+' [A/m^2]') for name in names])
    integer(element_order,'off-axis magnetic element_order');integer(quadrature_order,'off-axis magnetic quadrature_order')
    if element_order not in (1,2) or not 4<=quadrature_order<=32:raise ValueError('off-axis magnetic forms require P1/P2 and quadrature_order from 4 to 32')
    base=partition.mesh;tags=np.full(len(base.boundary_edges),'boundary',dtype='U20')
    mesh=Mesh(base.points_rz_m,base.triangles,base.boundary_edges,tags,base.boundary_cells,np.array([],dtype=np.int64))
    if element_order==2:
        q=quadratic_space(mesh);points,dofs,boundary=q.dof_points,q.cell_dofs,q.boundary_dofs
    else:points,dofs,boundary=mesh.points,mesh.triangles,mesh.boundary_edges
    for array in (points,dofs,boundary):array.setflags(write=False)
    space=OffAxisMagnetostaticSpace(partition,mesh,element_order,points,dofs,boundary)
    stiffness,load=_assemble(space,densities,quadrature_order);high_k,high_f=_assemble(space,densities,quadrature_order+4)
    k_difference=float(np.linalg.norm((stiffness-high_k).data)/np.linalg.norm(high_k.data))
    f_scale=max(np.linalg.norm(load),np.linalg.norm(high_f));f_difference=float(np.linalg.norm(load-high_f)/f_scale) if f_scale else 0.
    region_current=densities*partition.region_area_m2;current=float(region_current.sum());absolute=float(abs(region_current).sum())
    balance=float(abs(load.sum()/TAU-current)/absolute) if absolute else float(abs(load.sum()/TAU))
    if not np.isfinite([k_difference,f_difference,current,absolute,balance]).all() or max(k_difference,f_difference,balance)>5e-12:
        raise ValueError('off-axis magnetic 1/r integration or total current is unresolved; refine mesh or increase quadrature_order')
    report=dict(orders=[quadrature_order,quadrature_order+4],stiffness_relative_difference=k_difference,load_relative_difference=f_difference,
        current_conservation_relative_difference=balance,total_source_current_a=current,sum_load_a=float(load.sum()),
        region_source_current_a={name:float(v) for name,v in zip(names,region_current)},
        scalar='reduced flux psi=r*Aphi',coefficient_unit='Wb',stiffness_unit='1/H',load_unit='A',energy_unit='J',
        volume_measure='2*pi*r dr dz',source_current_measure='Jphi dr dz [A]; sum(load)/(2*pi)',axis_present=False,
        constant_psi_kernel_retained=True,boundary_conditions_applied=False,
        interpretation='strictly r>0; constant psi is curl-free Aphi=C/r, not uniform B; excluded-axis absolute flux reference is undetermined; no boundary solve or discretization error bound')
    return space,stiffness,load,report
