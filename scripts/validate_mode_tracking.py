# SPDX-License-Identifier: Apache-2.0
"""Independent cylinder crossing check using saved FEM fields and an explicit map."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
from superfish_ng import Case,solve
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution
from superfish_ng.analytic import tm0np_frequency
from superfish_ng.mode_tracking import track_cylindrical_modes


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out;out.mkdir(parents=True,exist_ok=False)
    files=[p for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    before=hashes();solutions=[];frequency_checks=[]
    labels=(((1,0),(2,0),(1,1)),((1,0),(1,1),(2,0)))
    for i,length in enumerate((.055,.075)):
        case=Case(((0.,.1),(length,.1)),nr=12,nz=12,modes=3,element_order=2)
        directory=out/f'cylinder-{i}';save_run(case,solve(case),directory)
        solution=read_solution(directory);solutions.append(solution)
        frequency_checks.append([dict(n=n,p=p,numerical_hz=float(f),analytical_hz=tm0np_frequency(.1,length,n,p),
            relative_error=abs(float(f)/tm0np_frequency(.1,length,n,p)-1)) for f,(n,p) in zip(solution.frequencies_hz,labels[i])])
    reports=[track_cylindrical_modes(*solutions,['TM010','TM020','TM011'],mapping='normalized_cylinder',sample_order=order,
        minimum_overlap=.98,minimum_assignment_margin=.05,relative_cluster_gap=1e-6) for order in (12,18)]
    passed=(all(r['status']=='PASS' and r['current_mode_ids']==['TM010','TM011','TM020'] for r in reports)
            and all(x['relative_error']<.002 for rows in frequency_checks for x in rows) and before==hashes())
    result=dict(passed=passed,frequency_checks=frequency_checks,tracking=reports,source_sha256=before,
                source_changed_during_run=before!=hashes(),scope='two synthetic PEC cylinders; native P2 FEM; explicit normalized-cylinder Hphi map; not general-shape or continuous-path tracking acceptance')
    (out/'mode_tracking.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(f'Mode tracking {"PASS" if passed else "FAIL"}: {out}');return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
