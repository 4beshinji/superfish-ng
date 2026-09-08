# SPDX-License-Identifier: Apache-2.0
"""Rational enclosures of conic normal offsets for fillet center searches.

Stored parameters and binary rotation coefficients define the mathematical
curve. Bounds do not assert an intersection or a cusp exists, nor include the
roundoff of a separately evaluated floating-point geometry primitive.
"""
from fractions import Fraction as F
from .conics import LineSegment,EllipseArc,HyperbolaArc,rotation_cos_sin
from .certified_arcs import _number,_multiply,transcendental_interval,DEFAULT_ENDPOINT_WIDTH
from .contact_enclosures import _interval_add as add,_interval_divide as divide
from .rational_bounds import _sqrt_bound


def scale(a,value):
    return tuple(sorted(value*x for x in a))


def square(a):
    return (F(0) if a[0]<=0<=a[1] else min(x*x for x in a),max(x*x for x in a))


def root(a):
    return F(_sqrt_bound(a[0],False)),F(_sqrt_bound(a[1],True))


def _trig(kind,lo,hi,controls):
    # |sin'|, |cos'| <= 1, so a midpoint enclosure plus interval radius is valid.
    a,b=transcendental_interval(kind,(lo+hi)/2,**controls)
    radius=(hi-lo)/2
    return max(F(-1),a-radius),min(F(1),b+radius)


def normal_offset_bounds(curve,first=0.,last=1.,*,distance_m,
                         endpoint_width=DEFAULT_ENDPOINT_WIDTH,max_series_terms=96):
    """Bound x+d*left(T), its fraction derivative, and 1-d*signed_curvature.

    Positive d is to the left of the directed arc. A factor interval containing
    zero is unresolved, even if all sampled points would be regular.
    """
    if not isinstance(curve,(LineSegment,EllipseArc,HyperbolaArc)):
        raise ValueError('normal offsets require a line, ellipse or hyperbola arc')
    first,last=_number(first,'first'),_number(last,'last')
    distance=_number(distance_m,'distance_m')
    if first>last or not isinstance(curve,LineSegment) and not 0<=first<=last<=1:
        raise ValueError('offset interval requires ordered endpoints; conic fractions must be in [0,1]')
    controls=dict(endpoint_width=endpoint_width,max_terms=max_series_terms)
    transcendental_interval('sin',0,**controls)  # Validate even in exact special cases.
    if isinstance(curve,LineSegment):
        start=tuple(map(F,curve.start_zr_m))
        delta=tuple(F(curve.end_zr_m[i])-start[i] for i in range(2))
        squared=sum(x*x for x in delta);length=root((squared,squared))
        if length[0]<=0:raise ValueError('positive line length is below representable bound')
        normal=(divide((-delta[1],)*2,length),divide((delta[0],)*2,length))
        box=tuple(add(add((x,x),scale((first,last),v)),scale(n,distance)) for x,v,n in zip(start,delta,normal))
        return dict(interval=(first,last),center_box_zr_m=box,derivative_box_zr_m=tuple((x,x) for x in delta),
                    signed_curvature_interval_per_m=(F(0),F(0)),speed_factor_interval=(F(1),F(1)),regularity='FORWARD',
                    scope='exact binary supporting line and signed normal offset; rational enclosure')
    a,b=map(F,curve.semiaxes_m);c,s=map(F,rotation_cos_sin(curve.rotation_rad))
    determinant=c*c+s*s
    if isinstance(curve,EllipseArc):
        start,span=F(curve.start_rad),F(curve.sweep_rad)
    else:
        start,span=F(curve.start_parameter),F(curve.end_parameter)-F(curve.start_parameter)
    low,high=sorted((start+span*first,start+span*last))
    direction=1 if span>0 else -1
    if isinstance(curve,EllipseArc):
        sn,cs=_trig('sin',low,high,controls),_trig('cos',low,high,controls)
        local=(scale(cs,a),scale(sn,b));derivative=(scale(sn,-a),scale(cs,b))
        speed_squared=add((b*b,b*b),scale(square(sn),a*a-b*b))
        speed_squared=(max(min(a*a,b*b),speed_squared[0]),min(max(a*a,b*b),speed_squared[1]))
        curvature_numerator=direction*a*b*determinant
    else:
        left=transcendental_interval('sinh',low,**controls)
        right=transcendental_interval('sinh',high,**controls)
        sn=(left[0],right[1]);cs=root(add((F(1),F(1)),square(sn)))
        local=(scale(cs,curve.branch*a),scale(sn,b))
        derivative=(scale(sn,curve.branch*a),scale(cs,b))
        speed_squared=add((b*b,b*b),scale(square(sn),a*a+b*b))
        curvature_numerator=-direction*curve.branch*a*b*determinant
    speed_squared=scale(speed_squared,determinant)
    speed=root(speed_squared)
    if speed[0]<=0:raise ValueError('positive source speed is below representable bound; rescale geometry')
    curvature=divide((curvature_numerator,curvature_numerator),_multiply(speed_squared,speed))
    factor=add((F(1),F(1)),scale(curvature,-distance))

    def rotate(vector):
        return add(scale(vector[0],c),scale(vector[1],-s)),add(scale(vector[0],s),scale(vector[1],c))

    displacement=rotate(local);parameter_derivative=rotate(derivative)
    normal=(scale(divide(parameter_derivative[1],speed),-direction),
            scale(divide(parameter_derivative[0],speed),direction))
    offset=tuple(add(x,scale(n,distance)) for x,n in zip(displacement,normal))
    is_circle=isinstance(curve,EllipseArc) and a==b
    if is_circle:
        # Constant curvature permits correlated cancellation, including a circle
        # offset by exactly its radius collapsing to its center.
        offset=tuple(_multiply(factor,x) for x in displacement)
    center=tuple(add((F(z),F(z)),x) for z,x in zip(curve.center_zr_m,offset))
    derivative_box=tuple(_multiply(scale(x,span),factor) for x in parameter_derivative)
    regularity=('COLLAPSED' if is_circle and factor==(0,0) else
                'FORWARD' if factor[0]>0 else 'REVERSED' if factor[1]<0 else 'UNVERIFIED')
    return dict(interval=(first,last),center_box_zr_m=center,derivative_box_zr_m=derivative_box,
                signed_curvature_interval_per_m=curvature,speed_factor_interval=factor,
                regularity=regularity,
                scope='exact binary-parameter conic and normal offset; rational enclosures; no intersection/existence or floating-output certificate')


