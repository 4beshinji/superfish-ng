# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from scipy.integrate import quad
from superfish_ng.quadratic_rf import quadratic_voltage, accelerating_voltage_p2
from superfish_ng import Case
from superfish_ng.high_order import solve_p2
from superfish_ng.sampling import FieldSampler


class QuadraticVoltageTests(unittest.TestCase):
    def test_oscillatory_polynomial_partial_interval_and_absolute_roots(self):
        z = np.array([0., .021, .079, .2])
        ends = np.column_stack((z[:-1], z[1:]))
        f = lambda x: (x-.037)*(x-.133)*1e5
        values = np.column_stack((f(z[:-1]), f(z[1:]), f((z[:-1]+z[1:])/2)))
        a, b, origin = .013, .187, -.17
        absolute = quad(lambda x: abs(f(x)), a, b, points=[.037, .133], epsabs=1e-11)[0]
        for k in [0., 1e-10, .01, 10., 3000., -3000.]:
            real = quad(f, a, b, weight='cos', wvar=k, epsabs=1e-10)[0]
            imag = quad(f, a, b, weight='sin', wvar=k, epsabs=1e-10)[0]
            expected = complex(real, imag)*np.exp(-1j*k*origin)
            actual, denom = quadratic_voltage(ends, values, k, interval=(a, b), phase_origin=origin)
            self.assertAlmostEqual(abs(actual-expected), 0, delta=2e-11)
            self.assertAlmostEqual(denom, absolute, delta=2e-11)
        reverse = quadratic_voltage(ends[::-1, ::-1], values[::-1][:, [1, 0, 2]], 10.)
        np.testing.assert_allclose(reverse, quadratic_voltage(ends, values, 10.), atol=1e-12)

    def test_constant_zero_and_invalid_edges(self):
        for value in [0., -2., 3.]:
            self.assertEqual(quadratic_voltage([[0, 1]], [[value]*3], 0), (complex(value), abs(value)))
        for edges in [[[0, 0]], [[0, .4], [.5, 1]], [[0, .6], [.5, 1]]]:
            with self.assertRaises(ValueError):
                quadratic_voltage(edges, np.ones((len(edges), 3)), 1.)
        with self.assertRaises(ValueError):
            quadratic_voltage([[0, 1]], [[1, 2, 3]], 1., interval=(-1, 1))

    def test_solved_field_low_beta_partial_voltage(self):
        from superfish_ng.constants import C0, TAU
        case = Case(((0., .1), (.2, .1)), nr=5, nz=9, modes=2, beta=.03,
                    voltage_interval_m=(.013, .187), phase_origin_m=.071)
        sol = solve_p2(case)
        sampler = FieldSampler.from_solution(sol)
        for mode in [0, 1]:
            k = TAU*sol.frequencies_hz[mode]/(case.beta*C0)
            f = lambda z: sampler.evaluate([[0., z]], mode)['Ez_quadrature_V_per_m'][0]
            breaks = np.unique(np.r_[.013, sol.mesh.points[sol.mesh.axis_nodes, 1], .187])
            breaks = breaks[(breaks >= .013) & (breaks <= .187)]
            real = sum(quad(f, a, b, weight='cos', wvar=k, epsabs=1e-7)[0] for a,b in zip(breaks[:-1], breaks[1:]))
            imag = sum(quad(f, a, b, weight='sin', wvar=k, epsabs=1e-7)[0] for a,b in zip(breaks[:-1], breaks[1:]))
            expected = complex(real, imag)*np.exp(-1j*k*.071)
            actual, _ = accelerating_voltage_p2(case, sol, mode)
            self.assertLess(abs(actual-expected)/max(abs(expected), 1), 1e-10)
