# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import time
import unittest
from superfish_ng.jobs import JobManager,_state
from superfish_ng.gui_adaptive_refinement import adaptive_refinement_response


class GuiAdaptiveRefinementTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        self.manager=JobManager(self.root);self.addCleanup(self.manager.close)
        self.request=json.loads(Path('examples/adaptive_refinement/pillbox_confirmed.json').read_text())
    def action(self,action,**data):return adaptive_refinement_response(self.manager,action,data)
    def wait(self,identifier):
        deadline=time.monotonic()+40
        while time.monotonic()<deadline:
            if self.manager.status(identifier)['status'] not in ('queued','running'):
                return self.action('adaptive-refinement-result',id=identifier)
            time.sleep(.025)
        self.fail('GUI adaptive refinement timed out')

    def test_start_replay_and_resume_preserve_confirmation_and_ancestry(self):
        self.request['mode_id']='second'
        first=self.wait(self.action('start-adaptive-refinement',request=self.request,max_new_levels=4)['id'])
        self.assertEqual(first['document']['status'],'PAUSED')
        self.assertEqual(first['document']['levels'][-1]['refinement_kind'],'uniform_confirmation')
        self.assertEqual(self.action('replay-adaptive-refinement',document=first['serialized']),first)
        final=self.wait(self.action('resume-adaptive-refinement',document=first['serialized'])['id'])
        self.assertEqual(final['document']['status'],'TARGETS_MET')
        self.assertEqual(final['document']['level_runs'][:4],first['document']['level_runs'])
        self.assertEqual(len(final['document']['levels']),5)
        self.assertEqual(final['document']['levels'][-1]['mode_index'],1)
        self.assertEqual(self.action('replay-adaptive-refinement',document=final['serialized']),final)
        with self.assertRaisesRegex(ValueError,'PAUSED'):self.action('resume-adaptive-refinement',document=final['serialized'])

    def test_strict_transport_and_changed_checkpoint(self):
        for action,data in [('start-adaptive-refinement',dict(request=self.request,unknown=True)),
                ('start-adaptive-refinement',dict(request=self.request,max_new_levels=True)),
                ('adaptive-refinement-result',dict(id='../x')),('replay-adaptive-refinement',dict(document={})),
                ('unknown',{})]:
            with self.assertRaises(ValueError):self.action(action,**data)
        self.assertEqual(list(self.root.glob('*/job.json')),[])
        first=self.wait(self.action('start-adaptive-refinement',request=self.request,max_new_levels=1)['id'])
        changed=deepcopy(first['document']);changed['surface_status']='PASS'
        with self.assertRaisesRegex(ValueError,'replay'):self.action('replay-adaptive-refinement',document=json.dumps(changed))
        with self.assertRaises(ValueError):self.action('resume-adaptive-refinement',document=first['serialized'],request=self.request)
        source=Path(first['document']['level_runs'][0])/'case.json';source.write_text(source.read_text()+'\n')
        with self.assertRaises(ValueError):self.action('replay-adaptive-refinement',document=first['serialized'])

    def test_numerical_stop_and_cancelled_partial_checkpoint_are_distinct(self):
        self.request['controls']['relative_cluster_gap']=.9
        stopped=self.wait(self.action('start-adaptive-refinement',request=self.request)['id'])
        self.assertEqual(stopped['document']['status'],'UNVERIFIED')
        self.assertIsNone(stopped['document']['levels'][-1]['quantities'])
        with self.assertRaises(ValueError):self.action('resume-adaptive-refinement',document=stopped['serialized'])
        directory=self.root/'cancelled';directory.mkdir();_state(directory,'cancelled',kind='adaptive_refinement')
        with self.assertRaisesRegex(ValueError,'completed adaptive refinement'):self.action('adaptive-refinement-result',id='cancelled')
        # A completed checkpoint survives a failed/cancelled execution independently of its job state.
        self.request=json.loads(Path('examples/adaptive_refinement/pillbox.json').read_text())
        first_id=self.action('start-adaptive-refinement',request=self.request,max_new_levels=1)['id']
        first=self.wait(first_id);_state(self.manager.directory(first_id),'cancelled',kind='adaptive_refinement')
        self.assertEqual(self.action('replay-adaptive-refinement',document=first['serialized']),first)
        resumed=self.wait(self.action('resume-adaptive-refinement',document=first['serialized'])['id'])
        self.assertEqual(resumed['document']['status'],'TARGETS_MET')
        from superfish_ng.jobs import execute_project
        from superfish_ng.project import Project
        execute_project(Project.from_dict(self.request['case']),self.root/'individual')
        with self.assertRaisesRegex(ValueError,'adaptive refinement job'):self.action('adaptive-refinement-result',id='individual')

    def test_raw_request_preserves_strict_duplicate_key_rejection(self):
        raw=json.dumps(self.request)
        duplicates=[raw.replace('"schema_version": 2','"schema_version": 1, "schema_version": 2',1),
                    raw.replace('"mapping": "nested_affine"','"mapping": "same_domain", "mapping": "nested_affine"',1)]
        for document in duplicates:
            with self.assertRaisesRegex(ValueError,'duplicate JSON key'):
                self.action('start-adaptive-refinement',request=document,max_new_levels=1)
        self.assertEqual(list(self.root.glob('*/job.json')),[])
        first=self.wait(self.action('start-adaptive-refinement',request=raw,max_new_levels=1)['id'])
        self.assertEqual(first['document']['request'],self.request)
