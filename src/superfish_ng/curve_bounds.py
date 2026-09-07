# SPDX-License-Identifier: Apache-2.0
"""Conservative conic interval boxes and bounded separation certification."""
import math
import numpy as np
from .conics import LineSegment, EllipseArc, HyperbolaArc


def curve_bounds(curve,first=0.,last=1.):
    """Include coordinate extrema, then pad for floating-point evaluation.

    Returns lower/upper (z,r). Padding is conservative engineering arithmetic,
    not a formally rounded interval implementation of transcendental functions.
    """
    if not isinstance(curve,(LineSegment,EllipseArc,HyperbolaArc)):
        raise ValueError('bounds require a supported curve primitive')
    if any(type(x) not in (int,float) or not math.isfinite(x) for x in (first,last)) or not 0<=first<last<=1:
        raise ValueError('bounds require 0 <= first < last <= 1')
    fractions = [first,last]
    if not isinstance(curve,LineSegment):
        a,b = curve.semiaxes_m
        c,s = math.cos(curve.rotation_rad),math.sin(curve.rotation_rad)
        if isinstance(curve,EllipseArc):
            start,span = curve.start_rad,curve.sweep_rad
            coefficients = ((a*c,-b*s),(a*s,b*c))
        else:
            start,span = curve.start_parameter,curve.end_parameter-curve.start_parameter
            coefficients = ((curve.branch*a*c,-b*s),(curve.branch*a*s,b*c))
        low,high = sorted((start+span*first,start+span*last))
        for A,B in coefficients:
            if isinstance(curve,EllipseArc):
                root = math.atan2(B,A)
                candidates = [root+k*math.pi for k in range(math.ceil((low-root)/math.pi),math.floor((high-root)/math.pi)+1)]
            else:
                candidates = [math.atanh(-B/A)] if A!=0 and abs(B/A)<1 else []
            fractions.extend((x-start)/span for x in candidates if low<=x<=high)
    p = curve.evaluate(np.clip(fractions,first,last))['points_zr_m']
    scale = float(np.max(np.abs(p)))
    if not isinstance(curve,LineSegment):
        scale = max(scale,max(curve.semiaxes_m),max(map(abs,curve.center_zr_m)))
    pad = 128*np.finfo(float).eps*scale
    lower = np.nextafter(p.min(axis=0)-pad,-np.inf)
    upper = np.nextafter(p.max(axis=0)+pad,np.inf)
    if not np.all(np.isfinite([lower,upper])):
        raise ValueError('curve bounds exceed floating-point range')
    return lower,upper


def certify_curve_separation(first,second,minimum_gap_m=0.,*,max_boxes=10000,
                             first_interval=(0.,1.),second_interval=(0.,1.)):
    """Certify disjoint curve images using interval subdivision.

    Adjacent primitives sharing a valid join cannot pass this test. A failure
    without a proximity witness means unresolved, not a proven intersection.
    """
    if type(minimum_gap_m) not in (int,float) or not math.isfinite(minimum_gap_m) or minimum_gap_m<0:
        raise ValueError('minimum_gap_m must be finite and nonnegative')
    if type(max_boxes) is not int or max_boxes<1:
        raise ValueError('max_boxes must be a positive integer')
    curve_bounds(first,*first_interval)
    curve_bounds(second,*second_interval)
    pending = [(*first_interval,*second_interval)]
    checked = 0
    bound = math.inf
    while pending:
        if checked>=max_boxes:
            raise ValueError('curve separation UNVERIFIED: max_boxes reached; increase limit or inspect touching/intersecting curves')
        a,b,c,d = pending.pop()
        left,right = curve_bounds(first,a,b),curve_bounds(second,c,d)
        checked += 1
        delta = np.maximum(np.maximum(left[0]-right[1],right[0]-left[1]),0)
        distance = math.hypot(*delta)
        if distance>minimum_gap_m:
            bound = min(bound,distance)
            continue
        p = first.evaluate([a,(a+b)/2,b])['points_zr_m']
        q = second.evaluate([c,(c+d)/2,d])['points_zr_m']
        witness = float(np.min(np.hypot((p[:,None]-q)[...,0],(p[:,None]-q)[...,1])))
        if witness<=minimum_gap_m:
            raise ValueError(f'curve separation FAIL: sampled distance {witness:.9g} m <= {minimum_gap_m:.9g} m')
        if math.hypot(*(left[1]-left[0])) >= math.hypot(*(right[1]-right[0])):
            midpoint = (a+b)/2
            if midpoint in (a,b):
                raise ValueError('curve separation UNVERIFIED at floating-point resolution')
            pending.extend(((a,midpoint,c,d),(midpoint,b,c,d)))
        else:
            midpoint = (c+d)/2
            if midpoint in (c,d):
                raise ValueError('curve separation UNVERIFIED at floating-point resolution')
            pending.extend(((a,b,c,midpoint),(a,b,midpoint,d)))
    return dict(separated=True,lower_bound_m=bound,boxes_checked=checked)


