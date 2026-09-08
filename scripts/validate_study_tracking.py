# SPDX-License-Identifier: Apache-2.0
"""Track an actual completed Study across an analytical cylinder degeneracy."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import numpy as np
from scipy.special import jn_zeros
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
from superfish_ng import Case
from superfish_ng.project import Project
from superfish_ng.studies import Study,execute_study
from superfish_ng.analytic import tm0np_frequency
from superfish_ng.study_mode_tracking import save_study_mode_tracking,read_study_mode_tracking


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    files=[p for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    before=hashes();zeros=jn_zeros(0,2);crossing=float(np.pi*.1/np.sqrt(zeros[1]**2-zeros[0]**2))
    case=Case(((0.,.1),(.055,.1)),nr=12,nz=12,modes=3,element_order=2)
    study=Study(Project.from_dict(case.to_dict()),'sweep','/case/geometry/points_zr_m/1/0',[.055,crossing,.075])
    report=execute_study(study,out/'study');original=(out/'study'/'study-results.json').read_bytes()
    errors=[]
    for point in report['points']:
        expected=sorted(tm0np_frequency(.1,point['value'],n,p) for n,p in [(1,0),(2,0),(1,1)])
        errors.append(max(abs(m['frequency_hz']/f-1) for m,f in zip(point['modes'],expected)))
    controls=dict(mapping='normalized_cylinder',sample_order=12,minimum_overlap=.98,minimum_assignment_margin=.05,relative_cluster_gap=1e-3,
        minimum_relative_singular_value=1e-8,cluster_transition_policy='retain_subspace',minimum_cluster_link=.2)
    request=dict(schema_version=1,study_run='study',initial_ids=['TM010','TM020','TM011'],step_controls=[deepcopy(controls),deepcopy(controls)])
    (out/'request.json').write_text(json.dumps(request,indent=2)+'\n')
    tracked=save_study_mode_tracking(request,out/'study-tracking.json',base_directory=out)
    replayed=read_study_mode_tracking(out/'study-tracking.json')
    stopped_request=deepcopy(request)
    for key in ('cluster_transition_policy','minimum_cluster_link'):del stopped_request['step_controls'][0][key]
    stopped=save_study_mode_tracking(stopped_request,out/'stopped-study-tracking.json',base_directory=out)
    expected_groups=[dict(indices=[1],ids=['TM010']),dict(indices=[2,3],ids=['TM011','TM020'])]
    passed=(max(errors)<.002 and tracked==replayed and tracked['status']=='PASS' and tracked['visited_point_indices']==[0,1,2]
            and tracked['history']['current_identity_groups']==expected_groups and stopped['status']=='UNVERIFIED' and stopped['unvisited_point_indices']==[2]
            and read_study_mode_tracking(out/'stopped-study-tracking.json')==stopped and original==(out/'study'/'study-results.json').read_bytes() and before==hashes())
    result=dict(passed=passed,frequency_relative_errors=errors,visited_point_indices=tracked['visited_point_indices'],stopped_unvisited_point_indices=stopped['unvisited_point_indices'],
        source_sha256=before,source_changed_during_run=before!=hashes(),scope='native completed three-point P2 Study; independent cylinder frequencies and retained ID sets; tracking does not change Study convergence claims')
    (out/'validation.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(f'Study tracking {"PASS" if passed else "FAIL"}: {out}');return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
