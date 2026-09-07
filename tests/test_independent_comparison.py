# SPDX-License-Identifier: Apache-2.0
"""Acceptance must detect common-mode error, missing convergence and wrong fields."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np
from scipy.special import j1, jn_zeros

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from compare_ngsolve import Case, LIMITS, acceptance, probe_points, reference
from superfish_ng.analytic import pillbox_tm010, pillbox_tm_mode
from compare_contour_ngsolve import electric_difference


class ComparisonGateTests(unittest.TestCase):
    def setUp(self):
        self.exact = {key: 1. for key in LIMITS}
        row = dict(self.exact, hphi_probes_a_per_m=[1., 2., 3.])
        self.rows = [deepcopy(row) for _ in range(3)]

    def test_agreement_cannot_hide_unconverged_rf(self):
        bad = deepcopy(self.rows)
        bad[-2]["r_over_q_accelerator_ohm"] = 1.1
        self.assertFalse(acceptance(bad, self.rows)["passed"])
        self.assertFalse(acceptance(self.rows, bad)["passed"])

    def test_analytic_control_detects_shared_error(self):
        wrong = dict(self.exact, frequency_hz=1.01)
        self.assertFalse(acceptance(self.rows, self.rows, wrong)["passed"])

    def test_field_sign_is_arbitrary_but_shape_is_not(self):
        other = deepcopy(self.rows)
        other[-1]["hphi_probes_a_per_m"] = [-1., -2., -3.]
        self.assertTrue(acceptance(self.rows, other)["passed"])
        other[-1]["hphi_probes_a_per_m"] = [3., 2., 1.]
        self.assertFalse(acceptance(self.rows, other)["passed"])

    def test_nonfinite_and_missing_convergence_cannot_pass(self):
        bad = deepcopy(self.rows)
        bad[-1]["geometry_factor_ohm"] = float("nan")
        self.assertFalse(acceptance(self.rows, bad)["passed"])
        with self.assertRaisesRegex(ValueError, "three"):
            acceptance(self.rows[:2], self.rows)

    def test_electric_comparison_uses_magnetic_sign_without_amplitude_fit(self):
        exact = dict(hphi_probes_a_per_m=[1.,2.],electric_probes_v_per_m=[[0.,3.],[2.,4.]])
        opposite = dict(hphi_probes_a_per_m=[-1.,-2.],electric_probes_v_per_m=[[0.,-3.],[-2.,-4.]])
        self.assertEqual(electric_difference(exact,opposite),0.)
        wrong = deepcopy(exact)
        wrong['electric_probes_v_per_m'] = (2*np.asarray(exact['electric_probes_v_per_m'])).tolist()
        self.assertAlmostEqual(electric_difference(wrong,exact),1.)


@unittest.skipUnless(importlib.util.find_spec("ngsolve"), "optional NGSolve reference environment")
class ReferencePhysicsTests(unittest.TestCase):
    def test_pillbox_frequency_rf_and_bessel_field(self):
        case = Case(((0., .08), (.12, .08)), modes=1)
        row = reference(case, .012)
        exact = pillbox_tm010(.08, .12)
        for key, limit in LIMITS.items():
            self.assertLess(abs(row[key]/exact[key]-1), limit, key)
        amplitude = pillbox_tm_mode(.08, .12)["h0_a_per_m"]
        field = amplitude*j1(jn_zeros(0, 1)[0]*probe_points(case)[:, 0]/.08)
        actual = np.asarray(row["hphi_probes_a_per_m"])
        error = min(np.linalg.norm(actual-field), np.linalg.norm(actual+field))/np.linalg.norm(field)
        self.assertLess(error, 1e-4)
        from scipy.special import j0
        exact_e = pillbox_tm_mode(.08,.12)['e0_v_per_m']*j0(jn_zeros(0,1)[0]*probe_points(case)[:,0]/.08)
        sign = 1 if np.dot(actual,field)>=0 else -1
        actual_e = sign*np.asarray(row['electric_probes_v_per_m'])
        self.assertLess(np.linalg.norm(actual_e[:,1]-exact_e)/np.linalg.norm(exact_e),.001)
        self.assertLess(np.linalg.norm(actual_e[:,0])/np.linalg.norm(exact_e),.001)

    def test_reference_rejects_unsupported_physics(self):
        with self.assertRaisesRegex(ValueError, "PEC"):
            reference(Case(((0., .08), (.12, .08)), modes=1, z_min="magnetic_symmetry"), .012)
