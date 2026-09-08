# SPDX-License-Identifier: Apache-2.0
"""Symmetric physical-volume sampling across independently triangulated domains."""
import numpy as np
from .curved_solution import CurvedSolution
from .fem import triangle_quadrature
from .sampling import FieldSampler
from .mode_tracking import track_sampled_mode_subspaces


def _same_boundary(first,second):
    meshes=(first.mesh,second.mesh)
    for mesh in meshes:
        if any(tag not in ('axis','pec') for tag in mesh.boundary_tags):
            raise ValueError('same_domain requires closed PEC and axis boundaries only')
    scale=max(float(np.max(np.abs(m.points))) for m in meshes)
    tolerance=128*np.finfo(float).eps*scale
    # Cover every boundary segment in both directions, allowing subdivision.
    # Endpoint-only tests would miss an intervening notch or an uncovered gap.
    for source,target in (meshes,meshes[::-1]):
        edges=target.points[target.boundary_edges]
        for edge,tag in zip(source.boundary_edges,source.boundary_tags):
            a,b=source.points[edge];length=np.linalg.norm(b-a);unit=(b-a)/length
            delta=edges-a;projection=delta@unit
            distance=np.abs(delta[:,:,0]*unit[1]-delta[:,:,1]*unit[0])
            aligned=(distance<=tolerance).all(axis=1)&(target.boundary_tags==tag)
            intervals=sorted((max(0.,float(min(t))),min(length,float(max(t)))) for t in projection[aligned])
            covered=0.
            for lo,hi in intervals:
                if hi<lo:continue
                if lo>covered+tolerance:break
                covered=max(covered,hi)
            if covered<length-tolerance:
                raise ValueError('same_domain boundary differs; use an explicit shape correspondence, not same-domain remeshing')
    return tolerance


def track_same_domain_modes(previous,current,previous_ids,*,mapping,sample_order,**controls):
    """Compare native Hphi on a common physical domain without node correspondence.

    Half of each mesh's positive volume quadrature forms a symmetric measure.
    This is sampled correspondence, not an exact mesh-intersection integral.
    """
    if mapping!='same_domain':raise ValueError('explicit mapping must be same_domain')
    if type(sample_order) is not int or not 2<=sample_order<=32:
        raise ValueError('same_domain sample_order must be an integer from 2 to 32 per triangle')
    if any(isinstance(s,CurvedSolution) for s in (previous,current)):
        raise ValueError('same_domain currently requires straight geometric triangles; differing curved boundary approximations need a common-domain map')
    tolerance=_same_boundary(previous,current)
    counts=[len(s.mesh.triangles) for s in (previous,current)]
    count=sum(counts)*sample_order**2
    if count>262144:raise ValueError('same_domain exceeds 262144 samples; reduce sample_order or comparison mesh size')
    rule=list(triangle_quadrature(order=sample_order));bary=np.array([b for b,_ in rule]);reference=np.array([w for _,w in rule])
    points=[];weights=[];volumes=[]
    for solution in (previous,current):
        vertices=solution.mesh.points[solution.mesh.triangles]
        coordinates=np.einsum('qi,tij->tqj',bary,vertices)
        determinants=np.linalg.det(np.stack((vertices[:,1]-vertices[:,0],vertices[:,2]-vertices[:,0]),axis=-1))
        measure=coordinates[:,:,0]*determinants[:,None]*reference
        if not np.isfinite(measure).all() or np.any(measure<=0):raise ValueError('same_domain requires positive finite physical volume weights')
        volumes.append(float(2*np.pi*np.sum(measure)));points.append(coordinates.reshape(-1,2));weights.append(measure.ravel()/2)
    points=np.concatenate(points);weights=np.concatenate(weights)
    samples=[]
    for solution in (previous,current):
        sampler=FieldSampler.from_solution(solution)
        samples.append(np.column_stack([sampler.evaluate(points,i,outside='raise')['Hphi_A_per_m'] for i in range(len(solution.frequencies_hz))]))
    report=track_sampled_mode_subspaces(*samples,weights,previous.frequencies_hz,current.frequencies_hz,previous_ids,
        comparison_description='identical straight-sided physical domain; Hphi at both meshes triangle quadrature points; half-sum physical r dr dz measure; no node or cell correspondence',**controls)
    report['physical_mapping']=dict(name=mapping,sample_order=sample_order,sample_count=count,triangle_counts=counts,
        axisymmetric_volumes_m3=volumes,boundary_roundoff_tolerance_m=tolerance,field='Hphi_A_per_m',
        quadrature='half of each mesh positive triangle quadrature, weighted by physical radius and determinant; common 2*pi omitted',
        scope='same represented polygonal domain, including folded boundaries; independent connectivity and P1/P2 fields; sample-order convergence required; not changed-shape correspondence or FEM convergence acceptance')
    return report
