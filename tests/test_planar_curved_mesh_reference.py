# SPDX-License-Identifier: Apache-2.0
"""Independent polynomial, area and vector invariants of the P07 validator."""
from dataclasses import replace
from fractions import Fraction
import json
from pathlib import Path
import sys
import unittest
import numpy as np
from superfish_ng.planar_curved import PlanarCurvedCase
from superfish_ng.planar_curved_solver import solve_planar_curved
from test_planar_curved import curved_ellipse, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from planar_curved_mesh_reference import restriction_chain, common_charts, compare_meshes
from validate_planar_curved_convergence import _rule
from validate_planar_curved_independent import independent_integrals


class PlanarCurvedMeshReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = curved_ellipse(8)
        cls.a = restriction_chain(cls.original, ('uniform',))
        cls.b = restriction_chain(cls.original, ('bisection', 'uniform'))
        cls.solutions = [solve_planar_curved(PlanarCurvedCase(c.domain, modes=2,
            max_geometry_boxes=100000000)) for c in (cls.a, cls.b)]

    def manufactured(self, polarization='te', rotation=None, amplitude=1., frequency=1.):
        solutions = []
        for index, solution in enumerate(self.solutions):
            xy = solution.case.domain.points_xy_m-np.array([-.03, .01])
            coefficients = xy if index == 0 else xy*amplitude
            if index == 1 and rotation is not None:
                coefficients = coefficients@rotation
            solutions.append(replace(solution, coefficients=coefficients,
                case=replace(solution.case, polarization=polarization),
                frequencies_hz=np.repeat(1e10, 2)*(frequency if index else 1.)))
        return solutions

    def test_exact_common_area_and_linear_moments_on_two_scales(self):
        refs, weights = _rule(8)
        for length in (.01, .02):
            original = patch(length)
            a = restriction_chain(original, ('uniform', 'uniform'))
            b = restriction_chain(original, ('bisection', 'uniform'))
            measure = np.zeros(3)
            reference_area = Fraction(0)
            for parent, _, _, triangle, determinant, _, _ in common_charts(a, b):
                reference_area += Fraction(determinant)
                points = triangle[0]+refs@(triangle[1:]-triangle[0])
                mapped = original.elements[parent].evaluate(points)
                w = weights*determinant*mapped['determinant_m2']
                measure += [sum(w), w@mapped['points_xy_m'][:, 0], w@mapped['points_xy_m'][:, 1]]
            self.assertEqual(reference_area, 1)
            expected = [length**2*(.5-.2/6), length**3*(1/6-.2/12), length**3*(1/6-.2**2/60)]
            np.testing.assert_allclose(measure, expected, rtol=1e-12, atol=0)
            self.assertLess(max(a.maximum_relative_coordinate_bound, b.maximum_relative_coordinate_bound), 512*np.finfo(float).eps)

    def test_independent_meshes_preserve_original_linear_fields_both_polarizations(self):
        for polarization in ('te', 'tm'):
            first, second = self.manufactured(polarization)
            result = compare_meshes(first, second, self.a, self.b, [2])
            self.assertEqual(json.loads(json.dumps(result)), result)
            row = result['groups'][0]
            self.assertTrue(row['passed'])
            self.assertLess(row['electric_relative_L2_difference'], 1e-12)
            self.assertLess(row['magnetic_relative_L2_difference'], 1e-12)
            self.assertLess(max(row['RF_relative_differences'].values()), 1e-11)

    def test_one_known_group_rotation_preserves_E_and_H(self):
        angle = .63
        rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        first, second = self.manufactured(rotation=rotation)
        row = compare_meshes(first, second, self.a, self.b, [2])['groups'][0]
        np.testing.assert_allclose(row['common_scalar_rotation'], rotation, rtol=0, atol=1e-13)
        self.assertLess(row['electric_relative_L2_difference'], 1e-12)
        self.assertLess(row['magnetic_relative_L2_difference'], 1e-12)

    def test_frequency_and_amplitude_differences_cannot_be_aligned_away(self):
        for polarization in ('te', 'tm'):
            first, second = self.manufactured(polarization, frequency=1.03)
            row = compare_meshes(first, second, self.a, self.b, [2])['groups'][0]
            derived = 'electric' if polarization == 'te' else 'magnetic'
            scalar = 'magnetic' if polarization == 'te' else 'electric'
            self.assertAlmostEqual(row[f'{derived}_relative_L2_difference'], .03, places=12)
            self.assertLess(row[f'{scalar}_relative_L2_difference'], 1e-12)
            first, second = self.manufactured(polarization, amplitude=1.03)
            row = compare_meshes(first, second, self.a, self.b, [2])['groups'][0]
            for field in ('electric', 'magnetic'):
                self.assertAlmostEqual(row[f'{field}_relative_L2_difference'], 1-1/1.03, places=12)
            self.assertFalse(row['passed'])

    def test_reverse_comparison_and_same_domain_quadrature_case(self):
        first, second = self.manufactured()
        direct = compare_meshes(first, second, self.a, self.b, [2])
        reverse = compare_meshes(second, first, self.b, self.a, [2])
        self.assertEqual(direct['common_reference_triangles'], reverse['common_reference_triangles'])
        changed_orders = replace(first, case=replace(first.case, quadrature_order=12, wall_quadrature_order=16))
        self.assertTrue(compare_meshes(first, changed_orders, self.a, self.a, [2])['groups'][0]['passed'])

    def test_independent_area_energy_and_normal_subtracted_wall(self):
        for polarization in ('te', 'tm'):
            first, _ = self.manufactured(polarization)
            integrals = independent_integrals(first)
            self.assertTrue(integrals['passed'])
            self.assertLess(max(integrals['differences'].values()), 1e-11)

    def test_geometry_groups_and_budget_fail_closed(self):
        first, second = self.manufactured()
        with self.assertRaisesRegex(ValueError, 'regenerated'):
            compare_meshes(first, second, self.b, self.a, [2])
        different = restriction_chain(curved_ellipse(8, axes=(.021, .012)))
        with self.assertRaisesRegex(ValueError, 'same complete'):
            list(common_charts(self.a, different))
        for groups in ([], [1], [0, 2], [True, 1]):
            with self.assertRaisesRegex(ValueError, 'partition'):
                compare_meshes(first, second, self.a, self.b, groups)
        for kwargs in ({'max_candidate_tests': 1}, {'max_overlay_triangles': 1}, {'max_candidate_tests': True}):
            with self.assertRaisesRegex(ValueError, 'budget|exceed|integers'):
                list(common_charts(self.a, self.b, **kwargs))


if __name__ == '__main__':
    unittest.main()
