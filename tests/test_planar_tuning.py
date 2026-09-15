# SPDX-License-Identifier: Apache-2.0
"""Planar tuning: analytical cutoff, actual rank crossing and saved failures."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng.constants import C0
from superfish_ng.planar import PlanarCase, solve_planar
from superfish_ng.planar_project import PlanarProject
from superfish_ng.planar_tracking import PlanarTrackingControls
from superfish_ng.planar_tuning import (validate_planar_tune, trial_planar_project,
    execute_planar_tune, replay_planar_tune)


def request():
    return dict(format='superfish_ng_planar_tune',schema_version=1,
        project=PlanarProject(PlanarCase(.18,.2,nx=6,ny=6,modes=3)).to_dict(),
        parameter='/case/geometry/width_m',bounds=[.18,.22],target_hz=C0/(2*.22),
        frequency_tolerance_hz=2e5,parameter_tolerance=1e-8,max_trials=8,
        initial_ids=['y','x'],mode_id='x',controls=PlanarTrackingControls().to_dict(),
        refinement_levels=1,max_triangles=20000,mesh_frequency_tolerance_hz=2e5)


class PlanarTuningTests(unittest.TestCase):
    def test_rectangle_rank_crossing_analytic_cutoff_resume_and_mesh_gate(self):
        raw=request()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            first=execute_planar_tune(raw,root/'first',max_new_trials=2)
            self.assertEqual(first['status'],'PAUSED')
            self.assertEqual(first['trials'][1]['current_mode_ids'],['x','y'])
            self.assertEqual(first['decision']['next_trial']['phase'],'refinement')
            final=execute_planar_tune(raw,root/'rest',checkpoint=first)
            self.assertEqual(final['status'],'TUNED')
            self.assertEqual(replay_planar_tune(final),final)
            self.assertLess(abs(final['trials'][-1]['frequency_hz']/raw['target_hz']-1),1e-4)
            self.assertTrue(final['decision']['mesh_difference_met'])
            changed=deepcopy(final);changed['trials'][-1]['frequency_hz']*=1.01
            with self.assertRaises(ValueError):replay_planar_tune(changed)
            with self.assertRaises(ValueError):execute_planar_tune(raw,root/'terminal',checkpoint=final)
            self.assertFalse((root/'terminal').exists())
            # A stricter independently declared mesh gate reuses verified fields,
            # never substitutes a changed decision into a saved checkpoint.
            from superfish_ng.planar_tuning import _assemble
            strict=dict(raw,mesh_frequency_tolerance_hz=1.)
            result=_assemble(strict,final['trial_runs'])
            self.assertEqual(result['status'],'REFINEMENT_FAILED')
            self.assertTrue(result['decision']['refined_target_met'])
            self.assertFalse(result['decision']['mesh_difference_met'])

    def test_square_ambiguity_never_becomes_frequency_evaluation(self):
        raw=request();raw['bounds']=[.18,.2]
        with tempfile.TemporaryDirectory() as tmp:
            result=execute_planar_tune(raw,Path(tmp)/'ambiguous')
            self.assertEqual(result['status'],'UNVERIFIED')
            self.assertEqual(len(result['trials']),2)
            self.assertIsNone(result['trials'][-1]['frequency_hz'])
            self.assertIsNone(result['trials'][-1]['target_error_hz'])
            self.assertEqual(replay_planar_tune(result),result)

    def test_invalid_requests_and_preserved_checkpoint_on_failed_trial(self):
        raw=request()
        for key,value in [('schema_version',True),('initial_ids',['a','b','guard']),
                          ('bounds',[0.,1.]),('refinement_levels',0),('max_triangles',10),
                          ('parameter','/case/rf/stored_energy_j_per_m'),('extra',None)]:
            with self.subTest(key=key),self.assertRaises(ValueError):validate_planar_tune(dict(raw,**{key:value}))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);first=execute_planar_tune(raw,root/'first',max_new_trials=1)
            saved=(root/'first/checkpoint-001.json').read_bytes()
            with patch('superfish_ng.planar_tuning.execute_planar_project',side_effect=RuntimeError('injected solve failure')):
                with self.assertRaisesRegex(RuntimeError,'injected'):
                    execute_planar_tune(raw,root/'failed',checkpoint=first)
            failure=json.loads((root/'failed/failure-002.json').read_text())
            self.assertEqual(failure['status'],'FAILED');self.assertNotIn('frequency_hz',failure)
            self.assertEqual(saved,(root/'first/checkpoint-001.json').read_bytes())
            self.assertFalse(list((root/'failed').glob('checkpoint-*.json')))
            self.assertEqual(replay_planar_tune(first),first)

    def test_polygon_scale_preserves_area_measure_and_real_tm_tuning(self):
        from superfish_ng.planar_polygon import load_planar_case
        case=load_planar_case(Path(__file__).resolve().parents[1]/'examples/planar/triangle_tm.json')
        raw=request();raw.update(project=PlanarProject(case).to_dict(),parameter='uniform_scale',
            bounds=[1.,2.],initial_ids=['triangle'],mode_id='triangle',frequency_tolerance_hz=1e6,
            mesh_frequency_tolerance_hz=1e6)
        # Right-isosceles triangle Dirichlet fundamental (m,n)=(2,1).
        side=.2;raw['target_hz']=C0/2*np.sqrt(5)/side/2
        a=trial_planar_project(raw,1.,'search');b=trial_planar_project(raw,2.,'refinement')
        self.assertAlmostEqual(b.case.mesh.area_m2,4*a.case.mesh.area_m2,places=14)
        self.assertEqual(b.case.normalization_j_per_m,a.case.normalization_j_per_m)
        with tempfile.TemporaryDirectory() as tmp:
            result=execute_planar_tune(raw,Path(tmp)/'polygon')
            self.assertEqual(result['status'],'TUNED')
            self.assertLess(abs(result['trials'][-1]['frequency_hz']/raw['target_hz']-1),1e-4)
            self.assertEqual(result['trials'][-1]['tracking']['physical_mapping']['reference_measure'],'previous physical xy area in m^2')
            self.assertEqual(replay_planar_tune(result),result)


if __name__=='__main__':unittest.main()
