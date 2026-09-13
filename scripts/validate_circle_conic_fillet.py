# SPDX-License-Identifier: Apache-2.0
"""Independent circular/conic source pairs, output geometry and real FEM scaling."""
import argparse
from copy import deepcopy
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import time
import numpy as np
from validate_circle_conic_crossings import reference, rotation
from validate_algebraic_conic_fillet import evaluate, rescale, reverse
from validate_general_coincident_circle_arcs import decimal_value as dec, phase_reference, reference_pi
from superfish_ng.conics import EllipseArc, HyperbolaArc, curve_from_dict, curve_to_dict
from superfish_ng.circle_conic_fillet import circle_conic_fillet_candidates
from superfish_ng.tangent_construction import _json_value

ROOT = Path(__file__).resolve().parents[1]


def families():
    for b in (1.,1.5):
        yield 'endpoint',EllipseArc((.875,.375),(1.25,1.25),-1.,1.),EllipseArc((0,0),(2,b),0.,1.),.625
    yield 'whole',EllipseArc((1.375,.625),(1.25,1.25),-1.,1.,-math.pi/2),EllipseArc((0,0),(2,1),0.,1.),.625
    yield 'cusp',EllipseArc((1.5,-1.5),(2,2),-3.,6.),EllipseArc((0,0),(2,1),-.1,3.4),.5
    yield 'shared',EllipseArc((1,0),(3,3),-.1,6.2),EllipseArc((0,0),(2,1),-.1,3.4),2.
    yield 'negative',EllipseArc((0,0),(1.5,1.5),-3.,6.),EllipseArc((0,0),(2,1),-3.,6.),2.
    yield 'hyperbola',EllipseArc((1.25,-.75),(1,1),0.,1.),HyperbolaArc((0,0),(2,1),0.,1.),-.25
    yield 'hyperbola',EllipseArc((-3.25,.75),(1.5,1.5),-1.,1.),HyperbolaArc((0,0),(2,1),0.,1.,branch=-1),.25
    for d in (.25,2.):
        yield 'rotated',EllipseArc((0,0),(1.5,1.5),-3.,6.,.7),EllipseArc((0,0),(2,1),-3.,6.,.3),d
    yield 'translated',EllipseArc((.25,.125),(1.5,1.5),-3.,6.),EllipseArc((0,0),(2,1),-3.,6.,.3),.25


