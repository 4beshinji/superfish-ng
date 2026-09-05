# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import importlib.util
import sys
import unittest
import numpy as np
from superfish_ng import Case, make_mesh
from superfish_ng.geometry import profile_area, linearize_profile
from superfish_ng.mesh import element_geometry

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))


class EndCellTests(unittest.TestCase):
    def test_full_ends_retain_half_disks_at_iris_center_cuts(self):
        for family, aperture in [('flat', .010857), ('rounded', .00985)]:
            case = Case.load(ROOT/f'examples/seminar_4cell_{family}_full_ends.json')
            half = Case.load(ROOT/f'examples/seminar_4cell_{family}.json')
            self.assertEqual(case.length, .13996)
            self.assertEqual(case.profile[0], (0., aperture))
            self.assertEqual(case.profile[-1], (.13996, aperture))
            self.assertAlmostEqual(profile_area(case)/profile_area(half), 4/3, places=12)
            profile = np.array(linearize_profile(case))
            mirror = profile[::-1].copy(); mirror[:, 0] = case.length-mirror[:, 0]
            np.testing.assert_allclose(profile, mirror, rtol=0, atol=1e-14)
            mesh = make_mesh(case)
            self.assertEqual(set(mesh.boundary_tags), {'axis', 'pec'})
            _, det, _ = element_geometry(mesh)
            polygon = sum((b[0]-a[0])*(b[1]+a[1])/2 for a, b in zip(profile, profile[1:]))
            self.assertAlmostEqual(det.sum()/2, polygon, places=12)
            self.assertEqual(len(case.arcs), 8 if family == 'rounded' else 0)

    @unittest.skipUnless(importlib.util.find_spec('matplotlib'), 'optional plotting dependency not installed')
    def test_full_end_order_is_zero_count_not_half_end_phase(self):
        from seminar_end_cells import zero_identification
        z = np.linspace(0., 1., 801)
        fields = np.column_stack([np.cos(p*np.pi*z) for p in (2, 0, 3, 1)])
        result = zero_identification(z, fields, (np.arange(4)+.5)/4)
        self.assertEqual([m['mode_index'] for m in result], [2, 4, 1, 3])
        self.assertTrue(all('phase_rad' not in m for m in result))
        with self.assertRaises(ValueError):
            zero_identification(z, np.ones((len(z), 4)), (np.arange(4)+.5)/4)


if __name__ == '__main__':
    unittest.main()
