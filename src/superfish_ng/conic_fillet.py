# SPDX-License-Identifier: Apache-2.0
"""Explicit conic-arc fillets from certified normal-offset intersections."""
from dataclasses import replace
from fractions import Fraction as F
import math
from .arc_tangents import _positive
from .conics import EllipseArc,check_curve_join,curve_to_dict,curve_from_dict
from .normal_offsets import normal_offset_bounds
from .offset_intersections import intersect_normal_offsets
from .certified_construction import _endpoint_box,_distance_bound
from .certified_arcs import DEFAULT_ENDPOINT_WIDTH


def _trim(curve,fraction,keep_start):
    if isinstance(curve,EllipseArc):
        if keep_start:return replace(curve,sweep_rad=float(F(curve.sweep_rad)*F(fraction)))
        return replace(curve,start_rad=float(F(curve.start_rad)+F(curve.sweep_rad)*F(fraction)),
                       sweep_rad=float(F(curve.sweep_rad)*(1-F(fraction))))
    parameter=float(F(curve.start_parameter)+(F(curve.end_parameter)-F(curve.start_parameter))*F(fraction))
    return replace(curve,**({'end_parameter':parameter} if keep_start else {'start_parameter':parameter}))


def conic_fillet_candidates(first,second,*,radius_m,turn_direction,max_sweep_rad,
                            position_tolerance_m,angle_tolerance_rad,
                            fraction_width=F(1,2**40),max_boxes=10000,precision_bits=96,
                            endpoint_width=DEFAULT_ENDPOINT_WIDTH,max_series_terms=96):
    """Enumerate one explicitly selected radius/turn family on finite arcs.

    Positive turn is counterclockwise. Both contacts must have the same signed
    left-normal distance to preserve directed G1 joins. Root search completeness
    is separate from each candidate's numerical construction eligibility.
    """
    _positive(radius_m,'radius_m');_positive(position_tolerance_m,'position_tolerance_m')
    _positive(angle_tolerance_rad,'angle_tolerance_rad',upper=math.pi/2)
    _positive(max_sweep_rad,'max_sweep_rad')
    if max_sweep_rad>2*math.pi:raise ValueError('max_sweep_rad must be at most 2*pi')
    if type(turn_direction) is not int or turn_direction not in (-1,1):
        raise ValueError('turn_direction must be explicit integer -1 or 1')
    distance=turn_direction*radius_m
    search=intersect_normal_offsets(first,second,first_distance_m=distance,second_distance_m=distance,
                                    fraction_width=fraction_width,max_boxes=max_boxes,precision_bits=precision_bits,
                                    endpoint_width=endpoint_width,max_series_terms=max_series_terms)
    endpoint_controls=dict(endpoint_width=endpoint_width,max_terms=max_series_terms)
    candidates=[];unresolved=list(search['unresolved'])
    for index,root in enumerate(search['roots']):
        record=dict(root=root,connection_direction='UNVERIFIED',contacts_zr_m=(),contact_distance_m=None)
        try:
            fractions=tuple(float(sum(interval)/2) for interval in root['parameter_box'])
            if not all(0<f<1 for f in fractions):raise ValueError('retained arc is empty or contact fraction is not representable in its interior')
            left,right=_trim(first,fractions[0],True),_trim(second,fractions[1],False)
            center=tuple(float(sum(interval)/2) for interval in root['center_box_zr_m'])
            p,q=[tuple(map(float,c.evaluate(f)['points_zr_m'])) for c,f in ((left,1.),(right,0.))]
            if not all(math.isfinite(x) for x in center):raise ValueError('fillet center is not representable')
            length=math.dist(p,q)
            if not math.isfinite(length):raise ValueError('contact distance exceeds output range')
            record.update(contacts_zr_m=(p,q),contact_distance_m=length,center_zr_m=center,contact_fractions=fractions,
                          fraction_midpoints_inside_root_box=tuple(lo<=F(f)<=hi for f,(lo,hi) in zip(fractions,root['parameter_box'])))
            if p==q or p==center or q==center:
                record.update(connection_direction='ZERO_LENGTH',construction_reason='fillet contacts or radial directions collapse at output precision')
                candidates.append(record);continue
            start=math.atan2(p[1]-center[1],p[0]-center[0]);end=math.atan2(q[1]-center[1],q[0]-center[0])
            sweep=turn_direction*((turn_direction*(end-start))%(2*math.pi))
            if sweep==0:raise ValueError('fillet sweep is zero at output precision')
            arc_length=radius_m*abs(sweep)
            if not math.isfinite(arc_length):raise ValueError('fillet arc length exceeds output range')
            record.update(fillet_sweep_rad=sweep,fillet_arc_length_m=arc_length)
            if abs(sweep)>max_sweep_rad:
                record.update(connection_direction='SWEEP_LIMIT',construction_reason='directed fillet sweep exceeds explicit max_sweep_rad',fillet_sweep_rad=sweep)
                candidates.append(record);continue
            fillet=EllipseArc(center,(radius_m,radius_m),start,sweep)
            def overlaps(fillet):
                for a,b in ((left,fillet),(fillet,right)):
                    x,y=a.evaluate(1.),b.evaluate(0.)
                    gap=y['points_zr_m']-x['points_zr_m']
                    direction=x['tangent_zr']+y['tangent_zr']
                    if sum(float(gap[i])*float(direction[i]) for i in range(2))<0:return True
                return False
            inset=0.
            if overlaps(fillet):
                # Preserve the radius and center; leave a directed sub-tolerance
                # gap instead of permitting a backwards-overlapping float join.
                inset=min(position_tolerance_m/(16*radius_m),angle_tolerance_rad/16,abs(sweep)/16)
                fillet=replace(fillet,start_rad=start+turn_direction*inset,
                               sweep_rad=sweep-2*turn_direction*inset)
                if overlaps(fillet):raise ValueError('fillet endpoint inset cannot separate rounded joins within output precision')
            record.update(fillet_endpoint_inset_rad=inset,requested_fillet_sweep_rad=sweep)
            sweep=fillet.sweep_rad;arc_length=radius_m*abs(sweep)
            contact_boxes=[normal_offset_bounds(curve,*interval,distance_m=0.,endpoint_width=endpoint_width,
                                                 max_series_terms=max_series_terms)['center_box_zr_m']
                           for curve,interval in zip((first,second),root['parameter_box'])]
            trim_boxes=(_endpoint_box(left,True,endpoint_controls),_endpoint_box(right,False,endpoint_controls))
            fillet_boxes=(_endpoint_box(fillet,False,endpoint_controls),_endpoint_box(fillet,True,endpoint_controls))
            trim_errors=tuple(_distance_bound(a,b) for a,b in zip(trim_boxes,contact_boxes))
            fillet_errors=tuple(_distance_bound(a,b) for a,b in zip(fillet_boxes,contact_boxes))
            center_error=_distance_bound(tuple((F(x),F(x)) for x in center),root['center_box_zr_m'])
            outer_errors=tuple(_distance_bound(_endpoint_box(a,end,endpoint_controls),_endpoint_box(b,end,endpoint_controls))
                               for a,b,end in ((first,left,False),(second,right,True)))
            record.update(contact_boxes_zr_m=contact_boxes,trim_contact_error_bounds_m=trim_errors,
                          fillet_contact_error_bounds_m=fillet_errors,center_error_bound_m=center_error,
                          retained_outer_endpoint_error_bounds_m=outer_errors)
            if any(F(x)>F(position_tolerance_m) for x in (*trim_errors,*fillet_errors,center_error,*outer_errors)):
                raise ValueError('fillet/trim/center/outer endpoint error bound exceeds position_tolerance_m')
            curves=(left,fillet,right)
            joins=[check_curve_join(a,b,position_tolerance_m=position_tolerance_m,
                                    angle_tolerance_rad=angle_tolerance_rad,require_tangent=True) for a,b in zip(curves,curves[1:])]
            record.update(connection_direction='FORWARD',trimmed_curves=[curve_to_dict(c) for c in curves],
                          fillet_sweep_rad=sweep,fillet_arc_length_m=arc_length,joins=joins)
        except (ValueError,OverflowError) as error:
            record.update(connection_direction='UNVERIFIED',construction_reason=str(error))
            unresolved.append(dict(stage='fillet_trim',candidate_index=index,reason=str(error)))
        candidates.append(record)
    return dict(status=search['status'],candidates=candidates,unresolved=unresolved,excluded=[],certificate=search,
                radius_m=radius_m,turn_direction=turn_direction,max_sweep_rad=max_sweep_rad,
                arc_filter_status='CERTIFIED_CONIC_FILLET_CONTACTS',
                scope='certified finite offset crossings and bounded output contact errors; specified radius/turn/sweep; floating G1; closed contour checked separately')


def connect_conic_fillet(first,second,*,candidate_index,**controls):
    if type(candidate_index) is not int or candidate_index<0:
        raise ValueError('candidate_index must be an explicit nonnegative integer')
    report=conic_fillet_candidates(first,second,**controls)
    if report['status']!='PASS':raise ValueError('conic fillet intersection search is UNVERIFIED; inspect unresolved regions')
    if candidate_index>=len(report['candidates']):raise ValueError('candidate_index is outside the conic fillet list')
    selected=report['candidates'][candidate_index]
    if selected['connection_direction']!='FORWARD':raise ValueError(selected.get('construction_reason','fillet is not usable'))
    return dict(curves=tuple(curve_from_dict(row) for row in selected['trimmed_curves']),
                selected_candidate=selected,joins=selected['joins'],enumeration=report)
