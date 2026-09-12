# SPDX-License-Identifier: Apache-2.0
"""Planar tensor reluctivity and separate current/remanence weak loads."""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import coo_matrix
from .recoil_materials import PlanarRecoilPartition
from .electrostatic_boundary import finite_signed
from .mesh import Mesh,element_geometry
from .high_order import quadratic_space,basis_p2
from .fem import triangle_quadrature
from .config import integer,keys


@dataclass(frozen=True)
class PlanarRecoilSpace:
    partition: PlanarRecoilPartition
    mesh: Mesh
    element_order: int
    dof_points_xy_m: np.ndarray
    cell_dofs: np.ndarray
    boundary_dofs: np.ndarray


def _assemble(space,densities,order):
    _,det,grad=element_geometry(space.mesh);dofs=space.cell_dofs;size=dofs.shape[1]
    local_k=np.zeros((len(dofs),size,size));local_f=np.zeros((len(dofs),size));local_remanent=np.zeros_like(local_f);p=space.partition;current_density=densities[p.cell_region_indices]
    for bary,weight in triangle_quadrature(order):
        values,derivatives=(bary,grad) if space.element_order==1 else basis_p2(bary,grad)
        measure=weight*det
        curls=np.stack((derivatives[:,:,1],-derivatives[:,:,0]),axis=-1)
        local_k+=measure[:,None,None]*np.einsum('tia,tab,tjb->tij',curls,p.reluctivity_tensor_m_per_h,curls)
        local_remanent+=measure[:,None]*np.einsum('tia,ta->ti',curls,p.remanent_h_a_per_m)
        local_f+=(current_density*measure)[:,None]*values[None,:]
    rows=np.repeat(dofs,size,axis=1).ravel();columns=np.tile(dofs,(1,size)).ravel()
    stiffness=coo_matrix((local_k.ravel(),(rows,columns)),shape=(len(space.dof_points_xy_m),)*2).tocsr()
    load=np.bincount(dofs.ravel(),weights=local_f.ravel(),minlength=len(space.dof_points_xy_m))
    remanent=np.bincount(dofs.ravel(),weights=local_remanent.ravel(),minlength=len(space.dof_points_xy_m))
    if not np.isfinite(remanent).all():raise ValueError('planar remanent load exceeds finite SI arithmetic')
    if not np.isfinite(stiffness.data).all() or not np.isfinite(load).all() or np.any(stiffness.diagonal()<=0):raise ValueError('planar magnetostatic stiffness/load exceed finite positive SI arithmetic')
    return stiffness,load,remanent


def planar_recoil_forms(partition,current_density_z_a_per_m2,element_order=2,*,quadrature_order=4):
    """Assemble tensor K[m/H], separate fJ and frem[A], and constant Az kernel.

    B=curl(Az ez), H=nu(B-Brem). The constitutive potential referenced to
    B=0 is .5*B.nu.B-B.nu.Brem [J/m after integration], which may be
    negative. Adding .5*Brem.nu.Brem gives the nonnegative quadratic
    potential referenced to B=Brem. Neither defines irreversible magnet
    energy, demagnetization, or a winding inductance. No boundary solve.
    """
    if type(partition) is not PlanarRecoilPartition:raise ValueError('explicit PlanarRecoilPartition required')
    partition=PlanarRecoilPartition.from_dict(partition.to_dict());names=[r.id for r in partition.regions]
    keys(current_density_z_a_per_m2,names,names,'planar current_density_z_a_per_m2 by region')
    densities=np.array([finite_signed(current_density_z_a_per_m2[name],'planar current density for '+name+' [A/m^2]') for name in names])
    integer(element_order,'planar magnetostatic element_order');integer(quadrature_order,'planar magnetostatic quadrature_order')
    if element_order not in (1,2) or not 4<=quadrature_order<=32:raise ValueError('planar magnetostatic forms require P1/P2 and quadrature_order from 4 to 32')
    base=partition.mesh;mesh=Mesh(base.points_xy_m,base.triangles,base.boundary_edges,np.full(len(base.boundary_edges),'boundary',dtype='U20'),base.boundary_cells,np.array([],dtype=np.int64))
    if element_order==2:
        q=quadratic_space(mesh);points,dofs,boundary=q.dof_points,q.cell_dofs,q.boundary_dofs
    else:points,dofs,boundary=mesh.points,mesh.triangles,mesh.boundary_edges
    for array in (points,dofs,boundary):array.setflags(write=False)
    space=PlanarRecoilSpace(partition,mesh,element_order,points,dofs,boundary)
    stiffness,load,remanent=_assemble(space,densities,quadrature_order);high_k,high_f,high_remanent=_assemble(space,densities,quadrature_order+4)
    kd=float(np.linalg.norm((stiffness-high_k).data)/np.linalg.norm(high_k.data));fscale=max(np.linalg.norm(load),np.linalg.norm(high_f));fd=float(np.linalg.norm(load-high_f)/fscale) if fscale else 0.
    rscale=max(np.linalg.norm(remanent),np.linalg.norm(high_remanent));rd=float(np.linalg.norm(remanent-high_remanent)/rscale) if rscale else 0.
    rsum=float(abs(remanent.sum())/sum(abs(remanent))) if np.any(remanent) else 0.
    _,det,_=element_geometry(mesh)
    constant=.25*float(det@np.einsum('ti,ti->t',partition.remanent_b_t,partition.remanent_h_a_per_m))
    region_current=densities*partition.region_area_m2;current=float(region_current.sum());absolute=float(abs(region_current).sum())
    balance=float(abs(load.sum()-current)/absolute) if absolute else float(abs(load.sum()))
    if not np.isfinite([kd,fd,rd,rsum,constant,current,absolute,balance]).all() or max(kd,fd,rd,rsum,balance)>5e-12:raise ValueError('planar magnetostatic integration or current conservation is unresolved')
    report=dict(remanent_load_relative_difference=rd,remanent_zero_sum_relative_difference=rsum,remanent_reference_constant_j_per_m=constant,orders=[quadrature_order,quadrature_order+4],stiffness_relative_difference=kd,load_relative_difference=fd,
        current_conservation_relative_difference=balance,total_current_a=current,sum_load_a=float(load.sum()),
        region_current_a={name:float(value) for name,value in zip(names,region_current)},
        scalar='out-of-plane magnetic vector potential Az',coefficient_unit='Wb/m',stiffness_unit='m/H',load_unit='A',measure='dx*dy per metre of uniform extrusion',
        constant_Az_gauge_kernel_retained=True,boundary_conditions_applied=False,
        constitutive_relation='B=mu0*mu_rec*H+B_rem; tensor and remanent vector in declared region orientation',
        constitutive_potential='w0=.5*B.nu.B-B.nu.Brem, reference B=0; ws=.5*(B-Brem).nu.(B-Brem), reference B=Brem; gradient is H',
        interpretation='separate Jz and remanence loads, constant Az kernel; no implicit thickness, axis, boundary solve, absolute magnet internal energy or discretization error bound')
    return space,stiffness,load,remanent,report
