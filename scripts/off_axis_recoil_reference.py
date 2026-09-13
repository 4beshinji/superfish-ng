# SPDX-License-Identifier: Apache-2.0
"""Synthetic positive-radius recoil fields from curl and constitutive integration."""
import math
import numpy as np
from superfish_ng.constants import MU0,TAU
from superfish_ng.recoil_materials import LinearRecoilMaterial,OrientedMagneticRegion
from superfish_ng.off_axis_recoil_materials import OffAxisRecoilPartition
from superfish_ng.off_axis_magnetostatic_boundary import OffAxisMagnetostaticBoundary
from superfish_ng.off_axis_recoil import OffAxisRecoilCase
from scripts.off_axis_magnetostatic_reference import _mesh
from scripts.axis_recoil_reference import _moments,_constant_potentials


def _boundaries(mesh,psi,h,boundary):
    lo=mesh.outer_rz_m[:,0].min();hi=mesh.outer_rz_m[:,0].max();groups=dict(inner=[],outer=[]);other={}
    for i,edge in enumerate(mesh.boundary_edges):
        v,w=mesh.points_rz_m[edge];r,z=(v+w)/2
        if r==lo:groups['inner'].append(i)
        elif r==hi:groups['outer'].append(i)
        else:
            tangent=(w-v)/np.linalg.norm(w-v);value=float(np.asarray(h(r))@tangent);other.setdefault((value,tuple(tangent)),[]).append(i)
    assert boundary in ('fixed','tangential')
    result=[OffAxisMagnetostaticBoundary('inner','fixed_psi',groups['inner'],float(psi(lo)))]
    result.append(OffAxisMagnetostaticBoundary('outer','fixed_psi',groups['outer'],float(psi(hi))) if boundary=='fixed' else OffAxisMagnetostaticBoundary('outer','tangential_h',groups['outer'],float(h(hi)[1])))
    result.extend(OffAxisMagnetostaticBoundary(f'natural-{i}','tangential_h',edges,value) for i,((value,_),edges) in enumerate(other.items()))
    return result


def _fluxes(case,fields):
    mesh=case.partition.mesh;flux={b.id:0. for b in case.boundaries};reaction={b.id:0. for b in case.boundaries if b.kind=='fixed_psi'}
    nodes,weights=np.polynomial.legendre.leggauss(4);t=(nodes+1)/2;weights=weights/2
    for boundary in case.boundaries:
        for edge_index in boundary.edge_indices:
            v,w=mesh.points_rz_m[mesh.boundary_edges[edge_index]];delta=w-v;length=np.linalg.norm(delta);tangent=delta/length;normal=np.array([tangent[1],-tangent[0]])
            points=v[None,:]+t[:,None]*delta;_,_,b,h=fields(points)
            flux[boundary.id]+=float((TAU*points[:,0]*length*weights)@(b@normal))
            if boundary.kind=='fixed_psi':reaction[boundary.id]+=float((TAU*length*weights)@(h@tangent))
    return flux,reaction


def _reference(case,fields,potentials,field_scale,intensity_scale,source=0.,**extra):
    flux,reaction=_fluxes(case,fields);radius=case.partition.mesh.outer_rz_m[:,0].max()
    return case,dict(fields=fields,potentials=potentials,source_current_a=source,fixed_reaction_a=reaction,boundary_flux_wb=flux,
        field_scale=float(field_scale),intensity_scale=float(intensity_scale),potential_scale=float(field_scale*radius**2),**extra)


def uniform_remanence(order=2,n=2,scale=1.,mu_scale=1.,amplitude=1.,boundary='tangential',shift=0.,holes=0,reference_psi=0.):
    mesh=_mesh(n,scale,shift,holes);a=mesh.outer_rz_m[:,0].min();bz=.1*amplitude;principal=np.array([2.,5.])*mu_scale
    p=OffAxisRecoilPartition(mesh,[LinearRecoilMaterial('m',tuple(principal),(0.,bz))],[OrientedMagneticRegion('all','m',list(range(len(mesh.triangles))),0.)])
    psi=lambda r:reference_psi+bz*(np.asarray(r)**2-a*a)/2
    case=OffAxisRecoilCase(p,dict(all=0.),_boundaries(mesh,psi,lambda r:[0.,0.],boundary),order,name='off-axis-uniform-remanence')
    def fields(points):
        r,z=np.asarray(points).T;potential=psi(r);b=np.column_stack((0*r,0*r+bz));return potential,potential/r,b,np.zeros_like(b)
    nu=[np.diag(1/(MU0*principal))];b=np.array([[0.,bz]]);potentials=_constant_potentials(b,nu,b,[_moments(mesh,0)])
    return _reference(case,fields,potentials,abs(bz),abs(bz)/(MU0*principal[1]))


