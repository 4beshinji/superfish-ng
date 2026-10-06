# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import sys
import unittest
import numpy as np
from superfish_ng.planar_curved import PlanarCurvedCase
from superfish_ng.planar_curved_solver import solve_planar_curved
from superfish_ng.planar_curved_refinement import refine_planar_curved_domain
from test_planar_curved import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from validate_planar_curved_fem import circle_domain
from validate_planar_curved_geometry_series import circle_geometry, fixed_domain_passed
from validate_planar_curved_convergence import compare_pair
from planar_curved_vector_reference import vectorized_validation_view


class PlanarCurvedGeometrySeriesReferenceTests(unittest.TestCase):
    def test_circle_geometry_series_keeps_actual_P2_area_and_true_errors_separate(self):
        for radius in (.01, .02):
            rows = [circle_geometry(circle_domain(radius, n), radius, n) for n in (16, 32, 64)]
            for name in ('true_area_relative_error', 'true_perimeter_relative_error', 'true_boundary_distance_upper_bound_over_major_axis'):
                self.assertTrue(all(a[name] > b[name] for a, b in zip(rows, rows[1:])))
                self.assertLessEqual(rows[-1][name], 1e-4)
            self.assertTrue(all(r['exact_P2_area_relative_error'] <= 1e-12 for r in rows))
        with self.assertRaisesRegex(ValueError, 'area'):
            circle_geometry(circle_domain(.01, 16), .02, 16)

    def test_guard_band_completeness_and_target_failure_are_independent(self):
        for shape, count in (('circle', 4), ('ellipse', 6)):
            for polarization in ('te', 'tm'):
                with self.assertRaisesRegex(ValueError, 'complete'):
                    fixed_domain_passed({'groups': []}, shape, polarization)
                groups = [{'passed': True} for _ in range(count)]
                self.assertTrue(fixed_domain_passed({'groups': groups}, shape, polarization))
                groups[-1]['passed'] = False
                self.assertTrue(fixed_domain_passed({'groups': groups}, shape, polarization))
                groups[0]['passed'] = False
                self.assertFalse(fixed_domain_passed({'groups': groups}, shape, polarization))

    def test_uniform_parent_comparison_adapter_preserves_original_fields_and_RF(self):
        original = patch(shift=(-.03, .01))
        coarse = solve_planar_curved(PlanarCurvedCase(original, modes=2, max_geometry_boxes=100000000))
        refinement = refine_planar_curved_domain(original, max_geometry_boxes=100000000)
        fine = solve_planar_curved(PlanarCurvedCase(refinement.domain, modes=2, max_geometry_boxes=100000000))
        plain = compare_pair(coarse, fine, [1, 1])
        adapted = compare_pair(vectorized_validation_view(coarse), vectorized_validation_view(fine), [1, 1])
        for a, b in zip(plain['groups'], adapted['groups']):
            self.assertEqual(a['gates'], b['gates'])
            self.assertEqual(a['RF_relative_differences'], b['RF_relative_differences'])
            for name in ('electric_relative_L2_difference', 'magnetic_relative_L2_difference'):
                self.assertAlmostEqual(a[name], b[name], places=13)
        self.assertEqual(plain['coarse_RF'], adapted['coarse_RF'])
        self.assertEqual(plain['fine_RF'], adapted['fine_RF'])


if __name__ == '__main__':
    unittest.main()
