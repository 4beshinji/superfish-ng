# SPDX-License-Identifier: Apache-2.0
"""Finite planar magnetic multipole polynomials with explicit SI frames.

These are field representations, not a magnetic solver or a claim that an
arbitrary sampled field is harmonic. Coefficients have absolute units of T.
"""
from dataclasses import dataclass
from math import comb
import numpy as np
from .bh_curve import _real_array
from .config import keys


def _scalar(value,name,positive=False):
    values=_real_array([value],name)
    if values.shape!=(1,) or (positive and values[0]<=0.):raise ValueError(name+' requires a finite '+('positive ' if positive else '')+'real SI scalar')
    return float(values[0])


def _product(a,b,label):
    with np.errstate(over='ignore',under='ignore',invalid='ignore'):
        a=np.asarray(a,dtype=complex);b=np.asarray(b,dtype=complex);result=a*b
    if not np.isfinite(result).all() or np.any((result==0)&(a!=0)&(b!=0)):raise ValueError(label+' exceeds resolvable finite SI arithmetic')
    return result


@dataclass(frozen=True,eq=False)
class PlanarMagneticMultipoleFrame:
    center_xy_m: tuple
    reference_radius_m: float
    rotation_rad: float

    def __post_init__(self):
        center=_real_array(self.center_xy_m,'multipole center [m]')
        if center.shape!=(2,):raise ValueError('multipole center requires exactly [x_m,y_m]')
        radius=_scalar(self.reference_radius_m,'multipole reference radius [m]',True);angle=_scalar(self.rotation_rad,'multipole local-axis rotation [rad]')
        with np.errstate(over='ignore',invalid='ignore'):
            upper=center+radius;lower=center-radius
        if not np.isfinite(upper).all() or not np.isfinite(lower).all() or np.any(upper==center) or np.any(lower==center):raise ValueError('multipole radius is not resolved around its center in finite SI coordinates')
        object.__setattr__(self,'center_xy_m',tuple(map(float,center)));object.__setattr__(self,'reference_radius_m',radius);object.__setattr__(self,'rotation_rad',angle)

    def to_dict(self):return dict(center_xy_m=list(self.center_xy_m),reference_radius_m=self.reference_radius_m,rotation_rad=self.rotation_rad)

    @classmethod
    def from_dict(cls,data):
        names=['center_xy_m','reference_radius_m','rotation_rad'];keys(data,names,names,'planar magnetic multipole frame');return cls(**data)

    def local_coordinates(self,points_xy_m):
        points=_real_array(points_xy_m,'multipole evaluation coordinates [m]')
        if points.ndim!=2 or points.shape[1]!=2 or not len(points):raise ValueError('multipole points require nonempty [x_m,y_m] rows')
        with np.errstate(over='ignore',under='ignore',invalid='ignore',divide='ignore'):
            delta=points-np.asarray(self.center_xy_m);scaled=delta/self.reference_radius_m;z=scaled[:,0]+1j*scaled[:,1]
        if not np.isfinite(z).all() or np.any((z==0)&np.any(delta!=0,axis=1)):raise ValueError('multipole local coordinates exceed resolvable finite SI arithmetic')
        return _product(z,np.exp(-1j*self.rotation_rad),'multipole local coordinate rotation')


