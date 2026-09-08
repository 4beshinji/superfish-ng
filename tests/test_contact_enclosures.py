# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from fractions import Fraction as F
import math
import unittest
from superfish_ng.conics import EllipseArc, HyperbolaArc
from superfish_ng.contact_enclosures import supporting_contact_enclosures


def contains_signed_sqrt(test, box, square, sign):
    lo, hi = box if sign > 0 else (-box[1], -box[0])
    test.assertLessEqual(lo*lo if lo > 0 else F(0), square)
    test.assertGreaterEqual(hi, 0)
    test.assertGreaterEqual(hi*hi, square)


class ContactEnclosureTests(unittest.TestCase):
    def circle(self, center):
        return EllipseArc(center, (1, 1), 0, math.pi)

    def test_known_inner_and_outer_circle_contacts_are_enclosed(self):
        result = supporting_contact_enclosures(self.circle((0, 0)), self.circle((4, 0)))
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(len(result['contacts']), 4)
        for item in result['contacts']:
            p, q = item['contact_boxes_zr_m']
            point = item['candidate']['contacts_zr_m'][0]
            if abs(point[0]) < 1e-10:
                self.assertEqual(p[0], (F(0), F(0)))
                self.assertEqual(q[0], (F(4), F(4)))
                self.assertEqual(p[1], (F(round(point[1])),)*2)
            else:
                self.assertLessEqual(p[0][0], F(1, 2)); self.assertGreaterEqual(p[0][1], F(1, 2))
                self.assertLessEqual(q[0][0], F(7, 2)); self.assertGreaterEqual(q[0][1], F(7, 2))
                sign = 1 if point[1] > 0 else -1
                contains_signed_sqrt(self, p[1], F(3, 4), sign)
                contains_signed_sqrt(self, q[1], F(3, 4), -sign)
            self.assertLess(max(item['returned_point_error_bounds_m']), 1e-10)

    def test_concentric_ellipses_keep_two_irrational_offsets(self):
        a = EllipseArc((0, 0), (2, 1), 0, math.pi)
        b = replace(a, semiaxes_m=(1, 2))
        result = supporting_contact_enclosures(a, b)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(len(result['contacts']), 4)
        for item in result['contacts']:
            for box, point, squares in zip(item['contact_boxes_zr_m'], item['candidate']['contacts_zr_m'],
                                           ((F(16, 5), F(1, 5)), (F(1, 5), F(16, 5)))):
                for interval, coordinate, square in zip(box, point, squares):
                    contains_signed_sqrt(self, interval, square, 1 if coordinate > 0 else -1)

    def test_root_width_reduction_reduces_contact_boxes(self):
        a, b = self.circle((0, 0)), self.circle((4, 0))
        coarse = supporting_contact_enclosures(a, b, normal_width=F(1, 2**34), residual_tolerance=1e-6,
                                               max_contact_width_m=1.)
        fine = supporting_contact_enclosures(a, b, normal_width=F(1, 2**48))
        self.assertEqual(coarse['status'], 'PASS'); self.assertEqual(fine['status'], 'PASS')
        width = lambda r: max(float(hi-lo) for item in r['contacts'] for box in item['contact_boxes_zr_m'] for lo, hi in box)
        self.assertLess(width(fine), width(coarse)/1000)
        tight = supporting_contact_enclosures(a, b, max_contact_width_m=1e-30)
        self.assertEqual(tight['status'], 'UNVERIFIED')
        self.assertTrue(any(item['width_status'] == 'UNVERIFIED' for item in tight['contacts']))

    def test_hyperbola_known_cross_branch_contacts(self):
        a = HyperbolaArc((0, 0), (1, 1), -1, 1)
        result = supporting_contact_enclosures(a, replace(a, center_zr_m=(0, 4)))
        self.assertEqual(result['status'], 'PASS')
        for item in result['contacts']:
            for box, point, center in zip(item['contact_boxes_zr_m'], item['candidate']['contacts_zr_m'], (0, 4)):
                if abs(abs(point[0])-1) < 1e-10:
                    self.assertEqual(box[0], (F(round(point[0])),)*2)
                else:
                    contains_signed_sqrt(self, box[0], F(5, 4), 1 if point[0] > 0 else -1)
                    expected = F(-1, 2) if center == 0 else F(9, 2)
                    self.assertLessEqual(box[1][0], expected); self.assertGreaterEqual(box[1][1], expected)

    def test_unfinished_roots_coincidence_and_invalid_width(self):
        a, b = self.circle((0, 0)), self.circle((4, 0))
        for second, controls in ((a, {}), (b, {'max_boxes': 1})):
            result = supporting_contact_enclosures(a, second, **controls)
            self.assertEqual(result['status'], 'UNVERIFIED')
            self.assertTrue(result['unresolved'])
        for width in (True, 0, -1, math.inf, math.nan):
            with self.assertRaises(ValueError): supporting_contact_enclosures(a, b, max_contact_width_m=width)

    def test_exact_cardinal_rotation_translation_and_scale(self):
        # R(pi/2)(x,y)=(-y,x) is exact in the supporting-conic convention.
        for scale in (2.**-20, 1., 2.**20):
            center = (32*scale, 64*scale)
            first = EllipseArc(center, (scale, scale), 0., math.pi, math.pi/2)
            second = replace(first, center_zr_m=(center[0], center[1]+4*scale))
            result = supporting_contact_enclosures(first, second, max_contact_width_m=1e-9*scale)
            self.assertEqual(result['status'], 'PASS')
            for item in result['contacts']:
                transformed = []
                for box in item['contact_boxes_zr_m']:
                    z, r = box
                    transformed.append(((r[0]-F(center[1]))/F(scale), (r[1]-F(center[1]))/F(scale),
                                        (F(center[0])-z[1])/F(scale), (F(center[0])-z[0])/F(scale)))
                p, q = transformed
                # Outer tangents have y=+/-1, inner tangents x=1/2 and 7/2.
                if p[0] == p[1] == 0:
                    self.assertEqual(q[:2], (F(4), F(4)))
                    self.assertEqual(p[2], p[3]); self.assertEqual(abs(p[2]), 1)
                else:
                    self.assertLessEqual(p[0], F(1, 2)); self.assertGreaterEqual(p[1], F(1, 2))
                    self.assertLessEqual(q[0], F(7, 2)); self.assertGreaterEqual(q[1], F(7, 2))
                    contains_signed_sqrt(self, p[2:], F(3, 4), 1 if p[2] > 0 else -1)

    def test_contact_roundoff_bound_contains_independent_reference_error(self):
        a = EllipseArc((0, 0), (2, 1), 0, math.pi)
        result = supporting_contact_enclosures(a, replace(a, semiaxes_m=(1, 2)))
        for item in result['contacts']:
            for point, bound, square in zip(item['candidate']['contacts_zr_m'],
                                            item['returned_point_error_bounds_m'], (F(16, 5), F(1, 5))):
                # |x-sqrt(square)| <= bound, checked without rounded sqrt.
                x = abs(F(point[0])); radius = F(bound)
                self.assertLessEqual(max(F(0), x-radius)**2, square)
                self.assertGreaterEqual((x+radius)**2, square)

    def test_hyperbola_branch_is_certified_without_atan_or_asinh(self):
        a = HyperbolaArc((0, 0), (1, 1), -1, 1)
        b = replace(a, center_zr_m=(0, 4))
        positive = supporting_contact_enclosures(a, b)
        negative = supporting_contact_enclosures(replace(a, branch=-1), replace(b, branch=-1))
        for first, second in zip(positive['contacts'], negative['contacts']):
            self.assertEqual(first['contact_boxes_zr_m'], second['contact_boxes_zr_m'])
            self.assertEqual(first['local_contact_boxes'], second['local_contact_boxes'])
            for x, y in zip(first['specified_branch_status'], second['specified_branch_status']):
                self.assertEqual({x, y}, {'MATCHES', 'OTHER'})
