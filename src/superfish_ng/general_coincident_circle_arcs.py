# SPDX-License-Identifier: Apache-2.0
"""General binary rotations and algebraic radii for coincident circular offsets."""
from fractions import Fraction as F
from .conics import EllipseArc, rotation_cos_sin
from .coincident_circle_arcs import pi_bounds


def _sign(value):return (value>0)-(value<0)


def _signed_radius_sign(square, distance):
    return 1 if distance<0 else _sign(square-distance*distance)


def _equal_support_radii(a,b,first_distance,second_distance):
    """Prove |sqrt(a)-d1|=|sqrt(b)-d2| without rounding either square root."""
    if a<=0 or b<=0:raise ValueError('source squared radii must be positive')
    signs=(_signed_radius_sign(a,first_distance),_signed_radius_sign(b,second_distance))
    if 0 in signs:return None
    orientation=signs[0]*signs[1];difference=first_distance-orientation*second_distance
    remainder=a+b-difference*difference
    if difference==0:
        equal=orientation==1 and a==b
    else:
        expected_sign=_sign(a-b) if orientation==1 else 1
        equal=(_sign(difference)==expected_sign and _sign(remainder)==orientation
               and remainder*remainder==4*a*b)
    if not equal:return None
    return dict(source_radius_squares=(a,b),oriented_distances=(first_distance,second_distance),
                signed_radius_signs=signs,relative_sign=orientation,root_difference=difference,
                squared_identity_remainder=remainder)


def _atan_series(value,width,max_terms):
    if value==0:return F(0),F(0)
    power=value;total=F(0)
    for index in range(max_terms):
        total+=(-1 if index%2 else 1)*power/(2*index+1)
        following=power*value*value/(2*index+3)
        bounds=(total,total+following) if index%2 else (total-following,total)
        if following<=width:return bounds
        power*=value*value
    raise ValueError('general-circle relative angle series budget exhausted')


def _atan_small(value,width,max_terms):
    if not 0<=value<=1:raise ValueError('reduced arctangent argument must lie in [0,1]')
    if value<=F(1,2):return _atan_series(value,width,max_terms)
    left=_atan_series(F(1,2),width/2,max_terms)
    right=_atan_series((value-F(1,2))/(1+value/2),width/2,max_terms)
    return left[0]+right[0],left[1]+right[1]


def _scale(value,bounds):return tuple(sorted(value*x for x in bounds))


def _relative_phase(x,y,width,max_terms):
    """Return a rational pi coefficient plus a remainder enclosing atan2(y,x)."""
    if x==0:
        if y==0:raise ValueError('relative rotation vector must be nonzero')
        return F(_sign(y),2),(F(0),F(0))
    if y==0:return F(0 if x>0 else 1),(F(0),F(0))
    ratio=abs(y/x)
    if ratio<=1:coefficient=F(0);remainder=_atan_small(ratio,width,max_terms)
    else:coefficient=F(1,2);remainder=_scale(-1,_atan_small(1/ratio,width,max_terms))
    if x<0:coefficient=1-coefficient;remainder=_scale(-1,remainder)
    if y<0:coefficient=-coefficient;remainder=_scale(-1,remainder)
    return coefficient,remainder


def classify_general_coincident_arcs(curves,distances,domains,*,endpoint_width,max_series_terms):
    """Prove finite intersections after the caller has strictly validated inputs.

    None means this is not a pair of provably coincident noncollapsed circular
    offsets. It does not mean disjointness or replace a general crossing search.
    """
    if not all(isinstance(c,EllipseArc) and c.semiaxes_m[0]==c.semiaxes_m[1] for c in curves):return None
    if curves[0].center_zr_m!=curves[1].center_zr_m:return None
    rotations=[tuple(map(F,rotation_cos_sin(c.rotation_rad))) for c in curves]
    squares=[F(c.semiaxes_m[0])**2*sum(x*x for x in rotation) for c,rotation in zip(curves,rotations)]
    oriented=[(1 if c.sweep_rad>0 else -1)*F(distance) for c,distance in zip(curves,distances)]
    proof=_equal_support_radii(*squares,*oriented)
    if proof is None:return None
    proof['center_zr_m']=tuple(map(F,curves[0].center_zr_m));proof['binary_rotations']=rotations
    sign=proof['relative_sign'];a,b=rotations
    x=sign*sum(u*v for u,v in zip(a,b));y=sign*(a[0]*b[1]-a[1]*b[0])
    ranges=[tuple(sorted(F(c.start_rad)+F(c.sweep_rad)*F(t) for t in domain)) for c,domain in zip(curves,domains)]
    first,second=ranges
    try:
        width=F(endpoint_width)/64
        pi=pi_bounds(width,max_series_terms)
        coefficient,remainder=_relative_phase(x,y,width,max_series_terms)
    except ValueError as error:
        return dict(classification='COINCIDENT_SUPPORTING_CIRCLES',evidence=proof,reason=str(error))
    phase_pi=_scale(coefficient,pi);phase=tuple(a+b for a,b in zip(phase_pi,remainder))
    difference=(first[0]-second[1]-phase[1],first[1]-second[0]-phase[0])
    periods=[v/(2*p) for v in difference for p in pi]
    lower,upper=min(periods),max(periods)
    first_period=-((-lower.numerator)//lower.denominator);last_period=upper.numerator//upper.denominator
    records=[]
    for period in range(first_period,last_period+1):
        pi_coefficient=coefficient+2*period
        translated_pi=_scale(pi_coefficient,pi);shift=tuple(a+b for a,b in zip(translated_pi,remainder))
        low=(max(first[0],second[0]+shift[0]),max(first[0],second[0]+shift[1]))
        high=(min(first[1],second[1]+shift[0]),min(first[1],second[1]+shift[1]))
        if low[0]>high[1]:kind='DISJOINT'
        elif low[1]<high[0]:kind='POSITIVE_INTERVAL'
        elif pi_coefficient==0 and remainder==(0,0) and low[0]==low[1]==high[0]==high[1]:kind='SHARED_ENDPOINT'
        else:kind='UNVERIFIED'
        records.append(dict(period=period,pi_coefficient=pi_coefficient,shift_bounds=shift,
                            overlap_start_bounds=low,overlap_end_bounds=high,classification=kind))
    positive=sum(x['classification']=='POSITIVE_INTERVAL' for x in records)
    endpoints=sum(x['classification']=='SHARED_ENDPOINT' for x in records)
    unknown=any(x['classification']=='UNVERIFIED' for x in records)
    if positive:classification,centers,infinite='INFINITE_PARAMETER_PAIRS',None,True
    elif unknown:classification,centers,infinite='COINCIDENT_SUPPORTING_CIRCLES',None,None
    elif endpoints:classification,centers,infinite='SHARED_PARAMETER_ENDPOINT',endpoints,False
    else:classification,centers,infinite='DISJOINT',0,False
    proof.update(angular_ranges=ranges,relative_rotation_vector=(x,y),pi_bounds=pi,
                 phase_pi_coefficient=coefficient,phase_remainder_bounds=remainder,period_range=(first_period,last_period),
                 periodic_intersections=records,positive_components=positive,isolated_endpoints=endpoints)
    return dict(classification=classification,complete=not unknown,centers=centers,infinite=infinite,evidence=proof,
                reason='all possible periodic interval intersections classified' if not unknown else 'some finite interval endpoints remain unresolved')
