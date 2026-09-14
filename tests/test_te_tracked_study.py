# SPDX-License-Identifier: Apache-2.0
"""TE Study execution verifies native electric fields across saved restarts."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng.jobs import execute_project
from superfish_ng.te_saved import read_te_run
from superfish_ng.te import te_quantities
from superfish_ng.tracked_study import execute_tracked_study, replay_tracked_study
from superfish_ng.adaptive_study import execute_adaptive_study, replay_adaptive_study
from test_te_affine_study import te_affine_study
from test_curved_affine_study import controls


def te_tracking_request():
    return dict(schema_version=1,study=te_affine_study(),initial_ids=['TE-fundamental'],step_controls=[controls()])


class TETrackedStudyTests(unittest.TestCase):
    def test_real_pause_resume_native_scaling_and_tamper_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);request=te_tracking_request()
            first=execute_tracked_study(request,root/'first',max_new_points=1)
            self.assertEqual(first['status'],'PAUSED')
            with patch('superfish_ng.tracked_study.execute_project',wraps=execute_project) as solver:
                last=execute_tracked_study(request,root/'last',checkpoint=first)
                self.assertEqual(solver.call_count,1)
            self.assertEqual(last['status'],'COMPLETE')
            self.assertEqual(last['history']['current_mode_ids'],['TE-fundamental'])
            self.assertEqual(last['history']['steps'][0]['tracking']['physical_mapping']['field'],'Ephi_V_per_m')
            a,b=[read_te_run(Path(p)/'solution') for p in last['point_runs']]
            np.testing.assert_allclose(a.frequencies_hz,2*b.frequencies_hz,rtol=1e-10)
            np.testing.assert_allclose(a.coefficients_v_per_m2,2**2.5*b.coefficients_v_per_m2,rtol=1e-10,atol=1e-10)
            qa,qb=map(te_quantities,[a,b])
            self.assertLess(abs(qa['geometry_factor_ohm']/qb['geometry_factor_ohm']-1),1e-10)
            for q in [qa,qb]:
                self.assertIsNone(q['r_over_q_accelerator_ohm']);self.assertIsNone(q['r_over_q_circuit_ohm'])
            with patch('superfish_ng.tracked_study.execute_project',side_effect=AssertionError('replay must not solve')):
                self.assertEqual(replay_tracked_study(last),last)
            target=Path(last['point_runs'][0])/'solution/axis_001.csv'
            target.write_text(target.read_text()+'\n')
            with self.assertRaises(ValueError):replay_tracked_study(last)

    def test_adaptive_failed_pair_retains_te_sources_and_stops_at_limit(self):
        request=te_tracking_request()
        # Radial-only deformation changes the field shape under the map.
        request['study']['affine_coefficients']['axial_scale']=[.5]
        request['step_controls'][0]['minimum_overlap']=.999999
        request['adaptive']=dict(max_depth=0,max_attempts=2,minimum_parameter_step=1e-6)
        with tempfile.TemporaryDirectory() as tmp:
            result=execute_adaptive_study(request,Path(tmp)/'run')
            self.assertEqual(result['status'],'UNVERIFIED')
            self.assertEqual(result['stop_reason'],'maximum_depth')
            self.assertEqual(result['unreached_target_indices'],[1])
            self.assertEqual(replay_adaptive_study(result),result)
            for p in result['points']:
                self.assertIsNone(te_quantities(read_te_run(Path(p['run'])/'solution'))['r_over_q_accelerator_ohm'])
