# SPDX-License-Identifier: Apache-2.0
"""Conforming restrictions of the original xy quadratic maps.

Uniform red refinement, opposite-edge bisection and boundary-cell red refinement
with shared-edge closure.
All coordinates come from exact rational parent evaluation, never a circle or
ellipse projection. Binary64 restriction differences are bounded explicitly.
"""
from dataclasses import dataclass
from fractions import Fraction
import numpy as np
from scipy.sparse import coo_matrix
from .planar_curved import PlanarCurvedDomain
from .planar_curved_geometry import _map_coefficients, immutable_array

_REFERENCE = ((0,0),(1,0),(0,1),(Fraction(1,2),0),(Fraction(1,2),Fraction(1,2)),(0,Fraction(1,2)))
_EDGES = ((0,1),(1,2),(2,0))


def _basis(point):
    x,y = point
    bary = (1-x-y,x,y)
    return tuple(v*(2*v-1) for v in bary)+tuple(4*bary[i]*bary[j] for i,j in _EDGES)


def _evaluate(coefficients, point):
    x,y = point
    weights = (1,x,y,x*x,x*y,y*y)
    return tuple(sum(w*c[a] for w,c in zip(weights,coefficients)) for a in range(2))


def _patterns(marked):
    if len(marked)==3:
        return ((0,3,5),(3,1,4),(5,4,2),(3,4,5))
    if not marked:
        return ((0,1,2),)
    if len(marked)==1:
        edge=next(iter(marked));i,j=_EDGES[edge];opposite=3-i-j;mid=3+edge
        return ((opposite,i,mid),(opposite,mid,j))
    # Rotate a two-marked-edge template; the unmarked edge is opposite the
    # shared endpoint. This is a conforming green closure, not hanging nodes.
    unmarked=next(iter(set(range(3))-marked))
    i,j=_EDGES[unmarked];v=3-i-j
    def midpoint(a,b):
        return 3+next(k for k,pair in enumerate(_EDGES) if set(pair)=={a,b})
    vi,vj=midpoint(v,i),midpoint(v,j)
    return ((v,vi,vj),(vi,i,j),(vi,j,vj))


@dataclass(frozen=True)
class PlanarCurvedRefinement:
    original_domain: PlanarCurvedDomain
    domain: PlanarCurvedDomain
    parent_cells: np.ndarray
    parent_reference_vertices: np.ndarray
    prolongation: object
    coordinate_error_bounds_m: np.ndarray
    maximum_relative_coordinate_bound: float
    pattern: str


def refine_planar_curved_domain(domain, *, pattern='uniform', max_geometry_boxes=None):
    if not isinstance(domain,PlanarCurvedDomain) or pattern not in ('uniform','bisection','boundary'):
        raise ValueError('curved planar refinement requires a PlanarCurvedDomain and uniform/bisection/boundary pattern')
    budget=domain.max_geometry_boxes if max_geometry_boxes is None else max_geometry_boxes
    marked=set()
    if pattern=='bisection':
        marked={tuple(sorted(map(int,cell[1:3]))) for cell in domain.cell_nodes}
    elif pattern=='boundary':
        boundary_edges={tuple(sorted(map(int,edge[:2]))) for edge in domain.boundary_nodes}
        for cell in domain.cell_nodes:
            edges={tuple(sorted((int(cell[a]),int(cell[b])))) for a,b in _EDGES}
            if edges & boundary_edges:
                marked.update(edges)
    points=domain.points_xy_m.tolist()
    cache={}
    rows,cols,values=[],[],[]
    def key(cell,ref):
        bary=(1-ref[0]-ref[1],ref[0],ref[1])
        return tuple(sorted((int(node),Fraction(weight)) for node,weight in zip(cell[:3],bary) if weight))
    for cell in domain.cell_nodes:
        for node,ref in zip(cell,_REFERENCE):
            cache[key(cell,ref)]=int(node)
    # Original nodes stay present; their scalar transfer is the identity.
    rows.extend(range(len(points)));cols.extend(range(len(points)));values.extend([1.]*len(points))
    new_cells,parents,charts,bounds=[],[],[],[]
    for parent,cell in enumerate(domain.cell_nodes):
        coefficients=_map_coefficients(domain.points_xy_m[cell])
        selected=set(range(3)) if pattern=='uniform' else {i for i,(a,b) in enumerate(_EDGES) if tuple(sorted((int(cell[a]),int(cell[b])))) in marked}
        for triangle in _patterns(selected):
            vertices=[_REFERENCE[i] for i in triangle]
            refs=vertices+[tuple((vertices[i][a]+vertices[j][a])/2 for a in range(2)) for i,j in _EDGES]
            actual=[];expected=[];nodes=[]
            for ref in refs:
                ref=tuple(Fraction(v) for v in ref)
                identity=key(cell,ref)
                coordinate=_evaluate(coefficients,ref)
                if identity not in cache:
                    index=len(points);cache[identity]=index
                    points.append([float(v) for v in coordinate])
                    for oldnode,weight in zip(cell,_basis(ref)):
                        if weight:
                            rows.append(index);cols.append(int(oldnode));values.append(float(weight))
                index=cache[identity]
                nodes.append(index)
                actual.append([Fraction(float(v)) for v in points[index]])
                expected.append(coordinate)
            error=[[a-b for a,b in zip(p,q)] for p,q in zip(actual,expected)]
            controls=error[:3]+[[2*error[3+i][a]-(error[j][a]+error[k][a])/2 for a in range(2)] for i,(j,k) in enumerate(_EDGES)]
            bound=[max(abs(p[a]) for p in controls) for a in range(2)]
            bounds.append([float(np.nextafter(float(v),np.inf)) if v else 0. for v in bound])
            new_cells.append(nodes);parents.append(parent);charts.append(vertices)
    incidence={}
    for cell in new_cells:
        for i,(a,b) in enumerate(_EDGES):
            start,end,mid=cell[a],cell[b],cell[3+i]
            incidence.setdefault(tuple(sorted((start,end))),[]).append((start,end,mid))
    exterior={pair[0][0]:pair[0] for pair in incidence.values() if len(pair)==1}
    boundary=[];start=int(domain.boundary_nodes[0,0]);node=start
    for _ in range(len(exterior)):
        if node not in exterior:
            raise ValueError('curved planar refinement generated a broken boundary')
        edge=exterior[node];boundary.append(edge);node=edge[1]
    if node!=start:
        raise ValueError('curved planar refinement boundary did not close')
    output=PlanarCurvedDomain(points,new_cells,boundary,budget)
    extents=np.max(np.ptp(output.points_xy_m[output.cell_nodes],axis=1),axis=1)
    bounds=np.array(bounds)
    relative=float(np.max(np.max(bounds,axis=1)/extents))
    if not np.isfinite(relative) or relative>512*np.finfo(float).eps:
        raise ValueError('curved planar refinement UNVERIFIED: parent restriction roundoff exceeds local resolution')
    transfer=coo_matrix((values,(rows,cols)),shape=(len(points),len(domain.points_xy_m))).tocsr()
    return PlanarCurvedRefinement(domain,output,immutable_array(parents,np.int64),
        immutable_array(charts,float),transfer,immutable_array(bounds,float),relative,pattern)
