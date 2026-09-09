# SPDX-License-Identifier: Apache-2.0
"""Verified uniform Cartesian refinement and nested nodal coefficient transfer."""
import numpy as np
from scipy.sparse import coo_matrix
from .planar_mesh import PlanarMesh
from .config import integer

REFERENCE = np.array([[1.,0.,0.],[0.,1.,0.],[0.,0.,1.],[.5,.5,0.],[0.,.5,.5],[.5,0.,.5]])
SPLIT = np.array([[0,3,5],[3,1,4],[5,4,2],[3,4,5]])

def refine_planar_mesh(mesh, *, max_triangles=250000):
    if not isinstance(mesh, PlanarMesh):raise ValueError('expected a declared PlanarMesh')
    integer(max_triangles, 'max_triangles')
    if 4*len(mesh.triangles)>max_triangles:raise ValueError('uniform planar refinement exceeds max_triangles')
    mesh=PlanarMesh.create(mesh.polygon_xy_m,mesh.points_xy_m,mesh.triangles)
    points,cells=mesh.points_xy_m,mesh.triangles
    edges,inverse=np.unique(np.sort(cells[:,[[0,1],[1,2],[2,0]]].reshape(-1,2),axis=1),axis=0,return_inverse=True)
    all_points=np.vstack((points,points[edges].mean(axis=1)))
    local=np.column_stack((cells,len(points)+inverse.reshape(-1,3)))
    children=local[:,SPLIT].reshape(-1,3)
    refined=PlanarMesh.create(mesh.polygon_xy_m,all_points,children)
    return refined

def _transfer_matrix(coarse_space,fine_space,parent_cells,child_vertex_barycentric,order):
    if order not in (1,2):raise ValueError('nested transfer requires P1 or P2')
    ref=REFERENCE[:3] if order==1 else REFERENCE
    records=[None]*len(fine_space.dof_points_xy_m)
    for child,dofs in enumerate(fine_space.cell_dofs):
        bary=ref@child_vertex_barycentric[child]
        values=bary if order==1 else np.column_stack((bary*(2*bary-1),4*bary[:,0]*bary[:,1],4*bary[:,1]*bary[:,2],4*bary[:,2]*bary[:,0]))
        old_dofs=coarse_space.cell_dofs[parent_cells[child]]
        for dof,value in zip(dofs,values):
            row={int(k):float(v) for k,v in zip(old_dofs,value) if v!=0}
            if records[dof] is not None and records[dof]!=row:
                raise ValueError('shared refined node has inconsistent coarse trace')
            records[dof]=row
    rows=[];cols=[];values=[]
    for i,row in enumerate(records):
        if row is None:raise ValueError('uncovered fine degree of freedom')
        for j,v in row.items():rows.append(i);cols.append(j);values.append(v)
    return coo_matrix((values,(rows,cols)),shape=(len(records),len(coarse_space.dof_points_xy_m))).tocsr()


def planar_refinement_relation(coarse, fine):
    """Derive the parent map only for the exact, unchanged four-way refinement."""
    if not isinstance(coarse, PlanarMesh) or not isinstance(fine, PlanarMesh):
        raise ValueError('refinement relation requires two declared PlanarMesh objects')
    expected=refine_planar_mesh(coarse,max_triangles=4*len(coarse.triangles))
    for name in ('polygon_xy_m','points_xy_m','triangles'):
        if not np.array_equal(getattr(expected,name),getattr(fine,name)):
            raise ValueError('fine planar mesh is not the declared uniform refinement of the same physical domain')
    parents=np.repeat(np.arange(len(coarse.triangles)),4)
    bary=np.tile(REFERENCE[SPLIT],(len(coarse.triangles),1,1))
    parents.setflags(write=False);bary.setflags(write=False)
    return parents,bary


def planar_prolongation(coarse, fine, element_order=2, polarization='te'):
    """Preserve a nodal scalar field; this operation does not perform a new solve."""
    from .planar import planar_mesh_matrices
    parents,bary=planar_refinement_relation(coarse,fine)
    a,_,_,_=planar_mesh_matrices(coarse,element_order,polarization)
    b,_,_,_=planar_mesh_matrices(fine,element_order,polarization)
    return _transfer_matrix(a,b,parents,bary,element_order)
