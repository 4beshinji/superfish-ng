# SPDX-License-Identifier: Apache-2.0
"""Independent original-parameter conic incidence, stationary points and cusps.

Two sampling densities bracket the source-gradient zeros independently of the
product's eliminated incidence polynomial. Decimal Newton and bisection refine
these numerical references; their own completeness is not a proof certificate.
"""
import argparse
from dataclasses import replace
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import time
import numpy as np
from validate_general_coincident_circle_arcs import decimal_value as dec, phase_reference, sine_cosine, reference_pi
from validate_circle_conic_crossings import rotation
from validate_algebraic_conic_fillet import rescale, reverse
from superfish_ng.conics import EllipseArc, HyperbolaArc, curve_to_dict
from superfish_ng.conic_implicit_offset import classify_conic_implicit_offset
from superfish_ng.tangent_construction import _json_value

ROOT=Path(__file__).resolve().parents[1]


def reference(curve,target,distance,domains,unit):
    unit=dec(unit);ellipse=isinstance(curve,EllipseArc);branch=1 if ellipse else curve.branch
    a,b=[dec(x)/unit for x in curve.semiaxes_m];ta,tb=[dec(x)/unit for x in target.semiaxes_m]
    c,s=rotation(curve.rotation_rad);tc,ts=rotation(target.rotation_rad);n=c*c+s*s;k=tc*tc+ts*ts
    center,origin=[tuple(dec(x)/unit for x in p) for p in (curve.center_zr_m,target.center_zr_m)]
    start=dec(curve.start_rad if ellipse else curve.start_parameter)
    span=dec(curve.sweep_rad) if ellipse else dec(curve.end_parameter)-start
    low,high=sorted(start+span*dec(t) for t in domains[0]);d=dec(distance)/unit*(1 if span>0 else -1)
    epsilon=D(1 if isinstance(target,EllipseArc) else -1);curvature=a*b*n*(1 if ellipse else -branch)
    pi=reference_pi();tolerance=D('1e-85')
    def bilinear(u,v):
        return ((tc*u[0]+ts*u[1])*(tc*v[0]+ts*v[1])/(ta*ta)+epsilon*(-ts*u[0]+tc*u[1])*(-ts*v[0]+tc*v[1])/(tb*tb))/(k*k)
    def evaluate(t):
        sn,co=sine_cosine(t) if ellipse else ((t.exp()-(-t).exp())/2,(t.exp()+(-t).exp())/2)
        x,y=branch*a*co,b*sn;dx,dy=(-a*sn if ellipse else branch*a*sn),b*co
        vector=(c*x-s*y,s*x+c*y);v=(c*dx-s*dy,s*dx+c*dy);acc=tuple((-1 if ellipse else 1)*z for z in vector)
        speed=sum(z*z for z in v).sqrt();factor=1-d*curvature/speed**3
        point=(center[0]+vector[0]-d*v[1]/speed,center[1]+vector[1]+d*v[0]/speed)
        w=tuple(z-o for z,o in zip(point,origin));g=bilinear(v,w)
        return bilinear(w,w)-1,point,factor,g,bilinear(acc,w)+factor*bilinear(v,v),(branch*co,sn)
    def grid(count):
        t=np.linspace(float(low),float(high),count+1);sn,co=(np.sin(t),np.cos(t)) if ellipse else (np.sinh(t),np.cosh(t))
        aa,bb,cc,ss,dd=map(float,(a,b,c,s,d));ttc,tts,tta,ttb,kk=map(float,(tc,ts,ta,tb,k))
        x,y=branch*aa*co,bb*sn;dx,dy=(-aa*sn if ellipse else branch*aa*sn),bb*co
        vx,vy=cc*dx-ss*dy,ss*dx+cc*dy;speed=np.hypot(vx,vy)
        wx=float(center[0]-origin[0])+cc*x-ss*y-dd*vy/speed;wy=float(center[1]-origin[1])+ss*x+cc*y+dd*vx/speed
        g=((ttc*vx+tts*vy)*(ttc*wx+tts*wy)/(tta*tta)+float(epsilon)*(-tts*vx+ttc*vy)*(-tts*wx+ttc*wy)/(ttb*ttb))/(kk*kk)
        seeds=[(float(x)+float(y))/2 for x,y,left,right in zip(t,t[1:],g,g[1:]) if left*right<0]
        scale=max(abs(g));assert scale>1e-25,'constant or near-constant gradient requires an independent special reference'
        seeds += [float(t[i]) for i in np.flatnonzero(np.abs(g)<scale*1e-13)]
        result=[]
        for seed in seeds:
            value=D.from_float(seed)
            for _ in range(50):
                _,_,_,g,dg,_=evaluate(value)
                if abs(g)<D('1e-125'):break
                assert dg!=0,'multiple stationary root needs a dedicated reference'
                value-=g/dg
            assert abs(evaluate(value)[3])<D('1e-115')
            if low-tolerance<=value<=high+tolerance and not any(abs(value-v)<tolerance for v in result):result.append(value)
        return sorted(result)
    coarse,fine=grid(1024),grid(2048)
    assert len(coarse)==len(fine) and all(abs(a-b)<tolerance for a,b in zip(coarse,fine)),'stationary reference changes with sampling density'
    critical=[low,high,*[x for x in fine if low<x<high]]
    def add_parameter(t):
        for period in (range(-4,5) if ellipse else (0,)):
            value=t+2*period*pi
            if low<value<high:critical.append(value)
    # Known axes supplement stationary roots of higher multiplicity.
    for t in ((D(0),pi/2,-pi/2,pi,-pi) if ellipse else (D(0),)):
        if abs(evaluate(t)[3])<D('1e-115'):add_parameter(t)
    if d*curvature>0:
        speed_squared=(2*(d*curvature).ln()/3).exp();q=(speed_squared/n-b*b)/(a*a-b*b if ellipse else a*a+b*b)
        if abs(q)<tolerance:q=D(0)
        if abs(q-1)<tolerance:q=D(1)
        if ellipse and 0<=q<=1:
            angle=phase_reference(F((1-q).sqrt()),F(q.sqrt()))
            for t in (angle,-angle,pi-angle,pi+angle):add_parameter(t)
        elif not ellipse and q>=0:
            t=(q.sqrt()+(1+q).sqrt()).ln();add_parameter(t);add_parameter(-t)
    critical.sort();unique=[]
    for t in critical:
        if not unique or t-unique[-1]>tolerance:unique.append(t)
    def sign(x):return 0 if abs(x)<tolerance else 1 if x>0 else -1
    values=[evaluate(t)[0] for t in unique];parameters=[t for t,value in zip(unique,values) if sign(value)==0]
    for lo,hi,left,right in zip(unique,unique[1:],values,values[1:]):
        if sign(left)*sign(right)!=-1:continue
        for _ in range(370):
            mid=(lo+hi)/2;value=evaluate(mid)[0]
            if value==0:lo=hi=mid;break
            if (left>0)==(value>0):lo,left=mid,value
            else:hi=mid
        assert hi-lo<D('1e-105');parameters.append((lo+hi)/2)
    target_start=dec(target.start_rad if isinstance(target,EllipseArc) else target.start_parameter)
    target_span=dec(target.sweep_rad) if isinstance(target,EllipseArc) else dec(target.end_parameter)-target_start
    target_range=sorted(target_start+target_span*dec(t) for t in domains[1]);accepted=[]
    for parameter in sorted(parameters):
        residual,point,factor,g,_,local=evaluate(parameter);assert abs(residual)<tolerance
        w=tuple(z-o for z,o in zip(point,origin));target_local=((tc*w[0]+ts*w[1])/(k*ta),(-ts*w[0]+tc*w[1])/(k*tb))
        if isinstance(target,EllipseArc):
            phase=phase_reference(F(target_local[0]),F(target_local[1]))
            if not any(target_range[0]-tolerance<=phase+2*j*pi<=target_range[1]+tolerance for j in range(-4,5)):continue
        else:
            if target_local[0]*target.branch<=0:continue
            y=target_local[1];phase=(y+(1+y*y).sqrt()).ln()
            if not target_range[0]-tolerance<=phase<=target_range[1]+tolerance:continue
        kind='CUSP' if sign(factor)==0 else 'REGULAR_TANGENCY' if sign(g)==0 else 'TRANSVERSE'
        accepted.append(dict(parameter=parameter,point=tuple(x*unit for x in point),kind=kind,local=local,target_local=target_local))
    groups=[]
    for i,row in enumerate(accepted):
        for group in groups:
            if max(abs(x-y) for x,y in zip(row['point'],accepted[group[0]]['point']))<unit*tolerance:group.append(i);break
        else:groups.append([i])
    return accepted,groups,len(unique)-1,len(fine)


