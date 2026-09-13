# SPDX-License-Identifier: Apache-2.0
"""Synthetic symmetric finite currents in a uniform imposed field, actual FEM only."""
import numpy as np
from superfish_ng.planar_mesh import PlanarMesh
from superfish_ng.magnetic_materials import LinearMagneticMaterial,MagneticRegion,PlanarMagneticPartition
from superfish_ng.magnetostatic_boundary import MagnetostaticBoundary
from superfish_ng.planar_magnetostatic import PlanarMagnetostaticCase


def current_body(n=8,order=2,pair=False,scale=1.,current_a=10.,external_b_t=.25,rotation_rad=0.,offset=.125,weight_outer=.95):
    if n%8:raise ValueError('symmetric reference requires n divisible by eight')
    length=.125*scale;axis=np.linspace(0.,length,n+1);points=np.array([[x,y] for y in axis for x in axis]);triangles=[];labels=[];centers=[]
    for j in range(n):
        for i in range(n):
            a=j*(n+1)+i;b=a+1;c=a+n+1;d=c+1;point=np.array([(i+.5)*length/n,(j+.5)*length/n]);center=len(points)+len(centers);centers.append(point)
            active=3*length/8<point[1]<5*length/8
            if pair:label=1 if active and length/8<point[0]<3*length/8 else 2 if active and 5*length/8<point[0]<7*length/8 else 0
            else:label=1 if active and 3*length/8<point[0]<5*length/8 else 0
            triangles.extend(((a,b,center),(b,d,center),(d,c,center),(c,a,center)));labels.extend([label]*4)
    local=np.vstack((points,centers));labels=np.array(labels);q=np.array([[np.cos(rotation_rad),-np.sin(rotation_rad)],[np.sin(rotation_rad),np.cos(rotation_rad)]]);shift=np.array([.25,-.125])*scale;polygon=np.array([[0.,0.],[length,0.],[length,length],[0.,length]])@q.T+shift
    mesh=PlanarMesh.create(polygon,local@q.T+shift,triangles);regions=[MagneticRegion('air' if i==0 else f'body-{i}','vacuum',np.flatnonzero(labels==i).tolist()) for i in range(3 if pair else 2)];partition=PlanarMagneticPartition(mesh,[LinearMagneticMaterial('vacuum',1.)],regions)
    area=(length/4)**2;currents={region.id:0. if i==0 else current_a/area*(-1 if pair and i==1 else 1) for i,region in enumerate(regions)};groups={name:[] for name in ('bottom','top','left','right')}
    for index,edge in enumerate(mesh.boundary_edges):
        x,y=local[edge].mean(axis=0);groups['bottom' if y==0. else 'top' if y==length else 'left' if x==0. else 'right'].append(index)
    boundaries=[MagnetostaticBoundary('bottom','fixed_az',groups['bottom'],offset),MagnetostaticBoundary('top','fixed_az',groups['top'],offset+external_b_t*length)]+[MagnetostaticBoundary(name,'tangential_h',groups[name],0.) for name in ('left','right')]
    case=PlanarMagnetostaticCase(partition,currents,boundaries,order,name='synthetic-symmetric-current-body-and-uniform-field')
    inner=.75 if pair else .25;rho=np.max(abs(local-length/2)/(length/2),axis=1);weights=np.clip((weight_outer-rho)/(weight_outer-inner),0.,1.);weights[rho<=inner]=1.;weights[rho>=weight_outer]=0.
    center=np.array([length/2,length/2])@q.T+shift;force=np.zeros(2) if pair else current_a*external_b_t*np.array([0.,1.])@q.T;torque=current_a*external_b_t*length/2 if pair else 0.
    return case,tuple(r.id for r in regions[1:]),weights,center,dict(force_xy_n_per_m=force,torque_z_nm_per_m=torque,force_scale=abs(current_a*external_b_t),torque_scale=abs(current_a*external_b_t*length),length_m=length,body_center_xy_m=center,interpretation='synthetic symmetric finite current regions; self-force/torque cancel by symmetry; external uniform field supplies Lorentz force/couple')
