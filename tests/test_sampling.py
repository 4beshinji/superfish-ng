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


class QuadraticSamplingTests(unittest.TestCase):
    def test_quadratic_polynomial_fields_axis_and_outside(self):
        from superfish_ng.high_order import quadratic_space
        mesh = make_mesh(Case(((0., .1), (.2, .1)), nr=4, nz=5))
        space = quadratic_space(mesh)
        r, z = space.dof_points.T
        u = (2+3*r-7*z+5*r*r+11*r*z-13*z*z)[:, None]
        sampler = FieldSampler(mesh.points, mesh.triangles, u, [1e9], space=space)
        probes = np.array([[0, .073], [.017, .034], [.083, .191], [.1, .13]])
        r, z = probes.T
        value = 2+3*r-7*z+5*r*r+11*r*z-13*z*z
        dr, dz = 3+10*r+11*z, -7+11*r-26*z
        fields = sampler.evaluate(probes)
        assert_allclose(fields['Hphi_A_per_m'], r*value, atol=1e-14)
        assert_allclose(fields['Er_quadrature_V_per_m'], -r*dz/(TAU*1e9*EPS0), atol=1e-12)
        assert_allclose(fields['Ez_quadrature_V_per_m'], (2*value+r*dr)/(TAU*1e9*EPS0), atol=1e-12)
        outside = sampler.evaluate([[.2, .1]], outside='nan')
        self.assertFalse(outside['inside'][0])
        self.assertTrue(np.isnan(outside['Hphi_A_per_m'][0]))
        with self.assertRaises(ValueError):
            FieldSampler(mesh.points, mesh.triangles, u, [1e9])
        space.cell_dofs[0, 3] = space.cell_dofs[0, 4]
        with self.assertRaisesRegex(ValueError, 'connectivity'):
            FieldSampler(mesh.points, mesh.triangles, u, [1e9], space=space)

    def test_solution_factory_and_axis_bessel_limit(self):
        from superfish_ng.high_order import solve_p2
        case = Case(((0., .1), (.2, .1)), nr=12, nz=24, modes=1)
        solution = solve_p2(case)
        sampler = FieldSampler.from_solution(solution)
        z = np.linspace(.003, .197, 31)
        fields = sampler.evaluate(np.column_stack((np.zeros_like(z), z)))
        # TM010 has constant axial Ez; compare shape independently of amplitude/sign.
        ez = fields['Ez_quadrature_V_per_m']
        self.assertLess(np.max(abs(ez/ez.mean()-1)), .001)
        assert_allclose(fields['Hphi_A_per_m'], 0)
        assert_allclose(fields['Er_quadrature_V_per_m'], 0)
        solution.space = None
        with self.assertRaisesRegex(ValueError, 'inconsistent'):
            FieldSampler.from_solution(solution)
