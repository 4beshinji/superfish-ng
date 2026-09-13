# SPDX-License-Identifier: Apache-2.0
"""Synthetic axis recoil equilibria derived from curl and constitutive laws."""
import math
import numpy as np
from superfish_ng.constants import MU0,TAU
from superfish_ng.axis_connected_mesh import AxisConnectedMesh
from superfish_ng.recoil_materials import LinearRecoilMaterial,OrientedMagneticRegion
from superfish_ng.axis_recoil_materials import AxisRecoilPartition
from superfish_ng.axis_magnetostatic_boundary import AxisMagnetostaticBoundary
from superfish_ng.axis_recoil import AxisRecoilCase
from scripts.electrostatic_reference import rectangle
from scripts.curved_meridional_reference import fixture


def _mesh(n,scale,shift,holes=0):
    mesh=fixture(True,holes,n=n,scale=scale,shear=0.)[0]['base_mesh'] if holes else rectangle(True,2*n,4*n,scale)[0]
    t=np.array([0.,shift]);return AxisConnectedMesh(mesh.outer_rz_m+t,[h+t for h in mesh.holes_rz_m],mesh.points_rz_m+t,mesh.triangles)


def _boundaries(mesh,outer_a,hz):
    radius=mesh.outer_rz_m[:,0].max();groups={k:[] for k in ('outer','axis')};natural={}
    for i,edge in enumerate(mesh.boundary_edges):
        v,w=mesh.points_rz_m[edge];r,z=(v+w)/2
        if r==0.:groups['axis'].append(i)
        elif r==radius:groups['outer'].append(i)
        else:
            tangent=(w-v)/np.linalg.norm(w-v);value=float(tangent[1]*hz(r));natural.setdefault((value,tuple(tangent)),[]).append(i)
    boundaries=[AxisMagnetostaticBoundary('axis','axis_regularity',groups['axis'])]
    boundaries.append(AxisMagnetostaticBoundary('outer','fixed_aphi_over_r',groups['outer'],outer_a) if outer_a is not None else AxisMagnetostaticBoundary('outer','tangential_h',groups['outer'],hz(radius)))
    boundaries.extend(AxisMagnetostaticBoundary(f'natural-{i}','tangential_h',edges,value) for i,((value,_),edges) in enumerate(natural.items()))
    return boundaries


def _moments(mesh,power):
    return sum(sign*np.pi*(polygon[:,1].max()-polygon[:,1].min())*2*(polygon[:,0].max()**(power+2)-polygon[:,0].min()**(power+2))/(power+2)
        for polygon,sign in [(mesh.outer_rz_m,1),*((h,-1) for h in mesh.holes_rz_m)])


def _constant_potentials(b,nu,br,volumes):
    quadratic=.5*sum(float(x@n@x)*v for x,n,v in zip(b,nu,volumes));coupling=sum(float(x@n@y)*v for x,n,y,v in zip(b,nu,br,volumes))
    constant=.5*sum(float(y@n@y)*v for n,y,v in zip(nu,br,volumes));shifted=.5*sum(float((x-y)@n@(x-y))*v for x,n,y,v in zip(b,nu,br,volumes))
    return dict(b_quadratic_j=quadratic,remanence_coupling_j=coupling,constitutive_potential_b0_j=quadratic-coupling,constitutive_potential_h0_j=shifted,remanent_reference_constant_j=constant)


def _fluxes(case,fields):
    # Analytical B is constant or linear along each oriented boundary edge.
    mesh=case.partition.mesh;result={b.id:0. for b in case.boundaries};reaction={b.id:0. for b in case.boundaries if b.kind=='fixed_aphi_over_r'}
    nodes,weights=np.polynomial.legendre.leggauss(4);t=(nodes+1)/2;weights=weights/2
    for boundary in case.boundaries:
        for edge_index in boundary.edge_indices:
            v,w=mesh.points_rz_m[mesh.boundary_edges[edge_index]];delta=w-v;length=np.linalg.norm(delta);tangent=delta/length;normal=np.array([tangent[1],-tangent[0]])
            points=v[None,:]+t[:,None]*delta;_,_,b,h=fields(points)
            result[boundary.id]+=float((TAU*points[:,0]*length*weights)@(b@normal))
            if boundary.kind=='fixed_aphi_over_r':reaction[boundary.id]+=float((TAU*points[:,0]**2*length*weights)@(h@tangent))
    return result,reaction


