# SPDX-License-Identifier: Apache-2.0
"""Memory-bounded checker agrees with earlier full-sample analytical gates."""
from dataclasses import replace
from pathlib import Path
import sys
import unittest
import numpy as np
from superfish_ng.planar_curved import PlanarCurvedCase
from superfish_ng.planar_curved_solver import solve_planar_curved
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from validate_planar_curved_fem import circle_domain
from validate_planar_curved_rf import analytic_fields, check_solution
from planar_curved_circle_reference import CircularReference, check_circle_streaming


class PlanarCurvedCircleReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        domain = circle_domain(.01, 16)
        cls.solutions = [solve_planar_curved(PlanarCurvedCase(domain, polarization,
            modes=7 if polarization == 'te' else 6, max_geometry_boxes=100000000))
            for polarization in ('te', 'tm')]

    def test_complete_analytical_scalar_vectors_and_origin_match_existing_reference(self):
        points = np.array([[0., 0.], [.002, -.003], [.009, 0.], [-.003, .004]])
        for radius in (.01, .02):
            for polarization in ('te', 'tm'):
                reference = CircularReference(radius, polarization)
                a = reference.fields(points)
                b = analytic_fields(points, radius, polarization)
                for actual, expected in zip(a, b[:3]):
                    np.testing.assert_allclose(actual, expected, rtol=1e-14, atol=0)
                np.testing.assert_array_equal(reference.frequencies_hz, b[3])
                np.testing.assert_array_equal(reference.geometry_factors_ohm, b[4])
                normalized = CircularReference(radius, polarization, 2.5).fields(points)
                for value, original in zip(normalized, a):
                    np.testing.assert_allclose(value, np.sqrt(2.5)*original, rtol=1e-14, atol=0)

    def test_streamed_complete_group_gates_and_original_RF_match_full_sample(self):
        for solution in self.solutions:
            expected, actual = check_solution(solution, .01), check_circle_streaming(solution, .01)
            self.assertEqual(actual['target_groups_passed'], expected['target_groups_passed'])
            self.assertEqual(actual['RF'], expected['RF'])
            self.assertTrue(actual['full_analytic_guard_groups_present'])
            self.assertTrue(actual['independent_energy_passed'])
            for a, b in zip(actual['groups'], expected['groups']):
                self.assertEqual(a['gates'], b['gates'])
                for name in ('frequency_relative_error', 'electric_relative_L2_error',
                    'magnetic_relative_L2_error', 'geometry_factor_relative_error'):
                    self.assertAlmostEqual(a[name], b[name], places=12)

    def test_one_scalar_rotation_preserves_complete_degenerate_group_errors(self):
        solution = self.solutions[0]
        angle = .57
        rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        coefficients = solution.coefficients.copy()
        coefficients[:, :2] = coefficients[:, :2]@rotation
        altered = replace(solution, coefficients=coefficients)
        a, b = check_circle_streaming(solution, .01), check_circle_streaming(altered, .01)
        for key in ('electric_relative_L2_error', 'magnetic_relative_L2_error'):
            self.assertAlmostEqual(a['groups'][0][key], b['groups'][0][key], places=12)

    def test_incomplete_bands_invalid_orders_and_invalid_reference_are_rejected(self):
        solution = self.solutions[0]
        with self.assertRaisesRegex(ValueError, 'complete'):
            check_circle_streaming(replace(solution, case=replace(solution.case, modes=5)), .01)
        for order in (True, 3, 33):
            with self.assertRaises(ValueError):
                check_circle_streaming(solution, .01, quadrature_order=order)
        for args in ((True, 'te'), (-1., 'te'), (.01, 'hybrid')):
            with self.assertRaises(ValueError):
                CircularReference(*args)


if __name__ == '__main__':
    unittest.main()
