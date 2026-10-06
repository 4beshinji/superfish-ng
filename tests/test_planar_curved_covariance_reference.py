# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from pathlib import Path
import sys
import unittest
import numpy as np
from superfish_ng.planar_curved import PlanarCurvedCase
from superfish_ng.planar_curved_solver import solve_planar_curved
from test_planar_curved import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from validate_planar_curved_covariance import transformed_domain, compare_covariance


class PlanarCurvedCovarianceReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        angle = .37
        cls.rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
        cls.translation = np.array([-.07, .02])
        cls.first = solve_planar_curved(PlanarCurvedCase(patch(shift=(-.03, .01)), modes=2,
            max_geometry_boxes=100000000))
        cls.second = solve_planar_curved(replace(cls.first.case,
            domain=transformed_domain(cls.first.case.domain, 2., cls.rotation, cls.translation)))

    def compare(self, second=None, **kwargs):
        controls = dict(scale=2., rotation=self.rotation, translation=self.translation, groups=[1, 1])
        controls.update(kwargs)
        return compare_covariance(self.first, self.second if second is None else second, **controls)

    def test_independent_actual_FEM_preserves_signed_vector_and_all_RF_scale_laws(self):
        result = self.compare()
        self.assertTrue(result['passed'])
        for row in result['groups']:
            self.assertLess(row['frequency_scale_relative_error'], 1e-12)
            self.assertLess(row['electric_relative_L2_error'], 1e-12)
            self.assertLess(row['magnetic_relative_L2_error'], 1e-12)
            self.assertLess(max(row['RF_scale_relative_errors'].values()), 1e-12)

    def test_frequency_and_scalar_amplitude_cannot_be_fitted_away(self):
        changed = replace(self.second, frequencies_hz=self.second.frequencies_hz*1.03)
        row = self.compare(changed)['groups'][0]
        self.assertFalse(row['gates']['frequency'])
        self.assertAlmostEqual(row['electric_relative_L2_error'], .03, places=12)
        self.assertLess(row['magnetic_relative_L2_error'], 1e-12)
        changed = replace(self.second, coefficients=self.second.coefficients*1.03)
        row = self.compare(changed)['groups'][0]
        self.assertFalse(row['passed'])
        self.assertAlmostEqual(row['magnetic_relative_L2_error'], 1-1/1.03, places=12)

    def test_full_geometry_and_explicit_proper_transform_are_required(self):
        for kwargs in ({'scale': True}, {'scale': 0.}, {'rotation': [[1., 0.], [0., -1.]]},
            {'translation': [0., 0.]}, {'groups': [1]}, {'groups': [True, 1]}):
            with self.assertRaises(ValueError):
                self.compare(**kwargs)


if __name__ == '__main__':
    unittest.main()
