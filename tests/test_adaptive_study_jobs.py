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
from superfish_ng.adaptive_study import read_adaptive_study

class AdaptiveStudyJobTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.manager=JobManager(self.root);self.addCleanup(self.manager.close)
        case=Case(((0.,.07),(.025,.055),(.065,.1),(.1,.08)),nr=8,nz=12,modes=1,element_order=2)
        study=Study(Project.from_dict(case.to_dict()),'sweep','/case/geometry/points_zr_m/1/1',[.055,.08])
        control=dict(mapping='normalized_profile',sample_order=12,minimum_overlap=.99,minimum_assignment_margin=.05,
            relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)
        self.request=dict(schema_version=1,study=study.to_dict(),initial_ids=['fundamental'],step_controls=[control],
            adaptive=dict(max_depth=4,max_attempts=16,minimum_parameter_step=1e-6))

    def wait(self,identifier):
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            state=self.manager.status(identifier)
            if state['status'] not in ('queued','running'):return self.manager.status(identifier,verify=True)
            time.sleep(.025)
        self.fail('adaptive worker did not finish')

    def test_background_bisection_resume_and_prior_sources(self):
        first=self.manager.start_adaptive_study(self.request,max_new_attempts=1);state=self.wait(first)
        self.assertEqual(state['status'],'complete');self.assertEqual(state['tracking_status'],'PAUSED')
        self.assertEqual(state['computed_points'],2);self.assertEqual(state['accepted_points'],1);self.assertEqual(state['completed_attempts'],1)
        checkpoint=read_adaptive_study(self.root/first/'adaptive-study-results.json')
        second=self.manager.start_adaptive_study(self.request,checkpoint=checkpoint);state=self.wait(second)
        self.assertEqual(state['tracking_status'],'COMPLETE');self.assertEqual(state['computed_points'],3);self.assertEqual(state['accepted_points'],3)
        self.assertEqual(state['unreached_target_indices'],[]);self.assertEqual(state['numerical_validation'],'not_checked')
        self.assertFalse((self.root/second/'execution/point-002').exists())
        self.manager.close();self.manager=JobManager(self.root);self.addCleanup(self.manager.close)
        self.assertEqual(self.manager.status(second,verify=True)['tracking_status'],'COMPLETE')
        path=self.root/first/'execution/point-002/job.json';path.write_text(path.read_text()+' ')
        with self.assertRaises(ValueError):self.manager.status(second,verify=True)

    def test_limits_complete_worker_but_not_tracking(self):
        self.request['adaptive']['max_depth']=0
        identifier=self.manager.start_adaptive_study(self.request);state=self.wait(identifier)
        self.assertEqual(state['status'],'complete');self.assertEqual(state['tracking_status'],'UNVERIFIED');self.assertFalse(state['can_resume'])
        self.assertEqual(state['unreached_target_indices'],[1]);self.assertFalse((self.root/identifier/'execution/point-003').exists())
        with self.assertRaisesRegex(ValueError,'PAUSED'):
            self.manager.start_adaptive_study(self.request,checkpoint=read_adaptive_study(self.root/identifier/'adaptive-study-results.json'))

    def test_cancel_and_interrupted_kind(self):
        request=deepcopy(self.request);request['study']['project']['case']['mesh'].update(nr=250,nz=250)
        identifier=self.manager.start_adaptive_study(request);self.assertEqual(self.manager.cancel(identifier)['status'],'cancelled')
        out=self.root/'abandoned';out.mkdir();(out/'job.json').write_text(json.dumps(dict(status='running',kind='adaptive_study')))
        self.manager.close();self.manager=JobManager(self.root);self.addCleanup(self.manager.close)
        self.assertEqual(self.manager.status('abandoned')['status'],'interrupted');self.assertEqual(self.manager.status('abandoned')['kind'],'adaptive_study')

    def test_preflight_and_summary_integrity(self):
        request=deepcopy(self.request);request['adaptive']['max_depth']=True
        with self.assertRaises(ValueError):self.manager.start_adaptive_study(request)
        self.assertEqual(self.manager.list(),[])
        identifier=self.manager.start_adaptive_study(self.request,max_new_attempts=1);self.wait(identifier)
        path=self.root/identifier/'job.json';original=path.read_text()
        for key,value in [('accepted_points',2),('completed_attempts',9),('unreached_target_indices',[])]:
            state=json.loads(original);state[key]=value;path.write_text(json.dumps(state))
            with self.assertRaisesRegex(ValueError,'summary'):read_job(self.root/identifier)
        path.write_text(original)

    def test_worker_failure_does_not_publish_completion(self):
        self.request['step_controls'][0]['mapping']='normalized_cylinder'
        identifier=self.manager.start_adaptive_study(self.request);state=self.wait(identifier)
        self.assertEqual(state['status'],'failed');self.assertEqual(state['kind'],'adaptive_study')
        self.assertFalse((self.root/identifier/'manifest.json').exists());self.assertFalse((self.root/identifier/'adaptive-study-results.json').exists())
