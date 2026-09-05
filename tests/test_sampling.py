# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from numpy.testing import assert_allclose
from superfish_ng import Case, make_mesh
from superfish_ng.constants import EPS0, TAU
from superfish_ng.sampling import FieldSampler, radial_extent


class SamplingTests(unittest.TestCase):
    def setUp(self):
        self.mesh = make_mesh(Case(((0., .07), (.03, .09), (.17, .04)), nr=7, nz=9))
        r, z = self.mesh.points.T
        # A known affine u checks both derivatives and coordinate ordering.
        self.u = np.column_stack((2+3*r-7*z, 4-2*r+5*z))
        self.sampler = FieldSampler(self.mesh.points, self.mesh.triangles, self.u, np.array([1e9, 2e9]))

    def test_affine_field_reconstruction_and_axis_limit(self):
        probes = np.array([[0., .05], [.02, .05], [.01, .12], [.04, .17]])
        for mode, a, b, c, frequency in [(0, 2, 3, -7, 1e9), (1, 4, -2, 5, 2e9)]:
            f = self.sampler.evaluate(probes, mode)
            r, z = probes.T
            value = a+b*r+c*z
            assert_allclose(f['Hphi_A_per_m'], r*value, atol=1e-14)
            assert_allclose(f['Er_quadrature_V_per_m'], -r*c/(TAU*frequency*EPS0), atol=1e-12)
            assert_allclose(f['Ez_quadrature_V_per_m'], (2*value+r*b)/(TAU*frequency*EPS0), rtol=1e-12)

    def test_outside_and_invalid_probes(self):
        for points in [[[.2, .05]], [[0, .2]], [[float('nan'), 0]], []]:
            with self.assertRaises(ValueError):
                self.sampler.evaluate(points)
        fields = self.sampler.evaluate([[.2, .05], [0, .05]], outside='nan')
        self.assertFalse(fields['inside'][0])
        self.assertTrue(np.isnan(fields['Ez_quadrature_V_per_m'][0]))
        self.assertTrue(np.isfinite(fields['Ez_quadrature_V_per_m'][1]))
        for mode in [-1, 2, True, .5]:
            with self.assertRaises(ValueError):
                self.sampler.evaluate([[0, .05]], mode)

    def test_radial_probe_preserves_boundary_profile(self):
        for z, expected in [(0, .07), (.03, .09), (.10, .065), (.17, .04)]:
            self.assertAlmostEqual(radial_extent(self.mesh.points, self.mesh.boundary_edges, z), expected)
