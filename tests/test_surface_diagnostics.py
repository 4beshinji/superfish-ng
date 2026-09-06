# SPDX-License-Identifier: Apache-2.0
"""Independent geometry and analytic-field controls for the surface experiment."""
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from evaluate_surface_fields import fillet_case, run_case, sharp_probes, probe_surface
from superfish_ng import Case
from superfish_ng.analytic import pillbox_tm_mode
from superfish_ng.geometry import arc_geometry


class SurfaceDiagnosticsTests(unittest.TestCase):
    def test_fillet_radius_tangency_and_reflection(self):
        base = Case.load(ROOT/'examples/shaped_cell.json')
        case = fillet_case(base)
        vertices = np.asarray(case.profile)
        for index, radius, direction in case.arcs:
            center, _, _ = arc_geometry(vertices[index-1], vertices[index], radius, direction)
            for point, tangent in [(vertices[index-1], vertices[index-1]-vertices[index-2]),
                                   (vertices[index], vertices[index+1]-vertices[index])]:
                self.assertAlmostEqual(np.linalg.norm(point-center), .003, places=13)
                self.assertAlmostEqual(np.dot((point-center)/radius, tangent/np.linalg.norm(tangent)), 0., places=12)
        reflected = vertices[::-1].copy()
        reflected[:, 0] = base.length-reflected[:, 0]
        np.testing.assert_allclose(vertices, reflected, atol=1e-14, rtol=0)
        with self.assertRaisesRegex(ValueError, 'overlap'):
            fillet_case(base, radius_m=1.)

    def test_probe_retains_both_discontinuous_traces(self):
        ends = np.array([[[.1, 0.], [.1, .1]], [[.1, .1], [.1, .2]]])
        fields = np.array([[[2., 0.], [2., 0.]], [[5., 0.], [5., 0.]]])
        result = probe_surface(ends, fields, np.array([.1, .1]), [.1, .1])
        self.assertEqual(result['trace_count'], 2)
        self.assertEqual(result['e_min_v_per_m'], 2.)
        self.assertEqual(result['e_max_v_per_m'], 5.)
        self.assertEqual(result['tangential_e_max_v_per_m'], 0.)
        with self.assertRaisesRegex(ValueError, 'does not lie'):
            probe_surface(ends, fields, np.array([.1, .1]), [.09, .1])

    def test_probe_distance_is_physical_and_mesh_independent(self):
        base = Case.load(ROOT/'examples/shaped_cell.json')
        probes = sharp_probes(base)
        self.assertEqual(probes, sharp_probes(replace(base, nr=256, nz=512)))
        for p in probes:
            corner = np.array(base.profile[p['corner_index']])[::-1]
            self.assertAlmostEqual(np.linalg.norm(np.array(p['point_rz_m'])-corner), p['distance_m'], places=14)

    def test_surface_field_converges_to_bessel_solution(self):
        exact = pillbox_tm_mode(.075, .08)
        with tempfile.TemporaryDirectory() as folder:
            results = []
            for n in [12, 24]:
                case = Case(((0., .075), (.08, .075)), modes=1, nr=n, nz=n)
                row = run_case(case, Path(folder)/str(n), analytic=exact)
                results.append(row['analytic'])
            for key in ['surface_max_absolute_error_over_e0', 'peak_relative_error', 'frequency_relative_error']:
                self.assertLess(results[1][key], results[0][key])
            self.assertLess(results[-1]['peak_relative_error'], .01)


if __name__ == '__main__':
    unittest.main()
