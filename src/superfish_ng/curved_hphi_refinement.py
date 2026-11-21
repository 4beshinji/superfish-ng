# SPDX-License-Identifier: Apache-2.0
"""Topology-preserving uniform native P2 restriction for vacuum Hphi spaces."""
from dataclasses import dataclass
from fractions import Fraction as F
import numpy as np
from scipy.sparse import coo_matrix
from .config import integer
from .curved_meridional_geometry import CurvedMeridionalGeometry,_polynomial
from .curved_hphi_comparison import CurvedHphiComparisonDomain,build_curved_hphi_comparison,CurvedHphiComparisonBudgetExceeded,_vertices

_REFERENCE=((F(0),F(0)),(F(1),F(0)),(F(0),F(1)),(F(1,2),F(0)),(F(1,2),F(1,2)),(F(0),F(1,2)))
_CHILDREN=((0,3,5),(3,1,4),(5,4,2),(3,4,5))


@dataclass(frozen=True)
class CurvedHphiRefinement:
    geometry: CurvedMeridionalGeometry
    native_cells: list
    prolongation: object
    diagnostic: dict


def _basis(point,order):
    x,y=point;b=(1-x-y,x,y)
    return b if order==1 else tuple(v*(2*v-1) for v in b)+(4*b[0]*b[1],4*b[1]*b[2],4*b[2]*b[0])


