# SPDX-License-Identifier: Apache-2.0
"""Conforming marked-cell restriction of the represented quadratic geometry."""
from dataclasses import dataclass
import math
from types import MappingProxyType
import numpy as np
from scipy.sparse import coo_matrix
from .config import integer
from .curved_split_pattern import CurvedSplitPattern,curved_topology_digest
from .curved_space import CurvedSpace,check_curved_edges
from .curved_refinement import RestrictedGeometry,_REFERENCE,_CHILDREN
from .quadratic_geometry import QuadraticTriangle,quadratic_minimum,_VANDERMONDE
from .quadratic_boundary import check_quadratic_boundary


@dataclass(frozen=True)
class CurvedMarkedRefinement:
    space: CurvedSpace
    prolongation: object
    parent_cells: np.ndarray
    parent_reference_vertices: np.ndarray
    requested_cells: np.ndarray
    split_edges: np.ndarray
    quality: object
    split_pattern: CurvedSplitPattern


def _maps(points,cells):
    maps=[]
    for nodes in cells:
        mapping=QuadraticTriangle(points[nodes]);radius=points[nodes,0]
        controls=np.r_[radius[:3],2*radius[3:]-.5*radius[:3]-.5*radius[[1,2,0]]]
        if np.any(controls<0) and quadratic_minimum(np.linalg.solve(_VANDERMONDE,radius))[0]<0:
            raise ValueError('curved restriction crosses r=0')
        maps.append(mapping)
    return tuple(maps)


def _minimum_corner_angle(maps):
    angles=[]
    for mapping in maps:
        jacobians=mapping.evaluate(_REFERENCE[:3])['jacobian']
        for i in range(3):
            a=jacobians[i]@(_REFERENCE[(i+1)%3]-_REFERENCE[i])
            b=jacobians[i]@(_REFERENCE[(i+2)%3]-_REFERENCE[i])
            a=a/max(abs(a));b=b/max(abs(b))
            angles.append(math.atan2(a[0]*b[1]-a[1]*b[0],float(a@b)))
    return float(np.rad2deg(min(angles)))


