# SPDX-License-Identifier: Apache-2.0
"""Bessel dispersion, Maxwell scaling and restart for explicit tune recovery."""
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
from superfish_ng.tuning import execute_tune,read_tune,_assemble
from superfish_ng.jobs import JobManager
from superfish_ng.saved import read_solution
from superfish_ng.sampling import FieldSampler
from superfish_ng.analytic import tm0np_frequency
from validate_large_curved_mesh_selection import fingerprints


def request_for(scale=1.,energy=1.):
    base=json.loads((ROOT/'examples/tuning/pillbox_length.json').read_text())
    for p in base['project']['case']['geometry']['points_zr_m']:p[:]=[x*scale for x in p]
    base['project']['case']['rf']['normalization_j']=energy
    base['bounds']=[x*scale for x in base['bounds']]
    for key in ['target_hz','frequency_tolerance_hz','mesh_frequency_tolerance_hz']:base[key]/=scale
    base['parameter_tolerance']*=scale;controls=deepcopy(base['controls'])
    base['controls'].update(relative_cluster_gap=.2,cluster_transition_policy='retain_subspace',minimum_cluster_link=.2)
    return dict(schema_version=6,tune_request=base,identity_recovery=dict(anchor_selection='fixed_trial',anchor_trial_index=0,controls=controls))


