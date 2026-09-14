# SPDX-License-Identifier: Apache-2.0
"""Compare curved native fields only after full quadratic boundary coincidence."""
import numpy as np
from .curved_solution import CurvedSolution
from .te import TESolution,is_te
from .quadratic_boundary import QuadraticEdge
from .fem import triangle_quadrature
from .sampling import FieldSampler
from .mode_tracking import track_sampled_mode_subspaces


def _te_end_conditions(cases):
    from .te import validate_te_case
    for case in cases:validate_te_case(case)
    conditions=[(case.z_min,case.z_max) for case in cases]
    if conditions[0]!=conditions[1] or sum(tag!='pec' for tag in conditions[0])>1:
        raise ValueError('TE curved comparison requires the same symmetry sector and at most one symmetry end')
    return conditions[0]


def _te_symmetry_sector(solutions):
    reflected=[s.reflection_source_case is not None for s in solutions]
    if reflected[0]!=reflected[1]:
        raise ValueError('TE curved comparison cannot mix direct and reflected fields')
    conditions=_te_end_conditions([s.reflection_source_case or s.case for s in solutions])
    if reflected[0] and conditions==('pec','pec'):
        raise ValueError('TE reflected comparison requires a source symmetry sector')
    if conditions==('pec','pec'):return None
    return dict(source_end_conditions=dict(zip(('z_min','z_max'),conditions)),reflected=reflected[0],
                mode_indices='source symmetry-sector frequency order; not full-spectrum ranks')


def _restricted_controls(edge,lo,hi):
    p=edge.control_points
    def evaluate(t):return (1-t)**2*p[0]+2*t*(1-t)*p[1]+t*t*p[2]
    return QuadraticEdge.from_nodes(evaluate(lo),evaluate(hi),evaluate((lo+hi)/2)).control_points


def compare_quadratic_boundaries(previous,current):
    """Require identical native declarations and coincident whole quadratic edges."""
    return _compare_quadratic_boundaries(previous,current)


def _affine_points(points,affine,inverse=False):
    a,b,c=affine
    result=np.empty_like(points)
    with np.errstate(over='ignore',invalid='ignore',divide='ignore'):
        if inverse:
            result[:,0]=points[:,0]/a;result[:,1]=(points[:,1]-b*result[:,0])/c
        else:
            result[:,0]=a*points[:,0];result[:,1]=b*points[:,0]+c*points[:,1]
    if not np.isfinite(result).all():raise ValueError('affine map produces nonfinite curved coordinates')
    return result


def _compare_quadratic_boundaries(previous,current,affine=None):
    """Compare Bernstein coefficients on every common primitive-parameter interval.

    The maximum norm of coefficient differences bounds positional difference
    throughout an interval by the Bernstein convex-hull property. Floating
    comparisons use an explicit geometry-scaled roundoff tolerance.
    """
    solutions=(previous,current)
    if any(not isinstance(s,(CurvedSolution,TESolution)) or s.case.geometry_order!=2 for s in solutions):raise ValueError('curved_same_domain requires native curved solutions on both sides')
    te=[is_te(s.case) for s in solutions]
    if any(te) and not all(te):raise ValueError('mixed TE/TM curved correspondence is unsupported')
    if all(te):
        sector=_te_symmetry_sector(solutions)
        if sector is not None and affine is not None and affine[1]!=0:
            raise ValueError('TE symmetry affine comparison requires zero axial shear to preserve the symmetry plane')
    return compare_quadratic_space_boundaries(previous.case,previous.space,current.case,current.space,affine=affine)


def compare_quadratic_space_boundaries(previous_case,previous_space,current_case,current_space,*,affine=None):
    """Compare whole boundaries of two already validated native quadratic spaces."""
    cases=(previous_case,current_case);spaces=(previous_space,current_space)
    if affine is None and previous_case.curved_contour.to_dict()!=current_case.curved_contour.to_dict():
        raise ValueError('curved_same_domain requires identical native curve declarations and parameterization')
    if len(previous_case.curved_contour.curves)!=len(current_case.curved_contour.curves):
        raise ValueError('affine quadratic boundary comparison requires corresponding native primitive indices and parameters')
    allowed=('axis','pec')
    if all(is_te(case) for case in cases):
        _te_end_conditions(cases)
        allowed+=('electric_symmetry','magnetic_symmetry')
    for space in spaces:
        if any(tag not in allowed for tag in space.boundary_tags):raise ValueError('curved_same_domain requires PEC/axis boundaries or a matching TE symmetry sector')
    coordinates=[s.geometry.points_rz_m for s in spaces]
    if affine is not None:coordinates[1]=_affine_points(coordinates[1],affine,inverse=True)
    scale=max(float(np.max(np.abs(p))) for p in coordinates)
    tolerance=512*np.finfo(float).eps*scale;parameter_tolerance=512*np.finfo(float).eps
    partitions=[]
    for case,space,points in zip(cases,spaces,coordinates):
        geometry=space.geometry;curves=[[] for _ in case.curved_contour.curves]
        for nodes,owner,parameters,tag in zip(geometry.boundary_nodes,geometry.boundary_curve_indices,geometry.boundary_parameters,space.boundary_tags):
            lo,hi=map(float,parameters);a,b,mid=points[nodes]
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
                if difference>tolerance:
                    if affine is not None:raise ValueError('affine_map quadratic boundary differs after pullback; check the map, primitive parameters and represented boundary')
                    raise ValueError('quadratic boundary differs despite common analytic curves; preserve the represented boundary or declare another mapping')
            old_end,new_end=a[1],b[1]
            if old_end<=new_end+parameter_tolerance:i+=1
            if new_end<=old_end+parameter_tolerance:j+=1
    return dict(common_interval_count=count,maximum_coefficient_distance_m=maximum,roundoff_tolerance_m=tolerance,
        parameter_roundoff_tolerance=parameter_tolerance,criterion='Bernstein coefficient distance on common native-parameter intervals; whole-edge positional bound with floating roundoff tolerance')