def interface_patch(order=2,n=2,scale=1.,mu_scale=1.,amplitude=1.,boundary='tangential',shift=0.,holes=1,reference_psi=0.):
    mesh=_mesh(n,scale,shift,holes);vertices=mesh.points_rz_m[mesh.triangles];labels=np.arange(len(vertices))%3;a=mesh.outer_rz_m[:,0].min()
    b=np.array([0.,.1*amplitude]);h=np.array([3000.,20000.])*amplitude/mu_scale;principals=[(2.,5.),(3.,11.),(7.,4.)];angles=[.2,.3,-.6]
    materials=[];regions=[];nus=[];remanent=[]
    for i,(principal,angle) in enumerate(zip(principals,angles)):
        cs,sn=math.cos(angle),math.sin(angle);q=np.array([[cs,-sn],[sn,cs]]);values=np.array(principal)*mu_scale;mu=MU0*q@np.diag(values)@q.T;br=b-mu@h
        materials.append(LinearRecoilMaterial(f'm{i}',tuple(values),tuple(q.T@br)));regions.append(OrientedMagneticRegion(f'r{i}',f'm{i}',np.flatnonzero(labels==i).tolist(),angle));nus.append(np.linalg.inv(mu));remanent.append(br)
    p=OffAxisRecoilPartition(mesh,materials,regions);psi=lambda r:reference_psi+b[1]*(np.asarray(r)**2-a*a)/2
    case=OffAxisRecoilCase(p,{r.id:0. for r in regions},_boundaries(mesh,psi,lambda r:h,boundary),order,name='off-axis-oriented-interface-patch')
    def fields(points):
        r,z=np.asarray(points).T;potential=psi(r);return potential,potential/r,np.tile(b,(len(r),1)),np.tile(h,(len(r),1))
    delta=vertices[:,1:]-vertices[:,0,None,:];area=.5*(delta[:,0,0]*delta[:,1,1]-delta[:,0,1]*delta[:,1,0]);volumes=TAU*area*vertices[:,:,0].mean(axis=1)
    potentials=_constant_potentials([b]*3,nus,remanent,np.bincount(labels,weights=volumes,minlength=3))
    return _reference(case,fields,potentials,np.linalg.norm(b),np.linalg.norm(h))


def blocked_flux(order=2,n=2,scale=1.,mu_scale=1.,amplitude=1.,boundary='tangential',shift=0.,holes=0,reference_psi=0.):
    mesh=_mesh(n,scale,shift,holes);angle=.3;cs,sn=math.cos(angle),math.sin(angle);q=np.array([[cs,-sn],[sn,cs]]);principal=np.array([2.,5.])*mu_scale
    local=np.array([.05,.1])*amplitude;br=q@local;nu=np.linalg.inv(MU0*q@np.diag(principal)@q.T);h=-nu@br
    p=OffAxisRecoilPartition(mesh,[LinearRecoilMaterial('m',tuple(principal),tuple(local))],[OrientedMagneticRegion('all','m',list(range(len(mesh.triangles))),angle)])
    case=OffAxisRecoilCase(p,dict(all=0.),_boundaries(mesh,lambda r:reference_psi,lambda r:h,boundary),order,name='off-axis-zero-B-nonzero-H')
    def fields(points):
        r,z=np.asarray(points).T;potential=np.full(len(r),reference_psi);return potential,potential/r,np.zeros((len(r),2)),np.tile(h,(len(r),1))
    potentials=_constant_potentials([np.zeros(2)],[nu],[br],[_moments(mesh,0)])
    return _reference(case,fields,potentials,np.linalg.norm(br),np.linalg.norm(h))


