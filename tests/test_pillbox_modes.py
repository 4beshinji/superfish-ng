# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from scipy.integrate import quad
from scipy.special import j0, j1
from superfish_ng import Case, solve
from superfish_ng.analytic import pillbox_tm_mode, pillbox_tm010
from superfish_ng.constants import MU0, EPS0, C0, TAU
from superfish_ng.rf import quantities
from superfish_ng.sampling import FieldSampler


class PillboxModeTests(unittest.TestCase):
    def test_general_reference_matches_existing_tm010(self):
        old, new = pillbox_tm010(.075, .08), pillbox_tm_mode(.075, .08)
        for key in old.keys() & new.keys():
            self.assertAlmostEqual(new[key]/old[key], 1., places=12)

    def test_tm011_rf_reference_against_volume_wall_and_voltage_integrals(self):
        radius, length = .075, .08
        a = pillbox_tm_mode(radius, length, p=1)
        h0, alpha, kz = a['h0_a_per_m'], a['radial_wave_number_per_m'], a['axial_wave_number_per_m']
        radial = quad(lambda r: r*j1(alpha*r)**2, 0, radius)[0]
        axial = quad(lambda z: np.cos(kz*z)**2, 0, length)[0]
        energy = MU0/2*TAU*h0**2*radial*axial
        wall_h2 = TAU*h0**2*(radius*j1(alpha*radius)**2*axial+2*radial)
        loss = a['surface_resistance_ohm']/2*wall_h2
        k = TAU*a['frequency_hz']/C0
        v = a['e0_v_per_m']*complex(quad(lambda z: np.cos(kz*z)*np.cos(k*z), 0, length)[0],
                                   quad(lambda z: np.cos(kz*z)*np.sin(k*z), 0, length)[0])
        self.assertAlmostEqual(energy, 1., places=12)
        self.assertAlmostEqual(loss/a['wall_loss_w'], 1., places=12)
        self.assertAlmostEqual(abs(v)/a['vacc_v'], 1., places=12)
        self.assertAlmostEqual(abs(v)**2/(TAU*a['frequency_hz']*energy)/a['r_over_q_accelerator_ohm'], 1., places=12)

    def test_tm011_frequency_rf_and_field_shape_are_separate_gates(self):
        case = Case(((0., .075), (.08, .075)), nr=64, nz=70, modes=2)
        s = solve(case)
        a = pillbox_tm_mode(.075, .08, p=1)
        q = quantities(case, s, 1)
        self.assertLess(abs(q['frequency_hz']/a['frequency_hz']-1), .001)
        for key in ['q0', 'geometry_factor_ohm', 'r_over_q_accelerator_ohm', 'wall_loss_w', 'transit_time_factor_abs']:
            self.assertLess(abs(q[key]/a[key]-1), .005)
        z = np.linspace(0, .08, 401)
        sampler = FieldSampler(s.mesh.points, s.mesh.triangles, s.u, s.frequencies_hz)
        axis = sampler.evaluate(np.column_stack((np.zeros(len(z)), z)), 1)['Ez_quadrature_V_per_m']
        expected = a['e0_v_per_m']*np.cos(np.pi*z/.08)
        axis *= 1 if np.dot(axis, expected) > 0 else -1
        self.assertLess(np.linalg.norm(axis-expected)/np.linalg.norm(expected), .005)
        self.assertLess(abs(axis[len(z)//2])/np.max(np.abs(axis)), .001)
