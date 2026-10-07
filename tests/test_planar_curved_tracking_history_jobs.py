# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
from superfish_ng.jobs import JobManager,read_job,_digest
from superfish_ng.planar_curved_tracking_saved import execute_owned_planar_curved_tracking,curved_tracking_snapshot
from superfish_ng.planar_curved_tracking_jobs import execute_planar_curved_tracking
from superfish_ng.planar_curved_identity_recovery import PlanarCurvedIdentityRecoveryRequest
from superfish_ng.planar_curved_tracking_history import PlanarCurvedTrackingHistoryRequest
from superfish_ng.planar_curved_tracking_history_jobs import (INPUT,_prepare,execute_prepared_planar_curved_history,
    execute_planar_curved_history,read_planar_curved_history,recover_planar_curved_history,extend_planar_curved_history)
from test_planar_curved_identity_recovery import solutions,compare
from test_planar_curved_tracking_history import native_chain
from test_planar_curved_tuning import workspace


def chain(root):
    a,c,b,later=solutions();paths=native_chain(root)
    requests=[compare(a,c),compare(c,b,True),replace(compare(b,later),previous_mode_ids=['even-x','odd-x'])]
    pairs=[]
    for i,q in enumerate(requests):
        path=root/f'pair-{i}';execute_owned_planar_curved_tracking(paths[i],paths[i+1],q,path);pairs.append(path)
    return paths,pairs,PlanarCurvedIdentityRecoveryRequest(0,compare(a,b))


def snapshot(path):return {p.relative_to(path).as_posix():p.read_bytes() for p in path.rglob('*') if p.is_file()}


