# SPDX-License-Identifier: Apache-2.0
"""Hand-computed sample norms, common phasor sign and worst peak endpoints."""
from copy import deepcopy
import unittest
import numpy as np
from superfish_ng.adaptive_efficiency_accuracy import assess_efficiency_samples


class AdaptiveEfficiencyAccuracyTests(unittest.TestCase):
    def inputs(self):
        q = dict(frequency_hz=1000., r_over_q_accelerator_ohm=100., r_over_q_circuit_ohm=50.,
                 geometry_factor_ohm=100., epk_over_eacc=1., bpk_over_eacc_mt_per_mv_per_m=1.)
        return dict(native_fields=np.array([[0.,1.,2.],[0.,2.,1.]]),
                    reference_fields=np.array([[0.,1.,2.],[0.,2.,1.]]), volume_weights=np.array([1.,3.]),
                    native_axis_ez=np.array([1.,2.]), reference_axis_ez=np.array([1.,2.]), axis_weights=np.array([2.,1.]),
                    native_quantities=deepcopy(q), reference_quantities=deepcopy(q),
                    native_peak_intervals={key:[1.,1.] for key in ('epk_over_eacc','bpk_over_eacc_mt_per_mv_per_m')})

    def test_one_common_negative_sign_and_original_arrays_unchanged(self):
        data = self.inputs();data['native_fields'] *= -1;data['native_axis_ez'] *= -1
        before = deepcopy(data)
        result = assess_efficiency_samples(**data)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['common_hphi_sign'], -1)
        self.assertTrue(all(value == 0 for value in result['relative_errors'].values()))
        self.assertEqual(result['physical_acceptance_status'], 'SOURCE_DOMAIN_REFERENCE_CHECKS_REQUIRED')
        self.assertIsNone(result['physical_error_bound'])
        for name in ('native_fields','reference_fields','native_axis_ez','reference_axis_ez','volume_weights','axis_weights'):
            np.testing.assert_array_equal(data[name], before[name])
        result['limits']['frequency_hz'] = 1.
        self.assertEqual(assess_efficiency_samples(**data)['limits']['frequency_hz'], 1e-4)

    def test_absolute_field_amplitude_error_uses_native_norm_without_fit(self):
        data = self.inputs();data['native_fields'] *= 1.006;data['native_axis_ez'] *= 1.006
        result = assess_efficiency_samples(**data)
        expected = .006/1.006
        for name in ('electric_relative_l2','magnetic_relative_l2','axis_ez_relative_l2'):
            self.assertAlmostEqual(result['relative_errors'][name], expected, places=14)
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(result['gates']['frequency_hz'])
        self.assertFalse(result['gates']['electric_relative_l2'])
        self.assertFalse(result['gates']['magnetic_relative_l2'])
        self.assertTrue(result['gates']['axis_ez_relative_l2'])

    def test_wrong_electric_phase_is_not_rescued_with_an_independent_sign(self):
        data = self.inputs();data['native_fields'][:,:2] *= -1;data['native_axis_ez'] *= -1
        result = assess_efficiency_samples(**data)
        self.assertEqual(result['common_hphi_sign'], 1)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['relative_errors']['electric_relative_l2'], 2.)
        self.assertEqual(result['relative_errors']['axis_ez_relative_l2'], 2.)
        self.assertEqual(result['relative_errors']['magnetic_relative_l2'], 0.)

    def test_both_peak_endpoints_evaluated_even_when_estimate_would_pass(self):
        data = self.inputs();data['native_peak_intervals']['epk_over_eacc'] = [1.,1.02]
        result = assess_efficiency_samples(**data)
        self.assertEqual(result['status'], 'FAIL')
        self.assertAlmostEqual(result['relative_errors']['epk_over_eacc'], .02, places=14)
        self.assertFalse(result['gates']['epk_over_eacc'])
        self.assertTrue(result['gates']['frequency_hz'])

    def test_missing_nonfinite_zero_norm_or_discarded_nodes_are_unverified(self):
        for name,value in (('reference_fields', [[0.,1.,2.]]), ('volume_weights', [1.,0.]),
                           ('native_axis_ez',[0.,0.]), ('reference_axis_ez',[1.,float('nan')]),
                           ('native_fields',[[0.,1.,0.],[0.,2.,0.]]),
                           ('reference_fields',np.ones((2,3),dtype=complex))):
            with self.subTest(name=name):
                data = self.inputs();data[name] = value
                result = assess_efficiency_samples(**data)
                self.assertEqual(result['status'], 'UNVERIFIED')
                self.assertTrue(all(v is None for v in result['relative_errors'].values()))
                self.assertFalse(any(result['gates'].values()))

    def test_rq_convention_mismatch_or_missing_rf_remains_unverified(self):
        for missing in (False,True):
            data = self.inputs()
            if missing:
                del data['reference_quantities']['geometry_factor_ohm']
            else:
                data['native_quantities']['r_over_q_circuit_ohm'] = 100.
            result = assess_efficiency_samples(**data)
            self.assertEqual(result['status'], 'UNVERIFIED')
            self.assertTrue(all(v is None for v in result['relative_errors'].values()))

    def test_valid_zero_lower_peak_bound_is_a_failed_accuracy_not_missing_data(self):
        data = self.inputs();data['native_peak_intervals']['epk_over_eacc'] = [0.,2.]
        result = assess_efficiency_samples(**data)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['relative_errors']['epk_over_eacc'], 1.)

    def test_unrepresentable_relative_weights_do_not_silently_discard_nodes(self):
        data = self.inputs();data['volume_weights'] = np.array([1e-300,1e300])
        result = assess_efficiency_samples(**data)
        self.assertEqual(result['status'], 'UNVERIFIED')
        self.assertIn('lost a supplied node', result['unverified_reason'])
        self.assertTrue(all(v is None for v in result['relative_errors'].values()))


if __name__ == '__main__':
    unittest.main()
