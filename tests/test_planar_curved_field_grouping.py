# SPDX-License-Identifier: Apache-2.0
"""Owner grouping preserves original fields and avoids C complete point scans."""
from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng.constants import EPS0, MU0, TAU
from superfish_ng.planar_curved import PlanarCurvedCase
from superfish_ng.planar_curved_refinement import refine_planar_curved_domain
from superfish_ng.planar_curved_solver import PlanarCurvedSolution, _components
from test_planar_curved_solver import straight_case


def original_masks(solution, cells, refs, mode=None):
    """Previous implementation, with identical per-owner arithmetic/order."""
    count = 1 if mode is not None else solution.case.modes
    scalar = np.empty((len(cells), count))
    derivative = np.empty((len(cells), count, 2))
    points = np.empty_like(refs)
    for cell in np.unique(cells):
        selected = np.flatnonzero(cells == cell)
        mapped = solution.case.domain.elements[cell].evaluate(refs[selected])
        coefficient = solution.coefficients[solution.space.cell_nodes[cell]]
        if mode is not None:
            scalar[selected, 0] = mapped['basis_values'] @ coefficient[:, mode]
            derivative[selected, 0] = np.einsum('qia,i->qa', mapped['basis_gradients'], coefficient[:, mode])
        else:
            scalar[selected] = mapped['basis_values'] @ coefficient
            derivative[selected] = np.einsum('qia,im->qma', mapped['basis_gradients'], coefficient)
        points[selected] = mapped['points_xy_m']
    return scalar, derivative, points


class FieldGroupingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        domain = straight_case().domain
        for _ in range(3):
            domain = refine_planar_curved_domain(domain).domain
        x, y = domain.points_xy_m.T
        # Manufactured P2 scalar tests original API arithmetic and the first
        # signed Maxwell law; this is not an eigenpair/discretization validator.
        coefficients = np.column_stack((x + 2*y, x*x + x*y + 3*y*y, np.ones(len(x))))
        case = PlanarCurvedCase(domain, modes=3)
        cls.solution = PlanarCurvedSolution(case, SimpleNamespace(cell_nodes=domain.cell_nodes),
            None, None, np.arange(len(x)), np.arange(1, 4), np.arange(1, 4)*1e9,
            coefficients, np.zeros(3), 0.)
        cls.cells = np.repeat(np.arange(len(domain.cell_nodes)), 3)
        cls.refs = np.tile([[.2, .3], [.1, .6], [.4, .1]], (len(domain.cell_nodes), 1))

    def test_point_scan_work_is_linear_for_sorted_and_unordered_owners(self):
        permutation = np.random.default_rng(719).permutation(len(self.cells))
        for order in (np.arange(len(self.cells)), permutation):
            cells, refs = self.cells[order], self.refs[order]
            for call in (self.solution.scalar_at_reference, self.solution.all_fields_at_reference):
                with patch('numpy.flatnonzero', wraps=np.flatnonzero) as scans:
                    call(cells, refs)
                inspected = sum(np.asarray(row.args[0]).size for row in scans.call_args_list)
                self.assertLessEqual(inspected, 8*len(cells),
                    'owner grouping must not scan every point for every cell')

    def test_original_batch_arithmetic_and_output_order_are_bitwise_preserved(self):
        permutations = (np.arange(len(self.cells)),
            np.random.default_rng(201).permutation(len(self.cells)),
            np.arange(len(self.cells)-1, -1, -1))
        for polarization in ('te', 'tm'):
            solution = replace(self.solution, case=replace(self.solution.case, polarization=polarization))
            for order in permutations:
                cells, refs = self.cells[order], self.refs[order]
                scalar, derivative, _ = original_masks(solution, cells, refs)
                expected = _components(scalar, derivative, TAU*solution.frequencies_hz, polarization)
                actual = solution.all_fields_at_reference(cells, refs)
                for name in expected:
                    np.testing.assert_array_equal(actual[name], expected[name])
                    self.assertEqual(actual[name].dtype, expected[name].dtype)
                    self.assertEqual(actual[name].tobytes(), expected[name].tobytes(),
                        'bitwise output must also preserve the sign of zero')
                for mode in range(3):
                    scalar, derivative, points = original_masks(solution, cells, refs, mode)
                    mapped = solution.scalar_at_reference(cells, refs, mode)
                    for name, value in [('scalar', scalar[:, 0]), ('gradient_xy', derivative[:, 0]), ('points_xy_m', points)]:
                        np.testing.assert_array_equal(mapped[name], value)
                        self.assertEqual(mapped[name].dtype, value.dtype)
                        self.assertEqual(mapped[name].tobytes(), value.tobytes(),
                            'bitwise scalar/gradient/coordinates include signed zero')

    def test_unordered_manufactured_linear_scalar_obeys_signed_Maxwell_law(self):
        order = np.random.default_rng(902).permutation(len(self.cells))
        cells, refs = self.cells[order], self.refs[order]
        for polarization in ('te', 'tm'):
            solution = replace(self.solution, case=replace(self.solution.case, polarization=polarization))
            mapped = solution.scalar_at_reference(cells, refs)
            np.testing.assert_allclose(mapped['gradient_xy'], np.tile([1., 2.], (len(cells), 1)), rtol=0, atol=2e-13)
            np.testing.assert_allclose(mapped['scalar'], mapped['points_xy_m'] @ [1., 2.], rtol=0, atol=2e-17)
            fields = solution.fields_at_reference(cells, refs)
            omega = TAU*solution.frequencies_hz[0]
            if polarization == 'te':
                expected = {'Ex_quadrature_V_per_m': -2/(omega*EPS0), 'Ey_quadrature_V_per_m': 1/(omega*EPS0)}
            else:
                expected = {'Hx_quadrature_A_per_m': 2/(omega*MU0), 'Hy_quadrature_A_per_m': -1/(omega*MU0)}
            for name, value in expected.items():
                np.testing.assert_allclose(fields[name], value, rtol=2e-13, atol=0)


if __name__ == '__main__':
    unittest.main()
