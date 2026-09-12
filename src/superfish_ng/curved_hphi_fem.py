# SPDX-License-Identifier: Apache-2.0
"""Vacuum m=0 Hphi forms on explicit curved meridional geometry.

Positive-radius geometry uses q=r*Hphi, including its constant static kernel.
Axis-connected geometry uses regular u=Hphi/r and retains every axis DOF.
The scalar matrices omit the common 2*pi factor, as do the straight forms.
"""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import coo_matrix
from .axis_connected_mesh import AxisConnectedMesh
from .curved_meridional_geometry import CurvedMeridionalGeometry
from .quadratic_geometry import QuadraticTriangle
from .fem import triangle_quadrature


@dataclass(frozen=True)
class CurvedHphiSpace:
    geometry: CurvedMeridionalGeometry
    element_order: int
    scalar: str
    dof_points: np.ndarray
    cell_dofs: np.ndarray
    boundary_dofs: np.ndarray
    axis_dofs: np.ndarray


def _assemble(space,order):
    rule=list(triangle_quadrature(order));bary=np.asarray([p for p,w in rule]);weights=np.asarray([w for p,w in rule])
    size=space.cell_dofs.shape[1];local_k=np.zeros((len(space.cell_dofs),size,size));local_m=np.zeros_like(local_k)
    for cell,nodes in enumerate(space.geometry.cell_nodes):
        mapped=QuadraticTriangle(space.geometry.points_rz_m[nodes]).evaluate(bary[:,1:])
        r=mapped['points_rz_m'][:,0];measure=weights*mapped['determinant_m2']
        if np.any(r<=0):raise ValueError('curved Hphi quadrature radius must be strictly positive inside each element')
        if space.element_order==2:
            values=mapped['basis_values'];grad=mapped['basis_gradients']
        else:
            values=bary
            grad=np.einsum('ia,qab->qib',np.array([[-1.,-1.],[1.,0.],[0.,1.]]),np.linalg.inv(mapped['jacobian']))
        if space.scalar=='q=r*Hphi':
            k=np.einsum('q,qia,qja->ij',measure/r,grad,grad)
            m=np.einsum('q,qi,qj->ij',measure/r,values,values)
        else:
            curl_r=r[:,None]*grad[:,:,1];curl_z=2*values+r[:,None]*grad[:,:,0]
            k=np.einsum('q,qi,qj->ij',measure*r,curl_r,curl_r)+np.einsum('q,qi,qj->ij',measure*r,curl_z,curl_z)
            m=np.einsum('q,qi,qj->ij',measure*r**3,values,values)
        local_k[cell]=k;local_m[cell]=m
    rows=np.repeat(space.cell_dofs,size,axis=1).ravel();columns=np.tile(space.cell_dofs,(1,size)).ravel()
    matrices=tuple(coo_matrix((a.ravel(),(rows,columns)),shape=(len(space.dof_points),)*2).tocsr() for a in (local_k,local_m))
    if any(not np.isfinite(a.data).all() or np.any(a.diagonal()<=0) for a in matrices):
        raise ValueError('curved Hphi K/M is outside finite positive SI arithmetic')
    return matrices


def curved_hphi_matrices(geometry,element_order=2,*,quadrature_order=12):
    """Return space, K, M and a finite two-order quadrature comparison.

    No eigensolve, static-mode removal, RF quantity or discretization bound is
    produced. Geometry is fully reconstructed before constructing the forms.
    """
    if type(geometry) is not CurvedMeridionalGeometry:
        raise ValueError('explicit validated CurvedMeridionalGeometry required')
    if type(element_order) is not int or element_order not in (1,2):
        raise ValueError('curved Hphi element_order must be P1 or P2')
    if type(quadrature_order) is not int or not 2<=quadrature_order<=32:
        raise ValueError('curved Hphi quadrature_order must be an integer from 2 to 32')
    g=CurvedMeridionalGeometry.from_dict(geometry.to_dict());axis=isinstance(g.base_mesh,AxisConnectedMesh)
    if element_order==2:points,cells,boundary=g.points_rz_m,g.cell_nodes,g.boundary_nodes
    else:points,cells,boundary=g.base_mesh.points_rz_m,g.cell_nodes[:,:3],g.boundary_nodes[:,:2]
    axis_dofs=np.unique(boundary[g.boundary_tags=='axis'])
    axis_dofs=axis_dofs[np.argsort(points[axis_dofs,1])];axis_dofs.setflags(write=False)
    space=CurvedHphiSpace(g,element_order,'u=Hphi/r' if axis else 'q=r*Hphi',points,cells,boundary,axis_dofs)
    k,m=_assemble(space,quadrature_order);high=_assemble(space,quadrature_order+4)
    differences=[float(np.linalg.norm((a-b).data)/np.linalg.norm(b.data)) for a,b in zip((k,m),high)]
    if not np.isfinite(differences).all() or max(differences)>5e-10:
        raise ValueError('curved Hphi quadrature is unresolved; increase quadrature_order or refine the explicit geometry')
    report=dict(orders=[quadrature_order,quadrature_order+4],stiffness_relative_difference=differences[0],
                mass_relative_difference=differences[1],relative_tolerance=5e-10,scalar=space.scalar,
                common_azimuthal_factor_included=False,axis_dofs_retained=len(axis_dofs),
                static_kernel='none in the regular axis-connected space' if axis else 'constant q retained; no positive-spectrum extraction',
                interpretation='finite quadrature comparison; not a discretization error bound')
    return space,k,m,report
