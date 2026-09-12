# SPDX-License-Identifier: Apache-2.0
"""Synthetic finite electrostatic fixtures and independent closed-form fields."""
import numpy as np
from superfish_ng.constants import EPS0,TAU
from superfish_ng.axis_connected_mesh import AxisConnectedMesh
from superfish_ng.meridional_mesh import MeridionalMesh
from superfish_ng.dielectrics import LinearDielectric,DielectricRegion,AxisymmetricDielectricPartition
from superfish_ng.electrostatic_boundary import ElectrostaticBoundary
from superfish_ng.electrostatic import AxisymmetricElectrostaticCase


def rectangle(axis=True,nr=4,nz=8,scale=1.):
    a=0. if axis else .03125*scale;b=.0625*scale;length=.125*scale
    points=np.array([(r,z) for z in np.linspace(0.,length,nz+1) for r in np.linspace(a,b,nr+1)])
    triangles=[]
    for j in range(nz):
        for i in range(nr):
            v=j*(nr+1)+i;w=v+nr+1;triangles.extend(((v,v+1,w+1),(v,w+1,w)))
    cls=AxisConnectedMesh if axis else MeridionalMesh
    return cls([[a,0.],[b,0.],[b,length],[a,length]],[],points,np.asarray(triangles)),a,b,length


def parallel_plate(order=2,n=2,scale=1.,voltage=5.,offset=-2.,epsilon_scale=1.):
    mesh,a,b,length=rectangle(True,2*n,4*n,scale);cut=length/2
    labels=mesh.points_rz_m[mesh.triangles][:,:,1].mean(axis=1)>=cut
    materials=(LinearDielectric('lower',2.*epsilon_scale),LinearDielectric('upper',5.*epsilon_scale))
    regions=(DielectricRegion('bottom','lower',np.flatnonzero(~labels).tolist()),DielectricRegion('top','upper',np.flatnonzero(labels).tolist()))
    p=AxisymmetricDielectricPartition(mesh,materials,regions);groups={k:[] for k in ('lower','upper','side','axis')}
    for i,edge in enumerate(mesh.boundary_edges):
        r,z=mesh.points_rz_m[edge].mean(axis=0)
        key='axis' if r==0 else 'lower' if z==0 else 'upper' if z==length else 'side';groups[key].append(i)
    boundaries=[ElectrostaticBoundary('lower','electrode_potential',groups['lower'],offset),ElectrostaticBoundary('upper','electrode_potential',groups['upper'],offset+voltage),
        ElectrostaticBoundary('side','outward_displacement',groups['side'],0.),ElectrostaticBoundary('axis','axis_symmetry',groups['axis'])]
    case=AxisymmetricElectrostaticCase(p,dict(bottom=0.,top=0.),boundaries,order)
    denominator=cut/materials[0].epsilon_r+(length-cut)/materials[1].epsilon_r
    capacitance=EPS0*np.pi*b*b/denominator
    def fields(points):
        r,z=np.asarray(points).T;eps=np.where(z<cut,materials[0].epsilon_r,materials[1].epsilon_r)
        potential=offset+voltage*(np.minimum(z,cut)/materials[0].epsilon_r+np.maximum(z-cut,0.)/materials[1].epsilon_r)/denominator
        electric_z=-voltage/(denominator*eps)
        return potential,np.column_stack((np.zeros(len(r)),electric_z)),np.column_stack((np.zeros(len(r)),np.full(len(r),-EPS0*voltage/denominator)))
    region_energy={name:.5*EPS0*np.pi*b*b*(length/2)*voltage**2/(denominator**2*m.epsilon_r) for name,m in zip(('bottom','top'),materials)}
    return case,dict(fields=fields,capacitance_f=capacitance,energy_j=.5*capacitance*voltage**2,
        region_energy_j=region_energy,electrode_charge_c=dict(lower=-capacitance*voltage,upper=capacitance*voltage),cut=cut)


