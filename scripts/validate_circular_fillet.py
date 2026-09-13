# SPDX-License-Identifier: Apache-2.0
"""Independent Euclidean circles, source contacts, bounded output and FEM scaling."""
import argparse
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import hashlib
import itertools
import json
import math
from pathlib import Path
import time
import numpy as np
from validate_algebraic_conic_fillet import evaluate, rescale, reverse
from validate_algebraic_circular_offsets import model
from validate_general_coincident_circle_arcs import decimal_value as dec, phase_reference, reference_pi
from superfish_ng.conics import EllipseArc, curve_from_dict, curve_to_dict
from superfish_ng.circular_fillet import circular_fillet_candidates
from superfish_ng.tangent_construction import _json_value

ROOT = Path(__file__).resolve().parents[1]


def families():
    yield 'endpoint',EllipseArc((.875,.375),(1.25,1.25),-1.,1.),EllipseArc((0,0),(2,2),0.,1.),.625
    yield 'whole',EllipseArc((1.375,.625),(1.25,1.25),-1.,1.,-math.pi/2),EllipseArc((0,0),(2,2),0.,1.),.625
    for distance,separation in itertools.product((.25,-.5,2.25),(.75,2.25,4.5)):
        yield 'rotated',EllipseArc((0,0),(2,2),-3.,6.,.3),EllipseArc((separation,.375),(1.5,1.5),-3.,6.,.7),distance
    for ra,rb,separation,aa,ab in ((2.,2.,2.,0.,math.pi),(3.,2.,1.,0.,0.),(.5,.5,1.,math.pi,0.),(.5,1.5,1.,math.pi,math.pi)):
        yield 'tangent',EllipseArc((0,0),(ra,ra),-1.,2.,aa),EllipseArc((separation,0),(rb,rb),-1.,2.,ab),1.
    for delta in (-2**-30,0.,2**-30):
        yield 'near',EllipseArc((0,0),(2,2),-1.,2.),EllipseArc((2+delta,0),(2,2),-1.,2.,math.pi),1.
    a=EllipseArc((0,0),(3,3),-1.,1.);b=EllipseArc((0,0),(1,1),0.,1.,math.pi)
    yield 'shared-forward',a,b,2.
    yield 'shared-zero',a,replace(a,start_rad=0.),2.
    yield 'shared-rotated',replace(a,start_rad=-.75,rotation_rad=.3),replace(a,start_rad=.25,rotation_rad=.3),2.
    yield 'shared-overlap',replace(a,start_rad=-.5),replace(b,start_rad=-.5),2.
    yield 'rotated-overlap',replace(a,start_rad=-.5,rotation_rad=.3),replace(a,start_rad=-.5,rotation_rad=-.3),2.
    yield 'concentric-unequal',replace(a,rotation_rad=.3),replace(a,rotation_rad=.7),2.
    a=EllipseArc((1,0),(1,1),-.5,1.);b=EllipseArc((0,0),(2,2),-.5,1.)
    yield 'one-collapsed',a,b,1.
    yield 'collapsed-excluded',a,replace(b,start_rad=1.),1.
    yield 'two-collapsed',a,a,1.
    yield 'collapsed-disjoint',a,replace(a,center_zr_m=(3,0)),1.


def source_fraction(curve, m, point, pi):
    x,y=(p-c for p,c in zip(point,m['center']));c,s=m['rotation'];sign=1 if m['radius']>0 else -1
    phase=phase_reference(F(sign*(c*x+s*y)),F(sign*(-s*x+c*y)))
    accepted=[]
    for period in range(-4,5):
        f=(phase+2*period*pi-dec(curve.start_rad))/dec(curve.sweep_rad)
        if -D('1e-100')<=f<=1+D('1e-100'):
            accepted.append(D(0) if abs(f)<D('1e-100') else D(1) if abs(f-1)<D('1e-100') else f)
    assert len(accepted)<=1
    return accepted[0] if accepted else None