def annular_current(order=2,n=2,scale=1.,mu_scale=1.,amplitude=1.,boundary='tangential',shift=0.,holes=0,reference_psi=0.):
    mesh=_mesh(n,scale,shift,holes);a=mesh.outer_rz_m[:,0].min();radius=mesh.outer_rz_m[:,0].max();mu_z=MU0*5*mu_scale
    j=2e5*amplitude/(scale*mu_scale);outer_h=5000*amplitude/mu_scale;c=outer_h+j*radius;br=.1*amplitude;constant_b=mu_z*c+br;slope=-mu_z*j
    p=OffAxisRecoilPartition(mesh,[LinearRecoilMaterial('m',(2*mu_scale,5*mu_scale),(0.,br))],[OrientedMagneticRegion('all','m',list(range(len(mesh.triangles))),0.)])
    primitive=lambda r:constant_b*np.asarray(r)**2/2+slope*np.asarray(r)**3/3
    psi=lambda r:reference_psi+primitive(r)-primitive(a)
    case=OffAxisRecoilCase(p,dict(all=j),_boundaries(mesh,psi,lambda r:[0.,c-j*r],boundary),order,name='off-axis-recoil-annular-current')
    def fields(points):
        r,z=np.asarray(points).T;potential=psi(r);b=np.column_stack((0*r,constant_b+slope*r));h=np.column_stack((0*r,c-j*r));return potential,potential/r,b,h
    m0,m1,m2=(_moments(mesh,i) for i in range(3));u=(constant_b**2*m0+2*constant_b*slope*m1+slope**2*m2)/(2*mu_z)
    coupling=br*(constant_b*m0+slope*m1)/mu_z;constant=br*br*m0/(2*mu_z);ws=.5*mu_z*(c*c*m0-2*c*j*m1+j*j*m2)
    potentials=dict(b_quadratic_j=u,remanence_coupling_j=coupling,constitutive_potential_b0_j=u-coupling,constitutive_potential_h0_j=ws,remanent_reference_constant_j=constant)
    area=sum(sign*np.ptp(polygon[:,0])*np.ptp(polygon[:,1]) for polygon,sign in [(mesh.outer_rz_m,1),*((h,-1) for h in mesh.holes_rz_m)])
    return _reference(case,fields,potentials,max(abs(constant_b+slope*a),abs(constant_b+slope*radius)),max(abs(c-j*a),abs(outer_h)),j*area)


def layered_remanence(order=2,n=2,scale=1.,mu_scale=1.,amplitude=1.,boundary='tangential',shift=0.,holes=0,reference_psi=0.):
    assert holes==0;mesh=_mesh(n,scale,shift,0);a=mesh.outer_rz_m[:,0].min();radius=mesh.outer_rz_m[:,0].max();cut=(a+radius)/2;length=np.ptp(mesh.outer_rz_m[:,1]);labels=(mesh.points_rz_m[mesh.triangles][:,:,0].mean(axis=1)>=cut).astype(int)
    principal=np.array([[2.,5.],[3.,11.]])*mu_scale;br=np.array([.1,-.04])*amplitude;hz=20000*amplitude/mu_scale;mu_z=MU0*principal[:,1];bz=mu_z*hz+br
    p=OffAxisRecoilPartition(mesh,[LinearRecoilMaterial(f'm{i}',tuple(principal[i]),(0.,br[i])) for i in range(2)],
        [OrientedMagneticRegion(f'r{i}',f'm{i}',np.flatnonzero(labels==i).tolist(),0.) for i in range(2)])
    def psi(r):
        r=np.asarray(r);outside=r>=cut;return reference_psi+(bz[0]*(np.minimum(r,cut)**2-a*a)+np.where(outside,bz[1]*(r*r-cut*cut),0.))/2
    case=OffAxisRecoilCase(p,dict(r0=0.,r1=0.),_boundaries(mesh,psi,lambda r:[0.,hz],boundary),order,name='off-axis-layered-remanence')
    def fields(points):
        r,z=np.asarray(points).T;owners=(r>=cut).astype(int);potential=psi(r);return potential,potential/r,np.column_stack((0*r,bz[owners])),np.column_stack((0*r,0*r+hz))
    volumes=np.pi*length*np.array([cut*cut-a*a,radius*radius-cut*cut]);nus=[np.diag(1/(MU0*row)) for row in principal]
    potentials=_constant_potentials([np.array([0.,v]) for v in bz],nus,[np.array([0.,v]) for v in br],volumes)
    return _reference(case,fields,potentials,max(abs(bz)),abs(hz),cut=cut)
