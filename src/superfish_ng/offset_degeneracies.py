# SPDX-License-Identifier: Apache-2.0
"""Exact special-case diagnostics for finite normal-offset degeneracies.

Witnesses and complete finite-domain classifications are explicitly distinct.
Unrecognized cases stay unknown; this module never replaces root isolation.
"""
from fractions import Fraction as F
from math import isqrt
from .conics import LineSegment, EllipseArc, HyperbolaArc, rotation_cos_sin
from .certified_arcs import _number, _arc_membership, transcendental_interval, DEFAULT_ENDPOINT_WIDTH


def _sqrt_exact(value):
    a,b=isqrt(value.numerator),isqrt(value.denominator)
    return F(a,b) if a*a==value.numerator and b*b==value.denominator else None


def _dot(a,b):return sum(x*y for x,y in zip(a,b))
def _sub(a,b):return tuple(x-y for x,y in zip(a,b))
def _cross(a,b):return a[0]*b[1]-a[1]*b[0]


def _parameters(curve):
    if isinstance(curve,EllipseArc):return F(curve.start_rad),F(curve.sweep_rad)
    return F(curve.start_parameter),F(curve.end_parameter)-F(curve.start_parameter)


def _circle(curve,distance):
    if not isinstance(curve,EllipseArc) or curve.semiaxes_m[0]!=curve.semiaxes_m[1]:return None
    c,s=map(F,rotation_cos_sin(curve.rotation_rad));det=c*c+s*s
    length=_sqrt_exact(det)
    if length is None:return None
    signed_radius=F(curve.semiaxes_m[0])*length-(1 if curve.sweep_rad>0 else -1)*distance
    return dict(center=tuple(map(F,curve.center_zr_m)),radius=abs(signed_radius),
                signed_radius=signed_radius,rotation=(c,s),rotation_length=length)


def _line(curve,distance):
    if not isinstance(curve,LineSegment):return None
    p=tuple(map(F,curve.start_zr_m));delta=_sub(tuple(map(F,curve.end_zr_m)),p)
    length=_sqrt_exact(_dot(delta,delta))
    if length is None and distance!=0:return None
    origin=p if distance==0 else (p[0]-distance*delta[1]/length,p[1]+distance*delta[0]/length)
    return dict(origin=origin,delta=delta)


def _report(classification,*,complete=False,centers=None,infinite=None,evidence=None,reason=''):
    return dict(status='UNVERIFIED' if classification=='UNVERIFIED' else 'CERTIFIED',
                classification=classification,finite_domain_complete=complete,
                finite_center_count=centers,infinite_parameter_pairs=infinite,
                evidence=evidence or {},reason=reason,
                scope='exact special-case offset diagnosis; witness is not exhaustive unless finite_domain_complete; no fillet selection or FEM accuracy claim')


def _membership(curve,model,point,interval,controls):
    if isinstance(curve,LineSegment):
        t=_dot(_sub(point,model['origin']),model['delta'])/_dot(model['delta'],model['delta'])
        lo,hi=interval
        return dict(status='EXTERIOR' if t<lo or t>hi else 'START' if t==lo else 'END' if t==hi else 'INTERIOR',fraction=t)
    if model['radius']==0:return dict(status='COLLAPSED',fraction_interval=interval)
    delta=_sub(point,model['center']);c,s=model['rotation']
    factor=1/(model['signed_radius']*model['rotation_length'])
    local=(factor*(c*delta[0]+s*delta[1]),factor*(-s*delta[0]+c*delta[1]))
    start,span=_parameters(curve)
    return _arc_membership(curve,tuple((x,x) for x in local),
                           parameter_endpoints=tuple(start+span*t for t in interval),**controls)


def _point_result(kind,curves,models,point,domain,controls,*,infinite=False):
    membership=[_membership(c,m,point,i,controls) for c,m,i in zip(curves,models,domain)]
    evidence=dict(center_zr_m=point,membership=membership,supporting_classification=kind)
    if any(x['status']=='EXTERIOR' for x in membership):
        return _report('DISJOINT',complete=True,centers=0,infinite=False,evidence=evidence)
    if any(x['status']=='UNVERIFIED' for x in membership):
        return _report('UNVERIFIED',evidence=evidence,reason='supporting contact proved; finite-arc membership unresolved')
    return _report(kind,complete=True,centers=1,infinite=infinite,evidence=evidence)


