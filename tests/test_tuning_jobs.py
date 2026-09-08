# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import json
import math
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from superfish_ng.constants import C0
from superfish_ng.jobs import JobManager,read_job,_digest
from superfish_ng.tuning import read_tune,execute_tune
from superfish_ng.tuning_jobs import execute_prepared_tune


class TuningJobTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.manager=JobManager(self.root);self.addCleanup(self.manager.close)
        self.request=json.loads(Path('examples/tuning/pillbox_length.json').read_text())
        self.request['project']['case']['mesh'].update(nr=6,nz=8)
        self.request.update(target_hz=C0/(2*math.pi)*math.hypot(2.404825557695773/.1,math.pi/.08),
            frequency_tolerance_hz=1e5,mesh_frequency_tolerance_hz=1e5)

    def wait(self,identifier):
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            if self.manager.status(identifier)['status'] not in ('queued','running'):
                return self.manager.status(identifier,verify=True)
            time.sleep(.025)
        self.fail('background tune did not finish')

    def test_background_resume_rank_crossing_and_ancestral_verification(self):
        first=self.manager.start_tune(self.request,max_new_trials=2);state=self.wait(first)
        self.assertEqual(state['status'],'complete');self.assertEqual(state['tuning_status'],'PAUSED')
        checkpoint=read_tune(self.root/first/'tune-results.json')
        second=self.manager.start_tune(self.request,checkpoint=checkpoint);state=self.wait(second)
        self.assertEqual(state['tuning_status'],'TUNED');self.assertEqual(state['computed_trials'],4)
        self.assertEqual(state['numerical_validation'],'not_checked');self.assertFalse(state['can_resume'])
        self.assertFalse((self.root/second/'execution/trial-001').exists())
        result=read_tune(self.root/second/'tune-results.json')
        self.assertEqual(result['trials'][-1]['current_mode_ids'].index('TM011'),1)
        self.manager.close();self.manager=JobManager(self.root);self.addCleanup(self.manager.close)
        self.assertEqual(self.manager.status(second,verify=True)['tuning_status'],'TUNED')
        source=self.root/first/'execution/trial-001/job.json';source.write_text(source.read_text()+' ')
        with self.assertRaises(ValueError):self.manager.status(second,verify=True)

    def test_numerical_stops_are_completed_jobs_without_success_claim(self):
        for label,change,status in [('unverified',{'controls':dict(self.request['controls'],minimum_overlap=1.)},'UNVERIFIED'),
                ('refinement',{'mesh_frequency_tolerance_hz':1.},'REFINEMENT_FAILED'),('budget',{'max_trials':2},'ITERATION_LIMIT')]:
            req=dict(self.request,**change);identifier=self.manager.start_tune(req);state=self.wait(identifier)
            self.assertEqual(state['status'],'complete');self.assertEqual(state['tuning_status'],status)
            self.assertFalse(state['can_resume'])
            with self.assertRaisesRegex(ValueError,'PAUSED'):
                self.manager.start_tune(req,checkpoint=read_tune(self.root/identifier/'tune-results.json'))

    def test_invalid_preflight_and_changed_resume_request_create_no_job(self):
        for req,limit in [(dict(self.request,extra=True),None),(self.request,True),(self.request,0)]:
            with self.assertRaises(ValueError):self.manager.start_tune(req,max_new_trials=limit)
        self.assertEqual(self.manager.list(),[])
        first=self.manager.start_tune(self.request,max_new_trials=1);self.wait(first)
        saved=read_tune(self.root/first/'tune-results.json');before=len(self.manager.list())
        with self.assertRaisesRegex(ValueError,'request differs'):
            self.manager.start_tune(dict(self.request,target_hz=1e10),checkpoint=saved)
        self.assertEqual(len(self.manager.list()),before)

    def test_cancel_after_checkpoint_and_resume_without_overwriting(self):
        req=deepcopy(self.request);req.update(frequency_tolerance_hz=1e-5,parameter_tolerance=1e-15,max_trials=60)
        identifier=self.manager.start_tune(req);checkpoint=self.root/identifier/'execution/checkpoint-001.json'
        deadline=time.monotonic()+30
        prior=None
        while time.monotonic()<deadline:
            try:prior=read_tune(checkpoint);break
            except (ValueError,OSError):time.sleep(.005)
        self.assertIsNotNone(prior);self.assertIsNone(self.manager.processes[identifier].poll())
        state=self.manager.cancel(identifier);self.assertEqual(state['status'],'cancelled');self.assertEqual(state['kind'],'tune')
        prior=read_tune(checkpoint);second=self.manager.start_tune(req,checkpoint=prior,max_new_trials=1)
        self.assertEqual(self.wait(second)['tuning_status'],'PAUSED');self.assertEqual(read_tune(checkpoint),prior)
        abandoned=self.root/'abandoned';abandoned.mkdir();(abandoned/'job.json').write_text(json.dumps(dict(status='running',kind='tune')))
        self.manager.close();self.manager=JobManager(self.root);self.addCleanup(self.manager.close)
        self.assertEqual(self.manager.status('abandoned')['status'],'interrupted')
        self.assertEqual(self.manager.status('abandoned')['kind'],'tune')

    def test_summary_kind_and_worker_envelope_tampering_are_rejected(self):
        identifier=self.manager.start_tune(self.request,max_new_trials=1);self.wait(identifier);directory=self.root/identifier
        path=directory/'job.json';original=path.read_text();state=json.loads(original);state['tuning_status']='TUNED';path.write_text(json.dumps(state))
        with self.assertRaisesRegex(ValueError,'summary'):read_job(directory)
        state=json.loads(original);state['kind']='solve';path.write_text(json.dumps(state))
        with self.assertRaisesRegex(ValueError,'kind'):read_job(directory)
        path.write_text(original)
        request_path=directory/'tune-request.json';envelope=json.loads(request_path.read_text());envelope['max_new_trials']=2
        request_path.write_text(json.dumps(envelope));manifest_path=directory/'manifest.json';manifest=json.loads(manifest_path.read_text())
        manifest['files']['tune-request.json']=_digest(request_path);manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError,'trial budget'):read_job(directory)
        envelope['max_new_trials']=1;request_path.write_text(json.dumps(envelope))
        manifest['files']['tune-request.json']=_digest(request_path)
        del manifest['files']['execution/checkpoint-001.json'];manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError,'omits'):read_job(directory)

    def test_worker_failure_keeps_checkpoint_without_completion_manifest(self):
        directory=self.root/'prepared';directory.mkdir()
        (directory/'tune-request.json').write_text(json.dumps(dict(request=self.request,max_new_trials=None,checkpoint=None)))
        def failing(request,out,**kwargs):
            execute_tune(request,out,max_new_trials=1)
            raise RuntimeError('injected worker failure')
        with patch('superfish_ng.tuning_jobs.execute_tune',side_effect=failing):
            with self.assertRaisesRegex(RuntimeError,'injected'):execute_prepared_tune(directory)
        state=read_job(directory);self.assertEqual(state['status'],'failed');self.assertEqual(state['kind'],'tune')
        self.assertFalse((directory/'manifest.json').exists())
        self.assertEqual(read_tune(directory/'execution/checkpoint-001.json')['status'],'PAUSED')

    def test_request_changed_during_worker_execution_is_not_published(self):
        directory=self.root/'changed';directory.mkdir();path=directory/'tune-request.json'
        path.write_text(json.dumps(dict(request=self.request,max_new_trials=1,checkpoint=None)))
        def changing(request,out,**kwargs):
            result=execute_tune(request,out,**kwargs);path.write_text(path.read_text()+' ');return result
        with patch('superfish_ng.tuning_jobs.execute_tune',side_effect=changing):
            with self.assertRaisesRegex(RuntimeError,'request changed'):execute_prepared_tune(directory)
        self.assertEqual(read_job(directory)['status'],'failed');self.assertFalse((directory/'manifest.json').exists())
        self.assertEqual(read_tune(directory/'execution/checkpoint-001.json')['status'],'PAUSED')
