# SPDX-License-Identifier: Apache-2.0
"""Independent geometry and integrability gates for P07 synthetic inputs."""
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from planar_curved_shape_reference import ellipse_domain, ellipse_geometry, corner_domain, corner_harmonic_integrals
from validate_planar_curved_shapes import mode_groups, band_checks


class PlanarCurvedShapeReferenceTests(unittest.TestCase):
    def test_rotated_translated_ellipse_geometry_series_two_scales(self):
        for scale in (1., 2.):
            rows = [ellipse_geometry(ellipse_domain(n, scale=scale), n, scale=scale) for n in (16, 32, 64)]
            for key in ('true_area_relative_error', 'true_perimeter_relative_error', 'true_boundary_distance_upper_bound_over_major_axis'):
                self.assertTrue(all(a[key] > b[key] for a, b in zip(rows, rows[1:])))
                self.assertLessEqual(rows[-1][key], 1e-4)
            self.assertTrue(rows[-1]['geometry_gates_passed'])

    def test_graded_reentrant_geometry_keeps_full_area_and_wall(self):
        for length in (.01, .02):
            for grading in (1, 3):
                domain = corner_domain(length, grading=grading)
                self.assertLess(abs(domain.area_m2/(3*length**2)-1), 1e-12)
                self.assertLess(abs(domain.boundary_length_m()/(8*length)-1), 1e-12)
                self.assertEqual(len(domain.cell_nodes), 96)
                distances = np.linalg.norm(domain.points_xy_m, axis=1)
                self.assertLess(min(distances[distances > 0]), length/4)

    def test_corner_singularity_has_finite_integrals_and_diverging_point_gradient(self):
        for length in (.01, .02):
            full = corner_harmonic_integrals(length)
            self.assertIsNone(full['gradient_at_inner_radius'])
            self.assertLess(max(full['wall_relative_error'], full['gradient_relative_error']), 1e-11)
            rows = [corner_harmonic_integrals(length, inner_radius=length*h) for h in (1e-2, 1e-4, 1e-6)]
            self.assertTrue(all(a['gradient_at_inner_radius'] < b['gradient_at_inner_radius'] for a, b in zip(rows, rows[1:])))
            self.assertTrue(all(row['wall_squared_derivative_integral'] < full['wall_squared_derivative_integral'] for row in rows))

    def test_invalid_local_corner_controls_are_rejected(self):
        for args in ({'divisions': True}, {'divisions': 0}, {'grading': 0}):
            with self.assertRaises(ValueError):
                corner_domain(.01, **args)
        for radius in (-1., .01):
            with self.assertRaises(ValueError):
                corner_harmonic_integrals(.01, inner_radius=radius)

    def test_complete_neumann_pair_and_group_guards_fail_closed(self):
        from superfish_ng.constants import C0
        self.assertEqual(mode_groups('corner', 'te'), [1, 1, 2, 1, 1])
        frequencies = np.array([.39, .60, 1., 1., 1.08, 1.13])*C0/.02
        solution = SimpleNamespace(case=SimpleNamespace(polarization='te'), frequencies_hz=frequencies)
        self.assertTrue(band_checks(solution, 'corner', 1)['passed'])
        changed = frequencies.copy()
        changed[3] *= 1.001
        solution.frequencies_hz = changed
        self.assertFalse(band_checks(solution, 'corner', 1)['passed'])
        changed = frequencies.copy()
        changed[4] = changed[3]*(1+1e-4)
        solution.frequencies_hz = changed
        self.assertFalse(band_checks(solution, 'corner', 1)['complete_band_separated'])


if __name__ == '__main__':
    unittest.main()