def _shared_parameters(first,second,distances,domain):
    if type(first) is not type(second) or not isinstance(first,(EllipseArc,HyperbolaArc)):return None
    common=('center_zr_m','semiaxes_m','rotation_rad')+ (('branch',) if isinstance(first,HyperbolaArc) else ())
    if any(getattr(first,k)!=getattr(second,k) for k in common):return None
    parameters=tuple(_parameters(c) for c in (first,second))
    if distances[0]*(1 if parameters[0][1]>0 else -1)!=distances[1]*(1 if parameters[1][1]>0 else -1):return None
    ranges=[sorted(start+span*t for t in interval) for (start,span),interval in zip(parameters,domain)]
    low,high=max(x[0] for x in ranges),min(x[1] for x in ranges)
    if low>high:return None  # Offsets may self-intersect, or circle angles may wrap.
    fractions=[tuple(sorted((u-start)/span for u in (low,high))) for start,span in parameters]
    return _report('INFINITE_PARAMETER_PAIRS' if low<high else 'SHARED_PARAMETER_ENDPOINT',
                   infinite=True if low<high else None,
                   evidence=dict(shared_parameter_interval=(low,high),fraction_intervals=fractions,
                                 identity='same source parameterization and same orientation-adjusted signed distance'),
                   reason='certified shared-parameter witness; other parameter pairs are not classified')


def _classify_offset_degeneracies(first,second,*,first_distance_m,second_distance_m,
                                 first_interval=(0.,1.),second_interval=(0.,1.),
                                 endpoint_width=DEFAULT_ENDPOINT_WIDTH,max_series_terms=96,
                                 finite_circle_intersections=False):
    """Diagnose shared parameters, exact circles and rational straight offsets.

    Complete circle/line tangency and disjointness require finite membership.
    Irrational rotation norms/line lengths, crossings and unproved identities
    remain unknown. Rational inputs denote exact stored binary geometry.
    """
    curves=(first,second)
    if not all(isinstance(c,(LineSegment,EllipseArc,HyperbolaArc)) for c in curves):
        raise ValueError('offset diagnosis requires supported lines or conic arcs')
    distances=tuple(_number(x,'distance_m') for x in (first_distance_m,second_distance_m))
    controls=dict(endpoint_width=endpoint_width,max_series_terms=max_series_terms)
    transcendental_interval('sin',0,endpoint_width=endpoint_width,max_terms=max_series_terms)
    domain=[]
    for curve,interval in zip(curves,(first_interval,second_interval)):
        if not isinstance(interval,(tuple,list)) or len(interval)!=2:raise ValueError('fraction interval requires a pair')
        lo,hi=(_number(x,'fraction interval') for x in interval)
        if lo>=hi or not isinstance(curve,LineSegment) and not 0<=lo<hi<=1:
            raise ValueError('fraction interval must increase; conic fractions must be in [0,1]')
        domain.append((lo,hi))
    circles=[_circle(c,d) for c,d in zip(curves,distances)]
    lines=[_line(c,d) for c,d in zip(curves,distances)]
    try:
        if all(circles) and any(m['radius']==0 for m in circles):
            a,b=circles;delta=_sub(b['center'],a['center']);d2=_dot(delta,delta)
            if a['radius']==b['radius']==0:
                equal=d2==0
                return _report('INFINITE_PARAMETER_PAIRS' if equal else 'DISJOINT',complete=True,
                               centers=1 if equal else 0,infinite=equal,
                               evidence=dict(collapsed_centers=(a['center'],b['center']),domain_box=domain))
            collapsed=a if a['radius']==0 else b;other=b if a['radius']==0 else a
            if d2!=other['radius']**2:return _report('DISJOINT',complete=True,centers=0,infinite=False,evidence=dict(distance_squared=d2,radius_squared=other['radius']**2))
            return _point_result('INFINITE_PARAMETER_PAIRS',curves,circles,collapsed['center'],domain,controls,infinite=True)
        if finite_circle_intersections and all(circles) and circles[0]['center']==circles[1]['center'] and circles[0]['radius']==circles[1]['radius']:
            from .coincident_circle_arcs import coincident_circle_intervals
            try:
                overlap=coincident_circle_intervals(curves,circles,domain,**controls)
            except ValueError as error:
                shared=_shared_parameters(first,second,distances,domain)
                if shared is not None:return shared
                return _report('COINCIDENT_SUPPORTING_CIRCLES',reason=str(error))
            if overlap is not None:
                return _report(**overlap)
        shared=_shared_parameters(first,second,distances,domain)
        if shared is not None:return shared
        if all(circles):
            a,b=circles;delta=_sub(b['center'],a['center']);d2=_dot(delta,delta)
            low=(a['radius']-b['radius'])**2;high=(a['radius']+b['radius'])**2
            evidence=dict(distance_squared=d2,difference_radius_squared=low,sum_radius_squared=high)
            if d2<low or d2>high:return _report('DISJOINT',complete=True,centers=0,infinite=False,evidence=evidence)
            if d2==0:return _report('COINCIDENT_SUPPORTING_CIRCLES',evidence=evidence,reason='finite-arc overlap not proved')
            if d2 in (low,high):
                scale=(a['radius']**2-b['radius']**2+d2)/(2*d2)
                point=tuple(x+scale*y for x,y in zip(a['center'],delta))
                return _point_result('SINGLE_TANGENCY',curves,circles,point,domain,controls)
        if any(lines) and any(circles):
            i=0 if lines[0] else 1;line=lines[i];circle=circles[1-i]
            delta=line['delta'];t=_dot(_sub(circle['center'],line['origin']),delta)/_dot(delta,delta)
            point=tuple(x+t*y for x,y in zip(line['origin'],delta));gap=_sub(point,circle['center']);d2=_dot(gap,gap)
            if d2>circle['radius']**2:return _report('DISJOINT',complete=True,centers=0,infinite=False,evidence=dict(distance_squared=d2,radius_squared=circle['radius']**2))
            if d2==circle['radius']**2:
                models=[lines[k] or circles[k] for k in range(2)];collapsed=circle['radius']==0
                return _point_result('INFINITE_PARAMETER_PAIRS' if collapsed else 'SINGLE_TANGENCY',curves,models,point,domain,controls,infinite=collapsed)
        if all(lines):
            a,b=lines;delta=_sub(b['origin'],a['origin']);det=_cross(a['delta'],b['delta'])
            if det==0:
                if _cross(delta,a['delta'])!=0:return _report('DISJOINT',complete=True,centers=0,infinite=False,evidence=dict(parallel_line_separation_cross=_cross(delta,a['delta'])))
                squared=_dot(a['delta'],a['delta']);shift=_dot(delta,a['delta'])/squared;scale=_dot(b['delta'],a['delta'])/squared
                mapped=sorted(shift+scale*t for t in domain[1]);lo=max(domain[0][0],mapped[0]);hi=min(domain[0][1],mapped[1])
                evidence=dict(first_fraction_overlap=(lo,hi),second_to_first=(shift,scale))
                if lo>hi:return _report('DISJOINT',complete=True,centers=0,infinite=False,evidence=evidence)
                return _report('INFINITE_PARAMETER_PAIRS' if lo<hi else 'SHARED_PARAMETER_ENDPOINT',complete=True,centers=None if lo<hi else 1,infinite=lo<hi,evidence=evidence)
        return _report('UNVERIFIED',reason='no exact special-case classification; use finite-domain crossing search')
    except ValueError as error:
        return _report('UNVERIFIED',reason=str(error))


