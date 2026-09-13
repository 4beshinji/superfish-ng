# SPDX-License-Identifier: Apache-2.0
"""Compare actual static Project API, worker and CLI outcomes with accepted native runs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from scripts.validate_static_field_project import references, fingerprints
from superfish_ng.static_field_project import StaticFieldProject
from superfish_ng.static_field_jobs import execute_static_field_project, read_static_field_job, _outcome
from superfish_ng.jobs import JobManager, read_job


def failure_references(root):
    chosen=[]
    for family in ('planar-bh','axis-bh','off-axis-bh'):
        directory=root/(family+'-native-independent-trial-20260913')
        assert json.loads((directory/'report.json').read_text())['status']=='PASS'
        reasons={}
        for path in sorted((directory/'api-failure').glob('*/failure.json')):
            reason=json.loads(path.read_text())['reason']
            reasons.setdefault(reason,path.parent)
        assert set(reasons)=={'invalid_initial_field','iteration_limit','line_search_limit'}
        chosen.extend((family,path,json.loads((path/'case.json').read_text()),True) for path in reasons.values())
    assert len(chosen)==9
    return chosen


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-root',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();before=fingerprints();root=args.reference_root.resolve()
    selected=[(*row,False) for row in references(root)]+failure_references(root)
    originals={};preserved={};records=[];calls=0;worker_results={}
    def cli(name,arguments,expected):
        nonlocal calls
        calls+=1
        result=subprocess.run([sys.executable,'-m','superfish_ng',*map(str,arguments)],cwd=ROOT,
            env={**os.environ,'OPENBLAS_NUM_THREADS':'1','PYTHONPATH':str(ROOT/'src')},capture_output=True,text=True,timeout=180)
        (out/(name+'.stdout')).write_text(result.stdout);(out/(name+'.stderr')).write_text(result.stderr)
        assert result.returncode==expected,(name,result.returncode,result.stderr)
        return result.stdout
    workspace=out/'workspace';manager=JobManager(workspace)
    try:
        for index,(family,source,case,failed) in enumerate(selected):
            native={p.name:p.read_bytes() for p in source.iterdir()}
            assert len(native)==(3 if failed else 5)
            originals.update({str(source/n):hashlib.sha256(raw).hexdigest() for n,raw in native.items()})
            project=StaticFieldProject.from_dict(dict(format='superfish_ng_static_field_project',project_version=1,
                case=case,display_length_unit='m' if index%2 else 'mm'))
            expected=_outcome(source,project,failed)
            assert expected==json.loads(native['failure.json' if failed else 'results.json'])
            directory=out/f'{index:02d}-{family}';directory.mkdir();input_file=directory/'input.json';project.save(input_file)
            api=directory/'api';result=execute_static_field_project(project,api)
            assert result['outcome']==expected and result['project']==project.to_dict()
            assert result['status']==('nonlinear_failed' if failed else 'complete')
            identifier=manager.start_static_field(project);end=time.monotonic()+180
            while time.monotonic()<end:
                state=manager.status(identifier)
                if state['status'] not in ('queued','running'):break
                time.sleep(.025)
            else:raise AssertionError(('worker timeout',family,source.name))
            manager.processes[identifier].wait(timeout=10)
            assert manager.processes[identifier].returncode==(1 if failed else 0)
            worker=manager.directory(identifier)
            worker_results[identifier]=result
            command=directory/'cli'
            raw=cli(f'{index}-solve',['solve-static-project',input_file,'--out',command],1 if failed else 0)
            assert json.loads(raw)==result
            assert cli(f'{index}-replay',['replay-static-project',command],1 if failed else 0)==raw
            for target in (api,worker,command):
                assert read_static_field_job(target)==result
                assert read_job(target)['status']==('failed' if failed else 'complete')
                assert (target/'project.json').read_bytes()==input_file.read_bytes()
                assert {p.name:p.read_bytes() for p in (target/'solution').iterdir()}==native
                for path in [target/'project.json',target/'manifest.json',target/'job.json',*(target/'solution').iterdir()]:
                    preserved[str(path.relative_to(out))]=hashlib.sha256(path.read_bytes()).hexdigest()
            records.append(dict(family=family,source=str(source),failed=failed,element_order=case['element_order'],
                display_length_unit=project.display_length_unit,worker_id=identifier,
                full_outcomes_identical=True,project_and_native_bytes_identical=True,
                failure_reason=expected['reason'] if failed else None))
            print('DONE',index,family,source.name,'failure' if failed else 'complete',flush=True)
    finally:manager.close()
    manager=JobManager(workspace)
    try:
        for identifier,expected in worker_results.items():
            assert read_static_field_job(manager.directory(identifier))==expected
            assert manager.status(identifier,verify=True)['status']==('failed' if expected['status']=='nonlinear_failed' else 'complete')
    finally:manager.close()
    cli('overwrite',['solve-static-project',input_file,'--out',command],2)
    cli('missing',['replay-static-project',out/'missing'],2)
    bad=out/'invalid.json';bad.write_text('{"format":"unknown_static_physics"}')
    cli('invalid',['solve-static-project',bad,'--out',out/'invalid-output'],2)
    assert not (out/'invalid-output').exists()
    for name,digest in originals.items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
    for name,digest in preserved.items():assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
    assert fingerprints()==before and calls==87 and len(originals)==192 and len(preserved)==954
    report=dict(status='PASS',cases=42,successful_cases=33,actual_nonlinear_failure_cases=9,case_families=11,
        api_jobs=42,real_worker_jobs=42,cli_jobs=42,restarted_worker_replays=42,cli_calls=calls,
        reference_files_unchanged=len(originals),owned_files_unchanged=len(preserved),
        source_sha256=before,records=records,seconds=time.monotonic()-started,
        interpretation='Full Project and native bytes, original FEM outcomes and actual nonlinear failure histories agree across API, local workers, CLI and restart. This does not establish target-version compatibility, GUI/Study completion or new discretization accuracy.')
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print({k:v for k,v in report.items() if k not in ('records','source_sha256')})


if __name__=='__main__':main()
