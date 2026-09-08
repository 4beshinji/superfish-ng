# SPDX-License-Identifier: Apache-2.0
"""Finite normal-offset intersections with rational Krawczyk certificates.

Every excluded region is proved root-free. Strict interior inclusion and a
contraction bound prove each accepted root exists uniquely. Singular contacts,
shared boundaries and exhausted budgets remain unresolved, never sampled away.
"""
from fractions import Fraction as F
from functools import lru_cache
from .conics import LineSegment,EllipseArc,HyperbolaArc
from .normal_offsets import normal_offset_bounds,add,scale
from .certified_arcs import _number,_multiply,transcendental_interval,DEFAULT_ENDPOINT_WIDTH
from .contact_enclosures import _interval_subtract as subtract


def _intersection(a,b):
    result=tuple((max(x[0],y[0]),min(x[1],y[1])) for x,y in zip(a,b))
    return None if any(lo>hi for lo,hi in result) else result


def _outward(interval,bits):
    grid=2**bits
    lo,hi=(x*grid for x in interval)
    return F(lo.numerator//lo.denominator,grid),F(-((-hi.numerator)//hi.denominator),grid)


def _krawczyk(box,values,jacobian,bits):
    mid=tuple(sum(x)/2 for x in box)
    matrix=[[sum(x)/2 for x in row] for row in jacobian]
    a,b=matrix[0];c,d=matrix[1];det=a*d-b*c
    if det==0:return None
    try:
        inverse=tuple(tuple(F(float(x/det)) for x in row) for row in ((d,-b),(-c,a)))
    except (ValueError,OverflowError):return None
    if inverse[0][0]*inverse[1][1]-inverse[0][1]*inverse[1][0]==0:return None
    remainder=[];image=[]
    for i in range(2):
        row=[]
        for j in range(2):
            product=add(scale(jacobian[0][j],inverse[i][0]),scale(jacobian[1][j],inverse[i][1]))
            row.append(subtract((F(i==j),)*2,product))
        remainder.append(row)
        displacement=add(scale(values[0],-inverse[i][0]),scale(values[1],-inverse[i][1]))
        for j in range(2):
            displacement=add(displacement,_multiply(row[j],(box[j][0]-mid[j],box[j][1]-mid[j])))
        image.append(_outward(add((mid[i],mid[i]),displacement),bits))
    norm=max(sum(max(abs(lo),abs(hi)) for lo,hi in row) for row in remainder)
    return dict(domain_box=box,midpoint=mid,preconditioner=inverse,krawczyk_box=tuple(image),
                contraction_bound=norm,
                strict_inclusion=all(a<lo<=hi<b for (lo,hi),(a,b) in zip(image,box)))


def intersect_normal_offsets(first,second,*,first_distance_m,second_distance_m,
                             first_interval=(0.,1.),second_interval=(0.,1.),
                             fraction_width=F(1,2**24),max_boxes=10000,precision_bits=96,
                             endpoint_width=DEFAULT_ENDPOINT_WIDTH,max_series_terms=96):
    """Search an explicit finite fraction rectangle for all isolated crossings.

    PASS means no unprocessed/unresolved region remains and every root box meets
    fraction_width. Root boxes enclose mathematical binary-model parameters;
    no float contact trimming or usable fillet geometry is returned here.
    """
    if not all(isinstance(c,(LineSegment,EllipseArc,HyperbolaArc)) for c in (first,second)):
        raise ValueError('offset intersections require supported lines or conic arcs')
    distances=tuple(_number(x,'distance_m') for x in (first_distance_m,second_distance_m))
    width=_number(fraction_width,'fraction_width')
    if not 0<width<1 or type(max_boxes) is not int or max_boxes<1:
        raise ValueError('fraction_width must be in (0,1); max_boxes must be a positive integer')
    if type(precision_bits) is not int or precision_bits<1:
        raise ValueError('precision_bits must be a positive integer')
    domain=[]
    for curve,interval in zip((first,second),(first_interval,second_interval)):
        if not isinstance(interval,(tuple,list)) or len(interval)!=2:
            raise ValueError('fraction interval requires a pair')
        lo,hi=(_number(x,'fraction interval') for x in interval)
        if lo>=hi or not isinstance(curve,LineSegment) and not 0<=lo<hi<=1:
            raise ValueError('fraction interval must be increasing; conic fractions must be in [0,1]')
        domain.append((lo,hi))
    transcendental_interval('sin',0,endpoint_width=endpoint_width,max_terms=max_series_terms)
    curves=(first,second)

    @lru_cache(maxsize=512)
    def bounds(index,lo,hi):
        return normal_offset_bounds(curves[index],lo,hi,distance_m=distances[index],
                                    endpoint_width=endpoint_width,max_series_terms=max_series_terms)

    pending=[(tuple(domain),None)];roots=[];unresolved=[];checked=0;excluded=0
    while pending:
        box,certificate=pending.pop()
        if checked>=max_boxes:
            unresolved.extend(dict(parameter_box=b,certificate=c,reason='box budget exhausted') for b,c in [(box,certificate),*pending])
            break
        checked+=1
        try:
            left,right=[bounds(i,*box[i]) for i in range(2)]
            center=_intersection(left['center_box_zr_m'],right['center_box_zr_m'])
            if center is None:
                if certificate is not None:raise RuntimeError('certified intersection contradicted by coordinate exclusion')
                excluded+=1;continue
            if certificate is not None and max(hi-lo for lo,hi in box)<=width:
                roots.append(dict(parameter_box=box,center_box_zr_m=center,certificate=certificate))
                continue
            if 'COLLAPSED' in (left['regularity'],right['regularity']):
                unresolved.append(dict(parameter_box=box,certificate=certificate,reason='collapsed offset overlaps other center enclosure'))
                continue
            mid=tuple(sum(x)/2 for x in box)
            values=tuple(subtract(a,b) for a,b in zip(bounds(0,mid[0],mid[0])['center_box_zr_m'],
                                                    bounds(1,mid[1],mid[1])['center_box_zr_m']))
            jacobian=tuple((left['derivative_box_zr_m'][i],scale(right['derivative_box_zr_m'][i],-1)) for i in range(2))
            step=_krawczyk(box,values,jacobian,precision_bits)
            if step is not None:
                narrowed=_intersection(box,step['krawczyk_box'])
                if narrowed is None:
                    if certificate is not None:raise RuntimeError('certified root contradicted by Krawczyk exclusion')
                    excluded+=1;continue
                if step['strict_inclusion'] and step['contraction_bound']<1:
                    certificate=step
                if narrowed!=box:
                    pending.append((narrowed,certificate));continue
            if certificate is not None or max(hi-lo for lo,hi in box)<=width:
                unresolved.append(dict(parameter_box=box,certificate=certificate,reason='inclusion stalled or crossing not isolated at requested width'))
                continue
            # Closed children share a boundary. A root there cannot pass strict
            # interior inclusion in both, and is conservatively left unresolved.
            axis=max(range(2),key=lambda i:box[i][1]-box[i][0]);lo,hi=box[axis];middle=(lo+hi)/2
            for interval in ((middle,hi),(lo,middle)):
                child=list(box);child[axis]=interval;pending.append((tuple(child),None))
        except ValueError as error:
            unresolved.append(dict(parameter_box=box,certificate=certificate,reason=str(error)))
    roots.sort(key=lambda r:r['parameter_box'])
    return dict(status='UNVERIFIED' if unresolved else 'PASS',roots=roots,unresolved=unresolved,
                domain_box=tuple(domain),boxes_checked=checked,excluded_boxes=excluded,
                controls=dict(first_distance_m=distances[0],second_distance_m=distances[1],fraction_width=width,
                              max_boxes=max_boxes,precision_bits=precision_bits,
                              endpoint_width=_number(endpoint_width,'endpoint_width'),max_series_terms=max_series_terms),
                scope='complete finite-domain crossing search when PASS; rational existence/uniqueness certificates; no fillet trimming or physical accuracy claim')