def _classify_offset_degeneracies_v2(first,second,*,first_distance_m,second_distance_m,
                                 first_interval=(0.,1.),second_interval=(0.,1.),
                                 endpoint_width=DEFAULT_ENDPOINT_WIDTH,max_series_terms=96):
    """Preserve version 2 quarter-turn rules for saved construction diagnoses."""
    return _classify_offset_degeneracies(first,second,first_distance_m=first_distance_m,
        second_distance_m=second_distance_m,first_interval=first_interval,second_interval=second_interval,
        endpoint_width=endpoint_width,max_series_terms=max_series_terms,finite_circle_intersections=True)


def _classify_offset_degeneracies_v3(first,second,*,first_distance_m,second_distance_m,
                                 first_interval=(0.,1.),second_interval=(0.,1.),
                                 endpoint_width=DEFAULT_ENDPOINT_WIDTH,max_series_terms=96):
    """Extend the version 2 special cases to general coincident circular offsets."""
    previous=_classify_offset_degeneracies_v2(first,second,first_distance_m=first_distance_m,
        second_distance_m=second_distance_m,first_interval=first_interval,second_interval=second_interval,
        endpoint_width=endpoint_width,max_series_terms=max_series_terms)
    if previous['finite_domain_complete']:return previous
    from .general_coincident_circle_arcs import classify_general_coincident_arcs
    result=classify_general_coincident_arcs((first,second),(first_distance_m,second_distance_m),
        (first_interval,second_interval),endpoint_width=endpoint_width,max_series_terms=max_series_terms)
    if result is None:return previous
    # Keep already proved shared-parameter witnesses on enclosure exhaustion.
    if (result['classification']=='COINCIDENT_SUPPORTING_CIRCLES'
            and previous['classification'] in ('INFINITE_PARAMETER_PAIRS','SHARED_PARAMETER_ENDPOINT')):return previous
    return _report(**result)


