# SPDX-License-Identifier: Apache-2.0
"""Synthetic annular magnetic fields from integrating d_r Hz=-Jphi."""
import numpy as np
from superfish_ng.constants import MU0,TAU
from superfish_ng.meridional_mesh import MeridionalMesh
from superfish_ng.magnetic_materials import LinearMagneticMaterial,MagneticRegion
from superfish_ng.off_axis_magnetic_materials import OffAxisMagneticPartition
from superfish_ng.off_axis_magnetostatic_boundary import OffAxisMagnetostaticBoundary
from superfish_ng.off_axis_magnetostatic import OffAxisMagnetostaticCase
from scripts.electrostatic_reference import rectangle


def _mesh(n,scale,shift,holes):
    if holes:
        from scripts.curved_meridional_reference import fixture
        mesh=fixture(False,holes,n=n,scale=scale,shear=0.)[0]['base_mesh']
    else:mesh=rectangle(False,2*n,4*n,scale)[0]
    delta=np.array([0.,shift])
    return MeridionalMesh(mesh.outer_rz_m+delta,[h+delta for h in mesh.holes_rz_m],mesh.points_rz_m+delta,mesh.triangles)


def _boundaries(mesh,psi,h,boundary):
    lo=mesh.outer_rz_m.min(axis=0);hi=mesh.outer_rz_m.max(axis=0)
    groups={name:[] for name in ('inner','outer','bottom','top')};other={}
    for i,edge in enumerate(mesh.boundary_edges):
        v,w=mesh.points_rz_m[edge];r,z=(v+w)/2
        if r==lo[0]:name='inner'
        elif r==hi[0]:name='outer'
        elif z==lo[1]:name='bottom'
        elif z==hi[1]:name='top'
        else:
            delta=w-v;ht=float(h(r)*delta[1]/np.linalg.norm(delta));other.setdefault(ht,[]).append(i);continue
        groups[name].append(i)
    result=[OffAxisMagnetostaticBoundary('inner','fixed_psi',groups['inner'],psi(lo[0]))]
    assert boundary in ('fixed','tangential')
    result.append(OffAxisMagnetostaticBoundary('outer','fixed_psi',groups['outer'],psi(hi[0])) if boundary=='fixed'
        else OffAxisMagnetostaticBoundary('outer','tangential_h',groups['outer'],h(hi[0])))
    for name in ('bottom','top'):result.append(OffAxisMagnetostaticBoundary(name,'tangential_h',groups[name],0.))
    for i,(value,edges) in enumerate(other.items()):result.append(OffAxisMagnetostaticBoundary(f'hole-h-{i}','tangential_h',edges,value))
    return result


def annular_current(order=2,n=2,scale=1.,mu_r=3.,current_density=2e5,outer_h=0.,boundary='tangential',shift=0.,holes=0,reference_psi=0.):
    mesh=_mesh(n,scale,shift,holes);a,z0=mesh.outer_rz_m.min(axis=0);b,z1=mesh.outer_rz_m.max(axis=0)
    mu=MU0*mu_r;c=outer_h+current_density*b;length=z1-z0
    def primitive(r):return mu*(c*r*r/2-current_density*r**3/3)
    def psi(r):return reference_psi+primitive(r)-primitive(a)
    def h(r):return c-current_density*r
    p=OffAxisMagneticPartition(mesh,[LinearMagneticMaterial('magnetic',mu_r)],[MagneticRegion('all','magnetic',list(range(len(mesh.triangles))))])
    case=OffAxisMagnetostaticCase(p,dict(all=current_density),_boundaries(mesh,psi,h,boundary),order,name='synthetic-annular-current')
    def fields(points):
        r,z=np.asarray(points).T;potential=psi(r);intensity=np.column_stack((np.zeros(len(r)),h(r)))
        return potential,potential/r,mu*intensity,intensity
    energy=current=0.
    for polygon,sign in [(mesh.outer_rz_m,1),*((hole,-1) for hole in mesh.holes_rz_m)]:
        r0,w0=polygon.min(axis=0);r1,w1=polygon.max(axis=0)
        energy+=sign*np.pi*mu*(w1-w0)*(c*c*(r1*r1-r0*r0)/2-2*c*current_density*(r1**3-r0**3)/3+current_density**2*(r1**4-r0**4)/4)
        current+=sign*current_density*(r1-r0)*(w1-w0)
    reaction=dict(inner=-TAU*length*h(a))
    if boundary=='fixed':reaction['outer']=TAU*length*h(b)
    flux=TAU*(psi(b)-psi(a));field_scale=mu*max(abs(h(a)),abs(h(b)))
    return case,dict(fields=fields,energy_j=energy,source_current_a=current,fixed_reaction_a=reaction,
        boundary_flux_wb=None if holes else dict(inner=0.,outer=0.,bottom=-flux,top=flux),
        field_scale=field_scale,intensity_scale=field_scale/mu,potential_scale=field_scale*b*b,
        interpretation='flux is through annular surfaces in the declared domain; excluded-axis absolute flux is not supplied')


