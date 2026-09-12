# SPDX-License-Identifier: Apache-2.0
"""Fixed-current finite-boundary magnetic references with explicit remote limits."""
import numpy as np
from superfish_ng.constants import MU0,TAU
from superfish_ng.planar_mesh import PlanarMesh
from superfish_ng.axis_connected_mesh import AxisConnectedMesh
from superfish_ng.magnetic_materials import LinearMagneticMaterial,MagneticRegion,PlanarMagneticPartition
from superfish_ng.axis_magnetic_materials import AxisMagneticPartition
from superfish_ng.magnetostatic_boundary import MagnetostaticBoundary
from superfish_ng.axis_magnetostatic_boundary import AxisMagnetostaticBoundary
from superfish_ng.planar_magnetostatic import PlanarMagnetostaticCase
from superfish_ng.axis_magnetostatic import AxisMagnetostaticCase
from scripts.electrostatic_boundary_reference import grid


def current_slab(order=2,n=8,outer_ratio=2.,mu_r=3.,sign=1.):
    assert outer_ratio in (2.,4.,8.)
    a=.03125;width=.0625;b=a*outer_ratio;mu=MU0*mu_r;current=sign*2e5
    points,cells=grid(np.linspace(0.,width,5),np.linspace(0.,b,int(outer_ratio)*n+1))
    mesh=PlanarMesh.create([[0.,0.],[width,0.],[width,b],[0.,b]],points,cells);core=points[cells][:,:,1].mean(axis=1)<a
    p=PlanarMagneticPartition(mesh,[LinearMagneticMaterial('magnetic',mu_r)],[MagneticRegion('source','magnetic',np.flatnonzero(core).tolist()),MagneticRegion('exterior','magnetic',np.flatnonzero(~core).tolist())])
    fixed=[];natural=[]
    for i,edge in enumerate(mesh.boundary_edges):(fixed if points[edge,1].mean()==b else natural).append(i)
    case=PlanarMagnetostaticCase(p,dict(source=current,exterior=0.),[MagnetostaticBoundary('fixed','fixed_az',fixed,0.),MagnetostaticBoundary('symmetry-and-sides','tangential_h',natural,0.)],order,name='fixed-current-slab')
    def fields(points):
        y=np.asarray(points)[:,1];az=np.where(y<a,mu*current*(a*b-a*a/2-y*y/2),mu*current*a*(b-y))
        h=np.column_stack((-current*np.minimum(y,a),np.zeros(len(y))))
        return az,mu*h,h
    probes=np.array([[width/3,y] for y in (.25*a,.75*a,1.25*a,1.75*a)])
    return case,dict(fields=fields,energy=mu*current**2*width*(a*a*b-2*a**3/3)/2,
        fixed_reaction=-current*width*a,common_points=probes,outer_distance_m=b,source_current=current*width*a,
        field_scale=mu*abs(current)*a,intensity_scale=abs(current)*a,potential_scale=mu*abs(current)*a*b,
        boundary_potential_shift=lambda other_b:mu*current*a*(other_b-b),
        interpretation='fixed slab current; common B/H independent of remote fixed Az, but Az offset and total J/m energy grow linearly with distance; no finite zero-at-infinity potential')


def current_cylinder(order=2,n=8,outer_ratio=2.,mu_r=3.,sign=1.):
    assert outer_ratio in (2.,4.,8.)
    a=.03125;length=.0625;b=a*outer_ratio;mu=MU0*mu_r;current=sign*2e5;background=-current*a**3/(3*b*b)
    points,cells=grid(np.linspace(0.,b,int(outer_ratio)*n+1),np.linspace(0.,length,5))
    mesh=AxisConnectedMesh([[0.,0.],[b,0.],[b,length],[0.,length]],[],points,cells);core=points[cells][:,:,0].mean(axis=1)<a
    p=AxisMagneticPartition(mesh,[LinearMagneticMaterial('magnetic',mu_r)],[MagneticRegion('source','magnetic',np.flatnonzero(core).tolist()),MagneticRegion('exterior','magnetic',np.flatnonzero(~core).tolist())])
    groups=dict(axis=[],fixed=[],ends=[])
    for i,edge in enumerate(mesh.boundary_edges):
        r=points[edge,0].mean();groups['axis' if r==0. else 'fixed' if r==b else 'ends'].append(i)
    case=AxisMagnetostaticCase(p,dict(source=current,exterior=0.),[AxisMagnetostaticBoundary('axis','axis_regularity',groups['axis']),
        AxisMagnetostaticBoundary('fixed','fixed_aphi_over_r',groups['fixed'],0.),AxisMagnetostaticBoundary('ends','tangential_h',groups['ends'],0.)],order,name='fixed-core-azimuthal-current')
    def fields(points):
        r=np.asarray(points)[:,0];regular=mu*(background/2+current*(a/2-r/3));outside=r>=a
        regular[outside]=mu*(background/2+current*a**3/(6*r[outside]**2))
        h=np.column_stack((np.zeros(len(r)),background+current*np.maximum(a-r,0.)))
        return regular,mu*h,h
    probes=np.array([[r,length/3] for r in (.25*a,.75*a,1.25*a,1.75*a)])
    infinite_energy=np.pi*mu*current**2*length*a**4/12
    finite_energy=infinite_energy-np.pi*mu*current**2*length*a**6/(18*b*b)
    def infinite_fields(points):
        r=np.asarray(points)[:,0];regular=mu*current*(a/2-r/3);outside=r>=a;regular[outside]=mu*current*a**3/(6*r[outside]**2)
        h=np.column_stack((np.zeros(len(r)),current*np.maximum(a-r,0.)))
        return regular,mu*h,h
    return case,dict(fields=fields,energy=finite_energy,infinite_energy=infinite_energy,infinite_fields=infinite_fields,
        fixed_reaction=-TAU*current*length*a**3/3,common_points=probes,outer_distance_m=b,source_current=current*a*length,
        field_scale=mu*abs(current)*a,intensity_scale=abs(current)*a,potential_scale=mu*abs(current)*a,
        background_h=background,boundary_background_h_shift=lambda other_b:-current*a**3/(3*other_b**2)-background,
        interpretation='fixed azimuthal current core; finite outer Aphi/r=0 adds uniform Hz=-Jphi*a^3/(3*b^2), which changes B and is not gauge; finite-boundary and infinite-cylinder fields are separate references')
