# SPDX-License-Identifier: Apache-2.0
"""Explicit isotropic, monotone H(B) tables with no extrapolation or hysteresis."""
from dataclasses import dataclass,field
from numbers import Real
import numpy as np
from .config import keys


def _real_array(value,name):
    try:raw=np.asarray(value,dtype=object)
    except (TypeError,ValueError) as exc:raise ValueError(name+' requires finite real numbers') from exc
    if not raw.size or any(not isinstance(v,Real) or isinstance(v,(bool,np.bool_)) for v in raw.flat):
        raise ValueError(name+' requires finite real numbers; booleans, strings and complex values are unsupported')
    try:result=np.asarray(value,dtype=np.float64)
    except (TypeError,ValueError,OverflowError) as exc:raise ValueError(name+' exceeds finite SI arithmetic') from exc
    if not np.isfinite(result).all():raise ValueError(name+' requires finite real numbers')
    return result.copy()


@dataclass(frozen=True,eq=False)
class MonotoneBHCurve:
    id: str
    b_t: tuple
    h_a_per_m: tuple
    provenance: str
    _b: np.ndarray=field(init=False,repr=False)
    _h: np.ndarray=field(init=False,repr=False)
    _slopes: np.ndarray=field(init=False,repr=False)
    _energy: np.ndarray=field(init=False,repr=False)
    _coenergy: np.ndarray=field(init=False,repr=False)

    def __post_init__(self):
        for name in ('id','provenance'):
            if type(getattr(self,name)) is not str or not getattr(self,name).strip():raise ValueError('B-H curve '+name+' must be nonempty')
        for name in ('b_t','h_a_per_m'):
            if not isinstance(getattr(self,name),(list,tuple)):raise ValueError('B-H table '+name+' must be an explicit list or tuple')
        b=_real_array(self.b_t,'B [T]');h=_real_array(self.h_a_per_m,'H [A/m]')
        if b.ndim!=1 or h.shape!=b.shape or len(b)<2:raise ValueError('B-H table requires matching one-dimensional columns with at least two points')
        if b[0]!=0. or h[0]!=0. or np.any(np.diff(b)<=0.) or np.any(np.diff(h)<=0.):
            raise ValueError('B-H table must start at (0 T, 0 A/m), with both columns strictly increasing')
        with np.errstate(over='ignore',under='ignore',invalid='ignore',divide='ignore'):
            db=np.diff(b);dh=np.diff(h);slope=dh/db;inverse=db/dh
            energy=np.r_[0.,np.cumsum(db*(h[:-1]+.5*dh))]
            coenergy=np.r_[0.,np.cumsum(dh*(b[:-1]+.5*db))]
            secant=h[1:]/b[1:];product=b*h
        if (not all(np.isfinite(v).all() for v in (slope,inverse,energy,coenergy,secant,product))
            or any(np.any(v<=0.) for v in (slope,inverse,secant,np.diff(energy),np.diff(coenergy)))):
            raise ValueError('B-H slopes or integrated energies are unresolved in finite SI arithmetic; reduce table contrast or range')
        object.__setattr__(self,'b_t',tuple(map(float,b)));object.__setattr__(self,'h_a_per_m',tuple(map(float,h)))
        for name,value in dict(_b=b,_h=h,_slopes=slope,_energy=energy,_coenergy=coenergy).items():
            value.setflags(write=False);object.__setattr__(self,name,value)

    def _intervals(self,values,nodes,name):
        if np.any(values<0.) or np.any(values>nodes[-1]):
            raise ValueError(f'{name} is outside the declared B-H table [0, {nodes[-1]}]; extrapolation is unsupported')
        return np.minimum(np.searchsorted(nodes,values,side='right')-1,len(nodes)-2)

    def evaluate_magnitudes(self,b_t):
        b=_real_array(b_t,'B magnitude [T]');i=self._intervals(b,self._b,'B [T]');db=b-self._b[i];slope=self._slopes[i]
        with np.errstate(over='ignore',under='ignore',invalid='ignore',divide='ignore'):
            h=self._h[i]+slope*db;h=np.where(b==self._b[-1],self._h[-1],h)
            secant=np.divide(h,b,out=np.full_like(b,self._slopes[0]),where=b!=0.)
            energy=self._energy[i]+db*(self._h[i]+.5*slope*db)
            dh=h-self._h[i];coenergy=self._coenergy[i]+dh*(self._b[i]+.5*dh/slope)
        result=dict(h_a_per_m=h,secant_reluctivity_m_per_h=secant,differential_reluctivity_m_per_h=slope,
            energy_density_j_per_m3=energy,coenergy_density_j_per_m3=coenergy,interval_indices=i)
        if (any(not np.isfinite(v).all() for v in result.values()) or np.any(secant<=0.)
            or any(np.any((b>0.)&(v<=0.)) for v in (h,energy,coenergy))):
            raise ValueError('B-H evaluation is unresolved in finite SI arithmetic')
        return result

    def induction_magnitudes(self,h_a_per_m):
        h=_real_array(h_a_per_m,'H magnitude [A/m]');i=self._intervals(h,self._h,'H [A/m]')
        b=self._b[i]+((h-self._h[i])/(self._h[i+1]-self._h[i]))*(self._b[i+1]-self._b[i])
        b=np.where(h==self._h[-1],self._b[-1],b)
        if not np.isfinite(b).all() or np.any((h>0.)&(b<=0.)):raise ValueError('B-H inverse is unresolved in finite SI arithmetic')
        return b

    def evaluate_vectors(self,b_t):
        b=_real_array(b_t,'B vector [T]')
        if b.ndim<1 or b.shape[-1] not in (2,3):raise ValueError('B vectors require a final dimension of 2 or 3')
        magnitude=np.hypot.reduce(b,axis=-1);state=self.evaluate_magnitudes(magnitude)
        n=np.divide(b,magnitude[...,None],out=np.zeros_like(b),where=magnitude[...,None]!=0.)
        secant=state['secant_reluctivity_m_per_h'];slope=state['differential_reluctivity_m_per_h']
        tangent=secant[...,None,None]*np.eye(b.shape[-1])+(slope-secant)[...,None,None]*n[...,None]*n[...,None,:]
        h=state['h_a_per_m'][...,None]*n
        if not np.isfinite(tangent).all() or not np.isfinite(h).all():raise ValueError('B-H vector evaluation exceeds finite SI arithmetic')
        try:np.linalg.cholesky(tangent)
        except np.linalg.LinAlgError as exc:raise ValueError('B-H vector tangent is numerically unresolved; reduce curve contrast') from exc
        return dict(state,h_a_per_m=h,tangent_reluctivity_m_per_h=tangent,magnitude_b_t=magnitude)

    def to_dict(self):
        return dict(type='isotropic_monotone_bh_curve',schema_version=1,id=self.id,b_t=list(self.b_t),h_a_per_m=list(self.h_a_per_m),
            provenance=self.provenance,interpolation='piecewise_linear_h_of_b',extrapolation='reject')

    @classmethod
    def from_dict(cls,data):
        names=['type','schema_version','id','b_t','h_a_per_m','provenance','interpolation','extrapolation'];keys(data,names,names,'isotropic B-H curve')
        if data['type']!='isotropic_monotone_bh_curve' or type(data['schema_version']) is not int or data['schema_version']!=1:
            raise ValueError('expected isotropic_monotone_bh_curve schema version 1')
        if data['interpolation']!='piecewise_linear_h_of_b' or data['extrapolation']!='reject':
            raise ValueError('only piecewise_linear_h_of_b interpolation with extrapolation=reject is supported')
        if type(data['b_t']) is not list or type(data['h_a_per_m']) is not list:raise ValueError('B-H columns require JSON lists')
        return cls(data['id'],data['b_t'],data['h_a_per_m'],data['provenance'])
