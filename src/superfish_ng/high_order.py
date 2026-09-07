# SPDX-License-Identifier: Apache-2.0
"""Research P2 TM core. RF/export integration is tracked separately by N02."""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import coo_matrix
from .fem import triangle_quadrature
from .mesh import element_geometry


@dataclass
class QuadraticSpace:
    mesh: object
    dof_points: np.ndarray
    cell_dofs: np.ndarray
    boundary_dofs: np.ndarray
    axis_dofs: np.ndarray


def quadratic_space(mesh):
    """Attach a single shared midpoint degree of freedom to each mesh edge."""
    element_geometry(mesh)
    edges, inverse = np.unique(np.sort(mesh.triangles[:, [[0,1],[1,2],[2,0]]].reshape(-1,2), axis=1),
                               axis=0, return_inverse=True)
    count = len(mesh.points)
    lookup = {tuple(edge): count+i for i,edge in enumerate(edges)}
    boundary_midpoints = np.array([lookup[tuple(sorted(edge))] for edge in mesh.boundary_edges])
    points = np.vstack((mesh.points, mesh.points[edges].mean(axis=1)))
    cell_dofs = np.column_stack((mesh.triangles, count+inverse.reshape(-1,3)))
    boundary_dofs = np.column_stack((mesh.boundary_edges, boundary_midpoints))
    axis = np.flatnonzero(points[:,0] == 0)
    axis = axis[np.argsort(points[axis,1])]
    return QuadraticSpace(mesh, points, cell_dofs, boundary_dofs, axis)


def basis_p2(barycentric, barycentric_gradients):
    """Values and physical gradients: vertices 0/1/2, then edges 01/12/20."""
    n, grad = np.asarray(barycentric), np.asarray(barycentric_gradients)
    if n.shape != (3,) or grad.shape[-2:] != (3,2):
        raise ValueError('P2 basis needs three barycentric values and 3x2 gradients')
    values = np.concatenate((n*(2*n-1), [4*n[i]*n[j] for i,j in [(0,1),(1,2),(2,0)]]))
    vertex_gradients = (4*n-1)[:,None]*grad
    edge_gradients = np.stack([4*(n[i]*grad[...,j,:]+n[j]*grad[...,i,:])
                               for i,j in [(0,1),(1,2),(2,0)]], axis=-2)
    return values, np.concatenate((vertex_gradients, edge_gradients), axis=-2)


def assemble_p2(space):
    """Exact straight-element degree-7 mass and degree-5 stiffness integration."""
    p, det, grad = element_geometry(space.mesh)
    k = np.zeros((len(p),6,6)); m = np.zeros_like(k)
    for barycentric, weight in triangle_quadrature(order=5):
        n, derivative = basis_p2(barycentric, grad)
        r = p[:,:,0] @ barycentric
        curl_z = 2*n[None,:]+r[:,None]*derivative[:,:,0]
        curl_r = r[:,None]*derivative[:,:,1]
        k += (weight*det*r)[:,None,None]*(curl_z[:,:,None]*curl_z[:,None,:]+curl_r[:,:,None]*curl_r[:,None,:])
        m += (weight*det*r**3)[:,None,None]*np.outer(n,n)
    rows = np.repeat(space.cell_dofs,6,axis=1).ravel()
    columns = np.tile(space.cell_dofs,(1,6)).ravel()
    shape = (len(space.dof_points),)*2
    return tuple(coo_matrix((matrix.ravel(),(rows,columns)),shape=shape).tocsr() for matrix in (k,m))


def solve_p2(case, *, mesh_data=None):
    """Research eigensolve only; P1 RF and save routines reject this solution."""
    from .solver import _solve
    return _solve(case, mesh_data=mesh_data, element_order=2)