def uniform_field(order=2,n=2,scale=1.,mu_r=3.,field_t=.02,boundary='fixed',shift=0.,holes=0,reference_psi=0.):
    return annular_current(order,n,scale,mu_r,0.,field_t/(MU0*mu_r),boundary,shift,holes,reference_psi)


def layered_current(order=2,n=4,scale=1.,mu_scale=1.,current_density=2e5,shift=0.,reference_psi=0.):
    mesh=_mesh(n,scale,shift,0);a,z0=mesh.outer_rz_m.min(axis=0);b,z1=mesh.outer_rz_m.max(axis=0);cut=(a+b)/2;length=z1-z0
    labels=mesh.points_rz_m[mesh.triangles][:,:,0].mean(axis=1)>=cut;mus=np.array([2.,5.])*mu_scale;mu=MU0*mus
    currents=np.array([1.,-.4])*current_density;constants=np.array([currents[0]*cut+currents[1]*(b-cut),currents[1]*b])
    materials=[LinearMagneticMaterial(name,v) for name,v in zip(('inner','outer'),mus)]
    regions=[MagneticRegion('inside','inner',np.flatnonzero(~labels).tolist()),MagneticRegion('outside','outer',np.flatnonzero(labels).tolist())]
    p=OffAxisMagneticPartition(mesh,materials,regions)
    def primitive(i,r):return mu[i]*(constants[i]*r*r/2-currents[i]*r**3/3)
    correction=primitive(0,cut)-primitive(1,cut)
    def psi(r):
        index=(np.asarray(r)>=cut).astype(int)
        return reference_psi+primitive(index,r)+np.where(index,correction,0.)-primitive(0,a)
    def h(r):
        index=(np.asarray(r)>=cut).astype(int);return constants[index]-currents[index]*r
    case=OffAxisMagnetostaticCase(p,dict(inside=currents[0],outside=currents[1]),_boundaries(mesh,psi,h,'tangential'),order,name='synthetic-layered-annular-current')
    def fields(points):
        r,z=np.asarray(points).T;owners=(r>=cut).astype(int);potential=psi(r);intensity=np.column_stack((np.zeros(len(r)),h(r)))
        return potential,potential/r,mu[owners,None]*intensity,intensity
    energy={}
    for i,(lo,hi) in enumerate(((a,cut),(cut,b))):
        c,j=constants[i],currents[i]
        energy[regions[i].id]=np.pi*mu[i]*length*(c*c*(hi*hi-lo*lo)/2-2*c*j*(hi**3-lo**3)/3+j*j*(hi**4-lo**4)/4)
    flux=TAU*(psi(b)-psi(a));intensity_scale=max(abs(h(a)),abs(h(cut)));field_scale=max(mu)*intensity_scale
    return case,dict(fields=fields,energy_j=sum(energy.values()),region_energy_j=energy,
        source_current_a=length*(currents[0]*(cut-a)+currents[1]*(b-cut)),fixed_reaction_a=dict(inner=-TAU*length*h(a)),
        boundary_flux_wb=dict(inner=0.,outer=0.,bottom=-flux,top=flux),field_scale=field_scale,intensity_scale=intensity_scale,
        potential_scale=field_scale*b*b,cut=cut)
