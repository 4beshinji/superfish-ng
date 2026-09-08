# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from superfish_ng import Case
from superfish_ng.project import Project
from superfish_ng.studies import Study
from superfish_ng.jobs import execute_project
from superfish_ng.adaptive_study import execute_adaptive_study,read_adaptive_study,replay_adaptive_study

class AdaptiveResumeTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        case=Case(((0.,.07),(.025,.055),(.065,.1),(.1,.08)),nr=8,nz=12,modes=1,element_order=2)
        study=Study(Project.from_dict(case.to_dict()),'sweep','/case/geometry/points_zr_m/1/1',[.055,.08])
        control=dict(mapping='normalized_profile',sample_order=12,minimum_overlap=.99,minimum_assignment_margin=.05,
            relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)
        self.request=dict(schema_version=1,study=study.to_dict(),initial_ids=['fundamental'],step_controls=[control],
            adaptive=dict(max_depth=4,max_attempts=16,minimum_parameter_step=1e-6))

    def test_pause_after_rejection_resume_midpoint_then_cached_endpoint(self):
        first=execute_adaptive_study(self.request,self.root/'first',max_new_attempts=1)
        self.assertEqual(first['status'],'PAUSED');self.assertTrue(first['can_resume']);self.assertIsNone(first['history'])
        self.assertEqual([p['value'] for p in first['pending_targets']],[.0675,.08])
        self.assertEqual(first['attempts'][0]['decision'],'BISECT')
        old=(self.root/'first/checkpoint-001.json').read_bytes()
        with patch('superfish_ng.adaptive_study.execute_project',wraps=execute_project) as solve:
            second=execute_adaptive_study(self.request,self.root/'second',checkpoint=first,max_new_attempts=1)
            self.assertEqual(solve.call_count,1)
        self.assertEqual(second['status'],'PAUSED');self.assertEqual(second['accepted_point_indices'],[0,2])
        with patch('superfish_ng.jobs.solve',side_effect=AssertionError('cached endpoint must not solve')):
            third=execute_adaptive_study(self.request,self.root/'third',checkpoint=second)
            self.assertEqual(read_adaptive_study(self.root/'third/adaptive-study-results.json'),third)
        self.assertEqual(third['status'],'COMPLETE');self.assertFalse(third['can_resume'])
        self.assertEqual(third['accepted_point_indices'],[0,2,1]);self.assertEqual(third['history']['current_mode_ids'],['fundamental'])
        self.assertEqual((self.root/'first/checkpoint-001.json').read_bytes(),old)
        self.assertEqual(read_adaptive_study(self.root/'first/checkpoint-001.json'),first)
        self.assertFalse((self.root/'third/point-001').exists())

    def test_global_limits_do_not_reset_on_resume(self):
        self.request['adaptive']['max_attempts']=2
        first=execute_adaptive_study(self.request,self.root/'first',max_new_attempts=1)
        stopped=execute_adaptive_study(self.request,self.root/'second',checkpoint=first,max_new_attempts=1)
        self.assertEqual(stopped['status'],'UNVERIFIED');self.assertEqual(stopped['stop_reason'],'maximum_attempts')
        self.assertEqual(stopped['unreached_target_indices'],[1])
        with self.assertRaisesRegex(ValueError,'PAUSED'):execute_adaptive_study(self.request,self.root/'invalid',checkpoint=stopped)
        self.assertFalse((self.root/'invalid').exists())

    def test_request_queue_and_source_tampering_are_rejected(self):
        first=execute_adaptive_study(self.request,self.root/'first',max_new_attempts=1)
        request=deepcopy(self.request);request['adaptive']['max_attempts']+=1
        with self.assertRaisesRegex(ValueError,'request differs'):execute_adaptive_study(request,self.root/'invalid',checkpoint=first)
        changed=deepcopy(first);changed['pending_targets'].reverse()
        with self.assertRaisesRegex(ValueError,'replay'):replay_adaptive_study(changed)
        path=Path(first['points'][1]['run'])/'job.json';path.write_text(path.read_text()+' ')
        with self.assertRaises(ValueError):execute_adaptive_study(self.request,self.root/'invalid',checkpoint=first)
        self.assertFalse((self.root/'invalid').exists())

    def test_failure_retains_replayable_checkpoint_for_new_output_retry(self):
        count=0
        def failing(project,run):
            nonlocal count
            count+=1
            if count==3:raise RuntimeError('injected midpoint failure')
            return execute_project(project,run)
        with patch('superfish_ng.adaptive_study.execute_project',side_effect=failing):
            with self.assertRaisesRegex(RuntimeError,'midpoint'):execute_adaptive_study(self.request,self.root/'failed')
        checkpoint=read_adaptive_study(self.root/'failed/checkpoint-001.json')
        result=execute_adaptive_study(self.request,self.root/'retry',checkpoint=checkpoint)
        self.assertEqual(result['status'],'COMPLETE');self.assertEqual(len(result['points']),3)
        self.assertFalse((self.root/'failed/adaptive-study-results.json').exists())

    def test_version_one_replay_and_cli_resume(self):
        from superfish_ng.cli import main
        path=self.root/'request.json';path.write_text(json.dumps(self.request))
        self.assertEqual(main(['execute-adaptive-study',str(path),'--out',str(self.root/'first'),'--max-new-attempts','1']),0)
        self.assertEqual(main(['resume-adaptive-study',str(self.root/'first/checkpoint-001.json'),'--out',str(self.root/'second')]),0)
        result=read_adaptive_study(self.root/'second/adaptive-study-results.json')
        legacy=deepcopy(result);legacy['schema_version']=1;del legacy['can_resume'];del legacy['pending_targets']
        self.assertEqual(replay_adaptive_study(legacy),legacy)
        with self.assertRaisesRegex(ValueError,'PAUSED'):execute_adaptive_study(self.request,self.root/'invalid',checkpoint=legacy)
        for value in (0,True,1.5):
            with self.assertRaisesRegex(ValueError,'positive integer'):execute_adaptive_study(self.request,self.root/'invalid',max_new_attempts=value)
