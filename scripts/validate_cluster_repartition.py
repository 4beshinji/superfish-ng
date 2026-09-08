# SPDX-License-Identifier: Apache-2.0
"""Native cylinder spectrum and explicitly seeded uncertain ID-set replay."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
from scipy.special import jn_zeros
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng import Case,solve
from superfish_ng.io import save_run
from superfish_ng.analytic import tm0np_frequency
from superfish_ng.saved_mode_tracking import save_mode_tracking,read_mode_tracking
from superfish_ng.mode_tracking_history import start_mode_history,extend_mode_history,save_mode_history,read_mode_history


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    def hashes():
        return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}
    before=hashes();zeros=jn_zeros(0,2);length=2*np.pi*.1/np.sqrt(zeros[1]**2-zeros[0]**2)
    case=Case(((0.,.1),(length,.1)),nr=12,nz=16,modes=5,element_order=2)
    solution=solve(case);save_run(case,solution,out/'native')
    expected=sorted(tm0np_frequency(.1,length,n,p) for n,p in [(1,0),(1,1),(2,0),(1,2),(2,1)])
    errors=[abs(f/g-1) for f,g in zip(solution.frequencies_hz,expected,strict=True)]
    groups=[dict(indices=[1],ids=['fundamental']),dict(indices=[2,3],ids=['A','B']),dict(indices=[4,5],ids=['C','D'])]
    checks=[]
    for order in (12,18):
        controls=dict(mapping='normalized_cylinder',sample_order=order,minimum_overlap=.98,minimum_assignment_margin=.05,
            relative_cluster_gap=.001,minimum_relative_singular_value=1e-8,cluster_transition_policy='retain_subspace',minimum_cluster_link=.2)
        request=dict(schema_version=2,previous_run='native',current_run='native',previous_groups=groups,controls=controls)
        old=save_mode_tracking(request,out/f'old-{order}.json',base_directory=out)
        controls['cluster_transition_policy']='retain_connected_subspace'
        pair=save_mode_tracking(request,out/f'pair-{order}.json',base_directory=out)
        history=extend_mode_history(start_mode_history(pair),dict(current_run='native',controls=controls),base_directory=out)
        save_mode_history(history,out/f'history-{order}.json')
        checks.append(old['status']=='UNVERIFIED' and pair['status']=='PASS'
            and pair['tracking']['cluster_transitions']['events'][0]['kind']=='REPARTITION'
            and read_mode_tracking(out/f'pair-{order}.json')==pair
            and read_mode_history(out/f'history-{order}.json')==history
            and history['current_mode_ids']==['fundamental',None,None,None,None]
            and history['current_identity_groups']==[groups[0],dict(indices=[2,3,4,5],ids=['A','B','C','D'])])
    passed=all(checks) and max(errors)<.002 and before==hashes()
    report=dict(passed=passed,frequency_relative_errors=errors,checks=checks,source_sha256=before,source_changed_during_run=before!=hashes(),
        scope='native P2 TM020/TM012 cylinder degeneracy; self-comparison with deliberately seeded uncertain prior ID sets; not a physical trajectory or individual branch recovery')
    (out/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(f'Cluster repartition {"PASS" if passed else "FAIL"}: {out}');return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
