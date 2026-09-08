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

class AdaptiveStudyTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
        case=Case(((0.,.07),(.025,.055),(.065,.1),(.1,.08)),nr=8,nz=12,modes=1,element_order=2)
        study=Study(Project.from_dict(case.to_dict()),'sweep','/case/geometry/points_zr_m/1/1',[.055,.08])
        control=dict(mapping='normalized_profile',sample_order=12,minimum_overlap=.99,minimum_assignment_margin=.05,
            relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)
        self.request=dict(schema_version=1,study=study.to_dict(),initial_ids=['fundamental'],step_controls=[control],
            adaptive=dict(max_depth=4,max_attempts=16,minimum_parameter_step=1e-6))

    def test_failed_coarse_pair_is_retained_and_endpoint_is_solved_once(self):
        with patch('superfish_ng.adaptive_study.execute_project',wraps=execute_project) as solver:
            result=execute_adaptive_study(self.request,self.root/'run');self.assertEqual(solver.call_count,3)
        self.assertEqual(result['status'],'COMPLETE')
        self.assertEqual([a['decision'] for a in result['attempts']],['BISECT','ACCEPT','ACCEPT'])
        self.assertEqual(result['attempts'][0]['correspondence']['status'],'UNVERIFIED')
        self.assertEqual(result['accepted_point_indices'],[0,2,1]);self.assertEqual(result['unreached_target_indices'],[])
        self.assertEqual(result['history']['current_mode_ids'],['fundamental'])
        for a in result['attempts']:self.assertEqual(a['correspondence']['request']['controls']['minimum_overlap'],.99)
        with patch('superfish_ng.jobs.solve',side_effect=AssertionError('replay must not solve')):
            self.assertEqual(read_adaptive_study(self.root/'run/adaptive-study-results.json'),result)
        with self.assertRaises(FileExistsError):execute_adaptive_study(self.request,self.root/'run')

    def test_each_explicit_limit_stops_without_skipping_target(self):
        for key,value,reason in [('max_depth',0,'maximum_depth'),('max_attempts',2,'maximum_attempts'),('minimum_parameter_step',.02,'minimum_parameter_step')]:
            request=deepcopy(self.request);request['adaptive'][key]=value
            result=execute_adaptive_study(request,self.root/key)
            self.assertEqual(result['status'],'UNVERIFIED');self.assertEqual(result['stop_reason'],reason)
            self.assertEqual(result['unreached_target_indices'],[1])
            self.assertEqual(replay_adaptive_study(result),result)

    def test_decreasing_sweep_and_strict_preflight(self):
        request=deepcopy(self.request);request['study']['values'].reverse()
        result=execute_adaptive_study(request,self.root/'reverse')
        self.assertEqual(result['status'],'COMPLETE')
        values=[result['points'][i]['value'] for i in result['accepted_point_indices']]
        self.assertTrue(all(a>b for a,b in zip(values,values[1:])))
        for bad in [dict(self.request,unexpected=True),dict(self.request,adaptive=dict(self.request['adaptive'],max_depth=True))]:
            with self.assertRaises(ValueError):execute_adaptive_study(bad,self.root/'invalid')
            self.assertFalse((self.root/'invalid').exists())
        request['study']['values']=[.055,.08,.06];request['step_controls']*=2
        with self.assertRaisesRegex(ValueError,'monotone'):execute_adaptive_study(request,self.root/'invalid')

    def test_decision_and_rejected_source_tampering_are_detected(self):
        result=execute_adaptive_study(self.request,self.root/'run')
        changed=deepcopy(result);changed['attempts'][0]['decision']='ACCEPT'
        with self.assertRaisesRegex(ValueError,'replay'):replay_adaptive_study(changed)
        changed=deepcopy(result);changed['points'].reverse()
        with self.assertRaisesRegex(ValueError,'sequence'):replay_adaptive_study(changed)
        path=Path(result['points'][1]['run'])/'job.json';path.write_text(path.read_text()+' ')
        with self.assertRaises(ValueError):replay_adaptive_study(result)

    def test_point_source_changes_during_refinement_are_rejected(self):
        count=0
        def changing(project,run):
            nonlocal count
            state=execute_project(project,run);count+=1
            if count==3:
                path=self.root/'run/point-001/job.json';path.write_text(path.read_text()+' ')
            return state
        with patch('superfish_ng.adaptive_study.execute_project',side_effect=changing):
            with self.assertRaisesRegex(ValueError,'sources changed'):execute_adaptive_study(self.request,self.root/'run')
        self.assertFalse((self.root/'run/adaptive-study-results.json').exists())

    def test_cli_execution_and_replay(self):
        from superfish_ng.cli import main
        path=self.root/'request.json';path.write_text(json.dumps(self.request))
        self.assertEqual(main(['execute-adaptive-study',str(path),'--out',str(self.root/'cli')]),0)
        self.assertEqual(main(['replay-adaptive-study',str(self.root/'cli/adaptive-study-results.json')]),0)
