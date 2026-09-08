# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import math
from superfish_ng import Case
from superfish_ng.project import Project
from superfish_ng.constants import C0
from superfish_ng.jobs import execute_project
from superfish_ng.tuning import execute_tune,read_tune,replay_tune


def request():
    case=Case(((0.,.1),(.06,.1)),nr=6,nz=8,modes=3,element_order=2)
    return dict(schema_version=1,project=Project(case).to_dict(),parameter='/case/geometry/points_zr_m/1/0',
        bounds=[.06,.1],target_hz=C0/(2*math.pi)*math.hypot(2.404825557695773/.1,math.pi/.08),
        frequency_tolerance_hz=1e5,parameter_tolerance=1e-8,max_trials=16,initial_ids=['TM010','TM020','TM011'],mode_id='TM011',
        controls=dict(mapping='normalized_cylinder',sample_order=12,minimum_overlap=.97,minimum_assignment_margin=.05,
            relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8),refinement_scale=2,mesh_frequency_tolerance_hz=1e5)


class TuningTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name);self.request=request()

    def test_analytic_length_target_tracks_rank_crossing_and_refines(self):
        result=execute_tune(self.request,self.root/'run')
        self.assertEqual(result['status'],'TUNED')
        coarse=[r for r in result['trials'] if r['phase']=='search']
        self.assertAlmostEqual(coarse[-1]['value'],.08)
        self.assertEqual(coarse[0]['current_mode_ids'].index('TM011'),2)
        self.assertEqual(coarse[1]['current_mode_ids'].index('TM011'),1)
        self.assertEqual(result['trials'][-1]['phase'],'refinement')
        self.assertLessEqual(abs(result['trials'][-1]['target_error_hz']),1e5)
        self.assertLessEqual(result['decision']['mesh_frequency_difference_hz'],1e5)
        with patch('superfish_ng.jobs.solve',side_effect=AssertionError('must not solve during replay')):
            self.assertEqual(replay_tune(result),result)

    def test_pause_resume_preserves_prior_sources_and_only_solves_new_trials(self):
        first=execute_tune(self.request,self.root/'first',max_new_trials=2)
        self.assertEqual(first['status'],'PAUSED')
        old=read_tune(self.root/'first/checkpoint-002.json')
        with patch('superfish_ng.tuning.execute_project',wraps=execute_project) as solver:
            last=execute_tune(self.request,self.root/'next',checkpoint=old)
            self.assertEqual(solver.call_count,2)
        self.assertEqual(last['status'],'TUNED');self.assertEqual(read_tune(self.root/'first/checkpoint-002.json'),first)
        self.assertEqual(last['trial_sources_sha256'][:2],first['trial_sources_sha256'])

    def test_refinement_difference_is_not_hidden_by_target_tolerance(self):
        self.request['mesh_frequency_tolerance_hz']=1.
        result=execute_tune(self.request,self.root/'run')
        self.assertEqual(result['status'],'REFINEMENT_FAILED')
        self.assertLess(abs(result['trials'][-1]['target_error_hz']),self.request['frequency_tolerance_hz'])
        self.assertGreater(result['decision']['mesh_frequency_difference_hz'],1.)

    def test_unverified_and_subspace_stop_before_root_update(self):
        for name,change in [('overlap',dict(minimum_overlap=1.)),('subspace',dict(relative_cluster_gap=.2))]:
            req=deepcopy(self.request);req['controls'].update(change)
            result=execute_tune(req,self.root/name)
            self.assertEqual(result['status'],'UNVERIFIED');self.assertEqual(len(result['trials']),2)
            self.assertIsNone(result['trials'][-1]['frequency_hz']);self.assertFalse(result['can_resume'])

    def test_unbracketed_and_explicit_limits_are_not_success(self):
        for name,change,status in [('outside',dict(target_hz=1e10),'UNBRACKETED'),
                ('count',dict(max_trials=2),'ITERATION_LIMIT'),('width',dict(parameter_tolerance=.05),'PARAMETER_LIMIT')]:
            result=execute_tune(dict(self.request,**change),self.root/name)
            self.assertEqual(result['status'],status);self.assertEqual(len(result['trials']),2)

    def test_strict_request_and_checkpoint_tampering(self):
        for change in [dict(schema_version=True),dict(bounds=[.1,.06]),dict(refinement_scale=1),dict(max_trials=True),
                dict(parameter='/case/solver/modes'),dict(mode_id='missing'),dict(frequency_tolerance_hz=float('nan')),dict(extra=1)]:
            with self.assertRaises(ValueError):execute_tune(dict(self.request,**change),self.root/'bad')
            self.assertFalse((self.root/'bad').exists())
        first=execute_tune(self.request,self.root/'first',max_new_trials=1)
        changed=deepcopy(first);changed['trials'][0]['value']=.09
        with self.assertRaises(ValueError):replay_tune(changed)
        with self.assertRaisesRegex(ValueError,'request differs'):
            execute_tune(dict(self.request,target_hz=2e9),self.root/'bad',checkpoint=first)
        source=Path(first['trial_runs'][0])/'job.json';source.write_text(source.read_text()+' ')
        with self.assertRaises(ValueError):replay_tune(first)

    def test_failed_solve_keeps_checkpoint_and_failure_record(self):
        count=0
        def failing(project,directory):
            nonlocal count
            count+=1
            if count==2:raise RuntimeError('injected solve failure')
            return execute_project(project,directory)
        with patch('superfish_ng.tuning.execute_project',side_effect=failing):
            with self.assertRaisesRegex(RuntimeError,'injected'):execute_tune(self.request,self.root/'first')
        self.assertTrue((self.root/'first/failure-002.json').is_file())
        prior=read_tune(self.root/'first/checkpoint-001.json')
        self.assertEqual(execute_tune(self.request,self.root/'retry',checkpoint=prior)['status'],'TUNED')

    def test_bisection_updates_sign_bracket_with_multiple_trials(self):
        self.request['project']['case']['mesh'].update(nr=12,nz=16)
        self.request['target_hz']=C0/(2*math.pi)*math.hypot(2.404825557695773/.1,math.pi/.083)
        result=execute_tune(self.request,self.root/'run')
        self.assertEqual(result['status'],'TUNED')
        self.assertGreater(len(result['trials']),5)
        self.assertLess(abs(result['decision']['value']-.083),2e-5)
        self.assertLessEqual(abs(result['trials'][-1]['target_error_hz']),1e5)

    def test_prior_source_change_during_new_trial_cannot_be_blessed(self):
        first=execute_tune(self.request,self.root/'first',max_new_trials=1)
        def changing(project,directory):
            state=execute_project(project,directory)
            p=Path(first['trial_runs'][0])/'job.json';p.write_text(p.read_text()+' ')
            return state
        with patch('superfish_ng.tuning.execute_project',side_effect=changing):
            with self.assertRaisesRegex(ValueError,'prior checkpoint sources changed'):
                execute_tune(self.request,self.root/'next',checkpoint=first)
        self.assertFalse((self.root/'next/checkpoint-002.json').exists())

    def test_cli_pause_resume_replay_and_non_success_exit(self):
        import json
        from superfish_ng.cli import main
        p=self.root/'request.json';p.write_text(json.dumps(self.request))
        self.assertEqual(main(['tune',str(p),'--out',str(self.root/'cli'),'--max-new-trials','2']),0)
        checkpoint=self.root/'cli/checkpoint-002.json'
        self.assertEqual(main(['replay-tune',str(checkpoint)]),0)
        self.assertEqual(main(['resume-tune',str(checkpoint),'--out',str(self.root/'resume')]),0)
        self.assertEqual(read_tune(self.root/'resume/checkpoint-004.json')['status'],'TUNED')
        p.write_text(json.dumps(dict(self.request,max_trials=2)))
        self.assertEqual(main(['tune',str(p),'--out',str(self.root/'limited')]),1)

    def test_fine_target_must_pass_even_when_mesh_difference_passes(self):
        self.request['target_hz']=C0/(2*math.pi)*math.hypot(2.404825557695773/.1,math.pi/.083)
        result=execute_tune(self.request,self.root/'run')
        self.assertEqual(result['status'],'REFINEMENT_FAILED')
        self.assertTrue(result['decision']['mesh_difference_met'])
        self.assertFalse(result['decision']['refined_target_met'])
        self.assertLess(abs(result['trials'][-2]['target_error_hz']),1e5)
        self.assertGreater(abs(result['trials'][-1]['target_error_hz']),1e5)
