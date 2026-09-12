# SPDX-License-Identifier: Apache-2.0
"""Synthetic planar recoil patches and polynomial source references."""
import numpy as np
from scripts.planar_electrostatic_reference import rectangle
from superfish_ng.constants import MU0
from superfish_ng.recoil_materials import LinearRecoilMaterial,OrientedMagneticRegion,PlanarRecoilPartition
from superfish_ng.magnetostatic_boundary import MagnetostaticBoundary
from superfish_ng.planar_recoil import PlanarRecoilCase


def rotation(angle):
    c,s=np.cos(angle),np.sin(angle);return np.array([[c,-s],[s,c]])


def tensor(principal,angle):return rotation(angle)@np.diag(MU0*np.asarray(principal))@rotation(angle).T


def _case(mesh,local,labels,material_data,angle,offset,current,field,order,name):
    materials=[LinearRecoilMaterial(f'm{i}',principal,remanent) for i,(principal,remanent,_) in enumerate(material_data)]
    regions=[OrientedMagneticRegion(f'region-{i}',f'm{i}',np.flatnonzero(labels==i).tolist(),orientation+angle) for i,(_,_,orientation) in enumerate(material_data)]
    partition=PlanarRecoilPartition(mesh,materials,regions);fixed=[];groups={};edge_flux={};edge_h={}
    for index,edge in enumerate(mesh.boundary_edges):
        v,w=local[edge];point=(v+w)/2;delta=w-v;length=np.linalg.norm(delta);normal=np.array([delta[1],-delta[0]])/length
        _,b,h=field(np.array([point]),np.array([labels[mesh.boundary_cells[index]]]))
        ht=float(h[0]@delta/length);edge_h[index]=ht*length;edge_flux[index]=float(b[0]@normal)*length
        if point[1]==0.:fixed.append(index)
        else:groups.setdefault(ht,[]).append(index)
    boundaries=[MagnetostaticBoundary('fixed','fixed_az',fixed,offset)]+[MagnetostaticBoundary(f'h-{i}','tangential_h',edges,value) for i,(value,edges) in enumerate(groups.items())]
    case=PlanarRecoilCase(partition,{v.id:float(current[i]) for i,v in enumerate(regions)},boundaries,order,name=name)
    flux={v.id:sum(edge_flux[i] for i in v.edge_indices) for v in boundaries}
    return case,flux,dict(fixed=-sum(edge_h[i] for i in fixed))


def _potentials(b,h,nu,br,areas):
    u=.5*np.einsum('ti,tij,tj->t',b,nu,b);coupling=np.einsum('ti,tij,tj->t',b,nu,br)
    constant=.5*np.einsum('ti,tij,tj->t',br,nu,br);delta=b-br;ws=.5*np.einsum('ti,tij,tj->t',delta,nu,delta)
    return dict(b_quadratic_j_per_m=float(areas@u),remanence_coupling_j_per_m=float(areas@coupling),
        constitutive_potential_b0_j_per_m=float(areas@(u-coupling)),constitutive_potential_h0_j_per_m=float(areas@ws),
        remanent_reference_constant_j_per_m=float(areas@constant))


def uniform_remanence(order=2,n=2,scale=1.,angle=0.,amplitude=.1,mu_scale=1.,offset=.002,shift=(0.,0.)):
    q=rotation(angle);mesh,local,width,height,_,_=rectangle(n,scale,rotation=q,shift=shift)
    principal=(2*mu_scale,5*mu_scale);br=np.array([amplitude,0.]);nu=np.diag(1/(MU0*np.asarray(principal)))
    def local_fields(points,owners=None):
        return offset+amplitude*points[:,1],np.tile(br,(len(points),1)),np.zeros((len(points),2))
    case,flux,reaction=_case(mesh,local,np.zeros(len(mesh.triangles),dtype=int),[(principal,tuple(br),0.)],angle,offset,[0.],local_fields,order,'uniform-remanent-zero-H')
    def fields(points):
        az,b,h=local_fields((np.asarray(points)-shift)@q);return az,b@q.T,h@q.T
    potentials=_potentials(br[None,:],np.zeros((1,2)),nu[None,:,:],br[None,:],np.array([width*height]))
    return case,dict(fields=fields,potentials=potentials,source_current_a=0.,fixed_reaction_current_a=reaction,boundary_normal_flux_wb_per_m=flux,
        potential_scale=abs(amplitude)*height,field_scale=abs(amplitude),intensity_scale=abs(amplitude)/(MU0*min(principal)),width=width,height=height)


