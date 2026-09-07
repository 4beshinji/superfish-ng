# SPDX-License-Identifier: Apache-2.0
"""Independent regular l=1, m=0 TM solution of a closed PEC sphere.

This reference is never called by the FEM solver. See docs/SPHERE_REFERENCE.md.
"""
from dataclasses import dataclass
from functools import cached_property
import math
import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.special import spherical_jn
from .config import positive
from .constants import C0, EPS0, MU0, TAU


def _radial(x):
    """j1(x)/x and its derivative divided by x, including the origin."""
    x = np.asarray(x, dtype=float)
    small = abs(x) < 1e-3
    safe = np.where(small, 1., x)
    j = spherical_jn(1, safe)
    value = j/safe
    derivative_over_x = spherical_jn(1,safe,derivative=True)/safe**2-j/safe**3
    square = x*x
    return (np.where(small, 1/3-square/30+square**2/840-square**3/45360,value),
            np.where(small, -1/15+square/210-square**2/7560+square**3/498960,derivative_over_x))


@dataclass(frozen=True)
class SphereTM:
    radius_m: float
    beta: float = 1.
    conductivity_s_per_m: float = 5.8e7
    normalization_j: float = 1.

    def __post_init__(self):
        for key in ('radius_m','beta','conductivity_s_per_m','normalization_j'):
            positive(getattr(self,key),key)
        if self.beta > 1:
            raise ValueError('beta must be <= 1')

    @cached_property
    def root(self):
        # PEC: d[x j1(x)]/dx = 0. This bracket contains the first positive root.
        return brentq(lambda x: spherical_jn(1,x)+x*spherical_jn(1,x,derivative=True),2.,3.,xtol=1e-14)

    @property
    def frequency_hz(self):
        return C0*self.root/(TAU*self.radius_m)

    @cached_property
    def amplitude(self):
        integral = quad(lambda t: t**4*float(_radial(self.root*t)[0])**2,0.,1.,
                        epsabs=1e-14,epsrel=1e-12)[0]
        magnetic_integral = (8*math.pi/3)*self.radius_m**5*integral
        return math.sqrt(2*self.normalization_j/(MU0*magnetic_integral))

    def fields(self, points_rz_m):
        p = np.asarray(points_rz_m)
        if p.dtype.kind not in 'iuf' or p.ndim != 2 or p.shape[1] != 2 or not len(p):
            raise ValueError('sphere points must be finite N by 2 (r,z) coordinates')
        p = p.astype(float)
        r,z = p[:,0],p[:,1]-self.radius_m
        distance = np.hypot(r,z)
        if not np.isfinite(p).all() or np.any(r<0) or np.any(distance>self.radius_m*(1+1e-13)):
            raise ValueError('sphere points must lie in the closed r>=0 spherical domain')
        k = self.root/self.radius_m
        value,derivative_over_x = _radial(k*distance)
        u = self.amplitude*value
        derivative_over_s = self.amplitude*k*k*derivative_over_x
        omega = TAU*self.frequency_hz
        return {
            'Hphi_A_per_m': r*u,
            'Er_quadrature_V_per_m': -r*z*derivative_over_s/(omega*EPS0),
            'Ez_quadrature_V_per_m': (2*u+r*r*derivative_over_s)/(omega*EPS0),
        }

    def quantities(self):
        omega = TAU*self.frequency_hz
        rs = math.sqrt(omega*MU0/(2*self.conductivity_s_per_m))
        boundary_u = self.amplitude*float(_radial(self.root)[0])
        surface_integral = (8*math.pi/3)*self.radius_m**4*boundary_u**2
        loss = rs*surface_integral/2
        kb_radius = self.root/self.beta
        if not math.isfinite(kb_radius):
            raise ValueError('sphere transit phase exceeds floating-point range')
        # Centered even axis field: weighted oscillatory quadrature, then phase at z=R.
        axis = lambda t: 2*self.amplitude*float(_radial(self.root*abs(t))[0])/(omega*EPS0)
        transit = self.radius_m*quad(axis,-1.,1.,weight='cos',wvar=kb_radius,epsabs=1e-7,epsrel=1e-11)[0]
        absolute = self.radius_m*quad(axis,-1.,1.,epsabs=1e-7,epsrel=1e-11)[0]
        voltage = transit*complex(math.cos(kb_radius),math.sin(kb_radius))
        rq = abs(voltage)**2/(omega*self.normalization_j)
        return dict(frequency_hz=self.frequency_hz,stored_energy_j=self.normalization_j,
                    surface_resistance_ohm=rs,wall_loss_w=loss,
                    geometry_factor_ohm=omega*self.normalization_j*rs/loss,
                    q0=omega*self.normalization_j/loss,
                    voltage_real_v=voltage.real,voltage_imag_v=voltage.imag,
                    r_over_q_accelerator_ohm=rq,r_over_q_circuit_ohm=rq/2,
                    transit_time_factor_abs=abs(voltage)/absolute)
