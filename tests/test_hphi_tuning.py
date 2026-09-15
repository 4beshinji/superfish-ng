# SPDX-License-Identifier: Apache-2.0
import copy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from superfish_ng.axis_hphi import AxisHphiCase
from superfish_ng.coaxial import CoaxialCase
from superfish_ng.hphi_mesh import HphiMeshCase
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_tracking import HphiTrackingControls
from superfish_ng.hphi_tuning import validate_hphi_tune, read_hphi_tune_request, trial_hphi_project
from superfish_ng.hphi_tuning import run_hphi_tune, assess_hphi_tune
from superfish_ng.constants import C0
from test_hphi_mass_projection import declared


def request(case=None):
    return dict(format='superfish_ng_hphi_tune', schema_version=1,
        project=HphiProject(case or CoaxialCase(.025, .05, .18, nr=3, nz=8, modes=3)).to_dict(),
        parameter='uniform_scale', mapping=dict(kind='uniform_scale'), bounds=[1., 2.],
        target_hz=416378413.8888889, frequency_tolerance_hz=1e6, parameter_tolerance=1e-6,
        max_trials=20, initial_ids=['fundamental'], mode_id='fundamental',
        controls=HphiTrackingControls().to_dict(), refinement_levels=1,
        max_triangles=10000, max_dofs=10000, mesh_frequency_tolerance_hz=1e6)


class HphiTuneRequestTests(unittest.TestCase):
    def test_strict_reader_and_rejections(self):
        q = request()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'request.json'
            path.write_text(json.dumps(q))
            self.assertEqual(read_hphi_tune_request(path), q)
            path.write_text(json.dumps(q)[:-1]+', "max_trials": 20}')
            with self.assertRaises(ValueError):
                read_hphi_tune_request(path)
        changes = [('extra', 1), ('schema_version', True), ('bounds', [2., 1.]),
            ('bounds', [True, 2.]), ('bounds', [1., float('nan')]), ('parameter_tolerance', 2.),
            ('parameter', 'stored_energy_j'), ('parameter', '/case/rf/conductivity_s_per_m'),
            ('mapping', {'kind': 'same_vacuum'}), ('mapping', {'kind': 'uniform_scale', 'extra': 1}),
            ('initial_ids', ['a', 'a']), ('initial_ids', ['a', 'b', 'c']), ('mode_id', 'missing'),
            ('refinement_levels', 9), ('target_hz', np.float64(4e8))]
        changes += [(name, True) for name in ('target_hz', 'frequency_tolerance_hz', 'parameter_tolerance',
            'max_trials', 'refinement_levels', 'max_triangles', 'max_dofs', 'mesh_frequency_tolerance_hz')]
        for name, value in changes:
            with self.subTest(name=name, value=value):
                bad = copy.deepcopy(q); bad[name] = value
                with self.assertRaises(ValueError): validate_hphi_tune(bad)
        for name in q['controls']:
            bad = copy.deepcopy(q); bad['controls'][name] = True
            with self.assertRaises(ValueError): validate_hphi_tune(bad)
        bad = copy.deepcopy(q); bad['project']['case']['format'] = 'superfish_ng_material_hphi_case'
        with self.assertRaises(ValueError): validate_hphi_tune(bad)

    def test_budget_checks_before_refinement_allocation(self):
        from unittest.mock import patch
        for name, value in [('max_triangles', 191), ('max_dofs', 230)]:
            q = request(); q[name] = value
            with patch('superfish_ng.hphi_tuning._trial', side_effect=AssertionError('allocated')):
                with self.assertRaisesRegex(ValueError, 'exceeds'): validate_hphi_tune(q)
        q = request(); q['controls']['max_dofs'] = 100
        with self.assertRaisesRegex(ValueError, 'max_dofs'): validate_hphi_tune(q)
        q = request(); q['controls']['max_gram_modes'] = 2
        with self.assertRaisesRegex(ValueError, 'max_gram_modes'): validate_hphi_tune(q)

    def test_original_project_determinism_and_independent_geometric_invariants(self):
        cases = [CoaxialCase(.025, .05, .18, nr=3, nz=8, modes=3)]
        cases += [kind(declared(1, 1, axis), modes=3)
                  for axis, kind in [(False, HphiMeshCase), (True, AxisHphiCase)]]
        for case in cases:
            q = request(case); before = copy.deepcopy(q)
            coarse = trial_hphi_project(q, 2., 'search')
            fine = trial_hphi_project(q, 2., 'refinement')
            trial_hphi_project(q, 1.5, 'search')
            self.assertEqual(trial_hphi_project(q, 2., 'refinement'), fine)
            self.assertEqual(q, before)
            if type(case) is CoaxialCase:
                self.assertEqual((fine.case.nr, fine.case.nz), (6, 16))
                self.assertAlmostEqual(fine.case.volume_m3/case.volume_m3, 8.)
            else:
                a, b = coarse.case.mesh, fine.case.mesh
                self.assertEqual(len(b.triangles), 4*len(a.triangles))
                self.assertAlmostEqual(b.area_m2/case.mesh.area_m2, 4.)
                self.assertAlmostEqual(b.volume_m3/case.mesh.volume_m3, 8.)
                np.testing.assert_array_equal(b.outer_rz_m, a.outer_rz_m)
                for x, y in zip(a.holes_rz_m, b.holes_rz_m): np.testing.assert_array_equal(x, y)
                for mesh in (a, b):
                    vertices = mesh.points_rz_m[mesh.triangles]
                    det = np.linalg.det(vertices[:, 1:]-vertices[:, :1])
                    self.assertTrue(np.all(det > 0))
                    volume = np.sum(det/2 * 2*np.pi*vertices[:, :, 0].mean(axis=1))
                    self.assertAlmostEqual(volume, mesh.volume_m3)
                if type(case) is AxisHphiCase:
                    self.assertEqual(len(b.axis_edges), 2*len(a.axis_edges))


class HphiTuneExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.q = request()
        cls.q['target_hz'] = C0/(2*.18*1.5)
        cls.execution = run_hphi_tune(cls.q)

    def test_real_bisection_analytic_tem_and_original_field_scaling(self):
        run = self.execution
        self.assertEqual(run.report['status'], 'TUNED', run.report)
        self.assertEqual([t['value'] for t in run.report['trials']], [1., 2., 1.5, 1.5])
        self.assertEqual([t['parent_index'] for t in run.report['trials']], [None, 0, 0, 2])
        self.assertEqual(run.report['trials'][-1]['parent_index'], 2)
        self.assertTrue(run.report['decision']['refined_target_met'])
        self.assertTrue(run.report['decision']['mesh_difference_met'])
        for p, s in zip(run.projects, run.solutions):
            self.assertLess(abs(s.frequencies_hz[0]/(C0/(2*p.case.length_m))-1), 2e-5)
        a, b = run.solutions[:2]
        np.testing.assert_allclose(b.frequencies_hz, a.frequencies_hz/2, rtol=1e-10)
        tracking = run.report['trials'][1]['tracking']
        for family in ('electric_grams', 'magnetic_grams'):
            aa, ab, bb = map(np.asarray, tracking['physical_mapping'][family])
            overlap = ab/np.sqrt(np.diag(aa)[:, None]*np.diag(bb)[None, :])
            np.testing.assert_allclose(abs(overlap), np.eye(3), atol=1e-9)
        self.assertEqual(tracking['physical_mapping']['previous_frequency_scale'], .5)
        self.assertEqual(tracking['request']['mapping'], dict(kind='uniform_scale', previous_scale=2.))

    def test_both_frequency_gates_and_no_trials_after_terminal(self):
        q = copy.deepcopy(self.q); q['mesh_frequency_tolerance_hz'] = 1e-5
        replay = assess_hphi_tune(q, self.execution.solutions)
        self.assertEqual(replay.report['status'], 'REFINEMENT_FAILED')
        self.assertTrue(replay.report['decision']['refined_target_met'])
        self.assertFalse(replay.report['decision']['mesh_difference_met'])
        q = copy.deepcopy(self.q)
        q['target_hz'] = float(self.execution.solutions[2].frequencies_hz[0])
        q['frequency_tolerance_hz'] = 1e-3
        replay = assess_hphi_tune(q, self.execution.solutions)
        self.assertEqual(replay.report['status'], 'REFINEMENT_FAILED')
        self.assertFalse(replay.report['decision']['refined_target_met'])
        self.assertTrue(replay.report['decision']['mesh_difference_met'])
        with self.assertRaisesRegex(ValueError, 'terminal'):
            assess_hphi_tune(self.q, self.execution.solutions+(self.execution.solutions[-1],))

    def test_guard_unverified_and_budget_refusal_do_not_evaluate_frequency(self):
        q = copy.deepcopy(self.q); q['controls']['relative_cluster_gap'] = .9
        result = assess_hphi_tune(q, self.execution.solutions[:1]).report
        self.assertEqual(result['status'], 'UNVERIFIED')
        self.assertIsNone(result['trials'][0]['frequency_hz'])
        self.assertIsNone(result['trials'][0]['target_error_hz'])
        with self.assertRaisesRegex(ValueError, 'terminal'):
            assess_hphi_tune(q, self.execution.solutions[:2])
        q = copy.deepcopy(self.q); q['controls']['max_candidate_tests'] = 1
        result = assess_hphi_tune(q, self.execution.solutions[:1]).report
        self.assertEqual(result['status'], 'UNVERIFIED')
        self.assertIsNone(result['trials'][0]['frequency_hz'])

    def test_pause_unbracketed_and_iteration_parameter_limits(self):
        q = copy.deepcopy(self.q); q['target_hz'] *= 3
        result = assess_hphi_tune(q, self.execution.solutions[:2]).report
        self.assertEqual(result['status'], 'UNBRACKETED')
        q = copy.deepcopy(self.q); q['max_trials'] = 2
        self.assertEqual(assess_hphi_tune(q, self.execution.solutions[:2]).report['status'], 'ITERATION_LIMIT')
        q = copy.deepcopy(self.q); q['parameter_tolerance'] = 1.
        self.assertEqual(assess_hphi_tune(q, self.execution.solutions[:2]).report['status'], 'PARAMETER_LIMIT')
        paused = run_hphi_tune(self.q, max_new_trials=1)
        self.assertEqual(paused.report['status'], 'PAUSED')
        self.assertEqual(len(paused.solutions), 1)
        self.assertTrue(paused.report['can_resume'])


if __name__ == '__main__':
    unittest.main()
