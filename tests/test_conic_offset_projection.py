# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from fractions import Fraction as F
import math
import unittest

from superfish_ng.conics import EllipseArc, HyperbolaArc, LineSegment, rotation_cos_sin
from superfish_ng.conic_offset_projection import conic_offset_projection, project_conic_offset_candidates, _discriminant_numerator
from superfish_ng.polynomial_roots import _value
from superfish_ng.offset_degeneracies import classify_offset_degeneracies


def determinant(matrix):
    matrix = [list(map(F, row)) for row in matrix]; result = F(1)
    for i in range(len(matrix)):
        pivot = next((j for j in range(i, len(matrix)) if matrix[j][i]), None)
        if pivot is None: return F(0)
        if pivot != i: matrix[i], matrix[pivot] = matrix[pivot], matrix[i]; result = -result
        value = matrix[i][i]; result *= value
        for j in range(i+1, len(matrix)):
            factor = matrix[j][i]/value
            for k in range(i, len(matrix)): matrix[j][k] -= factor*matrix[i][k]
    return result


def projection(a, b, d=.25, e=.25, side=1):
    return conic_offset_projection(a, b, first_distance_m=d, second_distance_m=e, side=side)


class ConicOffsetProjectionTests(unittest.TestCase):
    def test_cubic_discriminant_agrees_with_independent_sylvester_determinant(self):
        for c0, c1, c2, c3 in ((-1, 3, 2, -4), (1, 2, 3, -2), (0, -2, 0, 1), (-1, 3, -3, 1)):
            rows = [[c3, c2, c1, c0, 0], [0, c3, c2, c1, c0],
                    [3*c3, 2*c2, c1, 0, 0], [0, 3*c3, 2*c2, c1, 0], [0, 0, 3*c3, 2*c2, c1]]
            rational, radical = _discriminant_numerator(((F(c1),), (F(0),)), ((F(c2),), (F(0),)),
                                                         F(c0), F(c3), (F(1),), (F(2),))
            self.assertEqual(rational, (-determinant(rows)/c3,)); self.assertEqual(radical, (F(0),))

    def test_known_offset_tangencies_cusp_and_nonvertex_rational_sources(self):
        a = EllipseArc((0, 0), (2, 1), -.5, 1.)
        for b, d, e in ((EllipseArc((.5, 0), (1.5, .75), -.5, 1.), .25, .25),
                        (HyperbolaArc((.5, 0), (1, .75), -.5, .5), .25, -.25),
                        (EllipseArc((0, 0), (1.75, .75), -.5, 1.), .5, .25)):
            p = projection(a, b, d, e)
            self.assertFalse(p['identically_zero']); self.assertEqual(_value(p['equation'], F(0)), 0)
            self.assertEqual(_value(p['discriminant_rational'], F(0))+_value(p['discriminant_radical'], F(0)), 0)
            changed = projection(a, b, d, math.nextafter(e, math.inf))
            self.assertNotEqual(_value(changed['equation'], F(0)), 0)
        a = EllipseArc((0, 0), (5, 2.5), -3., 6.)
        b = EllipseArc((1.5, 1), (2.5, 1.25), -3., 6.)
        # At q=1/2 both original points are (3,2), and their normals agree.
        self.assertEqual(_value(projection(a, b)['equation'], F(1, 2)), 0)

    def test_binary_rotations_and_scale_keep_exact_known_root_and_orientation(self):
        for unit in (2.**-40, 1., 2.**40):
            for rotation in (0., .3):
                c, s = rotation_cos_sin(rotation)
                a = EllipseArc((0, 0), (2*unit, unit), -.5, 1., rotation)
                b = EllipseArc((c*unit, s*unit), (unit, .75*unit), -.5, 1., rotation)
                base = projection(a, b, .25*unit, .25*unit)
                self.assertEqual(_value(base['equation'], F(0)), 0)
                reverse = projection(replace(a, start_rad=.5, sweep_rad=-1.), b, -.25*unit, .25*unit)
                self.assertEqual(base['equation'], reverse['equation'])
                self.assertEqual(base['equation'], projection(a, b, .25*unit, -.25*unit)['equation'])
                self.assertEqual(_value(projection(b, a, .25*unit, .25*unit)['equation'], F(0)), 0)

    def test_identity_and_target_sign_are_not_complete_intersections(self):
        a = EllipseArc((0, 0), (2, 1), -3., 6.)
        p = projection(a, a)
        self.assertTrue(p['identically_zero']); self.assertIsNone(p['degree'])
        result = project_conic_offset_candidates(a, a, first_distance_m=.25, second_distance_m=.25)
        self.assertFalse(result['projection_complete']); self.assertTrue(result['unresolved'])
        self.assertFalse(result['target_incidence_certified'])
        # Current diagnosis stays on its accepted version 11 path.
        self.assertTrue(classify_offset_degeneracies(a, a, first_distance_m=.25, second_distance_m=.25)['infinite_parameter_pairs'])

    def test_symmetric_offsets_retain_four_true_points_and_extra_candidates(self):
        a = EllipseArc((0, 0), (2, 1), -3., 6.); b = replace(a, semiaxes_m=(1, 2))
        result = project_conic_offset_candidates(a, b, first_distance_m=.25, second_distance_m=.25)
        self.assertTrue(result['projection_complete']); self.assertFalse(result['target_incidence_certified'])
        self.assertEqual(len(result['source_candidates']), 8)
        diagonal = []
        for row in result['source_candidates']:
            x, y = [float(sum(box)/2) for box in row['center_box_zr_m']]
            if abs(abs(x)-abs(y)) < 1e-12: diagonal.append((x > 0, y > 0))
            self.assertEqual(row['original_pencil_discriminant_sign'], 0)
            self.assertEqual(row['source_regularity'], 'REGULAR')
        self.assertEqual(set(diagonal), {(True, True), (False, True), (False, False), (True, False)})
        self.assertTrue(any('opposite source radical' in row['reason'] for row in result['excluded']))

    def test_cusp_membership_budgets_and_strict_inputs(self):
        a = EllipseArc((0, 0), (2, 1), -.5, 1.); b = replace(a, semiaxes_m=(1.75, .75))
        result = project_conic_offset_candidates(a, b, first_distance_m=.5, second_distance_m=.25)
        self.assertTrue(result['projection_complete'])
        cusp = next(row for row in result['source_candidates'] if row['rational_parameter_interval'] == (0, 0))
        self.assertEqual(cusp['source_regularity'], 'CUSP')
        self.assertEqual(cusp['center_box_zr_m'], ((F(3, 2), F(3, 2)), (F(0), F(0))))
        wide = replace(a, start_rad=-3., sweep_rad=6.)
        for settings in ({'max_root_boxes': 1}, {'max_refinements': 1}, {'max_series_terms': 1}):
            result = project_conic_offset_candidates(wide, replace(wide, semiaxes_m=(1, 2)),
                        first_distance_m=.25, second_distance_m=.25, **settings)
            self.assertFalse(result['projection_complete']); self.assertTrue(result['unresolved'])
        for settings in ({'side': True}, {'side': 0}, {'d': 0}, {'e': 0}, {'d': float('nan')}):
            with self.assertRaises(ValueError): projection(a, b, **settings)
        with self.assertRaises(ValueError): projection(LineSegment((0, 0), (1, 1)), b)
        for interval in ((0, 2), (1, 0), (0,), (True, 1)):
            with self.assertRaises(ValueError): project_conic_offset_candidates(a, b, first_distance_m=.5, second_distance_m=.25, first_interval=interval)


if __name__ == '__main__': unittest.main()
