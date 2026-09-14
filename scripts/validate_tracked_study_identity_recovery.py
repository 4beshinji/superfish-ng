# SPDX-License-Identifier: Apache-2.0
"""Independent cylinder fields, scaling and restarted workers for ID recovery."""
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
from superfish_ng.tracked_study import execute_tracked_study,read_tracked_study,replay_tracked_study
from validate_large_curved_mesh_selection import fingerprints


def request_for(scale=1.,energy=1.):
    zeros=jn_zeros(0,2);crossing=float(np.pi*.1/np.sqrt(zeros[1]**2-zeros[0]**2))
    case=Case(((0.,.1*scale),(.055*scale,.1*scale)),nr=12,nz=12,modes=3,element_order=2,normalization_j=energy)
    study=Study(Project.from_dict(case.to_dict()),'sweep','/case/geometry/points_zr_m/1/0',[x*scale for x in [.055,crossing,.075,.056,crossing,.08]])
    controls=dict(mapping='normalized_cylinder',sample_order=12,minimum_overlap=.98,minimum_assignment_margin=.05,
        relative_cluster_gap=.001,minimum_relative_singular_value=1e-8)
    return dict(schema_version=2,study=study.to_dict(),initial_ids=['TM010','TM020','TM011'],
        step_controls=[dict(controls,cluster_transition_policy='retain_subspace',minimum_cluster_link=.2) for _ in range(5)],
        identity_recoveries=[dict(point_index=2,anchor_snapshot_index=0,controls=controls),dict(point_index=5,anchor_snapshot_index=2,controls=controls)])


def hashes(directory):
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(directory).rglob('*') if p.is_file()}


def verify_unchanged(before):
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==value for p,value in before.items())


def physics(final,scale):
    errors=[];solutions=[]
    for run,length in zip(final['point_runs'],final['request']['study']['values']):
        solution=read_solution(Path(run)/'solution');solutions.append(solution)
        exact=sorted(tm0np_frequency(.1*scale,length,n,p) for n,p in [(1,0),(2,0),(1,1)])
        errors.extend(abs(f/g-1) for f,g in zip(solution.frequencies_hz,exact))
    assert max(errors)<.002
    assert final['status']=='COMPLETE' and [e['after_step_index'] for e in final['history']['identity_recoveries']]==[1,4]
    assert final['point_results'][2]['current_mode_ids']==['TM010','TM011','TM020']
    assert final['point_results'][3]['current_mode_ids']==['TM010','TM020','TM011']
    assert final['point_results'][5]['current_mode_ids']==['TM010','TM011','TM020']
    return solutions,max(errors)


