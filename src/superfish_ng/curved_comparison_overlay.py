# SPDX-License-Identifier: Apache-2.0
"""Exact common integration partitions of independent native P2 histories."""
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction as F
import numpy as np
from .config import integer
from .curved_comparison_correspondence import infer_curved_comparison_correspondence
from .curved_selection_transfer import UNIT,_prepare,_lineage,_area,_encode
from .planar_tracking_overlap import _clip,_cross
from .quadratic_geometry import QuadraticTriangle


@dataclass(frozen=True)
class CurvedComparisonOverlay:
    base_maps: tuple
    report: dict

    def evaluate(self,side,q):
        """Return physical points and determinants for common-triangle sampling."""
        data=[]
        for triangle in self.report['triangles']:
            vertices=np.array([[float(F(*v)) for v in p] for p in triangle['reference_vertices']])
            a,b,c=vertices;determinant=float(F(*triangle['reference_determinant']))
            if not np.isfinite(determinant) or determinant<=0:
                raise ValueError('curved common reference triangle is unresolved in floating arithmetic')
            item=self.base_maps[side][triangle['base_cell']].evaluate(a+q[:,0,None]*(b-a)+q[:,1,None]*(c-a))
            # The base evaluation also contains its own basis and Jacobian.
            # Those use base coordinates and are not common-triangle data.
            data.append(dict(points_rz_m=item['points_rz_m'],determinant_m2=item['determinant_m2']*determinant))
        return data


def build_curved_comparison_overlay(previous,current,*,boundary_pairing,max_pair_tests,max_triangles):
    """Intersect both final histories in corresponding initial reference cells.

    The base orientation and fan triangulation are fixed independently of IDs
    and of which side is previous. Every final cell on both sides is covered
    exactly. This integration partition is not a new FEM solution or a mesh
    reprojected onto the analytic boundary.
    """
    integer(max_pair_tests,'max_pair_tests');integer(max_triangles,'max_triangles')
    prepared=[_prepare(p) for p in (previous,current)];projects=[p for p,_,_ in prepared];bases=[s for _,s,_ in prepared]
    correspondence=infer_curved_comparison_correspondence([p.case for p in projects],bases,boundary_pairing=boundary_pairing)
    reference=correspondence['previous_reference_cell_nodes'];node_map=np.asarray(correspondence['current_node_for_previous'])
    base_maps=[];histories=[]
    for side,(project,base,limit) in enumerate(prepared):
        nodes=np.asarray(reference)
        if side:nodes=node_map[nodes]
        base_maps.append(tuple(QuadraticTriangle(base.geometry.points_rz_m[row]) for row in nodes))
        lookup={tuple(sorted(map(int,row[:3]))):i for i,row in enumerate(base.geometry.cell_nodes)}
        initial=[None]*len(nodes)
        for canonical,row in enumerate(nodes):
            native=lookup[tuple(sorted(map(int,row[:3])))];coordinates={int(node):UNIT[i] for i,node in enumerate(row[:3])}
            initial[native]=(canonical,tuple(coordinates[int(node)] for node in base.geometry.cell_nodes[native,:3]))
        histories.append(_lineage(project,base,min(limit,max_triangles),initial))
    if max(map(len,histories))>max_triangles:
        raise ValueError('curved common partition exceeds max_triangles before intersection')
    groups=[]
    for history in histories:
        group=defaultdict(list)
        for cell,(owner,vertices) in enumerate(history):group[owner].append((cell,vertices))
        groups.append(group)
    candidates=sum(len(rows)*len(groups[1][owner]) for owner,rows in groups[0].items())
    if candidates>max_pair_tests:
        raise ValueError(f'curved common partition requires {candidates} base-local pairs, exceeding max_pair_tests={max_pair_tests}')
    covered=[defaultdict(F),defaultdict(F)];totals=defaultdict(F);triangles=[]
    def bounds(vertices):return tuple((min(p[k] for p in vertices),max(p[k] for p in vertices)) for k in (0,1))
    for owner in range(len(reference)):
        for old,a in groups[0][owner]:
            box=bounds(a)
            for new,b in groups[1][owner]:
                if any(max(x[0],y[0])>=min(x[1],y[1]) for x,y in zip(box,bounds(b))):continue
                polygon=_clip(a,b)
                if _area(polygon)==0:continue
                # Collinear vertices do not change the convex intersection;
                # removing them gives the same fan in either direction.
                polygon=[p for i,p in enumerate(polygon) if _cross(polygon[i-1],p,polygon[(i+1)%len(polygon)])!=0]
                start=min(range(len(polygon)),key=lambda i:polygon[i]);polygon=polygon[start:]+polygon[:start]
                for i in range(1,len(polygon)-1):
                    vertices=(polygon[0],polygon[i],polygon[i+1]);determinant=_cross(*vertices)
                    if determinant<=0:raise ValueError('curved common reference triangle has nonpositive orientation')
                    if len(triangles)>=max_triangles:raise ValueError('curved common intersections exceed max_triangles / samples budget')
                    area=determinant/2;covered[0][old]+=area;covered[1][new]+=area;totals[owner]+=area
                    triangles.append((owner,vertices,old,new,determinant))
    for history,areas in zip(histories,covered):
        if any(areas[cell]!=_area(vertices) for cell,(_,vertices) in enumerate(history)):
            raise ValueError('curved common intersections do not exactly cover every final cell')
    if any(totals[owner]!=F(1,2) for owner in range(len(reference))):
        raise ValueError('curved common intersections do not exactly cover every initial triangle')
    triangles.sort(key=lambda row:(row[0],row[1]))
    report=dict(method='exact_rational_intersections_of_native_refinement_histories',base_correspondence=correspondence,
        final_cell_counts=list(map(len,histories)),base_local_pair_tests=candidates,
        base_reference_areas=[_encode(totals[i]) for i in range(len(reference))],
        triangles=[dict(base_cell=owner,previous_cell=old,current_cell=new,
            reference_vertices=[[_encode(x),_encode(y)] for x,y in vertices],reference_determinant=_encode(det))
            for owner,vertices,old,new,det in triangles],
        scope='complete common integration partition in boundary-anchored initial reference cells; physical P2 maps are restricted without reprojection; not new FEM connectivity, inferred physical correspondence or a quadrature error bound')
    for name,history,areas in zip(('previous','current'),histories,covered):
        report[name+'_cell_coverage']=[dict(cell=cell,base_cell=owner,reference_area=_encode(_area(vertices)),covered_reference_area=_encode(areas[cell]))
            for cell,(owner,vertices) in enumerate(history)]
    return CurvedComparisonOverlay(tuple(base_maps),report)
