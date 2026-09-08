# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from superfish_ng import Case
from superfish_ng.project import Project
from superfish_ng.studies import Study,execute_study
from superfish_ng.jobs import JobManager
from superfish_ng.gui_mode_tracking import tracking_response

class GUIStudyTrackingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);cls.root=Path(cls.tmp.name)
        cls.manager=JobManager(cls.root);cls.addClassCleanup(cls.manager.close)
        case=Case(((0.,.1),(.055,.1)),nr=8,nz=8,modes=3,element_order=2)
        study=Study(Project.from_dict(case.to_dict()),'sweep','/case/geometry/points_zr_m/1/0',[.055,.075,.08])
        execute_study(study,cls.root/'study')
        cls.controls=dict(mapping='normalized_cylinder',sample_order=12,minimum_overlap=.98,minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)

    def data(self):return dict(study_id='study',initial_ids=['TM010','TM020','TM011'],controls=self.controls)

    def test_shared_controls_expand_to_each_step_and_replay_text(self):
        result=tracking_response(self.manager,'track-study-modes',self.data())
        self.assertEqual(result['document']['status'],'PASS');self.assertEqual(len(result['document']['request']['step_controls']),2)
        self.assertEqual(result['document']['point_results'][-1]['current_mode_ids'],['TM010','TM011','TM020'])
        self.assertEqual(tracking_response(self.manager,'replay-mode-tracking',dict(document=result['serialized'])),result)

    def test_per_step_controls_and_unvisited_points_survive_replay(self):
        data=self.data();del data['controls'];data['step_controls']=[dict(self.controls,minimum_overlap=1),dict(self.controls)]
        result=tracking_response(self.manager,'track-study-modes',data)
        self.assertEqual(result['document']['status'],'UNVERIFIED');self.assertEqual(result['document']['unvisited_point_indices'],[2])
        self.assertEqual(tracking_response(self.manager,'replay-mode-tracking',dict(document=result['serialized'])),result)
        changed=deepcopy(result['document']);changed['point_results'][2]['status']='PASS'
        with self.assertRaisesRegex(ValueError,'replay'):tracking_response(self.manager,'replay-mode-tracking',dict(document=changed))

    def test_strict_configuration_and_wrong_job_kind(self):
        both=self.data();both['step_controls']=[self.controls,self.controls]
        with self.assertRaises(ValueError):tracking_response(self.manager,'track-study-modes',both)
        bad=self.data();bad['study_id']='../study'
        with self.assertRaisesRegex(ValueError,'identifier'):tracking_response(self.manager,'track-study-modes',bad)
        child=self.manager.import_result(str(self.root/'study'/'point-001'))
        bad=self.data();bad['study_id']=child
        with self.assertRaisesRegex(ValueError,'completed Study'):tracking_response(self.manager,'track-study-modes',bad)
