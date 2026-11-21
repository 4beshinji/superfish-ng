# SPDX-License-Identifier: Apache-2.0
"""Independent cylinder fields/RF and uniform budget/failure invariants."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from scipy.special import j0, j1

from superfish_ng.adaptive_efficiency_plan import build_adaptive_efficiency_plan
from superfish_ng.adaptive_efficiency_timing import PhaseRecorder
from superfish_ng.adaptive_efficiency_uniform import execute_uniform_efficiency
from superfish_ng.analytic import pillbox_tm_mode
from superfish_ng.analytic_sphere import SphereTM
from superfish_ng.curved_same_domain_tracking import compare_quadratic_boundaries
from superfish_ng.constants import EPS0, TAU
from superfish_ng.fem import triangle_quadrature
from superfish_ng.high_order import basis_p2
from superfish_ng.mesh import element_geometry
from superfish_ng.saved import read_solution


class AdaptiveEfficiencyUniformTests(unittest.TestCase):
    def request(self):
        return build_adaptive_efficiency_plan()['cases'][0]['request']

    def field_errors(self, solution, reference, mode):
        vertices, determinant, gradient = element_geometry(solution.mesh)
        coefficients = solution.u[solution.space.cell_dofs, mode]
        values, fields, weights = [], [], []
        for n, w in triangle_quadrature(order=8):
            basis, derivatives = basis_p2(n, gradient)
            u = coefficients @ basis
            du = np.einsum('tij,ti->tj', derivatives, coefficients)
            r = vertices[:,:,0] @ n
            omega = TAU*solution.frequencies_hz[mode]
            native = np.column_stack((r*u, -r*du[:,1]/(omega*EPS0), (2*u+r*du[:,0])/(omega*EPS0)))
            exact = np.column_stack((reference['h0_a_per_m']*j1(reference['radial_wave_number_per_m']*r),
                                     np.zeros_like(r), reference['e0_v_per_m']*j0(reference['radial_wave_number_per_m']*r)))
            values.append(exact);fields.append(native);weights.append(w*determinant*2*np.pi*r)
        exact, native, weights = np.concatenate(values), np.concatenate(fields), np.concatenate(weights)
        sign = 1 if np.dot(weights, exact[:,0]*native[:,0]) >= 0 else -1
        native *= sign
        return {label: float(np.sqrt(np.sum(weights[:,None]*(native[:,selection]-exact[:,selection])**2)/
                                    np.sum(weights[:,None]*exact[:,selection]**2)))
                for label, selection in (('H', [0]), ('E', [1,2]))}

    def test_actual_three_uniform_solves_bessel_fields_wall_loss_rq_and_cost(self):
        request = self.request()
        reference = pillbox_tm_mode(.1, .2)
        recorder = PhaseRecorder()
        with tempfile.TemporaryDirectory() as tmp:
            result = execute_uniform_efficiency(request, Path(tmp)/'uniform', max_new_levels=3, recorder=recorder)
            self.assertEqual(len(result['levels']), 3)
            self.assertEqual(result['physical_acceptance_status'], 'NOT_RUN')
            self.assertIsNone(result['physical_error_bound'])
            self.assertEqual(result['request'], request)
            self.assertEqual([r['triangles'] for r in result['levels']], [40,160,640])
            self.assertTrue(all(r['current_mode_ids'] == request['initial_ids'] for r in result['levels']))
            self.assertTrue(all(r['tracking']['status'] == 'PASS' for r in result['levels'][1:]))
            errors = []
            fields = []
            for row, run in zip(result['levels'], result['level_runs']):
                q = row['quantities']
                errors.append(abs(q['frequency_hz']/reference['frequency_hz']-1))
                fields.append(self.field_errors(read_solution(run), reference, row['mode_index']))
                self.assertAlmostEqual(q['stored_energy_j'], 1., places=12)
                self.assertAlmostEqual(q['r_over_q_accelerator_ohm'], 2*q['r_over_q_circuit_ohm'], places=12)
            self.assertTrue(all(0 < b < a for a,b in zip(errors, errors[1:])))
            for field in ('E','H'):
                self.assertTrue(all(b[field] < a[field] for a,b in zip(fields,fields[1:])))
                self.assertLess(fields[-1][field], .005)
            q = result['levels'][-1]['quantities']
            self.assertLess(errors[-1], 1e-4)
            for key in ('wall_loss_w','r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm'):
                self.assertLess(abs(q[key]/reference[key]-1), .005)
            self.assertEqual(json.loads((Path(tmp)/'uniform/result.json').read_text()), result)
        cost = recorder.finish()
        self.assertEqual(cost['status'], 'COMPLETE')
        self.assertEqual(sum(p['name']=='native_solve_and_normalization' for p in cost['phases']), 3)
        self.assertFalse(any('selection' in p['name'] for p in cost['phases']))

    def test_uniform_element_limit_stops_before_next_solve_and_preserves_first(self):
        request = self.request();request['max_triangles'] = 150
        with tempfile.TemporaryDirectory() as tmp:
            from superfish_ng.solver import solve
            with patch('superfish_ng.adaptive_efficiency_uniform.solve', wraps=solve) as actual:
                result = execute_uniform_efficiency(request, Path(tmp)/'limited', max_new_levels=3)
            self.assertEqual(actual.call_count, 1)
            self.assertEqual(result['status'], 'REFINEMENT_LIMIT')
            self.assertEqual(len(result['level_runs']), 1)
            saved = read_solution(result['level_runs'][0])
            self.assertEqual(len(saved.mesh.triangles), 40)
            self.assertFalse((Path(tmp)/'limited/level-002').exists())
            self.assertEqual(result['physical_acceptance_status'], 'NOT_RUN')

    def test_unsupported_physics_fails_before_output_or_fem(self):
        request = self.request();request['case']['model']['polarization'] = 'te'
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'unsupported'
            with patch('superfish_ng.adaptive_efficiency_uniform.solve') as solve:
                with self.assertRaisesRegex(ValueError, 'closed vacuum.*TM'):
                    execute_uniform_efficiency(request, out)
                solve.assert_not_called()
            self.assertFalse(out.exists())

    def test_original_solver_failure_and_prior_artifacts_preserved(self):
        request = self.request();error = RuntimeError('original eigensolver failure')
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/'failed'
            with patch('superfish_ng.adaptive_efficiency_uniform.solve', side_effect=error):
                with self.assertRaises(RuntimeError) as caught:
                    execute_uniform_efficiency(request, out)
            self.assertIs(caught.exception, error)
            failure = json.loads((out/'failure-001.json').read_text())
            self.assertEqual(failure['error_type'], 'RuntimeError')
            self.assertEqual(failure['preceding_level_runs'], [])
            self.assertFalse((out/'result.json').exists())

    def test_actual_curved_uniform_sphere_original_domain_quadrature_and_rf(self):
        request = build_adaptive_efficiency_plan()['cases'][1]['request']
        reference = SphereTM(.08).quantities()
        with tempfile.TemporaryDirectory() as tmp:
            result = execute_uniform_efficiency(request, Path(tmp)/'sphere', max_new_levels=3)
            self.assertEqual(len(result['levels']), 3)
            solutions = [read_solution(p) for p in result['level_runs']]
            self.assertEqual([s.case.curved_refinement_levels for s in solutions], [0,1,2])
            self.assertTrue(all(s.source_mesh_data == solutions[0].source_mesh_data for s in solutions))
            for a,b in zip(solutions, solutions[1:]):
                certificate = compare_quadratic_boundaries(a,b)
                self.assertGreater(certificate['common_interval_count'], 0)
                self.assertLessEqual(certificate['maximum_coefficient_distance_m'], certificate['roundoff_tolerance_m'])
                self.assertLessEqual(b.frequencies_hz[0], a.frequencies_hz[0]*(1+2e-12))
            self.assertTrue(all(row['quadrature_check']['passed'] for row in result['levels']))
            self.assertTrue(all(row['current_mode_ids'] == ['fundamental'] for row in result['levels']))
            q = result['levels'][-1]['quantities']
            for key,limit in (('frequency_hz',1e-4),('r_over_q_accelerator_ohm',.005),
                              ('r_over_q_circuit_ohm',.005),('geometry_factor_ohm',.005),('wall_loss_w',.005)):
                self.assertLess(abs(q[key]/reference[key]-1), limit)
            self.assertIsNone(result['physical_error_bound'])
            self.assertEqual(result['physical_acceptance_status'], 'NOT_RUN')


if __name__ == '__main__':
    unittest.main()
