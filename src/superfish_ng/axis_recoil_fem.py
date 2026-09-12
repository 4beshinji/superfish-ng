# SPDX-License-Identifier: Apache-2.0
"""Tensor recoil magnetic forms in the regular axis unknown a=Aphi/r [T]."""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import coo_matrix
from .axis_recoil_materials import AxisRecoilPartition
from .magnetostatic_boundary import finite_signed
from .mesh import Mesh,element_geometry
from .high_order import quadratic_space,basis_p2
from .fem import triangle_quadrature
from .constants import TAU
from .config import integer,keys


@dataclass(frozen=True)
class AxisRecoilSpace:
    partition: AxisRecoilPartition
    mesh: Mesh
    element_order: int
    dof_points: np.ndarray
    cell_dofs: np.ndarray
    boundary_dofs: np.ndarray
    axis_dofs: np.ndarray


def _assemble(space,densities,order):
    _,det,grad=element_geometry(space.mesh);vertices=space.mesh.points[space.mesh.triangles]
    dofs=space.cell_dofs;size=dofs.shape[1];local_k=np.zeros((len(dofs),size,size));local_f=np.zeros((len(dofs),size))
    p=space.partition;current=densities[p.cell_region_indices];local_remanent=np.zeros_like(local_f)
    for bary,weight in triangle_quadrature(order):
        values,derivatives=(bary,grad) if space.element_order==1 else basis_p2(bary,grad)
        radius=vertices[:,:,0]@bary;measure=TAU*radius*weight*det
        br=-radius[:,None]*derivatives[:,:,1];bz=2*values[None,:]+radius[:,None]*derivatives[:,:,0]
        curls=np.stack((br,bz),axis=-1)
        local_k+=measure[:,None,None]*np.einsum('tia,tab,tjb->tij',curls,p.reluctivity_tensor_m_per_h,curls)
        local_remanent+=measure[:,None]*np.einsum('tia,ta->ti',curls,p.remanent_h_a_per_m)
        local_f+=(current*radius*measure)[:,None]*values[None,:]
    rows=np.repeat(dofs,size,axis=1).ravel();columns=np.tile(dofs,(1,size)).ravel()
    stiffness=coo_matrix((local_k.ravel(),(rows,columns)),shape=(len(space.dof_points),)*2).tocsr()
    load=np.bincount(dofs.ravel(),weights=local_f.ravel(),minlength=len(space.dof_points))
    if not np.isfinite(stiffness.data).all() or not np.isfinite(load).all() or np.any(stiffness.diagonal()<=0):
        raise ValueError('axis magnetic stiffness/load exceed finite positive SI arithmetic')
    remanent=np.bincount(dofs.ravel(),weights=local_remanent.ravel(),minlength=len(space.dof_points))
    if not np.isfinite(remanent).all():raise ValueError('axis remanent load exceeds finite SI arithmetic')
    return stiffness,load,remanent


