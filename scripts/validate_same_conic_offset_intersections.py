# SPDX-License-Identifier: Apache-2.0
"""Independent normal-displacement root search for same-conic offset contacts."""
import argparse
from dataclasses import replace
from decimal import Decimal as D,localcontext
from fractions import Fraction as F
from functools import lru_cache
import itertools,json
from pathlib import Path
import time

from validate_coincident_circle_arcs import fingerprints,reference_pi
from validate_general_coincident_circle_arcs import decimal_value,phase_reference
from superfish_ng.conics import EllipseArc,HyperbolaArc,curve_to_dict,rotation_cos_sin
from superfish_ng.offset_degeneracies import classify_offset_degeneracies


def sign(value):return (value>0)-(value<0)


def bisect_normal_component(function,low,high):
    left,right=function(low),function(high)
    assert left*right<0,'independent normal component must bracket a root'
    for _ in range(420):
        middle=(low+high)/2;value=function(middle)
        if value==0:return middle
        if value*left>0:low,left=middle,value
        else:high=middle
        if high-low<D('1e-100'):return (low+high)/2
    raise AssertionError('independent normal component root did not converge')


@lru_cache(maxsize=None)
def reference_contacts(kind,branch,a,b,distance,rotation_square):
    """Solve original normal components; no sin²/sinh² closed-form roots."""
    aa,bb,dd=map(decimal_value,(a,b,distance));length=decimal_value(rotation_square).sqrt()
    pi=reference_pi();pairs=[]
    if kind=='ellipse':
        if distance<=0:return ()
        for axis in (0,1):
            # A center on axis 0 requires the original y component to vanish.
            target,multiplier=(b,a) if axis==0 else (a,b)
            def endpoint_sign(speed):
                return sign((target*speed)**2*rotation_square-(distance*multiplier)**2)
            def component(sine):
                cosine_square=1-sine*sine
                speed=(aa*aa*sine*sine+bb*bb*cosine_square).sqrt()
                return decimal_value(target)-dd*decimal_value(multiplier)/(length*speed)
            left,right=endpoint_sign(b),endpoint_sign(a)
            if left==0:root=D(0)
            elif right==0:root=D(1)
            elif left*right<0:root=bisect_normal_component(component,D(0),D(1))
            else:continue
            # Excluded endpoint has identical source contacts, not a double point.
            if (axis==0 and root==0) or (axis==1 and root==1):continue
            angle=D(0) if root==0 else pi/2 if root==1 else phase_reference(F((1-root*root).sqrt()),F(root))
            if axis==0:
                pairs.append(((-angle,False),(angle,False)))
                if root!=1:pairs.append(((pi-angle,False),(pi+angle,False)))
            else:
                pairs.append(((angle,root==0),(pi-angle,False)))
                if root!=0:pairs.append(((-angle,False),(pi+angle,False)))
    else:
        effective=-branch*distance
        if effective<=0 or sign(b**4*rotation_square-(effective*a)**2)>=0:return ()
        def component(sine):
            cosine_square=1+sine*sine
            speed=(aa*aa*sine*sine+bb*bb*cosine_square).sqrt()
            return bb+dd*branch*aa/(length*speed)
        high=D(1)
        while component(high)<=0:
            high*=2
            assert high<D('1e50'),'independent hyperbola bracket exceeded reference scope'
        root=bisect_normal_component(component,D(0),high)
        parameter=(root+(1+root*root).sqrt()).ln()
        pairs.append(((-parameter,False),(parameter,False)))
    return tuple(pairs)


def parameter_range(curve,domain):
    if isinstance(curve,EllipseArc):start,span=F(curve.start_rad),F(curve.sweep_rad)
    else:start,span=F(curve.start_parameter),F(curve.end_parameter)-F(curve.start_parameter)
    return tuple(sorted(start+span*F(value) for value in domain))


def point_compare(point,period,bound,pi):
    angle,zero=point
    if zero and period==0:return sign(-bound)
    difference=angle+2*period*pi-decimal_value(bound)
    assert abs(difference)>D('1e-85'),'independent reference endpoint sign unresolved'
    return sign(difference)


def contains(interval,point,periodic,pi):
    return any(point_compare(point,period,interval[0],pi)>=0 and point_compare(point,period,interval[1],pi)<=0
               for period in (range(-8,9) if periodic else (0,)))


