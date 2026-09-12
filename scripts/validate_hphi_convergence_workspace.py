# SPDX-License-Identifier: Apache-2.0
"""Actual Hphi convergence workers, original level imports, cancellation and restart."""
import argparse,hashlib,json,subprocess,sys,time
from contextlib import ExitStack
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from validate_hphi_convergence import request as explicit_request
from superfish_ng.coaxial import CoaxialCase
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_convergence import HphiConvergence
from superfish_ng.hphi_convergence_jobs import read_hphi_convergence_job
from superfish_ng.hphi_convergence_saved import execute_hphi_convergence
from superfish_ng.jobs import JobManager
from superfish_ng.gui_hphi import hphi_convergence_response


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def native_hashes(path):return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in path.iterdir() if p.is_file()}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--reference',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();started=time.monotonic();records=[];original={};cli=[]
    with ExitStack() as cleanup:
        manager=JobManager(out/'workspace');cleanup.callback(manager.close)
        requests=[(f'axis-{int(axis)}-holes-{holes}',explicit_request(axis,holes,2,1.),args.reference/f'axis-{int(axis)}-holes-{holes}-p-2-scale-1/convergence-results.json') for axis in (False,True) for holes in (0,1,2)]
        coaxial=HphiConvergence([HphiProject(CoaxialCase(.03125,.0625,.1875,nr=n,nz=2*n,element_order=2,modes=3)) for n in (2,4,8)])
        standalone=execute_hphi_convergence(coaxial,out/'coaxial-standalone');requests.append(('closed-coaxial',coaxial,out/'coaxial-standalone/convergence-results.json'))
        for name,request,reference in requests:
            identifier=manager.start_hphi_convergence(request);assert manager.processes[identifier].wait(timeout=180)==0
            directory=manager.directory(identifier);state=manager.status(identifier,verify=True);result=read_hphi_convergence_job(directory)
            assert state['status']=='complete' and state['numerical_validation']==result['status'];assert result==json.loads(reference.read_text())
            response=hphi_convergence_response(manager,'hphi-convergence-result',dict(id=identifier))[0];assert response['result']==result and response['request']==request.to_dict()
            for index,project in enumerate(request.projects):
                native=directory/f'point-{index:04d}'/'solution';original[str(native)]=native_hashes(native)
                imported=hphi_convergence_response(manager,'hphi-convergence-point',dict(id=identifier,index=index))[0]['id'];target=manager.directory(imported)
                assert HphiProject.load(target/'project.json')==project and native_hashes(target/'solution')==original[str(native)]
            command=['replay-hphi-convergence',str(directory)];done=subprocess.run([sys.executable,'-m','superfish_ng',*command],capture_output=True,text=True);assert done.returncode==0,done.stderr;assert json.loads(done.stdout)==result;cli.append(command)
            records.append(dict(name=name,job=identifier,status=result['status'],levels=len(request.projects)));(out/'progress.json').write_text(json.dumps(records,indent=2)+'\n');print('DONE',name,result['status'],flush=True)
        cancelled=manager.start_hphi_convergence(coaxial);assert manager.cancel(cancelled)['status']=='cancelled'
        large=HphiConvergence([HphiProject(CoaxialCase(.03125,.0625,.1875,nr=n,nz=n,element_order=2,modes=12)) for n in (16,32,64)])
        running=manager.start_hphi_convergence(large)
        for _ in range(600):
            state=manager.status(running)
            if state['status']=='running':break
            assert state['status']=='queued';time.sleep(.05)
        else:raise AssertionError('worker did not enter running state')
        assert manager.cancel(running)['status']=='cancelled';manager.close();manager=JobManager(out/'workspace');cleanup.callback(manager.close)
        states=manager.list();assert len(states)==30 and sum(s['status']=='complete' for s in states)==28 and sum(s['status']=='cancelled' for s in states)==2
        for state in states:assert manager.status(state['id'],verify=True)['status']==state['status']
        assert all(native_hashes(Path(path))==expected for path,expected in original.items()) and fingerprints()==before
    report=dict(status='PASS',workers=7,worker_fem_levels=21,standalone_coaxial_fem_levels=3,imported_levels=21,restarted_jobs=30,cancelled_jobs=2,cli_commands=cli,records=records,original_native_sha256=original,source_sha256=before,seconds=time.monotonic()-started)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
