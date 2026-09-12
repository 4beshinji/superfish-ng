# SPDX-License-Identifier: Apache-2.0
"""Independent saved chains: topology, degeneracy, identity loss and physical source continuity."""
import argparse,hashlib,json,shutil,subprocess,sys,time
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from superfish_ng.jobs import JobManager
from superfish_ng.hphi_native import read_hphi_run
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_tracking import HphiTrackingRequest
from superfish_ng.hphi_tracking_jobs import read_hphi_tracking,_snapshot
from superfish_ng.hphi_tracking_history import HphiTrackingHistoryRequest
from superfish_ng.hphi_tracking_history_saved import read_hphi_history,history_snapshot


def fingerprints():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('src','tests','scripts','examples') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    reference=args.reference.resolve();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False);before=fingerprints();start=time.monotonic();records=[];commands=[];original={};parents={}
    fixed=json.loads((reference/'report.json').read_text());assert fixed['status']=='PASS';fixtures=fixed['records'][:8]
    with ExitStack() as cleanup:
        manager=JobManager(out/'workspace');cleanup.callback(manager.close)
        def done(identifier):assert manager.processes[identifier].wait(timeout=300)==0;return manager.directory(identifier)
        def cli(command,expected):
            process=subprocess.run([sys.executable,'-m','superfish_ng',*command],cwd=ROOT,capture_output=True,text=True);assert process.returncode==0,process.stderr;assert json.loads(process.stdout)==expected;commands.append(command)
        for i,record in enumerate(fixtures):
            source=reference/'workspace'/record['job'];original[str(source)]=_snapshot(source);forward=manager.directory(f'fixed-{i:04d}');shutil.copytree(source,forward)
            a=read_hphi_tracking(forward);assert a==json.loads((source/'tracking-results.json').read_text())
            q=HphiTrackingRequest.from_dict(a['request']);groups=[dict(indices=m['current_indices'],ids=m['previous_ids']) for m in a['matches']]
            reverse_q=replace(q,previous_comparison_mesh=q.current_comparison_mesh,current_comparison_mesh=q.previous_comparison_mesh,
                previous_comparison_order=q.current_comparison_order,current_comparison_order=q.previous_comparison_order,
                previous_mode_count=q.current_mode_count,current_mode_count=q.previous_mode_count,
                previous_mode_ids=a['current_mode_ids'] if a['individual_ids_complete'] else None,
                previous_identity_groups=None if a['individual_ids_complete'] else groups)
            reverse=done(manager.start_hphi_tracking(forward/'current',forward/'previous',reverse_q));b=read_hphi_tracking(reverse);assert b['status']=='PASS'
            first=done(manager.start_hphi_history([forward],HphiTrackingHistoryRequest(1,3)));parents[str(first)]=history_snapshot(first)
            extended=done(manager.extend_hphi_history(first,reverse));history=read_hphi_history(extended);assert history['status']=='PASS' and history['can_extend'];assert len(history['steps'])==2
            assert history['individual_ids_complete']==a['individual_ids_complete']
            assert {identifier for group in history['current_identity_groups'] for identifier in group['ids']}=={identifier for match in a['matches'] for identifier in match['previous_ids']}
            if not a['individual_ids_complete']:assert any(len(g['indices'])==2 for g in history['current_identity_groups'])
            if i in (0,6):cli(['replay-hphi-history',str(extended)],history)
            records.append(dict(name=record['name'],forward=forward.name,reverse=reverse.name,first=first.name,extended=extended.name,individual_ids_complete=history['individual_ids_complete']))
            print('DONE',record['name'],flush=True)
        first_record=records[0];forward=manager.directory(first_record['forward']);reverse=manager.directory(first_record['reverse']);first=manager.directory(first_record['first']);extended=manager.directory(first_record['extended'])
        a=read_hphi_tracking(forward);q=HphiTrackingRequest.from_dict(a['request']);reverse_q=HphiTrackingRequest.load(reverse/'tracking.json')
        # Changing U preserves the eigenfrequencies, but changes the original
        # field. Such a pair passes alone and must fail as an ancestry link.
        original_current=read_hphi_run(forward/'current/solution')
        changed=done(manager.start_hphi(HphiProject(replace(original_current.case,normalization_j=4*original_current.case.normalization_j))))
        changed_solution=read_hphi_run(changed/'solution');np.testing.assert_allclose(changed_solution.frequencies_hz,original_current.frequencies_hz,rtol=2e-13,atol=0)
        changed_pair=done(manager.start_hphi_tracking(changed,forward/'previous',reverse_q));assert read_hphi_tracking(changed_pair)['status']=='PASS'
        count=len(manager.list())
        try:manager.extend_hphi_history(first,changed_pair)
        except ValueError as error:assert 'native spectrum' in str(error)
        else:raise AssertionError('same frequencies with different normalization were linked')
        assert len(manager.list())==count
        # Display units belong to the owned Project. They do not change a
        # byte-identical native field at the common intermediate sample.
        display=done(manager.start_hphi(HphiProject(original_current.case,display_length_unit='m')))
        assert {p.name:p.read_bytes() for p in (display/'solution').iterdir()}=={p.name:p.read_bytes() for p in (forward/'current/solution').iterdir()}
        display_pair=done(manager.start_hphi_tracking(display,forward/'previous',reverse_q));display_history=done(manager.extend_hphi_history(first,display_pair));assert read_hphi_history(display_history)['status']=='PASS'
        assert json.loads((display_history/'step-0000/current/project.json').read_text())['display_length_unit']=='mm'
        assert json.loads((display_history/'step-0001/previous/project.json').read_text())['display_length_unit']=='m'
        strict_pair=done(manager.start_hphi_tracking(forward/'previous',forward/'current',replace(q,controls=replace(q.controls,minimum_overlap=1.))))
        stopped=done(manager.extend_hphi_history(extended,strict_pair));stopped_result=read_hphi_history(stopped);assert stopped_result['status']=='UNVERIFIED' and not stopped_result['can_extend'] and stopped_result['current_identity_groups'] is None
        count=len(manager.list())
        try:manager.extend_hphi_history(stopped,reverse)
        except ValueError as error:assert 'UNVERIFIED' in str(error)
        else:raise AssertionError('history continued after an unresolved comparison')
        assert len(manager.list())==count
        limited=done(manager.start_hphi_history([forward],HphiTrackingHistoryRequest(1,1)));limited_result=read_hphi_history(limited);assert limited_result['status']=='PASS' and not limited_result['can_extend'] and limited_result['current_mode_ids']==a['current_mode_ids']
        cancelled=[]
        for running in (False,True):
            identifier=manager.start_hphi_history([forward,reverse],HphiTrackingHistoryRequest(2))
            if running:
                deadline=time.monotonic()+30
                while manager.status(identifier)['status']=='queued':assert time.monotonic()<deadline;time.sleep(.02)
                assert manager.status(identifier)['status']=='running'
            observed=manager.status(identifier)['status'];assert manager.cancel(identifier)['status']=='cancelled';cancelled.append(dict(job=identifier,observed_before_cancel=observed))
        request_path=out/'history.json';HphiTrackingHistoryRequest(1,3).save(request_path)
        # Exact full result includes snapshots of the owned pair documents.
        from superfish_ng.hphi_tracking_history import verify_hphi_history_steps
        cli(['execute-hphi-history',str(request_path),'--steps',str(forward),'--out',str(out/'cli-first')],verify_hphi_history_steps([forward],HphiTrackingHistoryRequest(1,3)))
        expected=read_hphi_history(extended)
        cli(['extend-hphi-history',str(out/'cli-first'),str(reverse),'--out',str(out/'cli-extended')],expected);cli(['replay-hphi-history',str(out/'cli-extended')],expected)
        worker_kinds=[manager.status(identifier)['kind'] for identifier in manager.processes]
        manager.close()
        portable=out/'portable';shutil.copytree(extended,portable);forward.rename(out/'moved-forward');reverse.rename(out/'moved-reverse');first.rename(out/'moved-first')
        assert read_hphi_history(portable)==expected
        moved={str(first):out/'moved-first'}
        for path,snapshot in parents.items():assert history_snapshot(moved.get(path,Path(path)))==snapshot
        manager.close();manager=JobManager(out/'workspace');cleanup.callback(manager.close);states=manager.list()
        assert sum(s['status']=='cancelled' for s in states)==2
        for state in states:assert manager.status(state['id'],verify=True)['status']==state['status']
    for path,snapshot in original.items():assert _snapshot(Path(path))==snapshot
    assert fingerprints()==before
    report=dict(status='PASS',two_step_chains=len(records),history_workers=worker_kinds.count('hphi_tracking_history'),tracking_workers=worker_kinds.count('hphi_tracking'),source_project_workers=worker_kinds.count('hphi_solve'),records=records,strict_stopped_history=stopped.name,limited_history=limited.name,display_unit_history=display_history.name,
        different_normalization_same_frequencies_rejected=True,display_units_preserved_across_identical_native=True,portable_replay_after_source_moves=True,cancellations=cancelled,restarted_jobs=len(states),cli_commands=commands,original_tracking_sources_unchanged=len(original),source_sha256=before,seconds=time.monotonic()-start)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('records','source_sha256','cli_commands')}))


if __name__=='__main__':main()
