# SPDX-License-Identifier: Apache-2.0
"""Analytically located cylinder degeneracy, solved with native P2 FEM."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import numpy as np
from scipy.special import jn_zeros
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
from superfish_ng import Case,solve
from superfish_ng.io import save_run
from superfish_ng.analytic import tm0np_frequency
from superfish_ng.saved_mode_tracking import save_mode_tracking
from superfish_ng.mode_tracking_history import start_mode_history,extend_mode_history,save_mode_history,read_mode_history


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    files=[p for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    before=hashes();zeros=jn_zeros(0,2);length=np.pi*.1/np.sqrt(zeros[1]**2-zeros[0]**2)
    frequency_errors={};degenerate_gap=None
    for name,size in [('a',.055),('b',length),('c',.075)]:
        case=Case(((0.,.1),(size,.1)),nr=12,nz=12,modes=3,element_order=2);solution=solve(case);save_run(case,solution,out/name)
        expected=sorted(tm0np_frequency(.1,size,n,p) for n,p in [(1,0),(2,0),(1,1)])
        frequency_errors[name]=max(abs(f/g-1) for f,g in zip(solution.frequencies_hz,expected))
        if name=='b':degenerate_gap=abs(solution.frequencies_hz[2]/solution.frequencies_hz[1]-1)
    histories=[]
    for q in (12,18):
        controls=dict(mapping='normalized_cylinder',sample_order=q,minimum_overlap=.98,minimum_assignment_margin=.05,relative_cluster_gap=1e-3,
            minimum_relative_singular_value=1e-8,cluster_transition_policy='retain_subspace',minimum_cluster_link=.2)
        seed_request=dict(schema_version=1,previous_run='a',current_run='a',previous_ids=['TM010','TM020','TM011'],controls=controls)
        pair=save_mode_tracking(seed_request,out/f'seed-{q}.json',base_directory=out)
        history=start_mode_history(pair)
        for stage in ('b','c'):
            request=dict(current_run=stage,controls=controls)
            (out/f'extension-{stage}-{q}.json').write_text(json.dumps(request,indent=2)+'\n')
            history=extend_mode_history(history,request,base_directory=out)
            save_mode_history(history,out/f'history-{stage}-{q}.json');history=read_mode_history(out/f'history-{stage}-{q}.json')
        histories.append(history)
    expected_groups=[dict(indices=[1],ids=['TM010']),dict(indices=[2,3],ids=['TM011','TM020'])]
    passed=(max(frequency_errors.values())<.002 and degenerate_gap<1e-3 and before==hashes()
            and all(h['status']=='PASS' and h['current_mode_ids']==['TM010',None,None] and h['current_identity_groups']==expected_groups
                    and [s['tracking']['cluster_transitions']['events'][0]['kind'] for s in h['steps'][1:]]==['MERGE','SPLIT']
                    and all(s['tracking']['cluster_transitions']['events'][0]['status']=='PASS' for s in h['steps'][1:]) for h in histories))
    result=dict(passed=passed,analytical_degeneracy_length_m=float(length),frequency_relative_errors=frequency_errors,numerical_degenerate_relative_gap=float(degenerate_gap),
        histories=histories,source_sha256=before,source_changed_during_run=before!=hashes(),scope='native P2 cylinder passing an analytically located TM020/TM011 degeneracy; retain the ID union after splitting; no recovery of individual branch labels')
    (out/'cluster_transitions.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(f'Cluster transitions {"PASS" if passed else "FAIL"}: {out}');return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
