# SPDX-License-Identifier: Apache-2.0
"""Planar magnetic reluctivity stiffness and signed axial-current load."""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import coo_matrix
from .magnetic_materials import PlanarMagneticPartition
from .electrostatic_boundary import finite_signed
from .mesh import Mesh,element_geometry
from .high_order import quadratic_space,basis_p2
from .fem import triangle_quadrature
from .config import integer,keys


@dataclass(frozen=True)
class PlanarMagnetostaticSpace:
    partition: PlanarMagneticPartition
    mesh: Mesh
    element_order: int
    dof_points_xy_m: np.ndarray
    cell_dofs: np.ndarray
    boundary_dofs: np.ndarray


def _assemble(space,densities,order):
    _,det,grad=element_geometry(space.mesh);dofs=space.cell_dofs;size=dofs.shape[1]
    local_k=np.zeros((len(dofs),size,size));local_f=np.zeros((len(dofs),size));p=space.partition;current_density=densities[p.cell_region_indices]
    for bary,weight in triangle_quadrature(order):
        values,derivatives=(bary,grad) if space.element_order==1 else basis_p2(bary,grad)
        measure=weight*det
        local_k+=(p.reluctivity_m_per_h*measure)[:,None,None]*np.einsum('tij,tkj->tik',derivatives,derivatives)
        local_f+=(current_density*measure)[:,None]*values[None,:]
    rows=np.repeat(dofs,size,axis=1).ravel();columns=np.tile(dofs,(1,size)).ravel()
    stiffness=coo_matrix((local_k.ravel(),(rows,columns)),shape=(len(space.dof_points_xy_m),)*2).tocsr()
    load=np.bincount(dofs.ravel(),weights=local_f.ravel(),minlength=len(space.dof_points_xy_m))
    if not np.isfinite(stiffness.data).all() or not np.isfinite(load).all() or np.any(stiffness.diagonal()<=0):raise ValueError('planar magnetostatic stiffness/load exceed finite positive SI arithmetic')
    return stiffness,load


def planar_magnetostatic_forms(partition,current_density_z_a_per_m2,element_order=2,*,quadrature_order=4):
    """Assemble K[m/H], f[A], preserving all DOFs and constant Az gauge.

    Az[Wb/m] gives B=(dAz/dy,-dAz/dx)[T], H=B/(mu0*mu_r)[A/m].
    The energy form is integral |B|^2/(2*mu) dxdy [J/m]. Current
    Jz[A/m^2] integrates to a load in amperes. No implicit thickness,
    rotation axis, boundary value, gauge constraint or field solve.
    """
    if type(partition) is not PlanarMagneticPartition:raise ValueError('explicit PlanarMagneticPartition required')
    partition=PlanarMagneticPartition.from_dict(partition.to_dict());names=[r.id for r in partition.regions]
    keys(current_density_z_a_per_m2,names,names,'planar current_density_z_a_per_m2 by region')
    densities=np.array([finite_signed(current_density_z_a_per_m2[name],'planar current density for '+name+' [A/m^2]') for name in names])
    integer(element_order,'planar magnetostatic element_order');integer(quadrature_order,'planar magnetostatic quadrature_order')
    if element_order not in (1,2) or not 4<=quadrature_order<=32:raise ValueError('planar magnetostatic forms require P1/P2 and quadrature_order from 4 to 32')
    base=partition.mesh;mesh=Mesh(base.points_xy_m,base.triangles,base.boundary_edges,np.full(len(base.boundary_edges),'boundary',dtype='U20'),base.boundary_cells,np.array([],dtype=np.int64))
    if element_order==2:
        q=quadratic_space(mesh);points,dofs,boundary=q.dof_points,q.cell_dofs,q.boundary_dofs
    else:points,dofs,boundary=mesh.points,mesh.triangles,mesh.boundary_edges
    for array in (points,dofs,boundary):array.setflags(write=False)
    space=PlanarMagnetostaticSpace(partition,mesh,element_order,points,dofs,boundary)
    stiffness,load=_assemble(space,densities,quadrature_order);high_k,high_f=_assemble(space,densities,quadrature_order+4)
    kd=float(np.linalg.norm((stiffness-high_k).data)/np.linalg.norm(high_k.data));fscale=max(np.linalg.norm(load),np.linalg.norm(high_f));fd=float(np.linalg.norm(load-high_f)/fscale) if fscale else 0.
    region_current=densities*partition.region_area_m2;current=float(region_current.sum());absolute=float(abs(region_current).sum())
    balance=float(abs(load.sum()-current)/absolute) if absolute else float(abs(load.sum()))
    if not np.isfinite([kd,fd,current,absolute,balance]).all() or max(kd,fd,balance)>5e-12:raise ValueError('planar magnetostatic integration or current conservation is unresolved')
    report=dict(orders=[quadrature_order,quadrature_order+4],stiffness_relative_difference=kd,load_relative_difference=fd,
        current_conservation_relative_difference=balance,total_current_a=current,sum_load_a=float(load.sum()),
        region_current_a={name:float(value) for name,value in zip(names,region_current)},
        scalar='out-of-plane magnetic vector potential Az',coefficient_unit='Wb/m',stiffness_unit='m/H',load_unit='A',measure='dx*dy per metre of uniform extrusion',
        constant_Az_gauge_kernel_retained=True,boundary_conditions_applied=False,
        interpretation='planar Az reluctivity form and signed Jz load; finite quadrature comparison, no implicit thickness, axis, boundary solve or discretization error bound')
    return space,stiffness,load,report
