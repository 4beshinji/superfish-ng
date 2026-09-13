# SPDX-License-Identifier: Apache-2.0
"""Finite same-conic offsets: equal parameters and all reflected self-contacts.

For a noncircular ellipse, equal-distance normal contacts have an axis-aligned
mid-angle. For one hyperbola branch their mid-parameter is zero. The elementary
distance/tangent elimination is documented in SAME_CONIC_OFFSET_SELF_INTERSECTIONS_PLAN.
"""
from fractions import Fraction as F
from math import isqrt
from .conics import EllipseArc,HyperbolaArc,rotation_cos_sin
from .coincident_circle_arcs import pi_bounds
from .certified_arcs import _arc_membership,transcendental_interval


def _scale(interval,value):return tuple(sorted(value*x for x in interval))


def _sqrt_interval(value,width):
    if value<0 or width<=0:raise ValueError('nonnegative radicand and positive enclosure width required')
    bits=max(0,width.denominator.bit_length()-width.numerator.bit_length()+1)
    denominator=2**bits;numerator=value.numerator*denominator*denominator
    lower=isqrt(numerator//value.denominator)
    upper=lower if lower*lower*value.denominator==numerator else lower+1
    return F(lower,denominator),F(upper,denominator)


def _diagonal(curves,domains,width,max_terms):
    ranges=[]
    for curve,domain in zip(curves,domains):
        if isinstance(curve,EllipseArc):start,span=F(curve.start_rad),F(curve.sweep_rad)
        else:start,span=F(curve.start_parameter),F(curve.end_parameter)-F(curve.start_parameter)
        ranges.append(tuple(sorted(start+span*F(t) for t in domain)))
    first,second=ranges
    if isinstance(curves[0],HyperbolaArc):pi=None;first_period=last_period=0
    else:
        pi=pi_bounds(width/64,max_terms)
        quotients=[value/(2*p) for value in (first[0]-second[1],first[1]-second[0]) for p in pi]
        lower,upper=min(quotients),max(quotients)
        first_period=-((-lower.numerator)//lower.denominator);last_period=upper.numerator//upper.denominator
    records=[]
    for period in range(first_period,last_period+1):
        shift=(F(0),F(0)) if period==0 else _scale(pi,2*period)
        low=tuple(max(first[0],second[0]+x) for x in shift)
        high=tuple(min(first[1],second[1]+x) for x in shift)
        if low[0]>high[1]:kind='DISJOINT'
        elif low[1]<high[0]:kind='POSITIVE_INTERVAL'
        elif period==0 and low[0]==low[1]==high[0]==high[1]:kind='SHARED_ENDPOINT'
        else:kind='UNVERIFIED'
        records.append(dict(period=period,shift_bounds=shift,overlap_start_bounds=low,overlap_end_bounds=high,classification=kind))
    return dict(parameter_ranges=ranges,pi_bounds=pi,period_range=(first_period,last_period),periodic_intersections=records,
                complete=all(row['classification']!='UNVERIFIED' for row in records),
                positive_components=sum(row['classification']=='POSITIVE_INTERVAL' for row in records),
                shared_endpoints=[row['overlap_start_bounds'][0] for row in records if row['classification']=='SHARED_ENDPOINT'])


def _self_contacts(curve,distance,rotation_square,width):
    a,b=map(F,curve.semiaxes_m);candidates=[]
    def point(x,y):return (x,y)
    if isinstance(curve,EllipseArc):
        if distance<=0:return candidates
        difference=a*a-b*b
        q=(distance*distance*a*a/(rotation_square*b*b)-b*b)/difference
        if 0<q<=1:
            cosine=_sqrt_interval(1-q,width);sine=_sqrt_interval(q,width)
            for sign in ((1,) if q==1 else (-1,1)):
                candidates.append(dict(axis=0,coordinate_factor=sign*difference/a,coordinate_square=1-q,
                    parameter_square=q,contacts=(point(_scale(cosine,sign),_scale(sine,-1)),point(_scale(cosine,sign),sine))))
        q=(distance*distance*b*b/(rotation_square*a*a)-b*b)/difference
        if 0<=q<1:
            cosine=_sqrt_interval(1-q,width);sine=_sqrt_interval(q,width)
            for sign in ((1,) if q==0 else (-1,1)):
                candidates.append(dict(axis=1,coordinate_factor=-sign*difference/b,coordinate_square=q,
                    parameter_square=q,contacts=(point(_scale(cosine,-1),_scale(sine,sign)),point(cosine,_scale(sine,sign)))))
    else:
        if -curve.branch*distance<=0:return candidates
        total=a*a+b*b;q=(distance*distance*a*a/(rotation_square*b*b)-b*b)/total
        if q>0:
            cosine=_scale(_sqrt_interval(1+q,width),curve.branch);sine=_sqrt_interval(q,width)
            candidates.append(dict(axis=0,coordinate_factor=curve.branch*total/a,coordinate_square=1+q,
                                   parameter_square=q,contacts=(point(cosine,_scale(sine,-1)),point(cosine,sine))))
    return candidates


def _same_endpoint_as_contact(curve,parameter,contacts,controls):
    if isinstance(curve,EllipseArc):
        value=tuple(transcendental_interval(kind,parameter,**controls) for kind in ('cos','sin'))
    else:
        sine=transcendental_interval('sinh',parameter,**controls)
        low=F(0) if sine[0]<=0<=sine[1] else min(x*x for x in sine)
        high=max(x*x for x in sine);width=F(controls['endpoint_width'])/64
        cosine=(_sqrt_interval(1+low,width)[0],_sqrt_interval(1+high,width)[1])
        value=(_scale(cosine,curve.branch),sine)
    if any(all(a[0]==a[1]==b[0]==b[1] for a,b in zip(value,point)) for point in contacts):return True
    if all(any(a[1]<b[0] or b[1]<a[0] for a,b in zip(value,point)) for point in contacts):return False
    return None


def classify_same_conic_offsets(curves,distances,domains,*,endpoint_width,max_series_terms):
    """Caller validates types, finite controls and increasing fraction domains.

    None denotes a different support or orientation-adjusted distance, not
    disjointness. Self-contact positions are algebraic evidence, not fillets.
    """
    first,second=curves
    if type(first) is not type(second) or not isinstance(first,(EllipseArc,HyperbolaArc)):return None
    if isinstance(first,EllipseArc) and first.semiaxes_m[0]==first.semiaxes_m[1]:return None
    if first.center_zr_m!=second.center_zr_m or first.semiaxes_m!=second.semiaxes_m:return None
    if isinstance(first,HyperbolaArc) and first.branch!=second.branch:return None
    rotations=[tuple(map(F,rotation_cos_sin(curve.rotation_rad))) for curve in curves]
    if rotations[0]!=rotations[1]:return None
    spans=[F(curve.sweep_rad) if isinstance(curve,EllipseArc) else F(curve.end_parameter)-F(curve.start_parameter) for curve in curves]
    oriented=[(1 if span>0 else -1)*F(distance) for span,distance in zip(spans,distances)]
    if oriented[0]!=oriented[1]:return None
    width=F(endpoint_width);rotation_square=sum(value*value for value in rotations[0])
    diagonal=_diagonal(curves,domains,width,max_series_terms)
    candidates=_self_contacts(first,oriented[0],rotation_square,width/64)
    complete=diagonal['complete'];accepted=0
    controls=dict(endpoint_width=endpoint_width,max_terms=max_series_terms)
    for row in candidates:
        memberships=[]
        for curve,domain,span in zip(curves,domains,spans):
            start=F(curve.start_rad) if isinstance(curve,EllipseArc) else F(curve.start_parameter)
            endpoints=tuple(start+span*F(t) for t in domain)
            memberships.append([_arc_membership(curve,point,endpoint_width=endpoint_width,
                max_series_terms=max_series_terms,parameter_endpoints=endpoints) for point in row['contacts']])
        valid=('START','END','INTERIOR');directions=[]
        for left,right in ((0,1),(1,0)):
            statuses=memberships[0][left]['status'],memberships[1][right]['status']
            directions.append(False if 'EXTERIOR' in statuses else True if all(status in valid for status in statuses) else None)
        exists=True if True in directions else None if None in directions else False
        row.update(membership=memberships,parameter_pair_in_domain=exists)
        if exists is None:complete=False
        if exists:
            duplicates=[_same_endpoint_as_contact(first,parameter,row['contacts'],controls) for parameter in diagonal['shared_endpoints']]
            row['duplicates_shared_endpoint']=duplicates
            if None in duplicates:complete=False
            if all(value is False for value in duplicates):accepted+=1
    positive=diagonal['positive_components'];endpoints=len(diagonal['shared_endpoints'])
    if positive:classification,centers,infinite='INFINITE_PARAMETER_PAIRS',None,True
    elif not complete:classification,centers,infinite=('SHARED_PARAMETER_ENDPOINT' if endpoints else 'UNVERIFIED'),None,None
    elif accepted:classification,centers,infinite='FINITE_CENTERS',accepted+endpoints,False
    elif endpoints:classification,centers,infinite='SHARED_PARAMETER_ENDPOINT',endpoints,False
    else:classification,centers,infinite='DISJOINT',0,False
    return dict(classification=classification,complete=complete,centers=centers,infinite=infinite,
                evidence=dict(identity='same noncircular conic support and orientation-adjusted normal distance',
                              rotation=rotations[0],rotation_square=rotation_square,oriented_distance=oriented[0],
                              diagonal=diagonal,self_contacts=candidates,distinct_added_centers=accepted),
                reason='all equal-parameter and reflected-contact possibilities classified' if complete else 'some memberships or shared-endpoint identities remain unresolved')
