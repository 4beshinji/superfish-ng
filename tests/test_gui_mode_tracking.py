# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from superfish_ng import Case,solve
from superfish_ng.io import save_run
from superfish_ng.jobs import JobManager
from superfish_ng.gui_mode_tracking import tracking_response

class GUIModeTrackingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);cls.root=Path(cls.tmp.name)
        cls.manager=JobManager(cls.root/'workspace');cls.ids={}
        for name,length,modes in [('a',.055,3),('b',.075,3),('short',.075,2)]:
            case=Case(((0.,.1),(length,.1)),nr=8,nz=8,modes=modes,element_order=2);path=cls.root/name
            save_run(case,solve(case),path);cls.ids[name]=cls.manager.import_result(str(path))
        cls.controls=dict(mapping='normalized_cylinder',sample_order=12,minimum_overlap=.98,minimum_assignment_margin=.05,relative_cluster_gap=1e-3,minimum_relative_singular_value=1e-8)

    def compare(self,current='b',controls=None):
        return tracking_response(self.manager,'compare-modes',dict(previous_id=self.ids['a'],current_id=self.ids[current],previous_ids=['TM010','TM020','TM011'],controls=controls or self.controls))

    def test_compare_saved_results_and_serialized_replay(self):
        response=self.compare();self.assertEqual(response['document']['tracking']['current_mode_ids'],['TM010','TM011','TM020'])
        replay=tracking_response(self.manager,'replay-mode-tracking',dict(document=response['serialized']))
        self.assertEqual(replay,response)
        self.assertEqual(json.loads(response['serialized']),response['document'])

    def test_start_and_resume_history_without_overriding_ids(self):
        pair=self.compare();history=tracking_response(self.manager,'start-mode-history',dict(document=pair['document']))
        result=tracking_response(self.manager,'extend-mode-history',dict(document=history['document'],current_id=self.ids['a'],controls=self.controls))
        self.assertEqual(result['document']['current_mode_ids'],['TM010','TM020','TM011'])
        self.assertEqual(tracking_response(self.manager,'replay-mode-tracking',dict(document=result['serialized'])),result)

    def test_unverified_and_subspace_status_are_not_individual_acceptance(self):
        failed=self.compare('short');self.assertEqual(failed['document']['status'],'UNVERIFIED')
        history=tracking_response(self.manager,'start-mode-history',dict(document=failed['document']))
        self.assertFalse(history['document']['can_extend'])
        with self.assertRaisesRegex(ValueError,'unresolved'):tracking_response(self.manager,'extend-mode-history',dict(document=history['document'],current_id=self.ids['a'],controls=self.controls))
        grouped=self.compare(controls=dict(self.controls,relative_cluster_gap=.9))
        self.assertEqual(grouped['document']['status'],'PASS');self.assertFalse(grouped['document']['tracking']['individual_ids_complete'])
        self.assertEqual(grouped['document']['tracking']['current_mode_ids'],[None]*3)

    def test_integer_threshold_uses_unmodified_server_document_text(self):
        response=self.compare(controls=dict(self.controls,minimum_overlap=1))
        self.assertEqual(response['document']['status'],'UNVERIFIED')
        history=tracking_response(self.manager,'start-mode-history',dict(document=response['serialized']))
        self.assertEqual(history['document']['status'],'UNVERIFIED')
        self.assertFalse(history['document']['can_extend'])

    def test_strict_actions_job_identity_and_modified_document(self):
        response=self.compare();changed=deepcopy(response['document']);changed['tracking']['current_mode_ids'][0]='fake'
        with self.assertRaisesRegex(ValueError,'replay'):tracking_response(self.manager,'replay-mode-tracking',dict(document=changed))
        with self.assertRaisesRegex(ValueError,'identifier'):tracking_response(self.manager,'compare-modes',dict(previous_id='../a',current_id=self.ids['b'],previous_ids=['A'],controls=self.controls))
        with self.assertRaises(ValueError):tracking_response(self.manager,'start-mode-history',dict(document=response['document'],extra=True))
        with self.assertRaises(ValueError):tracking_response(self.manager,'unknown',{})
