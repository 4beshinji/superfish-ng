# SPDX-License-Identifier: Apache-2.0
"""Independent cylinder degeneracy and execution-stop checks for tracked Studies."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import numpy as np
from scipy.special import jn_zeros
from superfish_ng import Case
from superfish_ng.project import Project
from superfish_ng.studies import Study
from superfish_ng.saved import read_solution
from superfish_ng.analytic import tm0np_frequency
from superfish_ng.tracked_study import execute_tracked_study,read_tracked_study


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    files=[p for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    before=hashes();radius=.1;zeros=jn_zeros(0,2);cross=np.pi*radius/np.sqrt(zeros[1]**2-zeros[0]**2)
    study=Study(Project.from_dict(Case(((0.,radius),(.055,radius)),nr=12,nz=12,modes=3,element_order=2).to_dict()),
        'sweep','/case/geometry/points_zr_m/1/0',[.055,float(cross),.075])
    controls=dict(mapping='normalized_cylinder',sample_order=12,minimum_overlap=.98,minimum_assignment_margin=.05,
        relative_cluster_gap=.001,minimum_relative_singular_value=1e-8,cluster_transition_policy='retain_subspace',minimum_cluster_link=.2)
    request=dict(schema_version=1,study=study.to_dict(),initial_ids=['TM010','TM020','TM011'],step_controls=[dict(controls),dict(controls)])
    (out/'request.json').write_text(json.dumps(request,indent=2)+'\n')
    first=execute_tracked_study(request,out/'first',max_new_points=1)
    checkpoint=out/'first/checkpoint-001.json';original=checkpoint.read_bytes()
    complete=execute_tracked_study(request,out/'continued',checkpoint=read_tracked_study(checkpoint))
    errors=[]
    for run,length in zip(complete['point_runs'],study.values):
        frequencies=np.array([m['frequency_hz'] for m in read_solution(Path(run)/'solution').results['modes']])
        expected=np.sort([tm0np_frequency(radius,length,n,p) for n,p in ((1,0),(2,0),(1,1))])
        errors.append(float(np.max(abs(frequencies-expected)/expected)))
    stopped_request=deepcopy(request)
    for control in stopped_request['step_controls']:
        del control['cluster_transition_policy'];del control['minimum_cluster_link']
    stopped=execute_tracked_study(stopped_request,out/'stopped')
    passed=(first['status']=='PAUSED' and complete['status']=='COMPLETE' and max(errors)<.002
        and complete['history']['current_identity_groups']==[dict(indices=[1],ids=['TM010']),dict(indices=[2,3],ids=['TM011','TM020'])]
        and read_tracked_study(out/'continued/checkpoint-003.json')==complete and checkpoint.read_bytes()==original
        and stopped['status']=='UNVERIFIED' and len(stopped['point_runs'])==2 and not (out/'stopped/point-003').exists()
        and read_tracked_study(out/'stopped/checkpoint-002.json')==stopped and before==hashes())
    result=dict(passed=passed,frequency_relative_errors=errors,completed_status=complete['status'],stopped_status=stopped['status'],
        stopped_computed_points=len(stopped['point_runs']),source_sha256=before,source_changed_during_run=before!=hashes(),
        scope='three-point real P2 FEM cylinder degeneracy; immutable resume and stop-before-next-solve; no physical convergence claim')
    (out/'validation.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(f'Tracked Study {"PASS" if passed else "FAIL"}: {out}');return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