def _classify_offset_degeneracies_v4(first,second,*,first_distance_m,second_distance_m,
                                 first_interval=(0.,1.),second_interval=(0.,1.),
                                 endpoint_width=DEFAULT_ENDPOINT_WIDTH,max_series_terms=96):
    """Extend version 3 with all same-conic reflected normal-offset contacts."""
    previous=_classify_offset_degeneracies_v3(first,second,first_distance_m=first_distance_m,
        second_distance_m=second_distance_m,first_interval=first_interval,second_interval=second_interval,
        endpoint_width=endpoint_width,max_series_terms=max_series_terms)
    if previous['finite_domain_complete']:return previous
    from .same_conic_offset_intersections import classify_same_conic_offsets
    try:
        result=classify_same_conic_offsets((first,second),(first_distance_m,second_distance_m),
            (first_interval,second_interval),endpoint_width=endpoint_width,max_series_terms=max_series_terms)
    except ValueError:return previous
    if result is None:return previous
    if previous['classification'] in ('INFINITE_PARAMETER_PAIRS','SHARED_PARAMETER_ENDPOINT'):
        result['evidence']=dict(previous['evidence'],**result['evidence'])
        if result['classification']=='UNVERIFIED':
            result.update(classification=previous['classification'],infinite=previous['infinite_parameter_pairs'])
    return _report(**result)


def _classify_offset_degeneracies_v5(first,second,*,first_distance_m,second_distance_m,
                                 first_interval=(0.,1.),second_interval=(0.,1.),
                                 endpoint_width=DEFAULT_ENDPOINT_WIDTH,max_series_terms=96):
    """Version 5 also classifies all rational circular/straight crossings."""
    previous=_classify_offset_degeneracies_v4(first,second,first_distance_m=first_distance_m,
        second_distance_m=second_distance_m,first_interval=first_interval,second_interval=second_interval,
        endpoint_width=endpoint_width,max_series_terms=max_series_terms)
    if previous['finite_domain_complete']:return previous
    from .finite_circular_crossings import classify_finite_circular_crossings
    result=classify_finite_circular_crossings((first,second),(first_distance_m,second_distance_m),
        (first_interval,second_interval),endpoint_width=endpoint_width,max_series_terms=max_series_terms)
    return previous if result is None else _report(**result)


def _classify_offset_degeneracies_v6(first,second,*,first_distance_m,second_distance_m,
                                 first_interval=(0.,1.),second_interval=(0.,1.),
                                 endpoint_width=DEFAULT_ENDPOINT_WIDTH,max_series_terms=96):
    """Version 6 retains algebraic radii and lengths for circular/straight offsets."""
    previous=_classify_offset_degeneracies_v5(first,second,first_distance_m=first_distance_m,
        second_distance_m=second_distance_m,first_interval=first_interval,second_interval=second_interval,
        endpoint_width=endpoint_width,max_series_terms=max_series_terms)
    if previous['finite_domain_complete']:return previous
    from .algebraic_circular_offsets import classify_algebraic_circular_offsets
    result=classify_algebraic_circular_offsets((first,second),(first_distance_m,second_distance_m),
        (first_interval,second_interval),endpoint_width=endpoint_width,max_series_terms=max_series_terms)
    return previous if result is None else _report(**result)


def _classify_offset_degeneracies_v7(first,second,*,first_distance_m,second_distance_m,
                                 first_interval=(0.,1.),second_interval=(0.,1.),
                                 endpoint_width=DEFAULT_ENDPOINT_WIDTH,max_series_terms=96):
    """Version 7 adds line/noncircular contacts and proved global projection bounds."""
    previous=_classify_offset_degeneracies_v6(first,second,first_distance_m=first_distance_m,
        second_distance_m=second_distance_m,first_interval=first_interval,second_interval=second_interval,
        endpoint_width=endpoint_width,max_series_terms=max_series_terms)
    if previous['finite_domain_complete']:return previous
    from .line_noncircular_offset_contacts import classify_line_noncircular_contacts
    result=classify_line_noncircular_contacts((first,second),(first_distance_m,second_distance_m),
        (first_interval,second_interval),endpoint_width=endpoint_width,max_series_terms=max_series_terms)
    return previous if result is None else _report(**result)


