# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from superfish_ng import Case,solve
from superfish_ng.adaptive_refinement import execute_adaptive_refinement,replay_adaptive_refinement,_next
from test_adaptive_refinement import request


def confirmed_request():
    req=request();req.update(schema_version=2,confirmation='uniform_two_steps',max_levels=5)
    req['controls']['mapping']='nested_affine';del req['controls']['sample_order']
    return req


class UniformRFConfirmationTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)

    def test_local_candidate_requires_two_real_uniform_solves(self):
        req=confirmed_request();result=execute_adaptive_refinement(req,self.root/'run')
        self.assertEqual(result['status'],'TARGETS_MET');self.assertEqual(len(result['levels']),5)
        self.assertEqual([r['refinement_kind'] for r in result['levels']],['initial','residual','residual','uniform_confirmation','uniform_confirmation'])
        for a,b in zip(result['levels'][2:],result['levels'][3:]):
            self.assertEqual(b['triangles'],4*a['triangles']);self.assertEqual(b['marked_cells'],list(range(a['triangles'])))
        self.assertEqual(replay_adaptive_refinement(result),result)
        self.assertIsNone(result['physical_error_bound']);self.assertEqual(result['surface_status'],'UNASSESSED')

    def test_pause_resume_confirmation_and_tamper_rejection(self):
        req=confirmed_request();first=execute_adaptive_refinement(req,self.root/'first',max_new_levels=4)
        self.assertEqual(first['status'],'PAUSED')
        self.assertEqual(first['decision']['next_refinement_kind'],'uniform_confirmation')
        with patch('superfish_ng.adaptive_refinement.solve',wraps=solve) as calls:
            last=execute_adaptive_refinement(req,self.root/'resumed',checkpoint=first)
            self.assertEqual(calls.call_count,1)
        self.assertEqual(last['status'],'TARGETS_MET')
        from superfish_ng.cli import main
        self.assertEqual(main(['replay-adaptive-refinement',str(self.root/'resumed/checkpoint-005.json')]),0)
        bad=deepcopy(first);bad['levels'][-1]['refinement_kind']='residual'
        with self.assertRaises(ValueError):replay_adaptive_refinement(bad)
        for change in (dict(confirmation='none'),dict(max_levels=4),dict(controls=dict(req['controls'],sample_order=3))):
            with self.assertRaises(ValueError):execute_adaptive_refinement(dict(req,**change),self.root/'bad')
            self.assertFalse((self.root/'bad').exists())

    def test_confirmation_failure_does_not_accept_local_success(self):
        req=confirmed_request();req['relative_tolerances']=dict.fromkeys(req['relative_tolerances'],.005)
        levels=[dict(status='PASS',refinement_kind=kind,quantities=dict(frequency_hz=1.,geometry_factor_ohm=1.,r_over_q_accelerator_ohm=rq))
            for kind,rq in zip(['initial','residual','residual','uniform_confirmation','uniform_confirmation'],[1.,1.,1.,1.02,1.02])]
        decision,_=_next(Case.from_dict(req['case']),req,levels,None)
        self.assertEqual(decision['status'],'LEVEL_LIMIT')
        self.assertFalse(decision['changes'][0]['r_over_q_accelerator_ohm']['passed'])
