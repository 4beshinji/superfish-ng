# SPDX-License-Identifier: Apache-2.0
"""Synthetic triangle with an exact quadratic Az and a source-free quadrupole."""
import numpy as np
from superfish_ng.planar_polygon import PlanarMesh
from superfish_ng.magnetic_materials import PlanarMagneticPartition,LinearMagneticMaterial,MagneticRegion
from superfish_ng.magnetostatic_boundary import MagnetostaticBoundary
from superfish_ng.planar_magnetostatic import PlanarMagnetostaticCase
from superfish_ng.planar_magnetic_multipoles import PlanarMagneticMultipoleFrame
from superfish_ng.constants import MU0


def quadrupole(n=8,order=2,scale=1.,strength=1.,mu_r=2.,rotation_rad=0.,offset=.125):
    length=.125*scale;co,si=np.cos(rotation_rad),np.sin(rotation_rad);rotation=np.array([[co,-si],[si,co]]);shift=np.array([.25,-.125])*scale
    local=np.array([(length*i/n,length*j/n) for j in range(n+1) for i in range(j+1)]);indices={(i,j):j*(j+1)//2+i for j in range(n+1) for i in range(j+1)};triangles=[]
    for j in range(n):
        for i in range(j+1):
            a=indices[i,j];c=indices[i,j+1];d=indices[i+1,j+1];triangles.append((a,d,c))
            if i<j:triangles.append((a,indices[i+1,j],d))
    polygon=np.array([[0.,0.],[length,length],[0.,length]])@rotation.T+shift;points=local@rotation.T+shift;mesh=PlanarMesh.create(polygon,points,np.asarray(triangles))
    partition=PlanarMagneticPartition(mesh,[LinearMagneticMaterial('uniform',mu_r)],[MagneticRegion('domain','uniform',list(range(len(triangles))))]);groups=dict(diagonal=[],top=[],left=[])
    for i,edge in enumerate(mesh.boundary_edges):
        v,w=local[edge]
        if v[0]==v[1] and w[0]==w[1]:groups['diagonal'].append(i)
        elif v[1]==length and w[1]==length:groups['top'].append(i)
        else:assert v[0]==w[0]==0.;groups['left'].append(i)
    boundaries=[MagnetostaticBoundary('diagonal','fixed_az',groups['diagonal'],offset),MagnetostaticBoundary('top','tangential_h',groups['top'],strength/(MU0*mu_r)),MagnetostaticBoundary('left','tangential_h',groups['left'],0.)]
    case=PlanarMagnetostaticCase(partition,dict(domain=0.),boundaries,order)
    center=np.array([.25,.75])*length;frame=PlanarMagneticMultipoleFrame(tuple(center@rotation.T+shift),length/8,rotation_rad+.2)
    def fields(points):
        original=(np.asarray(points)-shift)@rotation;return np.column_stack((-strength*original[:,1]/length,-strength*original[:,0]/length))@rotation.T
    # Convert the exact affine global vector at the frame center and its
    # local gradient. This does not use production polynomial evaluation.
    at_center=fields([frame.center_xy_m])[0];angle=frame.rotation_rad;axis=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]]);local_b=at_center@axis
    first=complex(local_b[1],local_b[0]);second=-strength*frame.reference_radius_m/length*np.exp(2j*(frame.rotation_rad-rotation_rad))
    return case,frame,dict(fields=fields,coefficients_t=np.array([first,second]),length_m=length,strength_t=strength,local_points=local)


def uniform_dipole(n=4,order=1,scale=1.,strength=1.,mu_r=2.,rotation_rad=0.,offset=.125):
    from dataclasses import replace
    case,frame,ref=quadrupole(n,order,scale,strength,mu_r,rotation_rad,offset)
    boundaries=[b if b.kind=='fixed_az' else MagnetostaticBoundary(b.id,b.kind,b.edge_indices,strength/(MU0*mu_r)) for b in case.boundaries];case=replace(case,boundaries=boundaries)
    co,si=np.cos(rotation_rad),np.sin(rotation_rad);rotation=np.array([[co,-si],[si,co]]);field=np.array([-strength,-strength])@rotation.T
    def fields(points):return np.tile(field,(len(points),1))
    first=-strength*(1+1j)*np.exp(1j*(frame.rotation_rad-rotation_rad))
    return case,frame,dict(fields=fields,coefficients_t=np.array([first,0j]),length_m=ref['length_m'],strength_t=strength,local_points=ref['local_points'])
