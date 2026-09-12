# SPDX-License-Identifier: Apache-2.0
"""Synthetic fixed-charge finite-boundary benchmarks; no open-boundary solver."""
import numpy as np
from superfish_ng.constants import EPS0,TAU
from superfish_ng.planar_mesh import PlanarMesh
from superfish_ng.meridional_mesh import MeridionalMesh
from superfish_ng.dielectrics import LinearDielectric,DielectricRegion,AxisymmetricDielectricPartition
from superfish_ng.planar_dielectrics import PlanarDielectricPartition
from superfish_ng.electrostatic_boundary import ElectrostaticBoundary
from superfish_ng.electrostatic import AxisymmetricElectrostaticCase
from superfish_ng.planar_electrostatic import PlanarElectrostaticCase


def grid(x,y):
    points=np.array([(a,b) for b in y for a in x]);nx=len(x);triangles=[]
    for j in range(len(y)-1):
        for i in range(nx-1):
            a=j*nx+i;b=a+nx;triangles.extend(((a,a+1,b+1),(a,b+1,b)))
    return points,np.asarray(triangles)


def charged_slab(order=2,n=8,outer_ratio=2.,epsilon_r=3.,sign=1.):
    a=.03125;width=.0625;b=a*outer_ratio;epsilon=EPS0*epsilon_r;rho=sign*EPS0*1000.
    y=np.r_[np.linspace(0.,a,n+1),np.linspace(a,b,n+1)[1:]];points,cells=grid(np.linspace(0.,width,5),y)
    mesh=PlanarMesh.create([[0.,0.],[width,0.],[width,b],[0.,b]],points,cells);core=points[cells][:,:,1].mean(axis=1)<a
    p=PlanarDielectricPartition(mesh,[LinearDielectric('dielectric',epsilon_r)],[DielectricRegion('source','dielectric',np.flatnonzero(core).tolist()),DielectricRegion('exterior','dielectric',np.flatnonzero(~core).tolist())])
    ground=[];insulating=[]
    for i,edge in enumerate(mesh.boundary_edges):(ground if points[edge,1].mean()==b else insulating).append(i)
    case=PlanarElectrostaticCase(p,dict(source=rho,exterior=0.),[ElectrostaticBoundary('ground','electrode_potential',ground,0.),ElectrostaticBoundary('symmetry-and-sides','outward_displacement',insulating,0.)],order)
    def fields(points):
        y=np.asarray(points)[:,1];potential=np.where(y<a,rho/(2*epsilon)*(2*a*b-a*a-y*y),rho*a/epsilon*(b-y))
        electric=np.column_stack((np.zeros(len(y)),rho/epsilon*np.minimum(y,a)))
        return potential,electric,epsilon*electric
    probes=np.array([[width/3,y] for y in (.25*a,.75*a,1.25*a,1.75*a)])
    return case,dict(fields=fields,energy=rho*rho*width/(2*epsilon)*(a*a*b-2*a**3/3),ground_charge=-rho*width*a,
        common_points=probes,outer_distance_m=b,source_charge=rho*width*a,
        boundary_potential_shift=lambda other_b:rho*a/epsilon*(other_b-b),
        interpretation='fixed slab volume charge; common field independent of remote ground, potential grows linearly with its distance; no finite zero-at-infinity potential')


def charged_coax(order=2,n=8,outer_ratio=2.,epsilon_r=3.,sign=1.):
    a=.03125;b=a*outer_ratio;length=.125;epsilon=EPS0*epsilon_r;line_charge=sign*EPS0*100.
    points,cells=grid(np.geomspace(a,b,n+1),np.linspace(0.,length,5));mesh=MeridionalMesh([[a,0.],[b,0.],[b,length],[a,length]],[],points,cells)
    p=AxisymmetricDielectricPartition(mesh,[LinearDielectric('dielectric',epsilon_r)],[DielectricRegion('all','dielectric',list(range(len(cells))))]);groups=dict(inner=[],ground=[],ends=[])
    for i,edge in enumerate(mesh.boundary_edges):
        r,z=points[edge].mean(axis=0);groups['inner' if r==a else 'ground' if r==b else 'ends'].append(i)
    case=AxisymmetricElectrostaticCase(p,dict(all=0.),[ElectrostaticBoundary('ground','electrode_potential',groups['ground'],0.),
        ElectrostaticBoundary('fixed-charge','outward_displacement',groups['inner'],-line_charge/(TAU*a)),ElectrostaticBoundary('ends','outward_displacement',groups['ends'],0.)],order)
    def fields(points):
        r=np.asarray(points)[:,0];potential=line_charge/(TAU*epsilon)*np.log(b/r);electric=np.column_stack((line_charge/(TAU*epsilon*r),np.zeros(len(r))))
        return potential,electric,epsilon*electric
    probes=np.array([[r,length/3] for r in (1.125*a,1.25*a,1.5*a,1.75*a)])
    return case,dict(fields=fields,energy=line_charge**2*length/(2*TAU*epsilon)*np.log(b/a),ground_charge=-line_charge*length,
        common_points=probes,outer_distance_m=b,source_charge=line_charge*length,
        boundary_potential_shift=lambda other_b:line_charge/(TAU*epsilon)*np.log(other_b/b),
        interpretation='fixed inner normal displacement; common field independent of remote ground, potential grows logarithmically with its radius; no finite zero-at-infinity potential')