def workers(out,reference):
    request=request_for();manager=JobManager(out/'jobs');ids={}
    def wait(identifier):
        while True:
            state=manager.status(identifier)
            if state['status'] not in ('queued','running'):
                assert state['status']=='complete',state
                manager.status(identifier,verify=True)
                return read_tracked_study(manager.directory(identifier)/'tracked-study-results.json')
            time.sleep(.05)
    try:
        ids['first']=manager.start_tracked_study(request,max_new_points=2);first=wait(ids['first'])
        first_hashes=hashes(manager.directory(ids['first']))
        ids['recovered']=manager.start_tracked_study(request,max_new_points=1,checkpoint=first);recovered=wait(ids['recovered'])
        assert recovered['status']=='PAUSED' and recovered['history']['individual_ids_complete']
        verify_unchanged(first_hashes);prior=hashes(manager.directory(ids['recovered']))
        manager.close();manager=JobManager(out/'jobs')
        manager.status(ids['recovered'],verify=True)
        ids['final']=manager.start_tracked_study(request,checkpoint=recovered);final=wait(ids['final'])
        solutions,error=physics(final,1.);verify_unchanged(first_hashes);verify_unchanged(prior)
        assert not (manager.directory(ids['final'])/'execution/point-003').exists()
        failed=request_for();failed['identity_recoveries'][0]['point_index']=1
        ids['failed']=manager.start_tracked_study(failed);stopped=wait(ids['failed'])
        assert stopped['status']=='UNVERIFIED' and len(stopped['point_runs'])==2 and not stopped['can_resume']
        assert not (manager.directory(ids['failed'])/'execution/point-003').exists()
        equality=[]
        if reference:
            old=read_tracked_study(reference/'base/final/checkpoint-006.json')
            for previous,current in zip(old['point_runs'],final['point_runs']):
                a,b=np.load(Path(previous)/'solution/fields.npz'),np.load(Path(current)/'solution/fields.npz')
                assert a.files==b.files and all(np.array_equal(a[k],b[k]) for k in a.files)
                assert read_solution(Path(previous)/'solution').results['modes']==read_solution(Path(current)/'solution').results['modes']
                equality.append(dict(previous=previous,current=current,all_arrays_and_rf_equal=True))
        return dict(new_fem_solves=8,job_ids=ids,frequency_error=error,native_equality=equality,all_jobs_terminal=True)
    finally:manager.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--workers-only',action='store_true');parser.add_argument('--reference',type=Path)
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();started=time.monotonic()
    if args.workers_only:report=workers(out,args.reference.resolve() if args.reference else None)
    else:
        native={};rows=[];retained={}
        for name,scale,energy in [('base',1.,1.),('double',2.,1.),('energy4',1.,4.)]:
            directory=out/name;directory.mkdir();request=request_for(scale,energy)
            (directory/'request.json').write_text(json.dumps(request,indent=2)+'\n')
            first=execute_tracked_study(request,directory/'first',max_new_points=2);initial=hashes(directory/'first')
            assert first['status']=='PAUSED' and first['history']['current_mode_ids']==['TM010',None,None]
            recovered=execute_tracked_study(request,directory/'recovered',max_new_points=1,checkpoint=first)
            assert recovered['status']=='PAUSED' and recovered['history']['individual_ids_complete'];verify_unchanged(initial)
            preserved=hashes(directory/'recovered')
            final=execute_tracked_study(request,directory/'final',checkpoint=recovered)
            native[name],error=physics(final,scale);verify_unchanged(initial);verify_unchanged(preserved)
            assert read_tracked_study(directory/'final/checkpoint-006.json')==final
            for section,limit in [('first',2),('recovered',3),('final',6)]:
                assert not (directory/section/f'point-{limit+1:03d}').exists()
            command=subprocess.run([sys.executable,'-m','superfish_ng','replay-tracked-study',str(directory/'final/checkpoint-006.json')],capture_output=True,text=True,cwd=ROOT)
            (directory/'cli.log').write_text(command.stdout+command.stderr);assert command.returncode==0
            retained.update(hashes(directory));rows.append(dict(variant=name,frequency_error=error,current_mode_ids=final['history']['current_mode_ids']))
        failed=request_for();failed['identity_recoveries'][0]['point_index']=1
        stopped=execute_tracked_study(failed,out/'failed');assert stopped['status']=='UNVERIFIED' and len(stopped['point_runs'])==2
        assert not (out/'failed/point-003').exists() and replay_tracked_study(stopped)==stopped
        comparisons=[]
        for name,scale,energy in [('double',2.,1.),('energy4',1.,4.)]:
            for index,length in [(0,.055),(2,.075),(3,.056),(5,.08)]:
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
        verify_unchanged(retained);report=dict(new_fem_solves=20,rows=rows,comparisons=comparisons,retained_source_sha256=retained)
    assert fingerprints()==before
    report.update(status='PASS',seconds=time.monotonic()-started,source_sha256=before,source_unchanged=True,
        scope='sequential P2 cylinder recovery across two degeneracies; immutable pause/resume, stop before next solve, analytical frequencies and field/RF scaling; no continuous-branch certificate')
    (out/'validation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n');print(json.dumps({k:report[k] for k in ['status','new_fem_solves','seconds']}))


if __name__=='__main__':main()
