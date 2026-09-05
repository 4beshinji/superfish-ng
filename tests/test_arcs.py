# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from superfish_ng import Case, make_mesh
from superfish_ng.mesh import element_geometry


PROFILE = ((0., .05), (.02, .05), (.02, .02), (.03, .01),
           (.04, .01), (.05, .02), (.05, .05), (.07, .05))
ARCS = ((3, .01, 'ccw'), (5, .01, 'ccw'))


class ArcGeometryTests(unittest.TestCase):
    def test_circular_radius_direction_and_chord_error(self):
        from superfish_ng.geometry import arc_geometry, linearize_profile
        case = Case(PROFILE, geometry_type='arc_profile', arcs=ARCS, arc_chord_tolerance_m=1e-5)
        center, angle, sweep = arc_geometry(PROFILE[2], PROFILE[3], .01, 'ccw')
        np.testing.assert_allclose(center, [.03, .02], atol=1e-15)
        self.assertAlmostEqual(sweep, np.pi/2)
        points = np.array(linearize_profile(case))
        arc = points[(points[:, 0] >= .02) & (points[:, 0] <= .03) & (points[:, 1] <= .02)]
        np.testing.assert_allclose(np.linalg.norm(arc-center, axis=1), .01, atol=1e-15)
        midpoint = (arc[:-1]+arc[1:])/2
        self.assertLessEqual(np.max(.01-np.linalg.norm(midpoint-center, axis=1)), 1e-5)

    def test_strict_schema_retains_original_arcs_and_radius(self):
        case = Case(PROFILE, geometry_type='arc_profile', arcs=ARCS, arc_chord_tolerance_m=1e-5)
        data = case.to_dict()
        self.assertEqual(data['geometry']['points_zr_m'], [list(p) for p in PROFILE])
        self.assertEqual(Case.from_dict(data), case)
        data['schema_version'] = 1
        with self.assertRaises(ValueError): Case.from_dict(data)
        for arcs in [((3, .001, 'ccw'),), ((3, .0075, 'ccw'),), ((3, .01, 'wrong'),), ((0, .01, 'ccw'),), ((3, .01, 'ccw'),)*2]:
            with self.subTest(arcs=arcs), self.assertRaises(ValueError):
                Case(PROFILE, geometry_type='arc_profile', arcs=arcs)
        with self.assertRaises(ValueError):
            Case(PROFILE, geometry_type='stepped_profile', arcs=ARCS)

    def test_arc_domain_area_converges_separately_from_fem_spacing(self):
        from superfish_ng.geometry import linearize_profile, profile_area
        exact = .0025-np.pi*.01**2/2
        errors = []
        for tolerance in [4e-5, 1e-5, 2.5e-6]:
            case = Case(PROFILE, geometry_type='arc_profile', arcs=ARCS,
                        arc_chord_tolerance_m=tolerance, nr=20, nz=25)
            self.assertAlmostEqual(profile_area(case), exact, places=15)
            mesh = make_mesh(case)
            _, det, _ = element_geometry(mesh)
            errors.append(abs(det.sum()/2-exact))
            profile = linearize_profile(case)
            polygon_area = sum((b[0]-a[0])*(a[1]+b[1])/2 for a, b in zip(profile, profile[1:]))
            self.assertAlmostEqual(det.sum()/2, polygon_area, places=13)
        self.assertTrue(all(b < a/2 for a, b in zip(errors, errors[1:])))


if __name__ == '__main__':
    unittest.main()
