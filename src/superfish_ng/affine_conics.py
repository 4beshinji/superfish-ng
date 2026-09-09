# SPDX-License-Identifier: Apache-2.0
"""Axis-preserving affine conic transforms retaining the native arc fraction."""
import math
import numpy as np
from .affine_remesh_tracking import validate_affine_map
from .conics import LineSegment,EllipseArc,HyperbolaArc,rotation_cos_sin


def transform_curve(curve,affine_map):
    """Map (r,z) to (a*r,b*r+c*z), keeping corresponding fraction in [0,1].

    This transforms one primitive, not a validated cavity or mesh. Ill-resolved
    factorizations fail explicitly; a finite matrix alone is not a certificate.
    """
    a,b,c=validate_affine_map(affine_map)
    if not isinstance(curve,(LineSegment,EllipseArc,HyperbolaArc)):
        raise ValueError('affine curve requires a native line, ellipse or hyperbola')
    if (a,b,c)==(1.,0.,1.):return curve
    matrix=np.array([[c,b],[0.,a]])
    def point(value):
        with np.errstate(over='ignore',invalid='ignore'):result=matrix@value
        if not np.isfinite(result).all():raise ValueError('affine curve coordinates exceed finite range')
        return tuple(map(float,result))
    if isinstance(curve,LineSegment):return LineSegment(point(curve.start_zr_m),point(curve.end_zr_m))
    center=point(curve.center_zr_m);co,si=rotation_cos_sin(curve.rotation_rad)
    with np.errstate(over='ignore',invalid='ignore'):
        basis=matrix@np.array([[co,-si],[si,co]])@np.diag(curve.semiaxes_m)
    if not np.isfinite(basis).all():raise ValueError('affine conic axes exceed finite range')
    scale=float(np.max(np.abs(basis)))
    if scale==0:raise ValueError('affine conic axes are unresolved')
    normalized=basis/scale
    if isinstance(curve,EllipseArc):
        rotation,axes,right=np.linalg.svd(normalized)
        if np.linalg.det(rotation)<0:
            rotation[:,1]*=-1;right[1,:]*=-1
        shift=math.atan2(right[1,0],right[0,0])
        reconstructed=rotation@np.diag(axes)@np.array([[math.cos(shift),-math.sin(shift)],[math.sin(shift),math.cos(shift)]])
        parameters=dict(start_rad=curve.start_rad+shift,sweep_rad=curve.sweep_rad)
        cls=EllipseArc
    else:
        normalized[:,0]*=curve.branch
        u,v=normalized.T
        ratio=-2*float(u@v)/float(u@u+v@v)
        if not abs(ratio)<1:raise ValueError('affine hyperbola UNVERIFIED: hyperbolic shift is unresolved')
        shift=.5*math.atanh(ratio);ch,sh=math.cosh(shift),math.sinh(shift)
        orthogonal=normalized@np.array([[ch,sh],[sh,ch]])
        axes=np.linalg.norm(orthogonal,axis=0)
        rotation=orthogonal/axes;rotation[:,0]*=curve.branch
        reconstructed=rotation@np.diag([curve.branch*axes[0],axes[1]])@np.array([[ch,-sh],[-sh,ch]])
        parameters=dict(start_parameter=curve.start_parameter-shift,end_parameter=curve.end_parameter-shift,branch=curve.branch)
        cls=HyperbolaArc
    tolerance=4096*np.finfo(float).eps
    if (not np.isfinite(axes).all() or min(axes)<=tolerance*max(axes)
            or np.max(np.abs(rotation.T@rotation-np.eye(2)))>tolerance
            or np.linalg.det(rotation)<=0
            or np.max(np.abs(reconstructed-normalized))>tolerance):
        raise ValueError('affine conic UNVERIFIED: axis factorization is unresolved at roundoff scale')
    with np.errstate(over='ignore',invalid='ignore'):physical_axes=axes*scale
    if not np.isfinite(physical_axes).all() or min(physical_axes)<=0:
        raise ValueError('affine conic axes exceed finite range')
    return cls(center,tuple(map(float,physical_axes)),rotation_rad=math.atan2(rotation[1,0],rotation[0,0]),**parameters)
