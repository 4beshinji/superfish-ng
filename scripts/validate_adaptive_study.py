# SPDX-License-Identifier: Apache-2.0
"""Independent Maxwell scaling and cylinder frequency checks for adaptive sweeps."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
from superfish_ng import Case
from superfish_ng.project import Project
from superfish_ng.studies import Study
from superfish_ng.saved import read_solution
from superfish_ng.analytic import tm0np_frequency
from superfish_ng.adaptive_study import execute_adaptive_study,read_adaptive_study


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    files=[p for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
    def hashes():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    before=hashes();reports=[]
    controls=dict(mapping='normalized_profile',sample_order=12,minimum_overlap=.99,minimum_assignment_margin=.05,
        relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)
    for scale,name in [(1.,'profile'),(2.,'scaled')]:
        case=Case(tuple((scale*z,scale*r) for z,r in ((0.,.07),(.025,.055),(.065,.1),(.1,.08))),nr=12,nz=20,modes=1,element_order=2)
        study=Study(Project.from_dict(case.to_dict()),'sweep','/case/geometry/points_zr_m/1/1',[scale*.055,scale*.08])
        request=dict(schema_version=1,study=study.to_dict(),initial_ids=['fundamental'],step_controls=[dict(controls)],
            adaptive=dict(max_depth=4,max_attempts=16,minimum_parameter_step=scale*1e-6))
        (out/f'{name}-request.json').write_text(json.dumps(request,indent=2)+'\n')
        report=execute_adaptive_study(request,out/name);assert read_adaptive_study(out/name/'adaptive-study-results.json')==report
        reports.append(report)
    similarity={key:0. for key in ('frequency_hz','r_over_q_accelerator_ohm','geometry_factor_ohm')}
    for a,b in zip(reports[0]['points'],reports[1]['points'],strict=True):
        first=read_solution(Path(a['run'])/'solution').results['modes'][0];second=read_solution(Path(b['run'])/'solution').results['modes'][0]
        for key in similarity:similarity[key]=max(similarity[key],abs(second[key]*(2 if key=='frequency_hz' else 1)/first[key]-1))
    decisions=[[a['decision'] for a in report['attempts']] for report in reports]
    overlaps=[[a['correspondence']['tracking']['overlap_matrix'][0][0] for a in report['attempts']] for report in reports]
    cylinder=Case(((0.,.1),(.055,.1)),nr=12,nz=20,modes=1,element_order=2)
    study=Study(Project.from_dict(cylinder.to_dict()),'sweep','/case/geometry/points_zr_m/1/0',[.055,.08])
    request=dict(schema_version=1,study=study.to_dict(),initial_ids=['TM010'],step_controls=[dict(controls)],
        adaptive=dict(max_depth=4,max_attempts=16,minimum_parameter_step=1e-6))
    cylinder_result=execute_adaptive_study(request,out/'cylinder')
    cylinder_errors=[abs(read_solution(Path(p['run'])/'solution').results['modes'][0]['frequency_hz']/tm0np_frequency(.1,p['value'],1,0)-1) for p in cylinder_result['points']]
    passed=(all(r['status']=='COMPLETE' and r['accepted_point_indices']==[0,2,1] and r['unreached_target_indices']==[] for r in reports)
        and decisions==[['BISECT','ACCEPT','ACCEPT']]*2 and max(similarity.values())<2e-10
        and max(abs(a-b) for a,b in zip(*overlaps))<2e-10
        and cylinder_result['status']=='COMPLETE' and len(cylinder_result['points'])==2 and max(cylinder_errors)<.002 and before==hashes())
    result=dict(passed=passed,similarity_relative_errors=similarity,overlaps=overlaps,decisions=decisions,cylinder_frequency_relative_errors=cylinder_errors,
        source_sha256=before,source_changed_during_run=before!=hashes(),scope='real P2 FEM fundamental modes; Maxwell scale invariance of frequency/RQ/G and subdivision decisions; cylindrical Bessel reference; not physical convergence acceptance')
    (out/'validation.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(f'Adaptive Study {"PASS" if passed else "FAIL"}: {out}');return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