def partition_normal_offset(curve,*,distance_m,fraction_width=F(1,2**20),max_boxes=10000,
                            endpoint_width=DEFAULT_ENDPOINT_WIDTH,max_series_terms=96):
    """Cover the whole finite arc by regular, collapsed and unresolved intervals.

    Exhausted budgets keep every pending interval. Unknown intervals are not
    excluded and do not prove a cusp. This is preprocessing, not root isolation.
    """
    width=_number(fraction_width,'fraction_width')
    if not 0<width<1 or type(max_boxes) is not int or max_boxes<1:
        raise ValueError('fraction_width must be in (0,1); max_boxes must be a positive integer')
    if not isinstance(curve,(EllipseArc,HyperbolaArc)):
        raise ValueError('normal offsets require an ellipse or hyperbola arc')
    _number(distance_m,'distance_m')
    transcendental_interval('sin',0,endpoint_width=endpoint_width,max_terms=max_series_terms)
    pending=[(F(0),F(1))];regular=[];singular=[];unresolved=[];checked=0
    while pending:
        interval=pending.pop()
        if checked>=max_boxes:
            unresolved.extend(dict(interval=x,bounds=None,reason='subdivision budget exhausted') for x in [interval,*pending])
            break
        checked+=1
        try:
            bounds=normal_offset_bounds(curve,*interval,distance_m=distance_m,
                                        endpoint_width=endpoint_width,max_series_terms=max_series_terms)
        except ValueError as error:
            unresolved.append(dict(interval=interval,bounds=None,reason=str(error)))
            continue
        row=dict(interval=interval,bounds=bounds)
        if bounds['regularity'] in ('FORWARD','REVERSED'):regular.append(row)
        elif bounds['regularity']=='COLLAPSED':singular.append(row)
        elif interval[1]-interval[0]<=width:
            unresolved.append(dict(row,reason='speed factor contains zero at requested fraction width'))
        else:
            middle=sum(interval)/2
            pending.extend(((middle,interval[1]),(interval[0],middle)))
    return dict(status='UNVERIFIED' if unresolved else 'SINGULAR' if singular else 'PASS',
                regular=regular,singular=singular,unresolved=unresolved,boxes_checked=checked,
                scope='complete finite parameter cover; regularity bounds only, not fillet candidate enumeration')
