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


class QuadraticSurfaceTests(unittest.TestCase):
    def test_interior_stationary_points_and_constant_field(self):
        from superfish_ng.quadratic_rf import polynomial_peak_squared
        self.assertAlmostEqual(polynomial_peak_squared([[0, 4, -4], [0]]), 1.)
        self.assertAlmostEqual(polynomial_peak_squared([[3], [4]]), 25.)
        self.assertEqual(polynomial_peak_squared([[0]]), 0.)
        # Cubic H=t-t³ peaks at 1/sqrt(3), not an endpoint.
        self.assertAlmostEqual(polynomial_peak_squared([[0, 1, 0, -1]]), 4/27)

    def test_manufactured_surface_integral_and_one_sided_peaks(self):
        from superfish_ng.quadratic_rf import surface_integrals_p2
        from superfish_ng.constants import EPS0, TAU
        from scipy.optimize import minimize_scalar
        case = Case(((0., .1), (.2, .1)), nr=3, nz=4, modes=1)
        sol = solve_p2(case)
        r,z = sol.space.dof_points.T
        sol.u[:,0] = 1+2*r+3*z+4*r*r+5*r*z-6*z*z
        omega = TAU*sol.frequencies_hz[0]
        exact_integral, exact_e, exact_h = 0., 0., 0.
        for ends in sol.mesh.points[sol.mesh.boundary_edges[sol.mesh.boundary_tags == 'pec']]:
            length = np.linalg.norm(ends[1]-ends[0])
            def fields(t):
                r,z = ends[0]*(1-t)+ends[1]*t
                u = 1+2*r+3*z+4*r*r+5*r*z-6*z*z
                er = -r*(3+5*r-12*z)/(omega*EPS0)
                ez = (2*u+r*(2+8*r+5*z))/(omega*EPS0)
                return r, r*u, np.hypot(er,ez)
            exact_integral += quad(lambda t: TAU*length*fields(t)[0]*fields(t)[1]**2, 0, 1, epsabs=1e-13)[0]
            for index in [1,2]:
                value = max(abs(fields(0)[index]), abs(fields(1)[index]),
                            -minimize_scalar(lambda t: -abs(fields(t)[index]), bounds=(0,1), method='bounded').fun)
                if index == 1: exact_h=max(exact_h,value)
                else: exact_e=max(exact_e,value)
        np.testing.assert_allclose(surface_integrals_p2(sol), [exact_integral, exact_e, exact_h], rtol=2e-12)

    def test_multimode_rf_convergence_and_normalization(self):
        from dataclasses import replace
        from superfish_ng.rf import quantities, cell_fields
        from superfish_ng.analytic import pillbox_tm_mode
        errors=[]
        for n in [4,8,16]:
            case=Case(((0.,.1),(.2,.1)),nr=n,nz=2*n,modes=3)
            sol=solve_p2(case)
            level=[]
            for mode in range(3):
                result=quantities(case,sol,mode)
                exact=pillbox_tm_mode(.1,.2,p=mode)
                level.append([abs(result[k]/exact[k]-1) for k in ['r_over_q_accelerator_ohm','geometry_factor_ohm']])
                self.assertLess(result['energy_balance_relative'],1e-10)
                self.assertAlmostEqual(result['stored_energy_j'],1.,places=10)
                self.assertTrue(all(np.isfinite(x).all() for x in cell_fields(sol,mode)))
            errors.append(level)
        self.assertTrue(np.all(np.array(errors[-1]) < 1e-4),errors)
        self.assertTrue(np.all(np.array(errors[-1])/errors[-2] < .15),errors)
        scaled=replace(case,normalization_j=4.)
        sr=quantities(scaled,solve_p2(scaled))
        original=quantities(case,sol)
        for key in ['r_over_q_accelerator_ohm','geometry_factor_ohm','q0']:
            self.assertAlmostEqual(sr[key]/original[key],1.,places=10)
        self.assertAlmostEqual(sr['vacc_v']/original['vacc_v'],2.,places=10)
        self.assertAlmostEqual(sr['wall_loss_w']/original['wall_loss_w'],4.,places=10)

    def test_length_scaling_of_quadratic_rf(self):
        from dataclasses import replace
        from superfish_ng.rf import quantities
        case=Case(((0.,.1),(.2,.1)),nr=5,nz=10,modes=1,element_order=2)
        scaled=replace(case,profile=((0.,.3),(.6,.3)))
        a,b=quantities(case,solve_p2(case)),quantities(scaled,solve_p2(scaled))
        for key,ratio in [('frequency_hz',1/3),('stored_energy_j',1),('vacc_v',3**-.5),
                          ('wall_loss_w',3**-1.5),('q0',3**.5),('geometry_factor_ohm',1),
                          ('r_over_q_accelerator_ohm',1),('epk_surface_estimate_v_per_m',3**-1.5),
                          ('bpk_surface_estimate_t',3**-1.5)]:
            self.assertAlmostEqual(b[key]/a[key],ratio,places=9,msg=key)