def geometry_checks(out):
    records=[];pi=reference_pi()
    for family,(name,circle,arc,distance) in enumerate(families()):
        for variant in range(4):
            unit=(2.**-40,1.,2.**40,1.)[variant]
            c,a=rescale(circle,unit),rescale(arc,unit);d=distance*unit
            if variant==1:c,a,d=reverse(c),reverse(a),-d
            circle_first=variant%2==0;curves=(c,a) if circle_first else (a,c)
            expected,groups,_,collapsed=reference(a,c,(d,d),((0,1),(0,1)),unit)
            assert not collapsed
            start=dec(a.start_rad if isinstance(a,EllipseArc) else a.start_parameter)
            span=dec(a.sweep_rad) if isinstance(a,EllipseArc) else dec(a.end_parameter)-start
            cc,cs=rotation(c.rotation_rad);norm=(cc*cc+cs*cs).sqrt()
            rho=dec(c.semiaxes_m[0])*norm-dec(d)*(1 if c.sweep_rad>0 else -1)
            circle_start,circle_span=dec(c.start_rad),dec(c.sweep_rad)
            for row in expected:
                x,y=(value-dec(origin) for value,origin in zip(row['point'],c.center_zr_m))
                local=((cc*x+cs*y)/(rho*norm),(-cs*x+cc*y)/(rho*norm))
                angle=phase_reference(F(local[0]),F(local[1]))
                candidates=[(angle+2*j*pi-circle_start)/circle_span for j in range(-4,5)]
                accepted=[f for f in candidates if -D('1e-85')<=f<=1+D('1e-85')]
                assert len(accepted)==1
                cf,af=accepted[0],(row['parameter']-start)/span
                row['fractions']=(cf,af) if circle_first else (af,cf)
                row['contacts']=tuple(evaluate(curve,F(f))[0] for curve,f in zip(curves,row['fractions']))
            coordinate=0 if circle_first else 1
            for group in groups:
                common=sum(expected[i]['fractions'][coordinate] for i in group)/len(group)
                for i in group:
                    fractions=list(expected[i]['fractions']);fractions[coordinate]=common;expected[i]['fractions']=tuple(fractions)
            expected.sort(key=lambda r:r['fractions'])
            settings=dict(radius_m=abs(d),turn_direction=1 if d>0 else -1,max_sweep_rad=5.9,
                          position_tolerance_m=1e-9*unit,angle_tolerance_rad=1e-8)
            result=circle_conic_fillet_candidates(*curves,**settings)
            detail=dict(family=name,variant=variant,scale=unit,curves=[curve_to_dict(x) for x in curves],controls=settings,enumeration=result)
            (out/f'geometry-{family}-{variant}.json').write_text(json.dumps(_json_value(detail),indent=2)+'\n')
            assert result['status']=='PASS',result['unresolved']
            assert len(result['candidates'])==len(expected)
            states={};tolerance=dec(unit)*D('1e-85')
            for actual,target in zip(result['candidates'],expected):
                for bounds,value in zip(actual['root']['parameter_box'],target['fractions']):
                    assert dec(bounds[0])-D('1e-85')<=value<=dec(bounds[1])+D('1e-85')
                center=target['point'];p,q=target['contacts'];state=actual['connection_direction'];states[state]=states.get(state,0)+1
                center_matches=all(dec(lo)-tolerance<=x<=dec(hi)+tolerance for (lo,hi),x in zip(actual['root']['center_box_zr_m'],center))
                assert center_matches
                if max(abs(x-y) for x,y in zip(p,q))<tolerance:
                    assert state=='ZERO_LENGTH';assert actual['root']['source_contacts_coincide'];continue
                assert actual['root']['source_contacts_coincide'] is False
                if target['fractions'][0]<D('1e-85') or target['fractions'][1]>1-D('1e-85'):
                    assert state!='FORWARD';continue
                phases=[phase_reference(F(x[0]-center[0]),F(x[1]-center[1])) for x in (p,q)]
                sweep=settings['turn_direction']*(phases[1]-phases[0])
                while sweep<=0:sweep+=2*pi
                while sweep>2*pi:sweep-=2*pi
                if sweep>dec(settings['max_sweep_rad']):assert state=='SWEEP_LIMIT';continue
                assert state=='FORWARD',actual.get('construction_reason')
                output=[curve_from_dict(x) for x in actual['trimmed_curves']]
                assert output[1].semiaxes_m==(abs(d),abs(d))
                for point,trimmed,ff,endpoint,trim_bound,fillet_bound in zip((p,q),(output[0],output[2]),(0,1),(1,0),actual['trim_contact_error_bounds_m'],actual['fillet_contact_error_bounds_m']):
                    for actual_point,bound in ((evaluate(trimmed,endpoint)[0],trim_bound),(evaluate(output[1],ff)[0],fillet_bound)):
                        error=sum((x-y)**2 for x,y in zip(actual_point,point)).sqrt()
                        assert error<=dec(bound)+tolerance
                        assert bound<=settings['position_tolerance_m']
                for left,right in zip(output,output[1:]):
                    u,v=evaluate(left,1)[1],evaluate(right,0)[1]
                    angle=abs(phase_reference(F(sum(x*y for x,y in zip(u,v))),F(u[0]*v[1]-u[1]*v[0])))
                    assert angle<=dec(settings['angle_tolerance_rad'])
            records.append(dict(family=name,variant=variant,scale=unit,source_pairs=len(expected),centers=len(groups),states=states))
            print(json.dumps(dict(geometry_cases=len(records),family=name)),flush=True)
    return records