def coaxial_capacitor(order=2,n=4,scale=1.,voltage=5.,offset=-2.,epsilon_r=3.):
    mesh,a,b,length=rectangle(False,n,2*n,scale)
    p=AxisymmetricDielectricPartition(mesh,[LinearDielectric('dielectric',epsilon_r)],[DielectricRegion('all','dielectric',list(range(len(mesh.triangles))))])
    groups={k:[] for k in ('inner','outer','ends')}
    for i,edge in enumerate(mesh.boundary_edges):
        r,z=mesh.points_rz_m[edge].mean(axis=0);groups['inner' if r==a else 'outer' if r==b else 'ends'].append(i)
    boundaries=[ElectrostaticBoundary('inner','electrode_potential',groups['inner'],offset+voltage),ElectrostaticBoundary('outer','electrode_potential',groups['outer'],offset),
        ElectrostaticBoundary('ends','outward_displacement',groups['ends'],0.)]
    case=AxisymmetricElectrostaticCase(p,dict(all=0.),boundaries,order)
    capacitance=TAU*EPS0*epsilon_r*length/np.log(b/a)
    def fields(points):
        r,z=np.asarray(points).T;electric_r=voltage/(r*np.log(b/a));electric=np.column_stack((electric_r,np.zeros(len(r))))
        return offset+voltage*np.log(b/r)/np.log(b/a),electric,EPS0*epsilon_r*electric
    return case,dict(fields=fields,capacitance_f=capacitance,energy_j=.5*capacitance*voltage**2,
        electrode_charge_c=dict(inner=capacitance*voltage,outer=-capacitance*voltage))


def manufactured_quadratic(order=2,n=1,scale=1.,epsilon_r=4.,amplitude=100.,offset=0.,direction='axial',axis=True,holes=0):
    # Separate Phi=A*z^2 and Phi=A*r^2 have constant electrode traces on
    # coordinate-aligned rectangle boundaries and piecewise constant Dn.
    from scripts.curved_meridional_reference import fixture
    mesh=fixture(axis,holes,n=n,scale=scale,shear=0.)[0]['base_mesh']
    a,z0=mesh.outer_rz_m.min(axis=0);b,length=mesh.outer_rz_m.max(axis=0)
    assert direction in ('axial','radial');coordinate=1 if direction=='axial' else 0
    p=AxisymmetricDielectricPartition(mesh,[LinearDielectric('dielectric',epsilon_r)],[DielectricRegion('all','dielectric',list(range(len(mesh.triangles))))])
    electrode=[];axis_edges=[];flux_groups={}
    for i,edge in enumerate(mesh.boundary_edges):
        v,w=mesh.points_rz_m[edge];r,z=(v+w)/2;delta=w-v;normal=np.array([delta[1],-delta[0]])/np.linalg.norm(delta)
        if r==0:axis_edges.append(i)
        elif (z==z0 if direction=='axial' else r==b):electrode.append(i)
        else:
            flux=-2*EPS0*epsilon_r*amplitude*(z if direction=='axial' else r)*normal[coordinate]
            flux_groups.setdefault(float(flux),[]).append(i)
    electrode_value=offset+amplitude*(z0 if direction=='axial' else b)**2
    boundaries=[ElectrostaticBoundary('electrode','electrode_potential',electrode,electrode_value)]
    for i,(value,edges) in enumerate(flux_groups.items()):boundaries.append(ElectrostaticBoundary(f'flux-{i}','outward_displacement',edges,value))
    if axis_edges:boundaries.append(ElectrostaticBoundary('axis','axis_symmetry',axis_edges))
    rho=-(2 if direction=='axial' else 4)*EPS0*epsilon_r*amplitude
    case=AxisymmetricElectrostaticCase(p,dict(all=rho),boundaries,order)
    def fields(points):
        r,z=np.asarray(points).T;electric=np.zeros((len(r),2));x=z if direction=='axial' else r
        electric[:,coordinate]=-2*amplitude*x;return offset+amplitude*x*x,electric,EPS0*epsilon_r*electric
    volume=moment=0.
    for polygon,sign in [(mesh.outer_rz_m,1),*((h,-1) for h in mesh.holes_rz_m)]:
        ra,za=polygon.min(axis=0);rb,zb=polygon.max(axis=0)
        volume+=sign*np.pi*(rb*rb-ra*ra)*(zb-za)
        moment+=sign*(np.pi*(rb*rb-ra*ra)*(zb**3-za**3)/3 if direction=='axial' else np.pi*(rb**4-ra**4)*(zb-za)/2)
    electrode_charge=0. if direction=='axial' else 4*np.pi*EPS0*epsilon_r*amplitude*b*b*(length-z0)
    return case,dict(fields=fields,energy_j=2*EPS0*epsilon_r*amplitude**2*moment,
        volume_charge_c=rho*volume,electrode_charge_c=dict(electrode=electrode_charge))
