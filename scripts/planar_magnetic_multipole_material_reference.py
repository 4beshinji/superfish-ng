# SPDX-License-Identifier: Apache-2.0
"""Synthetic linear apertures with exterior nonlinear or anisotropic remanent layers."""
import numpy as np
from scripts.planar_magnetic_multipole_reference import quadrupole,uniform_dipole
from scripts.planar_bh_reference import _boundaries,_inverse,_curve
from scripts.planar_recoil_reference import _case
from scripts.planar_electrostatic_reference import rectangle
from superfish_ng.constants import MU0
from superfish_ng.bh_curve import MonotoneBHCurve
from superfish_ng.magnetic_materials import MagneticRegion
from superfish_ng.planar_bh_materials import PlanarBHPartition
from superfish_ng.planar_bh import PlanarBHCase
from superfish_ng.recoil_materials import LinearRecoilMaterial,OrientedMagneticRegion,PlanarRecoilPartition
from superfish_ng.planar_recoil import PlanarRecoilCase
from superfish_ng.planar_magnetic_multipoles import PlanarMagneticMultipoleFrame


def linear_limit(kind='bh',field='quadrupole',**kwargs):
    factory=quadrupole if field=='quadrupole' else uniform_dipole;case,frame,ref=factory(**kwargs);p=case.partition
    if kind=='bh':
        materials=[MonotoneBHCurve(m.id,(0.,.25,.5,1.,8.),tuple(b/(MU0*m.mu_r) for b in (0.,.25,.5,1.,8.)),'Synthetic exact linear table for harmonic validation') for m in p.materials]
        converted=PlanarBHCase(PlanarBHPartition(p.mesh,materials,p.regions),dict(case.current_density_z_a_per_m2),case.boundaries,case.element_order,name='synthetic-linear-BH-harmonics')
    elif kind=='recoil':
        materials=[LinearRecoilMaterial(m.id,(m.mu_r,m.mu_r),(0.,0.)) for m in p.materials];regions=[OrientedMagneticRegion(v.id,v.material,v.cell_indices,0.) for v in p.regions]
        converted=PlanarRecoilCase(PlanarRecoilPartition(p.mesh,materials,regions),dict(case.current_density_z_a_per_m2),case.boundaries,case.element_order,name='synthetic-linear-recoil-harmonics')
    else:raise ValueError('expected bh or recoil reference')
    return converted,frame,ref


def exterior_material(kind='bh',n=4,order=1,scale=1.,amplitude=1.,angle=0.,offset=.125):
    rotation=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]]);shift=np.array([.25,-.125])*scale;mesh,local,width,height,_,_=rectangle(n,scale,rotation=rotation,shift=shift);cut=height/2;labels=(local[mesh.triangles][:,:,1].mean(axis=1)>=cut).astype(int)
    if kind=='bh':
        linear=MonotoneBHCurve('m0',(0.,.25,.5,1.,8.),(0.,250.,500.,1000.,8000.),'Synthetic aperture exactly linear H=1000 B');nonlinear=_curve(1);materials=[linear,nonlinear];regions=[MagneticRegion(f'r{i}',f'm{i}',np.flatnonzero(labels==i).tolist()) for i in range(2)];partition=PlanarBHPartition(mesh,materials,regions);hx=875*amplitude;bs=np.array([hx/1000.,float(_inverse(nonlinear,hx))]);hs=np.array([[hx,0.],[hx,0.]])
    elif kind=='recoil':
        hx=20000*amplitude;orientation=-.4;turn=np.array([[np.cos(orientation),-np.sin(orientation)],[np.sin(orientation),np.cos(orientation)]]);nu=turn@np.diag(1/(MU0*np.array([3.,11.])))@turn.T;br=turn@np.array([.1,.03])*amplitude;bs=np.array([MU0*2*hx,br[0]+(hx+nu[0,1]*br[1])/nu[0,0]]);hs=np.array([[hx,0.],nu@(np.array([bs[1],0.])-br)])
    else:raise ValueError('expected bh or recoil reference')
    def potential(y):return offset+bs[0]*np.minimum(y,cut)+bs[1]*np.maximum(y-cut,0.)
    def local_fields(points,owners=None):
        y=points[:,1];owners=(y>=cut).astype(int) if owners is None else owners;return potential(y),np.column_stack((bs[owners],np.zeros(len(y)))),hs[owners]
    if kind=='bh':case=PlanarBHCase(partition,dict(r0=0.,r1=0.),_boundaries(partition,local,width,height,potential,lambda y:hx,'tangential'),order,name='synthetic-nonlinear-exterior-linear-aperture')
    else:case=_case(mesh,local,labels,[((2.,2.),(0.,0.),0.),((3.,11.),tuple(np.array([.1,.03])*amplitude),-.4)],angle,offset,[0.,0.],local_fields,order,'synthetic-anisotropic-remanent-exterior-linear-aperture')[0]
    center=np.array([width/2,height/4])@rotation.T+shift;frame=PlanarMagneticMultipoleFrame(tuple(center),min(width/8,height/8),angle+.2)
    def fields(points):return local_fields((np.asarray(points)-shift)@rotation)[1]@rotation.T
    f=1j*bs[0]*np.exp(.2j);return case,frame,dict(fields=fields,coefficients_t=np.array([f,0j]),aperture_b_t=float(bs[0]),material_kind=kind)
