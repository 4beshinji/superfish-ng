# SPDX-License-Identifier: Apache-2.0
"""Planar electrostatic stiffness and volume-charge load per unit extrusion length."""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import coo_matrix
from .planar_dielectrics import PlanarDielectricPartition
from .electrostatic_boundary import finite_signed
from .mesh import Mesh,element_geometry
from .high_order import quadratic_space,basis_p2
from .fem import triangle_quadrature
from .constants import EPS0
from .config import integer,keys


@dataclass(frozen=True)
class PlanarElectrostaticSpace:
    partition: PlanarDielectricPartition
    mesh: Mesh
    element_order: int
    dof_points_xy_m: np.ndarray
    cell_dofs: np.ndarray
    boundary_dofs: np.ndarray


def _assemble(space,densities,order):
    _,det,grad=element_geometry(space.mesh);dofs=space.cell_dofs;size=dofs.shape[1]
    local_k=np.zeros((len(dofs),size,size));local_f=np.zeros((len(dofs),size));p=space.partition;rho=densities[p.cell_region_indices]
    for bary,weight in triangle_quadrature(order):
        values,derivatives=(bary,grad) if space.element_order==1 else basis_p2(bary,grad)
        measure=weight*det
        local_k+=(EPS0*p.epsilon_r*measure)[:,None,None]*np.einsum('tij,tkj->tik',derivatives,derivatives)
        local_f+=(rho*measure)[:,None]*values[None,:]
    rows=np.repeat(dofs,size,axis=1).ravel();columns=np.tile(dofs,(1,size)).ravel()
    stiffness=coo_matrix((local_k.ravel(),(rows,columns)),shape=(len(space.dof_points_xy_m),)*2).tocsr()
    load=np.bincount(dofs.ravel(),weights=local_f.ravel(),minlength=len(space.dof_points_xy_m))
    if not np.isfinite(stiffness.data).all() or not np.isfinite(load).all() or np.any(stiffness.diagonal()<=0):raise ValueError('planar electrostatic stiffness/load exceed finite positive SI arithmetic')
    return stiffness,load


def planar_electrostatic_forms(partition,charge_density_c_per_m3,element_order=2,*,quadrature_order=4):
    """Assemble K[F/m], f[C/m], preserving all DOFs and the constant Phi kernel.

    Volume rho remains C/m^3. Integrating over xy gives a load per metre in
    the uniform extrusion direction. No radial factor, thickness, boundary
    value, gauge or Poisson solve is implicit in this API.
    """
    if type(partition) is not PlanarDielectricPartition:raise ValueError('explicit PlanarDielectricPartition required')
    partition=PlanarDielectricPartition.from_dict(partition.to_dict());names=[r.id for r in partition.regions]
    keys(charge_density_c_per_m3,names,names,'planar charge_density_c_per_m3 by region')
    densities=np.array([finite_signed(charge_density_c_per_m3[name],'planar charge density for '+name+' [C/m^3]') for name in names])
    integer(element_order,'planar electrostatic element_order');integer(quadrature_order,'planar electrostatic quadrature_order')
    if element_order not in (1,2) or not 4<=quadrature_order<=32:raise ValueError('planar electrostatic forms require P1/P2 and quadrature_order from 4 to 32')
    base=partition.mesh;mesh=Mesh(base.points_xy_m,base.triangles,base.boundary_edges,np.full(len(base.boundary_edges),'boundary',dtype='U20'),base.boundary_cells,np.array([],dtype=np.int64))
    if element_order==2:
        q=quadratic_space(mesh);points,dofs,boundary=q.dof_points,q.cell_dofs,q.boundary_dofs
    else:points,dofs,boundary=mesh.points,mesh.triangles,mesh.boundary_edges
    for array in (points,dofs,boundary):array.setflags(write=False)
    space=PlanarElectrostaticSpace(partition,mesh,element_order,points,dofs,boundary)
    stiffness,load=_assemble(space,densities,quadrature_order);high_k,high_f=_assemble(space,densities,quadrature_order+4)
    kd=float(np.linalg.norm((stiffness-high_k).data)/np.linalg.norm(high_k.data));fscale=max(np.linalg.norm(load),np.linalg.norm(high_f));fd=float(np.linalg.norm(load-high_f)/fscale) if fscale else 0.
    region_charge=densities*partition.region_area_m2;charge=float(region_charge.sum());absolute=float(abs(region_charge).sum())
    balance=float(abs(load.sum()-charge)/absolute) if absolute else float(abs(load.sum()))
    if not np.isfinite([kd,fd,charge,absolute,balance]).all() or max(kd,fd,balance)>5e-12:raise ValueError('planar electrostatic integration or charge conservation is unresolved')
    report=dict(orders=[quadrature_order,quadrature_order+4],stiffness_relative_difference=kd,load_relative_difference=fd,
        charge_conservation_relative_difference=balance,total_volume_charge_c_per_m=charge,sum_load_c_per_m=float(load.sum()),
        region_charge_c_per_m={name:float(value) for name,value in zip(names,region_charge)},
        scalar='electric potential Phi',coefficient_unit='V',stiffness_unit='F/m',load_unit='C/m',measure='dx*dy per metre of uniform extrusion',
        constant_potential_kernel_retained=True,boundary_conditions_applied=False,
        interpretation='planar static volume forms per unit length and finite quadrature comparison; no implicit thickness, axis, boundary solve or discretization error bound')
    return space,stiffness,load,report
