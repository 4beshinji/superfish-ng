# SPDX-License-Identifier: Apache-2.0
"""Synthetic axis-current analytical fields, energies and oriented fluxes."""
import numpy as np
from superfish_ng.constants import MU0,TAU
from superfish_ng.axis_connected_mesh import AxisConnectedMesh
from superfish_ng.magnetic_materials import LinearMagneticMaterial,MagneticRegion
from superfish_ng.axis_magnetic_materials import AxisMagneticPartition
from superfish_ng.axis_magnetostatic_boundary import AxisMagnetostaticBoundary
from superfish_ng.axis_magnetostatic import AxisMagnetostaticCase
from scripts.electrostatic_reference import rectangle


def _shift(mesh,shift):
    delta=np.array([0.,shift]);return AxisConnectedMesh(mesh.outer_rz_m+delta,[h+delta for h in mesh.holes_rz_m],mesh.points_rz_m+delta,mesh.triangles)


def _boundary(mesh,outer_a,outer_h):
    radius=mesh.outer_rz_m[:,0].max();groups={k:[] for k in ('outer','bottom','top','axis')};other={}
    z0,z1=mesh.outer_rz_m[:,1].min(),mesh.outer_rz_m[:,1].max()
    for i,edge in enumerate(mesh.boundary_edges):
        v,w=mesh.points_rz_m[edge];r,z=(v+w)/2
        if r==0:key='axis'
        elif r==radius:key='outer'
        elif z==z0:key='bottom'
        elif z==z1:key='top'
        else:
            delta=w-v;normal=np.array([delta[1],-delta[0]])/np.linalg.norm(delta);value=float(normal[0]*outer_h(r))
            other.setdefault(value,[]).append(i);continue
        groups[key].append(i)
    boundaries=[AxisMagnetostaticBoundary('axis','axis_regularity',groups['axis'])]
    boundaries.append(AxisMagnetostaticBoundary('outer','fixed_aphi_over_r',groups['outer'],outer_a) if outer_a is not None
        else AxisMagnetostaticBoundary('outer','tangential_h',groups['outer'],outer_h(radius)))
    for name in ('bottom','top'):boundaries.append(AxisMagnetostaticBoundary(name,'tangential_h',groups[name],0.))
    for i,(value,edges) in enumerate(other.items()):boundaries.append(AxisMagnetostaticBoundary(f'hole-h-{i}','tangential_h',edges,value))
    return boundaries


def uniform_field(order=2,n=2,scale=1.,mu_r=3.,field_t=.02,boundary='fixed',shift=0.):
    mesh,_,radius,length=rectangle(True,2*n,4*n,scale);mesh=_shift(mesh,shift)
    p=AxisMagneticPartition(mesh,[LinearMagneticMaterial('magnetic',mu_r)],[MagneticRegion('all','magnetic',list(range(len(mesh.triangles))))])
    assert boundary in ('fixed','tangential');h=field_t/(MU0*mu_r)
    boundaries=_boundary(mesh,field_t/2 if boundary=='fixed' else None,lambda r:h)
    case=AxisMagnetostaticCase(p,dict(all=0.),boundaries,order,name='uniform-axial-field')
    def fields(points):
        r,z=np.asarray(points).T;a=np.full(len(r),field_t/2);b=np.column_stack((np.zeros(len(r)),np.full(len(r),field_t)))
        return a,r*a,b,b/(MU0*mu_r)
    flux=field_t*np.pi*radius**2;reaction=TAU*radius**2*length*h
    return case,dict(fields=fields,energy_j=.5*field_t**2/(MU0*mu_r)*np.pi*radius**2*length,
        source_current_a=0.,fixed_reaction_a_m2={'outer':reaction} if boundary=='fixed' else {},
        boundary_flux_wb=dict(axis=0.,outer=0.,bottom=-flux,top=flux),field_scale=abs(field_t),intensity_scale=abs(h))


