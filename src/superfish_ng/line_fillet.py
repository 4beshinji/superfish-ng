# SPDX-License-Identifier: Apache-2.0
"""Radius-specified minor circular fillet of two directed finite lines.

Supporting intersections use exact binary rational coordinates. Generated
contacts, finite extents and G1 joins are checked numerically, not certified
as interval enclosures. No conic-arc fillets or automatic radius changes.
"""
from fractions import Fraction as F
import math
from .arc_tangents import _positive
from .conics import LineSegment, EllipseArc, check_curve_join, curve_to_dict, curve_from_dict


def _cross(a,b):
    return a[0]*b[1]-a[1]*b[0]


def line_fillet_candidates(first,second,*,radius_m,allow_extension,position_tolerance_m,angle_tolerance_rad):
    """Return the unique directed minor fillet, or a reason it cannot be used."""
    if not all(isinstance(c,LineSegment) for c in (first,second)):
        raise ValueError('line fillet requires two directed LineSegment primitives')
    if type(allow_extension) is not bool:
        raise ValueError('allow_extension must be an explicit boolean')
    for name,value in (('radius_m',radius_m),('position_tolerance_m',position_tolerance_m)):
        _positive(value,name)
    _positive(angle_tolerance_rad,'angle_tolerance_rad',upper=math.pi/2)
    starts=[tuple(map(F,c.start_zr_m)) for c in (first,second)]
    deltas=[tuple(F(c.end_zr_m[i])-F(c.start_zr_m[i]) for i in range(2)) for c in (first,second)]
    determinant=_cross(*deltas)
    report=dict(status='PASS',candidates=[],excluded=[],unresolved=[],
                contact_status='PARALLEL_SUPPORTS' if determinant==0 else 'FINITE_INTERSECTION',
                arc_filter_status='NUMERICAL_LINE_FILLET',radius_m=radius_m,allow_extension=allow_extension,
                scope='directed minor line-line circle fillet; exact binary supporting intersection; numerical contacts/extents/G1; no interval certificate')
    if determinant==0:return report
    difference=tuple(starts[1][i]-starts[0][i] for i in range(2))
    t=_cross(difference,deltas[1])/determinant
    vertex=tuple(starts[0][i]+t*deltas[0][i] for i in range(2))
    record=dict(support_intersection_zr_m=vertex)
    try:
        u,v=[tuple(map(float,c.evaluate(.5)['tangent_zr'])) for c in (first,second)]
        # Compute the cross from the exact determinant to preserve a shallow turn.
        lengths=[math.hypot(*(float(x) for x in d)) for d in deltas]
        cross=float(determinant/F(lengths[0])/F(lengths[1]))
        dot=sum(u[i]*v[i] for i in range(2))
        if cross==0:raise ValueError('nonparallel turn is not representable; reduce dimension extremes')
        sweep=math.atan2(cross,dot)
        if not 0<abs(sweep)<math.pi:raise ValueError('minor turn is not representable away from straight/reversing limits')
        setback=radius_m*(abs(cross)/(1+dot) if dot>=0 else (1-dot)/abs(cross))
        origin=tuple(map(float,vertex));sign=1 if determinant>0 else -1
        p=tuple(origin[i]-setback*u[i] for i in range(2))
        q=tuple(origin[i]+setback*v[i] for i in range(2))
        center=(p[0]-sign*radius_m*u[1],p[1]+sign*radius_m*u[0])
        if not all(math.isfinite(x) for x in (*p,*q,*center,setback)):
            raise ValueError('fillet coordinates exceed floating-point range')
        parameters=[];support_errors=[]
        for point,start,d,length in zip((p,q),starts,deltas,lengths):
            relative=tuple(F(point[i])-start[i] for i in range(2))
            parameters.append(sum(relative[i]*d[i] for i in range(2))/sum(x*x for x in d))
            support_errors.append(float(abs(_cross(relative,d))/F(length)))
        chord_length=math.dist(p,q);arc_length=radius_m*abs(sweep)
        if not all(math.isfinite(x) for x in (*support_errors,chord_length,arc_length)):
            raise ValueError('fillet diagnostics exceed floating-point range')
        record.update(contacts_zr_m=(p,q),contact_distance_m=chord_length,
                      line_parameters=parameters,line_extended=[not 0<=x<=1 for x in parameters],
                      center_zr_m=center,setback_m=setback,sweep_rad=sweep,
                      support_distance_errors_m=support_errors)
        if parameters[0]<=0 or parameters[1]>=1:
            record.update(connection_direction='EMPTY_LINE',construction_reason='radius leaves an empty or reversed retained line')
        elif any(record['line_extended']) and not allow_extension:
            record.update(connection_direction='OUTSIDE_SEGMENT',construction_reason='contact outside a finite segment; extension was not permitted')
        else:
            if max(support_errors)>position_tolerance_m:
                raise ValueError('generated contact misses a supporting line beyond position_tolerance_m')
            arc=EllipseArc(center,(radius_m,radius_m),math.atan2(p[1]-center[1],p[0]-center[0]),sweep)
            curves=(LineSegment(first.start_zr_m,p),arc,LineSegment(q,second.end_zr_m))
            joins=[check_curve_join(a,b,position_tolerance_m=position_tolerance_m,
                                    angle_tolerance_rad=angle_tolerance_rad,require_tangent=True)
                   for a,b in zip(curves,curves[1:])]
            # Also check retained segment directions against the original lines.
            direction_errors=[]
            for original,trimmed in ((first,curves[0]),(second,curves[2])):
                a=original.evaluate(.5)['tangent_zr'];b=trimmed.evaluate(.5)['tangent_zr']
                angle=math.atan2(abs(_cross(a,b)),float(sum(a[i]*b[i] for i in range(2))))
                if angle>angle_tolerance_rad:raise ValueError('retained line direction exceeds angle_tolerance_rad')
                direction_errors.append(angle)
            record.update(connection_direction='FORWARD',trimmed_curves=[curve_to_dict(c) for c in curves],
                          joins=joins,retained_direction_errors_rad=direction_errors,
                          fillet_arc_length_m=arc_length)
        report['candidates'].append(record)
    except (ValueError,OverflowError,ZeroDivisionError) as error:
        report['status']='UNVERIFIED';report['unresolved'].append(dict(record,reason=str(error)))
    return report


def connect_line_fillet(first,second,*,candidate_index,**controls):
    """Explicitly select the unique forward minor fillet (index 0)."""
    if type(candidate_index) is not int or candidate_index!=0:
        raise ValueError('line fillet requires explicit candidate_index 0')
    report=line_fillet_candidates(first,second,**controls)
    if report['status']!='PASS' or not report['candidates']:
        raise ValueError('no verified minor line fillet; inspect intersection and numerical diagnostics')
    selected=report['candidates'][0]
    if selected['connection_direction']!='FORWARD':raise ValueError(selected['construction_reason'])
    return dict(curves=tuple(curve_from_dict(row) for row in selected['trimmed_curves']),
                selected_candidate=selected,joins=selected['joins'],enumeration=report)
