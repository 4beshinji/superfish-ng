# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from superfish_ng import Case
from superfish_ng.project import Project
from superfish_ng.studies import Study
from superfish_ng.jobs import execute_project
from superfish_ng.tracked_study import execute_tracked_study,read_tracked_study,replay_tracked_study

class TrackedStudyTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        study=Study(Project.from_dict(Case(((0.,.1),(.055,.1)),nr=8,nz=8,modes=3,element_order=2).to_dict()),
                    'sweep','/case/geometry/points_zr_m/1/0',[.055,.075,.08])
        controls=dict(mapping='normalized_cylinder',sample_order=12,minimum_overlap=.98,minimum_assignment_margin=.05,
                      relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)
        self.request=dict(schema_version=1,study=study.to_dict(),initial_ids=['TM010','TM020','TM011'],step_controls=[dict(controls),dict(controls)])

    def test_pause_resume_does_not_resolve_previous_points(self):
        first=execute_tracked_study(self.request,self.root/'first',max_new_points=1)
        self.assertEqual(first['status'],'PAUSED');self.assertIsNone(first['history'])
        with patch('superfish_ng.tracked_study.execute_project',wraps=execute_project) as solve:
            last=execute_tracked_study(self.request,self.root/'second',checkpoint=read_tracked_study(self.root/'first/checkpoint-001.json'))
            self.assertEqual(solve.call_count,2)
        self.assertEqual(last['status'],'COMPLETE');self.assertFalse(last['can_resume'])
        self.assertEqual(last['point_results'][-1]['current_mode_ids'],['TM010','TM011','TM020'])
        with patch('superfish_ng.jobs.solve',side_effect=AssertionError('replay must not solve')):
            self.assertEqual(replay_tracked_study(last),last)
        self.assertEqual(read_tracked_study(self.root/'first/checkpoint-001.json'),first)

    def test_unverified_stops_computation_and_cannot_resume(self):
        self.request['step_controls'][0]['minimum_overlap']=1
        with patch('superfish_ng.tracked_study.execute_project',wraps=execute_project) as solve:
            result=execute_tracked_study(self.request,self.root/'run');self.assertEqual(solve.call_count,2)
        self.assertEqual(result['status'],'UNVERIFIED');self.assertEqual(result['point_results'][2]['status'],'NOT_COMPUTED')
        self.assertFalse((self.root/'run/point-003').exists())
        with self.assertRaisesRegex(ValueError,'PAUSED'):execute_tracked_study(self.request,self.root/'resume',checkpoint=result)
        self.assertFalse((self.root/'resume').exists())

    def test_failure_keeps_checkpoint_and_retry_uses_new_directory(self):
        calls=0
        def failing(project,directory):
            nonlocal calls
            calls+=1
            if calls==2:raise RuntimeError('injected solve failure')
            return execute_project(project,directory)
        with patch('superfish_ng.tracked_study.execute_project',side_effect=failing):
            with self.assertRaisesRegex(RuntimeError,'injected'):execute_tracked_study(self.request,self.root/'run')
        saved=read_tracked_study(self.root/'run/checkpoint-001.json')
        result=execute_tracked_study(self.request,self.root/'retry',checkpoint=saved)
        self.assertEqual(result['status'],'COMPLETE')
        with self.assertRaises(FileExistsError):execute_tracked_study(self.request,self.root/'run')

    def test_strict_preflight_and_tampering(self):
        for field,value in [('initial_ids',['x','x','z']),('step_controls',[{},{}]),('schema_version',True)]:
            request=deepcopy(self.request);request[field]=value
            with self.assertRaises(ValueError):execute_tracked_study(request,self.root/'invalid')
            self.assertFalse((self.root/'invalid').exists())
        first=execute_tracked_study(self.request,self.root/'first',max_new_points=1)
        changed=deepcopy(first);changed['point_results'][0]['value']=.08
        with self.assertRaises(ValueError):replay_tracked_study(changed)
        request=deepcopy(self.request);request['step_controls'][1]['minimum_overlap']=.9
        with self.assertRaisesRegex(ValueError,'request differs'):execute_tracked_study(request,self.root/'resume',checkpoint=first)
        path=self.root/'first/point-001/job.json';path.write_text(path.read_text()+' ')
        with self.assertRaisesRegex(ValueError,'replay differs'):replay_tracked_study(first)

    def test_prior_source_change_during_next_solve_is_rejected(self):
        first=execute_tracked_study(self.request,self.root/'first',max_new_points=1)
        def changing(project,directory):
            state=execute_project(project,directory)
            p=self.root/'first/point-001/job.json';p.write_text(p.read_text()+' ')
            return state
        with patch('superfish_ng.tracked_study.execute_project',side_effect=changing):
            with self.assertRaisesRegex(ValueError,'prior checkpoint sources changed'):
                execute_tracked_study(self.request,self.root/'second',checkpoint=first)
        self.assertFalse((self.root/'second/checkpoint-002.json').exists())

    def test_cli_execution_resume_and_replay(self):
        import json
        from superfish_ng.cli import main
        path=self.root/'request.json';path.write_text(json.dumps(self.request))
        self.assertEqual(main(['execute-tracked-study',str(path),'--out',str(self.root/'cli'),'--max-new-points','1']),0)
        saved=self.root/'cli/checkpoint-001.json'
        self.assertEqual(main(['replay-tracked-study',str(saved)]),0)
        self.assertEqual(main(['resume-tracked-study',str(saved),'--out',str(self.root/'continued')]),0)
        final=self.root/'continued/checkpoint-003.json'
        self.assertEqual(read_tracked_study(final)['status'],'COMPLETE')
        self.assertEqual(main(['resume-tracked-study',str(final),'--out',str(self.root/'invalid')]),2)
