# SPDX-License-Identifier: Apache-2.0
"""Analytic conic geometry primitives; independent of field/mesh order."""
from dataclasses import dataclass
import math
import numpy as np



def rotation_cos_sin(angle):
    """Exact signed permutations for cardinal rotations, without tolerance snapping."""
    cardinal = {0.: (1.,0.), math.pi/2: (0.,1.), -math.pi/2: (0.,-1.),
                math.pi: (-1.,0.), -math.pi: (-1.,0.)}
    return cardinal[angle] if angle in cardinal else (math.cos(angle),math.sin(angle))


def _checked_evaluation(points,tangent,curvature):
    if not all(np.all(np.isfinite(v)) for v in (points,tangent,curvature)) or np.any(curvature<=0):
        raise ValueError('conic evaluation exceeds floating-point range; reduce parameter or dimension extremes')
    return dict(points_zr_m=points,tangent_zr=tangent,curvature_per_m=curvature)


@dataclass(frozen=True)
class LineSegment:
    """Directed straight geometry primitive in (z,r)."""
    start_zr_m: tuple
    end_zr_m: tuple

    def __post_init__(self):
        for key in ('start_zr_m','end_zr_m'):
            value = getattr(self,key)
            if (not isinstance(value,(tuple,list)) or len(value)!=2
                    or any(type(x) not in (int,float) or not math.isfinite(x) for x in value)):
                raise ValueError(f'{key} requires two finite numbers')
            object.__setattr__(self,key,tuple(float(x) for x in value))
        delta = np.asarray(self.end_zr_m)-self.start_zr_m
        length = math.hypot(*delta)
        if not math.isfinite(length) or length<=0:
            raise ValueError('line requires distinct endpoints and a finite length')

    def evaluate(self,fraction):
        raw = np.asarray(fraction)
        if raw.dtype.kind not in 'iuf' or not np.all(np.isfinite(raw)) or np.any((raw<0)|(raw>1)):
            raise ValueError('line parameter fraction must be finite in [0,1]')
        delta = np.asarray(self.end_zr_m)-self.start_zr_m
        tangent = delta/math.hypot(*delta)
        return dict(points_zr_m=(1-raw[...,None])*self.start_zr_m+raw[...,None]*self.end_zr_m,
                    tangent_zr=np.broadcast_to(tangent,raw.shape+(2,)),
                    curvature_per_m=np.zeros(raw.shape))

    @property
    def minimum_radius_m(self):
        return math.inf  # Zero curvature; this is not an unmeasured radius.

    @property
    def signed_line_area_m2(self):
        a,b = self.start_zr_m,self.end_zr_m
        return (a[0]*b[1]-a[1]*b[0])/2

    def linearize(self,tolerance_m,*,max_segments=20000):
        if type(tolerance_m) not in (int,float) or not math.isfinite(tolerance_m) or tolerance_m<=0:
            raise ValueError('line chord tolerance must be finite and positive')
        if type(max_segments) is not int or max_segments<1:
            raise ValueError('max_segments must be a positive integer')
        return np.asarray((self.start_zr_m,self.end_zr_m))


def check_curve_join(first,second,*,position_tolerance_m,angle_tolerance_rad=1e-8,
                     require_tangent=True):
    """Check a directed end-to-start join without snapping either primitive.

    Position tolerance is explicit in SI. Tangency means aligned oriented
    unit vectors, not merely parallel lines. Curvature continuity is not implied.
    """
    if not isinstance(first,(LineSegment,EllipseArc,HyperbolaArc)) or not isinstance(second,(LineSegment,EllipseArc,HyperbolaArc)):
        raise ValueError('curve join requires supported geometry primitives')
    if (type(position_tolerance_m) not in (int,float) or not math.isfinite(position_tolerance_m)
            or position_tolerance_m<0):
        raise ValueError('position_tolerance_m must be finite and nonnegative')
    if (type(angle_tolerance_rad) not in (int,float) or not math.isfinite(angle_tolerance_rad)
            or not 0<=angle_tolerance_rad<math.pi/2):
        raise ValueError('angle_tolerance_rad must be finite in [0, pi/2)')
    if type(require_tangent) is not bool:
        raise ValueError('require_tangent must be boolean')
    a,b = first.evaluate(1.),second.evaluate(0.)
    delta = a['points_zr_m']-b['points_zr_m']
    gap = math.hypot(*delta)
    u,v = a['tangent_zr'],b['tangent_zr']
    angle = math.atan2(abs(u[0]*v[1]-u[1]*v[0]),float(np.dot(u,v)))
    if gap>position_tolerance_m:
        raise ValueError(f'curve endpoint gap {gap:.9g} m exceeds {position_tolerance_m:.9g} m')
    if require_tangent and angle>angle_tolerance_rad:
        raise ValueError(f'curve tangent angle {angle:.9g} rad exceeds {angle_tolerance_rad:.9g} rad')
    return dict(endpoint_gap_m=gap,tangent_angle_rad=angle,
                tangent_continuous=angle<=angle_tolerance_rad)


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
        c,s = rotation_cos_sin(self.rotation_rad)
        rotation = np.array([[c,-s],[s,c]])
        points = np.stack((a*np.cos(theta),b*np.sin(theta)),axis=-1) @ rotation.T
        derivative = np.stack((-a*np.sin(theta),b*np.cos(theta)),axis=-1) @ rotation.T
        speed = np.hypot(derivative[...,0],derivative[...,1])
        return _checked_evaluation(points+np.asarray(self.center_zr_m),
                    np.sign(self.sweep_rad)*derivative/speed[...,None],
                    (a/speed)*(b/speed)/speed)

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


