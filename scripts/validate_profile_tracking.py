# SPDX-License-Identifier: Apache-2.0
"""Independent Maxwell similarity and volume-aware profile tracking checks."""
import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
from superfish_ng import Case,solve
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution
from superfish_ng.profile_mode_tracking import track_profile_modes
from superfish_ng.saved_mode_tracking import save_mode_tracking
from superfish_ng.mode_tracking_history import start_mode_history,extend_mode_history,save_mode_history,read_mode_history


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    files=[p for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    before=hashes()
    a=Case(((0.,.07),(.025,.055),(.065,.1),(.1,.08)),nr=12,nz=20,modes=3,element_order=2)
    b=replace(a,profile=tuple((2*z,2*r) for z,r in a.profile))
    c=replace(b,profile=tuple((z,r*1.01 if i==1 else r) for i,(z,r) in enumerate(b.profile)))
    solutions=[];results=[]
    for name,case in zip(('a','b','c'),(a,b,c)):
        save_run(case,solve(case),out/name);solutions.append(read_solution(out/name));results.append(json.loads((out/name/'results.json').read_text()))
    similarity={}
    for key,scale in [('frequency_hz',2.),('r_over_q_accelerator_ohm',1.),('geometry_factor_ohm',1.)]:
        similarity[key]=max(abs(y[key]*scale/x[key]-1) for x,y in zip(results[0]['modes'],results[1]['modes']))
    controls=dict(mapping='normalized_profile',minimum_overlap=.98,minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)
    reports=[track_profile_modes(solutions[i],solutions[i+1],['A','B','C'],sample_order=q,**controls) for i in (0,1) for q in (8,12)]
    pair=save_mode_tracking(dict(schema_version=1,previous_run='a',current_run='b',previous_ids=['A','B','C'],controls=dict(controls,sample_order=12)),out/'pair.json',base_directory=out)
    history=extend_mode_history(start_mode_history(pair),dict(current_run='c',controls=dict(controls,sample_order=12)),base_directory=out)
    save_mode_history(history,out/'history.json');replayed=read_mode_history(out/'history.json')
    passed=(max(similarity.values())<2e-10 and all(r['status']=='PASS' and r['current_mode_ids']==['A','B','C'] for r in reports)
            and replayed['status']=='PASS' and before==hashes())
    result=dict(passed=passed,similarity_relative_errors=similarity,tracking=reports,source_sha256=before,source_changed_during_run=before!=hashes(),
        scope='synthetic positive radius profiles; native P2 FEM; Maxwell similarity and a 1 percent local radius perturbation; not arbitrary-contour or continuous-branch tracking acceptance')
    (out/'profile_tracking.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(f'Profile tracking {"PASS" if passed else "FAIL"}: {out}');return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
