# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import time
import unittest
from superfish_ng import Case
from superfish_ng.project import Project
from superfish_ng.studies import Study
from superfish_ng.jobs import JobManager,read_job
from superfish_ng.tracked_study import read_tracked_study

class TrackedStudyJobTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.manager=JobManager(self.root);self.addCleanup(self.manager.close)
        study=Study(Project.from_dict(Case(((0.,.1),(.055,.1)),nr=8,nz=8,modes=3,element_order=2).to_dict()),
            'sweep','/case/geometry/points_zr_m/1/0',[.055,.075,.08])
        control=dict(mapping='normalized_cylinder',sample_order=12,minimum_overlap=.98,minimum_assignment_margin=.05,
            relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)
        self.request=dict(schema_version=1,study=study.to_dict(),initial_ids=['TM010','TM020','TM011'],step_controls=[dict(control),dict(control)])

    def wait(self,identifier):
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            state=self.manager.status(identifier)
            if state['status'] not in ('queued','running'):return self.manager.status(identifier,verify=True)
            time.sleep(.025)
        self.fail('background tracked Study did not finish')

    def test_background_pause_resume_and_ancestral_verification(self):
        first=self.manager.start_tracked_study(self.request,max_new_points=1);state=self.wait(first)
        self.assertEqual(state['status'],'complete');self.assertEqual(state['tracking_status'],'PAUSED');self.assertTrue(state['can_resume'])
        checkpoint=read_tracked_study(self.root/first/'tracked-study-results.json')
        second=self.manager.start_tracked_study(self.request,checkpoint=checkpoint);state=self.wait(second)
        self.assertEqual(state['tracking_status'],'COMPLETE');self.assertEqual(state['computed_points'],3)
        self.assertEqual(state['numerical_validation'],'not_checked')
        self.assertFalse((self.root/second/'execution/point-001').exists())
        self.manager.close();self.manager=JobManager(self.root);self.addCleanup(self.manager.close)
        self.assertEqual(self.manager.status(second,verify=True)['tracking_status'],'COMPLETE')
        path=self.root/first/'execution/point-001/job.json';path.write_text(path.read_text()+' ')
        with self.assertRaises(ValueError):self.manager.status(second,verify=True)

    def test_unverified_is_completed_job_but_never_computes_next_point(self):
        self.request['step_controls'][0]['minimum_overlap']=1
        identifier=self.manager.start_tracked_study(self.request);state=self.wait(identifier)
        self.assertEqual(state['status'],'complete');self.assertEqual(state['tracking_status'],'UNVERIFIED');self.assertFalse(state['can_resume'])
        self.assertFalse((self.root/identifier/'execution/point-003').exists())
        with self.assertRaisesRegex(ValueError,'PAUSED'):
            self.manager.start_tracked_study(self.request,checkpoint=read_tracked_study(self.root/identifier/'tracked-study-results.json'))

    def test_cancel_and_restart_preserve_job_kind(self):
        request=deepcopy(self.request);request['study']['project']['case']['mesh'].update(nr=250,nz=250)
        identifier=self.manager.start_tracked_study(request);state=self.manager.cancel(identifier)
        self.assertEqual(state['status'],'cancelled');self.assertEqual(state['kind'],'tracked_study')
        out=self.root/'abandoned';out.mkdir();(out/'job.json').write_text(json.dumps(dict(status='running',kind='tracked_study')))
        self.manager.close();self.manager=JobManager(self.root);self.addCleanup(self.manager.close)
        self.assertEqual(self.manager.status('abandoned')['status'],'interrupted')
        self.assertEqual(self.manager.status('abandoned')['kind'],'tracked_study')

    def test_preflight_rejects_invalid_controls_without_job_creation(self):
        self.request['step_controls'][1]['unsupported']=True
        with self.assertRaises(ValueError):self.manager.start_tracked_study(self.request)
        self.assertEqual(self.manager.list(),[])

    def test_summary_tamper_and_worker_failure_are_not_success(self):
        identifier=self.manager.start_tracked_study(self.request,max_new_points=1);self.wait(identifier)
        path=self.root/identifier/'job.json';state=json.loads(path.read_text());state['tracking_status']='COMPLETE';path.write_text(json.dumps(state))
        with self.assertRaisesRegex(ValueError,'summary'):read_job(self.root/identifier)
        request=deepcopy(self.request)
        request['study']['project']['case']['geometry']['points_zr_m'][0][1]=.09
        failed=self.manager.start_tracked_study(request);state=self.wait(failed)
        self.assertEqual(state['status'],'failed');self.assertEqual(state['kind'],'tracked_study')
        self.assertFalse((self.root/failed/'manifest.json').exists())
        saved=read_tracked_study(self.root/failed/'execution/checkpoint-001.json')
        self.assertEqual(saved['status'],'PAUSED')
        self.assertFalse((self.root/failed/'execution/point-003').exists())
