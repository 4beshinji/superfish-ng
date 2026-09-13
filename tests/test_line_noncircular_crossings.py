# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from copy import deepcopy
from fractions import Fraction as F
import json
import math
from pathlib import Path
import tempfile
import unittest
from superfish_ng.conics import EllipseArc, HyperbolaArc, LineSegment
from superfish_ng.line_noncircular_crossings import classify_line_noncircular_crossings


class LineNoncircularCrossingTests(unittest.TestCase):
    def diagnose(self, curve, line, distance=0., line_distance=None, **controls):
        return classify_line_noncircular_crossings((curve, line), (distance, distance if line_distance is None else line_distance),
            controls.pop('domains', ((0, 1), (0, 1))), endpoint_width=F(1, 2**100),
            max_series_terms=controls.pop('max_series_terms', 96), **controls)

    def assert_count(self, report, count):
        self.assertTrue(report['complete'], report['evidence']['unresolved'])
        self.assertEqual(report['centers'], count)

    def test_axis_crossings_and_chart_boundaries_are_counted_once(self):
        ellipse = EllipseArc((0, 0), (2, 1), -3., 6.)
        result = self.diagnose(ellipse, LineSegment((0, -3), (0, 3)))
        self.assert_count(result, 2)
        self.assertEqual({r['center_box_zr_m'] for r in result['evidence']['intersections']},
                         {((F(0), F(0)), (F(-1), F(-1))), ((F(0), F(0)), (F(1), F(1)))})
        self.assertEqual(sum(r['reason'] == 'duplicate source at chart boundary' for r in result['evidence']['excluded']), 2)
        hyperbola = HyperbolaArc((0, 0), (2, 1), -2., 2.)
        self.assert_count(self.diagnose(hyperbola, LineSegment((3, -3), (3, 3))), 2)

    def test_same_center_contacts_and_another_crossing_remain_distinct(self):
        curve = EllipseArc((0, 0), (2, 1), -.1, 3.4)
        report = self.diagnose(curve, LineSegment((2, -2), (2, 2)), 2.)
        self.assert_count(report, 2)
        self.assertEqual(sorted(map(len, report['evidence']['same_center_groups'])), [1, 2])
        self.assertEqual(len(report['evidence']['intersections']), 3)
        self.assertEqual({r['contact_kind'] for r in report['evidence']['intersections']}, {'TRANSVERSE', 'REGULAR_TANGENCY'})

    def test_cusps_with_nonparallel_source_tangents_are_retained(self):
        cases = ((EllipseArc((0, 0), (2, 1), 0., 3.), LineSegment((-5, -8), (5, 2)), 4., (0, -3)),
                 (HyperbolaArc((0, 0), (2, 1), -2., 2.), LineSegment((.5, -2), (4.5, 2)), -.5, (2.5, 0)))
        for curve, line, distance, center in cases:
            report = self.diagnose(curve, line, distance, 0.)
            self.assertTrue(report['complete'], report['evidence']['unresolved'])
            cusps = [r for r in report['evidence']['intersections'] if r['contact_kind'] == 'CUSP']
            self.assertEqual(len(cusps), 1)
            self.assertNotEqual(cusps[0]['source_projection_derivative_sign'], 0)
            self.assertEqual(cusps[0]['center_box_zr_m'], tuple((F(x), F(x)) for x in center))

    def test_exact_line_arc_endpoints_and_one_ulp_near_tangency(self):
        curve = EllipseArc((0, 0), (2, 1), 0., 1.)
        line = LineSegment((2, 0), (3, 1))
        result = self.diagnose(curve, line)
        self.assert_count(result, 1)
        self.assertEqual([m['status'] for m in result['evidence']['intersections'][0]['membership']], ['START', 'START'])
        for domains in (((.1, 1), (0, 1)), ((0, 1), (.1, 1))):
            self.assert_count(self.diagnose(curve, line, domains=domains), 0)
        curve = replace(curve, start_rad=-1., sweep_rad=2.)
        for x, count in ((math.nextafter(2., math.inf), 0), (2., 1), (math.nextafter(2., -math.inf), 2)):
            self.assert_count(self.diagnose(curve, LineSegment((x, -2), (x, 2))), count)

    def test_binary_rotation_irrational_length_and_extraneous_root_signs(self):
        curve = EllipseArc((0, 0), (2, 1), -3., 6., .3)
        result = self.diagnose(curve, LineSegment((0, -3), (1, 3)), .25)
        self.assert_count(result, 2)
        self.assertTrue(all(len(r['polynomial']) == 17 for r in result['evidence']['charts']))
        extraneous = [r for r in result['evidence']['excluded'] if 'extraneous' in r['reason']]
        self.assertGreater(len(extraneous), 0)
        self.assertTrue(all(r['squared_incidence_sign'] != 0 or r['original_side_signs'][0] != -r['original_side_signs'][1] for r in extraneous))

    def test_both_branches_orientation_scale_and_exchange(self):
        for branch in (-1, 1):
            for scale in (2.**-100, 1., 2.**100):
                curve = HyperbolaArc((0, 0), (2*scale, scale), -2., 2., branch=branch)
                line = LineSegment((3*branch*scale, -3*scale), (3*branch*scale, 3*scale))
                for reverse in (False, True):
                    arc = replace(curve, start_parameter=2., end_parameter=-2.) if reverse else curve
                    self.assert_count(self.diagnose(arc, line, -.25*branch*scale*(-1 if reverse else 1), -.25*branch*scale), 2)
                    report = classify_line_noncircular_crossings((line, arc), (-.25*branch*scale, -.25*branch*scale*(-1 if reverse else 1)),
                        ((0, 1), (0, 1)), endpoint_width=F(1, 2**100), max_series_terms=96)
                    self.assert_count(report, 2)

    def test_exhausted_budgets_preserve_unfinished_roots(self):
        curve = EllipseArc((0, 0), (2, 1), -3., 6.)
        line = LineSegment((1, -3), (1, 3))
        for controls in ({'max_root_boxes': 1}, {'max_refinements': 1}, {'max_series_terms': 1}):
            result = self.diagnose(curve, line, .25, **controls)
            self.assertFalse(result['complete']); self.assertIsNone(result['centers'])
            self.assertTrue(result['evidence']['unresolved'])

    def test_public_schema_eight_and_saved_seven_keep_original_construction(self):
        from superfish_ng.construction_diagnostics import _from_replayed_construction, replay_construction_diagnosis
        from superfish_ng.gui import tangent_document
        from superfish_ng.cli import main
        fixture = Path(__file__).parent/'fixtures/offset_diagnosis_v7_line_crossings.json'
        raw = fixture.read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            for i, old in enumerate(json.loads(raw)):
                self.assertEqual(old['schema_version'], 7)
                self.assertEqual(old['diagnosis']['classification'], 'TANGENCY_WITNESSES')
                self.assertEqual(replay_construction_diagnosis(old), old)
                current = _from_replayed_construction(old['construction'], schema_version=8)
                self.assertEqual(current['schema_version'], 8)
                self.assertTrue(current['diagnosis']['finite_domain_complete'])
                self.assertEqual(current['diagnosis']['finite_center_count'], 2 if i == 3 else 1)
                self.assertEqual(current['construction'], old['construction'])
                for document in (old, current):
                    self.assertEqual(tangent_document(document, replay=True)['offset_diagnosis'], document)
                    source = Path(temporary)/f'{i}-{document["schema_version"]}.json'
                    output = source.with_suffix('.replayed.json')
                    source.write_text(json.dumps(document, indent=2)+'\n')
                    self.assertEqual(main(['diagnose-construction', str(source), '--out', str(output)]), 0)
                    self.assertEqual(source.read_bytes(), output.read_bytes())
                changed = deepcopy(current); changed['schema_version'] = 7
                with self.assertRaises(ValueError): replay_construction_diagnosis(changed)
        self.assertEqual(fixture.read_bytes(), raw)

    def test_public_request_and_unknown_controls_stay_strict(self):
        from superfish_ng.conics import curve_to_dict
        from superfish_ng.offset_degeneracies import diagnose_offsets_document
        request = dict(schema_version=1,
                       curves=[curve_to_dict(EllipseArc((0, 0), (2, 1), -3., 6.)), curve_to_dict(LineSegment((0, -3), (0, 3)))],
                       controls=dict(first_distance_m=0., second_distance_m=0.))
        report = diagnose_offsets_document(request)
        self.assertEqual(report['schema_version'], 9)
        self.assertEqual(report['diagnosis']['finite_center_count'], 2)
        for key, value in (('endpoint_width', 0), ('max_series_terms', True), ('unknown_control', 2)):
            changed = deepcopy(request); changed['controls'][key] = value
            with self.assertRaises(ValueError): diagnose_offsets_document(changed)

    def test_public_exhaustion_retains_previously_certified_contact_witness(self):
        from superfish_ng.offset_degeneracies import classify_offset_degeneracies
        result = classify_offset_degeneracies(EllipseArc((0, 0), (2, 1), 0., .5), LineSegment((2, -2), (2, 2)),
            first_distance_m=1., second_distance_m=1., endpoint_width=F(1, 2**600))
        self.assertEqual(result['classification'], 'TANGENCY_WITNESSES')
        self.assertFalse(result['finite_domain_complete'])
        self.assertIsNone(result['finite_center_count'])
        self.assertEqual(result['evidence']['tangency_witness_center_count'], 1)
        self.assertTrue(result['evidence']['general_crossing_search']['unresolved'])


if __name__ == '__main__': unittest.main()
