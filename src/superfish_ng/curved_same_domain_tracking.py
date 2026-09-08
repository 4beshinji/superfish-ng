# SPDX-License-Identifier: Apache-2.0
"""Compare curved native fields only after full quadratic boundary coincidence."""
import numpy as np
from .curved_solution import CurvedSolution
from .quadratic_boundary import QuadraticEdge
from .fem import triangle_quadrature
from .sampling import FieldSampler
from .mode_tracking import track_sampled_mode_subspaces


def _restricted_controls(edge,lo,hi):
    p=edge.control_points
    def evaluate(t):return (1-t)**2*p[0]+2*t*(1-t)*p[1]+t*t*p[2]
    return QuadraticEdge.from_nodes(evaluate(lo),evaluate(hi),evaluate((lo+hi)/2)).control_points


def compare_quadratic_boundaries(previous,current):
    """Compare Bernstein coefficients on every common primitive-parameter interval.

    The maximum norm of coefficient differences bounds positional difference
    throughout an interval by the Bernstein convex-hull property. Floating
    comparisons use an explicit geometry-scaled roundoff tolerance.
    """
    solutions=(previous,current)
    if any(not isinstance(s,CurvedSolution) for s in solutions):raise ValueError('curved_same_domain requires native curved solutions on both sides')
    if previous.case.curved_contour.to_dict()!=current.case.curved_contour.to_dict():
        raise ValueError('curved_same_domain requires identical native curve declarations and parameterization')
    for s in solutions:
        if any(tag not in ('axis','pec') for tag in s.space.boundary_tags):raise ValueError('curved_same_domain requires closed PEC and axis boundaries')
    scale=max(float(np.max(np.abs(s.space.geometry.points_rz_m))) for s in solutions)
    tolerance=512*np.finfo(float).eps*scale;parameter_tolerance=512*np.finfo(float).eps
    partitions=[]
    for solution in solutions:
        geometry=solution.space.geometry;curves=[[] for _ in solution.case.curved_contour.curves]
        for nodes,owner,parameters,tag in zip(geometry.boundary_nodes,geometry.boundary_curve_indices,geometry.boundary_parameters,solution.space.boundary_tags):
            lo,hi=map(float,parameters);a,b,mid=geometry.points_rz_m[nodes]
            if hi<lo:lo,hi=hi,lo;a,b=b,a
            if not hi-lo>parameter_tolerance:raise ValueError('quadratic boundary parameter interval is unresolved at roundoff scale')
            curves[int(owner)].append((lo,hi,QuadraticEdge.from_nodes(a,b,mid),str(tag)))
        for entries in curves:
            entries.sort(key=lambda e:e[0])
            if (not entries or abs(entries[0][0])>parameter_tolerance or abs(entries[-1][1]-1)>parameter_tolerance
                    or any(abs(a[1]-b[0])>parameter_tolerance for a,b in zip(entries,entries[1:]))):
                raise ValueError('quadratic boundary parameters must cover each native curve without gaps or overlaps')
        partitions.append(curves)
    maximum=0.;count=0
    for old,new in zip(*partitions):
        i=j=0
        while i<len(old) and j<len(new):
            a,b=old[i],new[j];lo=max(a[0],b[0]);hi=min(a[1],b[1])
            if hi>lo:
                if a[3]!=b[3]:raise ValueError('quadratic boundary tags differ')
                first=_restricted_controls(a[2],(lo-a[0])/(a[1]-a[0]),(hi-a[0])/(a[1]-a[0]))
                second=_restricted_controls(b[2],(lo-b[0])/(b[1]-b[0]),(hi-b[0])/(b[1]-b[0]))
                difference=float(np.max(np.linalg.norm(first-second,axis=1)));maximum=max(maximum,difference);count+=1
                if difference>tolerance:raise ValueError('quadratic boundary differs despite common analytic curves; preserve the represented boundary or declare another mapping')
            old_end,new_end=a[1],b[1]
            if old_end<=new_end+parameter_tolerance:i+=1
            if new_end<=old_end+parameter_tolerance:j+=1
    return dict(common_interval_count=count,maximum_coefficient_distance_m=maximum,roundoff_tolerance_m=tolerance,
        parameter_roundoff_tolerance=parameter_tolerance,criterion='Bernstein coefficient distance on common native-parameter intervals; whole-edge positional bound with floating roundoff tolerance')


def track_curved_same_domain_modes(previous,current,previous_ids,*,mapping,sample_order,**controls):
    if mapping!='curved_same_domain':raise ValueError('explicit mapping must be curved_same_domain')
    if type(sample_order) is not int or not 2<=sample_order<=32:raise ValueError('curved_same_domain sample_order must be an integer from 2 to 32')
    boundary=compare_quadratic_boundaries(previous,current);solutions=(previous,current)
    counts=[len(s.space.geometry.cell_nodes) for s in solutions];count=sum(counts)*sample_order**2
    if count>262144:raise ValueError('curved_same_domain exceeds 262144 samples; reduce sample_order or mesh size')
    rule=list(triangle_quadrature(order=sample_order));q=np.array([b[1:] for b,_ in rule]);reference=np.array([w for _,w in rule])
    samplers=[FieldSampler.from_solution(s) for s in solutions];values=[[],[]];weights=[];volumes=[]
    for side,solution in enumerate(solutions):
        g=solution.space.geometry;points=[];own=[];measure=[]
        for cell,mapping_cell in enumerate(g.local_maps):
            data=mapping_cell.evaluate(q);r=data['points_rz_m'][:,0];det=data['determinant_m2']
            points.append(data['points_rz_m']);own.append(r[:,None]*(data['basis_values']@solution.u[g.cell_nodes[cell]]));measure.append(r*det*reference)
        points=np.concatenate(points);measure=np.concatenate(measure)
        if not np.isfinite(measure).all() or np.any(measure<=0):raise ValueError('curved comparison requires positive finite volume weights')
        values[side].append(np.concatenate(own));other=1-side
        values[other].append(np.column_stack([samplers[other].evaluate(points,i,outside='raise')['Hphi_A_per_m'] for i in range(len(solutions[other].frequencies_hz))]))
        weights.append(measure/2);volumes.append(float(2*np.pi*np.sum(measure)))
    report=track_sampled_mode_subspaces(*[np.concatenate(v) for v in values],np.concatenate(weights),previous.frequencies_hz,current.frequencies_hz,previous_ids,
        comparison_description='same represented quadratic boundary; physical Hphi at both curved meshes quadrature points; half-sum physical r dr dz measure',**controls)
    report['physical_mapping']=dict(name=mapping,sample_order=sample_order,sample_count=count,triangle_counts=counts,axisymmetric_volumes_m3=volumes,
        boundary_coincidence=boundary,field='Hphi_A_per_m',scope='identical native curve parameterization and coincident represented quadratic boundary; independent curved P2 connectivity; sample-order convergence required; not equality of distinct curve approximations or physical convergence acceptance')
    return report