def directional_derivative_bounds(curve,direction,first=0.,last=1.):
    """Bounds for d(position)/d(fraction) projected onto a unit direction."""
    curve_bounds(curve,first,last)  # Common type and interval validation.
    direction = np.asarray(direction,dtype=float)
    if direction.shape!=(2,) or not np.all(np.isfinite(direction)):
        raise ValueError('projection direction must be a finite pair')
    norm = math.hypot(*direction)
    if not math.isfinite(norm) or norm==0:
        raise ValueError('projection direction must have finite nonzero norm')
    direction = direction/norm
    if isinstance(curve,LineSegment):
        value = float(np.dot(np.asarray(curve.end_zr_m)-curve.start_zr_m,direction))
        pad = 128*np.finfo(float).eps*math.hypot(*(np.asarray(curve.end_zr_m)-curve.start_zr_m))
        return value-pad,value+pad
    a,b = curve.semiaxes_m
    c,s = math.cos(curve.rotation_rad),math.sin(curve.rotation_rad)
    first_axis = float(np.dot(direction,[c,s]))
    second_axis = float(np.dot(direction,[-s,c]))
    if isinstance(curve,EllipseArc):
        start,span = curve.start_rad,curve.sweep_rad
        A,B = span*b*second_axis,-span*a*first_axis
    else:
        start,span = curve.start_parameter,curve.end_parameter-curve.start_parameter
        A,B = span*b*second_axis,span*curve.branch*a*first_axis
    low,high = sorted((start+span*first,start+span*last))
    candidates = [low,high]
    if isinstance(curve,EllipseArc):
        root = math.atan2(B,A)
        candidates.extend(root+k*math.pi for k in range(math.ceil((low-root)/math.pi),math.floor((high-root)/math.pi)+1))
        values = [A*math.cos(t)+B*math.sin(t) for t in candidates]
        scale = abs(A)+abs(B)
    else:
        if A!=0 and abs(B/A)<1:
            root = math.atanh(-B/A)
            if low<=root<=high:candidates.append(root)
        values = [A*math.cosh(t)+B*math.sinh(t) for t in candidates]
        extent = max(abs(low),abs(high))
        scale = abs(A)*math.cosh(extent)+abs(B)*math.sinh(extent)
    pad = 128*np.finfo(float).eps*scale
    bounds = min(values)-pad,max(values)+pad
    if not np.all(np.isfinite(bounds)):
        raise ValueError('curve derivative bounds exceed floating-point range')
    return bounds


def certify_adjacent_curves(first,second,*,position_tolerance_m,max_depth=32,max_boxes=10000):
    """Separate neighbors except for their declared end-to-start join.

    A common projection must increase strictly through a small join neighborhood.
    The remaining interval pairs are checked by ordinary separation. Endpoints
    are identified only within the supplied tolerance; no coordinates are moved.
    """
    from .conics import check_curve_join
    join = check_curve_join(first,second,position_tolerance_m=position_tolerance_m,require_tangent=False)
    if type(max_depth) is not int or max_depth<1 or type(max_boxes) is not int or max_boxes<1:
        raise ValueError('adjacency limits must be positive integers')
    u,v = first.evaluate(1.)['tangent_zr'],second.evaluate(0.)['tangent_zr']
    direction = u+v
    if math.hypot(*direction)<=128*np.finfo(float).eps:
        raise ValueError('curve adjacency UNVERIFIED: opposite tangents at the join')
    offset = second.evaluate(0.)['points_zr_m']-first.evaluate(1.)['points_zr_m']
    if float(np.dot(offset,direction))<0:
        raise ValueError('curve adjacency UNVERIFIED: endpoint tolerance overlaps the separating projection')
    for depth in range(max_depth):
        width = 2.**(-depth)
        a,b = 1-width,width
        if (directional_derivative_bounds(first,direction,a,1.)[0]>0
                and directional_derivative_bounds(second,direction,0.,b)[0]>0):
            break
    else:
        raise ValueError('curve adjacency UNVERIFIED: no strictly monotone join neighborhood')
    checked = 0
    for left,right in (((0.,a),(0.,1.)),((a,1.),(b,1.))):
        if left[0]==left[1] or right[0]==right[1]:continue
        if checked>=max_boxes:
            raise ValueError('curve adjacency UNVERIFIED: max_boxes reached')
        report = certify_curve_separation(first,second,max_boxes=max_boxes-checked,
                                          first_interval=left,second_interval=right)
        checked += report['boxes_checked']
    return dict(join=join,join_tolerance_m=position_tolerance_m,
                first_join_interval=(a,1.),second_join_interval=(0.,b),boxes_checked=checked)