def reference(curves,distance,unit,pi):
    models=[model(c,distance) for c in curves];a,b=models;epsilon=dec(unit)*D('1e-100')
    delta=tuple(y-x for x,y in zip(a['center'],b['center']));separation=sum(x*x for x in delta).sqrt()
    radii=abs(a['radius']),abs(b['radius']);collapsed=[r<epsilon for r in radii]
    points=[]
    if any(collapsed):
        if all(collapsed):return ('infinite',[]) if separation<epsilon else ('finite',[])
        i=collapsed.index(True);point=models[i]['center'];other=models[1-i]
        gap=sum((x-y)**2 for x,y in zip(point,other['center'])).sqrt()
        if abs(gap-abs(other['radius']))<epsilon and source_fraction(curves[1-i],other,point,pi) is not None:
            return 'infinite',[]
        return 'finite',[]
    if separation<epsilon:
        if abs(radii[0]-radii[1])>epsilon:return 'finite',[]
        phases=[phase_reference(F(m['rotation'][0]),F(m['rotation'][1]))+(pi if m['radius']<0 else 0) for m in models]
        intervals=[sorted((dec(c.start_rad)+p,dec(c.start_rad)+dec(c.sweep_rad)+p)) for c,p in zip(curves,phases)]
        for period in range(-4,5):
            lo=max(intervals[0][0],intervals[1][0]+2*period*pi)
            hi=min(intervals[0][1],intervals[1][1]+2*period*pi)
            if hi-lo>D('1e-100'):return 'infinite',[]
            if abs(hi-lo)<D('1e-100'):
                fraction=(lo-phases[0]-dec(curves[0].start_rad))/dec(curves[0].sweep_rad)
                p,t=evaluate(curves[0],F(fraction));length=sum(x*x for x in t).sqrt()
                points.append((p[0]-dec(distance)*t[1]/length,p[1]+dec(distance)*t[0]/length))
    elif separation>sum(radii)+epsilon or separation<abs(radii[0]-radii[1])-epsilon:
        return 'finite',[]
    else:
        along=(radii[0]**2-radii[1]**2+separation**2)/(2*separation)
        height_squared=radii[0]**2-along**2
        assert height_squared>=-epsilon*dec(unit)
        height=D(0) if abs(height_squared)<epsilon*dec(unit) else height_squared.sqrt()
        direction=tuple(x/separation for x in delta)
        center=tuple(x+along*v for x,v in zip(a['center'],direction))
        points=[(center[0]-side*height*direction[1],center[1]+side*height*direction[0]) for side in ((-1,1) if height else (1,))]
    result=[]
    for point in points:
        fractions=[source_fraction(c,m,point,pi) for c,m in zip(curves,models)]
        if any(f is None for f in fractions):continue
        contacts=[evaluate(c,F(f))[0] for c,f in zip(curves,fractions)]
        result.append(dict(center=point,fractions=fractions,contacts=contacts))
    return 'finite',sorted(result,key=lambda r:r['fractions'])


def geometry_checks(out):
    records=[];pi=reference_pi()
    for family,(name,a,b,distance) in enumerate(families()):
        for variant,(unit,reversed_arcs,exchange) in enumerate(itertools.product((2.**-40,1.,2.**40),(False,True),(False,True))):
            curves=[rescale(c,unit) for c in (a,b)];d=distance*unit
            if reversed_arcs:curves=[reverse(c) for c in curves];d=-d
            if exchange:curves.reverse()
            kind,expected=reference(curves,d,unit,pi)
            settings=dict(radius_m=abs(d),turn_direction=1 if d>0 else -1,max_sweep_rad=6.2,
                          position_tolerance_m=1e-9*unit,angle_tolerance_rad=1e-8)
            actual=circular_fillet_candidates(*curves,**settings)
            path=out/f'geometry-{family}-{variant}.json'
            path.write_text(json.dumps(_json_value(dict(family=name,variant=variant,curves=[curve_to_dict(c) for c in curves],controls=settings,enumeration=actual)),indent=2)+'\n')
            assert actual['status']==('UNVERIFIED' if kind=='infinite' else 'PASS'),str(path)
            assert len(actual['candidates'])==len(expected),str(path)
            states={};epsilon=dec(unit)*D('1e-95')
            for row,target in zip(actual['candidates'],expected):
                state=row['connection_direction'];states[state]=states.get(state,0)+1
                for bounds,value in zip(row['root']['parameter_box'],target['fractions']):
                    assert dec(bounds[0])-D('1e-95')<=value<=dec(bounds[1])+D('1e-95'),str(path)
                for bounds,value in zip(row['root']['center_box_zr_m'],target['center']):
                    assert dec(bounds[0])-epsilon<=value<=dec(bounds[1])+epsilon,str(path)
                p,q=target['contacts'];zero=max(abs(x-y) for x,y in zip(p,q))<epsilon
                assert row['root']['source_contacts_coincide']==zero,str(path)
                if zero:assert state=='ZERO_LENGTH';continue
                if target['fractions'][0]==0 or target['fractions'][1]==1:assert state=='UNVERIFIED';continue
                center=target['center'];phases=[phase_reference(F(x[0]-center[0]),F(x[1]-center[1])) for x in (p,q)]
                sweep=settings['turn_direction']*(phases[1]-phases[0])
                while sweep<=0:sweep+=2*pi
                while sweep>2*pi:sweep-=2*pi
                if sweep>dec(settings['max_sweep_rad']):assert state=='SWEEP_LIMIT';continue
                assert state=='FORWARD',(str(path),row.get('construction_reason'))
                output=[curve_from_dict(x) for x in row['trimmed_curves']]
                assert output[1].semiaxes_m==(abs(d),abs(d))
                for point,trimmed,ff,endpoint,trim_bound,fillet_bound in zip((p,q),(output[0],output[2]),(0,1),(1,0),row['trim_contact_error_bounds_m'],row['fillet_contact_error_bounds_m']):
                    for position,bound in ((evaluate(trimmed,endpoint)[0],trim_bound),(evaluate(output[1],ff)[0],fillet_bound)):
                        error=sum((x-y)**2 for x,y in zip(position,point)).sqrt()
                        assert error<=dec(bound)+epsilon and bound<=settings['position_tolerance_m'],str(path)
                for left,right in zip(output,output[1:]):
                    u,v=evaluate(left,1)[1],evaluate(right,0)[1]
                    angle=abs(phase_reference(F(sum(x*y for x,y in zip(u,v))),F(u[0]*v[1]-u[1]*v[0])))
                    assert angle<=dec(settings['angle_tolerance_rad'])
            records.append(dict(family=name,variant=variant,scale=unit,reverse=reversed_arcs,exchange=exchange,kind=kind,source_pairs=len(expected),states=states))
        print(json.dumps(dict(family=name,conditions=len(records))),flush=True)
    return records


