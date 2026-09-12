# SPDX-License-Identifier: Apache-2.0
"""Independent separated two-layer TEM reference; never used by the solver."""
import numpy as np
from superfish_ng.constants import C0,EPS0,MU0,TAU
from superfish_ng.meridional_mesh import MeridionalMesh
from superfish_ng.rf_materials import LinearRFMaterial,RFMaterialRegion,RFMaterialPartition


def layered_partition(nr=4,nz=24,scale=1.):
    if nz%3:raise ValueError('layered reference needs nz divisible by 3')
    a,b,length=scale*np.array([.03125,.046875,.1875]);cut=2*length/3
    radii=np.linspace(a,b,nr+1)
    zs=np.r_[np.linspace(0,cut,2*nz//3+1),np.linspace(cut,length,nz//3+1)[1:]]
    points=np.array([[r,z] for z in zs for r in radii]);triangles=[];labels=[]
    for j in range(nz):
        for i in range(nr):
            low=j*(nr+1)+i;right=low+1;top=low+nr+1;corner=top+1
            triangles.extend([[low,right,corner],[low,corner,top]]);labels.extend([int(j>=2*nz//3)]*2)
    mesh=MeridionalMesh([[a,0],[b,0],[b,length],[a,length]],[],points,triangles)
    materials=[LinearRFMaterial('vacuum',1.,1.),LinearRFMaterial('dielectric',4.,1.)]
    regions=[RFMaterialRegion('first','vacuum',np.flatnonzero(np.array(labels)==0).tolist()),
             RFMaterialRegion('second','dielectric',np.flatnonzero(np.array(labels)==1).tolist())]
    return RFMaterialPartition(mesh,materials,regions)


def layered_reference(n,scale=1.,energy=1.,conductivity=5.8e7):
    a,b,length=scale*np.array([.03125,.046875,.1875]);cut=2*length/3;k0=3*n*np.pi/(4*length);frequency=k0*C0/TAU
    # Weighted radial Poincare: rho_1 >= pi*sqrt(a/b)/(b-a). With epsilon<=4
    # and mu=1, every nonconstant radial sector has k0>=rho_1/2.
    radial_lower_bound=np.pi*np.sqrt(a/b)/(2*(b-a))
    if not k0<radial_lower_bound:raise ValueError('requested TEM mode lacks an independent radial-band guard')
    ratio=1. if n%2==0 else -2.;integrals=np.array([cut/2,ratio*ratio*(length-cut)/2])
    amplitude=np.sqrt(energy/(MU0*np.pi*np.log(b/a)*integrals.sum()));integrals*=amplitude**2
    def fields(points):
        points=np.asarray(points);r,z=points.T;left=z<=cut
        scalar=np.where(left,amplitude*np.cos(k0*z),ratio*amplitude*np.cos(2*k0*(length-z)))
        derivative=np.where(left,-amplitude*k0*np.sin(k0*z),2*k0*ratio*amplitude*np.sin(2*k0*(length-z)))
        eps=np.where(left,1.,4.);return scalar/r,derivative/(TAU*frequency*EPS0*eps*r),np.zeros(len(points))
    # Counterclockwise outer contour: bottom, outer cylinder, top, inner.
    walls=np.array([TAU*np.log(b/a)*amplitude**2,TAU/b*integrals.sum(),
                    TAU*np.log(b/a)*(ratio*amplitude)**2,TAU/a*integrals.sum()])
    rs=np.sqrt(np.pi*frequency*MU0/conductivity);loss=rs*walls.sum()/2
    # Integral of epsilon0*epsilon*E²/4. Derivative sin² integrals have the
    # same half-length factor here; epsilon cancels the local wave-number².
    electric_regions=MU0*np.pi/2*np.log(b/a)*integrals
    magnetic_regions=electric_regions.copy()
    return dict(frequency_hz=frequency,stored_energy_j=energy,electric_energy_j=energy/2,magnetic_energy_j=energy/2,
        wall_loss_w=loss,surface_resistance_ohm=rs,q0=TAU*frequency*energy/loss,
        geometry_factor_ohm=2*TAU*frequency*energy/walls.sum(),wall_h2_integral_a2_by_segment=walls,
        electric_energy_j_by_region=electric_regions,magnetic_energy_j_by_region=magnetic_regions,
        radial_mode_frequency_lower_bound_hz=radial_lower_bound*C0/TAU),fields
