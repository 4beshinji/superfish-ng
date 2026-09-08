# SPDX-License-Identifier: Apache-2.0
"""Maxwell similarity and restart evidence from isolated adaptive Study workers."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
from superfish_ng import Case
from superfish_ng.project import Project
from superfish_ng.studies import Study
from superfish_ng.jobs import JobManager
from superfish_ng.saved import read_solution
from superfish_ng.adaptive_study import read_adaptive_study


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    files=[p for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    before=hashes();reports=[];job_ids=[];manager=JobManager(out/'jobs')
    def wait(identifier):
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            state=manager.status(identifier)
            if state['status'] not in ('queued','running'):
                if state['status']!='complete':raise RuntimeError(str(state))
                return manager.status(identifier,verify=True),read_adaptive_study(manager.directory(identifier)/'adaptive-study-results.json')
            time.sleep(.025)
        raise RuntimeError('adaptive worker timeout')
    controls=dict(mapping='normalized_profile',sample_order=12,minimum_overlap=.99,minimum_assignment_margin=.05,
        relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)
    try:
        for scale,name in [(1.,'profile'),(2.,'scaled')]:
            case=Case(tuple((scale*z,scale*r) for z,r in ((0.,.07),(.025,.055),(.065,.1),(.1,.08))),nr=12,nz=20,modes=1,element_order=2)
            study=Study(Project.from_dict(case.to_dict()),'sweep','/case/geometry/points_zr_m/1/1',[scale*.055,scale*.08])
            request=dict(schema_version=1,study=study.to_dict(),initial_ids=['fundamental'],step_controls=[dict(controls)],
                adaptive=dict(max_depth=4,max_attempts=16,minimum_parameter_step=scale*1e-6))
            (out/f'{name}-request.json').write_text(json.dumps(request,indent=2)+'\n')
            first_id=manager.start_adaptive_study(request,max_new_attempts=1);state,first=wait(first_id)
            assert state['tracking_status']=='PAUSED' and state['accepted_points']==1 and state['computed_points']==2
            path=manager.directory(first_id)/'adaptive-study-results.json';original=path.read_bytes()
            middle_id=manager.start_adaptive_study(request,max_new_attempts=1,checkpoint=first);state,middle=wait(middle_id)
            assert state['tracking_status']=='PAUSED' and state['accepted_points']==2 and state['computed_points']==3
            final_id=manager.start_adaptive_study(request,checkpoint=middle);state,final=wait(final_id)
            assert state['tracking_status']=='COMPLETE' and not list((manager.directory(final_id)/'execution').glob('point-*'))
            assert path.read_bytes()==original and final['accepted_point_indices']==[0,2,1]
            reports.append(final);job_ids.append(dict(first=first_id,middle=middle_id,final=final_id))
        similarity={key:0. for key in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')}
        for a,b in zip(reports[0]['points'],reports[1]['points'],strict=True):
            first=read_solution(Path(a['run'])/'solution').results['modes'][0];second=read_solution(Path(b['run'])/'solution').results['modes'][0]
            for key in similarity:similarity[key]=max(similarity[key],abs(second[key]*(2 if key=='frequency_hz' else 1)/first[key]-1))
        request['adaptive']['max_depth']=0
        stopped_id=manager.start_adaptive_study(request);state,stopped=wait(stopped_id)
        decisions=[[a['decision'] for a in r['attempts']] for r in reports]
        passed=(max(similarity.values())<2e-10 and decisions==[['BISECT','ACCEPT','ACCEPT']]*2
            and state['tracking_status']=='UNVERIFIED' and state['accepted_points']==1 and state['computed_points']==2
            and state['unreached_target_indices']==[1] and not (manager.directory(stopped_id)/'execution/point-003').exists() and before==hashes())
        result=dict(passed=passed,similarity_relative_errors=similarity,decisions=decisions,job_ids=job_ids,stopped_job=stopped_id,
            source_sha256=before,source_changed_during_run=before!=hashes(),scope='isolated P2 FEM workers; adaptive pause/resume with rejected-pair evidence and Maxwell f/RQ/G similarity; no physical convergence certificate')
    finally:manager.close()
    (out/'validation.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(f'Adaptive Study jobs {"PASS" if passed else "FAIL"}: {out}');return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
