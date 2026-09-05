# SPDX-License-Identifier: Apache-2.0
import importlib.util
from pathlib import Path
import sys
import unittest
import numpy as np
from superfish_ng import Case


@unittest.skipUnless(importlib.util.find_spec('matplotlib'), 'optional plotting dependency not installed')
class SupplementalReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
        from seminar_multicell import finer_dx, replacement_identity
        cls.finer_dx = staticmethod(finer_dx)
        cls.identify = staticmethod(replacement_identity)

    def test_refinement_must_be_strictly_finer_for_that_mode(self):
        self.assertEqual(self.finer_dx('.011', .0125), .011)
        for value in (0, -.01, .0125, .025, float('inf'), float('nan')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.finer_dx(value, .0125)

    def test_replacement_preserves_phase_and_does_not_mutate_fields(self):
        case = Case(((0., .05), (1., .05)), modes=7)
        z = np.linspace(0., 1., 801)
        rows = [({'axis': np.column_stack((z, np.cos(p*np.pi*z)))}, None) for p in range(7)]
        candidate = {'axis': np.column_stack((z, -3*np.cos(6*np.pi*z)))}
        before = candidate['axis'].copy()
        result = self.identify(case, rows, 6, candidate)
        self.assertEqual(result['phase_index'], 6)
        self.assertEqual(result['zero_crossings'], 6)
        self.assertGreater(result['cell_overlap'], .99999)
        np.testing.assert_array_equal(candidate['axis'], before)
        np.testing.assert_array_equal(rows[6][0]['axis'][:, 1], np.cos(6*np.pi*z))

    def test_wrong_or_duplicate_mode_is_not_an_extra_refinement(self):
        case = Case(((0., .05), (1., .05)), modes=7)
        z = np.linspace(0., 1., 801)
        rows = [({'axis': np.column_stack((z, np.cos(p*np.pi*z)))}, None) for p in range(7)]
        for wrong in (0, 5):
            with self.subTest(wrong=wrong), self.assertRaises(ValueError):
                self.identify(case, rows, 6, {'axis': np.column_stack((z, np.cos(wrong*np.pi*z)))})


if __name__ == '__main__':
    unittest.main()