def cylinder_current(order=2,n=2,scale=1.,mu_r=3.,current_density=2e5,outer_h=0.,boundary='tangential',shift=0.,holes=0):
    if holes:
        from scripts.curved_meridional_reference import fixture
        mesh=fixture(True,holes,n=n,scale=scale,shear=0.)[0]['base_mesh'];radius=mesh.outer_rz_m[:,0].max()
    else:mesh,_,radius,_=rectangle(True,2*n,4*n,scale)
    mesh=_shift(mesh,shift);mu=MU0*mu_r;constant=outer_h+current_density*radius
    p=AxisMagneticPartition(mesh,[LinearMagneticMaterial('magnetic',mu_r)],[MagneticRegion('all','magnetic',list(range(len(mesh.triangles))))])
    assert boundary in ('fixed','tangential')
    boundaries=_boundary(mesh,mu*(outer_h/2+current_density*radius/6) if boundary=='fixed' else None,lambda r:constant-current_density*r)
    case=AxisMagnetostaticCase(p,dict(all=current_density),boundaries,order,name='uniform-azimuthal-current')
    def fields(points):
        r,z=np.asarray(points).T;a=mu*(constant/2-current_density*r/3);h=np.column_stack((np.zeros(len(r)),constant-current_density*r))
        return a,r*a,mu*h,h
    energy=0.;source=0.
    for polygon,sign in [(mesh.outer_rz_m,1),*((h,-1) for h in mesh.holes_rz_m)]:
        r0,z0=polygon.min(axis=0);r1,z1=polygon.max(axis=0)
        energy+=sign*np.pi*mu*(z1-z0)*(constant**2*(r1**2-r0**2)/2-2*constant*current_density*(r1**3-r0**3)/3+current_density**2*(r1**4-r0**4)/4)
        source+=sign*current_density*(r1-r0)*(z1-z0)
    length=np.ptp(mesh.outer_rz_m[:,1]);flux=TAU*radius**2*mu*(constant/2-current_density*radius/3)
    reaction=TAU*radius**2*length*outer_h
    boundary_flux=dict(axis=0.,outer=0.,bottom=-flux,top=flux)
    if holes:boundary_flux=None  # Hole groups are assigned by Ht; compare total div B separately.
    return case,dict(fields=fields,energy_j=energy,source_current_a=source,fixed_reaction_a_m2={'outer':reaction} if boundary=='fixed' else {},
        boundary_flux_wb=boundary_flux,field_scale=mu*max(abs(constant),abs(outer_h)),intensity_scale=max(abs(constant),abs(outer_h)))


def layered_current(order=2,n=4,scale=1.,mu_scale=1.,current_density=2e5,shift=0.):
    mesh,_,radius,length=rectangle(True,2*n,4*n,scale);mesh=_shift(mesh,shift);cut=radius/2
    labels=mesh.points_rz_m[mesh.triangles][:,:,0].mean(axis=1)>=cut
    mus=np.array([2.,5.])*mu_scale;currents=np.array([1.,-.4])*current_density
    materials=[LinearMagneticMaterial(name,value) for name,value in zip(('inner','outer'),mus)]
    regions=[MagneticRegion('inside','inner',np.flatnonzero(~labels).tolist()),MagneticRegion('outside','outer',np.flatnonzero(labels).tolist())]
    p=AxisMagneticPartition(mesh,materials,regions);boundaries=_boundary(mesh,None,lambda r:0.)
    case=AxisMagnetostaticCase(p,dict(inside=currents[0],outside=currents[1]),boundaries,order,name='layered-azimuthal-current')
    constants=np.array([currents[0]*cut+currents[1]*(radius-cut),currents[1]*radius]);mu=MU0*mus
    def primitive(i,r):return mu[i]*(constants[i]*r*r/2-currents[i]*r**3/3)
    correction=primitive(0,cut)-primitive(1,cut)
    def fields(points):
        r,z=np.asarray(points).T;owners=(r>=cut).astype(int);h=constants[owners]-currents[owners]*r
        regular=mu[owners]*(constants[owners]/2-currents[owners]*r/3)
        upper=owners==1;regular[upper]+=correction/r[upper]**2
        return regular,r*regular,np.column_stack((np.zeros(len(r)),mu[owners]*h)),np.column_stack((np.zeros(len(r)),h))
    region_energy={}
    for i,(lo,hi) in enumerate(((0.,cut),(cut,radius))):
        c,j=constants[i],currents[i];region_energy[regions[i].id]=np.pi*mu[i]*length*(c*c*(hi**2-lo**2)/2-2*c*j*(hi**3-lo**3)/3+j*j*(hi**4-lo**4)/4)
    flux=TAU*(primitive(1,radius)+correction);current=length*(currents[0]*cut+currents[1]*(radius-cut))
    return case,dict(fields=fields,energy_j=sum(region_energy.values()),region_energy_j=region_energy,source_current_a=current,
        fixed_reaction_a_m2={},boundary_flux_wb=dict(axis=0.,outer=0.,bottom=-flux,top=flux),
        field_scale=max(mu)*max(abs(constants)),intensity_scale=max(abs(constants)),cut=cut)
