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
from superfish_ng.jobs import JobManager,read_job
from superfish_ng.planar_curved_saved import save_planar_curved_run
from superfish_ng.planar_curved_tracking_jobs import (_prepare,execute_planar_curved_tracking,
    execute_prepared_planar_curved_tracking,read_planar_curved_tracking,INPUT)
from test_planar_curved_identity_recovery import solutions,compare
from test_planar_curved_tuning import workspace


def sources(root,managed=False):
    a,_,b,_=solutions()
    if managed:
        from superfish_ng.planar_project import PlanarProject
        from superfish_ng.planar_jobs import execute_planar_project
        execute_planar_project(PlanarProject(a.case,'m'),root/'a')
    else:save_planar_curved_run(a.case,a,root/'a')
    save_planar_curved_run(b.case,b,root/'b')
    return root/'a',root/'b',compare(a,b)


class PlanarCurvedTrackingJobTests(unittest.TestCase):
    def test_exact_managed_creator_native_and_portable_replay_with_kind_downgrade_rejection(self):
        with workspace('job-portable') as root:
            a,b,q=sources(root,True)
            original=[{p.relative_to(path).as_posix():p.read_bytes() for p in path.rglob('*') if p.is_file()} for path in (a,b)]
            report=execute_planar_curved_tracking(a,b,q,root/'job')
            self.assertEqual(report['current_mode_ids'],['even-x','odd-x'])
            state=read_job(root/'job');self.assertEqual(state['status'],'complete')
            self.assertEqual(state['numerical_validation'],'not_checked')
            for side,path,files in zip(('previous','current'),(a,b),original):
                for name,data in files.items():
                    self.assertEqual((path/name).read_bytes(),data)
                    self.assertEqual((root/'job/operands'/side/name).read_bytes(),data)
                    self.assertEqual((root/'job/execution'/side/name).read_bytes(),data)
            for path in (a,b):path.rename(path.with_name(path.name+'-unavailable'))
            (root/'job').rename(root/'moved')
            self.assertEqual(read_planar_curved_tracking(root/'moved'),report)
            shutil.copytree(root/'moved',root/'forged')
            for name in ('job.json','manifest.json'):
                path=root/'forged'/name;data=json.loads(path.read_text());data['kind']='planar_tracking';path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'kind=planar_curved_tracking'):read_job(root/'forged')

    def test_queued_input_links_and_unsupported_case_are_rejected(self):
        with workspace('job-invalid') as root:
            a,b,q=sources(root);_prepare(a,b,q,root/'queued')
            path=root/'queued'/INPUT;data=json.loads(path.read_text());data['request']['controls']['minimum_overlap']=.8;path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'queued curved tracking input changed'):execute_prepared_planar_curved_tracking(root/'queued')
            self.assertEqual(read_job(root/'queued')['status'],'failed')
            self.assertFalse((root/'queued/execution').exists())
            with self.assertRaisesRegex(ValueError,'fresh queued'):execute_prepared_planar_curved_tracking(root/'queued')
            alias=root/'alias';alias.symlink_to(a.resolve(),target_is_directory=True)
            with self.assertRaises(ValueError):_prepare(alias,b,q,root/'alias-rejected')
            self.assertFalse((root/'alias-rejected').exists())
            linked=root/'linked';shutil.copytree(b,linked);(linked/'fields.npz').unlink();(linked/'fields.npz').symlink_to((b/'fields.npz').resolve())
            with self.assertRaises(ValueError):_prepare(a,linked,q,root/'linked-rejected')
            self.assertFalse((root/'linked-rejected').exists())
            from superfish_ng.planar import PlanarCase,solve_planar
            from superfish_ng.planar_saved import save_planar_run
            case=PlanarCase(.02,.02,nx=2,ny=2,modes=3);save_planar_run(case,solve_planar(case),root/'straight')
            with self.assertRaises(ValueError):_prepare(root/'straight',b,q,root/'straight-rejected')
            self.assertFalse((root/'straight-rejected').exists())

    def test_later_copy_source_change_and_completion_change_cannot_remain_complete(self):
        with workspace('job-mutation') as root:
            a,b,q=sources(root);copy=shutil.copyfile;changed=False
            def mutate(src,dst,*args,**kwargs):
                nonlocal changed
                result=copy(src,dst,*args,**kwargs)
                if not changed and Path(src).parent==b.resolve():
                    path=a/'fields.npz';path.write_bytes(path.read_bytes()+b'changed');changed=True
                return result
            with patch('superfish_ng.planar_curved_tracking_jobs.shutil.copyfile',side_effect=mutate):
                with self.assertRaisesRegex(ValueError,'source changed'):_prepare(a,b,q,root/'copy-failed')
            self.assertTrue(changed);self.assertEqual(read_job(root/'copy-failed')['status'],'failed')
            self.assertFalse((root/'copy-failed/manifest.json').exists())
            saved=root/'copy-failed/operands/previous/fields.npz';(a/'fields.npz').write_bytes(saved.read_bytes())
            reader=read_planar_curved_tracking
            def change_completion(directory):
                result=reader(directory);path=Path(directory)/INPUT;path.write_text(path.read_text()+' ');return result
            with patch('superfish_ng.planar_curved_tracking_jobs.read_planar_curved_tracking',side_effect=change_completion):
                with self.assertRaisesRegex(ValueError,'changed during completion'):execute_planar_curved_tracking(a,b,q,root/'completion-failed')
            self.assertEqual(read_job(root/'completion-failed')['status'],'failed')
            with self.assertRaisesRegex(ValueError,'require complete'):read_planar_curved_tracking(root/'completion-failed')

    def test_actual_running_worker_cancel_new_job_restart_and_moved_replay(self):
        with workspace('job-worker') as root:
            a,b,q=sources(root);manager=JobManager(root/'jobs')
            try:
                cancelled=manager.start_planar_curved_tracking(a,b,q);process=manager.processes[cancelled]
                deadline=time.monotonic()+20
                while process.poll() is None and time.monotonic()<deadline:
                    if manager.status(cancelled,verify=False)['status']=='running':break
                    time.sleep(.01)
                self.assertIsNone(process.poll())
                self.assertEqual(manager.status(cancelled,verify=False)['status'],'running')
                self.assertEqual(manager.cancel(cancelled)['status'],'cancelled')
                self.assertIsNotNone(process.poll())
                identifier=manager.start_planar_curved_tracking(a,b,q)
                for path in (a,b):path.rename(path.with_name(path.name+'-unavailable'))
                completed=manager.processes[identifier];self.assertEqual(completed.wait(timeout=60),0)
                report=read_planar_curved_tracking(manager.directory(identifier))
                self.assertEqual(report['current_mode_ids'],['even-x','odd-x'])
                _prepare(root/'a-unavailable',root/'b-unavailable',q,root/'jobs/unconsumed')
            finally:manager.close()
            manager=JobManager(root/'jobs')
            try:
                self.assertEqual(manager.status(cancelled)['status'],'cancelled')
                self.assertEqual(manager.status(identifier,verify=True)['status'],'complete')
                self.assertEqual(manager.status('unconsumed')['status'],'interrupted')
                manager.directory(identifier).rename(root/'moved')
            finally:manager.close()
            self.assertEqual(read_planar_curved_tracking(root/'moved'),report)
            (root/'runtime-evidence.json').write_text(json.dumps(dict(cancelled_id=cancelled,cancelled_exit=process.returncode,
                completed_id=identifier,completed_exit=completed.returncode,cancelled_while_running=True,manager_restarted=True)))

    def test_cli_original_rank_exchange_and_guard_exit_status(self):
        with workspace('job-cli') as root:
            a,b,q=sources(root);q.save(root/'request.json')
            guard=replace(q,controls=replace(q.controls,relative_cluster_gap=.9));guard.save(root/'guard.json')
            for name,request,status,code in [('passed','request.json','PASS',0),('guarded','guard.json','UNVERIFIED',1)]:
                completed=subprocess.run([sys.executable,'-m','superfish_ng','execute-planar-curved-tracking',str(a),str(b),str(root/request),
                    '--out',str(root/name)],capture_output=True,text=True,timeout=60)
                (root/(name+'-cli.json')).write_text(completed.stdout);(root/(name+'-cli.err')).write_text(completed.stderr)
                self.assertEqual(completed.returncode,code,completed.stderr)
                report=json.loads(completed.stdout);self.assertEqual(report['status'],status)
                if status=='PASS':self.assertEqual(report['current_mode_ids'],['even-x','odd-x'])
                else:self.assertEqual(report['current_mode_ids'],[None,None])
                replay=subprocess.run([sys.executable,'-m','superfish_ng','replay-planar-curved-tracking',str(root/name)],
                    capture_output=True,text=True,timeout=60)
                (root/(name+'-replay.json')).write_text(replay.stdout);(root/(name+'-replay.err')).write_text(replay.stderr)
                self.assertEqual(replay.returncode,code,replay.stderr);self.assertEqual(json.loads(replay.stdout),report)

    def test_rehashed_result_and_manifest_cannot_replace_original_field_ids(self):
        from superfish_ng.jobs import _digest
        with workspace('job-rehashed') as root:
            a,b,q=sources(root);execute_planar_curved_tracking(a,b,q,root/'accepted')
            shutil.copytree(root/'accepted',root/'altered')
            result=root/'altered/execution/tracking-results.json';data=json.loads(result.read_text())
            data['current_mode_ids'].reverse();result.write_text(json.dumps(data))
            inner=root/'altered/execution/manifest.json';manifest=json.loads(inner.read_text())
            manifest['files']['tracking-results.json']=_digest(result);inner.write_text(json.dumps(manifest))
            outer=root/'altered/manifest.json';manifest=json.loads(outer.read_text())
            manifest['files']['execution/tracking-results.json']=_digest(result)
            manifest['files']['execution/manifest.json']=_digest(inner);outer.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,'complete original E/H'):read_job(root/'altered')
            self.assertEqual(read_planar_curved_tracking(root/'accepted')['current_mode_ids'],['even-x','odd-x'])
