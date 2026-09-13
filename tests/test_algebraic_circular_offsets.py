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

from superfish_ng.conics import EllipseArc, LineSegment, rotation_cos_sin
from superfish_ng.offset_degeneracies import _classify_offset_degeneracies_v6 as classify_offset_degeneracies


class AlgebraicCircularOffsetTests(unittest.TestCase):
    def diagnose(self, a, b, d=0, e=0, **controls):
        return classify_offset_degeneracies(a, b, first_distance_m=d, second_distance_m=e, **controls)

    def assert_count(self, result, count):
        self.assertTrue(result['finite_domain_complete'], result['reason'])
        self.assertEqual(result['finite_center_count'], count)

    def test_exact_external_internal_contacts_and_one_ulp_neighbors(self):
        c, s = rotation_cos_sin(.3)
        a = EllipseArc((0, 0), (2, 2), -.5, 1., .3)
        for internal in (False, True):
            first = replace(a, semiaxes_m=(3, 3)) if internal else a
            second = replace(a, center_zr_m=((2 if internal else 4)*c, (2 if internal else 4)*s),
                             semiaxes_m=(1, 1) if internal else (2, 2), start_rad=-.5 if internal else 2.7)
            distances = (.25, .25) if internal else (.5, -.5)
            for delta, count in ((-1, 0 if internal else 2), (0, 1), (1, 2 if internal else 0)):
                x, y = second.center_zr_m
                if delta: x = math.nextafter(x, math.inf if delta > 0 else -math.inf)
                result = self.diagnose(first, replace(second, center_zr_m=(x, y)), *distances)
                self.assert_count(result, count)
                if not delta:
                    self.assertEqual(result['classification'], 'SINGLE_TANGENCY')
                    self.assertEqual(result['evidence']['discriminant_sign'], 0)

    def test_exact_arc_and_irrational_line_endpoints_with_offsets(self):
        c, s = rotation_cos_sin(.3)
        arc = EllipseArc((-2*c, -2*s), (2, 2), 0., .5, .3)
        line = LineSegment((0, 0), (-s, c))
        result = self.diagnose(arc, line, .5, .5)
        self.assert_count(result, 1)
        self.assertEqual([r['status'] for r in result['evidence']['candidates'][0]['membership']], ['START', 'START'])
        self.assert_count(self.diagnose(arc, line, .5, .5, first_interval=(.1, 1)), 0)
        self.assert_count(self.diagnose(arc, line, .5, .5, second_interval=(.1, 1)), 0)
        reverse = LineSegment(line.end_zr_m, line.start_zr_m)
        result = self.diagnose(arc, reverse, .5, -.5)
        self.assert_count(result, 1)
        self.assertEqual(result['evidence']['candidates'][0]['membership'][1]['status'], 'END')

    def test_crossings_exchange_reverse_and_extreme_scale(self):
        for scale, exchange, reverse in itertools.product((2.**-200, 1., 2.**200), (False, True), (False, True)):
            a = EllipseArc((0, 0), (2*scale, 2*scale), -2.9, 5.8, .3)
            for b in (EllipseArc((1.5*scale, 0), (2*scale, 2*scale), -2.9, 5.8, .7),
                      LineSegment((.5*scale, -2*scale), (1.5*scale, 2*scale))):
                curves = [a, b]; distances = [.5*scale, .5*scale]
                if reverse:
                    curves[1] = (replace(b, start_rad=2.9, sweep_rad=-5.8) if isinstance(b, EllipseArc)
                                 else LineSegment(b.end_zr_m, b.start_zr_m))
                    distances[1] *= -1
                if exchange: curves.reverse(); distances.reverse()
                self.assert_count(self.diagnose(*curves, *distances), 2)

    def test_concentric_disjoint_collapsed_and_parallel_lines(self):
        a = EllipseArc((0, 0), (2, 2), -2.9, 5.8, .3)
        self.assert_count(self.diagnose(a, replace(a, semiaxes_m=(3, 3)), .5, .5), 0)
        # An arbitrary-rotation circle passes through the collapsed origin.
        c, s = rotation_cos_sin(.3)
        collapsed = EllipseArc((0, 0), (2, 2), 0., 1.)
        circle = EllipseArc((-2*c, -2*s), (2, 2), 0., .5, .3)
        result = self.diagnose(collapsed, circle, 2., 0.)
        self.assert_count(result, 1)
        self.assertTrue(result['infinite_parameter_pairs'])
        self.assert_count(self.diagnose(collapsed, replace(circle, start_rad=.1), 2., 0.), 0)
        a = LineSegment((0, 0), (1, 1)); b = LineSegment((1, 1), (2, 2))
        self.assert_count(self.diagnose(a, b, .5, .5), 1)
        self.assert_count(self.diagnose(a, b, .5, math.nextafter(.5, 1.)), 0)
        result = self.diagnose(a, b, .5, .5, first_interval=(0, 2))
        self.assertTrue(result['finite_domain_complete']); self.assertTrue(result['infinite_parameter_pairs'])
        result = self.diagnose(a, LineSegment((0, 1), (1, 0)), .5, .5)
        self.assert_count(result, 1)

    def test_budget_preserves_support_evidence_and_unsupported_conics(self):
        a = EllipseArc((0, 0), (2, 2), -2.9, 5.8, .3)
        b = replace(a, center_zr_m=(1.5, 0), rotation_rad=.7)
        result = self.diagnose(a, b, .5, .5, max_series_terms=1)
        self.assertFalse(result['finite_domain_complete'])
        self.assertEqual(result['evidence']['supporting_center_count'], 2)
        self.assertIsNone(result['finite_center_count'])
        self.assertFalse(self.diagnose(a, replace(b, semiaxes_m=(2, 1)), .5, .5)['finite_domain_complete'])
        for controls in ({'endpoint_width':0}, {'max_series_terms':False}, {'second_interval':(0, 2)}):
            with self.assertRaises(ValueError): self.diagnose(a, b, .5, .5, **controls)

    def test_saved_version_five_and_current_keep_construction_and_bytes(self):
        from superfish_ng.construction_diagnostics import diagnose_construction, replay_construction_diagnosis
        from superfish_ng.gui import tangent_document
        from superfish_ng.cli import main
        fixture = Path(__file__).parent/'fixtures/offset_diagnosis_v5_algebraic_circles.json'
        raw = fixture.read_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            for index, old in enumerate(json.loads(raw)):
                self.assertEqual(old['schema_version'], 5)
                self.assertFalse(old['diagnosis']['finite_domain_complete'])
                self.assertEqual(replay_construction_diagnosis(old), old)
                new = diagnose_construction(old['construction'])
                self.assertEqual(new['schema_version'], 12)
                self.assert_count(new['diagnosis'], 2)
                self.assertEqual(new['construction'], old['construction'])
                self.assertEqual(replay_construction_diagnosis(new), new)
                self.assertEqual(tangent_document(old, replay=True)['offset_diagnosis'], old)
                self.assertEqual(tangent_document(new, replay=True)['offset_diagnosis'], new)
                for document in (old, new):
                    source = Path(temporary)/f'{index}-{document["schema_version"]}.json'
                    target = source.with_suffix('.replayed.json')
                    source.write_text(json.dumps(document, indent=2)+'\n')
                    self.assertEqual(main(['diagnose-construction', str(source), '--out', str(target)]),
                                     1 if document['diagnosis']['status'] == 'UNVERIFIED' else 0)
                    self.assertEqual(source.read_bytes(), target.read_bytes())
                changed = deepcopy(new); changed['schema_version'] = 5
                with self.assertRaises(ValueError): replay_construction_diagnosis(changed)
                changed = deepcopy(new); changed['diagnosis']['finite_center_count'] = 1
                with self.assertRaises(ValueError): replay_construction_diagnosis(changed)
        self.assertEqual(fixture.read_bytes(), raw)


if __name__ == '__main__': unittest.main()
