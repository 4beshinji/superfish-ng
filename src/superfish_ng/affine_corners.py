# SPDX-License-Identifier: Apache-2.0
"""Exact sign diagnostics of the prescribed affine polygon's boundary turns."""
from fractions import Fraction
from .contour import Contour


def classify_affine_corners(case):
    if case.geometry_order!=1:raise ValueError('affine corner diagnosis requires straight geometry')
    contour=case.contour if case.contour is not None else Contour.from_profile(case)
    points=[tuple(Fraction(float(v)) for v in p) for p in contour.vertices_zr_m];tags=contour.edge_tags;joins=[]
    approximated=case.curved_contour is not None or case.geometry_type=='arc_profile'
    for i,p in enumerate(points):
        a=points[i-1];b=points[(i+1)%len(points)];incoming=tuple(p[k]-a[k] for k in range(2));outgoing=tuple(b[k]-p[k] for k in range(2))
        cross=incoming[0]*outgoing[1]-incoming[1]*outgoing[0];dot=sum(x*y for x,y in zip(incoming,outgoing));before,after=tags[i-1],tags[i]
        if before==after=='axis':category='axis_subdivision'
        elif 'axis' in (before,after):
            wall=outgoing if before=='axis' else incoming
            category='orthogonal_axis_join' if wall[0]==0 else 'unverified_axis_join'
        elif before==after=='pec':
            category='reentrant_pec_corner' if cross<0 else 'convex_pec_corner' if cross>0 else 'straight_pec_join' if dot>0 else 'unverified_turn'
        elif before==after and before.endswith('_symmetry') and cross==0 and dot>0:category='symmetry_subdivision'
        elif set((before,after)) in ({'pec','electric_symmetry'},{'pec','magnetic_symmetry'}) and cross>0 and dot==0:
            category='orthogonal_symmetry_join'
        else:category='unverified_boundary_join'
        joins.append(dict(vertex_index=i,point_zr_m=[float(v) for v in p],incoming_tag=before,outgoing_tag=after,
            cross_sign=(cross>0)-(cross<0),dot_sign=(dot>0)-(dot<0),classification=category))
    uncertain=any(j['classification'].startswith('unverified') for j in joins)
    reentrant=any(j['classification']=='reentrant_pec_corner' for j in joins)
    status='UNVERIFIED_GEOMETRY' if approximated else 'SINGULAR_GEOMETRY' if reentrant else 'UNVERIFIED_GEOMETRY' if uncertain else 'NO_REENTRANT_CORNERS'
    return dict(status=status,analytic_geometry_approximated=approximated,joins=joins,
        scope='exact binary prescribed-polygon turns and orthogonal axis/symmetry joins; a reentrant corner prevents peak acceptance, but singular coefficients and physical regularity are not proved')