def refine_marked_curved_space(parent,marked_cells,*,max_triangles=250000,minimum_corner_angle_deg=5.,split_pattern=None):
    """Restrict selected curved triangles and conforming transition neighbors.

    Selection splits all three edges of each requested cell; a touched cell's
    longest endpoint chord is also split to close the refinement. One/two/three
    split-edge templates live in parent reference coordinates. No point is
    reprojected to an analytic curve. Corner angles measure mapped tangents,
    not a global Jacobian-conditioning or physical-error bound.
    An explicit split_pattern replays its topological choices and still checks
    the current geometry, conformity, positive maps, quality and cell budget.
    """
    if not isinstance(parent,CurvedSpace):raise ValueError('marked curved refinement requires a CurvedSpace')
    integer(max_triangles,'max_triangles')
    if type(minimum_corner_angle_deg) not in (int,float) or not math.isfinite(minimum_corner_angle_deg) or not 0<minimum_corner_angle_deg<60:
        raise ValueError('minimum_corner_angle_deg must be finite and between 0 and 60')
    g=parent.geometry;points_array=np.asarray(g.points_rz_m);nodes_array=np.asarray(g.cell_nodes)
    check_curved_edges(points_array,nodes_array,g.boundary_nodes)
    check_quadratic_boundary(points_array,g.boundary_nodes)
    if not np.array_equal(np.unique(nodes_array),np.arange(len(points_array))):raise ValueError('curved space has unused nodes')
    tags=np.asarray(parent.boundary_tags)
    if tags.shape!=(len(g.boundary_nodes),) or any(t not in ('axis','pec','electric_symmetry','magnetic_symmetry') for t in tags):raise ValueError('invalid curved boundary tags')
    axis=np.unique(g.boundary_nodes[tags=='axis']);axis=axis[np.argsort(points_array[axis,1])]
    constrained=np.unique(g.boundary_nodes[tags=='magnetic_symmetry'])
    if not np.array_equal(axis,parent.axis_dofs) or not np.array_equal(constrained,parent.constrained_dofs):raise ValueError('curved boundary constraints disagree with tags')
    if not len(axis) or np.any(points_array[axis,0]!=0):raise ValueError('curved space requires an exact axis boundary')
    curve_ids=np.asarray(g.boundary_curve_indices);parameters=np.asarray(g.boundary_parameters)
    if (curve_ids.shape!=(len(tags),) or curve_ids.dtype.kind not in 'iu' or np.any(curve_ids<0)
            or parameters.shape!=(len(tags),2) or parameters.dtype.kind not in 'iuf' or not np.isfinite(parameters).all()
            or np.any(parameters<0) or np.any(parameters>1) or np.any(parameters[:,0]==parameters[:,1])):
        raise ValueError('invalid curved boundary ancestry')
    maps=_maps(points_array,nodes_array)
    if type(marked_cells) is not list or not marked_cells or any(type(i) is not int or not 0<=i<len(nodes_array) for i in marked_cells) or len(set(marked_cells))!=len(marked_cells):
        raise ValueError('marked_cells requires distinct valid zero-based integer cell indices')
    requested=np.asarray(sorted(marked_cells),dtype=np.int64)
    vertices=nodes_array[:,:3]
    edges,inverse=np.unique(np.sort(vertices[:,[[0,1],[1,2],[2,0]]].reshape(-1,2),axis=1),axis=0,return_inverse=True)
    cell_edges=inverse.reshape(-1,3);marked=np.zeros(len(edges),dtype=bool);marked[cell_edges[requested]]=True
    scale=float(np.max(np.ptp(points_array,axis=0)))
    if split_pattern is None:
        lengths=np.linalg.norm((points_array[edges[:,1]]-points_array[edges[:,0]])/scale,axis=1)
        longest=cell_edges[np.arange(len(vertices)),np.argmax(lengths[cell_edges],axis=1)]
        while True:
            required=longest[marked[cell_edges].any(axis=1)]
            if marked[required].all():break
            marked[required]=True
    else:
        if not isinstance(split_pattern,CurvedSplitPattern):raise ValueError('split_pattern requires an immutable CurvedSplitPattern')
        split_pattern.__post_init__()
        if split_pattern.parent_topology_sha256!=curved_topology_digest(parent):
            raise ValueError('split pattern parent topology differs; use its original numbered mesh and preceding history, or capture a new pattern')
        if split_pattern.marked_cells!=tuple(map(int,requested)):raise ValueError('split pattern marked cells differ from the request')
        lookup={tuple(map(int,edge)):i for i,edge in enumerate(edges)}
        if any(edge not in lookup for edge in split_pattern.split_edges):raise ValueError('split pattern names an absent parent edge')
        marked[:]=False;marked[[lookup[edge] for edge in split_pattern.split_edges]]=True
        if not marked[cell_edges[requested]].all():raise ValueError('split pattern must split all three edges of every requested cell')
        expected=set(map(int,np.flatnonzero(marked[cell_edges].sum(axis=1)==2)))
        if {cell for cell,_ in split_pattern.transition_diagonals}!=expected:
            raise ValueError('split pattern must declare exactly the two-edge transition diagonals')
    declared_diagonals={} if split_pattern is None else dict(split_pattern.transition_diagonals)
    chosen_diagonals=[]
    count=len(vertices)+int(marked[cell_edges].sum())
    if count>max_triangles:raise ValueError(f'curved refinement needs {count} triangles, exceeding max_triangles={max_triangles}')
    points=list(points_array.copy());coefficients=[{i:1.} for i in range(len(points))]
    midpoints={tuple(sorted((int(nodes[a]),int(nodes[b])))):int(nodes[3+i]) for nodes in nodes_array for i,(a,b) in enumerate(((0,1),(1,2),(2,0)))}
    cells=[];owners=[];references=[];tolerance=512*np.finfo(float).eps*scale
    for cell,(nodes,mapping,es) in enumerate(zip(nodes_array,maps,cell_edges)):
        flags=marked[es];number=int(flags.sum())
        if number==0:children=[(0,1,2)]
        elif number==3:children=_CHILDREN
        elif number==1:
            i=int(np.flatnonzero(flags)[0]);a,b,c=np.roll(np.arange(3),-i);m=3+i
            children=[(a,m,c),(m,b,c)]
        else:
            i=int(np.flatnonzero(~flags)[0]);a,b,c=np.roll(np.arange(3),-i);bc=3+(i+1)%3;ca=3+(i+2)%3
            children=[(ca,bc,c)]
            diagonal=declared_diagonals[cell] if split_pattern is not None else int(
                np.linalg.norm((points_array[nodes[a]]-points_array[nodes[bc]])/scale)>np.linalg.norm((points_array[nodes[b]]-points_array[nodes[ca]])/scale))
            chosen_diagonals.append((cell,diagonal))
            if diagonal==0:
                children.extend(((a,b,bc),(a,bc,ca)))
            else:children.extend(((a,b,ca),(b,bc,ca)))
        for child in children:
            child=np.asarray(child);child_vertices=nodes[child];mids=[]
            for a,b in ((0,1),(1,2),(2,0)):
                key=tuple(sorted((int(child_vertices[a]),int(child_vertices[b]))))
                reference=(_REFERENCE[child[a]]+_REFERENCE[child[b]])/2
                evaluated=mapping.evaluate([reference]);proposal=evaluated['points_rz_m'][0]
                if points[key[0]][0]==0 and points[key[1]][0]==0 and proposal[0]==0:proposal=(points[key[0]]+points[key[1]])/2
                row={int(n):float(v) for n,v in zip(nodes,evaluated['basis_values'][0]) if v!=0}
                if key in midpoints:
                    index=midpoints[key]
                    if np.linalg.norm(points[index]-proposal)>tolerance or coefficients[index]!=row:raise ValueError('inconsistent shared curved geometry or coefficient restriction')
                else:
                    index=len(points);midpoints[key]=index;points.append(proposal);coefficients.append(row)
                mids.append(index)
            cells.append([*child_vertices,*mids]);owners.append(cell);references.append(_REFERENCE[child])
    edge_lookup={tuple(e):i for i,e in enumerate(edges)};boundary=[];new_tags=[];curve_indices=[];parameters=[]
    for (a,b,mid),tag,curve,(lo,hi) in zip(g.boundary_nodes,tags,g.boundary_curve_indices,g.boundary_parameters):
        if marked[edge_lookup[tuple(sorted((a,b)))]]:
            boundary.extend(((a,mid,midpoints[tuple(sorted((int(a),int(mid))))]),(mid,b,midpoints[tuple(sorted((int(mid),int(b))))])))
            new_tags.extend((tag,tag));curve_indices.extend((curve,curve));centre=(lo+hi)/2;parameters.extend(((lo,centre),(centre,hi)))
        else:boundary.append((a,b,mid));new_tags.append(tag);curve_indices.append(curve);parameters.append((lo,hi))
    points=np.asarray(points);cells=np.asarray(cells);boundary=np.asarray(boundary);new_tags=np.asarray(new_tags)
    curve_indices=np.asarray(curve_indices);parameters=np.asarray(parameters);owners=np.asarray(owners);references=np.asarray(references)
    maps=_maps(points,cells);angle=_minimum_corner_angle(maps)
    if angle<minimum_corner_angle_deg:raise ValueError(f'curved refinement minimum corner angle {angle:.9g} is below minimum_corner_angle_deg={minimum_corner_angle_deg}')
    boundary_check=MappingProxyType(check_quadratic_boundary(points,boundary));edge_check=MappingProxyType(check_curved_edges(points,cells,boundary))
    axis=np.unique(boundary[new_tags=='axis']);axis=axis[np.argsort(points[axis,1])];constrained=np.unique(boundary[new_tags=='magnetic_symmetry'])
    split_edges=edges[marked].copy()
    for array in (points,cells,boundary,new_tags,curve_indices,parameters,owners,references,axis,constrained,requested,split_edges):array.setflags(write=False)
    geometry=RestrictedGeometry(points,cells,boundary,curve_indices,parameters,maps,boundary_check)
    space=CurvedSpace(geometry,new_tags,axis,constrained,edge_check)
    rows=[];columns=[];values=[]
    for i,row in enumerate(coefficients):
        for j,value in row.items():rows.append(i);columns.append(j);values.append(value)
    prolongation=coo_matrix((values,(rows,columns)),shape=(len(points),len(points_array))).tocsr()
    quality=MappingProxyType(dict(triangles=len(cells),minimum_corner_angle_deg=angle,required_minimum_corner_angle_deg=float(minimum_corner_angle_deg),max_triangles=max_triangles,
        scope='mapped tangent angles at element corners and validated quadratic maps/edges; no global conditioning or physical error bound'))
    pattern=CurvedSplitPattern(curved_topology_digest(parent),tuple(map(int,requested)),
                               tuple(tuple(map(int,edge)) for edge in split_edges),tuple(chosen_diagonals))
    return CurvedMarkedRefinement(space,prolongation,owners,references,requested,split_edges,quality,pattern)