@dataclass(frozen=True,eq=False)
class PlanarMagneticMultipoleSeries:
    frame: PlanarMagneticMultipoleFrame
    normal_t: tuple
    skew_t: tuple
    provenance: str

    def __post_init__(self):
        if type(self.frame) is not PlanarMagneticMultipoleFrame:raise ValueError('explicit PlanarMagneticMultipoleFrame required')
        normal=_real_array(self.normal_t,'normal multipole coefficients [T]');skew=_real_array(self.skew_t,'skew multipole coefficients [T]')
        if normal.ndim!=1 or not 1<=len(normal)<=32 or normal.shape!=skew.shape:raise ValueError('normal/skew multipoles require equal one-dimensional arrays with orders n=1..N, 1<=N<=32')
        if type(self.provenance) is not str or not self.provenance.strip():raise ValueError('multipole coefficient provenance must be explicit and nonempty')
        object.__setattr__(self,'normal_t',tuple(map(float,normal)));object.__setattr__(self,'skew_t',tuple(map(float,skew)))

    def to_dict(self):
        return dict(format='superfish_ng_planar_magnetic_multipole_series',schema_version=1,representation='finite_planar_harmonic_polynomial',
            convention='local_By_plus_iBx=sum((normal_n+i*skew_n)*(local_z/reference_radius)^(n-1));n=1..N',
            coefficient_unit='T',frame=self.frame.to_dict(),normal_t=list(self.normal_t),skew_t=list(self.skew_t),provenance=self.provenance,
            interpretation='finite polynomial representation only; no FEM solution, source-free-domain certification, omitted-order bound or longitudinal field integral inferred')

    @classmethod
    def from_dict(cls,data):
        names=['format','schema_version','representation','convention','coefficient_unit','frame','normal_t','skew_t','provenance','interpretation'];keys(data,names,names,'planar magnetic multipole series')
        if type(data['schema_version']) is not int or data['schema_version']!=1:raise ValueError('multipole series schema_version must be integer 1')
        result=cls(PlanarMagneticMultipoleFrame.from_dict(data['frame']),data['normal_t'],data['skew_t'],data['provenance']);expected=result.to_dict()
        if any(data[name]!=expected[name] for name in ('format','representation','convention','coefficient_unit','interpretation')):raise ValueError('multipole series requires the explicit finite polynomial, SI and normal/skew conventions')
        return result

    def evaluate(self,points_xy_m):
        z=self.frame.local_coordinates(points_xy_m);coefficients=np.asarray(self.normal_t)+1j*np.asarray(self.skew_t);value=np.full(len(z),coefficients[-1],dtype=complex)
        for coefficient in coefficients[-2::-1]:
            value=_product(value,z,'multipole field evaluation')
            with np.errstate(over='ignore',invalid='ignore'):value=value+coefficient
            if not np.isfinite(value).all():raise ValueError('multipole field sum exceeds finite SI arithmetic')
        # A passive rotation gives F_local=exp(i*theta)*F_global.
        value=_product(value,np.exp(-1j*self.frame.rotation_rad),'multipole field rotation');field=np.column_stack((value.imag,value.real));field.setflags(write=False);return field

    def in_frame(self,frame):
        if type(frame) is not PlanarMagneticMultipoleFrame:raise ValueError('explicit target PlanarMagneticMultipoleFrame required')
        old=self.frame;delta=old.local_coordinates([frame.center_xy_m])[0];angle=_scalar(frame.rotation_rad-old.rotation_rad,'multipole frame rotation difference [rad]')
        ratio=_scalar(frame.reference_radius_m/old.reference_radius_m,'multipole reference-radius ratio',True)
        values=np.asarray(self.normal_t)+1j*np.asarray(self.skew_t);result=np.zeros(len(values),dtype=complex)
        for k in range(len(values)):
            accumulated=0j;power=1+0j
            for n in range(k,len(values)):
                if n>k:power=complex(_product(power,delta,'multipole translation power'))
                term=complex(_product(values[n],power,'multipole translation term'))*comb(n,k)
                with np.errstate(over='ignore',invalid='ignore'):accumulated+=term
                if not np.isfinite(accumulated):raise ValueError('multipole translation sum exceeds finite SI arithmetic')
            radial=1.
            for _ in range(k):radial=complex(_product(radial,ratio,'multipole radius scaling'))
            result[k]=complex(_product(_product(accumulated,radial,'multipole radius coefficient'),np.exp(1j*_scalar((k+1)*angle,'multipole coefficient phase [rad]')),'multipole coefficient rotation'))
        return PlanarMagneticMultipoleSeries(frame,tuple(result.real),tuple(result.imag),self.provenance)