def uniform_remanence(order=2,n=2,scale=1.,mu_scale=1.,amplitude=1.,boundary='tangential',shift=0.,holes=0):
    mesh=_mesh(n,scale,shift,holes);bz=.1*amplitude;principal=(2*mu_scale,5*mu_scale)
    p=AxisRecoilPartition(mesh,[LinearRecoilMaterial('m',principal,(0.,bz))],[OrientedMagneticRegion('all','m',list(range(len(mesh.triangles))),0.)])
    case=AxisRecoilCase(p,dict(all=0.),_boundaries(mesh,bz/2 if boundary=='fixed' else None,lambda r:0.),order,name='axis-uniform-remanence')
    def fields(points):
        r,z=np.asarray(points).T;a=np.full(len(r),bz/2);b=np.column_stack((0*r,0*r+bz));return a,r*a,b,np.zeros_like(b)
    nu=np.array([np.diag(1/(MU0*np.array(principal)))]);b=np.array([[0.,bz]]);potential=_constant_potentials(b,nu,b,[_moments(mesh,0)])
    flux,reaction=_fluxes(case,fields)
    return case,dict(fields=fields,potentials=potential,source_current_a=0.,fixed_reaction_a_m2=reaction,boundary_flux_wb=flux,field_scale=abs(bz),intensity_scale=abs(bz)/(MU0*principal[1]))


def interface_patch(order=2,n=2,scale=1.,mu_scale=1.,amplitude=1.,boundary='tangential',shift=0.,holes=1):
    mesh=_mesh(n,scale,shift,holes);vertices=mesh.points_rz_m[mesh.triangles]
    labels=np.where(np.any(vertices[:,:,0]==0.,axis=1),0,1+np.arange(len(vertices))%2)
    b=np.array([0.,.1*amplitude]);h=np.array([0.,20000*amplitude/mu_scale]);principals=[(2.,5.),(3.,11.),(7.,4.)];angles=[0.,.3,-.6]
    materials=[];regions=[];nus=[];remanent=[]
    for i,(principal,angle) in enumerate(zip(principals,angles)):
        c,s=math.cos(angle),math.sin(angle);q=np.array([[c,-s],[s,c]]);values=mu_scale*np.array(principal);mu=MU0*q@np.diag(values)@q.T
        br=b-mu@h;local=q.T@br
        materials.append(LinearRecoilMaterial(f'm{i}',tuple(values),tuple(local)));regions.append(OrientedMagneticRegion(f'r{i}',f'm{i}',np.flatnonzero(labels==i).tolist(),angle))
        nus.append(np.linalg.inv(mu));remanent.append(br)
    p=AxisRecoilPartition(mesh,materials,regions);case=AxisRecoilCase(p,{r.id:0. for r in regions},_boundaries(mesh,b[1]/2 if boundary=='fixed' else None,lambda r:h[1]),order,name='axis-oriented-interface-patch')
    def fields(points):
        r,z=np.asarray(points).T;a=np.full(len(r),b[1]/2);return a,r*a,np.tile(b,(len(r),1)),np.tile(h,(len(r),1))
    # Independent tetrahedral radial moment for each straight triangle.
    delta=vertices[:,1:]-vertices[:,0,None,:];area=.5*(delta[:,0,0]*delta[:,1,1]-delta[:,0,1]*delta[:,1,0]);volumes=TAU*area*vertices[:,:,0].mean(axis=1)
    regional=np.bincount(labels,weights=volumes,minlength=3);potential=_constant_potentials([b]*3,nus,remanent,regional);flux,reaction=_fluxes(case,fields)
    return case,dict(fields=fields,potentials=potential,source_current_a=0.,fixed_reaction_a_m2=reaction,boundary_flux_wb=flux,field_scale=float(np.linalg.norm(b)),intensity_scale=float(np.linalg.norm(h)))


