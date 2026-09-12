# SPDX-License-Identifier: Apache-2.0
"""Synthetic planar capacitors and source problems with analytical static fields."""
import numpy as np
from superfish_ng.constants import EPS0
from superfish_ng.planar_mesh import PlanarMesh
from superfish_ng.planar_dielectrics import PlanarDielectricPartition,LinearDielectric,DielectricRegion
from superfish_ng.electrostatic_boundary import ElectrostaticBoundary
from superfish_ng.planar_electrostatic import PlanarElectrostaticCase


def rectangle(n=4,scale=1.,concave=False,rotation=None,shift=(0.,0.)):
    if n%2:raise ValueError('reference rectangle requires an even grid count')
    width=.125*scale;height=.0625*scale;rotation=np.eye(2) if rotation is None else np.asarray(rotation);shift=np.asarray(shift)
    squares=[(i,j) for j in range(n) for i in range(n) if not (concave and i>=n//2 and j>=n//2)]
    coordinates=sorted({(i+di,j+dj) for i,j in squares for di,dj in ((0,0),(1,0),(1,1),(0,1))},key=lambda p:(p[1],p[0]))
    indices={p:i for i,p in enumerate(coordinates)};local=np.array([(width*i/n,height*j/n) for i,j in coordinates]);cells=[]
    for i,j in squares:
        a,b,c,d=[indices[p] for p in ((i,j),(i+1,j),(i+1,j+1),(i,j+1))];cells.extend(((a,b,c),(a,c,d)))
    polygon=([[0.,0.],[width,0.],[width,height/2],[width/2,height/2],[width/2,height],[0.,height]] if concave else [[0.,0.],[width,0.],[width,height],[0.,height]])
    mesh=PlanarMesh.create(np.asarray(polygon)@rotation.T+shift,local@rotation.T+shift,np.asarray(cells))
    return mesh,local,width,height,rotation,shift


def parallel_plate(order=2,n=4,scale=1.,voltage=5.,offset=-2.,epsilon_scale=1.,rotation=None,shift=(0.,0.)):
    mesh,local,width,height,rotation,shift=rectangle(n,scale,rotation=rotation,shift=shift);labels=local[mesh.triangles][:,:,1].mean(axis=1)>=height/2
    materials=[LinearDielectric('lower',2*epsilon_scale),LinearDielectric('upper',5*epsilon_scale)]
    p=PlanarDielectricPartition(mesh,materials,[DielectricRegion('bottom','lower',np.flatnonzero(~labels).tolist()),DielectricRegion('top','upper',np.flatnonzero(labels).tolist())])
    low=[];high=[];sides=[]
    for i,edge in enumerate(mesh.boundary_edges):
        y=local[edge,1].mean();(low if y==0 else high if y==height else sides).append(i)
    boundaries=[ElectrostaticBoundary('lower','electrode_potential',low,offset),ElectrostaticBoundary('upper','electrode_potential',high,offset+voltage),ElectrostaticBoundary('sides','outward_displacement',sides,0.)]
    case=PlanarElectrostaticCase(p,dict(bottom=0.,top=0.),boundaries,order)
    denominator=height/2*(1/materials[0].epsilon_r+1/materials[1].epsilon_r);capacitance=EPS0*width/denominator
    def fields(points):
        x,y=((np.asarray(points)-shift)@rotation).T;epsilon=np.where(y<height/2,materials[0].epsilon_r,materials[1].epsilon_r)
        phi=offset+voltage*(np.minimum(y,height/2)/materials[0].epsilon_r+np.maximum(y-height/2,0.)/materials[1].epsilon_r)/denominator
        electric=np.column_stack((np.zeros(len(x)),-voltage/(epsilon*denominator)))@rotation.T
        return phi,electric,EPS0*epsilon[:,None]*electric
    return case,dict(fields=fields,capacitance_f_per_m=capacitance,energy_j_per_m=.5*capacitance*voltage**2,
        region_energy_j_per_m={name:.5*EPS0*width*height/2*voltage**2/(denominator**2*m.epsilon_r) for name,m in zip(('bottom','top'),materials)},
        electrode_charge_c_per_m=dict(lower=-capacitance*voltage,upper=capacitance*voltage))


def manufactured_quadratic(order=2,n=4,scale=1.,concave=False,direction='x',amplitude=100.,offset=3.,epsilon_r=4.,rotation=None,shift=(0.,0.)):
    mesh,local,width,height,rotation,shift=rectangle(n,scale,concave,rotation,shift);coordinate=0 if direction=='x' else 1
    p=PlanarDielectricPartition(mesh,[LinearDielectric('dielectric',epsilon_r)],[DielectricRegion('all','dielectric',list(range(len(mesh.triangles))))])
    electrode=[];groups={}
    # Lowest local x or y is zero: Phi=offset on that complete boundary side.
    for i,edge in enumerate(mesh.boundary_edges):
        a,b=local[edge];point=(a+b)/2;delta=b-a;normal=np.array([delta[1],-delta[0]])/np.linalg.norm(delta)
        if point[coordinate]==0:electrode.append(i)
        else:
            value=float(-2*EPS0*epsilon_r*amplitude*point[coordinate]*normal[coordinate]);groups.setdefault(value,[]).append(i)
    boundaries=[ElectrostaticBoundary('electrode','electrode_potential',electrode,offset)]
    boundaries += [ElectrostaticBoundary(f'flux-{i}','outward_displacement',edges,value) for i,(value,edges) in enumerate(groups.items())]
    rho=-2*EPS0*epsilon_r*amplitude;case=PlanarElectrostaticCase(p,dict(all=rho),boundaries,order)
    def fields(points):
        values=(np.asarray(points)-shift)@rotation;x=values[:,coordinate];electric=np.zeros_like(values);electric[:,coordinate]=-2*amplitude*x
        electric=electric@rotation.T;return offset+amplitude*x*x,electric,EPS0*epsilon_r*electric
    area=width*height;moment=(width**3*height if coordinate==0 else width*height**3)/3
    if concave:
        area-=width*height/4
        moment-=((width**3-(width/2)**3)*height/2 if coordinate==0 else width/2*(height**3-(height/2)**3))/3
    return case,dict(fields=fields,energy_j_per_m=2*EPS0*epsilon_r*amplitude**2*moment,
        volume_charge_c_per_m=rho*area,electrode_charge_c_per_m=dict(electrode=0.))


def rectangular_poisson(order=2,n=8,scale=1.,epsilon_r=3.,source_curvature=100.,offset=0.):
    mesh,local,width,height,rotation,shift=rectangle(n,scale)
    p=PlanarDielectricPartition(mesh,[LinearDielectric('dielectric',epsilon_r)],[DielectricRegion('all','dielectric',list(range(len(mesh.triangles))))])
    boundary=ElectrostaticBoundary('ground','electrode_potential',list(range(len(mesh.boundary_edges))),offset)
    rho=EPS0*epsilon_r*source_curvature;case=PlanarElectrostaticCase(p,dict(all=rho),[boundary],order)
    def fields(points,terms=1024):
        points=np.asarray(points);phi=np.empty(len(points));electric=np.empty_like(points,dtype=float)
        odd=np.arange(1,2*terms,2,dtype=float);wave=odd*np.pi/height;denominator=1+np.exp(-wave*width)
        coefficient=4*source_curvature*height**2/np.pi**3
        for start in range(0,len(points),128):
            x,y=points[start:start+128].T;left=np.exp(-x[:,None]*wave);right=np.exp(-(width-x[:,None])*wave)
            h=(left+right)/denominator;dh=(right-left)*wave/denominator;sine=np.sin(y[:,None]*wave);cosine=np.cos(y[:,None]*wave)
            phi[start:start+len(x)]=offset+source_curvature*y*(height-y)/2-coefficient*((sine*h)/odd**3).sum(axis=1)
            electric[start:start+len(x),0]=coefficient*((sine*dh)/odd**3).sum(axis=1)
            electric[start:start+len(x),1]=-source_curvature*(height-2*y)/2+coefficient*((cosine*h*wave)/odd**3).sum(axis=1)
        return phi,electric,EPS0*epsilon_r*electric
    # Integrate the separated solution exactly in x/y. This sum has an
    # n^-5 tail and is evaluated independently of the field sample count.
    odd=np.arange(1,32768,2,dtype=float)
    potential_integral=source_curvature*(width*height**3/12-16*height**4/np.pi**5*np.sum(np.tanh(odd*np.pi*width/(2*height))/odd**5))
    return case,dict(fields=fields,energy_j_per_m=.5*rho*potential_integral,volume_charge_c_per_m=rho*width*height,
        electrode_charge_c_per_m=dict(ground=-rho*width*height),reference='separated rectangle Poisson series; field truncation must be checked independently')
