# SPDX-License-Identifier: Apache-2.0
"""Recover individual cylinder branches after a native FEM degeneracy and split."""
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
from superfish_ng import Case,solve
from superfish_ng.analytic import tm0np_frequency
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution
from superfish_ng.sampling import FieldSampler
from superfish_ng.saved_mode_tracking import build_saved_mode_tracking
from superfish_ng.mode_tracking_history import start_mode_history,extend_mode_history,save_mode_history,read_mode_history
from superfish_ng.mode_identity_recovery import recover_mode_history
from validate_large_curved_mesh_selection import fingerprints


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--reuse-native',type=Path,help='verify existing base/double/energy4 native runs without another FEM solve')
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    before=fingerprints();started=time.monotonic();zeros=jn_zeros(0,2)
    length=np.pi*.1/np.sqrt(zeros[1]**2-zeros[0]**2)
    rows=[];native={};maximum_rf=0.;maximum_field=0.
    for name,scale,energy in [('base',1.,1.),('double',2.,1.),('energy4',1.,4.)]:
        directory=out/name;directory.mkdir();group={};frequency_errors=[]
        native_directory=args.reuse_native.resolve()/name if args.reuse_native else directory
        for stage,size in [('a',.055),('b',length),('c',.075)]:
            case=Case(((0.,.1*scale),(size*scale,.1*scale)),nr=12,nz=12,modes=3,element_order=2,normalization_j=energy)
            if args.reuse_native is None:save_run(case,solve(case),native_directory/stage)
            solution=read_solution(native_directory/stage);group[stage]=solution
            assert solution.case==case
            expected=sorted(tm0np_frequency(.1*scale,size*scale,n,p) for n,p in [(1,0),(2,0),(1,1)])
            frequency_errors.extend(abs(f/g-1) for f,g in zip(solution.frequencies_hz,expected))
        native[name]=group;native_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for stage in 'abc' for p in (native_directory/stage).iterdir() if p.is_file()}
        for order in (12,18):
            controls=dict(mapping='normalized_cylinder',sample_order=order,minimum_overlap=.98,
                minimum_assignment_margin=.05,relative_cluster_gap=.001,minimum_relative_singular_value=1e-8)
            retained=dict(controls,cluster_transition_policy='retain_subspace',minimum_cluster_link=.2)
            merged=start_mode_history(build_saved_mode_tracking(dict(schema_version=1,previous_run=str(native_directory/'a'),current_run=str(native_directory/'b'),
                previous_ids=['TM010','TM020','TM011'],controls=retained)))
            assert merged['status']=='PASS' and merged['current_mode_ids']==['TM010',None,None]
            split=extend_mode_history(merged,dict(current_run=str(native_directory/'c'),controls=retained));original=deepcopy(split)
            assert split['current_mode_ids']==['TM010',None,None]
            recovered=recover_mode_history(split,dict(anchor_snapshot_index=0,controls=controls))
            assert recovered['status']=='PASS' and recovered['current_mode_ids']==['TM010','TM011','TM020']
            assert recovered['steps']==split['steps'] and split==original
            path=directory/f'recovered-{order}.json';save_mode_history(recovered,path);assert read_mode_history(path)==recovered
            extended=extend_mode_history(recovered,dict(current_run=str(native_directory/'a'),controls=controls))
            assert extended['current_mode_ids']==['TM010','TM020','TM011'];save_mode_history(extended,directory/f'extended-{order}.json')
            failed=recover_mode_history(merged,dict(anchor_snapshot_index=0,controls=controls))
            assert failed['status']=='UNVERIFIED' and not failed['can_extend'] and failed['current_mode_ids']==['TM010',None,None]
            save_mode_history(failed,directory/f'unverified-{order}.json')
            command=subprocess.run([sys.executable,'-m','superfish_ng','replay-mode-history',str(path)],capture_output=True,text=True,cwd=ROOT)
            (directory/f'cli-{order}.log').write_text(command.stdout+command.stderr);assert command.returncode==0
            rows.append(dict(variant=name,order=order,current_mode_ids=recovered['current_mode_ids'],group_checks=recovered['identity_recoveries'][0]['assessment']['group_checks'],
                recovered=str(path),native_frequency_error=max(frequency_errors),minimum_overlap=min(m['minimum_principal_overlap'] for m in recovered['identity_recoveries'][0]['comparison']['tracking']['matches'])))
        assert max(frequency_errors)<.002
        assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in native_hashes.items())
    comparisons=[]
    for name,scale,energy in [('double',2.,1.),('energy4',1.,4.)]:
        for stage,size in [('a',.055),('c',.075)]:
            old,new=native['base'][stage],native[name][stage]
            probes=np.array([[r*.1,z*size] for r in [.13,.37,.61,.89] for z in [.14,.38,.62,.87]])
            for mode in range(3):
                q0,q1=old.results['modes'][mode],new.results['modes'][mode]
                rf={key:abs(q1[key]*(scale if key=='frequency_hz' else 1)/q0[key]-1)
                    for key in ['frequency_hz','r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm']}
                a,b=FieldSampler.from_solution(old).evaluate(probes,mode),FieldSampler.from_solution(new).evaluate(scale*probes,mode)
                factor=scale**1.5/energy**.5;sign=1 if np.dot(a['Hphi_A_per_m'],b['Hphi_A_per_m'])>=0 else -1
                magnetic=np.linalg.norm(a['Hphi_A_per_m']-sign*factor*b['Hphi_A_per_m'])/np.linalg.norm(a['Hphi_A_per_m'])
                ae=np.concatenate([a[k] for k in ['Er_quadrature_V_per_m','Ez_quadrature_V_per_m']]);be=np.concatenate([b[k] for k in ['Er_quadrature_V_per_m','Ez_quadrature_V_per_m']])
                electric=np.linalg.norm(ae-sign*factor*be)/np.linalg.norm(ae)
                maximum_rf=max(maximum_rf,*rf.values());maximum_field=max(maximum_field,float(magnetic),float(electric))
                comparisons.append(dict(variant=name,stage=stage,mode_index=mode+1,rf_errors=rf,magnetic_error=float(magnetic),electric_error=float(electric),diagnostic_sign=sign))
    assert maximum_rf<2e-9 and maximum_field<2e-9
    assert fingerprints()==before
    report=dict(status='PASS',new_fem_solves=0 if args.reuse_native else 9,verified_native_solves=9,
        reused_native_root=str(args.reuse_native.resolve()) if args.reuse_native else None,
        rows=rows,comparisons=comparisons,maximum_rf_scaling_error=maximum_rf,
        maximum_field_scaling_error=maximum_field,seconds=time.monotonic()-started,source_sha256=before,source_unchanged=True,
        scope='analytic cylinder crossing and degeneracy, explicit earlier-anchor recovery, saved/CLI replay, unresolved degeneracy refusal; length/energy invariance and separated-mode field/RF scaling; no individual basis comparison at degeneracy or continuous-branch certificate')
    (out/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:report[k] for k in ['status','new_fem_solves','seconds','maximum_rf_scaling_error','maximum_field_scaling_error']}))


if __name__=='__main__':main()
