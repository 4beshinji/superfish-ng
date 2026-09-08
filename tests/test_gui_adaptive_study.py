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
from superfish_ng.jobs import JobManager
from superfish_ng.gui_tracked_study import tracked_study_response

class GuiAdaptiveStudyTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.manager=JobManager(self.root);self.addCleanup(self.manager.close)
        case=Case(((0.,.07),(.025,.055),(.065,.1),(.1,.08)),nr=8,nz=12,modes=1,element_order=2)
        study=Study(Project.from_dict(case.to_dict()),'sweep','/case/geometry/points_zr_m/1/1',[.055,.08])
        control=dict(mapping='normalized_profile',sample_order=12,minimum_overlap=.99,minimum_assignment_margin=.05,
            relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)
        self.request=dict(schema_version=1,study=study.to_dict(),initial_ids=['fundamental'],step_controls=[control],
            adaptive=dict(max_depth=4,max_attempts=16,minimum_parameter_step=1e-6))

    def action(self,action,**data):return tracked_study_response(self.manager,action,data)
    def wait(self,identifier):
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            if self.manager.status(identifier)['status'] not in ('queued','running'):return self.action('adaptive-study-result',id=identifier)
            time.sleep(.025)
        self.fail('adaptive GUI worker timeout')

    def test_start_result_replay_and_resume(self):
        first=self.wait(self.action('start-adaptive-study',request=self.request,max_new_attempts=1)['id'])
        self.assertEqual(first['document']['status'],'PAUSED');self.assertEqual(first['document']['attempts'][0]['decision'],'BISECT')
        self.assertEqual(self.action('replay-adaptive-study',document=first['serialized']),first)
        final=self.wait(self.action('resume-adaptive-study',document=first['serialized'])['id'])
        self.assertEqual(final['document']['status'],'COMPLETE');self.assertEqual(final['document']['accepted_point_indices'],[0,2,1])
        with self.assertRaisesRegex(ValueError,'PAUSED'):self.action('resume-adaptive-study',document=final['serialized'])

    def test_strict_requests_and_wrong_job_or_document_kind(self):
        with self.assertRaises(ValueError):self.action('start-adaptive-study',request=self.request,max_new_points=1)
        with self.assertRaises(ValueError):self.action('adaptive-study-result',id='../outside')
        identifier=self.action('start-adaptive-study',request=self.request,max_new_attempts=1)['id'];first=self.wait(identifier)
        with self.assertRaises(ValueError):self.action('tracked-study-result',id=identifier)
        with self.assertRaises(ValueError):self.action('resume-tracked-study',document=first['serialized'])
        with self.assertRaises(ValueError):self.action('resume-adaptive-study',document=first['serialized'],request=self.request)

    def test_decision_tamper_and_limits(self):
        first=self.wait(self.action('start-adaptive-study',request=self.request,max_new_attempts=1)['id'])
        changed=deepcopy(first['document']);changed['attempts'][0]['decision']='ACCEPT'
        with self.assertRaisesRegex(ValueError,'replay'):self.action('replay-adaptive-study',document=json.dumps(changed))
        self.request['adaptive']['max_depth']=0
        stopped=self.wait(self.action('start-adaptive-study',request=self.request)['id'])
        self.assertEqual(stopped['document']['status'],'UNVERIFIED');self.assertEqual(stopped['document']['unreached_target_indices'],[1])
        with self.assertRaises(ValueError):self.action('resume-adaptive-study',document=stopped['serialized'])