def families():
    ell=EllipseArc((0,0),(2,1),-3.,6.)
    yield 'ellipse-zero',ell,EllipseArc((0,0),(1,2),-3.,6.),0.,((0,1),(0,1))
    for branch in (-1,1):
        yield 'ellipse-hyperbola-zero',ell,HyperbolaArc((0,0),(1,1),-2.,2.,branch=branch),0.,((0,1),(0,1))
        yield 'hyperbolas-zero',HyperbolaArc((0,0),(1,1),-2.,2.,branch=branch),HyperbolaArc((0,0),(2,3),-2.5,2.5,branch=branch),0.,((0,1),(0,1))
        yield 'hyperbola-offset',HyperbolaArc((0,0),(2,1),-2.,2.,branch=branch),EllipseArc((0,0),(3,2),-3.,6.),-.5*branch,((0,1),(0,1))
    for d in (-.25,.25,1.,3.):
        yield 'ellipse-offset',ell,EllipseArc((0,0),(1,2),-3.,6.),d,((0,1),(0,1))
    yield 'cusp',replace(ell,start_rad=-.5,sweep_rad=1.),EllipseArc((0,0),(1.5,.75),-.5,1.),.5,((0,1),(0,1))
    yield 'same-center',replace(ell,start_rad=-.1,sweep_rad=3.4),EllipseArc((1,0),(1,.5),-.5,1.,math.pi),2.,((0,1),(0,1))
    yield 'endpoint',replace(ell,start_rad=0.,sweep_rad=1.),EllipseArc((0,0),(1.75,.5),0.,1.),.25,((0,1),(0,1))
    yield 'extraneous',replace(ell,start_rad=0.,sweep_rad=1.),EllipseArc((0,0),(2.25,1.5),0.,1.),.25,((0,1),(0,1))
    yield 'offset-hyperbola',ell,HyperbolaArc((0,0),(1,1),-2.,2.),.25,((0,1),(0,1))
    yield 'restricted',ell,EllipseArc((0,0),(1,2),-3.,6.),0.,((F(1,4),F(3,4)),(F(1,8),F(7,8)))
    yield 'rotated-zero',replace(ell,rotation_rad=.3),EllipseArc((0,0),(1,2),-3.,6.,.3),0.,((0,1),(0,1))
    yield 'general-ellipse',replace(ell,rotation_rad=.3),EllipseArc((.25,.125),(1.5,1.25),-3.,6.,.7),.25,((0,1),(0,1))
    yield 'general-hyperbola',HyperbolaArc((.125,-.25),(2,1),-2.,2.,branch=-1,rotation_rad=.3),EllipseArc((0,0),(3,2),-3.,6.,.7),.5,((0,1),(0,1))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);parser.add_argument('--family')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False);start=time.monotonic();records=[]
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'src').rglob('*')) if p.is_file() and p.suffix in ('.py','.js','.html','.css')}
    before=hashes()
    with localcontext() as context:
        context.prec=140
        for family,(name,a,b,distance,domain) in enumerate(families()):
            if args.family and name!=args.family:continue
            for variant in range(4):
                unit=(2.**-40,1.,2.**40,1.)[variant];curves=[rescale(c,unit) for c in (a,b)];distances=(distance*unit,0.);domains=domain
                if variant==1:curves=[reverse(c) for c in curves];distances=tuple(-d for d in distances);domains=tuple((1-hi,1-lo) for lo,hi in domains)
                exchange=variant%2==1
                if exchange:curves.reverse();distances=distances[::-1];domains=domains[::-1]
                target_index=1 if distances[1]==0 else 0;source_index=1-target_index
                expected,groups,intervals,stationary=reference(curves[source_index],curves[target_index],distances[source_index],(domains[source_index],domains[target_index]),unit)
                actual=classify_conic_implicit_offset(curves,distances,domains,endpoint_width=F(1,2**100),max_series_terms=96)
                row=dict(family=name,variant=variant,scale=unit,exchange=exchange,reference_intervals=intervals,reference_stationary_points=stationary,expected_sources=len(expected),expected_centers=len(groups),curves=[curve_to_dict(c) for c in curves],distances=distances,domains=domains,diagnosis=actual)
                path=args.out/f'case-{family}-{variant}.json';path.write_text(json.dumps(_json_value(row),indent=2)+'\n')
                assert actual['complete'],(str(path),actual['evidence']['unresolved'])
                found=actual['evidence']['intersections'];assert len(found)==len(expected) and actual['centers']==len(groups),(str(path),len(found),len(expected),actual['centers'],len(groups))
                matched=set();tolerance=dec(unit)*D('1e-95')
                for target in expected:
                    indices=[i for i,item in enumerate(found) if i not in matched and item['contact_kind']==target['kind'] and
                        all(dec(lo)-tolerance<=value<=dec(hi)+tolerance for (lo,hi),value in zip(item['center_box_zr_m'],target['point'])) and
                        all(dec(lo)-D('1e-95')<=value<=dec(hi)+D('1e-95') for (lo,hi),value in zip(item['source_local_box'],target['local']))]
                    assert len(indices)==1,(str(path),target['kind'],target['point']);matched.add(indices[0])
                    assert all(dec(lo)-D('1e-95')<=value<=dec(hi)+D('1e-95') for (lo,hi),value in zip(found[indices[0]]['target_source_local_box'],target['target_local']))
                records.append(dict(family=name,variant=variant,scale=unit,sources=len(found),centers=actual['centers'],kinds=[r['contact_kind'] for r in found],reference_intervals=intervals))
                print(json.dumps(dict(conditions=len(records),family=name,variant=variant)),flush=True)
    assert hashes()==before
    report=dict(passed=True,seconds=time.monotonic()-start,conditions=len(records),source_pairs=sum(r['sources'] for r in records),records=records,decimal_precision=140,source_sha256=before,source_changed_during_run=False,reference='original conic equations; two gradient sampling densities, Decimal Newton, analytic curvature cusps and monotone bisection; numerical reference only')
    (args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k] for k in ('passed','seconds','conditions','source_pairs')}))


if __name__=='__main__':main()
