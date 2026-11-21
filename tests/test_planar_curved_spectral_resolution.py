# SPDX-License-Identifier: Apache-2.0
"""Independent dense finite spectra for fixed quadratic planar enrichment."""
from dataclasses import replace
import unittest
import numpy as np
from scipy.linalg import eigh
from superfish_ng.constants import C0, TAU
from superfish_ng.planar_curved import PlanarCurvedCase, PlanarCurvedDomain
from superfish_ng.planar_curved_solver import solve_planar_curved
from superfish_ng.planar_curved_fem import planar_curved_matrices
from test_planar_curved import curved_ellipse


class PlanarCurvedSpectralResolutionTests(unittest.TestCase):
    def test_intervals_contain_independent_enriched_spectrum_and_preserve_originals(self):
        from superfish_ng.planar_curved_spectral_resolution import planar_curved_spectral_resolution
        for polarization in ('te', 'tm'):
            case = PlanarCurvedCase(curved_ellipse(8), polarization, modes=3, quadrature_order=16)
            solution = solve_planar_curved(case)
            original = (solution.coefficients.tobytes(), solution.frequencies_hz.tobytes())
            report = planar_curved_spectral_resolution(solution)
            domain = PlanarCurvedDomain.from_dict(report['comparison_geometry'])
            _, k, m, free = planar_curved_matrices(replace(case, domain=domain, quadrature_order=report['quadrature_order']))
            k, m = k[free][:,free], m[free][:,free]
            values = eigh(k.toarray(), m.toarray(), eigvals_only=True)
            if polarization == 'te':
                self.assertLess(abs(values[0])/values[1], 1e-12)
                values = values[1:]
            frequencies = C0/TAU*np.sqrt(values)
            for a, b in report['nearby_enriched_frequency_intervals_hz']:
                self.assertTrue(np.any((frequencies >= a)&(True if b is None else frequencies <= b)))
            self.assertEqual(report['status'], 'PASS')
            self.assertEqual(original, (solution.coefficients.tobytes(), solution.frequencies_hz.tobytes()))
            self.assertNotIn('current_mode_ids', report)
            self.assertLess(max(report['relative_scalar_mass_difference']), 1e-12)

    def test_two_scale_covariance_and_rotation_of_all_intervals(self):
        from superfish_ng.planar_curved_spectral_resolution import planar_curved_spectral_resolution
        base = curved_ellipse(8)
        rotation = np.array([[0., -1.], [1., 0.]])
        for polarization in ('te', 'tm'):
            reports = []
            for scale in (1., 2.):
                domain = PlanarCurvedDomain(scale*base.points_xy_m@rotation.T, base.cell_nodes, base.boundary_nodes)
                solution = solve_planar_curved(PlanarCurvedCase(domain, polarization, modes=3, quadrature_order=16))
                reports.append(planar_curved_spectral_resolution(solution))
            a, b = reports
            np.testing.assert_allclose(b['original_frequencies_hz'], np.array(a['original_frequencies_hz'])/2, rtol=1e-11)
            np.testing.assert_allclose(b['nearby_enriched_frequency_intervals_hz'], np.array(a['nearby_enriched_frequency_intervals_hz'])/2, rtol=1e-10)
            np.testing.assert_allclose(b['relative_inverse_residual'], a['relative_inverse_residual'], rtol=1e-10)
            self.assertAlmostEqual(b['shift_per_m2']/a['shift_per_m2'], .25, places=12)

    def test_all_enrichment_budgets_preflight_without_partial_refinement(self):
        from unittest.mock import patch
        from superfish_ng.planar_curved_spectral_resolution import planar_curved_spectral_resolution
        from superfish_ng.planar_curved_comparison import PlanarCurvedComparisonBudgetExceeded
        solution = solve_planar_curved(PlanarCurvedCase(curved_ellipse(8), modes=3, quadrature_order=16))
        # 8 owners -> 32 cells, 81 native DOFs, 80 geometry pairs, 12800 area points.
        for options in ({'max_refined_triangles':31}, {'max_dofs':80}, {'max_pair_tests':79}, {'max_sample_points':12799}):
            with patch('superfish_ng.planar_curved_spectral_resolution.refine_planar_curved_domain', side_effect=AssertionError('partial refinement')):
                with self.subTest(options=options), self.assertRaises(PlanarCurvedComparisonBudgetExceeded) as caught:
                    planar_curved_spectral_resolution(solution, **options)
                self.assertEqual(caught.exception.status, 'UNVERIFIED')
        for options in ({'quadrature_order':True}, {'quadrature_order':33}, {'quadrature_order':3}, {'max_pair_tests':True}):
            with self.assertRaises(ValueError):planar_curved_spectral_resolution(solution, **options)
        with self.assertRaises(ValueError):planar_curved_spectral_resolution(replace(solution, coefficients=solution.coefficients*1.001))

    def test_same_domain_boundary_is_restriction_not_analytic_reprojection(self):
        from superfish_ng.planar_curved_spectral_resolution import planar_curved_spectral_resolution
        from superfish_ng.planar_curved_refinement import refine_planar_curved_domain
        base = curved_ellipse(8)
        expected = refine_planar_curved_domain(base)
        solution = solve_planar_curved(PlanarCurvedCase(base, modes=3, quadrature_order=16))
        report = planar_curved_spectral_resolution(solution)
        actual = PlanarCurvedDomain.from_dict(report['comparison_geometry'])
        np.testing.assert_array_equal(actual.points_xy_m, expected.domain.points_xy_m)
        np.testing.assert_array_equal(actual.cell_nodes, expected.domain.cell_nodes)
        np.testing.assert_array_equal(actual.boundary_nodes, expected.domain.boundary_nodes)
        self.assertEqual(report['geometry']['base_reference_areas'], [[1,2]]*8)
        self.assertLessEqual(report['maximum_original_map_relative_bound'], 512*np.finfo(float).eps)
        # The original quadratic ellipse approximant is not the true ellipse.
        # Each wall child quarter-point stays on that quadratic restriction.
        self.assertEqual(report['zero_mode'], 'TE constant retained in enriched operator')


if __name__ == '__main__':unittest.main()