class PlanarCurvedTrackingHistoryJobTests(unittest.TestCase):
    def test_comparison_job_and_owned_pair_keep_full_original_bytes_after_move(self):
        with workspace('history-job-portable') as root:
            a,_,b,later=solutions();sources=native_chain(root)
            execute_planar_curved_tracking(sources[0],sources[2],compare(a,b),root/'comparison')
            execute_owned_planar_curved_tracking(sources[2],sources[3],replace(compare(b,later),previous_mode_ids=['even-x','odd-x']),root/'pair')
            before=[snapshot(root/'comparison'),snapshot(root/'pair')]
            result=execute_planar_curved_history([root/'comparison',root/'pair'],PlanarCurvedTrackingHistoryRequest(2,3),root/'job')
            self.assertEqual(result['current_mode_ids'],['even-x','odd-x'])
            for i,files in enumerate(before):
                for name,data in files.items():self.assertEqual((root/'job/steps'/f'step-{i:04d}'/name).read_bytes(),data)
            self.assertEqual(result['step_sha256'][0],curved_tracking_snapshot(root/'comparison/execution'))
            self.assertEqual(read_job(root/'job')['step_count'],2)
            for path in [*sources,root/'comparison',root/'pair']:path.rename(path.with_name(path.name+'-unavailable'))
            (root/'job').rename(root/'moved');self.assertEqual(read_planar_curved_history(root/'moved'),result)
            shutil.copytree(root/'moved',root/'forged')
            for name in ('job.json','manifest.json'):
                path=root/'forged'/name;data=json.loads(path.read_text());data['kind']='planar_tracking_history';path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'kind=planar_curved_tracking_history'):read_job(root/'forged')

    def test_recover_extend_preserve_parent_and_optional_extension_anchor(self):
        with workspace('history-job-derived') as root:
            _,pairs,recovery=chain(root)
            unresolved=execute_planar_curved_history(pairs[:2],PlanarCurvedTrackingHistoryRequest(2,3),root/'unresolved')
            self.assertFalse(unresolved['individual_ids_complete']);before=snapshot(root/'unresolved')
            recovered=recover_planar_curved_history(root/'unresolved',recovery,root/'recovered')
            self.assertEqual(snapshot(root/'unresolved'),before)
            self.assertEqual(recovered['current_mode_ids'],['even-x','odd-x'])
            extended=extend_planar_curved_history(root/'recovered',pairs[2],root/'final')
            self.assertEqual(extended['status'],'PASS');self.assertFalse(extended['can_extend'])
            with self.assertRaisesRegex(ValueError,'max_steps'):extend_planar_curved_history(root/'final',pairs[2],root/'rejected')
            self.assertFalse((root/'rejected').exists())
            from superfish_ng.planar_curved_tracking_history import execute_owned_planar_curved_history
            execute_owned_planar_curved_history(pairs[:1],PlanarCurvedTrackingHistoryRequest(1,3),root/'raw-parent')
            raw_before=snapshot(root/'raw-parent')
            combined=extend_planar_curved_history(root/'raw-parent',pairs[1],root/'combined',recovery=recovery)
            self.assertEqual(snapshot(root/'raw-parent'),raw_before)
            self.assertEqual(combined['current_mode_ids'],['even-x','odd-x'])

    def test_queued_request_wrong_anchor_and_linked_or_duplicate_sources_rejected(self):
        with workspace('history-job-invalid') as root:
            sources,pairs,recovery=chain(root);request=PlanarCurvedTrackingHistoryRequest(2,3)
            _prepare(pairs[:2],request,root/'queued')
            path=root/'queued'/INPUT;data=json.loads(path.read_text());data['request']['max_steps']=4;path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'queued curved history input changed'):execute_prepared_planar_curved_history(root/'queued')
            self.assertEqual(read_job(root/'queued')['status'],'failed');self.assertFalse((root/'queued/execution').exists())
            with self.assertRaisesRegex(ValueError,'fresh queued'):execute_prepared_planar_curved_history(root/'queued')
            alias=root/'alias';alias.symlink_to(pairs[0].resolve(),target_is_directory=True)
            with self.assertRaises(ValueError):_prepare([alias,pairs[1]],request,root/'linked')
            self.assertFalse((root/'linked').exists())
            a,_,b,_=solutions();execute_planar_curved_tracking(sources[0],sources[2],compare(a,b),root/'comparison')
            with self.assertRaisesRegex(ValueError,'distinct original pairs'):
                _prepare([root/'comparison',root/'comparison/execution'],request,root/'duplicate')
            self.assertFalse((root/'duplicate').exists())
            bad=replace(recovery,anchor_snapshot_index=1,comparison=replace(recovery.comparison,previous_mode_ids=['odd-x','even-x']))
            bad_request=PlanarCurvedTrackingHistoryRequest(2,3,[dict(after_step_index=1,request=bad.to_dict())])
            with self.assertRaisesRegex(ValueError,'actual earlier resolved IDs'):
                execute_planar_curved_history(pairs[:2],bad_request,root/'anchor-failed')
            self.assertEqual(read_job(root/'anchor-failed')['status'],'failed');self.assertFalse((root/'anchor-failed/execution').exists())

    def test_copy_source_change_and_post_replay_input_change_fail_without_complete(self):
        with workspace('history-job-mutation') as root:
            a,_,b,later=solutions();sources=native_chain(root)
            execute_owned_planar_curved_tracking(sources[0],sources[2],compare(a,b),root/'first')
            execute_owned_planar_curved_tracking(sources[2],sources[3],replace(compare(b,later),previous_mode_ids=['even-x','odd-x']),root/'second')
            pairs=[root/'first',root/'second'];request=PlanarCurvedTrackingHistoryRequest(2,3)
            path=root/'first/tracking-results.json';original=path.read_bytes();copy=shutil.copyfile;changed=False
            def mutate(src,dst,*args,**kwargs):
                nonlocal changed
                result=copy(src,dst,*args,**kwargs)
                if not changed and Path(src).is_relative_to((root/'second').resolve()):path.write_bytes(original+b' ');changed=True
                return result
            with patch('superfish_ng.planar_curved_tracking_history_jobs.shutil.copyfile',side_effect=mutate):
                with self.assertRaisesRegex(ValueError,'source changed'):_prepare(pairs,request,root/'copy-failed')
            self.assertTrue(changed);self.assertEqual(read_job(root/'copy-failed')['status'],'failed')
            self.assertFalse((root/'copy-failed/manifest.json').exists())
            (root/'mutated-first-report.json').write_bytes(path.read_bytes());path.write_bytes(original)
            reader=read_planar_curved_history
            def change_completion(directory):
                result=reader(directory);metadata=Path(directory)/INPUT;metadata.write_text(metadata.read_text()+' ');return result
            with patch('superfish_ng.planar_curved_tracking_history_jobs.read_planar_curved_history',side_effect=change_completion):
                with self.assertRaisesRegex(ValueError,'changed during completion'):execute_planar_curved_history(pairs,request,root/'completion-failed')
            self.assertEqual(read_job(root/'completion-failed')['status'],'failed')

    def test_rehashed_anchor_frequencies_cannot_replace_complete_physics_replay(self):
        with workspace('history-job-rehashed') as root:
            _,pairs,recovery=chain(root)
            request=PlanarCurvedTrackingHistoryRequest(2,3,[dict(after_step_index=1,request=recovery.to_dict())])
            report=execute_planar_curved_history(pairs[:2],request,root/'accepted')
            self.assertEqual(report['current_mode_ids'],['even-x','odd-x'])
            shutil.copytree(root/'accepted',root/'altered')
            path=root/'altered/execution/history-results.json';data=json.loads(path.read_text())
            data['identity_recoveries'][0]['recovered_frequencies_hz']['even-x']*=1.01;path.write_text(json.dumps(data))
            inner=root/'altered/execution/manifest.json';data=json.loads(inner.read_text());data['files']['history-results.json']=_digest(path);inner.write_text(json.dumps(data))
            outer=root/'altered/manifest.json';data=json.loads(outer.read_text());data['files']['execution/history-results.json']=_digest(path)
            data['files']['execution/manifest.json']=_digest(inner);outer.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'complete original ancestry'):read_job(root/'altered')
            self.assertEqual(read_planar_curved_history(root/'accepted'),report)

    def test_true_doublet_and_guard_block_extension_with_cli_unverified_exit(self):
        with workspace('history-job-stops') as root:
            sources,pairs,_=chain(root);a,c,_,_=solutions()
            recovery=PlanarCurvedIdentityRecoveryRequest(0,compare(a,c))
            request=PlanarCurvedTrackingHistoryRequest(1,3,[dict(after_step_index=0,request=recovery.to_dict())])
            report=execute_planar_curved_history(pairs[:1],request,root/'doublet')
            self.assertEqual(report['status'],'UNVERIFIED');self.assertIsNone(report['identity_recoveries'][0]['recovered_frequencies_hz'])
            with self.assertRaisesRegex(ValueError,'UNVERIFIED'):extend_planar_curved_history(root/'doublet',pairs[1],root/'rejected')
            self.assertFalse((root/'rejected').exists())
            guard=replace(compare(a,c),controls=replace(compare(a,c).controls,relative_cluster_gap=.9))
            execute_owned_planar_curved_tracking(sources[0],sources[1],guard,root/'guard-pair')
            PlanarCurvedTrackingHistoryRequest(1,3).save(root/'guard-request.json')
            for name,args in [('execute',['execute-planar-curved-history',str(root/'guard-request.json'),'--steps',str(root/'guard-pair'),'--out',str(root/'guard')]),
                ('replay',['replay-planar-curved-history',str(root/'guard')])]:
                result=subprocess.run([sys.executable,'-m','superfish_ng',*args],capture_output=True,text=True,timeout=120)
                (root/(name+'-cli.json')).write_text(result.stdout);(root/(name+'-cli.err')).write_text(result.stderr)
                self.assertEqual(result.returncode,1,result.stderr)
                self.assertEqual(json.loads(result.stdout)['current_mode_ids'],[None,None])

    def test_actual_worker_cancel_recover_extend_restart_and_owned_move(self):
        with workspace('history-job-worker') as root:
            sources,pairs,recovery=chain(root);request=PlanarCurvedTrackingHistoryRequest(2,3);manager=JobManager(root/'jobs')
            completed=[]
            try:
                cancelled=manager.start_planar_curved_history(pairs[:2],request);process=manager.processes[cancelled];deadline=time.monotonic()+30
                while process.poll() is None and time.monotonic()<deadline:
                    if manager.status(cancelled,verify=False)['status']=='running':break
                    time.sleep(.01)
                self.assertIsNone(process.poll());self.assertEqual(manager.status(cancelled,verify=False)['status'],'running')
                self.assertEqual(manager.cancel(cancelled)['status'],'cancelled');self.assertIsNotNone(process.poll())
                identifier=manager.start_planar_curved_history(pairs[:2],request)
                self.assertIsNone(manager.processes[identifier].poll())
                for path in sources:path.rename(path.with_name(path.name+'-unavailable'))
                for path in pairs[:2]:path.rename(path.with_name(path.name+'-unavailable'))
                self.assertIsNone(manager.processes[identifier].poll())
                self.assertEqual(manager.processes[identifier].wait(timeout=180),0);completed.append(identifier)
                recovered=manager.recover_planar_curved_history(manager.directory(identifier),recovery)
                self.assertEqual(manager.processes[recovered].wait(timeout=180),0);completed.append(recovered)
                extended=manager.extend_planar_curved_history(manager.directory(recovered),pairs[2])
                self.assertEqual(manager.processes[extended].wait(timeout=180),0);completed.append(extended)
                report=read_planar_curved_history(manager.directory(extended));self.assertEqual(report['current_mode_ids'],['even-x','odd-x'])
                self.assertFalse(report['can_extend'])
            finally:manager.close()
            manager=JobManager(root/'jobs')
            try:
                self.assertEqual(manager.status(cancelled)['status'],'cancelled')
                for identifier in completed:self.assertEqual(manager.status(identifier,verify=True)['status'],'complete')
                manager.directory(extended).rename(root/'moved')
            finally:manager.close()
            pairs[2].rename(pairs[2].with_name(pairs[2].name+'-unavailable'))
            for identifier in completed[:-1]:(root/'jobs'/identifier).rename(root/'jobs'/(identifier+'-unavailable'))
            self.assertEqual(read_planar_curved_history(root/'moved'),report)
            (root/'runtime-evidence.json').write_text(json.dumps(dict(cancelled_id=cancelled,cancelled_exit=process.returncode,
                completed_ids=completed,completed_exits=[0]*len(completed),cancelled_while_running=True,manager_restarted=True,
                original_sources_moved_while_worker_live=True)))

    def test_cli_execute_recover_extend_and_moved_full_replay(self):
        with workspace('history-job-cli') as root:
            sources,pairs,recovery=chain(root);PlanarCurvedTrackingHistoryRequest(2,3).save(root/'request.json')
            (root/'recovery.json').write_text(json.dumps(recovery.to_dict()))
            commands=[('execute',['execute-planar-curved-history',str(root/'request.json'),'--steps',str(pairs[0]),str(pairs[1]),'--out',str(root/'unresolved')]),
                ('recover',['recover-planar-curved-history',str(root/'unresolved'),str(root/'recovery.json'),'--out',str(root/'recovered')]),
                ('extend',['extend-planar-curved-history',str(root/'recovered'),str(pairs[2]),'--out',str(root/'final')])]
            reports=[]
            for name,args in commands:
                result=subprocess.run([sys.executable,'-m','superfish_ng',*args],capture_output=True,text=True,timeout=180)
                (root/(name+'-cli.json')).write_text(result.stdout);(root/(name+'-cli.err')).write_text(result.stderr)
                self.assertEqual(result.returncode,0,result.stderr);reports.append(json.loads(result.stdout))
            self.assertEqual(reports[0]['current_mode_ids'],[None,None]);self.assertEqual(reports[1]['current_mode_ids'],['even-x','odd-x'])
            for path in [*sources,*pairs,root/'unresolved',root/'recovered']:path.rename(path.with_name(path.name+'-unavailable'))
            (root/'final').rename(root/'moved')
            result=subprocess.run([sys.executable,'-m','superfish_ng','replay-planar-curved-history',str(root/'moved')],capture_output=True,text=True,timeout=180)
            (root/'replay-cli.json').write_text(result.stdout);(root/'replay-cli.err').write_text(result.stderr)
            self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(json.loads(result.stdout),reports[-1])