def _classify_offset_degeneracies_v8(first,second,*,first_distance_m,second_distance_m,
                                 first_interval=(0.,1.),second_interval=(0.,1.),
                                 endpoint_width=DEFAULT_ENDPOINT_WIDTH,max_series_terms=96):
    """Version 8 adds exhaustive rational-chart roots for line/noncircular offsets."""
    previous=_classify_offset_degeneracies_v7(first,second,first_distance_m=first_distance_m,
        second_distance_m=second_distance_m,first_interval=first_interval,second_interval=second_interval,
        endpoint_width=endpoint_width,max_series_terms=max_series_terms)
    if previous['finite_domain_complete']:return previous
    from .line_noncircular_crossings import classify_line_noncircular_crossings
    result=classify_line_noncircular_crossings((first,second),(first_distance_m,second_distance_m),
        (first_interval,second_interval),endpoint_width=endpoint_width,max_series_terms=max_series_terms)
    if result is None:return previous
    if not result['complete'] and previous['status']=='CERTIFIED':
        previous['evidence']['general_crossing_search']=result['evidence']
        previous['reason']+='; '+result['reason']
        return previous
    return _report(**result)


def _classify_offset_degeneracies_v9(first,second,*,first_distance_m,second_distance_m,
                                 first_interval=(0.,1.),second_interval=(0.,1.),
                                 endpoint_width=DEFAULT_ENDPOINT_WIDTH,max_series_terms=96):
    """Version 9 adds complete circular/noncircular offset intersections."""
    previous=_classify_offset_degeneracies_v8(first,second,first_distance_m=first_distance_m,
        second_distance_m=second_distance_m,first_interval=first_interval,second_interval=second_interval,
        endpoint_width=endpoint_width,max_series_terms=max_series_terms)
    if previous['finite_domain_complete']:return previous
    from .circle_conic_crossings import classify_circle_conic_crossings
    result=classify_circle_conic_crossings((first,second),(first_distance_m,second_distance_m),
        (first_interval,second_interval),endpoint_width=endpoint_width,max_series_terms=max_series_terms)
    return previous if result is None else _report(**result)


def classify_offset_degeneracies(first,second,*,first_distance_m,second_distance_m,
                                 first_interval=(0.,1.),second_interval=(0.,1.),
                                 endpoint_width=DEFAULT_ENDPOINT_WIDTH,max_series_terms=96):
    """Version 10 adds noncircular pairs with at least one zero offset distance."""
    previous=_classify_offset_degeneracies_v9(first,second,first_distance_m=first_distance_m,
        second_distance_m=second_distance_m,first_interval=first_interval,second_interval=second_interval,
        endpoint_width=endpoint_width,max_series_terms=max_series_terms)
    if previous['finite_domain_complete']:return previous
    from .conic_implicit_offset import classify_conic_implicit_offset
    result=classify_conic_implicit_offset((first,second),(first_distance_m,second_distance_m),
        (first_interval,second_interval),endpoint_width=endpoint_width,max_series_terms=max_series_terms)
    if result is None:return previous
    if not result['complete'] and previous['status']=='CERTIFIED':
        previous['evidence']['general_conic_crossing_search']=result['evidence']
        previous['reason']+='; '+result['reason']
        return previous
    return _report(**result)


def diagnose_offsets_document(request):
    """Strict, self-contained JSON diagnosis; never a constructed Case."""
    from copy import deepcopy
    import hashlib
    from . import __version__
    from .config import keys
    from .conics import curve_from_dict
    from .tangent_construction import _canonical, _json_value
    keys(request,('schema_version','curves','controls'),('schema_version','curves','controls'),'offset diagnosis request')
    if type(request['schema_version']) is not int or request['schema_version']!=1:
        raise ValueError('offset diagnosis request requires schema_version 1')
    canonical=_canonical(request)
    rows=request['curves']
    if not isinstance(rows,list) or len(rows)!=2:raise ValueError('offset diagnosis requires exactly two curves')
    controls=request['controls']
    keys(controls,('first_distance_m','second_distance_m','first_interval','second_interval','endpoint_width','max_series_terms'),
         ('first_distance_m','second_distance_m'),'offset diagnosis controls')
    report=classify_offset_degeneracies(*(curve_from_dict(row) for row in rows),**controls)
    return _json_value(dict(schema_version=10,document_type='normal_offset_diagnosis',software_version=__version__,
                            request=deepcopy(request),request_sha256=hashlib.sha256(canonical.encode()).hexdigest(),
                            diagnosis=report))
