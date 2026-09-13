# SPDX-License-Identifier: Apache-2.0
"""Independent Newton trigonometry and square-root checks of coincident arcs."""
import argparse
from dataclasses import replace
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
from functools import lru_cache
import itertools
import json
import math
from pathlib import Path
import time

from validate_coincident_circle_arcs import fingerprints, reference_pi
from superfish_ng.conics import EllipseArc, curve_to_dict, rotation_cos_sin
from superfish_ng.general_coincident_circle_arcs import _equal_support_radii
from superfish_ng.offset_degeneracies import classify_offset_degeneracies


def decimal_value(value):
    value=F(value)
    return D(value.numerator)/D(value.denominator)


def sine_cosine(angle):
    sine=angle;cosine=D(1);sine_term=angle;cosine_term=D(1)
    for index in range(1,180):
        sine_term*=-angle*angle/D(2*index*(2*index+1))
        cosine_term*=-angle*angle/D((2*index-1)*2*index)
        sine+=sine_term;cosine+=cosine_term
        if max(abs(sine_term),abs(cosine_term))<D('1e-130'):return sine,cosine
    raise AssertionError('independent trigonometric reference did not converge')


@lru_cache(maxsize=None)
def phase_reference(x,y):
    """Newton root of y*cos(theta)-x*sin(theta); double atan2 is only a seed."""
    if y==0:return D(0) if x>0 else reference_pi()
    if x==0:return (1 if y>0 else -1)*reference_pi()/2
    scale=max(abs(x),abs(y));x=decimal_value(x/scale);y=decimal_value(y/scale)
    angle=D(math.atan2(float(y),float(x)))
    for _ in range(8):
        sine,cosine=sine_cosine(angle)
        angle+=(y*cosine-x*sine)/(y*sine+x*cosine)
    sine,cosine=sine_cosine(angle)
    assert abs(y*cosine-x*sine)<D('1e-110'),'independent phase residual failed'
    return +angle


