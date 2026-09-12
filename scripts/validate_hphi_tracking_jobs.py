# SPDX-License-Identifier: Apache-2.0
"""Owned tracking jobs, source preservation, restart, cancellation and actual CLI."""
import argparse,hashlib,json,os,shutil,subprocess,sys,time
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng.jobs import JobManager,read_job
from superfish_ng.hphi_tracking import HphiTrackingRequest
from superfish_ng.hphi_tracking_jobs import read_hphi_tracking,execute_hphi_tracking
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_native import read_hphi_run
from superfish_ng.axis_hphi import AxisAccelerationPath


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference-root',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    reference=args.reference_root.resolve();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();started=time.monotonic();records=[];commands=[];original={};fixtures=[];source_workers=0
    ordinary=reference/'hphi-same-domain-tracking-independent-20260912';degeneracy=reference/'hphi-tracking-degeneracy-20260912'
    for axis in (0,1):
        for holes in (0,1,2):
            name=f'axis-{axis}-holes-{holes}-s-1';fixtures.append((name,ordinary/f'{name}-n-2-p-2',ordinary/f'{name}-n-3-p-2',HphiTrackingRequest.load(ordinary/f'{name}-p-2-2.request.json'),json.loads((ordinary/f'{name}-p-2-2.result.json').read_text())))
    for name in ('axis-0-p-1-s-1','axis-1-p-2-s-1'):
        fixtures.append((name,degeneracy/f'{name}-side-0',degeneracy/f'{name}-side-1',HphiTrackingRequest.load(degeneracy/f'{name}.request.json'),json.loads((degeneracy/f'{name}.result.json').read_text())))
    for _,a,b,_,_ in fixtures:
        for parent in (a,b):
            for p in parent.iterdir():original[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    with ExitStack() as cleanup:
        manager=JobManager(out/'workspace');cleanup.callback(manager.close)
        def project_worker(project):
            nonlocal source_workers
            identifier=manager.start_hphi(project);assert manager.processes[identifier].wait(timeout=90)==0
            source_workers+=1;return manager.directory(identifier)
        for i,(name,a,b,q,expected) in enumerate(fixtures):
            if i%2==0:a=project_worker(HphiProject(read_hphi_run(a).case,display_length_unit='m'))
            identifier=manager.start_hphi_tracking(a,b,q);assert manager.processes[identifier].wait(timeout=180)==0
            directory=manager.directory(identifier);result=read_hphi_tracking(directory)
            assert result==expected,(name,'worker and previously fixed core result differ')
            for side in ('previous','current'):
                point=directory/side;imported=manager.import_hphi_result(point);target=manager.directory(imported)
                assert (target/'project.json').read_bytes()==(point/'project.json').read_bytes()
                assert {p.name:p.read_bytes() for p in (target/'solution').iterdir()}=={p.name:p.read_bytes() for p in (point/'solution').iterdir()}
            command=['replay-hphi-tracking',str(directory)]
            done=subprocess.run([sys.executable,'-m','superfish_ng',*command],cwd=ROOT,capture_output=True,text=True);assert done.returncode==0,done.stderr
            assert json.loads(done.stdout)==result;commands.append(command)
            records.append(dict(name=name,job=identifier,status=result['status'],individual_ids_complete=result['individual_ids_complete']))
            print('DONE',name,flush=True)
        _,a,b,q,expected=fixtures[3]
        strict=replace(q,controls=replace(q.controls,minimum_overlap=1.))
        identifier=manager.start_hphi_tracking(a,b,strict);assert manager.processes[identifier].wait(timeout=180)==0
        result=read_hphi_tracking(manager.directory(identifier));assert result['status']=='UNVERIFIED' and result['current_mode_ids']==[None,None]
        records.append(dict(name='strict-overlap',job=identifier,status=result['status'],individual_ids_complete=False))
        originals=[read_hphi_run(p) for p in (a,b)];paths=[]
        for i,solution in enumerate(originals):
            case=replace(solution.case,normalization_j=(.5,2.)[i],acceleration=AxisAccelerationPath(0.,solution.case.length_m,.83,-.02))
            paths.append(project_worker(HphiProject(case,display_length_unit=('m','mm')[i])))
        identifier=manager.start_hphi_tracking(*paths,q);assert manager.processes[identifier].wait(timeout=180)==0
        directory=manager.directory(identifier);accelerated=read_hphi_tracking(directory);assert accelerated['status']=='PASS' and accelerated['current_mode_ids']==expected['current_mode_ids']
        for side,source in zip(('previous','current'),paths):
            assert (directory/side/'project.json').read_bytes()==(source/'project.json').read_bytes()
            copied=read_hphi_run(directory/side/'solution');assert copied.case.acceleration==AxisAccelerationPath(0.,copied.case.length_m,.83,-.02)
        for name in ('electric_grams','magnetic_grams'):
            for actual,baseline,factor in zip(accelerated['physical_mapping'][name],expected['physical_mapping'][name],(.5,1.,2.)):
                assert np.max(abs(np.asarray(actual)/factor-np.asarray(baseline)))/np.max(abs(np.asarray(baseline)))<1e-10
        records.append(dict(name='explicit-axis-path-and-unequal-normalization',job=identifier,status='PASS',individual_ids_complete=True))
        cancellation=[]
        for running in (False,True):
            identifier=manager.start_hphi_tracking(a,b,q)
            if running:
                deadline=time.monotonic()+30
                while manager.status(identifier)['status']=='queued':
                    assert time.monotonic()<deadline;time.sleep(.01)
                assert manager.status(identifier)['status']=='running'
            observed=manager.status(identifier)['status'];assert manager.cancel(identifier)['status']=='cancelled'
            cancellation.append(dict(job=identifier,observed_before_cancel=observed))
        manager.close();manager=JobManager(out/'workspace');cleanup.callback(manager.close);states=manager.list()
        assert sum(s['status']=='cancelled' for s in states)==2
        for state in states:assert manager.status(state['id'],verify=True)['status']==state['status']
        restarted=len(states)
    portable=out/'portable-sources';portable.mkdir();shutil.copytree(a,portable/'previous');shutil.copytree(b,portable/'current')
    portable_result=execute_hphi_tracking(portable/'previous',portable/'current',q,out/'portable-tracking');portable.rename(out/'moved-portable-sources')
    assert read_hphi_tracking(out/'portable-tracking')==portable_result==expected
    for command in (['execute-hphi-tracking',str(a),str(b),str(ordinary/'axis-1-holes-0-s-1-p-2-2.request.json'),'--out',str(out/'cli-tracking')],['replay-hphi-tracking',str(out/'cli-tracking')]):
        done=subprocess.run([sys.executable,'-m','superfish_ng',*command],cwd=ROOT,capture_output=True,text=True);assert done.returncode==0,done.stderr;assert json.loads(done.stdout)==expected;commands.append(command)
    for path,digest in original.items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
    assert fingerprints()==before
    report=dict(status='PASS',tracking_workers=len(records),source_project_workers=source_workers,imported_tracking_sides=16,restarted_jobs=restarted,cancellations=cancellation,
        portable_source_move_replay='PASS',cli_commands=commands,records=records,original_native_files_unchanged=len(original),source_sha256=before,seconds=time.monotonic()-started)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print({k:report[k] for k in ('status','tracking_workers','source_project_workers','imported_tracking_sides','restarted_jobs','seconds')})


if __name__=='__main__':main()
