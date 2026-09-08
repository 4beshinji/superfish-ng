# SPDX-License-Identifier: Apache-2.0
"""Native adaptive workflow versus uniform refinement, analysis and scaling."""
import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys
import time
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng import Case,solve
from superfish_ng.analytic import pillbox_spectrum,pillbox_tm010
from superfish_ng.adaptive_refinement import execute_adaptive_refinement,replay_adaptive_refinement
from superfish_ng.io import save_run
from superfish_ng.mesh_input import mesh_to_dict
from superfish_ng.marked_refinement import refine_marked_cells
from superfish_ng.saved_mode_tracking import build_saved_mode_tracking
from superfish_ng.saved import read_solution
from superfish_ng.mesh import element_geometry
from superfish_ng.fem import triangle_quadrature
from superfish_ng.high_order import basis_p2


def nested_quadrature_difference(pair):
    request=pair['request'];a=read_solution(request['previous_run']);b=read_solution(request['current_run'])
    refined=refine_marked_cells(a.case,a.mesh,request['controls']['marked_cells'],max_triangles=len(b.mesh.triangles),minimum_angle_deg=1e-12)
    x=np.column_stack((refined.prolongation@a.u,b.u));x/=np.max(abs(x),axis=0)
    vertices,det,grad=element_geometry(b.mesh);dofs=b.space.cell_dofs if b.element_order==2 else b.mesh.triangles
    gram=np.zeros((x.shape[1],x.shape[1]))
    for n,w in triangle_quadrature(order=6):
        values=basis_p2(n,grad)[0] if b.element_order==2 else n
        fields=np.einsum('tjm,j->tm',x[dofs],values);radius=vertices[:,:,0]@n
        gram+=fields.T@((w*det*radius**3)[:,None]*fields)
    count=a.u.shape[1];scale=np.sqrt(np.diag(gram))
    expected=abs(gram[:count,count:]/scale[:count,None]/scale[None,count:])
    return float(np.max(abs(expected-np.asarray(pair['tracking']['overlap_matrix']))))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--confirmation',action='store_true',help='test version 2 with nested tracking and two uniform confirmation steps')
    args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    before=hashes();checks={}
    for kind in ('cylinder','folded'):
        for order in (1,2):
            series=[]
            for scale in (1.,2.):
                if kind=='cylinder':
                    case=Case(((0.,.1*scale),(.2*scale,.1*scale)),nr=6,nz=8,modes=2,element_order=order,normalization_j=scale**2)
                    exact=pillbox_spectrum(.1*scale,.2*scale,1)[0][0]
                else:
                    data=Case.load(ROOT/'examples/contour_folded.json').to_dict()
                    data['geometry']['vertices_zr_m']=(np.array(data['geometry']['vertices_zr_m'])*scale).tolist()
                    data['mesh']['contour_mesh']['max_edge_m']*=scale;data['solver']['element_order']=order;data['solver']['modes']=2
                    case=replace(Case.from_dict(data),normalization_j=scale**2)
                req=dict(schema_version=1,case=case.to_dict(),initial_mesh=None,initial_ids=['fundamental','second'],mode_id='fundamental',
                    controls=dict(mapping='same_domain',sample_order=3,minimum_overlap=.9,minimum_assignment_margin=.05,
                        relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8),bulk_fraction=.5,max_levels=7 if kind=='cylinder' and order==1 else 3,max_triangles=20000,
                    minimum_angle_deg=5.,relative_tolerances=dict(frequency_hz=1e-4,r_over_q_accelerator_ohm=.005,geometry_factor_ohm=.005))
                if args.confirmation:
                    req.update(schema_version=2,confirmation='uniform_two_steps',max_levels=8 if kind=='cylinder' and order==1 else 5,max_triangles=250000)
                    req['controls']['mapping']='nested_affine';del req['controls']['sample_order']
                name=f'{kind}-p{order}-s{int(scale)}';start=time.perf_counter()
                adaptive=execute_adaptive_refinement(req,out/name);seconds=time.perf_counter()-start
                replay_ok=replay_adaptive_refinement(adaptive)==adaptive
                (out/f'{name}.json').write_text(json.dumps(adaptive,indent=2,allow_nan=False)+'\n')
                quadrature=[];nested_differences=[]
                for row in adaptive['levels'][1:]:
                    if row['tracking'] is None:continue
                    if args.confirmation:
                        difference=nested_quadrature_difference(row['tracking']);nested_differences.append(difference)
                        quadrature.append(difference<1e-11 and row['tracking']['tracking']['individual_ids_complete']);continue
                    request=dict(row['tracking']['request']);request['controls']=dict(request['controls'],sample_order=4)
                    pair=build_saved_mode_tracking(request)
                    quadrature.append(pair['tracking']['individual_ids_complete'] and pair['tracking']['current_mode_ids']==row['current_mode_ids'] and pair['status']=='PASS')
                uniform=[];solution=solve(case)
                for level in range(3):
                    start=time.perf_counter()
                    if level:
                        refined=refine_marked_cells(case,solution.mesh,list(range(len(solution.mesh.triangles))))
                        solution=solve(case,mesh_data=mesh_to_dict(refined.mesh))
                    elapsed=time.perf_counter()-start;run=out/f'{name}-uniform-{level}';save_run(case,solution,run)
                    q=json.loads((run/'results.json').read_text())['modes'][0]
                    uniform.append(dict(triangles=len(solution.mesh.triangles),dofs=len(solution.u),refine_and_solve_seconds=elapsed,quantities=q))
                row=dict(adaptive=adaptive,uniform=uniform,adaptive_workflow_seconds=seconds,replay_identical=replay_ok,quadrature_cross_check_passed=quadrature)
                if args.confirmation:
                    row['nested_order6_overlap_absolute_differences']=nested_differences
                    row['quadrature_cross_check']='fine-mesh order-6 polynomial integration of all singleton cross-overlaps; not order-4 physical resampling'
                if kind=='cylinder':row['analytical_frequency_relative_errors']={branch:[level['quantities']['frequency_hz']/exact-1 for level in levels]
                    for branch,levels in (('adaptive',adaptive['levels']),('uniform',uniform))}
                if kind=='cylinder':
                    reference=pillbox_tm010(.1*scale,.2*scale)
                    row['analytical_rf_relative_errors']={branch:{key:[abs(level['quantities'][key]/reference[key]-1) for level in levels]
                        for key in ('r_over_q_accelerator_ohm','geometry_factor_ohm')} for branch,levels in (('adaptive',adaptive['levels']),('uniform',uniform))}
                series.append(row)
            similarity={key:max(abs(b['quantities'][key]*(2 if key=='frequency_hz' else 1)/a['quantities'][key]-1)
                for branch in ('adaptive','uniform') for a,b in zip(series[0][branch]['levels'] if branch=='adaptive' else series[0][branch],series[1][branch]['levels'] if branch=='adaptive' else series[1][branch]))
                for key in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')}
            isolated=all(all(v for v in s['quadrature_cross_check_passed']) and s['replay_identical'] and len(s['adaptive']['levels'])>=3 for s in series)
            same=all(a['marked_cells']==b['marked_cells'] for a,b in zip(series[0]['adaptive']['levels'],series[1]['adaptive']['levels']))
            statuses=[s['adaptive']['status'] for s in series]
            analytic=kind!='cylinder' or all(all(0<b<a for a,b in zip(errors,errors[1:])) for s in series for errors in s['analytical_frequency_relative_errors'].values())
            rf_improved=kind!='cylinder' or all(errors[-1]<errors[0] for s in series for branch in s['analytical_rf_relative_errors'].values() for errors in branch.values())
            monotonic=all(all(b['quantities']['frequency_hz']<=a['quantities']['frequency_hz']*(1+2e-12) for a,b in zip(s['adaptive']['levels'],s['adaptive']['levels'][1:])) for s in series)
            status_ok=all(v=='TARGETS_MET' for v in statuses) if kind=='cylinder' else all(v in ('TARGETS_MET','LEVEL_LIMIT') for v in statuses)
            passed=isolated and same and analytic and rf_improved and monotonic and status_ok and max(similarity.values())<2e-8
            checks[f'{kind}-p{order}']=dict(passed=bool(passed),statuses=statuses,series=series,similarity_relative_errors=similarity,
                same_scaled_selection=same,analytic_improvement=analytic,analytical_rf_improved=rf_improved,ritz_monotonic=monotonic)
    unchanged=before==hashes();passed=unchanged and all(c['passed'] for c in checks.values())
    report=dict(passed=passed,checks=checks,source_sha256=before,source_changed_during_run=not unchanged,
        scope='native affine adaptive API workflow and complete replay; isolated fundamental, cylinder analysis and uniform comparison, folded budget diagnostics, physical f/RQ/G similarity and tracking quadrature cross-check; not surface-peak or physical error-bound acceptance')
    report['uniform_confirmation']=args.confirmation
    (out/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(f'Adaptive refinement {"PASS" if passed else "FAIL"}: {out}');return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
