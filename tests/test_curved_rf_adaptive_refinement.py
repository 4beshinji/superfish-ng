# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from superfish_ng.adaptive_refinement import _request,execute_adaptive_refinement,replay_adaptive_refinement
from test_curved_adaptive_refinement import request
from test_curved_reflection import half_case


def rf_request():
    r=request();r['schema_version']=5
    r['case']=replace(half_case('z_min','electric_symmetry'),quadrature_order=12).to_dict()
    r['relative_tolerances']={k:1e-12 for k in r['relative_tolerances']}
    r['surface_relative_tolerances']={k:1e-12 for k in r['surface_relative_tolerances']}
    return r


class CurvedRFAdaptiveTests(unittest.TestCase):
    def test_strict_request_and_event_budget(self):
        r=rf_request();self.assertEqual(_request(r).geometry_order,2)
        for bad in (dict(r,selection='implicit'),dict(r,max_levels=2),dict(r,confirmation='none')):
            with self.assertRaises(ValueError):_request(bad)

    def test_probe_resume_branches_from_original_parent_and_replays(self):
        r=rf_request()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            first=execute_adaptive_refinement(r,root/'first',max_new_levels=2)
            self.assertEqual(first['status'],'PAUSED')
            self.assertEqual([x['refinement_kind'] for x in first['levels']],['initial','uniform_probe'])
            self.assertEqual(first['decision']['next_refinement_kind'],'rf_local')
            self.assertEqual(first['decision']['parent_event_index'],0)
            self.assertEqual(first['decision']['accepted_event_indices'],[0])
            with patch('superfish_ng.curved_rf_adaptive_refinement.solve',wraps=__import__('superfish_ng').solve) as calls:
                last=execute_adaptive_refinement(r,root/'resume',checkpoint=first,max_new_levels=1)
                self.assertEqual(calls.call_count,1)
            self.assertEqual(last['levels'][2]['parent_event_index'],0)
            self.assertEqual(last['decision']['accepted_event_indices'],[0,2])
            self.assertEqual(last['levels'][2]['uniform_confirmations'],0)
            from superfish_ng import Case
            local=Case.load(Path(last['level_runs'][2])/'case.json')
            self.assertEqual([s.kind for s in local.curved_refinement_steps],['marked'])
            with patch('superfish_ng.curved_solution.eigsh',side_effect=AssertionError('replay must not solve')):
                self.assertEqual(replay_adaptive_refinement(last),last)
            bad=deepcopy(last);bad['levels'][2]['parent_event_index']=1
            with self.assertRaises(ValueError):replay_adaptive_refinement(bad)
            bad=deepcopy(last);bad['levels'][1]['accepted']=True
            with self.assertRaises(ValueError):replay_adaptive_refinement(bad)

    def test_each_of_five_quantities_is_required(self):
        from superfish_ng.curved_rf_adaptive_refinement import _comparison
        r=rf_request();parent=dict(quantities=dict.fromkeys(r['relative_tolerances'],1.),
            surface=dict(intervals=dict.fromkeys(r['surface_relative_tolerances'],[1.,1.])))
        self.assertTrue(_comparison(parent,parent,r)['passed'])
        for key in r['relative_tolerances']:
            changed=deepcopy(parent);changed['quantities'][key]=1.5
            self.assertFalse(_comparison(parent,changed,r)['passed'])
        for key in r['surface_relative_tolerances']:
            changed=deepcopy(parent);changed['surface']['intervals'][key]=[.9,1.1]
            self.assertFalse(_comparison(parent,changed,r)['passed'])
            changed['surface']['intervals'][key]=None
            self.assertFalse(_comparison(parent,changed,r)['verified'])

    def test_two_real_uniform_confirmations_and_quadrature_gate(self):
        r=rf_request();standard=request()
        r['relative_tolerances']=standard['relative_tolerances']
        r['surface_relative_tolerances']=standard['surface_relative_tolerances']
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            first=execute_adaptive_refinement(r,root/'first',max_new_levels=2)
            self.assertEqual(first['status'],'PAUSED')
            self.assertEqual(first['levels'][-1]['uniform_confirmations'],1)
            last=execute_adaptive_refinement(r,root/'last',checkpoint=first,max_new_levels=1)
            self.assertEqual(last['status'],'TARGETS_MET')
            self.assertEqual(last['decision']['accepted_event_indices'],[0,1,2])
            self.assertEqual(last['levels'][-1]['uniform_confirmations'],2)
            self.assertEqual(last['decision']['completed_solve_events'],3)
            with patch('superfish_ng.curved_rf_adaptive_refinement._quadrature',return_value={'passed':False}):
                failed=execute_adaptive_refinement(r,root/'quadrature',max_new_levels=1)
            self.assertEqual(failed['status'],'QUADRATURE_UNVERIFIED')
            self.assertFalse(failed['can_resume'])
