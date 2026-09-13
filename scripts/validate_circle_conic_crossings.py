# SPDX-License-Identifier: Apache-2.0
"""Independent Decimal original-curve distance extrema and intersection checks.

Stationary distances use a separate quartic and direct-parameter Newton
refinement. Cusp parameters are obtained from the original curvature formula.
The product's rational charts, eliminated incidence and Sturm code are unused
by the reference. This is a high-precision numerical comparison, not a proof
certificate for the reference's own root approximations.
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
from superfish_ng.conics import EllipseArc, HyperbolaArc, curve_to_dict
from superfish_ng.circle_conic_crossings import classify_circle_conic_crossings
from superfish_ng.tangent_construction import _json_value

ROOT = Path(__file__).resolve().parents[1]


def rotation(angle):
    quarter = round(angle/(math.pi/2))
    pair = ((1,0),(0,1),(-1,0),(0,-1))[quarter % 4] if angle == quarter*(math.pi/2) else (math.cos(angle), math.sin(angle))
    return tuple(map(dec, pair))


def reference(curve, circle, distances, domains, unit):
    unit = dec(unit); ellipse = isinstance(curve, EllipseArc); branch = 1 if ellipse else curve.branch
    c, s = rotation(curve.rotation_rad); cc, cs = rotation(circle.rotation_rad)
    n, k = c*c+s*s, cc*cc+cs*cs
    a, b = [dec(x)/unit for x in curve.semiaxes_m]
    center, origin = [tuple(dec(x)/unit for x in p) for p in (curve.center_zr_m, circle.center_zr_m)]
    delta = tuple(x-y for x,y in zip(center,origin)); u, v = c*delta[0]+s*delta[1], -s*delta[0]+c*delta[1]
    start = dec(curve.start_rad if ellipse else curve.start_parameter)
    span = dec(curve.sweep_rad) if ellipse else dec(curve.end_parameter)-start
    low, high = sorted(start+span*dec(t) for t in domains[0])
    distance = dec(distances[0])/unit*(1 if span > 0 else -1)
    cd = dec(distances[1])/unit*(1 if circle.sweep_rad > 0 else -1)
    rho = dec(circle.semiaxes_m[0])/unit*k.sqrt()-cd
    curvature = a*b*n*(1 if ellipse else -branch)
    tolerance = D('1e-85'); pi = reference_pi()
    def trigonometry(t):
        return sine_cosine(t) if ellipse else ((t.exp()-(-t).exp())/2, (t.exp()+(-t).exp())/2)
    def stationary(t):
        sn, co = trigonometry(t)
        if ellipse:
            z = n*(b*b-a*a)
            return z*sn*co-a*u*sn+b*v*co, z*(co*co-sn*sn)-a*u*co-b*v*sn
        z = n*(a*a+b*b)
        return z*sn*co+branch*a*u*sn+b*v*co, z*(co*co+sn*sn)+branch*a*u*co+b*v*sn
    def evaluate(t):
        sn, co = trigonometry(t)
        x, y = branch*a*co, b*sn
        dx, dy = (-a*sn if ellipse else branch*a*sn), b*co
        tx, ty = c*dx-s*dy, s*dx+c*dy; speed = (tx*tx+ty*ty).sqrt()
        point = center[0]+c*x-s*y-distance*ty/speed, center[1]+s*x+c*y+distance*tx/speed
        value = sum((x-y)**2 for x,y in zip(point, origin))-rho*rho
        return value, point, 1-distance*curvature/speed**3, stationary(t)[0]
    critical = [low, high]
    def add_parameter(t):
        for turn in (range(-4, 5) if ellipse else (0,)):
            value = t+2*turn*pi
            if low < value < high: critical.append(value)
    if ellipse:
        z = n*(b*b-a*a)
        coefficients = [b*v, 2*(z-a*u), D(0), -2*(z+a*u), -b*v]
        if v == 0: add_parameter(pi)
    else:
        z = n*(a*a+b*b)
        coefficients = [-z, 2*(-branch*a*u+b*v), D(0), 2*(branch*a*u+b*v), z]
    while coefficients[-1] == 0: coefficients.pop()
    magnitude = max(map(abs, coefficients))
    roots = np.polynomial.polynomial.polyroots([float(x/magnitude) for x in coefficients])
    for root in roots:
        if abs(root.imag) > 1e-9 or not ellipse and root.real <= 0: continue
        t = D.from_float(2*math.atan(root.real)) if ellipse else D.from_float(math.log(root.real))
        for _ in range(40):
            value, derivative = stationary(t)
            if abs(value) < D('1e-125'): break
            assert derivative != 0, 'independent stationary root needs a multiple-root reference'
            t -= value/derivative
        assert abs(stationary(t)[0]) < D('1e-115')
        add_parameter(t)
    if distance*curvature > 0:
        speed_squared = (2*(distance*curvature).ln()/3).exp()
        q = (speed_squared/n-b*b)/(a*a-b*b if ellipse else a*a+b*b)
        if abs(q) < tolerance: q = D(0)
        if abs(q-1) < tolerance: q = D(1)
        if ellipse and 0 <= q <= 1:
            angle = phase_reference(F((1-q).sqrt()), F(q.sqrt()))
            for t in (angle, -angle, pi-angle, pi+angle): add_parameter(t)
        elif not ellipse and q >= 0:
            t = (q.sqrt()+(1+q).sqrt()).ln(); add_parameter(t); add_parameter(-t)
    critical.sort(); unique = []
    for t in critical:
        if not unique or t-unique[-1] > tolerance: unique.append(t)
    def sign(x): return 0 if abs(x) < tolerance else 1 if x > 0 else -1
    values = [evaluate(t)[0] for t in unique]
    parameters = [t for t,value in zip(unique,values) if sign(value) == 0]
    for lo,hi,left,right in zip(unique,unique[1:],values,values[1:]):
        if sign(left)*sign(right) != -1: continue
        for _ in range(370):
            mid = (lo+hi)/2; value = evaluate(mid)[0]
            if value == 0: lo = hi = mid; break
            if (left > 0) == (value > 0): lo,left = mid,value
            else: hi = mid
        assert hi-lo < D('1e-105'); parameters.append((lo+hi)/2)
    circle_endpoints = sorted(dec(circle.start_rad)+dec(circle.sweep_rad)*dec(t) for t in domains[1])
    accepted = []
    for t in sorted(parameters):
        residual,point,factor,tangent = evaluate(t); assert abs(residual) < tolerance
        if abs(rho) >= tolerance:
            x,y = (point[0]-origin[0], point[1]-origin[1])
            local = ((cc*x+cs*y)/(rho*k.sqrt()), (-cs*x+cc*y)/(rho*k.sqrt()))
            phase = phase_reference(F(local[0]),F(local[1]))
            if not any(circle_endpoints[0]-tolerance <= phase+2*j*pi <= circle_endpoints[1]+tolerance for j in range(-4,5)): continue
        kind = 'COLLAPSED_CIRCLE' if abs(rho) < tolerance else 'CUSP' if sign(factor) == 0 else 'REGULAR_TANGENCY' if sign(tangent) == 0 else 'TRANSVERSE'
        accepted.append(dict(parameter=t, point=tuple(x*unit for x in point), kind=kind))
    groups = []
    for i,row in enumerate(accepted):
        for group in groups:
            if max(abs(x-y) for x,y in zip(row['point'],accepted[group[0]]['point'])) < unit*tolerance:
                group.append(i); break
        else: groups.append([i])
    return accepted,groups,len(unique)-1,abs(rho) < tolerance


def cases():
    for unit in (2.**-60,1.,2.**60):
        for distance in (-.5,.25,.5,1.,2.,4.):
            for cd in (.125,2.):
                yield 'centered',EllipseArc((0,0),(2*unit,unit),-3.,6.),EllipseArc((0,0),(1.5*unit,1.5*unit),-3.,6.),(distance*unit,cd*unit),((0,1),(0,1)),unit
        for branch in (-1,1):
            yield 'hyperbola',HyperbolaArc((0,0),(2*unit,unit),-2.,2.,branch=branch),EllipseArc((0,0),(3*unit,3*unit),-.1,6.2),(-.5*branch*unit,.125*unit),((0,1),(0,1)),unit
    for angle,cd in ((.3,0.),(.3,.125)):
        yield 'general',EllipseArc((0,0),(2,1),-3.,6.,.3),EllipseArc((.25,.125),(1.5,1.5),-3.,6.,angle),(.25,cd),((0,1),(0,1)),1.
    yield 'general',HyperbolaArc((.125,-.25),(2,1),-2.,2.,branch=-1,rotation_rad=.3),EllipseArc((0,0),(3,3),-.1,6.2,.3),(.5,.125),((0,1),(0,1)),1.
    yield 'endpoint',EllipseArc((0,0),(2,1),0.,1.),EllipseArc((1,0),(1,1),0.,1.),(.25,.25),((0,1),(0,1)),1.
    yield 'cusp',EllipseArc((0,0),(2,1),-.1,3.4),EllipseArc((1.5,-1),(1,1),-3.,6.),(.5,0.),((0,1),(0,1)),1.
    yield 'self-center',EllipseArc((0,0),(2,1),-.1,3.4),EllipseArc((1,0),(1,1),-.1,6.2),(2.,0.),((0,1),(0,1)),1.
    yield 'collapsed',EllipseArc((0,0),(2,1),0.,1.),EllipseArc((2,0),(1,1),-.3,1.),(0.,1.),((0,1),(0,1)),1.
    yield 'restricted',EllipseArc((0,0),(2,1),-3.,6.),EllipseArc((0,0),(1.5,1.5),-3.,6.),(.25,.125),((F(1,4),F(3,4)),(F(1,8),F(7,8))),1.
    yield 'collapsed',EllipseArc((0,0),(2,1),0.,1.),EllipseArc((3,0),(1,1),-.3,1.),(0.,1.),((0,1),(0,1)),1.
    yield 'collapsed',EllipseArc((0,0),(2,1),0.,1.),EllipseArc((2,0),(1,1),-.3,1.),(0.,1.),((F(1,4),1),(0,1)),1.
    yield 'negative-rotated',EllipseArc((0,0),(2,1),-3.,6.,.3),EllipseArc((0,0),(1.5,1.5),-3.,6.,.7),(.25,2.75),((0,1),(0,1)),1.


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--family'); args = parser.parse_args(); args.out.mkdir(parents=True,exist_ok=False)
    def hashes():
        return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'src').rglob('*')) if p.is_file() and p.suffix in ('.py','.js','.html','.css')}
    before = hashes(); start = time.monotonic(); records = []
    with localcontext() as context:
        context.prec = 140
        for index,(family,curve,circle,distances,domains,unit) in enumerate(cases()):
            if args.family and family != args.family: continue
            reverse = index % 2 == 1; exchange = index % 3 == 1
            if reverse:
                curve = replace(curve,start_rad=curve.start_rad+curve.sweep_rad,sweep_rad=-curve.sweep_rad) if isinstance(curve,EllipseArc) else replace(curve,start_parameter=curve.end_parameter,end_parameter=curve.start_parameter)
                circle = replace(circle,start_rad=circle.start_rad+circle.sweep_rad,sweep_rad=-circle.sweep_rad)
                distances = tuple(-d for d in distances); domains = tuple((1-b,1-a) for a,b in domains)
            expected,groups,intervals,collapsed = reference(curve,circle,distances,domains,unit)
            result = classify_circle_conic_crossings((circle,curve) if exchange else (curve,circle),distances[::-1] if exchange else distances,
                domains[::-1] if exchange else domains,endpoint_width=F(1,2**100),max_series_terms=96)
            evidence = result['evidence']; found = evidence['intersections']; tolerance = dec(unit)*D('1e-95')
            row = dict(index=index,family=family,reverse=reverse,exchange=exchange,scale=unit,centers=result['centers'],expected_centers=len(groups),
                sources=len(found),expected_sources=len(expected),reference_monotone_intervals=intervals,
                curves=[curve_to_dict(curve),curve_to_dict(circle)],distances=distances,domains=domains,diagnosis=result)
            (args.out/f'case-{index}.json').write_text(json.dumps(_json_value(row),indent=2)+'\n')
            assert result['complete'],evidence['unresolved']
            assert result['centers']==len(groups) and len(found)==len(expected),(index,len(groups),len(expected),result['centers'],len(found))
            assert result['infinite']==bool(collapsed and expected)
            assert evidence['circle_collapsed']==collapsed
            matched = set()
            for target in expected:
                indices = [i for i,item in enumerate(found) if all(dec(lo)-tolerance <= value <= dec(hi)+tolerance for (lo,hi),value in zip(item['center_box_zr_m'],target['point'])) and item['contact_kind']==target['kind'] and i not in matched]
                assert indices,(index,target['kind'],target['point'])
                matched.add(indices[0])
            records.append({k:v for k,v in row.items() if k not in ('diagnosis','curves')})
            print(json.dumps(dict(passed_cases=len(records),index=index,family=family,seconds=time.monotonic()-start)),flush=True)
    assert hashes()==before
    report = dict(passed=True,conditions=len(records),seconds=time.monotonic()-start,decimal_precision=140,records=records,source_sha256=before,source_changed_during_run=False)
    (args.out/'report.json').write_text(json.dumps(_json_value(report),indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('passed','conditions','seconds')}))


if __name__=='__main__': main()