def refine_curved_hphi_geometry(geometry,*,element_order=2,max_triangles=250000,max_dofs=250000,
                                max_pair_tests=2000000):
    """Split each actual reference triangle into four without boundary reprojection.

    New physical midpoint coordinates are evaluated as exact rational P2
    polynomials and then rounded once to binary64. Axis midpoint constraints
    retain the native affine-axis convention. The explicit rounded-native
    comparison contract measures and bounds all resulting coefficient changes.
    Prolongation transfers scalar P1/P2 coefficients, not eigenfrequencies/RF.
    """
    if type(geometry) is not CurvedMeridionalGeometry:raise ValueError('complete curved Hphi geometry required')
    for name,value in (('element_order',element_order),('max_triangles',max_triangles),('max_dofs',max_dofs),('max_pair_tests',max_pair_tests)):
        integer(value,name)
    if element_order not in (1,2):raise ValueError('curved Hphi refinement supports scalar P1 or P2')
    if 4*len(geometry.cell_nodes)>max_triangles:
        raise CurvedHphiComparisonBudgetExceeded('curved Hphi refinement exceeds max_triangles')
    # Four children give 6 self pairs and 4 old/new pairs per parent.
    if 10*len(geometry.cell_nodes)>max_pair_tests:
        raise CurvedHphiComparisonBudgetExceeded('curved Hphi refinement exceeds max_pair_tests')
    expected_dofs=len(geometry.points_rz_m)+(2*len(geometry.edge_vertices)+3*len(geometry.cell_nodes) if element_order==2 else 0)
    if expected_dofs>max_dofs:
        raise CurvedHphiComparisonBudgetExceeded('curved Hphi refinement exceeds max_dofs')
    g=CurvedMeridionalGeometry.from_dict(geometry.to_dict())
    cells=[];owners=[];vertices=[]
    for owner,nodes in enumerate(g.cell_nodes):
        for child in _CHILDREN:
            cells.append([int(nodes[i]) for i in child]);owners.append(owner)
            vertices.append(tuple(_REFERENCE[i] for i in child))
    cells=np.asarray(cells,dtype=int)
    edges=np.unique(np.sort(cells[:,[[0,1],[1,2],[2,0]]].reshape(-1,2),axis=1),axis=0)
    dofs=len(g.points_rz_m)+(len(edges) if element_order==2 else 0)
    if dofs>max_dofs:raise CurvedHphiComparisonBudgetExceeded('curved Hphi refinement exceeds max_dofs')
    polynomial=[tuple(_polynomial(g.points_rz_m[row,k]) for k in (0,1)) for row in g.cell_nodes]
    edge_values={};charts=[]
    for cell,owner,points in zip(cells,owners,vertices):
        charts.append(dict(base_cell=owner,reference_vertices=_vertices(points)))
        for i,j in ((0,1),(1,2),(2,0)):
            key=tuple(sorted((int(cell[i]),int(cell[j]))));p=tuple((points[i][k]+points[j][k])/2 for k in (0,1))
            value=tuple(sum((v*p[0]**a*p[1]**b for (a,b),v in poly.items()),F(0)) for poly in polynomial[owner])
            if key in edge_values and edge_values[key]!=value:raise ValueError('inconsistent exact shared P2 restriction')
            edge_values[key]=value
    mids=np.asarray([[float(v) for v in edge_values[tuple(edge)]] for edge in edges])
    points=g.points_rz_m.copy()
    # Reconstruct each full boundary loop from topology, preserving holes/order.
    loops=[];axis_edges=set()
    for component in range(1+len(g.base_mesh.holes_rz_m)):
        successor={}
        for (a,b,mid),role,tag in zip(g.boundary_nodes,g.base_mesh.boundary_components,g.boundary_tags):
            if role!=component:continue
            successor[int(a)]=int(mid);successor[int(mid)]=int(b)
            if tag=='axis':axis_edges.update((tuple(sorted((int(a),int(mid)))),tuple(sorted((int(mid),int(b))))))
        start=min(successor);loop=[start]
        while successor[loop[-1]]!=start:loop.append(successor[loop[-1]])
        if len(loop)!=len(successor):raise ValueError('refined boundary component is not one complete oriented loop')
        loops.append(points[loop])
    for i,edge in enumerate(edges):
        if tuple(edge) in axis_edges:mids[i]=points[edge].mean(axis=0)
    base=type(g.base_mesh)(loops[0],loops[1:],points,cells)
    refined=CurvedMeridionalGeometry(base,edges,mids,max_boxes_per_pair=g.max_boxes_per_pair)
    domain=CurvedHphiComparisonDomain(g,g,'same_vacuum',restriction_policy='binary64_roundoff')
    comparison=build_curved_hphi_comparison(g,refined,domain,current_cells=charts,
        max_pair_tests=max_pair_tests,max_triangles=max_triangles)
    # Assemble every scalar nodal interpolation row from reference coordinates.
    rows=[None]*dofs
    for nodes,owner,points in zip(refined.cell_nodes,owners,vertices):
        samples=points if element_order==1 else points+tuple(tuple((points[i][k]+points[j][k])/2 for k in (0,1)) for i,j in ((0,1),(1,2),(2,0)))
        source=g.cell_nodes[owner,:3 if element_order==1 else 6]
        for node,point in zip(nodes,samples):
            values={int(i):v for i,v in zip(source,_basis(point,element_order)) if v}
            if rows[node] is not None and rows[node]!=values:raise ValueError('inconsistent shared scalar prolongation')
            rows[node]=values
    if any(row is None for row in rows):raise ValueError('refinement does not cover every scalar DOF')
    source_dofs=len(g.base_mesh.points_rz_m) if element_order==1 else len(g.points_rz_m)
    rr=[];cc=[];vv=[]
    for i,row in enumerate(rows):
        for j,v in row.items():rr.append(i);cc.append(j);vv.append(float(v))
    prolongation=coo_matrix((vv,(rr,cc)),shape=(dofs,source_dofs)).tocsr()
    for array in (prolongation.data,prolongation.indices,prolongation.indptr):array.setflags(write=False)
    report=dict(method='four_reference_children_of_original_quadratic_geometry',element_order=element_order,
        original_cells=len(g.cell_nodes),refined_cells=len(refined.cell_nodes),original_dofs=source_dofs,refined_dofs=dofs,
        geometry_comparison=comparison.report,area_relative_change=abs(refined.area_m2/g.area_m2-1),
        volume_relative_change=abs(refined.volume_m3/g.volume_m3-1),
        boundary_policy='all original P2 components restricted; no analytic-curve reprojection; native affine-axis midpoints retained',
        scope='scalar-space prolongation and bounded binary64 geometry restriction; not an eigenmode solve, frequency correction or discretization error bound')
    return CurvedHphiRefinement(refined,charts,prolongation,report)