def oracle(curves,distances,domains,pi):
    rotations=[tuple(map(F,rotation_cos_sin(c.rotation_rad))) for c in curves]
    squares=[F(c.semiaxes_m[0])**2*sum(t*t for t in r) for c,r in zip(curves,rotations)]
    radii=[decimal_value(square).sqrt()-(1 if c.sweep_rad>0 else -1)*D(d)
           for square,c,d in zip(squares,curves,distances)]
    # All generated arc pairs use the same raw radius and oriented distance.
    assert abs(radii[0])==abs(radii[1]) and radii[0]!=0
    sign=1 if radii[0]*radii[1]>0 else -1
    first,second=rotations
    x=sign*sum(a*b for a,b in zip(first,second));y=sign*(first[0]*second[1]-first[1]*second[0])
    phase=phase_reference(x,y)
    ranges=[sorted(F(c.start_rad)+F(c.sweep_rad)*t for t in domain) for c,domain in zip(curves,domains)]
    first,second=ranges;positive=endpoints=0
    periods={}
    # Original starts are normalized and all test sweeps have length <2*pi.
    # The fixed 17 translates enclose both ranges and every possible phase.
    for period in range(-8,9):
        if y==0 and x>0 and period==0:
            difference=min(first[1],second[1])-max(first[0],second[0])
            ordering=(difference>0)-(difference<0)
        else:
            shift=phase+2*period*pi
            low=max(decimal_value(first[0]),decimal_value(second[0])+shift)
            high=min(decimal_value(first[1]),decimal_value(second[1])+shift)
            difference=high-low
            assert abs(difference)>D('1e-85'),'independent endpoint sign unresolved'
            ordering=1 if difference>0 else -1
        periods[period]='POSITIVE_INTERVAL' if ordering>0 else 'SHARED_ENDPOINT' if ordering==0 else 'DISJOINT'
        positive+=ordering>0;endpoints+=ordering==0
    if positive:expected=('INFINITE_PARAMETER_PAIRS',None,True,positive)
    elif endpoints:expected=('SHARED_PARAMETER_ENDPOINT',endpoints,False,0)
    else:expected=('DISJOINT',0,False,0)
    return expected,periods


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    before=fingerprints();start=time.monotonic();records=[];support_records=[]
    with localcontext() as context:
        context.prec=120;pi=reference_pi()
        squares=tuple(F(x)**2 for x in (.25,.5,1,2,3,4))+(F(2),F(3),F(5),F(7),F(8),F(12))
        distances=tuple(map(F,(-4,-1,0,.5,1,2,4)))
        for a,b,d,e in itertools.product(squares,squares,distances,distances):
            first=decimal_value(a).sqrt()-decimal_value(d);second=decimal_value(b).sqrt()-decimal_value(e)
            difference=abs(first)-abs(second)
            if difference:assert abs(difference)>D('1e-90'),'independent radius comparison unresolved'
            expected=first!=0 and second!=0 and difference==0
            actual=_equal_support_radii(a,b,d,e) is not None
            row=dict(squares=[str(a),str(b)],distances=[str(d),str(e)],expected=expected,observed=actual)
            support_records.append(row)
            if actual!=expected:
                (args.out/'failure.json').write_text(json.dumps(row,indent=2)+'\n')
                raise AssertionError('independent square-root support comparison failed')
        arcs=((0.,1.,.5,1.),(0.,1.,1.,1.),(0.,1.,1.5,1.),(-2.,4.,-2.,4.),
              (3.,.5,-3.1,.3),(0.,1.,math.nextafter(1.,0.),1.),
              (0.,1.,math.nextafter(1.,math.inf),1.),(0.,math.nextafter(math.pi,math.inf),0.,.5))
        domains=(((F(0),F(1)),(F(0),F(1))),((F(1,4),F(3,4)),(F(1,8),F(7,8))))
        for index,(angle,reflected,arc,reverse,negative,scale,domain,exchange) in enumerate(itertools.product(
                (.1,.3,.7,1.2,1.55,2.8),(False,True),arcs,(False,True),(False,True),
                (2.**-100,1.,2.**100),domains,(False,True))):
            center=(3*scale,4*scale)
            first=EllipseArc(center,(2*scale,2*scale),arc[0],arc[1],angle)
            second=EllipseArc(center,(2*scale,2*scale),arc[2],arc[3],-angle if reflected else angle)
            distance=(4 if negative else 1)*scale;distances=(distance,distance)
            if reverse:
                second=replace(second,start_rad=arc[2]+arc[3],sweep_rad=-arc[3]);distances=(distance,-distance)
            curves=(first,second)
            if exchange:curves=curves[::-1];distances=distances[::-1];domain=domain[::-1]
            expected,periods=oracle(curves,distances,domain,pi)
            actual=classify_offset_degeneracies(*curves,first_distance_m=distances[0],second_distance_m=distances[1],
                        first_interval=domain[0],second_interval=domain[1])
            observed=(actual['classification'],actual['finite_center_count'],actual['infinite_parameter_pairs'],
                      actual['evidence'].get('positive_components',0))
            periodic=actual['evidence']['periodic_intersections']
            classifications={row['period']:row['classification'] for row in periodic}
            all_periods=all(classifications.get(period,'DISJOINT')==kind for period,kind in periods.items())
            row=dict(index=index,curves=[curve_to_dict(c) for c in curves],distances=distances,
                     domains=[[str(t) for t in d] for d in domain],expected=expected,observed=observed,
                     finite_domain_complete=actual['finite_domain_complete'],all_reference_periods_match=all_periods)
            records.append(row)
            if observed!=expected or not actual['finite_domain_complete'] or not all_periods:
                (args.out/'failure.json').write_text(json.dumps(row,indent=2)+'\n')
                raise AssertionError(f'independent general circle-set mismatch at {index}')
    assert fingerprints()==before
    report=dict(status='PASS',cases=len(records),support_cases=len(support_records),seconds=time.monotonic()-start,
                source_sha256=before,source_changed_during_run=False,
                reference='120-digit Decimal square roots, AGM pi, Newton trigonometric phase and fixed 17 translated angular intervals',
                scope='Original binary circle geometry and full finite interval classifications; no FEM or constructed fillet accuracy assertion',
                records=records,support_records=support_records)
    (args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print({key:report[key] for key in ('status','cases','support_cases','seconds')})


if __name__=='__main__':main()
