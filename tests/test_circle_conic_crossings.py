# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import json
import math
from pathlib import Path
import tempfile
import unittest
from superfish_ng.conics import EllipseArc, HyperbolaArc, curve_to_dict
from superfish_ng.circle_conic_crossings import classify_circle_conic_crossings


class CircleConicCrossingTests(unittest.TestCase):
    def classify(self, curve, circle, distance=0., circle_distance=0., **controls):
        return classify_circle_conic_crossings((curve, circle), (distance, circle_distance),
            controls.pop('domains', ((0, 1), (0, 1))), endpoint_width=F(1, 2**100),
            max_series_terms=controls.pop('max_series_terms', 96), **controls)

    def assert_count(self, report, count):
        self.assertTrue(report['complete'], report['evidence']['unresolved'])
        self.assertEqual(report['centers'], count)

    def test_independent_centered_ellipse_circle_four_intersections(self):
        result = self.classify(EllipseArc((0, 0), (2, 1), -3., 6.), EllipseArc((0, 0), (1.5, 1.5), -3., 6.))
        self.assert_count(result, 4)
        with localcontext() as context:
            context.prec = 100
            for sx in (-1, 1):
                for sy in (-1, 1):
                    target = (sx*(D(5)/3).sqrt(), sy*(D(7)/12).sqrt())
                    self.assertTrue(any(all(D(lo.numerator)/D(lo.denominator) <= value <= D(hi.numerator)/D(hi.denominator)
                        for (lo, hi), value in zip(row['center_box_zr_m'], target)) for row in result['evidence']['intersections']))
        self.assertEqual({row['contact_kind'] for row in result['evidence']['intersections']}, {'TRANSVERSE'})

    def test_exact_tangency_one_ulp_and_chart_boundaries(self):
        arc = EllipseArc((0, 0), (2, 1), -3., 6.)
        for radius, count in ((math.nextafter(1., 0.), 0), (1., 2), (math.nextafter(1., math.inf), 4)):
            report = self.classify(arc, EllipseArc((0, 0), (radius, radius), -3., 6.))
            self.assert_count(report, count)
            if radius == 1:
                self.assertEqual({r['contact_kind'] for r in report['evidence']['intersections']}, {'REGULAR_TANGENCY'})
                self.assertEqual(len([r for r in report['evidence']['excluded'] if 'duplicate source' in r['reason']]), 2)

    def test_original_endpoint_and_restricted_finite_arcs(self):
        arc = EllipseArc((0, 0), (2, 1), 0., 1.)
        circle = EllipseArc((1, 0), (1, 1), 0., 1.)
        report = self.classify(arc, circle, .25, .25)
        self.assert_count(report, 1)
        self.assertEqual([m['status'] for m in report['evidence']['intersections'][0]['membership']], ['START', 'START'])
        self.assertEqual(report['evidence']['intersections'][0]['center_box_zr_m'], ((F(7, 4), F(7, 4)), (F(0), F(0))))
        for domains in (((.1, 1), (0, 1)), ((0, 1), (.1, 1))):
            self.assert_count(self.classify(arc, circle, .25, .25, domains=domains), 0)
        end = self.classify(replace(arc, start_rad=-1.), replace(circle, start_rad=-1.), .25, .25)
        self.assert_count(end, 1)
        self.assertEqual([m['status'] for m in end['evidence']['intersections'][0]['membership']], ['END', 'END'])

    def test_cusp_and_distinct_source_points_at_one_center(self):
        arc = EllipseArc((0, 0), (2, 1), -.1, 3.4)
        cusp = self.classify(arc, EllipseArc((1.5, -1), (1, 1), -3., 6.), .5)
        self.assertTrue(cusp['complete'], cusp['evidence']['unresolved'])
        row = next(r for r in cusp['evidence']['intersections'] if r['contact_kind'] == 'CUSP')
        self.assertNotEqual(row['source_radial_derivative_sign'], 0)
        self.assertEqual(row['center_box_zr_m'], ((F(3, 2), F(3, 2)), (F(0), F(0))))
        shared = self.classify(arc, EllipseArc((1, 0), (1, 1), -.1, 6.2), 2.)
        self.assertTrue(shared['complete'], shared['evidence']['unresolved'])
        self.assertGreater(len(shared['evidence']['intersections']), shared['centers'])
        self.assertTrue(any(len(g) > 1 for g in shared['evidence']['same_center_groups']))

    def test_collapsed_circle_is_infinite_pairs_only_when_incident(self):
        arc = EllipseArc((0, 0), (2, 1), 0., 1.)
        circle = EllipseArc((2, 0), (1, 1), -.3, 1.)
        report = self.classify(arc, circle, circle_distance=1.)
        self.assert_count(report, 1); self.assertTrue(report['infinite'])
        self.assertEqual(report['classification'], 'INFINITE_PARAMETER_PAIRS')
        self.assertEqual(report['evidence']['intersections'][0]['membership'][1]['status'], 'COLLAPSED')
        disjoint = self.classify(arc, replace(circle, center_zr_m=(3, 0)), circle_distance=1.)
        self.assert_count(disjoint, 0)
        self.assertTrue(disjoint['evidence']['circle_collapsed'])
        outside = self.classify(arc, circle, circle_distance=1., domains=((.1, 1), (0, 1)))
        self.assert_count(outside, 0); self.assertFalse(outside['infinite'])

    def test_hyperbola_both_branches_scale_reverse_and_exchange(self):
        for branch in (-1, 1):
            for unit in (2.**-60, 1., 2.**60):
                arc = HyperbolaArc((0, 0), (2*unit, unit), -2., 2., branch=branch)
                circle = EllipseArc((0, 0), (3*unit, 3*unit), -.1 if branch < 0 else -3., 6.2 if branch < 0 else 6.)
                for reverse in (False, True):
                    a = replace(arc, start_parameter=2., end_parameter=-2.) if reverse else arc
                    c = replace(circle, start_rad=circle.start_rad+circle.sweep_rad, sweep_rad=-circle.sweep_rad) if reverse else circle
                    self.assert_count(self.classify(a, c, -.25*branch*unit*(-1 if reverse else 1), .125*unit*(-1 if reverse else 1)), 2)
                    report = classify_circle_conic_crossings((c, a), (.125*unit*(-1 if reverse else 1), -.25*branch*unit*(-1 if reverse else 1)),
                        ((0, 1), (0, 1)), endpoint_width=F(1, 2**100), max_series_terms=96)
                    self.assert_count(report, 2)

    def test_exhaustion_keeps_evidence_and_rejects_invalid_controls(self):
        arc = EllipseArc((0, 0), (2, 1), -3., 6.); circle = EllipseArc((.125, 0), (1.5, 1.5), -3., 6.)
        for control in ({'max_root_boxes': 1}, {'max_refinements': 1}, {'max_series_terms': 1}):
            report = self.classify(arc, circle, .25, .125, **control)
            self.assertFalse(report['complete']); self.assertIsNone(report['centers'])
            self.assertTrue(report['evidence']['unresolved'])
        for control in ({'max_root_boxes': True}, {'max_refinements': 0}):
            with self.assertRaises(ValueError): self.classify(arc, circle, **control)

    def test_public_nine_and_saved_eight_replay_full_documents(self):
        from superfish_ng.construction_diagnostics import diagnose_construction, replay_construction_diagnosis
        from superfish_ng.offset_degeneracies import diagnose_offsets_document
        from superfish_ng.gui import tangent_document
        from superfish_ng.cli import main
        fixture = Path(__file__).parent/'fixtures/offset_diagnosis_v8_circle_conic.json'; raw = fixture.read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            for i, old in enumerate(json.loads(raw)):
                self.assertEqual(replay_construction_diagnosis(old), old)
                current = diagnose_construction(old['construction'])
                self.assertEqual(current['schema_version'], 12)
                self.assertEqual(current['construction'], old['construction'])
                for doc in (old, current):
                    self.assertEqual(tangent_document(doc, replay=True)['offset_diagnosis'], doc)
                    source = Path(temporary)/f'{i}-{doc["schema_version"]}.json'; output = source.with_suffix('.replay.json')
                    source.write_text(json.dumps(doc, indent=2)+'\n')
                    self.assertEqual(main(['diagnose-construction', str(source), '--out', str(output)]), 0 if doc['diagnosis']['status'] == 'CERTIFIED' else 1)
                    self.assertEqual(source.read_bytes(), output.read_bytes())
                changed = deepcopy(current); changed['schema_version'] = 8
                if current['diagnosis'] != old['diagnosis']:
                    with self.assertRaises(ValueError): replay_construction_diagnosis(changed)
        self.assertEqual(fixture.read_bytes(), raw)
        request = dict(schema_version=1, curves=[curve_to_dict(EllipseArc((0,0),(2,1),-3.,6.)), curve_to_dict(EllipseArc((0,0),(1.5,1.5),-3.,6.))],
                       controls=dict(first_distance_m=0., second_distance_m=0.))
        report = diagnose_offsets_document(request)
        self.assertEqual(report['schema_version'], 12); self.assertEqual(report['diagnosis']['finite_center_count'], 4)
        request['controls']['max_root_boxes'] = 1
        with self.assertRaises(ValueError): diagnose_offsets_document(request)


if __name__ == '__main__': unittest.main()