def fem_checks(out):
    from superfish_ng.tangent_construction import construct_tangent_case
    from superfish_ng.config import Case
    from superfish_ng.solver import solve
    from superfish_ng.rf import quantities
    request = json.loads((ROOT/'examples/construction/circle_conic_fillet_request.json').read_text())
    results = []; reports = []
    for scale_factor in (1., 2.):
        r = deepcopy(request)
        for curve in r['case_template']['geometry']['curves']:
            for key in ('start_zr_m', 'end_zr_m', 'center_zr_m', 'semiaxes_m'):
                if key in curve: curve[key] = [x*scale_factor for x in curve[key]]
        for key in ('join_tolerance_m', 'minimum_gap_m', 'chord_tolerance_m'):
            r['case_template']['geometry'][key] *= scale_factor
        r['case_template']['mesh']['contour_mesh']['max_edge_m'] *= scale_factor
        for key in ('radius_m', 'position_tolerance_m'): r['controls'][key] *= scale_factor
        document = construct_tangent_case(r, candidate_index=0); case = Case.from_dict(document['case'])
        solution = solve(case); rf = quantities(case, solution)
        (out/f'constructed-{int(scale_factor)}.json').write_text(json.dumps(document, indent=2)+'\n')
        (out/f'rf-{int(scale_factor)}.json').write_text(json.dumps(rf, indent=2)+'\n')
        results.append(solution); reports.append(rf)
    first, second = results
    np.testing.assert_allclose(second.space.geometry.points_rz_m, 2*first.space.geometry.points_rz_m, rtol=1e-13, atol=1e-15)
    np.testing.assert_array_equal(second.space.geometry.cell_nodes, first.space.geometry.cell_nodes)
    assert first.u.shape == second.u.shape
    correlation = abs(np.dot(first.u[:, 0], second.u[:, 0]))/(np.linalg.norm(first.u[:, 0])*np.linalg.norm(second.u[:, 0]))
    assert 1-correlation < 1e-10
    ratios = {key: reports[1][key]/reports[0][key] for key in ('frequency_hz', 'r_over_q_accelerator_ohm', 'r_over_q_circuit_ohm', 'geometry_factor_ohm', 'transit_time_factor_abs')}
    assert abs(ratios['frequency_hz']-.5) < 1e-10
    assert all(abs(value-1) < 1e-9 for key, value in ratios.items() if key != 'frequency_hz')
    np.savez(out/'field-shape-scaling.npz', first=first.u, second=second.u,
             first_points=first.space.geometry.points_rz_m, second_points=second.space.geometry.points_rz_m,
             cell_nodes=first.space.geometry.cell_nodes)
    return dict(ratios=ratios, coefficient_shape_correlation=float(correlation), nodes=len(first.space.geometry.points_rz_m), scope='same constructed synthetic geometry at scales 1 and 2; invariant checks, not discretization-error bounds')


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--only', choices=('geometry', 'fem', 'all'), default='all')
    args = parser.parse_args(); args.out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    def hashes():
        return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'src').rglob('*'))
                if p.is_file() and p.suffix in ('.py', '.js', '.html', '.css')}
    before = hashes()
    geometry = []
    if args.only != 'fem':
        with localcontext() as context:
            context.prec = 140
            geometry = geometry_checks(args.out)
        (args.out/'geometry-report.json').write_text(json.dumps(dict(passed=True, geometry=geometry, source_sha256=before), indent=2)+'\n')
    fem = fem_checks(args.out) if args.only != 'geometry' else None
    assert hashes() == before
    report = dict(passed=True, seconds=time.monotonic()-start, selection=args.only, geometry_cases=len(geometry), source_pairs=sum(r['source_pairs'] for r in geometry),
                  decimal_precision=140, geometry=geometry, fem_scaling=fem, source_sha256=before, source_changed_during_run=False)
    (args.out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ('passed', 'seconds', 'geometry_cases', 'source_pairs')}))


if __name__ == '__main__': main()
