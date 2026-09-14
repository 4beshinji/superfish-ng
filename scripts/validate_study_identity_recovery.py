# SPDX-License-Identifier: Apache-2.0
"""Validate scheduled Study identity recovery with analytical modes and scaling."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
from scipy.special import jn_zeros
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from superfish_ng import Case
from superfish_ng.project import Project
from superfish_ng.studies import Study,execute_study
from superfish_ng.analytic import tm0np_frequency
from superfish_ng.saved import read_solution
from superfish_ng.sampling import FieldSampler
from superfish_ng.study_mode_tracking import save_study_mode_tracking,read_study_mode_tracking
from validate_large_curved_mesh_selection import fingerprints


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--reuse-native',type=Path);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();started=time.monotonic()
    zeros=jn_zeros(0,2);crossing=float(np.pi*.1/np.sqrt(zeros[1]**2-zeros[0]**2))
    lengths=[.055,crossing,.075,.056,crossing,.08];native={};rows=[];retained={}
    for name,scale,energy in [('base',1.,1.),('double',2.,1.),('energy4',1.,4.)]:
        directory=out/name;directory.mkdir();study_dir=(args.reuse_native.resolve()/name/'study') if args.reuse_native else directory/'study'
        case=Case(((0.,.1*scale),(.055*scale,.1*scale)),nr=12,nz=12,modes=3,element_order=2,normalization_j=energy)
        study=Study(Project.from_dict(case.to_dict()),'sweep','/case/geometry/points_zr_m/1/0',[x*scale for x in lengths])
        if args.reuse_native is None:execute_study(study,study_dir)
        assert Study.from_dict(json.loads((study_dir/'study.json').read_text())).to_dict()==study.to_dict()
        hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in study_dir.rglob('*') if p.is_file()};retained.update(hashes)
        native[name]=[read_solution(study_dir/f'point-{i+1:03d}/solution') for i in range(6)]
        errors=[]
        for size,solution in zip(lengths,native[name]):
            exact=sorted(tm0np_frequency(.1*scale,size*scale,n,p) for n,p in [(1,0),(2,0),(1,1)])
            errors.extend(abs(f/g-1) for f,g in zip(solution.frequencies_hz,exact))
        assert max(errors)<.002
        for order in (12,18):
            controls=dict(mapping='normalized_cylinder',sample_order=order,minimum_overlap=.98,minimum_assignment_margin=.05,
                relative_cluster_gap=.001,minimum_relative_singular_value=1e-8)
            request=dict(schema_version=2,study_run=str(study_dir),initial_ids=['TM010','TM020','TM011'],
                step_controls=[dict(controls,cluster_transition_policy='retain_subspace',minimum_cluster_link=.2) for _ in range(5)],
                identity_recoveries=[dict(point_index=2,anchor_snapshot_index=0,controls=controls),dict(point_index=5,anchor_snapshot_index=2,controls=controls)])
            path=directory/f'recovered-{order}.json';result=save_study_mode_tracking(request,path)
            assert read_study_mode_tracking(path)==result and result['status']=='PASS'
            assert [e['after_step_index'] for e in result['history']['identity_recoveries']]==[1,4]
            assert result['point_results'][2]['current_mode_ids']==['TM010','TM011','TM020']
            assert result['point_results'][3]['current_mode_ids']==['TM010','TM020','TM011']
            assert result['point_results'][5]['current_mode_ids']==['TM010','TM011','TM020']
            failed=deepcopy(request);failed['identity_recoveries'][0]['point_index']=1
            stop=save_study_mode_tracking(failed,directory/f'unverified-{order}.json')
            assert stop['status']=='UNVERIFIED' and stop['unvisited_point_indices']==[2,3,4,5]
            assert read_study_mode_tracking(directory/f'unverified-{order}.json')==stop
            original=deepcopy(request);original['schema_version']=1;original.pop('identity_recoveries')
            old=save_study_mode_tracking(original,directory/f'original-{order}.json');assert old['history']['current_mode_ids']==['TM010',None,None]
            command=subprocess.run([sys.executable,'-m','superfish_ng','replay-study-mode-tracking',str(path)],capture_output=True,text=True,cwd=ROOT)
            (directory/f'cli-{order}.log').write_text(command.stdout+command.stderr);assert command.returncode==0
            rows.append(dict(variant=name,order=order,frequency_error=max(errors),current_mode_ids=result['history']['current_mode_ids'],
                recoveries=len(result['history']['identity_recoveries']),failed_unvisited=stop['unvisited_point_indices']))
    comparisons=[]
    for name,scale,energy in [('double',2.,1.),('energy4',1.,4.)]:
        for index in [0,2,3,5]:
            old,new=native['base'][index],native[name][index]
            probes=np.array([[r*.1,z*lengths[index]] for r in [.13,.37,.61,.89] for z in [.14,.38,.62,.87]])
            for mode in range(3):
                a,b=FieldSampler.from_solution(old).evaluate(probes,mode),FieldSampler.from_solution(new).evaluate(scale*probes,mode)
                sign=1 if np.dot(a['Hphi_A_per_m'],b['Hphi_A_per_m'])>=0 else -1
                # Normalize the electric vector together: an analytically zero
                # component cannot serve as a relative-error denominator.
                factor=sign*scale**1.5/energy**.5
                ae=np.concatenate([a[key] for key in ['Er_quadrature_V_per_m','Ez_quadrature_V_per_m']])
                be=np.concatenate([b[key] for key in ['Er_quadrature_V_per_m','Ez_quadrature_V_per_m']])
                field=dict(magnetic=float(np.linalg.norm(a['Hphi_A_per_m']-factor*b['Hphi_A_per_m'])/np.linalg.norm(a['Hphi_A_per_m'])),
                           electric=float(np.linalg.norm(ae-factor*be)/np.linalg.norm(ae)))
                q0,q1=old.results['modes'][mode],new.results['modes'][mode]
                rf={key:abs(q1[key]*(scale if key=='frequency_hz' else 1)/q0[key]-1)
                    for key in ['frequency_hz','r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm']}
                assert max(field.values())<2e-9 and max(rf.values())<2e-9
                comparisons.append(dict(variant=name,point_index=index,mode_index=mode+1,rf_errors=rf,field_errors=field))
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in retained.items()) and fingerprints()==before
    report=dict(status='PASS',new_fem_solves=0 if args.reuse_native else 18,verified_native_solves=18,rows=rows,comparisons=comparisons,
        native_sha256=retained,source_sha256=before,source_unchanged=True,seconds=time.monotonic()-started,
        scope='completed six-point P2 cylinder Study: two degeneracy episodes, declared anchor recovery, RF/field scaling outside degeneracy, native and original history preservation; no continuous-branch proof')
    (out/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(json.dumps({k:report[k] for k in ['status','new_fem_solves','seconds']}))


if __name__=='__main__':main()
