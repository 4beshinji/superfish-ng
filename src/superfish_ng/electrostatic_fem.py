# SPDX-License-Identifier: Apache-2.0
"""Full-SI axisymmetric electrostatic K and volume-charge load; no boundary solve."""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import coo_matrix
from .dielectrics import AxisymmetricDielectricPartition
from .axis_connected_mesh import AxisConnectedMesh
from .mesh import Mesh,element_geometry
from .high_order import quadratic_space,basis_p2
from .fem import triangle_quadrature
from .constants import EPS0,TAU
from .config import integer,keys


@dataclass(frozen=True)
class AxisymmetricElectrostaticSpace:
    partition: AxisymmetricDielectricPartition
    mesh: Mesh
    element_order: int
    dof_points: np.ndarray
    cell_dofs: np.ndarray
    boundary_dofs: np.ndarray
    axis_dofs: np.ndarray


def _assemble(space,densities,order):
    _,det,grad=element_geometry(space.mesh);vertices=space.mesh.points[space.mesh.triangles]
    dofs=space.cell_dofs;size=dofs.shape[1];local_k=np.zeros((len(dofs),size,size));local_f=np.zeros((len(dofs),size))
    p=space.partition;rho=densities[p.cell_region_indices]
    for bary,weight in triangle_quadrature(order):
        values,derivatives=(bary,grad) if space.element_order==1 else basis_p2(bary,grad)
        measure=TAU*(vertices[:,:,0]@bary)*weight*det
        local_k+=(EPS0*p.epsilon_r*measure)[:,None,None]*np.einsum('tij,tkj->tik',derivatives,derivatives)
        local_f+=(rho*measure)[:,None]*values[None,:]
    rows=np.repeat(dofs,size,axis=1).ravel();columns=np.tile(dofs,(1,size)).ravel()
    stiffness=coo_matrix((local_k.ravel(),(rows,columns)),shape=(len(space.dof_points),)*2).tocsr()
    load=np.bincount(dofs.ravel(),weights=local_f.ravel(),minlength=len(space.dof_points))
    if not np.isfinite(stiffness.data).all() or not np.isfinite(load).all() or np.any(stiffness.diagonal()<=0):
        raise ValueError('electrostatic stiffness/load exceed finite positive SI arithmetic')
    return stiffness,load


def axisymmetric_electrostatic_forms(partition,charge_density_c_per_m3,element_order=2,*,quadrature_order=4):
    """Assemble Phi[V] stiffness[F] and charge load[C], including the full 2*pi.

    K=integral epsilon0*epsilon_r*grad(Ni).grad(Nj) dV and
    f=integral rho*Ni dV. Every region's signed rho must be explicit. The
    constant-potential kernel and all axis DOFs remain. This function applies
    no electrode potential, Neumann data or gauge, and does not solve Poisson.
    """
    if type(partition) is not AxisymmetricDielectricPartition:raise ValueError('explicit AxisymmetricDielectricPartition required')
    partition=AxisymmetricDielectricPartition.from_dict(partition.to_dict())
    names=[r.id for r in partition.regions];keys(charge_density_c_per_m3,names,names,'charge_density_c_per_m3 by region')
    densities=[]
    for name in names:
        value=charge_density_c_per_m3[name]
        try: finite=not isinstance(value,bool) and isinstance(value,(int,float)) and np.isfinite(float(value))
        except OverflowError: finite=False
        if not finite:
            raise ValueError('charge density for '+name+' must be a finite signed real number in C/m^3')
        densities.append(float(value))
    densities=np.asarray(densities)
    integer(element_order,'electrostatic element_order');integer(quadrature_order,'electrostatic quadrature_order')
    if element_order not in (1,2) or not 4<=quadrature_order<=32:raise ValueError('electrostatic forms require P1/P2 and quadrature_order from 4 to 32')
    base=partition.mesh;axis=isinstance(base,AxisConnectedMesh)
    tags=base.boundary_tags if axis else np.full(len(base.boundary_edges),'boundary',dtype='U20')
    axis_nodes=base.axis_nodes if axis else np.array([],dtype=np.int64)
    mesh=Mesh(base.points_rz_m,base.triangles,base.boundary_edges,tags,base.boundary_cells,axis_nodes)
    if element_order==2:
        q=quadratic_space(mesh);points,dofs,boundary,axis_dofs=q.dof_points,q.cell_dofs,q.boundary_dofs,q.axis_dofs
    else:points,dofs,boundary,axis_dofs=mesh.points,mesh.triangles,mesh.boundary_edges,axis_nodes
    for array in (points,dofs,boundary,axis_dofs):array.setflags(write=False)
    space=AxisymmetricElectrostaticSpace(partition,mesh,element_order,points,dofs,boundary,axis_dofs)
    stiffness,load=_assemble(space,densities,quadrature_order);high_k,high_f=_assemble(space,densities,quadrature_order+4)
    k_difference=float(np.linalg.norm((stiffness-high_k).data)/np.linalg.norm(high_k.data))
    f_scale=max(np.linalg.norm(load),np.linalg.norm(high_f));f_difference=float(np.linalg.norm(load-high_f)/f_scale) if f_scale else 0.
    region_charge=densities*partition.region_volume_m3;charge=float(region_charge.sum());absolute=float(abs(region_charge).sum())
    balance=float(abs(load.sum()-charge)/absolute) if absolute else float(abs(load.sum()))
    if not np.isfinite([k_difference,f_difference,charge,absolute,balance]).all() or max(k_difference,f_difference,balance)>5e-12:
        raise ValueError('electrostatic integration or total-charge conservation is unresolved; refine the mesh or increase quadrature_order')
    report=dict(orders=[quadrature_order,quadrature_order+4],stiffness_relative_difference=k_difference,load_relative_difference=f_difference,
        charge_conservation_relative_difference=balance,total_volume_charge_c=charge,sum_load_c=float(load.sum()),
        region_charge_c={name:float(value) for name,value in zip(names,region_charge)},
        scalar='electric potential Phi',coefficient_unit='V',stiffness_unit='F',load_unit='C',volume_measure='2*pi*r*dr*dz',
        axis_dofs_retained=len(axis_dofs),constant_potential_kernel_retained=True,boundary_conditions_applied=False,
        interpretation='full-SI electrostatic volume forms and finite quadrature comparison; no boundary solve or discretization error bound')
    return space,stiffness,load,report