def hashes(directory):return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(directory).rglob('*') if p.is_file()}
def unchanged(before):assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==v for p,v in before.items())
def save(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def verify_final(result,scale):
    assert result['status']=='TUNED' and len(result['trials'])==17
    assert abs(result['decision']['value']/(.083*scale)-1)<2e-5
    assert result['trials'][0]['current_mode_ids'].index('TM011')==2
    assert result['trials'][-1]['current_mode_ids'].index('TM011')==1
    assert result['trials'][-1]['identity_recovery']['status']=='PASS'
    solutions=[];errors=[]
    for trial,run in zip(result['trials'],result['trial_runs']):
        solution=read_solution(Path(run)/'solution');solutions.append(solution)
        expected=sorted(tm0np_frequency(.1*scale,trial['value'],n,p) for n,p in [(1,0),(2,0),(1,1)])
        errors.extend(abs(a/b-1) for a,b in zip(solution.frequencies_hz,expected))
        assert trial['frequency_hz']==solution.frequencies_hz[trial['current_mode_ids'].index('TM011')]
    assert max(errors)<2e-5
    assert abs(solutions[-1].frequencies_hz[1]/tm0np_frequency(.1*scale,result['decision']['value'],1,1)-1)<2e-6
    return solutions,max(errors)


def rebuild(request,runs,path):
    result=_assemble(request,runs);save(path,result);assert read_tune(path)==result
    return result


def worker_validation(out,reference):
    manager=JobManager(out/'jobs');request=request_for();ids={}
    def wait(identifier):
        while True:
            state=manager.status(identifier)
            if state['status'] not in ('queued','running'):
                assert state['status']=='complete',state;manager.status(identifier,verify=True)
                return read_tune(manager.directory(identifier)/'tune-results.json')
            time.sleep(.05)
    try:
        ids['first']=manager.start_tune(request,max_new_trials=2);first=wait(ids['first']);before=hashes(manager.directory(ids['first']))
        manager.close();manager=JobManager(out/'jobs');manager.status(ids['first'],verify=True)
        ids['final']=manager.start_tune(request,checkpoint=first);final=wait(ids['final']);_,error=verify_final(final,1.)
        unchanged(before);assert not (manager.directory(ids['final'])/'execution/trial-001').exists()
        failed=request_for();failed['identity_recovery']['controls']['relative_cluster_gap']=.2
        ids['failed']=manager.start_tune(failed);stopped=wait(ids['failed'])
        assert stopped['status']=='UNVERIFIED' and len(stopped['trials'])==2 and stopped['trials'][-1]['frequency_hz'] is None
        equality=[]
        if reference:
            direct=read_tune(reference/'base/final/checkpoint-017.json')
            for a,b in zip(direct['trial_runs'],final['trial_runs'],strict=True):
                with np.load(Path(a)/'solution/fields.npz') as left,np.load(Path(b)/'solution/fields.npz') as right:
                    assert left.files==right.files and all(np.array_equal(left[k],right[k]) for k in left.files)
                assert read_solution(Path(a)/'solution').results['modes']==read_solution(Path(b)/'solution').results['modes']
                equality.append(True)
        return dict(new_fem_solves=19,job_ids=ids,frequency_error=error,all_native_arrays_and_rf_equal=equality,all_jobs_terminal=True)
    finally:manager.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--workers-only',action='store_true');parser.add_argument('--reference',type=Path)
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();started=time.monotonic()
    if args.workers_only:report=worker_validation(out,args.reference.resolve() if args.reference else None)
    else:
        solutions={};rows=[];retained={}
        for name,scale,energy in [('base',1.,1.),('double',2.,1.),('energy4',1.,4.)]:
            directory=out/name;directory.mkdir();request=request_for(scale,energy);save(directory/'request.json',request)
            first=execute_tune(request,directory/'first',max_new_trials=2);prior=hashes(directory/'first')
            assert first['status']=='PAUSED' and first['trials'][1]['identity_recovery']['status']=='PASS'
            final=execute_tune(request,directory/'final',checkpoint=first);unchanged(prior)
            solutions[name],error=verify_final(final,scale)
            for order in [12,18]:
                changed=deepcopy(request);changed['tune_request']['controls']['sample_order']=order;changed['identity_recovery']['controls']['sample_order']=order
                verify_final(rebuild(changed,final['trial_runs'],directory/f'order-{order}.json'),scale)
            latest=deepcopy(request);latest['identity_recovery']=dict(anchor_selection='latest_resolved_trial',controls=latest['identity_recovery']['controls'])
            last=rebuild(latest,final['trial_runs'],directory/'latest.json');verify_final(last,scale)
            assert all(t['identity_recovery']['anchor_trial_index']==t['index']-1 for t in last['trials'] if t['identity_recovery'])
            for version in [2,3]:
                bound=deepcopy(request);base=bound['tune_request'];base.update(schema_version=version,parameter='length',parameter_unit='m',
                    bindings=[dict(path='/case/geometry/points_zr_m/1/0',**(dict(multiplier=1.,offset_m=0.) if version==2 else dict(coefficients=[0.,1.])))])
                verify_final(rebuild(bound,final['trial_runs'],directory/f'base-version-{version}.json'),scale)
            command=subprocess.run([sys.executable,'-m','superfish_ng','replay-tune',str(directory/'final/checkpoint-017.json')],capture_output=True,text=True,cwd=ROOT)
            (directory/'cli.log').write_text(command.stdout+command.stderr);assert command.returncode==0
            retained.update(hashes(directory));rows.append(dict(variant=name,frequency_error=error,decision=final['decision'],trial_count=len(final['trials']),
                recovery_count=sum(t['identity_recovery'] is not None for t in final['trials']),orders_12_18_same_decisions=True,latest_anchor_same_decisions=True,base_versions_2_3_same_decisions=True))
        failures=[]
        for name in ['unresolved','degenerate']:
            failed=request_for()
            if name=='unresolved':failed['identity_recovery']['controls']['relative_cluster_gap']=.2
            else:
                zeros=jn_zeros(0,2);failed['tune_request']['bounds']=[.055,float(np.pi*.1/np.sqrt(zeros[1]**2-zeros[0]**2))]
                failed['identity_recovery']['controls']['relative_cluster_gap']=.001
            stopped=execute_tune(failed,out/name)
            assert stopped['status']=='UNVERIFIED' and len(stopped['trials'])==2 and stopped['trials'][-1]['frequency_hz'] is None
            assert stopped['trials'][-1]['tracking']['status']=='PASS' and stopped['trials'][-1]['identity_recovery']['status']=='UNVERIFIED'
            assert not (out/name/'trial-003').exists();assert read_tune(out/name/'checkpoint-002.json')==stopped
            failures.append(dict(case=name,status=stopped['status'],frequency_evaluated=False))
        comparisons=[]
        for name,scale,energy in [('double',2.,1.),('energy4',1.,4.)]:
            base_doc=read_tune(out/'base/final/checkpoint-017.json')
            for index,trial in enumerate(base_doc['trials']):
                old,new=solutions['base'][index],solutions[name][index]
                probes=np.array([[.1*r,trial['value']*z] for r in [.13,.37,.61,.89] for z in [.14,.38,.62,.87]])
                for mode in range(3):
                    a,b=FieldSampler.from_solution(old).evaluate(probes,mode),FieldSampler.from_solution(new).evaluate(scale*probes,mode)
                    sign=1 if np.dot(a['Hphi_A_per_m'],b['Hphi_A_per_m'])>=0 else -1;factor=sign*scale**1.5/energy**.5
                    ae=np.concatenate([a[k] for k in ['Er_quadrature_V_per_m','Ez_quadrature_V_per_m']]);be=np.concatenate([b[k] for k in ['Er_quadrature_V_per_m','Ez_quadrature_V_per_m']])
                    field=dict(magnetic=float(np.linalg.norm(a['Hphi_A_per_m']-factor*b['Hphi_A_per_m'])/np.linalg.norm(a['Hphi_A_per_m'])),electric=float(np.linalg.norm(ae-factor*be)/np.linalg.norm(ae)))
                    qa,qb=old.results['modes'][mode],new.results['modes'][mode]
                    rf={k:abs(qb[k]*(scale if k=='frequency_hz' else 1)/qa[k]-1) for k in ['frequency_hz','r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm']}
                    assert max(field.values())<2e-9 and max(rf.values())<2e-9
                    comparisons.append(dict(variant=name,trial_index=index,mode_index=mode+1,rf_errors=rf,field_errors=field))
        unchanged(retained);report=dict(new_fem_solves=55,rows=rows,failures=failures,comparisons=comparisons,retained_source_sha256=retained)
    assert fingerprints()==before
    report.update(status='PASS',seconds=time.monotonic()-started,source_sha256=before,source_unchanged=True,
        scope='native P2 cylinder TM011 tuning across frequency rank exchange; explicit subspace recovery before root updates, analytical degeneracy refusal, Bessel dispersion and Maxwell field/RF scaling; no continuous-branch or RF-convergence certificate')
    save(out/'validation.json',report);print(json.dumps({k:report[k] for k in ['status','new_fem_solves','seconds']}))


if __name__=='__main__':main()
