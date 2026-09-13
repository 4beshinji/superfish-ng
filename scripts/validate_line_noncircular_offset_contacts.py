# SPDX-License-Identifier: Apache-2.0
"""Independent known contacts, normal displacements and global radius bounds."""
import argparse
from dataclasses import replace
from decimal import Decimal as D,localcontext
from fractions import Fraction as F
import itertools,json,math,time
from pathlib import Path
from validate_general_coincident_circle_arcs import decimal_value,phase_reference
from superfish_ng.conics import EllipseArc,HyperbolaArc,LineSegment,rotation_cos_sin
from superfish_ng.offset_degeneracies import classify_offset_degeneracies


def examples():
    for hyperbola,branch,angle,scale,distance,reverse,partial in itertools.product(
            (False,True),(-1,1),(0.,.3,.7,1.2),(2.**-160,1.,2.**160),
            (-1.,-.5,.25,.5,1.,5.),(False,True),(False,True)):
        if not hyperbola and branch != 1:continue
        c,s=rotation_cos_sin(angle);distance*=branch if hyperbola else 1
        center=(-2*(branch if hyperbola else 1)*c*scale,-2*(branch if hyperbola else 1)*s*scale)
        curve=(HyperbolaArc(center,(2*scale,scale),0.,.5,branch=branch,rotation_rad=angle) if hyperbola
               else EllipseArc(center,(2*scale,scale),0.,.5,angle))
        line=LineSegment((0,0),(-s*scale,c*scale))
        norm=(decimal_value(c)**2+decimal_value(s)**2).sqrt()
        normal=(-decimal_value(c)/norm,-decimal_value(s)/norm)
        point=tuple(decimal_value(distance*scale)*x for x in normal)
        minimum=norm/2;maximum=4*norm
        adjusted=D(branch*distance if hyperbola else distance)
        regular=(adjusted>=0 or abs(adjusted)<minimum) if hyperbola else adjusted<minimum or adjusted>maximum
        factor=1+(1 if hyperbola else -1)*adjusted*2/norm
        yield dict(name='vertex',curve=curve,line=line,distance=distance*scale,point=point,
                   parameter=D(0),span=D('.5'),regular=regular,factor=factor,reverse=reverse,partial=partial,scale=scale)
    for hyperbola,branch,scale,distance,reverse,partial in itertools.product(
            (False,True),(-1,1),(2.**-80,1.,2.**80),(-2.,.5,2.),(False,True),(False,True)):
        if not hyperbola and branch != 1:continue
        if hyperbola:
            a,b=3.,1.5;source=(5.*branch,2.);delta=(4.*branch,2.5)
            curve=HyperbolaArc((0,0),(a*scale,b*scale),0.,1.5,branch=branch)
            parameter=D(3).ln();distance*=branch
        else:
            a,b=5.,2.5;source=(3.,2.);delta=(-4.,1.5)
            curve=EllipseArc((0,0),(a*scale,b*scale),0.,1.5)
            parameter=phase_reference(F(3,5),F(4,5))
        line=LineSegment(tuple(x*scale for x in source),tuple((x+y)*scale for x,y in zip(source,delta)))
        norm=sum(D(x)**2 for x in delta).sqrt();normal=(-D(delta[1])/norm,D(delta[0])/norm)
        point=tuple((D(x)+D(distance)*n)*decimal_value(scale) for x,n in zip(source,normal))
        adjusted=D(branch*distance if hyperbola else distance)
        minimum=D(b)**2/D(a);maximum=D(a)**2/D(b)
        regular=(adjusted>=0 or abs(adjusted)<minimum) if hyperbola else adjusted<minimum or adjusted>maximum
        factor=1+(1 if hyperbola else -1)*adjusted*D(a)*D(b)/norm**3
        yield dict(name='rational-contact',curve=curve,line=line,distance=distance*scale,point=point,
                   parameter=parameter,span=D('1.5'),regular=regular,factor=factor,reverse=reverse,partial=partial,scale=scale)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    start=time.monotonic();records=[];counts={}
    with localcontext() as context:
        context.prec=160
        for case in examples():
            curve,line=case['curve'],case['line'];distances=[case['distance']]*2
            parameter=case['parameter']/case['span'];line_fraction=D(0)
            if case['reverse']:
                curve=(replace(curve,start_parameter=curve.end_parameter,end_parameter=curve.start_parameter)
                       if isinstance(curve,HyperbolaArc) else replace(curve,start_rad=curve.start_rad+curve.sweep_rad,sweep_rad=-curve.sweep_rad))
                line=LineSegment(line.end_zr_m,line.start_zr_m);distances=[-x for x in distances]
                parameter=1-parameter;line_fraction=D(1)
            domains=((F(1,2) if case['partial'] else F(0),F(1)),(F(0),F(1)))
            present=decimal_value(domains[0][0])<=parameter<=1 and 0<=line_fraction<=1
            expected=('SINGLE_TANGENCY' if present else 'DISJOINT') if case['regular'] else ('TANGENCY_WITNESSES' if present else 'UNVERIFIED')
            for exchange in (False,True):
                result=classify_offset_degeneracies(*( (line,curve) if exchange else (curve,line)),
                    first_distance_m=distances[1 if exchange else 0],second_distance_m=distances[0 if exchange else 1],
                    first_interval=domains[1 if exchange else 0],second_interval=domains[0 if exchange else 1])
                row=dict(index=len(records),family='hyperbola' if isinstance(curve,HyperbolaArc) else 'ellipse',
                         name=case['name'],scale=case['scale'],distance=case['distance'],reverse=case['reverse'],
                         partial=case['partial'],exchange=exchange,expected=expected,observed=result['classification'])
                try:
                    assert result['classification']==expected
                    assert result['finite_domain_complete']==case['regular']
                    assert result['finite_center_count']==(int(present) if case['regular'] else None)
                    contacts=[r for r in result['evidence']['source_tangent_contacts'] if r['incidence_sign']==0]
                    assert len(contacts)==1
                    actual=contacts[0]
                    assert actual['offset_speed_factor_sign']==(case['factor']>0)-(case['factor']<0)
                    uncertainty=decimal_value(case['scale'])*D('1e-110')
                    assert all(decimal_value(lo)-uncertainty<=value<=decimal_value(hi)+uncertainty
                               for (lo,hi),value in zip(actual['center_box_zr_m'],case['point']))
                    assert actual['parameter_pair_in_domain']==present
                except AssertionError:
                    (args.out/'failure.json').write_text(json.dumps(row,indent=2)+'\n');raise
                counts[expected]=counts.get(expected,0)+1;records.append(row)
    report=dict(passed=True,cases=len(records),classifications=counts,seconds=time.monotonic()-start,
                decimal_precision=160,reference='known source contacts, independent unit-normal displacement and curvature-radius inequalities',records=records)
    (args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='records'}))


if __name__=='__main__':main()