def oracle(curves,distances,domains,pi):
    periodic=isinstance(curves[0],EllipseArc);kind='ellipse' if periodic else 'hyperbola'
    ranges=[parameter_range(curve,domain) for curve,domain in zip(curves,domains)]
    first,second=ranges;positive=0;endpoints=[]
    for period in (range(-8,9) if periodic else (0,)):
        if period==0:
            low=max(first[0],second[0]);high=min(first[1],second[1]);difference=high-low
            if difference==0:endpoints.append(low)
            positive+=difference>0
        else:
            shift=2*period*pi
            low=max(decimal_value(first[0]),decimal_value(second[0])+shift)
            high=min(decimal_value(first[1]),decimal_value(second[1])+shift)
            assert abs(high-low)>D('1e-85'),'independent periodic endpoint sign unresolved'
            positive+=high>low
    a,b=map(F,curves[0].semiaxes_m);scale=max(a,b)
    span=F(curves[0].sweep_rad) if periodic else F(curves[0].end_parameter)-F(curves[0].start_parameter)
    distance=(1 if span>0 else -1)*F(distances[0]);rotation=tuple(map(F,rotation_cos_sin(curves[0].rotation_rad)))
    pairs=reference_contacts(kind,1 if periodic else curves[0].branch,a/scale,b/scale,distance/scale,sum(x*x for x in rotation))
    added=duplicates=present=0
    for pair in pairs:
        memberships=[[contains(interval,point,periodic,pi) for point in pair] for interval in ranges]
        exists=(memberships[0][0] and memberships[1][1]) or (memberships[0][1] and memberships[1][0])
        if not exists:continue
        present+=1
        duplicate=any(point_compare(point,period,endpoint,pi)==0 for endpoint in endpoints for point in pair
                      for period in (range(-8,9) if periodic else (0,)))
        duplicates+=duplicate;added+=not duplicate
    count=added+len(endpoints)
    if positive:expected=('INFINITE_PARAMETER_PAIRS',None,True)
    elif added:expected=('FINITE_CENTERS',count,False)
    elif endpoints:expected=('SHARED_PARAMETER_ENDPOINT',count,False)
    else:expected=('DISJOINT',0,False)
    return expected,dict(support_self_centers=len(pairs),finite_self_centers=present,duplicates=duplicates,
                         shared_endpoints=len(endpoints),positive_components=positive)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=False);before=fingerprints();start=time.monotonic();records=[]
    domains=(((F(0),F(1)),(F(0),F(1))),((F(1,4),F(3,4)),(F(1,8),F(7,8))))
    ellipse_arcs=((.5,.5,-1.,.5),(0.,1.,-1.,1.),(.25,.5,2.5,.5),(-1.,2.,2.,2.),(0.,3.,-3.,3.),(3.,.5,-3.1,.3))
    hyperbola_arcs=((.25,.75,-.75,-.25),(0.,1.,-1.,0.),(0.,2.,-2.,0.),(1.,2.,-2.,-1.),(-1.,1.,0.,2.),(2.,3.,-1.,0.))
    with localcontext() as context:
        context.prec=120;pi=reference_pi()
        for kind,shapes,distances,arcs in [('ellipse',((2.,1.),(1.,2.)),(-.75,0.,.5,.75,1.,2.,2.5,4.),ellipse_arcs),
                                          ('hyperbola',(1,-1),(-2.,-.75,-.5,-.25,.25,.5,.75,2.),hyperbola_arcs)]:
            for shape,distance,arc,angle,reverse,exchange,scale,domain in itertools.product(
                    shapes,distances,arcs,(0.,.3),(False,True),(False,True),(2.**-40,2.**40),domains):
                center=(3*scale,4*scale)
                if kind=='ellipse':
                    axes=tuple(x*scale for x in shape)
                    first=EllipseArc(center,axes,arc[0],arc[1],angle)
                    second=EllipseArc(center,axes,arc[2],arc[3],angle)
                else:
                    first=HyperbolaArc(center,(2*scale,scale),arc[0],arc[1],rotation_rad=angle,branch=shape)
                    second=replace(first,start_parameter=arc[2],end_parameter=arc[3])
                actual_distances=[distance*scale]*2
                if reverse:
                    second=(replace(second,start_rad=second.start_rad+second.sweep_rad,sweep_rad=-second.sweep_rad) if kind=='ellipse'
                            else replace(second,start_parameter=second.end_parameter,end_parameter=second.start_parameter))
                    actual_distances[1]=-actual_distances[1]
                curves=[first,second]
                if exchange:curves.reverse();actual_distances.reverse();domain=domain[::-1]
                expected,reference=oracle(curves,actual_distances,domain,pi)
                actual=classify_offset_degeneracies(*curves,first_distance_m=actual_distances[0],second_distance_m=actual_distances[1],
                            first_interval=domain[0],second_interval=domain[1])
                observed=(actual['classification'],actual['finite_center_count'],actual['infinite_parameter_pairs'])
                row=dict(index=len(records),kind=kind,curves=[curve_to_dict(curve) for curve in curves],distances=actual_distances,
                         domains=[[str(t) for t in interval] for interval in domain],expected=expected,observed=observed,
                         finite_domain_complete=actual['finite_domain_complete'],reference=reference)
                records.append(row)
                if expected!=observed or not actual['finite_domain_complete']:
                    (args.out/'failure.json').write_text(json.dumps(row,indent=2)+'\n')
                    raise AssertionError(f'independent same-conic offset comparison failed at {row["index"]}')
    assert fingerprints()==before
    report=dict(status='PASS',cases=len(records),seconds=time.monotonic()-start,source_sha256=before,source_changed_during_run=False,
                reference='120-digit bisection of original normal components, independent Newton/Decimal logarithm parameters, fixed 17 ellipse translates',
                scope='Same-source noncircular ellipses and one hyperbola branch; full finite-domain center counts, no fillet/FEM accuracy assertion',records=records)
    (args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print({key:report[key] for key in ('status','cases','seconds')})


if __name__=='__main__':main()
