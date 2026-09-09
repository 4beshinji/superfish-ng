# SPDX-License-Identifier: Apache-2.0
import copy
from dataclasses import replace
import unittest
import numpy as np
from superfish_ng.planar import PlanarCase, solve_planar
from superfish_ng.planar_tracking_fields import rectangle_electric_grams, electric_gram_features
from superfish_ng.planar_tracking_resolution import rectangle_spectral_resolution, resolution_frequency_groups
from superfish_ng.planar_mesh import PlanarMesh
from superfish_ng.planar_refinement import refine_planar_mesh
from superfish_ng.planar_polygon import PlanarPolygonCase
from superfish_ng.constants import EPS0


class PlanarTrackingFieldTests(unittest.TestCase):
    def test_electric_grams_exact_energy_transpose_and_polynomial_order(self):
        for pol in ('te', 'tm'):
            a = solve_planar(PlanarCase(.31, .2, pol, nx=4, ny=3, modes=3, element_order=1))
            b = solve_planar(PlanarCase(.22, .2, pol, nx=5, ny=4, modes=3, element_order=2))
            grams = rectangle_electric_grams(a, b)
            higher = rectangle_electric_grams(a, b, quadrature_order=5)
            reverse = rectangle_electric_grams(b, a)
            for x, y in zip(grams, higher):
                np.testing.assert_allclose(x, y, rtol=1e-11, atol=np.max(abs(x))*1e-12)
            np.testing.assert_allclose(grams[1], reverse[1].T, rtol=1e-11, atol=np.max(abs(grams[1]))*1e-12)
            for gram, solution in ((grams[0], a), (grams[2], b)):
                case = solution.case
                np.testing.assert_allclose(gram*EPS0*case.width_m*case.height_m/2,
                                           np.eye(3), rtol=1e-11, atol=1e-11)
            x, y = electric_gram_features(*grams)
            expected = grams[1]/np.sqrt(np.outer(np.diag(grams[0]), np.diag(grams[2])))
            np.testing.assert_allclose(x.T @ y, expected, rtol=1e-11, atol=1e-12)
            changed = copy.deepcopy(b)
            changed.coefficients *= -1
            flipped = rectangle_electric_grams(a, changed)
            np.testing.assert_array_equal(flipped[1], -grams[1])

    def test_enriched_intervals_contain_actual_enriched_eigenvalues(self):
        for pol in ('te', 'tm'):
            for order in (1, 2):
                case = PlanarCase(.2, .2, pol, nx=4, ny=4, modes=4, element_order=order)
                solution = solve_planar(case)
                resolution = rectangle_spectral_resolution(solution)
                mesh = PlanarMesh.create([[0., 0.], [.2, 0.], [.2, .2], [0., .2]],
                                         solution.space.points_xy_m, solution.space.triangles)
                fine = solve_planar(PlanarPolygonCase(refine_planar_mesh(mesh), pol, order, 12))
                for low, high in resolution['nearby_enriched_frequency_intervals_hz']:
                    self.assertTrue(np.any((fine.frequencies_hz >= low)*(fine.frequencies_hz <= high)))
                groups = resolution_frequency_groups(solution.frequencies_hz, resolution, .001)
                pair = [1, 2] if pol == 'te' else [2, 3]
                self.assertTrue(any(set(pair) <= set(group) for group in groups))
                scaled = solve_planar(replace(case, width_m=.4, height_m=.4, normalization_j_per_m=3.))
                other = rectangle_spectral_resolution(scaled)
                np.testing.assert_allclose(np.array(other['nearby_enriched_frequency_intervals_hz'])*2,
                                           resolution['nearby_enriched_frequency_intervals_hz'], rtol=1e-10)

    def test_mixed_physics_modified_mesh_and_bad_gram_rejected(self):
        a = solve_planar(PlanarCase(.31, .2, nx=3, ny=3, modes=2))
        b = solve_planar(replace(a.case, polarization='tm'))
        with self.assertRaisesRegex(ValueError, 'mix TE and TM'):
            rectangle_electric_grams(a, b)
        b = copy.deepcopy(a)
        b.space.points_xy_m *= 2
        with self.assertRaisesRegex(ValueError, 'mesh differs'):
            rectangle_electric_grams(a, b)
        with self.assertRaises(ValueError):
            rectangle_electric_grams(a, a, quadrature_order=True)
        with self.assertRaisesRegex(ValueError, 'positive semidefinite'):
            electric_gram_features(np.eye(2), 2*np.eye(2), np.eye(2))
