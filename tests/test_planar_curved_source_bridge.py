# SPDX-License-Identifier: Apache-2.0
"""A source compatibility claim must preserve complete physical RF metadata."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sys
import unittest
from superfish_ng.planar_curved import PlanarCurvedCase
from superfish_ng.planar_curved_solver import solve_planar_curved, planar_curved_quantities
from test_planar_curved import patch
from test_planar_curved import curved_ellipse
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from validate_planar_curved_source_bridge import verify_RF, sampled_original_fields


class SourceBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.solution = solve_planar_curved(PlanarCurvedCase(patch(), modes=2))
        cls.rf = [planar_curved_quantities(cls.solution, i) for i in range(2)]

    def test_complete_physical_RF_allows_only_floating_roundoff(self):
        self.assertTrue(all(v == 0 for v in verify_RF(self.rf, self.rf).values()))
        changed = deepcopy(self.rf)
        changed[0]['wall_loss_w_per_m'] *= 1+1e-13
        self.assertLess(verify_RF(changed, self.rf)['wall_loss_w_per_m'], 1e-12)
        for value in (1.0000000001, float('nan'), float('inf')):
            changed = deepcopy(self.rf)
            changed[0]['wall_loss_w_per_m'] *= value
            with self.subTest(value=value), self.assertRaises(ValueError):
                verify_RF(changed, self.rf)

    def test_missing_guard_schema_nulls_and_units_cannot_pass(self):
        for rows in ([], self.rf[:1]):
            with self.assertRaises(ValueError):
                verify_RF(rows, self.rf)
        for key, value in [('phasor_convention', 'rms'), ('longitudinal_units', 'J and W'),
            ('r_over_q_accelerator_ohm', 0.), ('r_over_q_circuit_ohm', 0.),
            ('accelerating_quantities_reason', ''), ('wall_quadrature_order', 16)]:
            changed = deepcopy(self.rf);changed[0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                verify_RF(changed, self.rf)
        changed = deepcopy(self.rf);del changed[1]['geometry_factor_ohm']
        with self.assertRaises(ValueError):
            verify_RF(changed, self.rf)

    def test_actual_original_public_signed_fields_match_literal_P2_Maxwell(self):
        probes = sampled_original_fields(self.solution)
        self.assertLess(probes['electric_relative_difference'], 1e-12)
        self.assertLess(probes['magnetic_relative_difference'], 1e-12)
        self.assertFalse(probes['exact_TM_PEC_wall_checked'])

    def test_TM_PEC_probe_covers_later_modes_not_only_first_mode(self):
        solution = solve_planar_curved(PlanarCurvedCase(curved_ellipse(12), 'tm', modes=3))
        coefficients = solution.coefficients.copy()
        coefficients[solution.case.domain.boundary_nodes[0, 0], 1] = 1.
        tampered = replace(solution, coefficients=coefficients)
        # This isolated trace validator must reject a later-mode violation even
        # with the first mode unchanged; it is not a valid eigenpair fixture.
        with self.assertRaisesRegex(ValueError, 'PEC scalar'):
            sampled_original_fields(tampered)


if __name__ == '__main__':
    unittest.main()
