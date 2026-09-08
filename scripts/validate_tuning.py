# SPDX-License-Identifier: Apache-2.0
"""Independent cylinder length/frequency and Maxwell scaling checks for tuning."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng import Case
from superfish_ng.project import Project
from superfish_ng.constants import C0
from superfish_ng.tuning import execute_tune,read_tune


def hashes():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*'))
        if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=hashes();rows=[]
    for scale in (1.,2.):
        radius=.1*scale;length=.083*scale
        # First zero of J0 is an external mathematical constant, used only in validation.
        target=C0/(2*math.pi)*math.hypot(2.404825557695773/radius,math.pi/length)
        request=dict(schema_version=1,project=Project(Case(((0.,radius),(.06*scale,radius)),nr=12,nz=16,modes=3,element_order=2)).to_dict(),
            parameter='/case/geometry/points_zr_m/1/0',bounds=[.06*scale,.1*scale],target_hz=target,
            frequency_tolerance_hz=1e4/scale,parameter_tolerance=1e-9*scale,max_trials=24,
            initial_ids=['TM010','TM020','TM011'],mode_id='TM011',
            controls=dict(mapping='normalized_cylinder',sample_order=16,minimum_overlap=.98,minimum_assignment_margin=.05,
                relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8),refinement_scale=2,mesh_frequency_tolerance_hz=1e4/scale)
        name=f'scale-{int(scale)}';(out/f'{name}-request.json').write_text(json.dumps(request,indent=2)+'\n')
        first=execute_tune(request,out/f'{name}-initial',max_new_trials=2)
        result=execute_tune(request,out/f'{name}-resumed',checkpoint=read_tune(out/f'{name}-initial/checkpoint-002.json'))
        last=result['trials'][-1];rank=last['current_mode_ids'].index('TM011')
        q=json.loads((Path(result['trial_runs'][-1])/'solution/results.json').read_text())['modes'][rank]
        exact_at_final=C0/(2*math.pi)*math.hypot(2.404825557695773/radius,math.pi/last['value'])
        row=dict(scale=scale,status=result['status'],trial_count=len(result['trials']),value_m=last['value'],quantities=q,
            parameter_relative_error=abs(last['value']/length-1),frequency_analytical_relative_error=abs(last['frequency_hz']/exact_at_final-1),
            target_error_hz=last['target_error_hz'],decision=result['decision'],initial_rank=first['trials'][0]['current_mode_ids'].index('TM011')+1,
            final_rank=rank+1,old_sources_preserved=result['trial_sources_sha256'][:2]==first['trial_sources_sha256'])
        rows.append(row)
    similarity={key:abs(rows[1]['quantities'][key]*(2 if key=='frequency_hz' else 1)/rows[0]['quantities'][key]-1)
        for key in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')}
    passed=(all(r['status']=='TUNED' and r['trial_count']>5 and r['parameter_relative_error']<2e-5 and r['frequency_analytical_relative_error']<2e-6
        and r['initial_rank']==3 and r['final_rank']==2 and r['old_sources_preserved'] for r in rows)
        and max(similarity.values())<2e-9 and before==hashes())
    report=dict(passed=passed,rows=rows,similarity_relative_errors=similarity,source_sha256=before,source_changed_during_run=before!=hashes(),
        scope='native P2 cylinder TM011 length tuning, analytic Bessel dispersion and uniform-scale f/RQ/G invariants; sampled rank crossing and immutable resume; not arbitrary-shape or RF-convergence acceptance')
    (out/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(f'Tuning {"PASS" if passed else "FAIL"}: {out}');return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