def axis_recoil_forms(partition,current_density_phi_a_per_m2,element_order=2,*,quadrature_order=4):
    """Assemble a=Aphi/r [T] K[m^4/H] and Jphi work load[A m^2].

    Br=-r*d_z(a), Bz=2*a+r*d_r(a); K integrates nu B_i.B_j dV,
    f integrates Jphi*r*Ni dV with dV=2*pi*r dr dz. All axis a DOFs
    remain. Constant a describes uniform axial B and is not a gauge kernel.
    H=nu*(B-Brem). The separate remanent load integrates B_i.nu.Brem dV.
    W0=.5*B.nu.B-B.nu.Brem references B=0; adding C0 gives the
    nonnegative potential referenced to H=0. No absolute magnet internal
    energy, boundary condition, normalization or solve is imposed.
    """
    if type(partition) is not AxisRecoilPartition:raise ValueError('explicit AxisRecoilPartition required')
    partition=AxisRecoilPartition.from_dict(partition.to_dict())
    names=[r.id for r in partition.regions];keys(current_density_phi_a_per_m2,names,names,'current_density_phi_a_per_m2 by region')
    densities=np.array([finite_signed(current_density_phi_a_per_m2[name],'azimuthal current density Jphi for '+name+' [A/m^2]') for name in names])
    integer(element_order,'axis magnetic element_order');integer(quadrature_order,'axis magnetic quadrature_order')
    if element_order not in (1,2) or not 4<=quadrature_order<=32:raise ValueError('axis magnetic forms require P1/P2 and quadrature_order from 4 to 32')
    base=partition.mesh;mesh=Mesh(base.points_rz_m,base.triangles,base.boundary_edges,base.boundary_tags,base.boundary_cells,base.axis_nodes)
    if element_order==2:
        q=quadratic_space(mesh);points,dofs,boundary,axis_dofs=q.dof_points,q.cell_dofs,q.boundary_dofs,q.axis_dofs
    else:points,dofs,boundary,axis_dofs=mesh.points,mesh.triangles,mesh.boundary_edges,base.axis_nodes
    for array in (points,dofs,boundary,axis_dofs):array.setflags(write=False)
    space=AxisRecoilSpace(partition,mesh,element_order,points,dofs,boundary,axis_dofs)
    stiffness,load,remanent=_assemble(space,densities,quadrature_order);high_k,high_f,high_remanent=_assemble(space,densities,quadrature_order+4)
    k_difference=float(np.linalg.norm((stiffness-high_k).data)/np.linalg.norm(high_k.data))
    f_scale=max(np.linalg.norm(load),np.linalg.norm(high_f));f_difference=float(np.linalg.norm(load-high_f)/f_scale) if f_scale else 0.
    r_scale=max(np.linalg.norm(remanent),np.linalg.norm(high_remanent));r_difference=float(np.linalg.norm(remanent-high_remanent)/r_scale) if r_scale else 0.
    _,det,_=element_geometry(mesh);r=mesh.points[mesh.triangles,0]
    volumes=TAU*(det/2)*r.mean(axis=1)
    constant=.5*float(volumes@np.einsum('ti,ti->t',partition.remanent_b_t,partition.remanent_h_a_per_m))
    expected_sum=float(2*volumes@partition.remanent_h_a_per_m[:,1])
    sum_scale=max(float(abs(remanent).sum()),float(2*volumes@abs(partition.remanent_h_a_per_m[:,1])))
    remanent_sum_error=float(abs(remanent.sum()-expected_sum)/sum_scale) if sum_scale else 0.
    radial_moment=TAU*(det/2)*(np.sum(r*r,axis=1)+r[:,0]*r[:,1]+r[:,1]*r[:,2]+r[:,2]*r[:,0])/6
    regional_moment=np.bincount(partition.cell_region_indices,weights=radial_moment,minlength=len(names))
    region_work=densities*regional_moment;work=float(region_work.sum());absolute=float(abs(region_work).sum())
    balance=float(abs(load.sum()-work)/absolute) if absolute else float(abs(load.sum()))
    region_current=densities*partition.region_area_m2;current=float(region_current.sum())
    if not np.isfinite([k_difference,f_difference,r_difference,remanent_sum_error,constant,work,absolute,balance,current]).all() or max(k_difference,f_difference,r_difference,remanent_sum_error,balance)>5e-12:
        raise ValueError('axis magnetic integration or current work sum is unresolved; refine the mesh or increase quadrature_order')
    report=dict(remanent_load_relative_difference=r_difference,remanent_uniform_axial_work_relative_difference=remanent_sum_error,remanent_reference_constant_j=constant,remanent_sum_load_a_m2=float(remanent.sum()),orders=[quadrature_order,quadrature_order+4],stiffness_relative_difference=k_difference,load_relative_difference=f_difference,
        current_work_relative_difference=balance,total_source_current_a=current,region_source_current_a={name:float(v) for name,v in zip(names,region_current)},
        total_current_radial_moment_a_m2=work,sum_load_a_m2=float(load.sum()),region_current_radial_moment_a_m2={name:float(v) for name,v in zip(names,region_work)},
        scalar='a=Aphi/r',coefficient_unit='T',stiffness_unit='m^4/H',load_unit='A m^2',volume_measure='2*pi*r*dr*dz',potential_unit='J',
        source_current_measure='Jphi dr dz [A]; source work integrates Jphi*Aphi*2*pi*r dr dz [J]',
        axis_dofs_retained=len(axis_dofs),constant_a_is_gauge=False,boundary_conditions_applied=False,
        constitutive_relation='B=mu0*mu_rec*H+Brem; original H=nu*(B-Brem); meridional tensors and remanence follow region orientation',
        azimuthal_model=partition.to_dict()['azimuthal_model'],
        constitutive_potential='W0=integral(.5*B.nu.B-B.nu.Brem) references B=0; Ws=integral(.5*(B-Brem).nu.(B-Brem)) references H=0; Ws=W0+C0 [J]',
        interpretation='regular axis-connected Aphi=r*a recoil forms with separate current/remanence loads; constant a is uniform Bz=2a; no boundary solve, absolute magnet internal energy or discretization error bound')
    return space,stiffness,load,remanent,report