@dataclass(frozen=True)
class HyperbolaArc:
    """Finite arc (branch*a*cosh(u), b*sinh(u)), rotated in (z,r)."""
    center_zr_m: tuple
    semiaxes_m: tuple
    start_parameter: float
    end_parameter: float
    branch: int = 1
    rotation_rad: float = 0.

    def __post_init__(self):
        # Reuse only the common center/axes/rotation validation.
        common = EllipseArc(self.center_zr_m,self.semiaxes_m,0.,1.,self.rotation_rad)
        for key in ('center_zr_m','semiaxes_m','rotation_rad'):
            object.__setattr__(self,key,getattr(common,key))
        for key in ('start_parameter','end_parameter'):
            value = getattr(self,key)
            if type(value) not in (int,float) or not math.isfinite(value):
                raise ValueError(f'{key} must be finite')
        if self.branch not in (-1,1) or type(self.branch) is not int:
            raise ValueError('hyperbola branch must be integer -1 or 1')
        if self.start_parameter == self.end_parameter:
            raise ValueError('hyperbola parameter interval must be nonzero')
        try:
            bound = math.hypot(self.semiaxes_m[0]*math.cosh(self.parameter_extent),
                               self.semiaxes_m[1]*math.sinh(self.parameter_extent))
        except OverflowError as error:
            raise ValueError('hyperbola interval exceeds floating-point range') from error
        if not math.isfinite(bound) or bound == 0:
            raise ValueError('hyperbola interval exceeds floating-point range')

    @property
    def parameter_extent(self):
        return max(abs(self.start_parameter),abs(self.end_parameter))

    def evaluate(self,fraction):
        raw = np.asarray(fraction)
        if raw.dtype.kind not in 'iuf' or not np.all(np.isfinite(raw)) or np.any((raw<0)|(raw>1)):
            raise ValueError('hyperbola parameter fraction must be finite in [0,1]')
        u = self.start_parameter+(self.end_parameter-self.start_parameter)*raw.astype(float)
        a,b = self.semiaxes_m
        c,s = rotation_cos_sin(self.rotation_rad)
        rotation = np.array([[c,-s],[s,c]])
        points = np.stack((self.branch*a*np.cosh(u),b*np.sinh(u)),axis=-1) @ rotation.T
        derivative = np.stack((self.branch*a*np.sinh(u),b*np.cosh(u)),axis=-1) @ rotation.T
        speed = np.hypot(derivative[...,0],derivative[...,1])
        return _checked_evaluation(points+np.asarray(self.center_zr_m),
                    np.sign(self.end_parameter-self.start_parameter)*derivative/speed[...,None],
                    (a/speed)*(b/speed)/speed)

    @property
    def minimum_radius_m(self):
        low,high = sorted((self.start_parameter,self.end_parameter))
        u = min(max(0.,low),high)
        a,b = self.semiaxes_m
        speed = math.hypot(a*math.sinh(u),b*math.cosh(u))
        return float((speed/a)*(speed/b)*speed)

    @property
    def signed_line_area_m2(self):
        ends = self.evaluate([0.,1.])['points_zr_m']
        delta = ends[1]-ends[0]
        z,r = self.center_zr_m
        a,b = self.semiaxes_m
        return float((self.branch*a*b*(self.end_parameter-self.start_parameter)+z*delta[1]-r*delta[0])/2)

    def linearize(self,tolerance_m,*,max_segments=20000):
        if type(tolerance_m) not in (int,float) or not math.isfinite(tolerance_m) or tolerance_m<=0:
            raise ValueError('hyperbola chord tolerance must be finite and positive')
        if type(max_segments) is not int or max_segments<1:
            raise ValueError('max_segments must be a positive integer')
        a,b = self.semiaxes_m
        bound = math.hypot(a*math.cosh(self.parameter_extent),b*math.sinh(self.parameter_extent))
        limit = math.sqrt(tolerance_m/bound)*math.sqrt(8)
        span = abs(self.end_parameter-self.start_parameter)
        if limit == 0 or span/max_segments > limit:
            raise ValueError('hyperbola chord tolerance exceeds max_segments; increase tolerance or explicit limit')
        count = max(1,math.ceil(span/limit))
        return self.evaluate(np.linspace(0,1,count+1))['points_zr_m']
