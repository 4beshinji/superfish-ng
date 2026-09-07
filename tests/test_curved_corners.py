# SPDX-License-Identifier: Apache-2.0
import math
import unittest
from superfish_ng.conics import LineSegment, EllipseArc
from superfish_ng.curved_contour import CurvedContour, split_curve
from superfish_ng.curved_corners import classify_curve_joins


class CurvedCornerTests(unittest.TestCase):
    def stepped(self, scale=1.):
        vertices = [(0, 0), (.2, 0), (.2, .1), (.1, .1), (.1, .05), (0, .05)]
        points = [tuple(scale*v for v in point) for point in vertices]
        return CurvedContour(tuple(LineSegment(points[i], points[(i+1)%6]) for i in range(6)),
                             ('axis', 'pec', 'pec', 'pec', 'pec', 'pec'), 0.)

    def test_known_reentrant_angle_and_scale_invariance(self):
        for scale in (1e-5, 1., 1e5):
            report = classify_curve_joins(self.stepped(scale))
            self.assertEqual(report['counts']['reentrant_pec_corner'], 1)
            self.assertEqual(report['counts']['convex_pec_corner'], 3)
            corner = next(j for j in report['joins'] if j['classification'] == 'reentrant_pec_corner')
            self.assertAlmostEqual(corner['vacuum_interior_angle_rad'], 3*math.pi/2)
            self.assertEqual(report['counts']['axis_join'], 2)
            self.assertEqual(report['physical_peak_status'], 'UNVERIFIED')

    def test_curve_splitting_adds_no_physical_corner(self):
        contour = self.stepped()
        pieces = sum((list(split_curve(curve)) for curve in contour.curves), [])
        refined = CurvedContour(tuple(pieces), tuple(tag for tag in contour.edge_tags for _ in range(2)), 0.)
        report = classify_curve_joins(refined)
        self.assertEqual(report['counts']['reentrant_pec_corner'], 1)
        self.assertEqual(report['counts']['convex_pec_corner'], 3)
        self.assertEqual(report['counts']['tangent_within_tolerance'], 5)

    def test_sphere_axis_and_mixed_joins_are_not_planar_corner_claims(self):
        curves = (LineSegment((0, 0), (.16, 0)), EllipseArc((.08, 0), (.08, .08), 0, math.pi))
        report = classify_curve_joins(CurvedContour(curves, ('axis', 'pec'), 1e-14))
        self.assertEqual(report['counts']['axis_join'], 2)
        self.assertTrue(all(j['vacuum_interior_angle_rad'] is None for j in report['joins']))
        base = self.stepped()
        mixed = CurvedContour(base.curves, ('axis', 'electric_symmetry', 'pec', 'pec', 'pec', 'pec'), 0.)
        self.assertEqual(classify_curve_joins(mixed)['counts']['mixed_boundary_join'], 1)
        for tolerance in (True, 0., float('nan'), math.pi):
            with self.assertRaises(ValueError):
                classify_curve_joins(base, angle_tolerance_rad=tolerance)
