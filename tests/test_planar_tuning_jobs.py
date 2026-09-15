# SPDX-License-Identifier: Apache-2.0
"""Real planar workers: cancellation, immutable ancestry and strict completion."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from superfish_ng.jobs import JobManager, read_job, _digest
from superfish_ng.planar_tuning import execute_planar_tune, read_planar_tune
from superfish_ng.planar_tuning_jobs import execute_prepared_planar_tune, INPUT, RESULT
from test_planar_tuning import request


class PlanarTuningJobTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name).resolve();self.manager=JobManager(self.root)
        self.addCleanup(self.manager.close);self.request=request()

    def wait(self, identifier):
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            state=self.manager.status(identifier)
            if state['status'] not in ('queued','running'):
                self.manager.processes[identifier].wait(timeout=10)
                return self.manager.status(identifier,verify=True)
            time.sleep(.025)
        self.fail('planar worker did not finish within 60 seconds')

    def prepare(self, name, limit=1):
        directory=self.root/name;directory.mkdir()
        (directory/INPUT).write_text(json.dumps(dict(request=self.request,max_new_trials=limit,checkpoint=None)))
        (directory/'job.json').write_text(json.dumps(dict(status='queued',kind='planar_tune',input_sha256={INPUT:_digest(directory/INPUT)})))
        return directory

    def test_real_worker_resume_restart_and_original_native_ancestry(self):
        first=self.manager.start_planar_tune(self.request,max_new_trials=2)
        self.assertNotEqual(self.manager.processes[first].pid,os.getpid())
        state=self.wait(first);self.assertEqual(state['tuning_status'],'PAUSED')
        original=read_planar_tune(self.root/first/RESULT)
        second=self.manager.start_planar_tune(self.request,checkpoint=original)
        state=self.wait(second);self.assertEqual(state['tuning_status'],'TUNED')
        self.assertEqual(state['computed_trials'],3)
        self.assertEqual(state['physics'],'cartesian_cutoff_rf')
        self.assertEqual(state['numerical_validation'],'not_checked')
        self.assertFalse((self.root/second/'execution/trial-001').exists())
        final=read_planar_tune(self.root/second/RESULT)
        self.assertEqual(final['trials'][-1]['current_mode_ids'],['x','y'])
        self.manager.close();self.manager=JobManager(self.root);self.addCleanup(self.manager.close)
        self.assertEqual(self.manager.status(second,verify=True)['tuning_status'],'TUNED')
        source=Path(original['trial_runs'][0])/'job.json';source.write_text(source.read_text()+' ')
        with self.assertRaises(ValueError):self.manager.status(second,verify=True)

    def test_cancel_after_checkpoint_and_resume_only_new_trial(self):
        raw=deepcopy(self.request);raw.update(frequency_tolerance_hz=1e-5,parameter_tolerance=1e-15,max_trials=60)
        from superfish_ng.constants import C0
        raw['target_hz']=C0/(2*.21)
        identifier=self.manager.start_planar_tune(raw)
        checkpoint=self.root/identifier/'execution/checkpoint-001.json'
        prior=None;deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            try:prior=read_planar_tune(checkpoint);break
            except (OSError,ValueError):time.sleep(.005)
        self.assertIsNotNone(prior)
        self.assertIsNone(self.manager.processes[identifier].poll())
        state=self.manager.cancel(identifier);self.assertEqual(state['status'],'cancelled')
        self.assertEqual(state['kind'],'planar_tune')
        self.assertEqual(read_planar_tune(checkpoint),prior)
        resumed=self.manager.start_planar_tune(raw,checkpoint=prior,max_new_trials=1)
        self.assertEqual(self.wait(resumed)['tuning_status'],'PAUSED')
        self.assertFalse((self.root/resumed/'execution/trial-001').exists())

    def test_unverified_is_completed_and_invalid_request_allocates_nothing(self):
        for data,limit in [(dict(self.request,extra=True),None),(self.request,0),(self.request,True)]:
            with self.assertRaises(ValueError):self.manager.start_planar_tune(data,max_new_trials=limit)
        self.assertEqual(self.manager.list(),[])
        raw=dict(self.request,bounds=[.18,.2])
        identifier=self.manager.start_planar_tune(raw);state=self.wait(identifier)
        self.assertEqual(state['status'],'complete');self.assertEqual(state['tuning_status'],'UNVERIFIED')
        self.assertFalse(state['can_resume'])
        result=read_planar_tune(self.root/identifier/RESULT)
        self.assertIsNone(result['trials'][-1]['frequency_hz'])
        with self.assertRaises(ValueError):self.manager.start_planar_tune(raw,checkpoint=result)

    def test_rehashed_prefix_kind_and_envelope_tampering_cannot_bypass_replay(self):
        identifier=self.manager.start_planar_tune(self.request,max_new_trials=1);self.wait(identifier)
        directory=self.root/identifier
        originals={p:p.read_bytes() for p in directory.rglob('*') if p.is_file()}
        def restore():
            for p,content in originals.items():p.write_bytes(content)
        for filename,key,value in [('job.json','kind','solve'),('manifest.json','kind','solve')]:
            p=directory/filename;d=json.loads(p.read_text());d[key]=value;p.write_text(json.dumps(d))
            with self.assertRaisesRegex(ValueError,'kind'):read_job(directory)
            restore()
        p=directory/'execution/checkpoint-001.json';d=json.loads(p.read_text());d['decision']['next_trial']['value']*=1.1;p.write_text(json.dumps(d))
        manifest=directory/'manifest.json';d=json.loads(manifest.read_text());d['files']['execution/checkpoint-001.json']=_digest(p);manifest.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError,'prefix'):read_job(directory)
        restore()
        p=directory/INPUT;d=json.loads(p.read_text());d['max_new_trials']=2;p.write_text(json.dumps(d))
        d=json.loads(manifest.read_text());d['files'][INPUT]=_digest(p);manifest.write_text(json.dumps(d))
        state=directory/'job.json';d=json.loads(state.read_text());d['input_sha256'][INPUT]=_digest(p);state.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError,'budget'):read_job(directory)
        restore()
        with self.assertRaisesRegex(ValueError,'fresh queued'):execute_prepared_planar_tune(directory)
        self.assertEqual(read_job(directory)['tuning_status'],'PAUSED')
        from superfish_ng.planar_tuning_jobs import verify_planar_tune_job
        stale=json.loads((directory/'job.json').read_text());stale['elapsed_seconds']+=1
        with self.assertRaisesRegex(ValueError,'changed during verification'):
            verify_planar_tune_job(directory,stale,json.loads((directory/'manifest.json').read_text()))

    def test_queued_mutation_and_failure_keep_checkpoint_without_completion(self):
        changed=self.prepare('changed');p=changed/INPUT;p.write_text(p.read_text()+' ')
        with self.assertRaisesRegex(ValueError,'input changed'):execute_prepared_planar_tune(changed)
        self.assertFalse((changed/'execution').exists());self.assertEqual(read_job(changed)['status'],'failed')
        failed=self.prepare('failed')
        def fail(request,out,**kwargs):
            execute_planar_tune(request,out,max_new_trials=1)
            raise RuntimeError('injected worker failure')
        with patch('superfish_ng.planar_tuning_jobs.execute_planar_tune',side_effect=fail):
            with self.assertRaisesRegex(RuntimeError,'injected'):execute_prepared_planar_tune(failed)
        self.assertEqual(read_job(failed)['status'],'failed')
        self.assertFalse((failed/'manifest.json').exists())
        self.assertEqual(read_planar_tune(failed/'execution/checkpoint-001.json')['status'],'PAUSED')
