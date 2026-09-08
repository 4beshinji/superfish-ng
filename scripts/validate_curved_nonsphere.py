# SPDX-License-Identifier: Apache-2.0
"""Prolate curved adaptive/uniform comparison, fixed geometry and Maxwell scaling."""
import argparse
from dataclasses import replace
import csv
import json
import math
import os
from pathlib import Path
import platform
import sys
import time
from unittest.mock import patch
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from superfish_ng import solve
from superfish_ng import curved_adaptive_refinement as engine
from superfish_ng.curved_refinement_steps import CurvedRefinementStep
from superfish_ng.curved_residual_indicator import curved_residual_indicator
from superfish_ng.fem import triangle_quadrature
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution
from superfish_ng.saved_mode_tracking import build_saved_mode_tracking
from superfish_ng.surface_convergence import _interval_change
from benchmark_curved_refinement import LIMITS, fingerprints, uniform_confirmed


def scaled_request(scale):
    r=json.loads((ROOT/'examples/adaptive_refinement/curved_prolate_confirmed.json').read_text())
    g=r['case']['geometry']
    for curve in g['curves']:
        for key in ('start_zr_m','end_zr_m','center_zr_m','semiaxes_m'):
            if key in curve:curve[key]=[scale*v for v in curve[key]]
    for key in ('chord_tolerance_m','join_tolerance_m','minimum_gap_m'):
        if key in g:g[key]*=scale
    r['case']['mesh']['contour_mesh']['max_edge_m']*=scale
    r['case']['rf']['normalization_j']=float(scale**2)
    return r


def volume(space):
    rule=list(triangle_quadrature(order=6));points=[n[1:] for n,w in rule];weights=np.array([w for n,w in rule])
    parts=[]
    for mapping in space.geometry.local_maps:
        q=mapping.evaluate(points)
        parts.append(float(np.dot(weights,q['points_rz_m'][:,0]*q['determinant_m2'])))
    return 2*math.pi*math.fsum(parts)


def intervals(level):
    result={k:[level['quantities'][k]]*2 for k in engine.RF}
    result.update(level['surface']['intervals'])
    return result


def row(level,seconds,domain_volume):
    return dict(triangles=level['triangles'],dofs=level['dofs'],intervals=intervals(level),solve_seconds=seconds,
                fixed_domain_volume_m3=domain_volume,quadrature_check=level['quadrature_check'])