def interface_patch(order=2,n=2,scale=1.,angle=0.,amplitude=1.,mu_scale=1.,offset=.002,shift=(0.,0.)):
    q=rotation(angle);mesh,local,width,height,_,_=rectangle(n,scale,rotation=q,shift=shift)
    labels=(local[mesh.triangles][:,:,0].mean(axis=1)>=width/2).astype(int)
    b=np.array([.08,0.])*amplitude;h=np.array([200.,-100.])*amplitude
    principal=np.array([[2.,5.],[3.,11.]])*mu_scale;angles=(.2,-.4);data=[];nus=[];brs=[]
    for i in range(2):
        mu=tensor(principal[i],angles[i]);br=b-mu@h;br_local=rotation(angles[i]).T@br
        data.append((tuple(principal[i]),tuple(br_local),angles[i]));nus.append(np.linalg.inv(mu));brs.append(br)
    def local_fields(points,owners=None):return offset+b[0]*points[:,1],np.tile(b,(len(points),1)),np.tile(h,(len(points),1))
    case,flux,reaction=_case(mesh,local,labels,data,angle,offset,[0.,0.],local_fields,order,'nonzero-normal-B-and-tangential-H-interface')
    def fields(points):
        az,b,h=local_fields((np.asarray(points)-shift)@q);return az,b@q.T,h@q.T
    potentials=_potentials(np.tile(b,(2,1)),np.tile(h,(2,1)),np.array(nus),np.array(brs),np.full(2,width*height/2))
    return case,dict(fields=fields,potentials=potentials,source_current_a=0.,fixed_reaction_current_a=reaction,boundary_normal_flux_wb_per_m=flux,
        potential_scale=np.linalg.norm(b)*height,field_scale=np.linalg.norm(b),intensity_scale=max(np.linalg.norm(h),np.linalg.norm(brs)/(MU0*min(principal.ravel()))),
        width=width,height=height,interface_local_normal=[1.,0.],interface_local_tangent=[0.,1.])


def layered_remanence(order=2,n=2,scale=1.,angle=0.,amplitude=1.,mu_scale=1.,offset=.002,shift=(0.,0.)):
    q=rotation(angle);mesh,local,width,height,_,_=rectangle(n,scale,rotation=q,shift=shift);cut=height/2
    labels=(local[mesh.triangles][:,:,1].mean(axis=1)>=cut).astype(int);principal=np.array([[2.,5.],[3.,11.]])*mu_scale
    angles=(.2,-.4);locals=np.array([[.1,.025],[-.04,.03]])*amplitude;hx=300.*amplitude/mu_scale
    nus=[];brs=[];bs=[];hs=[];data=[]
    for i in range(2):
        nu=np.linalg.inv(tensor(principal[i],angles[i]));br=rotation(angles[i])@locals[i]
        bx=br[0]+(hx+nu[0,1]*br[1])/nu[0,0];b=np.array([bx,0.]);h=nu@(b-br)
        nus.append(nu);brs.append(br);bs.append(b);hs.append(h);data.append((tuple(principal[i]),tuple(locals[i]),angles[i]))
    bs=np.array(bs);hs=np.array(hs)
    def local_fields(points,owners=None):
        y=points[:,1];indices=(y>=cut).astype(int) if owners is None else owners
        az=offset+bs[0,0]*np.minimum(y,cut)+bs[1,0]*np.maximum(y-cut,0.)
        return az,bs[indices],hs[indices]
    case,flux,reaction=_case(mesh,local,labels,data,angle,offset,[0.,0.],local_fields,order,'layered-remanence-continuous-Ht')
    def fields(points):
        az,b,h=local_fields((np.asarray(points)-shift)@q);return az,b@q.T,h@q.T
    potentials=_potentials(bs,hs,np.array(nus),np.array(brs),np.full(2,width*height/2))
    return case,dict(fields=fields,potentials=potentials,source_current_a=0.,fixed_reaction_current_a=reaction,boundary_normal_flux_wb_per_m=flux,
        potential_scale=np.max(np.linalg.norm(bs,axis=1))*height,field_scale=np.max(np.linalg.norm(bs,axis=1)),
        intensity_scale=max(np.max(np.linalg.norm(hs,axis=1)),np.linalg.norm(brs)/(MU0*min(principal.ravel()))),width=width,height=height,cut=cut)


def quadratic_current(order=2,n=4,scale=1.,angle=0.,amplitude=1.,mu_scale=1.,offset=.002,shift=(0.,0.),concave=False):
    q=rotation(angle);mesh,local,width,height,_,_=rectangle(n,scale,concave,rotation=q,shift=shift)
    principal=np.array([2.,7.])*mu_scale;nu=np.diag(1/(MU0*principal));br=np.array([.02,.03])*amplitude;alpha=1.5*amplitude
    def local_fields(points,owners=None):
        y=points[:,1];b=np.column_stack((2*alpha*y,np.zeros(len(y))))
        return offset+alpha*y*y,b,(b-br)@nu.T
    density=-2*alpha*nu[0,0]
    case,flux,reaction=_case(mesh,local,np.zeros(len(mesh.triangles),dtype=int),[(tuple(principal),tuple(br),0.)],angle,offset,[density],local_fields,order,'quadratic-recoil-current')
    def fields(points):
        az,b,h=local_fields((np.asarray(points)-shift)@q);return az,b@q.T,h@q.T
    area=width*height;first=width*height**2/2;second=width*height**3/3
    if concave:
        area-=width*height/4;first-=width/2*(height**2-(height/2)**2)/2;second-=width/2*(height**3-(height/2)**3)/3
    u=2*alpha**2*nu[0,0]*second;coupling=2*alpha*nu[0,0]*br[0]*first;constant=.5*float(br@nu@br)*area
    potentials=dict(b_quadratic_j_per_m=u,remanence_coupling_j_per_m=coupling,constitutive_potential_b0_j_per_m=u-coupling,
        constitutive_potential_h0_j_per_m=u-coupling+constant,remanent_reference_constant_j_per_m=constant)
    return case,dict(fields=fields,potentials=potentials,source_current_a=density*area,fixed_reaction_current_a=reaction,boundary_normal_flux_wb_per_m=flux,
        potential_scale=abs(alpha)*height**2,field_scale=max(2*abs(alpha)*height,np.linalg.norm(br)),intensity_scale=max(2*abs(alpha)*height,np.linalg.norm(br))/(MU0*min(principal)),width=width,height=height)
