# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
from superfish_ng.jobs import JobManager,read_job,_digest
from superfish_ng.planar_curved_tuning_saved import execute_owned_planar_curved_tune,read_owned_planar_curved_tune
from superfish_ng.planar_curved_tuning_jobs import (INPUT,RESULT,SEAL,START,_prepare,execute_prepared_planar_curved_tune,
    execute_planar_curved_tune_job,read_planar_curved_tune_job,read_planar_curved_tune_job_checkpoint)
from test_planar_curved_tuning import small_request,circle_request,workspace


def snapshot(path):return {p.relative_to(path).as_posix():p.read_bytes() for p in path.rglob('*') if p.is_file()}


class PlanarCurvedTuningJobTests(unittest.TestCase):
    def test_native_scale_prefix_creator_and_whole_job_portable_replay(self):
        with workspace('tune-job-portable') as root:
            request=small_request();first=execute_planar_curved_tune_job(request,root/'first',max_new_trials=1)
            before=snapshot(root/'first');native=snapshot(root/'first/execution/trial-001')
            second=execute_planar_curved_tune_job(request,root/'second',max_new_trials=1,checkpoint=root/'first/execution/checkpoint-001.json')
            self.assertEqual(snapshot(root/'first'),before);self.assertEqual(second['status'],'PAUSED')
            self.assertAlmostEqual(second['trials'][0]['frequency_hz']/second['trials'][1]['frequency_hz'],1.4,places=10)
            for target in (root/'second/ancestry/trial-001',root/'second/execution/trial-001'):self.assertEqual(snapshot(target),native)
            self.assertEqual(read_job(root/'second')['computed_trials'],2)
            self.assertEqual(read_job(root/'second')['numerical_validation'],'not_checked')
            (root/'first').rename(root/'first-unavailable');(root/'second').rename(root/'moved')
            moved=read_planar_curved_tune_job(root/'moved');self.assertEqual(moved['trials'],second['trials'])
            self.assertEqual(moved['trial_sources_sha256'],second['trial_sources_sha256'])
            self.assertEqual(read_planar_curved_tune_job_checkpoint(root/'moved',2)['trials'],second['trials'])

    def test_real_circle_tuned_two_gates_and_independent_bessel_absolute_frequency(self):
        with workspace('tune-job-circle') as root:
            request=circle_request();report=execute_planar_curved_tune_job(request,root/'job')
            self.assertEqual(report['status'],'TUNED',report['decision'])
            self.assertTrue(report['decision']['refined_target_met']);self.assertTrue(report['decision']['mesh_difference_met'])
            self.assertEqual(report['trials'][-1]['phase'],'refinement')
            self.assertLess(abs(report['trials'][-1]['frequency_hz']/request['target_hz']-1),1e-4)
            self.assertFalse(report['can_resume'])
            self.assertEqual(read_planar_curved_tune_job(root/'job')['trials'],report['trials'])
            with self.assertRaisesRegex(ValueError,'PAUSED'):_prepare(request,root/'forbidden',checkpoint=root/'job/execution'/f"checkpoint-{len(report['trials']):03d}.json")
            self.assertFalse((root/'forbidden').exists())

    def test_strict_submission_queued_mutation_and_prefix_request_links_are_rejected(self):
        with workspace('tune-job-invalid') as root:
            request=small_request()
            for field,value in [('schema_version',True),('extra',0),('parameter','radius_m')]:
                bad=deepcopy(request);bad[field]=value
                with self.assertRaises(ValueError):_prepare(bad,root/field)
                self.assertFalse((root/field).exists())
            for limit in (True,0):
                with self.assertRaises(ValueError):_prepare(request,root/'limit',max_new_trials=limit)
            self.assertFalse((root/'limit').exists())
            _prepare(request,root/'queued',max_new_trials=1)
            path=root/'queued'/INPUT;data=json.loads(path.read_text());data['request']['target_hz']*=1.01;path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'sealed original'):execute_prepared_planar_curved_tune(root/'queued')
            self.assertEqual(read_job(root/'queued')['status'],'failed');self.assertFalse((root/'queued/execution').exists())
            execute_owned_planar_curved_tune(request,root/'prefix',max_new_trials=1)
            changed=deepcopy(request);changed['target_hz']*=1.01
            with self.assertRaisesRegex(ValueError,'resume request differs'):_prepare(changed,root/'wrong-request',checkpoint=root/'prefix/checkpoint-001.json')
            self.assertFalse((root/'wrong-request').exists())
            alias=root/'alias';alias.symlink_to((root/'prefix').resolve(),target_is_directory=True)
            with self.assertRaises(ValueError):_prepare(request,root/'linked',checkpoint=alias/'checkpoint-001.json')
            self.assertFalse((root/'linked').exists())

    def test_failed_zero_and_resumed_prefix_remain_bound_and_replayable(self):
        with workspace('tune-job-failed') as root:
            request=small_request();first=execute_owned_planar_curved_tune(request,root/'prefix',max_new_trials=1)
            for name,checkpoint,index in [('initial',None,0),('continued',root/'prefix/checkpoint-001.json',1)]:
                _prepare(request,root/name,max_new_trials=1,checkpoint=checkpoint)
                with patch('superfish_ng.planar_curved_tuning_saved.execute_planar_project',side_effect=RuntimeError('new FEM failed')):
                    with self.assertRaisesRegex(RuntimeError,'new FEM failed'):execute_prepared_planar_curved_tune(root/name)
                self.assertEqual(read_job(root/name)['status'],'failed');self.assertFalse((root/name/'manifest.json').exists())
                saved=read_planar_curved_tune_job_checkpoint(root/name,index)
                self.assertEqual(saved['trials'],[] if index==0 else first['trials']);self.assertTrue(saved['can_resume'])
                failure=json.loads((root/name/'execution'/f'failure-{index+1:03d}.json').read_text());self.assertNotIn('frequency_hz',failure)
            resumed=execute_planar_curved_tune_job(request,root/'resumed-zero',checkpoint=root/'initial/execution/checkpoint-000.json',max_new_trials=1)
            self.assertEqual(len(resumed['trials']),1)
            before=snapshot(root/'continued');path=root/'continued'/INPUT;data=json.loads(path.read_text());data['request']['target_hz']*=2;path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):read_planar_curved_tune_job_checkpoint(root/'continued',1)
            path.write_bytes(before[INPUT])
            self.assertEqual(read_planar_curved_tune_job_checkpoint(root/'continued',1)['trials'],first['trials'])

    def test_rehashed_prefix_or_report_kind_and_start_claim_tampering_cannot_pass(self):
        with workspace('tune-job-rehashed') as root:
            request=small_request();execute_planar_curved_tune_job(request,root/'accepted',max_new_trials=1)
            for name,relative in [('prefix','execution/checkpoint-000.json'),('report',RESULT),('kind','job.json'),('start',START)]:
                target=root/name;shutil.copytree(root/'accepted',target);path=target/relative;data=json.loads(path.read_text())
                if name=='prefix':data['decision']['status']='TUNED'
                elif name=='report':data['trials'][0]['frequency_hz']*=1.01
                elif name=='kind':data['kind']='planar_tune'
                else:data['worker_claim_sha256']='0'*64
                path.write_text(json.dumps(data));manifest=target/'manifest.json';raw=json.loads(manifest.read_text())
                if name=='kind':raw['kind']='planar_tune'
                else:raw['files'][relative]=_digest(path)
                manifest.write_text(json.dumps(raw))
                with self.assertRaises(ValueError):read_job(target)
            self.assertEqual(read_job(root/'accepted')['tuning_status'],'PAUSED')

    def test_cli_pause_resume_job_selector_and_portable_replay(self):
        with workspace('tune-job-cli') as root:
            request=small_request();(root/'request.json').write_text(json.dumps(request))
            commands=[('first',['tune-planar-curved',str(root/'request.json'),'--out',str(root/'first'),'--max-new-trials','1']),
                ('resume',['resume-tune-planar-curved',str(root/'first'),'--checkpoint-index','1','--out',str(root/'second'),'--max-new-trials','1'])]
            reports=[]
            for name,args in commands:
                result=subprocess.run([sys.executable,'-m','superfish_ng',*args],capture_output=True,text=True,timeout=180)
                (root/(name+'-cli.json')).write_text(result.stdout);(root/(name+'-cli.err')).write_text(result.stderr)
                self.assertEqual(result.returncode,0,result.stderr);reports.append(json.loads(result.stdout))
            self.assertAlmostEqual(reports[0]['trials'][0]['frequency_hz']/reports[1]['trials'][1]['frequency_hz'],1.4,places=10)
            (root/'first').rename(root/'first-unavailable');(root/'second').rename(root/'moved')
            for name,args in [('replay',['replay-tune-planar-curved',str(root/'moved')]),
                ('prefix',['replay-tune-planar-curved',str(root/'moved'),'--checkpoint-index','2'])]:
                result=subprocess.run([sys.executable,'-m','superfish_ng',*args],capture_output=True,text=True,timeout=180)
                (root/(name+'-cli.json')).write_text(result.stdout);(root/(name+'-cli.err')).write_text(result.stderr)
                self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(json.loads(result.stdout)['trials'],reports[-1]['trials'])
            (root/'malformed.json').write_text('{}')
            result=subprocess.run([sys.executable,'-m','superfish_ng','resume-tune-planar-curved',str(root/'malformed.json'),'--out',str(root/'rejected')],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,2);self.assertNotIn('Traceback',result.stderr);self.assertFalse((root/'rejected').exists())

    def test_true_circle_doublet_is_completed_unverified_with_cli_exit_one(self):
        with workspace('tune-job-doublet') as root:
            request=small_request('te');(root/'request.json').write_text(json.dumps(request))
            result=subprocess.run([sys.executable,'-m','superfish_ng','tune-planar-curved',str(root/'request.json'),
                '--out',str(root/'job')],capture_output=True,text=True,timeout=180)
            (root/'execute-cli.json').write_text(result.stdout);(root/'execute-cli.err').write_text(result.stderr)
            self.assertEqual(result.returncode,1,result.stderr);report=json.loads(result.stdout)
            self.assertEqual(report['status'],'UNVERIFIED');self.assertFalse(report['can_resume'])
            self.assertEqual(len(report['trials']),1);self.assertIsNone(report['trials'][0]['frequency_hz'])
            state=read_job(root/'job');self.assertEqual(state['status'],'complete')
            self.assertEqual(state['tuning_status'],'UNVERIFIED');self.assertEqual(state['numerical_validation'],'not_checked')
            (root/'job').rename(root/'moved')
            replay=subprocess.run([sys.executable,'-m','superfish_ng','replay-tune-planar-curved',str(root/'moved')],
                capture_output=True,text=True,timeout=180)
            (root/'replay-cli.json').write_text(replay.stdout);(root/'replay-cli.err').write_text(replay.stderr)
            self.assertEqual(replay.returncode,1,replay.stderr);self.assertEqual(json.loads(replay.stdout)['trials'],report['trials'])
            resume=subprocess.run([sys.executable,'-m','superfish_ng','resume-tune-planar-curved',str(root/'moved'),
                '--checkpoint-index','1','--out',str(root/'rejected')],capture_output=True,text=True,timeout=180)
            (root/'resume-cli.err').write_text(resume.stderr)
            self.assertEqual(resume.returncode,2);self.assertNotIn('Traceback',resume.stderr);self.assertFalse((root/'rejected').exists())

    def test_actual_checkpoint_cancel_source_move_resume_and_manager_restart(self):
        with workspace('tune-job-worker') as root:
            request=small_request();measured=execute_owned_planar_curved_tune(request,root/'measured',max_new_trials=1)
            request.update(target_hz=measured['trials'][0]['frequency_hz']/1.0625,frequency_tolerance_hz=1.,parameter_tolerance=1e-15,max_trials=60)
            manager=JobManager(root/'jobs')
            try:
                cancelled=manager.start_planar_curved_tune(request);process=manager.processes[cancelled]
                checkpoint=manager.directory(cancelled)/'execution/checkpoint-001.json';deadline=time.monotonic()+180;complete_document=False
                while process.poll() is None and time.monotonic()<deadline:
                    try:complete_document=len(json.loads(checkpoint.read_text())['trials'])==1
                    except (OSError,ValueError,KeyError):complete_document=False
                    if complete_document:break
                    time.sleep(.01)
                self.assertTrue(complete_document);self.assertIsNone(process.poll())
                with self.assertRaisesRegex(ValueError,'stopped'):read_planar_curved_tune_job_checkpoint(manager.directory(cancelled),1)
                self.assertEqual(manager.cancel(cancelled)['status'],'cancelled');self.assertIsNotNone(process.poll())
                selected=read_planar_curved_tune_job_checkpoint(manager.directory(cancelled),1);self.assertEqual(selected['status'],'PAUSED')
                original=snapshot(manager.directory(cancelled)/'execution/trial-001')
                # Close the owner of the cancelled process before moving its directory.
                # A new manager owns only the resumed worker, whose input is copied.
                manager.close();manager=JobManager(root/'jobs')
                identifier=manager.start_planar_curved_tune(request,checkpoint=checkpoint,max_new_trials=1)
                completed=manager.processes[identifier];self.assertIsNone(completed.poll())
                manager.directory(cancelled).rename(root/'jobs'/(cancelled+'-unavailable'))
                self.assertIsNone(completed.poll());self.assertEqual(completed.wait(timeout=180),0)
                report=read_planar_curved_tune_job(manager.directory(identifier));self.assertEqual(report['status'],'PAUSED')
                self.assertEqual(report['trials'][0],selected['trials'][0]);self.assertEqual(len(report['trials']),2)
                for name in ('ancestry','execution'):self.assertEqual(snapshot(manager.directory(identifier)/name/'trial-001'),original)
            finally:manager.close()
            manager=JobManager(root/'jobs')
            try:
                self.assertEqual(manager.status(cancelled+'-unavailable')['status'],'cancelled')
                self.assertEqual(manager.status(identifier,verify=True)['tuning_status'],'PAUSED')
                manager.directory(identifier).rename(root/'moved')
            finally:manager.close()
            self.assertEqual(read_planar_curved_tune_job(root/'moved')['trials'],report['trials'])
            (root/'runtime-evidence.json').write_text(json.dumps(dict(cancelled_id=cancelled,cancelled_exit=process.returncode,
                completed_id=identifier,completed_exit=completed.returncode,cancelled_after_verified_checkpoint=True,
                original_job_moved_while_worker_live=True,manager_restarted=True)))
