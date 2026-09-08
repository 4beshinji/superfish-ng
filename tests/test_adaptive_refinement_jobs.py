# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from superfish_ng.jobs import JobManager,read_job,_digest
from superfish_ng.adaptive_refinement import execute_adaptive_refinement,read_adaptive_refinement
from superfish_ng.adaptive_refinement_jobs import execute_prepared_adaptive_refinement


class AdaptiveRefinementJobTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.manager=JobManager(self.root);self.addCleanup(self.manager.close)
        self.request=json.loads(Path('examples/adaptive_refinement/pillbox_confirmed.json').read_text())

    def wait(self,identifier):
        deadline=time.monotonic()+30
        while time.monotonic()<deadline:
            if self.manager.status(identifier)['status'] not in ('queued','running'):
                return self.manager.status(identifier,verify=True)
            time.sleep(.025)
        self.fail('background adaptive refinement did not finish')

    def result(self,identifier):return read_adaptive_refinement(self.root/identifier/'adaptive-refinement-results.json')

    def test_background_confirmation_resume_and_ancestor_verification(self):
        first=self.manager.start_adaptive_refinement(self.request,max_new_levels=4);state=self.wait(first)
        self.assertEqual(state['status'],'complete');self.assertEqual(state['refinement_status'],'PAUSED')
        checkpoint=self.result(first);self.assertEqual(checkpoint['levels'][-1]['refinement_kind'],'uniform_confirmation')
        second=self.manager.start_adaptive_refinement(self.request,checkpoint=checkpoint);state=self.wait(second)
        self.assertEqual(state['refinement_status'],'TARGETS_MET');self.assertEqual(state['computed_levels'],5)
        self.assertEqual(state['numerical_validation'],'not_checked');self.assertEqual(state['surface_status'],'UNASSESSED')
        self.assertFalse(state['can_resume']);self.assertFalse((self.root/second/'execution/level-001').exists())
        self.assertEqual(self.result(second)['sources'][:4],checkpoint['sources'])
        self.manager.close();self.manager=JobManager(self.root);self.addCleanup(self.manager.close)
        self.assertEqual(self.manager.status(second,verify=True)['refinement_status'],'TARGETS_MET')
        source=self.root/first/'execution/level-001/case.json';source.write_text(source.read_text()+' ')
        with self.assertRaises(ValueError):self.manager.status(second,verify=True)

    def test_numerical_stops_are_complete_without_accuracy_claim(self):
        for label,change,expected in (
            ('identity',dict(controls=dict(self.request['controls'],relative_cluster_gap=.9)),'UNVERIFIED'),
            ('mesh',dict(max_triangles=40),'REFINEMENT_LIMIT'),
            ('levels',dict(relative_tolerances=dict.fromkeys(self.request['relative_tolerances'],1e-14)),'LEVEL_LIMIT')):
            req=dict(self.request,**change);identifier=self.manager.start_adaptive_refinement(req);state=self.wait(identifier)
            self.assertEqual(state['status'],'complete');self.assertEqual(state['refinement_status'],expected)
            self.assertEqual(state['numerical_validation'],'not_checked');self.assertFalse(state['can_resume'])
            with self.assertRaisesRegex(ValueError,'PAUSED'):self.manager.start_adaptive_refinement(req,checkpoint=self.result(identifier))

    def test_preflight_creates_no_job_for_invalid_input_or_changed_request(self):
        for req,limit in ((dict(self.request,extra=1),None),(self.request,True),(self.request,0),(dict(self.request,max_triangles=1),None)):
            with self.assertRaises(ValueError):self.manager.start_adaptive_refinement(req,max_new_levels=limit)
        self.assertEqual(self.manager.list(),[])
        first=self.manager.start_adaptive_refinement(self.request,max_new_levels=1);self.wait(first);before=len(self.manager.list())
        with self.assertRaisesRegex(ValueError,'request differs'):
            self.manager.start_adaptive_refinement(dict(self.request,bulk_fraction=.4),checkpoint=self.result(first))
        self.assertEqual(len(self.manager.list()),before)
        legacy=json.loads(Path('examples/adaptive_refinement/pillbox.json').read_text())
        old=self.manager.start_adaptive_refinement(legacy,max_new_levels=1)
        self.assertEqual(self.wait(old)['refinement_status'],'PAUSED')

    def test_live_cancel_checkpoint_resume_and_restart(self):
        req=deepcopy(self.request);req['case']['mesh'].update(nr=8,nz=10)
        req.update(max_levels=12,max_triangles=100000,relative_tolerances=dict.fromkeys(req['relative_tolerances'],1e-14))
        identifier=self.manager.start_adaptive_refinement(req);path=self.root/identifier/'execution/checkpoint-001.json'
        deadline=time.monotonic()+30;prior=None
        while time.monotonic()<deadline:
            try:prior=read_adaptive_refinement(path);break
            except (ValueError,OSError):time.sleep(.005)
        self.assertIsNotNone(prior);self.assertIsNone(self.manager.processes[identifier].poll())
        state=self.manager.cancel(identifier);self.assertEqual(state['status'],'cancelled');self.assertEqual(state['kind'],'adaptive_refinement')
        prior=read_adaptive_refinement(path);second=self.manager.start_adaptive_refinement(req,checkpoint=prior,max_new_levels=1)
        self.assertEqual(self.wait(second)['refinement_status'],'PAUSED');self.assertEqual(read_adaptive_refinement(path),prior)
        abandoned=self.root/'abandoned';abandoned.mkdir();(abandoned/'job.json').write_text(json.dumps(dict(status='running',kind='adaptive_refinement')))
        self.manager.close();self.manager=JobManager(self.root);self.addCleanup(self.manager.close)
        self.assertEqual(self.manager.status('abandoned')['status'],'interrupted')
        self.assertEqual(self.manager.status('abandoned')['kind'],'adaptive_refinement')

    def test_summary_manifest_and_worker_budget_tampering(self):
        identifier=self.manager.start_adaptive_refinement(self.request,max_new_levels=1);self.wait(identifier);directory=self.root/identifier
        path=directory/'job.json';original=path.read_text()
        for key,value,message in (('refinement_status','TARGETS_MET','summary'),('computed_levels',True,'summary'),('kind','solve','kind'),('numerical_validation','passed','summary')):
            state=json.loads(original);state[key]=value;path.write_text(json.dumps(state))
            with self.assertRaisesRegex(ValueError,message):read_job(directory)
        path.write_text(original)
        request_path=directory/'adaptive-refinement-request.json';data=json.loads(request_path.read_text());data['max_new_levels']=2;request_path.write_text(json.dumps(data))
        manifest_path=directory/'manifest.json';manifest=json.loads(manifest_path.read_text());manifest['files'][request_path.name]=_digest(request_path);manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError,'level budget'):read_job(directory)
        data['max_new_levels']=1;request_path.write_text(json.dumps(data));manifest['files'][request_path.name]=_digest(request_path)
        del manifest['files']['execution/checkpoint-001.json'];manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError,'omits'):read_job(directory)

    def test_worker_failure_retains_checkpoint_without_completion(self):
        directory=self.root/'prepared';directory.mkdir()
        (directory/'adaptive-refinement-request.json').write_text(json.dumps(dict(request=self.request,max_new_levels=None,checkpoint=None)))
        def failing(request,out,**kwargs):
            execute_adaptive_refinement(request,out,max_new_levels=1);raise RuntimeError('injected worker failure')
        with patch('superfish_ng.adaptive_refinement_jobs.execute_adaptive_refinement',side_effect=failing):
            with self.assertRaisesRegex(RuntimeError,'injected'):execute_prepared_adaptive_refinement(directory)
        self.assertEqual(read_job(directory)['status'],'failed');self.assertFalse((directory/'manifest.json').exists())
        self.assertEqual(read_adaptive_refinement(directory/'execution/checkpoint-001.json')['status'],'PAUSED')

    def test_request_change_during_worker_run_prevents_publication(self):
        directory=self.root/'changed';directory.mkdir();path=directory/'adaptive-refinement-request.json'
        path.write_text(json.dumps(dict(request=self.request,max_new_levels=1,checkpoint=None)))
        def changing(request,out,**kwargs):
            result=execute_adaptive_refinement(request,out,**kwargs);path.write_text(path.read_text()+' ');return result
        with patch('superfish_ng.adaptive_refinement_jobs.execute_adaptive_refinement',side_effect=changing):
            with self.assertRaisesRegex(RuntimeError,'request changed'):execute_prepared_adaptive_refinement(directory)
        self.assertEqual(read_job(directory)['status'],'failed');self.assertFalse((directory/'manifest.json').exists())
        self.assertEqual(read_adaptive_refinement(directory/'execution/checkpoint-001.json')['status'],'PAUSED')
