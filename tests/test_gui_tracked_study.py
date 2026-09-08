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

class GuiTrackedStudyTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.manager=JobManager(self.root);self.addCleanup(self.manager.close)
        study=Study(Project.from_dict(Case(((0.,.1),(.055,.1)),nr=8,nz=8,modes=3,element_order=2).to_dict()),
            'sweep','/case/geometry/points_zr_m/1/0',[.055,.075,.08])
        control=dict(mapping='normalized_cylinder',sample_order=12,minimum_overlap=.98,minimum_assignment_margin=.05,
            relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)
        self.request=dict(schema_version=1,study=study.to_dict(),initial_ids=['TM010','TM020','TM011'],step_controls=[dict(control),dict(control)])

    def action(self,action,**data):return tracked_study_response(self.manager,action,data)
    def wait(self,identifier):
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            if self.manager.status(identifier)['status'] not in ('queued','running'):return self.action('tracked-study-result',id=identifier)
            time.sleep(.025)
        self.fail('GUI tracked Study timed out')

    def test_start_open_serialized_replay_and_resume(self):
        first=self.action('start-tracked-study',request=self.request,max_new_points=1)
        response=self.wait(first['id']);self.assertEqual(response['document']['status'],'PAUSED')
        self.assertEqual(self.action('replay-tracked-study',document=response['serialized']),response)
        resumed=self.action('resume-tracked-study',document=response['serialized'])
        last=self.wait(resumed['id']);self.assertEqual(last['document']['status'],'COMPLETE')
        self.assertEqual(last['document']['point_results'][-1]['current_mode_ids'],['TM010','TM011','TM020'])
        self.assertEqual(self.action('replay-tracked-study',document=last['serialized']),last)
        with self.assertRaisesRegex(ValueError,'PAUSED'):self.action('resume-tracked-study',document=last['serialized'])

    def test_strict_requests_and_modified_checkpoint(self):
        with self.assertRaises(ValueError):self.action('start-tracked-study',request=self.request,unknown=True)
        with self.assertRaises(ValueError):self.action('tracked-study-result',id='../outside')
        response=self.wait(self.action('start-tracked-study',request=self.request,max_new_points=1)['id'])
        changed=deepcopy(response['document']);changed['point_results'][0]['value']=.123
        with self.assertRaisesRegex(ValueError,'replay'):self.action('replay-tracked-study',document=json.dumps(changed))
        with self.assertRaises(ValueError):self.action('resume-tracked-study',document=response['serialized'],request=self.request)

    def test_unverified_result_and_nontracked_job_rejection(self):
        self.request['step_controls'][0]['minimum_overlap']=1
        result=self.wait(self.action('start-tracked-study',request=self.request)['id'])['document']
        self.assertEqual(result['status'],'UNVERIFIED');self.assertEqual(result['point_results'][2]['status'],'NOT_COMPUTED')
        with self.assertRaises(ValueError):self.action('resume-tracked-study',document=result)
        from superfish_ng.jobs import execute_project
        execute_project(Study.from_dict(self.request['study']).projects()[0],self.root/'individual')
        with self.assertRaisesRegex(ValueError,'tracked Study'):self.action('tracked-study-result',id='individual')
