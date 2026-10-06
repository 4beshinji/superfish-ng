# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from pathlib import Path
import sys
import unittest
import numpy as np
from superfish_ng.planar_curved import PlanarCurvedCase
from superfish_ng.planar_curved_solver import solve_planar_curved
from test_planar_curved import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from planar_curved_vector_reference import original_vectors, vectorized_validation_view
from validate_planar_curved_convergence import _vectors


class PlanarCurvedVectorReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.solution = solve_planar_curved(PlanarCurvedCase(patch(shift=(-.03, .01)), modes=2))

    def test_full_original_12_components_match_public_API_both_polarizations(self):
        random = np.random.default_rng(901).dirichlet([1., 1., 1.], size=300)[:, 1:]
        refs = np.vstack((random, [[0., 0.], [1., 0.], [0., 1.], [.5, 0.], [.5, .5], [0., .5]]))
        for polarization in ('te', 'tm'):
            solution = replace(self.solution, case=replace(self.solution.case, polarization=polarization))
            for actual, expected in zip(original_vectors(solution, 0, refs), _vectors(solution, 0, refs)):
                np.testing.assert_allclose(actual, expected, rtol=1e-13, atol=np.max(abs(expected))*1e-13)

    def test_physical_linear_scalar_gives_known_signed_Maxwell_fields(self):
        base = self.solution
        solution = replace(base, coefficients=np.column_stack((base.case.domain.points_xy_m[:, 0],
            base.case.domain.points_xy_m[:, 1])), frequencies_hz=np.array([1e9, 2e9]))
        from superfish_ng.constants import EPS0, TAU
        electric, magnetic = original_vectors(solution, 0, [[.2, .3]])
        np.testing.assert_allclose(electric[0, :2], [[0., -1j/(TAU*2e9*EPS0)], [1j/(TAU*1e9*EPS0), 0.]], rtol=1e-13, atol=1e-13)
        expected = solution.case.domain.elements[0].evaluate([[.2, .3]])['points_xy_m'][0]
        np.testing.assert_allclose(magnetic[0, 2], expected, rtol=1e-13, atol=1e-16)

    def test_strict_cells_and_outside_reference_points_are_rejected(self):
        for cell, refs in ((True, [[.2, .3]]), (-1, [[.2, .3]]), (1, [[.2, .3]]),
            (0, [[-.01, .2]]), (0, [[.6, .6]]), (0, [[True, .2]])):
            with self.assertRaises(ValueError):
                original_vectors(self.solution, cell, refs)

    def test_adapter_keeps_original_arrays_and_full_RF_and_API(self):
        from superfish_ng.planar_curved_solver import planar_curved_quantities
        view = vectorized_validation_view(self.solution)
        for name in ('case', 'coefficients', 'frequencies_hz', 'mass', 'stiffness', 'free_dofs'):
            self.assertIs(getattr(view, name), getattr(self.solution, name))
        refs = [[.1, .2], [.3, .4]]
        a = self.solution.all_fields_at_reference([0, 0], refs)
        b = view.all_fields_at_reference([0, 0], refs)
        self.assertEqual(set(a), set(b))
        for name in a:
            np.testing.assert_allclose(a[name], b[name], rtol=1e-13, atol=np.max(abs(a[name]))*1e-13)
        self.assertEqual(planar_curved_quantities(view), planar_curved_quantities(self.solution))

    def test_adapter_preserves_whole_partition_comparison_and_independent_RF_integrals(self):
        from planar_curved_mesh_reference import restriction_chain, compare_meshes
        from validate_planar_curved_independent import independent_integrals
        original = self.solution.case.domain
        a = restriction_chain(original, ('uniform',))
        b = restriction_chain(original, ('bisection', 'uniform'))
        solutions = [solve_planar_curved(PlanarCurvedCase(c.domain, modes=2,
            max_geometry_boxes=100000000)) for c in (a, b)]
        direct = compare_meshes(*solutions, a, b, [1, 1])
        adapted = compare_meshes(*map(vectorized_validation_view, solutions), a, b, [1, 1])
        for plain, fast in zip(direct['groups'], adapted['groups']):
            self.assertEqual(plain['gates'], fast['gates'])
            self.assertEqual(plain['RF_relative_differences'], fast['RF_relative_differences'])
            for name in ('electric_relative_L2_difference', 'magnetic_relative_L2_difference'):
                self.assertAlmostEqual(plain[name], fast[name], places=13)
        self.assertEqual(direct['first_RF'], adapted['first_RF'])
        self.assertEqual(direct['second_RF'], adapted['second_RF'])
        plain, fast = independent_integrals(solutions[0]), independent_integrals(vectorized_validation_view(solutions[0]))
        self.assertEqual(plain['passed'], fast['passed'])
        for name in plain['differences']:
            self.assertAlmostEqual(plain['differences'][name], fast['differences'][name], places=13)


if __name__ == '__main__':
    unittest.main()
