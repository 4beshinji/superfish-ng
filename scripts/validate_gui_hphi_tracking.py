# SPDX-License-Identifier: Apache-2.0
"""Replay fixed tracking records through GUI operations and preserve owned fields."""
import argparse,hashlib,json,shutil,subprocess,sys,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng.gui_hphi import hphi_response
from superfish_ng.jobs import JobManager


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    reference=args.reference.resolve();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();started=time.monotonic();records=[];original={};commands=[]
    fixed=json.loads((reference/'report.json').read_text());assert fixed['status']=='PASS'
    names={'axis-0-holes-2-s-1','axis-1-holes-2-s-1','axis-0-p-1-s-1','axis-1-p-2-s-1','strict-overlap','explicit-axis-path-and-unequal-normalization'}
    workspace=out/'workspace';workspace.mkdir();chosen=[r for r in fixed['records'] if r['name'] in names];assert len(chosen)==6
    for record in chosen:
        source=reference/'workspace'/record['job'];shutil.copytree(source,workspace/record['job'])
        for p in source.rglob('*'):
            if p.is_file():original[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    manager=JobManager(workspace);lock=threading.Lock()
    def api(action,**data):return hphi_response(manager,action,data,lock,out/'plot-cache')[0]
    try:
        for record in chosen:
            identifier=record['job'];source=reference/'workspace'/identifier
            reply=api('hphi-tracking-result',id=identifier);expected=json.loads((source/'tracking-results.json').read_text())
            assert reply['result']==expected and reply['state']['status']=='complete'
            assert api('hphi-normalize-tracking',document=json.dumps(reply['request']))==reply['request']
            imports={}
            for side in ('previous','current'):
                imported=api('hphi-tracking-side',id=identifier,side=side)['id'];imports[side]=imported
                restored=api('hphi-result',id=imported);point=source/side
                assert restored['project']==reply['projects'][side]==json.loads((point/'project.json').read_text())
                for name in ('case.json','mesh.npz','fields.npz','results.json','manifest.json'):
                    assert api('hphi-download',id=imported,file=name)==(point/'solution'/name).read_bytes()
            command=['replay-hphi-tracking',str(workspace/identifier)]
            done=subprocess.run([sys.executable,'-m','superfish_ng',*command],cwd=ROOT,capture_output=True,text=True);assert done.returncode==0,done.stderr
            assert json.loads(done.stdout)==reply['result'];commands.append(command)
            records.append(dict(name=record['name'],job=identifier,status=expected['status'],individual_ids_complete=expected['individual_ids_complete'],imported_sides=imports))
            print('DONE',record['name'],flush=True)
        manager.close();manager=JobManager(workspace);states=manager.list();assert len(states)==18
        for state in states:assert manager.status(state['id'],verify=True)['status']=='complete'
        for record in records:assert api('hphi-tracking-result',id=record['job'])['result']==json.loads((reference/'workspace'/record['job']/'tracking-results.json').read_text())
    finally:manager.close()
    for path,digest in original.items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
    assert fingerprints()==before
    report=dict(status='PASS',gui_replays=6,imported_sides=12,restarted_jobs=18,cli_commands=commands,records=records,original_files_unchanged=len(original),source_sha256=before,seconds=time.monotonic()-started)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('records','source_sha256','cli_commands')}))


if __name__=='__main__':main()