def difference(a,b):
    return {key:_interval_change(a['intervals'][key],b['intervals'][key]) for key in LIMITS}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--reference-max-triangles',type=int,default=100000)
    args=parser.parse_args()
    if args.reference_max_triangles<1:parser.error('reference-max-triangles must be positive')
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();checks={}
    for scale in (1,2):
        print(f'prolate scale {scale}: adaptive',flush=True)
        request=scaled_request(scale);case=engine.validate_request(request);_,plan=engine.assemble(request,[])
        request['initial_mesh']=plan.source_mesh
        if 16*len(plan.space.geometry.cell_nodes)>args.reference_max_triangles:
            raise ValueError('reference budget cannot support even the initial two uniform confirmations')
        exact_volume=4*math.pi*(.16*scale)*(.08*scale)**2/3
        base_volume=volume(plan.space);native_error=abs(case.curved_contour.volume_m3/exact_volume-1)
        timings=[];original=engine.solve
        def measured(*a,**kw):
            start=time.perf_counter();solution=original(*a,**kw)
            timings.append((time.perf_counter()-start,volume(solution.space)))
            return solution
        start=time.perf_counter()
        with patch.object(engine,'solve',measured):result=engine.execute(request,out/f's{scale}-adaptive')
        adaptive_seconds=time.perf_counter()-start
        adaptive_rows=[row(level,*timing) for level,timing in zip(result['levels'],timings)]
        assert len(timings)==len(result['levels'])
        print(f'prolate scale {scale}: uniform and additional reference',flush=True)
        uniform_rows=[];levels=[];runs=[];stop_index=None;uniform_seconds=None;reference_status='REFERENCE_BUDGET'
        start=time.perf_counter()
        for index in range(request['max_levels']):
            if len(plan.space.geometry.cell_nodes)*4**index>args.reference_max_triangles:break
            print(f'prolate scale {scale}: uniform level {index}',flush=True)
            c=replace(case,curved_refinement_levels=0,curved_refinement_steps=(CurvedRefinementStep('uniform'),)*index)
            clock=time.perf_counter();solution=solve(c,mesh_data=plan.source_mesh);seconds=time.perf_counter()-clock
            domain_volume=volume(solution.space);run=out/f's{scale}-uniform-{index:03d}';save_run(c,solution,run)
            current=read_solution(run)
            if runs:
                tracking=build_saved_mode_tracking(dict(schema_version=1,previous_run=str(runs[-1]),current_run=str(run),
                    previous_ids=request['initial_ids'],controls=request['controls']))
                (out/f's{scale}-tracking-{index:03d}.json').write_text(json.dumps(tracking,indent=2)+'\n')
                if tracking['tracking']['status']!='PASS' or tracking['tracking']['current_mode_ids']!=request['initial_ids']:
                    reference_status='UNVERIFIED';break
            q=json.loads((run/'results.json').read_text())['modes'][0]
            indicator=curved_residual_indicator(current.case,current,mode=0,quadrature_order=case.quadrature_order)
            engine._quality(current.space,request)
            level=dict(triangles=len(current.space.geometry.cell_nodes),dofs=len(current.u),quantities=q,
                surface=engine._surface(current,0,q),quadrature_check=engine._quadrature(current,request,0,indicator))
            levels.append(level);uniform_rows.append(row(level,seconds,domain_volume));runs.append(run)
            if not level['quadrature_check']['passed']:reference_status='QUADRATURE_UNVERIFIED';break
            if stop_index is None and uniform_confirmed(levels,request):
                stop_index=index;uniform_seconds=time.perf_counter()-start
            if stop_index is not None and index>stop_index and level['dofs']>adaptive_rows[-1]['dofs'] and uniform_confirmed(levels,request):
                reference_status='REFERENCE_COMPUTED';break
        reference_seconds=time.perf_counter()-start
        diffs={}
        if reference_status=='REFERENCE_COMPUTED':
            diffs=dict(adaptive=difference(adaptive_rows[-1],uniform_rows[-1]),
                       uniform_at_confirmation=difference(uniform_rows[stop_index],uniform_rows[-1]))
        fixed_volume_difference=max(abs(r['fixed_domain_volume_m3']/base_volume-1) for r in adaptive_rows+uniform_rows)
        ritz=all(all(b['intervals']['frequency_hz'][0]<=a['intervals']['frequency_hz'][0]*(1+1e-10) for a,b in zip(rows,rows[1:])) for rows in (adaptive_rows,uniform_rows))
        initial_equal=adaptive_rows[0]['intervals']==uniform_rows[0]['intervals']
        passed=(result['status']=='TARGETS_MET' and reference_status=='REFERENCE_COMPUTED' and stop_index is not None
            and native_error<2e-12 and fixed_volume_difference<2e-12 and ritz and initial_equal
            and all(v is not None and v<=LIMITS[k] for changes in diffs.values() for k,v in changes.items()))
        checks[str(scale)]=dict(passed=passed,request=request,adaptive_status=result['status'],reference_status=reference_status,
            uniform_confirmation_index=stop_index,adaptive=adaptive_rows,uniform=uniform_rows,
            adaptive_workflow_seconds=adaptive_seconds,uniform_confirmation_workflow_seconds=uniform_seconds,
            uniform_with_reference_workflow_seconds=reference_seconds,reference_differences=diffs,
            analytic_native_volume_relative_error=native_error,fixed_domain_volume_relative_error=abs(base_volume/exact_volume-1),
            fixed_volume_invariance_relative_difference=fixed_volume_difference,ritz_monotonicity=ritz,initial_quantities_identical=initial_equal,
            fixed_domain_scope='analytic ellipsoid volume is independent; quadratic-domain volume approximation is recorded, not converted into an RF error bound')
        (out/f'scale-{scale}.json').write_text(json.dumps(checks[str(scale)],indent=2,allow_nan=False)+'\n')
    similarity={};same_lengths=True;geometry_similarity={}
    for method in ('adaptive','uniform'):
        a,b=checks['1'][method],checks['2'][method];same_lengths=same_lengths and len(a)==len(b)
        geometry_similarity[method]=dict(same_mesh_counts=all((aa['triangles'],aa['dofs'])==(bb['triangles'],bb['dofs']) for aa,bb in zip(a,b)),
            volume_relative_difference=max(abs(bb['fixed_domain_volume_m3']/(8*aa['fixed_domain_volume_m3'])-1) for aa,bb in zip(a,b)))
        similarity[method]={key:max(abs(y*(2 if key=='frequency_hz' else 1)/x-1) for aa,bb in zip(a,b) for x,y in zip(aa['intervals'][key],bb['intervals'][key])) for key in LIMITS}
    passed=(before==fingerprints() and same_lengths and all(c['passed'] for c in checks.values())
            and max(v for m in similarity.values() for v in m.values())<2e-8
            and all(g['same_mesh_counts'] and g['volume_relative_difference']<2e-12 for g in geometry_similarity.values()))
    report=dict(passed=passed,checks=checks,similarity_relative_differences=similarity,same_level_counts=same_lengths,geometry_similarity=geometry_similarity,
        reference_difference_limits=LIMITS,source_sha256=before,source_changed_during_run=before!=fingerprints(),
        environment=dict(python=platform.python_version(),platform=platform.platform(),openblas_num_threads=os.environ.get('OPENBLAS_NUM_THREADS')),
        scope='synthetic prolate ellipsoid: fixed quadratic domain, adaptive versus uniform confirmation and an additional higher-DOF uniform reference, independent exact volume and Maxwell scaling; reference differences are not independent absolute RF errors or physical bounds; no general efficiency acceptance')
    (out/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    with (out/'reference-differences.csv').open('w') as stream:
        writer=csv.writer(stream);writer.writerow(['scale','method','level','triangles','dofs','solve_seconds',*LIMITS])
        for scale,check in checks.items():
            reference=check['uniform'][-1]
            for method in ('adaptive','uniform'):
                for index,r in enumerate(check[method]):
                    changes=difference(r,reference)
                    writer.writerow([scale,method,index,r['triangles'],r['dofs'],r['solve_seconds'],*[changes[k] for k in LIMITS]])
    print(f'Curved nonsphere comparison {"PASS" if passed else "FAIL"}: {out}',flush=True)
    return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
