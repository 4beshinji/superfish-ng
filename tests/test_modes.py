# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np


class ModeAnalysisTests(unittest.TestCase):
    def test_band_assignment_uses_fields_not_frequency_order(self):
        from superfish_ng.modes import identify_cell_band
        z = np.linspace(0., .21, 1001)
        permutation = [4, 0, 6, 2, 1, 5, 3]
        fields = np.column_stack([(-1)**p*np.cos(p*np.pi*z/.21) for p in permutation])
        modes = identify_cell_band(z, fields, np.linspace(0., .21, 7))
        self.assertEqual([m['mode_index'] for m in modes], [permutation.index(p)+1 for p in range(7)])
        self.assertEqual([m['zero_crossings'] for m in modes], list(range(7)))
        self.assertTrue(all(m['cell_overlap'] > .99999 for m in modes))

    def test_bad_field_shapes_and_duplicate_modes_are_rejected(self):
        from superfish_ng.modes import identify_cell_band
        z = np.linspace(0., 1., 401)
        fields = np.column_stack([np.cos(p*np.pi*z) for p in range(4)])
        fields[:, 2] = fields[:, 1]
        with self.assertRaises(ValueError):
            identify_cell_band(z, fields, np.linspace(0., 1., 4))
        for bad_z, bad_fields in [(z[::-1], fields), (z, fields[:-1]), (z, fields*np.nan)]:
            with self.assertRaises(ValueError):
                identify_cell_band(bad_z, bad_fields, np.linspace(0., 1., 4))

    def test_dispersion_fit_residual_and_coefficients(self):
        from superfish_ng.modes import fit_dispersion
        theta = np.linspace(0., np.pi, 7)
        frequency = 2.85e9-1.4e7*np.cos(theta)+2e5*np.cos(2*theta)
        fit = fit_dispersion(theta, frequency)
        residual = np.array(fit['residual_hz'])
        self.assertAlmostEqual(fit['m2_hz'], -1.4e7, delta=1e-5)
        self.assertLess(abs(residual.sum()), 1e-5)
        self.assertLess(abs(residual @ np.cos(theta)), 1e-5)
        np.testing.assert_allclose(np.array(fit['fitted_hz'])+residual, frequency)
        with self.assertRaises(ValueError):
            fit_dispersion([0., 0.], [1., 2.])


if __name__ == '__main__':
    unittest.main()
