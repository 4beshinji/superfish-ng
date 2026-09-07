# SPDX-License-Identifier: Apache-2.0
"""Analytic conic geometry primitives; independent of field/mesh order."""
from dataclasses import dataclass
import math
import numpy as np


@dataclass(frozen=True)
class EllipseArc:
    """Rotated ellipse arc in (z,r), parameterized by fraction in [0,1].

    Semi-axes refer to the unrotated z and r coordinates. Positive rotation
    and sweep are counterclockwise in (z,r). This primitive alone does not
    certify a physical cavity boundary, intersections, or axis connectivity.
    """
    center_zr_m: tuple
    semiaxes_m: tuple
    start_rad: float
    sweep_rad: float
    rotation_rad: float = 0.

    def __post_init__(self):
        for key in ('center_zr_m','semiaxes_m'):
            value = getattr(self,key)
            if (not isinstance(value,(tuple,list)) or len(value)!=2
                    or any(type(x) not in (int,float) or not math.isfinite(x) for x in value)):
                raise ValueError(f'{key} requires two finite numbers')
            object.__setattr__(self,key,tuple(float(x) for x in value))
        if min(self.semiaxes_m)<=0:
            raise ValueError('ellipse semiaxes must be positive')
        for key in ('start_rad','sweep_rad','rotation_rad'):
            value = getattr(self,key)
            if type(value) not in (int,float) or not math.isfinite(value):
                raise ValueError(f'{key} must be finite')
        if not 0<abs(self.sweep_rad)<2*math.pi:
            raise ValueError('ellipse arc requires nonzero sweep smaller than a full turn')
        for key in ('start_rad','rotation_rad'):
            object.__setattr__(self,key,math.remainder(getattr(self,key),2*math.pi))

    def evaluate(self,fraction):
        raw = np.asarray(fraction)
        if raw.dtype.kind not in 'iuf' or not np.all(np.isfinite(raw)) or np.any((raw<0)|(raw>1)):
            raise ValueError('ellipse parameter must be finite in [0,1]')
        theta = self.start_rad+raw.astype(float)*self.sweep_rad
        a,b = self.semiaxes_m
        c,s = math.cos(self.rotation_rad),math.sin(self.rotation_rad)
        rotation = np.array([[c,-s],[s,c]])
        points = np.stack((a*np.cos(theta),b*np.sin(theta)),axis=-1) @ rotation.T
        derivative = np.stack((-a*np.sin(theta),b*np.cos(theta)),axis=-1) @ rotation.T
        speed = np.linalg.norm(derivative,axis=-1)
        return dict(points_zr_m=points+np.asarray(self.center_zr_m),
                    tangent_zr=np.sign(self.sweep_rad)*derivative/speed[...,None],
                    curvature_per_m=a*b/speed**3)

    @property
    def minimum_radius_m(self):
        low,high = sorted((self.start_rad,self.start_rad+self.sweep_rad))
        critical = np.arange(math.ceil(low/(math.pi/2)),math.floor(high/(math.pi/2))+1)*math.pi/2
        theta = np.concatenate(([low,high],critical))
        a,b = self.semiaxes_m
        speed = np.hypot(a*np.sin(theta),b*np.cos(theta))
        return float(np.min(speed**3/(a*b)))

    @property
    def signed_line_area_m2(self):
        """One-half integral of z dr-r dz along this open arc."""
        ends = self.evaluate([0.,1.])['points_zr_m']
        delta = ends[1]-ends[0]
        z,r = self.center_zr_m
        a,b = self.semiaxes_m
        return float((a*b*self.sweep_rad+z*delta[1]-r*delta[0])/2)

    def linearize(self,tolerance_m,*,max_segments=20000):
        """Bound interpolation-to-chord distance by max(a,b)*delta_theta²/8.

        Returns both endpoints. It does not alter or join adjacent primitives.
        """
        if type(tolerance_m) not in (int,float) or not math.isfinite(tolerance_m) or tolerance_m<=0:
            raise ValueError('ellipse chord tolerance must be finite and positive')
        if type(max_segments) is not int or max_segments<1:
            raise ValueError('max_segments must be a positive integer')
        limit = math.sqrt(tolerance_m/max(self.semiaxes_m))*math.sqrt(8)
        if limit == 0 or abs(self.sweep_rad)/max_segments > limit:
            raise ValueError('ellipse chord tolerance exceeds max_segments; increase tolerance or explicit limit')
        count = max(1,math.ceil(abs(self.sweep_rad)/limit))
        return self.evaluate(np.linspace(0,1,count+1))['points_zr_m']