def cylinder_current(order=2,n=2,scale=1.,mu_scale=1.,amplitude=1.,boundary='tangential',shift=0.,holes=0):
    mesh=_mesh(n,scale,shift,holes);radius=mesh.outer_rz_m[:,0].max();mu_z=MU0*5*mu_scale;mu_r=MU0*2*mu_scale
    j=2e5*amplitude/(scale*mu_scale);outer_h=5000*amplitude/mu_scale;c=outer_h+j*radius;br=.1*amplitude;constant_b=mu_z*c+br;slope=-mu_z*j
    p=AxisRecoilPartition(mesh,[LinearRecoilMaterial('m',(2*mu_scale,5*mu_scale),(0.,br))],[OrientedMagneticRegion('all','m',list(range(len(mesh.triangles))),0.)])
    outer_a=constant_b/2+slope*radius/3
    case=AxisRecoilCase(p,dict(all=j),_boundaries(mesh,outer_a if boundary=='fixed' else None,lambda r:c-j*r),order,name='axis-recoil-azimuthal-current')
    def fields(points):
        r,z=np.asarray(points).T;a=constant_b/2+slope*r/3;b=np.column_stack((0*r,constant_b+slope*r));h=np.column_stack((0*r,c-j*r));return a,r*a,b,h
    m0,m1,m2=(_moments(mesh,i) for i in range(3));u=(constant_b**2*m0+2*constant_b*slope*m1+slope**2*m2)/(2*mu_z)
    coupling=br*(constant_b*m0+slope*m1)/mu_z;constant=br*br*m0/(2*mu_z);ws=.5*mu_z*(c*c*m0-2*c*j*m1+j*j*m2)
    potentials=dict(b_quadratic_j=u,remanence_coupling_j=coupling,constitutive_potential_b0_j=u-coupling,constitutive_potential_h0_j=ws,remanent_reference_constant_j=constant)
    area=sum(sign*np.ptp(polygon[:,0])*np.ptp(polygon[:,1]) for polygon,sign in [(mesh.outer_rz_m,1),*((h,-1) for h in mesh.holes_rz_m)])
    flux,reaction=_fluxes(case,fields)
    return case,dict(fields=fields,potentials=potentials,source_current_a=j*area,fixed_reaction_a_m2=reaction,boundary_flux_wb=flux,field_scale=max(abs(constant_b),abs(constant_b+slope*radius)),intensity_scale=max(abs(c),abs(outer_h)))


def layered_remanence(order=2,n=4,scale=1.,mu_scale=1.,amplitude=1.,shift=0.):
    mesh=_mesh(n,scale,shift);radius=mesh.outer_rz_m[:,0].max();cut=radius/2;length=np.ptp(mesh.outer_rz_m[:,1]);labels=(mesh.points_rz_m[mesh.triangles][:,:,0].mean(axis=1)>=cut).astype(int)
    principal=np.array([[2.,5.],[3.,11.]])*mu_scale;br=np.array([.1,-.04])*amplitude;hz=20000*amplitude/mu_scale;mu_z=MU0*principal[:,1];bz=mu_z*hz+br
    p=AxisRecoilPartition(mesh,[LinearRecoilMaterial(f'm{i}',tuple(principal[i]),(0.,br[i])) for i in range(2)],
        [OrientedMagneticRegion(f'r{i}',f'm{i}',np.flatnonzero(labels==i).tolist(),0.) for i in range(2)])
    case=AxisRecoilCase(p,dict(r0=0.,r1=0.),_boundaries(mesh,None,lambda r:hz),order,name='axis-layered-remanence')
    correction=(bz[0]-bz[1])*cut*cut/2
    def fields(points):
        r,z=np.asarray(points).T;owners=(r>=cut).astype(int);a=bz[owners]/2;outside=owners==1;a[outside]+=correction/r[outside]**2
        return a,r*a,np.column_stack((0*r,bz[owners])),np.column_stack((0*r,0*r+hz))
    volumes=np.pi*length*np.array([cut*cut,radius*radius-cut*cut]);nus=[np.diag(1/(MU0*row)) for row in principal]
    potential=_constant_potentials([np.array([0.,v]) for v in bz],nus,[np.array([0.,v]) for v in br],volumes);flux,reaction=_fluxes(case,fields)
    return case,dict(fields=fields,potentials=potential,source_current_a=0.,fixed_reaction_a_m2=reaction,boundary_flux_wb=flux,field_scale=float(max(abs(bz))),intensity_scale=abs(hz),cut=cut)
