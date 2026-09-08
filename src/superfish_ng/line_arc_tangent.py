# SPDX-License-Identifier: Apache-2.0
"""Fixed supporting-line contact with a finite conic arc; no tolerance snapping."""
from dataclasses import replace
from fractions import Fraction as F
import math
from .arc_tangents import _positive
from .conics import LineSegment, EllipseArc, check_curve_join, curve_to_dict, curve_from_dict
from .conic_tangents import _central
from .contact_enclosures import _local_contact_box
from .certified_arcs import _arc_membership, _parameter_fraction_enclosure, transcendental_interval, DEFAULT_ENDPOINT_WIDTH
from .certified_construction import _endpoint_box, _distance_bound


def line_arc_tangent_candidates(line, arc, *, line_first, allow_extension, position_tolerance_m,
                                angle_tolerance_rad, endpoint_width=DEFAULT_ENDPOINT_WIDTH,
                                max_series_terms=96, fraction_width=F(1,2**32), max_fraction_steps=64):
    """Assess the one possible finite contact of a specified supporting line.

    Tangency is exact in the binary-coefficient model: w²=n Q n. A nearby line
    is NOT_TANGENT, even if positional tolerances would permit snapping it.
    Extension and retained ends follow the explicit line_first/allow_extension.
    """
    if not isinstance(line,LineSegment) or type(line_first) is not bool or type(allow_extension) is not bool:
        raise ValueError('line must be LineSegment; line_first and allow_extension must be explicit booleans')
    _positive(position_tolerance_m,'position_tolerance_m')
    _positive(angle_tolerance_rad,'angle_tolerance_rad',upper=math.pi/2)
    transcendental_interval('sin',0,endpoint_width=endpoint_width,max_terms=max_series_terms)
    if type(fraction_width) not in (int,float,F) or not 0 < fraction_width < 1 or type(max_fraction_steps) is not int or max_fraction_steps < 1:
        raise ValueError('fraction_width must be between zero and one; max_fraction_steps must be a positive integer')
    center,Q=_central(arc)
    start,end=tuple(map(F,line.start_zr_m)),tuple(map(F,line.end_zr_m))
    d=tuple(end[i]-start[i] for i in range(2));n=(-d[1],d[0])
    w=sum(n[i]*(start[i]-center[i]) for i in range(2))
    Qn=tuple(sum(Q[i][j]*n[j] for j in range(2)) for i in range(2))
    square=sum(n[i]*Qn[i] for i in range(2))
    report=dict(status='PASS',candidates=[],excluded=[],unresolved=[],
                contact_status='NOT_TANGENT',tangency_equation_residual=w*w-square,
                line_first=line_first,allow_extension=allow_extension,
                arc_filter_status='CERTIFIED_FIXED_LINE_CONTACT',
                scope='exact binary fixed-line contact and arc membership; bounded trim position; floating G1; no line fitting')
    if w*w != square:
        return report
    if w == 0:
        report['contact_status']='AT_INFINITY'
        return report
    point=tuple(center[i]+Qn[i]/w for i in range(2));box=tuple((x,x) for x in point)
    parameter=sum((point[i]-start[i])*d[i] for i in range(2))/sum(x*x for x in d)
    record=dict(exact_contact_zr_m=point,line_parameter=parameter,line_extended=not 0 <= parameter <= 1)
    report['contact_status']='FINITE_TANGENT'
    if record['line_extended'] and not allow_extension:
        report['excluded'].append(dict(record,reason='contact outside finite line; extension was not permitted'))
        return report
    try:
        local=_local_contact_box(arc,box)
        controls=dict(endpoint_width=endpoint_width,max_series_terms=max_series_terms)
        membership=_arc_membership(arc,local,**controls)
        record.update(local_contact_box=local,arc_membership=membership)
        if membership['status']=='EXTERIOR':
            report['excluded'].append(dict(record,reason='contact outside specified finite arc or branch'))
            return report
        if membership['status']=='UNVERIFIED':
            raise ValueError('finite arc membership is UNVERIFIED')
        fraction=_parameter_fraction_enclosure(arc,local,fraction_width=fraction_width,
                                               max_fraction_steps=max_fraction_steps,**controls)
        record['parameter_fraction']=fraction
        if fraction['status']!='PASS':raise ValueError('arc fraction enclosure is UNVERIFIED')
        p=tuple(map(float,point))
        fixed=line.start_zr_m if line_first else line.end_zr_m
        positions=(fixed,p) if line_first else (p,fixed)
        distance=math.dist(*positions)
        if not math.isfinite(distance):raise ValueError('retained line length exceeds output range')
        record.update(contacts_zr_m=positions,contact_roles=('line_start','conic_contact') if line_first else ('conic_contact','line_end'),
                      contact_distance_m=distance)
        if (line_first and parameter==0) or (not line_first and parameter==1):
            record.update(connection_direction='EMPTY_LINE',construction_reason='retained line would be empty')
        elif (line_first and parameter<0) or (not line_first and parameter>1):
            record.update(connection_direction='OPPOSED',construction_reason='extension would reverse the directed line')
        elif membership['status']==('END' if line_first else 'START'):
            record.update(connection_direction='EMPTY_ARC',construction_reason='retained arc would be empty')
        else:
            lo,hi=fraction['interval'];f=float((lo+hi)/2)
            if not lo<=F(f)<=hi:raise ValueError('fraction midpoint is not representable within the certified interval')
            if membership['status']==('START' if line_first else 'END'):
                trimmed=arc
            elif isinstance(arc,EllipseArc):
                trimmed=(replace(arc,start_rad=float(F(arc.start_rad)+F(arc.sweep_rad)*F(f)),
                                  sweep_rad=float(F(arc.sweep_rad)*(1-F(f)))) if line_first else
                         replace(arc,sweep_rad=float(F(arc.sweep_rad)*F(f))))
            else:
                contact_parameter=float(F(arc.start_parameter)+(F(arc.end_parameter)-F(arc.start_parameter))*F(f))
                trimmed=replace(arc,**({'start_parameter':contact_parameter} if line_first else {'end_parameter':contact_parameter}))
            segment=LineSegment(*positions)
            endpoint_controls=dict(endpoint_width=endpoint_width,max_terms=max_series_terms)
            trim_box=_endpoint_box(trimmed,not line_first,endpoint_controls)
            line_box=tuple((F(x),F(x)) for x in p)
            error_bounds=(_distance_bound(line_box,box),_distance_bound(trim_box,box))
            outer_bound=_distance_bound(_endpoint_box(arc,line_first,endpoint_controls),
                                        _endpoint_box(trimmed,line_first,endpoint_controls))
            if any(F(x)>F(position_tolerance_m) for x in (*error_bounds,outer_bound)):
                raise ValueError('line/arc trimmed endpoint error bound exceeds position_tolerance_m')
            tangent=trimmed.evaluate(0. if line_first else 1.)['tangent_zr'];direction=segment.evaluate(.5)['tangent_zr']
            if sum(float(tangent[i])*float(direction[i]) for i in range(2))<=0:
                record.update(connection_direction='OPPOSED',construction_reason='line and arc directions oppose')
            else:
                curves=(segment,trimmed) if line_first else (trimmed,segment)
                join=check_curve_join(*curves,position_tolerance_m=position_tolerance_m,
                                      angle_tolerance_rad=angle_tolerance_rad,require_tangent=True)
                record.update(connection_direction='FORWARD',trimmed_curves=[curve_to_dict(c) for c in curves],
                              trim_contact_error_bounds_m=error_bounds if line_first else error_bounds[::-1],
                              retained_outer_endpoint_error_bound_m=outer_bound,joins=[join],contact_fraction=f)
        report['candidates'].append(record)
    except (ValueError,OverflowError) as error:
        report['status']='UNVERIFIED'
        report['unresolved'].append(dict(record,reason=str(error)))
    return report


def connect_line_arc(line,arc,*,candidate_index=0,**controls):
    if type(candidate_index) is not int or candidate_index!=0:
        raise ValueError('fixed-line construction requires explicit candidate 0')
    report=line_arc_tangent_candidates(line,arc,**controls)
    if report['status']!='PASS' or not report['candidates']:
        raise ValueError('no verified finite line/arc tangent; inspect contact and extension diagnostics')
    selected=report['candidates'][0]
    if selected['connection_direction']!='FORWARD':
        raise ValueError(selected.get('construction_reason','line/arc construction is not forward'))
    return dict(curves=tuple(curve_from_dict(row) for row in selected['trimmed_curves']),
                selected_candidate=selected,joins=selected['joins'],enumeration=report)
