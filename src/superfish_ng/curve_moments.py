# SPDX-License-Identifier: Apache-2.0
"""Analytic boundary moments of straight and conic segments."""
import cmath
import math
import numpy as np
from .conics import LineSegment,EllipseArc,HyperbolaArc


def revolution_volume_contribution(curve):
    """Return -pi integral r² dz along one directed primitive.

    The sum around a CCW (z,r) domain equals its volume of revolution by
    Green's theorem. A single open primitive's contribution can be negative.
    Conic coordinates are degree-one Laurent polynomials in exp(i*t) or
    exp(t); integrate their degree-three products without chord quadrature.
    """
    if isinstance(curve,LineSegment):
        (z0,r0),(z1,r1) = curve.start_zr_m,curve.end_zr_m
        value = -math.pi*(z1-z0)*(r0*r0+r0*r1+r1*r1)/3
        if not math.isfinite(value):raise ValueError('curve volume exceeds floating-point range')
        return value
    if not isinstance(curve,(EllipseArc,HyperbolaArc)):
        raise ValueError('volume requires a supported curve primitive')
    a,b = curve.semiaxes_m
    c,s = math.cos(curve.rotation_rad),math.sin(curve.rotation_rad)
    branch = curve.branch if isinstance(curve,HyperbolaArc) else 1
    def coefficients(offset,A,B):
        if isinstance(curve,EllipseArc):
            return {0:complex(offset),1:complex(A,-B)/2,-1:complex(A,B)/2}
        return {0:complex(offset),1:complex((A+B)/2),-1:complex((A-B)/2)}
    z = coefficients(curve.center_zr_m[0],branch*a*c,-b*s)
    r = coefficients(curve.center_zr_m[1],branch*a*s,b*c)
    imaginary = isinstance(curve,EllipseArc)
    factor = 1j if imaginary else 1.
    start = curve.start_rad if imaginary else curve.start_parameter
    span = curve.sweep_rad if imaginary else curve.end_parameter-curve.start_parameter
    midpoint = start+span/2
    product = {}
    for i,ri in r.items():
        for j,rj in r.items():
            for k,zk in z.items():
                if k==0:continue
                index = i+j+k
                product[index] = product.get(index,0j)+ri*rj*zk*k*factor
    terms = []
    try:
        for k,coefficient in product.items():
            if coefficient==0:continue
            if k==0:moment=span
            elif imaginary:
                moment=span*cmath.exp(1j*k*midpoint)*np.sinc(k*span/(2*math.pi))
            else:
                x=k*span/2
                moment=span*math.exp(k*midpoint)*(math.sinh(x)/x)
            terms.append(coefficient*moment)
        integral = complex(math.fsum(t.real for t in terms),math.fsum(t.imag for t in terms))
    except (OverflowError,ValueError) as error:
        raise ValueError('curve volume exceeds floating-point range') from error
    value = -math.pi*integral.real
    if not math.isfinite(value) or not math.isfinite(integral.imag):
        raise ValueError('curve volume exceeds floating-point range')
    return value
