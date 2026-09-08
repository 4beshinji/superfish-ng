# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_curved_rf_adaptive_refinement import rf_request
from test_curved_adaptive_refinement import request as standard_request
from superfish_ng import curved_rf_adaptive_refinement as engine
from superfish_ng.adaptive_refinement import replay_adaptive_refinement


class RFSurfacePolicyTests(unittest.TestCase):
    def test_strict_explicit_policy(self):
        r=rf_request();r['surface_refinement_policy']='uniform_when_rf_passes'
        engine.validate_request(r)
        for value in (None,True,[], 'automatic'):
            with self.assertRaises(ValueError):engine.validate_request(dict(r,surface_refinement_policy=value))
        engine.validate_request(dict(r,surface_refinement_policy='rf_goal'))

    def test_electric_and_magnetic_failure_progress_without_confirmation(self):
        for key in standard_request()['surface_relative_tolerances']:
            with self.subTest(key=key),tempfile.TemporaryDirectory() as temp:
                r=rf_request();r['surface_refinement_policy']='uniform_when_rf_passes'
                r['relative_tolerances']=standard_request()['relative_tolerances']
                r['surface_relative_tolerances']=standard_request()['surface_relative_tolerances']
                r['surface_relative_tolerances'][key]=1e-12
                root=Path(temp);first=engine.execute(r,root/'first',max_new_levels=2)
                probe=first['levels'][1]
                self.assertFalse(probe['confirmation_comparison']['passed'])
                self.assertTrue(all(v['passed'] for v in probe['confirmation_comparison']['changes'].values()))
                self.assertTrue(probe['accepted']);self.assertEqual(probe['uniform_confirmations'],0)
                self.assertEqual(first['status'],'PAUSED')
                self.assertEqual(first['decision']['next_refinement_kind'],'uniform_probe')
                self.assertEqual(first['decision']['parent_event_index'],1)
                final=engine.execute(r,root/'resumed',checkpoint=first,max_new_levels=1)
                self.assertEqual(final['levels'][2]['parent_event_index'],1)
                self.assertEqual(final['levels'][2]['triangles'],16*first['levels'][0]['triangles'])
                self.assertNotEqual(final['status'],'TARGETS_MET')
                with patch('superfish_ng.curved_solution.eigsh',side_effect=AssertionError('replay must not solve')):
                    self.assertEqual(replay_adaptive_refinement(final),final)

    def test_rf_failure_keeps_original_parent_branch(self):
        r=rf_request();r['surface_refinement_policy']='uniform_when_rf_passes'
        with tempfile.TemporaryDirectory() as temp:
            final=engine.execute(r,Path(temp)/'run',max_new_levels=3)
            self.assertFalse(final['levels'][1]['accepted'])
            self.assertEqual(final['levels'][2]['refinement_kind'],'rf_local')
            self.assertEqual(final['levels'][2]['parent_event_index'],0)
            self.assertEqual(replay_adaptive_refinement(final),final)

    def test_unknown_surface_and_quadrature_do_not_adopt(self):
        r=rf_request();r['surface_refinement_policy']='uniform_when_rf_passes'
        comparison=dict(verified=True,passed=False,changes={'rf':{'passed':True}})
        self.assertTrue(engine._surface_progress(comparison,r))
        for changed in (dict(comparison,verified=False),dict(comparison,changes={'rf':{'passed':False}})):
            self.assertFalse(engine._surface_progress(changed,r))
        self.assertFalse(engine._surface_progress(comparison,dict(r,surface_refinement_policy='rf_goal')))
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(engine,'_quadrature',return_value={'passed':False}):
                result=engine.execute(r,Path(temp)/'run',max_new_levels=1)
            self.assertEqual(result['status'],'QUADRATURE_UNVERIFIED')
            self.assertFalse(result['levels'][0]['accepted'])
