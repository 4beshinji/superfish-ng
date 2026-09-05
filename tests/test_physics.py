# SPDX-License-Identifier: Apache-2.0
import unittest
from dataclasses import replace
import numpy as np
from numpy.testing import assert_allclose
from scipy.integrate import quad
from scipy.special import j0, j1, jn_zeros
from superfish_ng import Case, solve, make_mesh
from superfish_ng.analytic import pillbox_tm010, pillbox_spectrum
from superfish_ng.constants import C0, MU0, EPS0, TAU, Z0
from superfish_ng.fem import assemble, triangle_quadrature
from superfish_ng.mesh import element_geometry
from superfish_ng.rf import quantities, linear_voltage


class PhysicsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = Case(((0., .1), (.2, .1)), nr=40, nz=48, modes=6)
        cls.sol = solve(cls.case)
        cls.q = quantities(cls.case, cls.sol)
        cls.exact = pillbox_tm010(.1, .2)

    def test_tm010_frequency(self):
        self.assertLess(abs(self.q['frequency_hz']/self.exact['frequency_hz']-1), 1e-4)

    def test_six_modes_including_axial_and_radial_families(self):
        expected = pillbox_spectrum(.1, .2, 6)
        self.assertIn('TM020', [row[1] for row in expected])
        self.assertIn('TM011', [row[1] for row in expected])
        assert_allclose(self.sol.frequencies_hz, [r[0] for r in expected], rtol=.003)

    def test_physical_field_shape_against_bessel_not_only_frequency(self):
        s, c = self.sol, self.case
        p, det, grad = element_geometry(s.mesh)
        u = s.u[:, 0][s.mesh.triangles]
        du = np.einsum('ti,tij->tj', u, grad)
        root = jn_zeros(0, 1)[0]
        h0 = np.sqrt(2/(MU0*np.pi*.1**2*.2*j1(root)**2))
        he = ee = hn = en = 0.
        for n, w in triangle_quadrature():
            r = p[:, :, 0] @ n
            uh = u @ n
            hh = r*uh
            er = -r*du[:, 1]/(TAU*s.frequencies_hz[0]*EPS0)
            ez = (2*uh+r*du[:, 0])/(TAU*s.frequencies_hz[0]*EPS0)
            ha, ea = h0*j1(root*r/.1), Z0*h0*j0(root*r/.1)
            weight = w*det*r
            he += np.sum(weight*(hh-ha)**2)
            ee += np.sum(weight*((ez-ea)**2+er**2))
            hn += np.sum(weight*ha**2)
            en += np.sum(weight*ea**2)
        self.assertLess(np.sqrt(he/hn), .002)
        self.assertLess(np.sqrt(ee/en), .02)

    def test_energy_and_mode_orthogonality(self):
        self.assertLess(self.sol.orthogonality_error, 1e-10)
        self.assertLess(max(self.sol.residuals), 1e-8)
        for i in range(self.case.modes):
            q = quantities(self.case, self.sol, i)
            self.assertAlmostEqual(q['stored_energy_j'], 1., places=9)
            self.assertLess(q['energy_balance_relative'], 1e-9)

    def test_q0_geometry_factor_rq_and_ttf(self):
        for key in ['q0', 'geometry_factor_ohm', 'r_over_q_accelerator_ohm', 'transit_time_factor_abs']:
            with self.subTest(key=key):
                self.assertLess(abs(self.q[key]/self.exact[key]-1), .005)

    def test_surface_peak_estimates_on_smooth_pillbox(self):
        for key in ['epk_over_eacc_estimate', 'bpk_over_eacc_estimate_mt_per_mv_per_m']:
            self.assertLess(abs(self.q[key]/self.exact[key]-1), .005)

    def test_rq_factor_two_and_shunt_definitions(self):
        q = self.q
        self.assertEqual(q['r_over_q_accelerator_ohm'], 2*q['r_over_q_circuit_ohm'])
        self.assertAlmostEqual(q['r_shunt_accelerator_ohm'], q['vacc_v']**2/q['wall_loss_w'], places=7)

    def test_linear_voltage_independent_quadrature_and_zero_k(self):
        z, values = np.array([0., .03, .1, .23]), np.array([2., -1., 3., -4.])
        for k in [0., 1e-9, 19., 1000.]:
            v, a = linear_voltage(z, values, k)
            expected = complex(quad(lambda x: np.interp(x,z,values)*np.cos(k*x), 0,.23, points=z, epsabs=1e-10, limit=200)[0],
                               quad(lambda x: np.interp(x,z,values)*np.sin(k*x), 0,.23, points=z, epsabs=1e-10, limit=200)[0])
            self.assertAlmostEqual(abs(v-expected), 0., places=10)
            expected_abs = quad(lambda x: abs(np.interp(x,z,values)), 0,.23, points=z, epsabs=1e-10, limit=200)[0]
            self.assertAlmostEqual(a, expected_abs, places=8)

    def test_beta_changes_voltage_but_not_eigenproblem(self):
        q = quantities(replace(self.case, beta=.7), self.sol)
        exact = pillbox_tm010(.1, .2, beta=.7)
        self.assertLess(abs(q['r_over_q_accelerator_ohm']/exact['r_over_q_accelerator_ohm']-1), .005)
        self.assertEqual(q['frequency_hz'], self.q['frequency_hz'])

    def test_voltage_cancellation_returns_null_peak_ratios(self):
        from superfish_ng.solver import Solution
        c = Case(((0., .1), (.2, .1)), nr=4, nz=4, modes=1)
        s = solve(c)
        # Exact constant-axis trial field and phase 2*pi across length.
        s.u[:, 0] = 1.
        s.frequencies_hz[0] = C0/.2
        q = quantities(c, s)
        self.assertLess(q['transit_time_factor_abs'], 1e-14)
        self.assertIsNone(q['epk_over_eacc_estimate'])

    def test_mass_and_stiffness_constant_trial_integrals(self):
        mesh = make_mesh(Case(((0., .1), (.2, .1)), nr=4, nz=5))
        k, m = assemble(mesh)
        one = np.ones(len(mesh.points))
        self.assertAlmostEqual(float(one @ k @ one)/(2*.1**2*.2), 1., places=12)
        self.assertAlmostEqual(float(one @ m @ one)/(.1**4*.2/4), 1., places=12)
        self.assertLess(np.max(np.abs((k-k.T).data), initial=0.), 1e-14)

    def test_mesh_refinement_decreases_frequency_error(self):
        errors = []
        for n in [8, 16, 32]:
            s = solve(replace(self.case, nr=n, nz=n, modes=1))
            errors.append(abs(s.frequencies_hz[0]/self.exact['frequency_hz']-1))
        self.assertTrue(all(b < .35*a for a,b in zip(errors,errors[1:])))

    def test_geometric_scaling_nontrivial_profile(self):
        case = Case(((0., .04), (.04, .09), (.11, .065), (.17, .04)), nr=16, nz=24, modes=3)
        s = solve(case)
        factor = 2.7
        big = replace(case, profile=tuple((z*factor,r*factor) for z,r in case.profile))
        sb = solve(big)
        assert_allclose(sb.frequencies_hz*factor, s.frequencies_hz, rtol=1e-10)
        q, qb = quantities(case,s), quantities(big,sb)
        self.assertAlmostEqual(qb['r_over_q_accelerator_ohm']/q['r_over_q_accelerator_ohm'], 1., places=9)
        self.assertAlmostEqual(qb['q0']/q['q0'], np.sqrt(factor), places=9)

    def test_normalization_and_conductivity_scaling(self):
        case = replace(self.case, nr=10, nz=12, modes=1)
        q1 = quantities(case, solve(case))
        c2 = replace(case, normalization_j=9., conductivity_s_per_m=4*case.conductivity_s_per_m)
        q2 = quantities(c2, solve(c2))
        for key in ['frequency_hz', 'r_over_q_accelerator_ohm', 'geometry_factor_ohm', 'epk_over_eacc_estimate']:
            self.assertAlmostEqual(q2[key]/q1[key], 1., places=9)
        self.assertAlmostEqual(q2['q0']/q1['q0'], 2., places=9)
        self.assertAlmostEqual(q2['vacc_v']/q1['vacc_v'], 3., places=9)
        self.assertAlmostEqual(q2['wall_loss_w']/q1['wall_loss_w'], 4.5, places=9)


if __name__ == '__main__':
    unittest.main()
