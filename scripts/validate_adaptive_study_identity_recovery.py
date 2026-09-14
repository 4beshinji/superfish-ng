# SPDX-License-Identifier: Apache-2.0
"""Original-target recovery after real bisection: analytical fields and restart."""
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
from superfish_ng.studies import Study
from superfish_ng.jobs import JobManager
from superfish_ng.saved import read_solution
from superfish_ng.sampling import FieldSampler
from superfish_ng.analytic import tm0np_frequency
from superfish_ng.adaptive_study import execute_adaptive_study,read_adaptive_study,_run,_save_document
from validate_large_curved_mesh_selection import fingerprints


def request_for(scale=1.,energy=1.):
    zeros=jn_zeros(0,2);crossing=float(np.pi*.1/np.sqrt(zeros[1]**2-zeros[0]**2))
    case=Case(((0.,.1*scale),(.04*scale,.1*scale)),nr=8,nz=8,modes=3,element_order=2,normalization_j=energy)
    study=Study(Project.from_dict(case.to_dict()),'sweep','/case/geometry/points_zr_m/1/0',[x*scale for x in [.04,.055,crossing,.075,.08,.085]])
    controls=dict(mapping='normalized_cylinder',sample_order=12,minimum_overlap=.98,minimum_assignment_margin=.05,
        relative_cluster_gap=.001,minimum_relative_singular_value=1e-8)
    steps=[dict(controls,cluster_transition_policy='retain_subspace',minimum_cluster_link=.2) for _ in range(5)]
    steps[0]['minimum_overlap']=.9999999988;steps[3]['relative_cluster_gap']=.2
    return dict(schema_version=2,study=study.to_dict(),initial_ids=['TM010','TM020','TM011'],step_controls=steps,
        adaptive=dict(max_depth=4,max_attempts=16,minimum_parameter_step=1e-6*scale),
        identity_recoveries=[dict(target_index=3,anchor_target_index=1,controls=controls),dict(target_index=5,anchor_target_index=3,controls=controls)])


def hashes(directory):
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(directory).rglob('*') if p.is_file()}


def unchanged(before):
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==value for p,value in before.items())


def verify_final(final,scale):
    assert final['status']=='COMPLETE' and len(final['points'])==7
    assert [a['decision'] for a in final['attempts']]==['BISECT']+['ACCEPT']*6
    assert final['accepted_point_indices']==[0,2,1,3,4,5,6]
    recoveries=[a['identity_recovery'] for a in final['attempts'] if a['identity_recovery']]
    assert [(e['target_index'],e['anchor_target_index'],e['anchor_snapshot_index']) for e in recoveries]==[(3,1,2),(5,3,4)]
    assert final['history']['current_mode_ids']==['TM010','TM011','TM020']
    errors=[];solutions=[]
    for point in final['points']:
        solution=read_solution(Path(point['run'])/'solution');solutions.append(solution)
        expected=sorted(tm0np_frequency(.1*scale,point['value'],n,p) for n,p in [(1,0),(2,0),(1,1)])
        errors.extend(abs(f/g-1) for f,g in zip(solution.frequencies_hz,expected))
    assert max(errors)<.002
    return solutions,max(errors)


def saved_rebuild(request,points,path):
    runs={point['value']:point['run'] for point in points}
    def obtain(index,value,project):
        if value not in runs:raise ValueError('rebuild requests a new physical point; existing samples do not prove the same decisions')
        return runs[value]
    result=_run(request,obtain,schema_version=3);_save_document(result,path)
    assert read_adaptive_study(path)==result
    return result


