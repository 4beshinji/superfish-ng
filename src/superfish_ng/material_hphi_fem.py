# SPDX-License-Identifier: Apache-2.0
"""Lossless isotropic material Hphi K/M; no eigensolve, RF output or vacuum fallback."""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import coo_matrix
from .rf_materials import RFMaterialPartition
from .axis_connected_mesh import AxisConnectedMesh
from .mesh import Mesh,element_geometry
from .high_order import quadratic_space,basis_p2
from .fem import triangle_quadrature
from .config import integer


@dataclass(frozen=True)
class MaterialHphiSpace:
    partition: RFMaterialPartition
    mesh: Mesh
    element_order: int
    scalar: str
    dof_points: np.ndarray
    cell_dofs: np.ndarray
    boundary_dofs: np.ndarray
    axis_dofs: np.ndarray


def _assemble_material(space,quadrature_order):
    _,det,grad=element_geometry(space.mesh);vertices=space.mesh.points[space.mesh.triangles]
    dofs=space.cell_dofs;size=dofs.shape[1];k=np.zeros((len(dofs),size,size));m=np.zeros_like(k)
    eps,mu=space.partition.epsilon_r,space.partition.mu_r
    for bary,weight in triangle_quadrature(quadrature_order):
        values,derivatives=(bary,grad) if space.element_order==1 else basis_p2(bary,grad)
        r=vertices[:,:,0]@bary;measure=weight*det
        if space.scalar=='q=r*Hphi':
            k+=(measure/(eps*r))[:,None,None]*np.einsum('tij,tkj->tik',derivatives,derivatives)
            m+=(measure*mu/r)[:,None,None]*np.outer(values,values)
        else:
            curl_r=r[:,None]*derivatives[:,:,1];curl_z=2*values[None,:]+r[:,None]*derivatives[:,:,0]
            k+=(measure*r/eps)[:,None,None]*(curl_r[:,:,None]*curl_r[:,None,:]+curl_z[:,:,None]*curl_z[:,None,:])
            m+=(measure*mu*r**3)[:,None,None]*np.outer(values,values)
    rows=np.repeat(dofs,size,axis=1).ravel();columns=np.tile(dofs,(1,size)).ravel()
    matrices=tuple(coo_matrix((v.ravel(),(rows,columns)),shape=(len(space.dof_points),)*2).tocsr() for v in (k,m))
    if any(not np.isfinite(a.data).all() or np.any(a.diagonal()<=0) for a in matrices):
        raise ValueError('material Hphi K/M is outside finite positive SI arithmetic')
    return matrices


def material_hphi_matrices(partition,element_order=2,*,quadrature_order=12):
    """Assemble K/epsilon_r and mu_r*M cellwise with continuous q or regular u.

    Hphi is tangential to every meridional material interface. Continuity is
    represented by the common scalar DOFs; the 1/epsilon_r curl flux appears in
    the weak form. No averaging of material coefficients or field gradients is
    performed. All axis DOFs remain; constant q remains in the matrix kernel.
    The generalized eigenvalue in a future solver is omega²/c0². The common
    2*pi factor is omitted from both forms.
    """
    if type(partition) is not RFMaterialPartition:raise ValueError('material Hphi requires an explicit RFMaterialPartition')
    integer(element_order,'material Hphi element_order');integer(quadrature_order,'material Hphi quadrature_order')
    if element_order not in (1,2) or not 4<=quadrature_order<=32:raise ValueError('material Hphi requires P1/P2 and quadrature_order from 4 to 32')
    partition=RFMaterialPartition.from_dict(partition.to_dict());base=partition.mesh;axis=isinstance(base,AxisConnectedMesh)
    tags=base.boundary_tags if axis else np.full(len(base.boundary_edges),'pec',dtype='U20')
    axis_nodes=base.axis_nodes if axis else np.array([],dtype=np.int64)
    mesh=Mesh(base.points_rz_m,base.triangles,base.boundary_edges,tags,base.boundary_cells,axis_nodes)
    if element_order==2:
        q=quadratic_space(mesh);points,dofs,boundary,axis_dofs=q.dof_points,q.cell_dofs,q.boundary_dofs,q.axis_dofs
    else:points,dofs,boundary,axis_dofs=mesh.points,mesh.triangles,mesh.boundary_edges,axis_nodes
    for array in (points,dofs,boundary,axis_dofs):array.setflags(write=False)
    space=MaterialHphiSpace(partition,mesh,element_order,'u=Hphi/r' if axis else 'q=r*Hphi',points,dofs,boundary,axis_dofs)
    k,m=_assemble_material(space,quadrature_order);high=_assemble_material(space,quadrature_order+4)
    differences=[float(np.linalg.norm((a-b).data)/np.linalg.norm(b.data)) for a,b in zip((k,m),high)]
    if not np.isfinite(differences).all() or max(differences)>5e-10:
        raise ValueError('material Hphi quadrature is unresolved; refine the mesh or increase quadrature_order')
    report=dict(orders=[quadrature_order,quadrature_order+4],stiffness_relative_difference=differences[0],mass_relative_difference=differences[1],
        relative_tolerance=5e-10,scalar=space.scalar,common_azimuthal_factor_included=False,
        axis_dofs_retained=len(axis_dofs),regions=len(partition.regions),material_interfaces=int(np.count_nonzero(partition.interface_coefficient_jumps)),
        static_kernel='none in the regular axis-connected space' if axis else 'constant q retained; no positive-spectrum extraction',
        interpretation='finite quadrature comparison for explicit lossless material coefficients; not a discretization error bound')
    return space,k,m,report
