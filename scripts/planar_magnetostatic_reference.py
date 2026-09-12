# SPDX-License-Identifier: Apache-2.0
"""Synthetic layered magnetic gaps and current-source problems with exact fields."""
import numpy as np
from scripts.planar_electrostatic_reference import rectangle
from superfish_ng.constants import MU0
from superfish_ng.magnetic_materials import PlanarMagneticPartition,LinearMagneticMaterial,MagneticRegion
from superfish_ng.magnetostatic_boundary import MagnetostaticBoundary
from superfish_ng.planar_magnetostatic import PlanarMagnetostaticCase


def layered_gap(order=2,n=4,scale=1.,az_difference=.0025,offset=-.0002,mu_scale=1.,rotation=None,shift=(0.,0.)):
    mesh,local,width,height,rotation,shift=rectangle(n,scale,rotation=rotation,shift=shift);labels=local[mesh.triangles][:,:,1].mean(axis=1)>=height/2
    materials=[LinearMagneticMaterial('lower',2*mu_scale),LinearMagneticMaterial('upper',5*mu_scale)]
    p=PlanarMagneticPartition(mesh,materials,[MagneticRegion('bottom','lower',np.flatnonzero(~labels).tolist()),MagneticRegion('top','upper',np.flatnonzero(labels).tolist())]);groups=dict(lower=[],upper=[],left=[],right=[])
    for i,edge in enumerate(mesh.boundary_edges):
        x,y=local[edge].mean(axis=0);groups['lower' if y==0 else 'upper' if y==height else 'left' if x==0 else 'right'].append(i)
    boundaries=[MagnetostaticBoundary('lower','fixed_az',groups['lower'],offset),MagnetostaticBoundary('upper','fixed_az',groups['upper'],offset+az_difference),
        MagnetostaticBoundary('left','tangential_h',groups['left'],0.),MagnetostaticBoundary('right','tangential_h',groups['right'],0.)]
    case=PlanarMagnetostaticCase(p,dict(bottom=0.,top=0.),boundaries,order);denominator=height/2*(materials[0].mu_r+materials[1].mu_r);h=az_difference/(MU0*denominator)
    def fields(points):
        x,y=((np.asarray(points)-shift)@rotation).T;mu=np.where(y<height/2,materials[0].mu_r,materials[1].mu_r)
        az=offset+az_difference*(np.minimum(y,height/2)*materials[0].mu_r+np.maximum(y-height/2,0.)*materials[1].mu_r)/denominator
        magnetic=np.column_stack((az_difference*mu/denominator,np.zeros(len(x))))@rotation.T
        return az,magnetic,magnetic/(MU0*mu[:,None])
    return case,dict(fields=fields,energy_j_per_m=.5*width*az_difference**2/(MU0*denominator),
        region_energy_j_per_m={name:.5*MU0*m.mu_r*h*h*width*height/2 for name,m in zip(('bottom','top'),materials)},
        fixed_reaction_current_a=dict(lower=-width*h,upper=width*h),source_current_a=0.,
        boundary_normal_flux_wb_per_m=dict(lower=0.,upper=0.,left=-az_difference,right=az_difference))


def manufactured_quadratic(order=2,n=4,scale=1.,concave=False,direction='x',amplitude=1.,offset=.0003,mu_r=4.,rotation=None,shift=(0.,0.)):
    mesh,local,width,height,rotation,shift=rectangle(n,scale,concave,rotation,shift);coordinate=0 if direction=='x' else 1;nu=1/(MU0*mu_r)
    p=PlanarMagneticPartition(mesh,[LinearMagneticMaterial('magnetic',mu_r)],[MagneticRegion('all','magnetic',list(range(len(mesh.triangles))))]);fixed=[];groups={}
    for i,edge in enumerate(mesh.boundary_edges):
        a,b=local[edge];point=(a+b)/2;delta=b-a;normal=np.array([delta[1],-delta[0]])/np.linalg.norm(delta)
        if point[coordinate]==0:fixed.append(i)
        else:
            value=float(-2*nu*amplitude*point[coordinate]*normal[coordinate]);groups.setdefault(value,[]).append(i)
    boundaries=[MagnetostaticBoundary('fixed','fixed_az',fixed,offset)]+[MagnetostaticBoundary(f'tangent-{i}','tangential_h',edges,value) for i,(value,edges) in enumerate(groups.items())]
    density=-2*nu*amplitude;case=PlanarMagnetostaticCase(p,dict(all=density),boundaries,order)
    def fields(points):
        values=(np.asarray(points)-shift)@rotation;x=values[:,coordinate];gradient=np.zeros_like(values);gradient[:,coordinate]=2*amplitude*x;gradient=gradient@rotation.T
        magnetic=np.column_stack((gradient[:,1],-gradient[:,0]));return offset+amplitude*x*x,magnetic,nu*magnetic
    area=width*height;moment=(width**3*height if coordinate==0 else width*height**3)/3
    if concave:
        area-=width*height/4;moment-=((width**3-(width/2)**3)*height/2 if coordinate==0 else width/2*(height**3-(height/2)**3))/3
    return case,dict(fields=fields,energy_j_per_m=2*nu*amplitude**2*moment,source_current_a=density*area,fixed_reaction_current_a=dict(fixed=0.))


def rectangular_current(order=2,n=8,scale=1.,mu_r=3.,source_curvature=1.,offset=0.):
    mesh,local,width,height,rotation,shift=rectangle(n,scale);nu=1/(MU0*mu_r)
    p=PlanarMagneticPartition(mesh,[LinearMagneticMaterial('magnetic',mu_r)],[MagneticRegion('all','magnetic',list(range(len(mesh.triangles))))]);case=PlanarMagnetostaticCase(p,dict(all=nu*source_curvature),[MagnetostaticBoundary('fixed','fixed_az',list(range(len(mesh.boundary_edges))),offset)],order)
    def fields(points,terms=4096):
        points=np.asarray(points);az=np.empty(len(points));magnetic=np.empty_like(points,dtype=float);odd=np.arange(1,2*terms,2,dtype=float);wave=odd*np.pi/height;denominator=1+np.exp(-wave*width);coefficient=4*source_curvature*height**2/np.pi**3
        for start in range(0,len(points),128):
            x,y=points[start:start+128].T;left=np.exp(-x[:,None]*wave);right=np.exp(-(width-x[:,None])*wave);h=(left+right)/denominator;dh=(right-left)*wave/denominator;sine=np.sin(y[:,None]*wave);cosine=np.cos(y[:,None]*wave)
            az[start:start+len(x)]=offset+source_curvature*y*(height-y)/2-coefficient*((sine*h)/odd**3).sum(axis=1)
            magnetic[start:start+len(x),0]=source_curvature*(height-2*y)/2-coefficient*((cosine*h*wave)/odd**3).sum(axis=1)
            magnetic[start:start+len(x),1]=coefficient*((sine*dh)/odd**3).sum(axis=1)
        return az,magnetic,nu*magnetic
    odd=np.arange(1,32768,2,dtype=float);az_integral=source_curvature*(width*height**3/12-16*height**4/np.pi**5*np.sum(np.tanh(odd*np.pi*width/(2*height))/odd**5));current=nu*source_curvature*width*height
    return case,dict(fields=fields,energy_j_per_m=.5*nu*source_curvature*az_integral,source_current_a=current,fixed_reaction_current_a=dict(fixed=-current),
        reference='separated scalar Az Poisson series; magnetic curl gives original B, reluctivity gives H; independently check truncation')