def worker_validation(out,reference):
    manager=JobManager(out/'jobs');request=request_for();ids={}
    def wait(identifier):
        while True:
            state=manager.status(identifier)
            if state['status'] not in ('queued','running'):
                assert state['status']=='complete',state;manager.status(identifier,verify=True)
                return read_adaptive_study(manager.directory(identifier)/'adaptive-study-results.json')
            time.sleep(.05)
    try:
        ids['first']=manager.start_adaptive_study(request,max_new_attempts=1);first=wait(ids['first']);before=hashes(manager.directory(ids['first']))
        ids['recovered']=manager.start_adaptive_study(request,max_new_attempts=4,checkpoint=first);recovered=wait(ids['recovered'])
        assert recovered['status']=='PAUSED' and recovered['attempts'][-1]['identity_recovery']['anchor_snapshot_index']==2
        unchanged(before);prior=hashes(manager.directory(ids['recovered']))
        manager.close();manager=JobManager(out/'jobs');manager.status(ids['recovered'],verify=True)
        ids['final']=manager.start_adaptive_study(request,checkpoint=recovered);final=wait(ids['final'])
        _,error=verify_final(final,1.);unchanged(before);unchanged(prior)
        assert not (manager.directory(ids['final'])/'execution/point-005').exists()
        failed=request_for();failed['identity_recoveries'][0]['target_index']=2
        ids['failed']=manager.start_adaptive_study(failed);stopped=wait(ids['failed'])
        assert stopped['status']=='UNVERIFIED' and stopped['stop_reason']=='identity_recovery_unverified' and len(stopped['points'])==4
        assert not (manager.directory(ids['failed'])/'execution/point-005').exists()
        equality=[]
        if reference:
            old=read_adaptive_study(reference/'base/final/adaptive-study-results.json')
            for a,b in zip(old['points'],final['points'],strict=True):
                with np.load(Path(a['run'])/'solution/fields.npz') as left,np.load(Path(b['run'])/'solution/fields.npz') as right:
                    assert left.files==right.files and all(np.array_equal(left[k],right[k]) for k in left.files)
                assert read_solution(Path(a['run'])/'solution').results['modes']==read_solution(Path(b['run'])/'solution').results['modes']
                equality.append(dict(value=a['value'],all_arrays_and_rf_equal=True))
        return dict(new_fem_solves=11,job_ids=ids,frequency_error=error,native_equality=equality,all_jobs_terminal=True)
    finally:manager.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--workers-only',action='store_true');parser.add_argument('--reference',type=Path)
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();started=time.monotonic()
    if args.workers_only:report=worker_validation(out,args.reference.resolve() if args.reference else None)
    else:
        native={};rows=[];retained={}
        for name,scale,energy in [('base',1.,1.),('double',2.,1.),('energy4',1.,4.)]:
            directory=out/name;directory.mkdir();request=request_for(scale,energy)
            (directory/'request.json').write_text(json.dumps(request,indent=2)+'\n')
            first=execute_adaptive_study(request,directory/'first',max_new_attempts=1);initial=hashes(directory/'first')
            assert first['status']=='PAUSED' and first['attempts'][0]['decision']=='BISECT'
            anchor=execute_adaptive_study(request,directory/'anchor',max_new_attempts=2,checkpoint=first)
            assert anchor['accepted_point_indices']==[0,2,1] and len(anchor['points'])==3
            recovered=execute_adaptive_study(request,directory/'recovered',max_new_attempts=2,checkpoint=anchor)
            assert recovered['history']['individual_ids_complete'] and recovered['status']=='PAUSED';unchanged(initial)
            preserved=hashes(directory/'recovered');final=execute_adaptive_study(request,directory/'final',checkpoint=recovered)
            native[name],error=verify_final(final,scale);unchanged(initial);unchanged(preserved)
            higher=deepcopy(request)
            for c in higher['step_controls']:c['sample_order']=18
            for r in higher['identity_recoveries']:r['controls']['sample_order']=18
            rebuilt=saved_rebuild(higher,final['points'],directory/'order-18.json');verify_final(rebuilt,scale)
            reverse=deepcopy(request);reverse['study']['values']=[request['study']['values'][i] for i in [3,2,1,0]]
            reverse['initial_ids']=['TM010','TM011','TM020'];reverse['step_controls']=[dict(request['step_controls'][1]) for _ in range(3)]
            reverse['identity_recoveries']=[dict(target_index=2,anchor_target_index=0,controls=request['identity_recoveries'][0]['controls'])]
            backward=saved_rebuild(reverse,final['points'],directory/'reverse.json')
            assert backward['status']=='COMPLETE' and backward['history']['current_mode_ids']==['TM010','TM020','TM011']
            command=subprocess.run([sys.executable,'-m','superfish_ng','replay-adaptive-study',str(directory/'final/adaptive-study-results.json')],capture_output=True,text=True,cwd=ROOT)
            (directory/'cli.log').write_text(command.stdout+command.stderr);assert command.returncode==0
            retained.update(hashes(directory));rows.append(dict(variant=name,frequency_error=error,accepted_point_indices=final['accepted_point_indices'],
                recovery_bindings=[{k:e[k] for k in ['target_index','anchor_target_index','anchor_snapshot_index','anchor_point_index','current_point_index']} for a in final['attempts'] if (e:=a['identity_recovery'])],order18_same_decisions=True,reverse_ids=backward['history']['current_mode_ids']))
        failed=request_for();failed['identity_recoveries'][0]['target_index']=2
        stopped=execute_adaptive_study(failed,out/'failed')
        assert stopped['status']=='UNVERIFIED' and stopped['stop_reason']=='identity_recovery_unverified' and len(stopped['points'])==4
        assert stopped['history']['current_mode_ids']==['TM010','TM020','TM011'] and not (out/'failed/point-005').exists()
        assert read_adaptive_study(out/'failed/adaptive-study-results.json')==stopped
        comparisons=[]
        for name,scale,energy in [('double',2.,1.),('energy4',1.,4.)]:
            for index,length in [(0,.04),(1,.055),(2,.0475),(4,.075),(5,.08),(6,.085)]:
                old,new=native['base'][index],native[name][index]
                probes=np.array([[r*.1,z*length] for r in [.13,.37,.61,.89] for z in [.14,.38,.62,.87]])
                for mode in range(3):
                    a,b=FieldSampler.from_solution(old).evaluate(probes,mode),FieldSampler.from_solution(new).evaluate(scale*probes,mode)
                    sign=1 if np.dot(a['Hphi_A_per_m'],b['Hphi_A_per_m'])>=0 else -1;factor=sign*scale**1.5/energy**.5
                    ae=np.concatenate([a[k] for k in ['Er_quadrature_V_per_m','Ez_quadrature_V_per_m']]);be=np.concatenate([b[k] for k in ['Er_quadrature_V_per_m','Ez_quadrature_V_per_m']])
                    field=dict(magnetic=float(np.linalg.norm(a['Hphi_A_per_m']-factor*b['Hphi_A_per_m'])/np.linalg.norm(a['Hphi_A_per_m'])),electric=float(np.linalg.norm(ae-factor*be)/np.linalg.norm(ae)))
                    q0,q1=old.results['modes'][mode],new.results['modes'][mode]
                    rf={key:abs(q1[key]*(scale if key=='frequency_hz' else 1)/q0[key]-1) for key in ['frequency_hz','r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm']}
                    assert max(field.values())<2e-9 and max(rf.values())<2e-9
                    comparisons.append(dict(variant=name,point_index=index,mode_index=mode+1,rf_errors=rf,field_errors=field))
        unchanged(retained);report=dict(new_fem_solves=25,rows=rows,comparisons=comparisons,retained_source_sha256=retained)
    assert fingerprints()==before
    report.update(status='PASS',seconds=time.monotonic()-started,source_sha256=before,source_unchanged=True,
        scope='adaptive P2 cylinder bisection before an original anchor, analytical degeneracy then explicitly declared near-frequency grouping; immutable recovery/resume and field/RF scaling; no continuous-branch certificate')
    (out/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(json.dumps({k:report[k] for k in ['status','new_fem_solves','seconds']}))


if __name__=='__main__':main()
