# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
import unittest
import numpy as np
from superfish_ng import Case, solve
from superfish_ng.constants import EPS0, TAU
from superfish_ng.curved_surface import CurvedSurfaceSampler, sampled_surface_summary
from superfish_ng.curved_extrema import edge_field_polynomials, bound_surface_peaks


def value(coefficients, t):
    return sum(c*Fraction(float(t))**i for i, c in enumerate(coefficients))


class CurvedExtremaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        case = replace(Case.load(Path(__file__).resolve().parents[1]/'examples/curved_ellipse.json'), geometry_order=2)
        cls.solution = solve(case)

    def test_exact_rational_trace_matches_physical_gradients(self):
        sampler = CurvedSurfaceSampler(self.solution)
        parameters = [0., .125, .3, .75, 1.]
        for edge in range(len(sampler.owners)):
            p = edge_field_polynomials(sampler, edge)
            actual = sampler.evaluate(edge, parameters)
            for key, numerator, denominator in (
                    ('Er_quadrature_V_per_m', p['electric'][0], p['denominator']),
                    ('Ez_quadrature_V_per_m', p['electric'][1], p['denominator']),
                    ('Hphi_A_per_m', p['magnetic'], [Fraction(1)])):
                expected = [float(value(numerator, t)/value(denominator, t)) for t in parameters]
                np.testing.assert_allclose(actual[key], expected, atol=1e-7, rtol=1e-11)

    def test_continuous_bounds_contain_dense_surface_samples(self):
        result = bound_surface_peaks(self.solution)
        samples = sampled_surface_summary(self.solution, samples_per_edge=65)
        for name, key in (('electric_v_per_m', 'E_abs_V_per_m'), ('magnetic_a_per_m', 'Hphi_A_per_m')):
            bounds = result[name]
            self.assertGreaterEqual(bounds['upper_bound']*(1+1e-12), samples[key]['value'])
            self.assertLessEqual(bounds['upper_bound']/bounds['lower_bound']-1, 1.000001e-6)
            self.assertEqual(self.solution.space.boundary_tags[bounds['boundary_index']], 'pec')

    def test_manufactured_constant_u_has_known_continuous_peaks(self):
        solution = replace(self.solution, u=np.ones_like(self.solution.u))
        result = bound_surface_peaks(solution)
        # H=r, |E|=2/(omega*epsilon); ellipse's maximum radius is .08 m.
        for key, exact in (('magnetic_a_per_m', .08),
                           ('electric_v_per_m', 2/(TAU*solution.frequencies_hz[0]*EPS0))):
            bounds = result[key]
            self.assertLessEqual(bounds['lower_bound'], exact*(1+1e-14))
            self.assertGreaterEqual(bounds['upper_bound'], exact*(1-1e-14))
        with self.assertRaises(ValueError):
            bound_surface_peaks(solution, mode=True)