def fem_checks(out):
    from superfish_ng.tangent_construction import construct_tangent_case
    from superfish_ng.config import Case
    from superfish_ng.solver import solve
    from superfish_ng.rf import quantities
    request=json.loads((ROOT/'examples/construction/circular_fillet_request.json').read_text());solutions=[];reports=[]
    for unit in (1.,2.):
        r=deepcopy(request)
        for curve in r['case_template']['geometry']['curves']:
            for key in ('start_zr_m','end_zr_m','center_zr_m','semiaxes_m'):
                if key in curve:curve[key]=[unit*x for x in curve[key]]
        for key in ('join_tolerance_m','minimum_gap_m','chord_tolerance_m'):r['case_template']['geometry'][key]*=unit
        r['case_template']['mesh']['contour_mesh']['max_edge_m']*=unit
        for key in ('radius_m','position_tolerance_m'):r['controls'][key]*=unit
        document=construct_tangent_case(r,candidate_index=0);case=Case.from_dict(document['case']);solution=solve(case);rf=quantities(case,solution)
        (out/f'constructed-{int(unit)}.json').write_text(json.dumps(document,indent=2)+'\n')
        (out/f'rf-{int(unit)}.json').write_text(json.dumps(rf,indent=2)+'\n')
        solutions.append(solution);reports.append(rf)
    a,b=solutions
    np.testing.assert_allclose(b.space.geometry.points_rz_m,2*a.space.geometry.points_rz_m,rtol=1e-13,atol=1e-15)
    np.testing.assert_array_equal(b.space.geometry.cell_nodes,a.space.geometry.cell_nodes)
    correlation=abs(np.dot(a.u[:,0],b.u[:,0]))/(np.linalg.norm(a.u[:,0])*np.linalg.norm(b.u[:,0]))
    assert 1-correlation<1e-10
    ratios={key:reports[1][key]/reports[0][key] for key in ('frequency_hz','r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm','transit_time_factor_abs')}
    assert abs(ratios['frequency_hz']-.5)<1e-10
    assert all(abs(value-1)<1e-9 for key,value in ratios.items() if key!='frequency_hz')
    np.savez(out/'field-shape-scaling.npz',first=a.u,second=b.u,first_points=a.space.geometry.points_rz_m,second_points=b.space.geometry.points_rz_m,cell_nodes=a.space.geometry.cell_nodes)
    return dict(ratios=ratios,coefficient_shape_correlation=float(correlation),nodes=len(a.space.geometry.points_rz_m),scope='constructed synthetic geometry at scales 1 and 2; invariant checks, not discretization-error bounds')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);parser.add_argument('--only',choices=('geometry','fem','all'),default='all')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False);start=time.monotonic()
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'src').rglob('*')) if p.is_file() and p.suffix in ('.py','.js','.html','.css')}
    before=hashes();geometry=[]
    if args.only!='fem':
        with localcontext() as context:
            context.prec=160;geometry=geometry_checks(args.out)
        (args.out/'geometry-report.json').write_text(json.dumps(dict(passed=True,geometry=geometry,source_sha256=before),indent=2)+'\n')
    fem=fem_checks(args.out) if args.only!='geometry' else None
    assert hashes()==before
    report=dict(passed=True,seconds=time.monotonic()-start,selection=args.only,geometry_cases=len(geometry),source_pairs=sum(r['source_pairs'] for r in geometry),geometry=geometry,fem_scaling=fem,source_sha256=before,source_changed_during_run=False,decimal_precision=160)
    (args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('passed','seconds','geometry_cases','source_pairs')}))


if __name__=='__main__':main()
