# SPDX-License-Identifier: Apache-2.0
"""Bounds on analytic PEC meridional curvature, separate from FEM accuracy."""
from fractions import Fraction as F
from .certified_arcs import _number,transcendental_interval,DEFAULT_ENDPOINT_WIDTH
from .conics import LineSegment,EllipseArc,HyperbolaArc,check_curve_join
from .normal_offsets import normal_offset_bounds


def _absolute(interval):
    a,b=interval
    return (F(0) if a<=0<=b else min(abs(a),abs(b))),max(abs(a),abs(b))


def certify_minimum_meridional_radius(curve,*,minimum_radius_m,max_boxes=4096,
                                      fraction_width=F(1,2**24),endpoint_width=DEFAULT_ENDPOINT_WIDTH,max_series_terms=96):
    minimum=_number(minimum_radius_m,'minimum_radius_m');width=_number(fraction_width,'fraction_width')
    if minimum<=0 or not 0<width<1:raise ValueError('minimum radius must be positive; fraction_width must be in (0,1)')
    if type(max_boxes) is not int or max_boxes<1:raise ValueError('max_boxes must be a positive integer')
    if not isinstance(curve,(LineSegment,EllipseArc,HyperbolaArc)):raise ValueError('radius constraint requires a supported primitive')
    transcendental_interval('sin',0,endpoint_width=endpoint_width,max_terms=max_series_terms)
    pending=[(F(0),F(1))];accepted=[];unknown=[];witness=None;checked=0;limit=1/minimum
    def curvature(interval):
        if isinstance(curve,LineSegment):return (F(0),F(0))
        return _absolute(normal_offset_bounds(curve,*interval,distance_m=0.,endpoint_width=endpoint_width,
                                             max_series_terms=max_series_terms)['signed_curvature_interval_per_m'])
    while pending:
        interval=pending.pop()
        if checked>=max_boxes:
            unknown.extend(dict(interval=x,reason='box budget exhausted') for x in (interval,*pending));break
        checked+=1
        try:
            bounds=curvature(interval)
            if bounds[1]<=limit:
                accepted.append(dict(interval=interval,absolute_curvature_interval_per_m=bounds));continue
            for t in (interval[0],sum(interval)/2,interval[1]):
                point=curvature((t,t))
                if point[0]>limit:
                    witness=dict(fraction=t,absolute_curvature_interval_per_m=point);break
            if witness is not None:break
            if interval[1]-interval[0]<=width:
                unknown.append(dict(interval=interval,reason='curvature bound straddles requested limit'));continue
            mid=sum(interval)/2;pending.extend(((mid,interval[1]),(interval[0],mid)))
        except ValueError as error:unknown.append(dict(interval=interval,reason=str(error)))
    return dict(status='FAIL' if witness else 'UNVERIFIED' if unknown else 'PASS',minimum_radius_m=minimum,
                maximum_curvature_per_m=limit,certified_intervals=accepted,unresolved=unknown,witness=witness,boxes_checked=checked,
                scope='rational bound on analytic meridional curvature over the full primitive when PASS; no azimuthal radius or FEM accuracy claim')


def contour_meridional_radius_report(curves,tags,*,minimum_radius_m,join_tolerance_m):
    rows=[]
    for i,(curve,tag) in enumerate(zip(curves,tags)):
        if tag!='pec':continue
        result=certify_minimum_meridional_radius(curve,minimum_radius_m=minimum_radius_m)
        rows.append(dict(primitive_index=i,**result))
        if result['status']!='PASS':return dict(status=result['status'],curves=rows,reason=f'PEC primitive {i} meridional curvature bound is {result["status"]}')
    for i in range(len(curves)):
        j=(i+1)%len(curves)
        if tags[i]==tags[j]=='pec':
            try:check_curve_join(curves[i],curves[j],position_tolerance_m=join_tolerance_m,angle_tolerance_rad=1e-8,require_tangent=True)
            except ValueError as error:return dict(status='FAIL',curves=rows,reason=f'PEC join {i}->{j} is not numerically G1: {error}')
    return dict(status='PASS',curves=rows,join_scope='PEC-PEC G1 checked numerically at 1e-8 rad; existing position tolerance; axis/symmetry joins excluded')
