# SPDX-License-Identifier: Apache-2.0
"""Conforming marked-cell subdivision and exact P1/P2 coefficient restriction."""
from dataclasses import dataclass
import math
import numpy as np
from scipy.sparse import coo_matrix
from .config import integer
from .contour_mesh import _split_marked_edges,contour_mesh_quality
from .high_order import quadratic_space,basis_p2
from .mesh_input import mesh_from_dict,mesh_to_dict


@dataclass(frozen=True)
class MarkedRefinement:
    mesh: object
    prolongation: object
    parent_cells: np.ndarray
    parent_barycentric_vertices: np.ndarray
    requested_cells: np.ndarray
    split_edges: np.ndarray
    quality: dict


def refine_marked_cells(case,mesh,marked_cells,*,max_triangles=250000,minimum_angle_deg=5.):
    """Split requested affine triangles into four and close shared-edge splits.

    A marked short edge also marks an owner's longest edge. Unmarked cells
    receive conforming one/two/three-edge transition templates. Boundary tags
    are inherited without moving the represented wall. Prolongation restricts
    the same P1/P2 function using dyadic parent barycentric coordinates; it is
    not a new eigensolve or an error estimator. Inputs are not mutated.
    """
    if case.geometry_order!=1:raise ValueError('marked-cell refinement currently requires straight geometric triangles; curved local restriction is not implemented')
    integer(max_triangles,'max_triangles')
    if (type(minimum_angle_deg) not in (int,float) or not math.isfinite(minimum_angle_deg)
            or not 0<minimum_angle_deg<60):raise ValueError('minimum_angle_deg must be finite and between 0 and 60 degrees')
    if case.contour_mesh is not None:
        max_triangles=min(max_triangles,case.contour_mesh.max_triangles)
        minimum_angle_deg=max(minimum_angle_deg,case.contour_mesh.min_angle_deg)
    mesh=mesh_from_dict(case,mesh_to_dict(mesh));triangles=mesh.triangles
    if (type(marked_cells) is not list or not marked_cells or any(type(i) is not int or not 0<=i<len(triangles) for i in marked_cells)
            or len(set(marked_cells))!=len(marked_cells)):
        raise ValueError('marked_cells must list distinct valid zero-based integer triangle indices')
    requested=np.array(sorted(marked_cells),dtype=np.int64)
    edges,inverse=np.unique(np.sort(triangles[:,[[0,1],[1,2],[2,0]]].reshape(-1,2),axis=1),axis=0,return_inverse=True)
    cell_edges=inverse.reshape(-1,3);marked=np.zeros(len(edges),dtype=bool);marked[cell_edges[requested]]=True
    length=np.linalg.norm(mesh.points[edges[:,1]]-mesh.points[edges[:,0]],axis=1)
    longest=cell_edges[np.arange(len(triangles)),np.argmax(length[cell_edges],axis=1)]
    while True:
        required=longest[marked[cell_edges].any(axis=1)]
        if marked[required].all():break
        marked[required]=True
    refined=_split_marked_edges(case,mesh,edges,cell_edges,marked,max_triangles)
    quality=contour_mesh_quality(refined)
    if quality['min_angle_deg']<minimum_angle_deg:
        raise ValueError(f'marked refinement minimum angle {quality["min_angle_deg"]:.9g} is below required {minimum_angle_deg:.9g} degrees; improve the base mesh or revise the explicit quality requirement')
    quality.update(required_minimum_angle_deg=float(minimum_angle_deg),max_triangles=max_triangles)
    # The shared splitter emits each parent's children in input-cell order.
    parents=np.repeat(np.arange(len(triangles)),1+marked[cell_edges].sum(axis=1))
    ids=np.flatnonzero(marked);midpoint={tuple(edges[e]):len(mesh.points)+j for j,e in enumerate(ids)}
    references=[];identity=np.eye(3)
    for child,parent in zip(refined.triangles,parents):
        vertices=triangles[parent];coordinates={int(v):identity[i] for i,v in enumerate(vertices)}
        for i,j in ((0,1),(1,2),(2,0)):
            index=midpoint.get(tuple(sorted((vertices[i],vertices[j]))))
            if index is not None:coordinates[index]=(identity[i]+identity[j])/2
        if any(int(v) not in coordinates for v in child):raise ValueError('shared splitter child order differs from parent ancestry')
        references.append([coordinates[int(v)] for v in child])
    references=np.asarray(references)
    if case.element_order==2:
        old_space,new_space=quadratic_space(mesh),quadratic_space(refined)
        old_nodes,new_nodes=old_space.cell_dofs,new_space.cell_dofs
        old_count,new_count=len(old_space.dof_points),len(new_space.dof_points)
    else:
        old_nodes,new_nodes=triangles,refined.triangles;old_count,new_count=len(mesh.points),len(refined.points)
    coefficients=[None]*new_count
    for parent,nodes,vertices in zip(parents,new_nodes,references):
        locations=vertices if case.element_order==1 else np.vstack((vertices,(vertices[0]+vertices[1])/2,(vertices[1]+vertices[2])/2,(vertices[2]+vertices[0])/2))
        for node,bary in zip(nodes,locations):
            values=bary if case.element_order==1 else basis_p2(bary,np.zeros((3,2)))[0]
            row={int(i):float(v) for i,v in zip(old_nodes[parent],values) if v!=0}
            if coefficients[node] is not None and coefficients[node]!=row:raise ValueError('inconsistent shared-node prolongation')
            coefficients[node]=row
    rows,columns,values=[],[],[]
    for i,row in enumerate(coefficients):
        if row is None:raise ValueError('refinement produced an unowned degree of freedom')
        for j,value in row.items():rows.append(i);columns.append(j);values.append(value)
    prolongation=coo_matrix((values,(rows,columns)),shape=(new_count,old_count)).tocsr()
    split_edges=edges[ids].copy()
    for array in (parents,references,requested,split_edges):array.setflags(write=False)
    return MarkedRefinement(refined,prolongation,parents,references,requested,split_edges,quality)
