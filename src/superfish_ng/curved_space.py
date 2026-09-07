# SPDX-License-Identifier: Apache-2.0
"""Conforming curved P2 spaces built from validated native chord meshes."""
from dataclasses import dataclass
from types import MappingProxyType
import numpy as np
from .curved_mesh import curve_geometry_candidate
from .quadratic_boundary import QuadraticEdge,separated_edges,adjacent_edges


def check_curved_edges(points,cell_nodes,boundary_nodes,*,max_boxes=10000):
    """Validate all unique geometric edges, including internal-edge intersections."""
    points = np.asarray(points)
    cells = np.asarray(cell_nodes)
    boundary = np.asarray(boundary_nodes)
    if points.dtype.kind not in 'iuf' or points.ndim!=2 or points.shape[1]!=2 or not np.isfinite(points).all():
        raise ValueError('curved space requires finite N by 2 points')
    if cells.dtype.kind not in 'iu' or cells.ndim!=2 or cells.shape[1]!=6 or not len(cells):
        raise ValueError('curved cells require six integer node indices')
    if np.any(cells<0) or np.any(cells>=len(points)):
        raise ValueError('curved cell index out of range')
    if boundary.dtype.kind not in 'iu' or boundary.ndim!=2 or boundary.shape[1]!=3:
        raise ValueError('curved boundary requires three integer node indices')
    if type(max_boxes) is not int or max_boxes<1:
        raise ValueError('max_boxes must be a positive integer')
    incidence = {}
    for index,nodes in enumerate(cells):
        if len(set(map(int,nodes)))!=6:
            raise ValueError('curved cell repeats a node')
        for i,(a,b) in enumerate(((0,1),(1,2),(2,0))):
            start,end,mid = map(int,(nodes[a],nodes[b],nodes[3+i]))
            incidence.setdefault(tuple(sorted((start,end))),[]).append((index,start,end,mid))
    mids = []
    for pair in incidence.values():
        if len(pair)>2 or len({p[3] for p in pair})!=1:
            raise ValueError('nonconforming shared quadratic edge')
        if len(pair)==2 and pair[0][1:3]!=pair[1][2:0:-1]:
            raise ValueError('shared edge orientations must oppose')
        mids.append(pair[0][3])
    vertices = set(map(int,cells[:,:3].ravel()))
    if len(set(mids))!=len(mids) or set(mids)&vertices:
        raise ValueError('each geometric edge requires its own midpoint node')
    expected = {(*edge,pair[0][3]) for edge,pair in incidence.items() if len(pair)==1}
    supplied = {(*sorted((int(a),int(b))),int(m)) for a,b,m in boundary}
    if supplied!=expected or len(boundary)!=len(expected):
        raise ValueError('curved boundary disagrees with cell incidence')
    if len(vertices)-len(incidence)+len(cells)!=1:
        raise ValueError('curved space must retain disk Euler characteristic')
    neighbors = [set() for _ in cells]
    for pair in incidence.values():
        if len(pair)==2:
            a,b = pair[0][0],pair[1][0]
            neighbors[a].add(b); neighbors[b].add(a)
    visited = {0}; pending = [0]
    while pending:
        for cell in neighbors[pending.pop()]-visited:
            visited.add(cell); pending.append(cell)
    if len(visited)!=len(cells):
        raise ValueError('curved cells must be connected')
    scale = float(np.max(np.ptp(points,axis=0)))
    if not np.isfinite(scale) or scale<=0:
        raise ValueError('curved space scale is invalid')
    p = (points-points[0])/scale
    padding = 512*np.finfo(float).eps
    keys = sorted(incidence)
    edges = [QuadraticEdge.from_nodes(p[a],p[b],p[incidence[(a,b)][0][3]]) for a,b in keys]
    for edge in edges:
        edge.regular(padding)
    bounds = np.array([edge.bounds(padding) for edge in edges])
    checked,pairs = 0,0
    for i,first in enumerate(edges):
        overlap = np.all(bounds[i,1]>=bounds[i+1:,0],axis=1)&np.all(bounds[i+1:,1]>=bounds[i,0],axis=1)
        for j in np.flatnonzero(overlap)+i+1:
            pairs += 1
            second = edges[j]
            shared = set(keys[i])&set(keys[j])
            if shared:
                node = next(iter(shared))
                a = first if keys[i][1]==node else QuadraticEdge(first.control_points[::-1])
                b = second if keys[j][0]==node else QuadraticEdge(second.control_points[::-1])
                checked += adjacent_edges(a,b,padding=padding,max_boxes=max_boxes)
            else:
                checked += separated_edges(first,second,padding=padding,max_boxes=max_boxes)
    return dict(status='PASS',edges=len(edges),overlapping_box_pairs=pairs,boxes_checked=checked,
                cells=len(cells),euler_characteristic=1,scope='all unique quadratic edges and shared topology')


@dataclass(frozen=True)
class CurvedSpace:
    geometry: object
    boundary_tags: np.ndarray
    axis_dofs: np.ndarray
    constrained_dofs: np.ndarray
    edge_check: object


def curved_space(case,mesh):
    geometry = curve_geometry_candidate(case,mesh)
    report = check_curved_edges(geometry.points_rz_m,geometry.cell_nodes,geometry.boundary_nodes)
    tags = np.asarray(mesh.boundary_tags).copy()
    axis = np.unique(geometry.boundary_nodes[tags=='axis'])
    axis = axis[np.argsort(geometry.points_rz_m[axis,1])]
    constrained = np.unique(geometry.boundary_nodes[tags=='magnetic_symmetry'])
    for array in (tags,axis,constrained):
        array.setflags(write=False)
    return CurvedSpace(geometry,tags,axis,constrained,MappingProxyType(report))
