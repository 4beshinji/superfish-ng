# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import math
import unittest
import numpy as np
from superfish_ng.conics import EllipseArc, HyperbolaArc
from superfish_ng.arc_tangents import finite_arc_tangents


class FiniteArcTangentTests(unittest.TestCase):
    def circle(self, centre, start=0., sweep=math.pi):
        return EllipseArc(centre, (1., 1.), start, sweep)

    def test_upper_semicircles_keep_only_upper_support(self):
        first, second = self.circle((0, 0)), self.circle((4, 0))
        result = finite_arc_tangents(first, second)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(len(result['candidates']), 1)
        item = result['candidates'][0]
        np.testing.assert_allclose(item['contacts_zr_m'], [[0, 1], [4, 1]], atol=1e-12)
        np.testing.assert_allclose(item['contact_fractions'], [.5, .5], atol=1e-12)
        self.assertEqual(item['connection_direction'], 'OPPOSED')
        self.assertEqual(result['supporting_result']['arc_filter_status'], 'NOT_APPLIED')

    def test_reversing_both_arcs_preserves_contacts_and_changes_direction(self):
        first = self.circle((0, 0), math.pi, -math.pi)
        second = replace(first, center_zr_m=(4, 0))
        result = finite_arc_tangents(first, second)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(len(result['candidates']), 1)
        self.assertEqual(result['candidates'][0]['connection_direction'], 'FORWARD')
        second = replace(second, start_rad=0., sweep_rad=math.pi)
        mixed = finite_arc_tangents(first, second)
        self.assertEqual(mixed['candidates'][0]['connection_direction'], 'OPPOSED')

    def test_periodic_seam_and_scale_rotation_invariance(self):
        for scale in (1e-5, 1., 1e5):
            angle = .37
            c, s = math.cos(angle), math.sin(angle)
            rotation = np.array([[c, -s], [s, c]])
            centre = np.array([2., 3.])*scale
            first = EllipseArc(tuple(map(float, centre)), (scale, scale),
                               -3*math.pi/4, -math.pi/2, angle)
            second = replace(first, center_zr_m=tuple(map(float, centre+rotation@[0., 4*scale])))
            result = finite_arc_tangents(first, second)
            self.assertEqual(result['status'], 'PASS')
            self.assertEqual(len(result['candidates']), 1)
            item = result['candidates'][0]
            np.testing.assert_allclose(item['contact_fractions'], [.5, .5], atol=1e-10)
            self.assertEqual(item['connection_direction'], 'FORWARD')

    def test_hyperbola_branches_and_finite_interval(self):
        # x^2-y^2=1 and x^2-(y-4)^2=1 share vertical tangents x=+/-1.
        first = HyperbolaArc((0, 0), (1, 1), -1, 1)
        second = replace(first, center_zr_m=(0, 4))
        for branch in (-1, 1):
            a, b = replace(first, branch=branch), replace(second, branch=branch)
            result = finite_arc_tangents(a, b)
            self.assertEqual(result['status'], 'PASS')
            self.assertEqual(len(result['candidates']), 1)
            np.testing.assert_allclose(result['candidates'][0]['contacts_zr_m'],
                                       [[branch, 0], [branch, 4]], atol=1e-12)
            self.assertEqual(result['candidates'][0]['connection_direction'], 'FORWARD')
        mixed = finite_arc_tangents(first, replace(second, branch=-1))
        self.assertEqual(mixed['status'], 'PASS')
        self.assertEqual(len(mixed['candidates']), 1)
        np.testing.assert_allclose(mixed['candidates'][0]['contacts_zr_m'],
                                   [[math.sqrt(1.25), -.5], [-math.sqrt(1.25), 4.5]], atol=1e-12)
        short = finite_arc_tangents(replace(first, start_parameter=.1), second)
        self.assertEqual(short['status'], 'PASS')
        self.assertFalse(short['candidates'])

    def test_endpoint_and_near_endpoint_are_unverified_without_snapping(self):
        for offset in (0., -1e-12, 1e-12):
            first = self.circle((0, 0), math.pi/2+offset, math.pi/4)
            result = finite_arc_tangents(first, self.circle((4, 0)))
            self.assertEqual(result['status'], 'UNVERIFIED')
            self.assertFalse(result['candidates'])
            self.assertTrue(any('endpoint' in x['reason'] for x in result['unresolved']))

    def test_zero_length_contact_and_unfinished_search_remain_visible(self):
        a = self.circle((0, 0), -.5, 1.)
        b = self.circle((2, 0), math.pi-.5, 1.)
        result = finite_arc_tangents(a, b)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(len(result['candidates']), 1)
        self.assertEqual(result['candidates'][0]['connection_direction'], 'ZERO_LENGTH')
        for b, kwargs in ((a, {}), (self.circle((4, 0)), {'max_boxes': 1})):
            result = finite_arc_tangents(a, b, **kwargs)
            self.assertEqual(result['status'], 'UNVERIFIED')
            self.assertTrue(result['unresolved'])

    def test_controls_are_strict(self):
        a, b = self.circle((0, 0)), self.circle((4, 0))
        for key in ('parameter_guard', 'position_tolerance_m', 'angle_tolerance_rad'):
            for value in (True, 0., -1., math.inf, math.nan):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    finite_arc_tangents(a, b, **{key: value})
        with self.assertRaises(ValueError):
            finite_arc_tangents(None, b)

    def test_explicit_trim_preserves_curves_and_checks_both_g1_joins(self):
        from superfish_ng.arc_tangents import connect_finite_arcs
        from superfish_ng.conics import check_curve_join
        first = self.circle((0, 0), math.pi, -math.pi)
        second = replace(first, center_zr_m=(4, 0))
        originals = (first, second)
        result = connect_finite_arcs(first, second, candidate_index=0,
                                     position_tolerance_m=1e-9, angle_tolerance_rad=1e-8)
        left, line, right = result['curves']
        self.assertEqual((first, second), originals)
        self.assertEqual(left.center_zr_m, first.center_zr_m)
        self.assertEqual(right.semiaxes_m, second.semiaxes_m)
        self.assertAlmostEqual(left.sweep_rad, -math.pi/2)
        self.assertAlmostEqual(right.start_rad, math.pi/2)
        np.testing.assert_allclose(left.evaluate(0)['points_zr_m'], first.evaluate(0)['points_zr_m'])
        np.testing.assert_allclose(right.evaluate(1)['points_zr_m'], second.evaluate(1)['points_zr_m'])
        for a, b in ((left, line), (line, right)):
            check_curve_join(a, b, position_tolerance_m=1e-9, angle_tolerance_rad=1e-8,
                             require_tangent=True)

    def test_trim_hyperbolas_and_refuse_unsafe_selection(self):
        from superfish_ng.arc_tangents import connect_finite_arcs
        a = HyperbolaArc((0, 0), (1, 1), -1, 1)
        b = replace(a, center_zr_m=(0, 4))
        result = connect_finite_arcs(a, b, candidate_index=0,
                                     position_tolerance_m=1e-9, angle_tolerance_rad=1e-8)
        self.assertAlmostEqual(result['curves'][0].end_parameter, 0.)
        self.assertAlmostEqual(result['curves'][2].start_parameter, 0.)
        upper = self.circle((0, 0))
        for first, second, index, kwargs in (
            (upper, self.circle((4, 0)), 0, {}),
            (a, b, -1, {}), (a, b, True, {}), (a, b, 99, {}),
            (a, a, 0, {}), (a, b, 0, {'max_boxes': 1}),
            (self.circle((0, 0), -.5, 1.), self.circle((2, 0), math.pi-.5, 1.), 0, {}),
        ):
            with self.subTest(index=index, kwargs=kwargs), self.assertRaises(ValueError):
                connect_finite_arcs(first, second, candidate_index=index,
                                    position_tolerance_m=1e-9, angle_tolerance_rad=1e-8, **kwargs)