def track_curved_same_domain_modes(previous,current,previous_ids,*,mapping,sample_order,**controls):
    if mapping!='curved_same_domain':raise ValueError('explicit mapping must be curved_same_domain')
    return _track_curved_modes(previous,current,previous_ids,sample_order=sample_order,**controls)


def _track_curved_modes(previous,current,previous_ids,*,sample_order,affine=None,**controls):
    if type(sample_order) is not int or not 2<=sample_order<=32:raise ValueError('curved_same_domain sample_order must be an integer from 2 to 32')
    boundary=_compare_quadratic_boundaries(previous,current,affine);solutions=(previous,current)
    te=is_te(previous.case);field='Ephi_V_per_m' if te else 'Hphi_A_per_m'
    counts=[len(s.space.geometry.cell_nodes) for s in solutions];count=sum(counts)*sample_order**2
    if count>262144:raise ValueError('curved_same_domain exceeds 262144 samples; reduce sample_order or mesh size')
    rule=list(triangle_quadrature(order=sample_order));q=np.array([b[1:] for b,_ in rule]);reference=np.array([w for _,w in rule])
    samplers=[FieldSampler.from_solution(s) for s in solutions];values=[[],[]];weights=[];volumes=[]
    for side,solution in enumerate(solutions):
        g=solution.space.geometry;points=[];own=[];measure=[]
        for cell,mapping_cell in enumerate(g.local_maps):
            data=mapping_cell.evaluate(q);r=data['points_rz_m'][:,0];det=data['determinant_m2']
            points.append(data['points_rz_m']);own.append(r[:,None]*(data['basis_values']@(solution.coefficients_v_per_m2 if te else solution.u)[g.cell_nodes[cell]]));measure.append(r*det*reference)
        points=np.concatenate(points);measure=np.concatenate(measure)
        if not np.isfinite(measure).all() or np.any(measure<=0):raise ValueError('curved comparison requires positive finite volume weights')
        own=np.concatenate(own)
        if affine is not None:
            a,b,c=affine;points=_affine_points(points,affine,inverse=side==1)
            if side==1:own=own/a;measure=measure/(a*a*c)
            if not np.isfinite(measure).all() or np.any(measure<=0):raise ValueError('affine curved comparison requires positive finite reference volume weights')
        values[side].append(own);other=1-side
        sampled=np.column_stack([samplers[other].evaluate(points,i,outside='raise')[field] for i in range(len(solutions[other].frequencies_hz))])
        if affine is not None and other==1:sampled=sampled/affine[0]
        values[other].append(sampled)
        weights.append(measure/2);volumes.append(float(2*np.pi*np.sum(measure)))
    report=track_sampled_mode_subspaces(*[np.concatenate(v) for v in values],np.concatenate(weights),previous.frequencies_hz,current.frequencies_hz,previous_ids,
        comparison_description=('same represented quadratic boundary; physical '+('Ephi' if te else 'Hphi')+' at both curved meshes quadrature points; half-sum physical r dr dz measure'),**controls)
    report['physical_mapping']=dict(name='curved_same_domain',sample_order=sample_order,sample_count=count,triangle_counts=counts,axisymmetric_volumes_m3=volumes,
        boundary_coincidence=boundary,field=field,scope='identical native curve parameterization and coincident represented quadratic boundary; independent curved P2 connectivity; sample-order convergence required; not equality of distinct curve approximations or physical convergence acceptance')
    if te:
        report['physical_mapping']['physics']='axisymmetric_m0_te'
        sector=_te_symmetry_sector(solutions)
        if sector is not None:report['physical_mapping']['symmetry_sector']=sector
    return report
