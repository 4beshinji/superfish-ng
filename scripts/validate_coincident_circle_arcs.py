# SPDX-License-Identifier: Apache-2.0
"""Independent Decimal circle-set oracle for finite coincident offset diagnostics."""
import argparse
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import hashlib
import itertools
import json
import math
from pathlib import Path
import time

from superfish_ng.conics import EllipseArc, curve_to_dict
from superfish_ng.offset_degeneracies import classify_offset_degeneracies

ROOT=Path(__file__).resolve().parents[1]


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def reference_pi():
    # AGM reference shares no series or angle-isolation code with the implementation.
    a,b,t,p=D(1),D(1)/D(2).sqrt(),D(1)/4,D(1)
    for _ in range(9):
        following=(a+b)/2;b=(a*b).sqrt();t-=p*(a-following)**2;a=following;p*=2
    return (a+b)**2/(4*t)


def oracle(curves,distances,domains,pi):
    phases={0.:0,math.pi/2:1,-math.pi/2:-1,math.pi:2,-math.pi:2}
    intervals=[]
    for curve,distance,domain in zip(curves,distances,domains):
        signed=D(curve.semiaxes_m[0])-(1 if curve.sweep_rad>0 else -1)*D(distance)
        assert signed!=0
        phase=phases[curve.rotation_rad]+(2 if signed<0 else 0)
        endpoints=[(F(curve.start_rad)+F(curve.sweep_rad)*t,phase) for t in domain]
        intervals.append(tuple(sorted(endpoints)))
    a,b=intervals;positive=endpoints=0
    def compare(first,second):
        rational=first[0]-second[0];phase=first[1]-second[1]
        if phase==0:return (rational>0)-(rational<0)
        difference=D(rational.numerator)/D(rational.denominator)+D(phase)*pi/2
        assert abs(difference)>D('1e-80'),'reference precision unresolved'
        return 1 if difference>0 else -1
    # Stored starts are normalized and both sweeps are <2*pi. These 17 translates
    # strictly cover the possible phase differences; this oracle does no adaptive isolation.
    for period in range(-8,9):
        shifted=[(value,phase+4*period) for value,phase in b]
        low=a[0] if compare(a[0],shifted[0])>=0 else shifted[0]
        high=a[1] if compare(a[1],shifted[1])<=0 else shifted[1]
        difference=compare(high,low)
        if difference>0:positive+=1
        elif difference==0:endpoints+=1
    if positive:return 'INFINITE_PARAMETER_PAIRS',None,True,positive
    if endpoints:return 'SHARED_PARAMETER_ENDPOINT',endpoints,False,0
    return 'DISJOINT',0,False,0


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False);start=time.monotonic();before=fingerprints();records=[]
    rotations=(0.,math.pi/2,-math.pi/2,math.pi)
    arcs=[(0.,1.,.5,1.),(0.,1.,1.,1.),(0.,1.,1.5,1.),(-2.,4.,-2.,4.),(3.,.5,-3.1,.3),
          (0.,math.pi,0.,.5),(0.,math.nextafter(math.pi,math.inf),0.,.5)]
    domains=[((F(0),F(1)),(F(0),F(1))),((F(1,4),F(3,4)),(F(1,8),F(7,8)))]
    with localcontext() as context:
        context.prec=120;pi=reference_pi()
        for index,(rotation_pair,arc,reverse,negative,scale,domain) in enumerate(itertools.product(
                itertools.product(rotations,repeat=2),arcs,(False,True),(False,True),(2.**-40,1.,2.**40),domains)):
            center=(3*scale,4*scale)
            first=EllipseArc(center,(2*scale,2*scale),arc[0],arc[1],rotation_pair[0])
            second=EllipseArc(center,(3*scale,3*scale),arc[2],arc[3],rotation_pair[1])
            distance=(4 if negative else 2)*scale
            if reverse:
                second=EllipseArc(center,(3*scale,3*scale),arc[2]+arc[3],-arc[3],rotation_pair[1]);distance=-distance
            curves=(first,second);distances=(scale,distance)
            expected=oracle(curves,distances,domain,pi)
            actual=classify_offset_degeneracies(first,second,first_distance_m=distances[0],second_distance_m=distances[1],
                        first_interval=domain[0],second_interval=domain[1])
            observed=(actual['classification'],actual['finite_center_count'],actual['infinite_parameter_pairs'],
                      actual['evidence'].get('positive_components',0))
            row=dict(index=index,curves=[curve_to_dict(c) for c in curves],distances=distances,
                     domains=[[str(t) for t in d] for d in domain],expected=expected,observed=observed,
                     finite_domain_complete=actual['finite_domain_complete'])
            records.append(row)
            if observed!=expected or not actual['finite_domain_complete']:
                (args.out/'failure.json').write_text(json.dumps(row,indent=2)+'\n')
                raise AssertionError(f'independent circle-set mismatch at {index}')
    after=fingerprints();assert before==after
    report=dict(status='PASS',cases=len(records),seconds=time.monotonic()-start,source_sha256=before,
                source_changed_during_run=False,reference='120-digit independent AGM pi and exhaustive translated Decimal angular intervals',
                scope='Known cardinal rotations, original binary arc inputs and signed radii; no physical FEM or fillet-construction accuracy assertion',records=records)
    (args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print({key:report[key] for key in ('status','cases','seconds')})


if __name__=='__main__':main()
