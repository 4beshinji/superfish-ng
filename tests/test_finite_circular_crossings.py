# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import itertools
import json
import math
from pathlib import Path
import tempfile
import unittest

from superfish_ng.conics import EllipseArc, LineSegment, curve_from_dict
from superfish_ng.offset_degeneracies import _classify_offset_degeneracies_v8 as classify_offset_degeneracies


class FiniteCircularCrossingTests(unittest.TestCase):
    def diagnose(self, a, b, d=0, e=0, **controls):
        return classify_offset_degeneracies(a, b, first_distance_m=d, second_distance_m=e, **controls)

    def assert_count(self, result, count):
        self.assertTrue(result['finite_domain_complete'], result['reason'])
        self.assertEqual(result['finite_center_count'], count)
        self.assertFalse(result['infinite_parameter_pairs'])

    def test_original_circle_and_line_equations_hold_for_every_algebraic_center(self):
        a = EllipseArc((0, 0), (2, 2), -2., 4.)
        b = replace(a, center_zr_m=(2, 0), start_rad=1.)
        line = LineSegment((1, -3), (1, 3))
        for pair, centers in (((a, b), ((0, 0), (2, 0))), ((a, line), ((0, 0),))):
            result = self.diagnose(*pair)
            self.assert_count(result, 2)
            for row in result['evidence']['candidates']:
                p, v, q = row['base_zr_m'], row['coefficient_zr_m'], row['radicand']
                for center in centers:
                    delta = tuple(x-y for x, y in zip(p, center))
                    self.assertEqual(sum(x*x for x in delta) + q*sum(x*x for x in v), 4)
                    self.assertEqual(sum(x*y for x, y in zip(delta, v)), 0)
                lo, hi = row['root_bounds']
                self.assertLessEqual(lo*lo, q)
                self.assertGreaterEqual(hi*hi, q)
                if line in pair:
                    self.assertEqual(p[0], 1)
                    self.assertEqual(v[0], 0)

    def test_exact_arc_endpoints_partial_domains_and_non_dyadic_rational_roots(self):
        a = EllipseArc((0, 0), (6, 6), 0., 2.)
        b = EllipseArc((5, 4), (5, 5), 0., 5., -math.pi/2)
        result = self.diagnose(a, b, 1, 1)
        self.assert_count(result, 2)
        rows = result['evidence']['candidates']
        endpoint = next(row for row in rows if row['membership'][0]['status'] == 'START')
        self.assertEqual(endpoint['membership'][1]['status'], 'START')
        self.assertEqual(endpoint['center_box_zr_m'], ((F(5), F(5)), (F(0), F(0))))
        self.assertEqual(endpoint['root_bounds'], (F(20, 41), F(20, 41)))
        self.assert_count(self.diagnose(a, b, 1, 1, first_interval=(0, .1)), 1)
        self.assert_count(self.diagnose(a, b, 1, 1, first_interval=(.1, .2)), 0)
        reverse = replace(a, start_rad=2., sweep_rad=-2.)
        result = self.diagnose(reverse, b, -1, 1)
        self.assert_count(result, 2)
        self.assertIn('END', [row['membership'][0]['status'] for row in result['evidence']['candidates']])

    def test_transverse_line_endpoints_and_explicit_extended_domains(self):
        a = LineSegment((0, 0), (1, 0))
        b = LineSegment((1, 0), (1, 1))
        result = self.diagnose(a, b)
        self.assert_count(result, 1)
        self.assertEqual([row['status'] for row in result['evidence']['candidates'][0]['membership']], ['END', 'START'])
        self.assert_count(self.diagnose(a, b, first_interval=(0, .5)), 0)
        b = LineSegment((2, 0), (2, 1))
        self.assert_count(self.diagnose(a, b), 0)
        self.assert_count(self.diagnose(a, b, first_interval=(0, 3)), 1)
        # No irrational length is needed for a zero-distance straight offset.
        self.assert_count(self.diagnose(LineSegment((0, 0), (1, 1)), LineSegment((0, 1), (1, 0))), 1)

    def test_one_ulp_inside_tangency_has_two_distinct_centers(self):
        a = EllipseArc((0, 0), (2, 2), -.5, 1.)
        b = replace(a, center_zr_m=(2, 0), rotation_rad=math.pi)
        for separation, count in ((math.nextafter(2., 0.), 2), (2., 1), (math.nextafter(2., math.inf), 0)):
            self.assert_count(self.diagnose(a, replace(b, center_zr_m=(separation, 0)), 1, 1), count)
        for position, count in ((math.nextafter(1., 0.), 2), (1., 1), (math.nextafter(1., math.inf), 0)):
            self.assert_count(self.diagnose(a, LineSegment((position, -1), (position, 1)), 1, 0), count)

    def test_exchange_reverse_quarter_rotation_translation_and_extreme_scale(self):
        for scale, angle, reverse, exchange in itertools.product((2.**-200, 1., 2.**200), (0., math.pi/2), (False, True), (False, True)):
            center = (3*scale, 4*scale)
            delta = (2*scale, 0) if angle == 0 else (0, 2*scale)
            a = EllipseArc(center, (3*scale, 3*scale), -2., 4., angle)
            b = replace(a, center_zr_m=tuple(x+y for x, y in zip(center, delta)), start_rad=1.)
            distances = [scale, scale]
            if reverse:
                b = replace(b, start_rad=5., sweep_rad=-4.)
                distances[1] *= -1
            curves = [a, b]
            if exchange:
                curves.reverse(); distances.reverse()
            self.assert_count(self.diagnose(*curves, *distances), 2)
        a = EllipseArc((0, 0), (2, 2), -2., 4.)
        b = replace(a, center_zr_m=(2, 0), start_rad=1.)
        # Negative signed radii reverse the local direction, not the locus.
        a = replace(a, start_rad=1.)
        b = replace(b, start_rad=-2.)
        self.assert_count(self.diagnose(a, b, 4, 4), 2)

    def test_budget_exclusion_unknown_supports_and_strict_controls(self):
        a = EllipseArc((0, 0), (2, 2), -2., 4.)
        b = replace(a, center_zr_m=(2, 0), start_rad=1.)
        result = self.diagnose(a, b, max_series_terms=1)
        self.assertFalse(result['finite_domain_complete'])
        self.assertIsNone(result['finite_center_count'])
        self.assertEqual(result['evidence']['supporting_center_count'], 2)
        # An excluded line fraction suffices even if arc membership exhausts its budget.
        self.assert_count(self.diagnose(a, LineSegment((1, 3), (1, 4)), max_series_terms=1), 0)
        self.assert_count(self.diagnose(a, replace(b, rotation_rad=.3)), 2)
        self.assertFalse(self.diagnose(a, replace(b, semiaxes_m=(2, 1)))['finite_domain_complete'])
        for controls in ({'first_interval':(-1, 1)}, {'endpoint_width':0}, {'max_series_terms':True}, {'first_interval':(0, True)}):
            with self.assertRaises(ValueError): self.diagnose(a, b, **controls)

    def test_saved_version_four_replay_and_current_cli_gui_keep_construction(self):
        from superfish_ng.construction_diagnostics import diagnose_construction, replay_construction_diagnosis
        from superfish_ng.gui import tangent_document
        from superfish_ng.cli import main
        fixture = Path(__file__).parent/'fixtures/offset_diagnosis_v4_circular_crossings.json'
        original = fixture.read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            for index, old in enumerate(json.loads(original)):
                self.assertEqual(old['schema_version'], 4)
                self.assertFalse(old['diagnosis']['finite_domain_complete'])
                self.assertEqual(replay_construction_diagnosis(old), old)
                new = diagnose_construction(old['construction'])
                self.assertEqual(new['schema_version'], 9)
                self.assertTrue(new['diagnosis']['finite_domain_complete'])
                self.assertEqual(new['construction'], old['construction'])
                self.assertEqual(replay_construction_diagnosis(new), new)
                response = tangent_document(new, replay=True)
                self.assertEqual(response['offset_diagnosis'], new)
                self.assertEqual(json.loads(response['serialized']), old['construction'])
                for document in (old, new):
                    source = Path(temporary)/f'{index}-{document["schema_version"]}.json'
                    target = source.with_suffix('.replayed.json')
                    source.write_text(json.dumps(document, indent=2)+'\n')
                    code = 1 if document['diagnosis']['status'] == 'UNVERIFIED' else 0
                    self.assertEqual(main(['diagnose-construction', str(source), '--out', str(target)]), code)
                    self.assertEqual(source.read_bytes(), target.read_bytes())
                for key, value in (('finite_center_count', 17), ('finite_domain_complete', False)):
                    changed = deepcopy(new); changed['diagnosis'][key] = value
                    with self.assertRaises(ValueError): replay_construction_diagnosis(changed)
                changed = deepcopy(new); changed['schema_version'] = 4
                with self.assertRaises(ValueError): replay_construction_diagnosis(changed)
        self.assertEqual(fixture.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
