# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from fractions import Fraction as F
import math
import unittest

from superfish_ng.conics import EllipseArc, HyperbolaArc
from superfish_ng.conic_offset_projection import conic_offset_projection
from superfish_ng.conic_offset_intersections import classify_conic_offset_intersections, _recover_target
from superfish_ng.algebraic_root_signs import RootSystem, AlgebraicRoot
from superfish_ng.polynomial_roots import _value


def classify(first, second, d=.25, e=.25, domains=((0, 1), (0, 1)), **settings):
    return classify_conic_offset_intersections((first, second), (d, e), domains,
        endpoint_width=F(1, 2**100), max_series_terms=settings.pop('max_series_terms', 96), **settings)


class ConicOffsetIntersectionTests(unittest.TestCase):
    def test_four_true_intersections_and_four_wrong_target_signs(self):
        first = EllipseArc((0, 0), (2, 1), -3., 6.)
        report = classify(first, replace(first, semiaxes_m=(1, 2)))
        self.assertTrue(report['complete']); self.assertEqual(report['centers'], 4)
        evidence = report['evidence']
        self.assertEqual(len(evidence['source_projection']['source_candidates']), 8)
        self.assertEqual(len(evidence['excluded']), 4)
        self.assertTrue(all('opposite target normal' in row['reason'] for row in evidence['excluded']))
        quadrants = set()
        for row in evidence['intersections']:
            x, y = (float(sum(box)/2) for box in row['center_box_zr_m'])
            quadrants.add((x > 0, y > 0))
            self.assertAlmostEqual(abs(x), abs(y), places=14)
            self.assertEqual(row['contact_kind'], 'TRANSVERSE')
            for box in row['target_local_box']:
                self.assertLessEqual(box[1]-box[0], F(1, 2**106))
        self.assertEqual(len(quadrants), 4)

    def test_vertex_tangency_and_source_and_target_cusps(self):
        first = EllipseArc((0, 0), (2, 1), -.5, 1.)
        cases = [(EllipseArc((.5, 0), (1.5, .75), -.5, 1.), .25, .25, 'REGULAR_TANGENCY'),
                 (HyperbolaArc((.5, 0), (1, .75), -.5, .5), .25, -.25, 'REGULAR_TANGENCY'),
                 (replace(first, semiaxes_m=(1.75, .75)), .5, .25, 'CUSP')]
        for second, d, e, kind in cases:
            for a, b, left, right in ((first, second, d, e), (second, first, e, d)):
                with self.subTest(a=a, kind=kind):
                    result = classify(a, b, left, right)
                    self.assertTrue(result['complete']); self.assertEqual(result['centers'], 1)
                    row, = result['evidence']['intersections']
                    self.assertEqual(row['contact_kind'], kind)
                    self.assertEqual(row['target_local_box'], ((1, 1), (0, 0)))

    def test_rank_one_recovers_two_feet_one_center_and_finite_arc_selects_each(self):
        first = EllipseArc((0, 0), (1, 2), -.5, 1.)
        target = EllipseArc((0, 0), (2, 1), -.1, 3.5)
        result = classify(first, target, 1, 2)
        self.assertTrue(result['complete']); self.assertEqual(result['centers'], 1)
        self.assertEqual(result['evidence']['same_center_groups'], [[0, 1]])
        proof, = result['evidence']['target_recoveries']
        self.assertEqual(proof['pencil_rank'], 1); self.assertEqual(len(proof['target_feet']), 2)
        self.assertEqual({r['target_local_box'][0] for r in proof['target_feet']}, {(-1, -1), (1, 1)})
        for target in (replace(target, start_rad=-.1, sweep_rad=.2), replace(target, start_rad=3., sweep_rad=.3)):
            selected = classify(first, target, 1, 2)
            self.assertTrue(selected['complete']); self.assertEqual(len(selected['evidence']['intersections']), 1)

    def test_rank_one_has_no_real_target_feet(self):
        # The target's rank-one kernel at center (0,12) forces normalized y=-4,
        # hence x²=-15. A zero real discriminant does not imply a real contact.
        first = EllipseArc((-1, 12), (2, 1), -.5, 1.)
        target = EllipseArc((0, 0), (2, 1), -3., 6.)
        result = classify(first, target, 1, 14)
        self.assertTrue(result['complete']); self.assertEqual(result['classification'], 'DISJOINT')
        proof, = result['evidence']['target_recoveries']
        self.assertEqual(proof['free_coordinate_squared'], -15)
        self.assertIn('no real target', proof['exclusion'])

    def test_distinct_sources_and_targets_at_one_center_keep_all_four_pairs(self):
        first = EllipseArc((0, 0), (1, 2), -.1, 3.5)
        target = EllipseArc((0, 0), (2, 1), -.1, 3.5)
        result = classify(first, target, 1, 2)
        self.assertTrue(result['complete']); self.assertEqual(result['centers'], 1)
        self.assertEqual(result['evidence']['same_center_groups'], [[0, 1, 2, 3]])
        self.assertEqual(len({row['source_candidate_index'] for row in result['evidence']['intersections']}), 2)

    def test_rank_one_irrational_feet_preserve_dependent_radical_tangency(self):
        # On the inward 3/4 offset of (2,1), a self-contact has normalized
        # target coordinates (sqrt(7/12), ±sqrt(5/12)). One foot is the source
        # itself, so its tangent must agree exactly even across both radicals.
        curve = EllipseArc((0, 0), (2, 1), -3., 6.)
        projection = conic_offset_projection(curve, curve, first_distance_m=F(3, 4),
                                               second_distance_m=F(3, 4), side=1)
        root = AlgebraicRoot(RootSystem((5, 0, -38, 0, 5)), (F(1, 3), F(2, 5)))
        proof = _recover_target(root, projection, curve, endpoint_width=F(1, 2**100))
        self.assertEqual(proof['pencil_rank'], 1); self.assertEqual(proof['free_coordinate_squared'], F(5, 12))
        self.assertEqual(sorted(r['tangent_parallel'] for r in proof['target_feet']), [False, True])
        for foot in proof['target_feet']:
            for square, (low, high) in zip((F(7, 12), F(5, 12)), foot['target_local_box']):
                lo, hi = sorted((low*low, high*high))
                self.assertLessEqual(lo, square); self.assertLessEqual(square, hi)

    def test_nonvertex_target_evolute_is_a_rank_two_triple_root(self):
        # At target cos(t)=3/5, sin(t)=4/5, |t'|=25375 and curvature
        # radius=24389. The evolute point is exactly (-4536,7680).
        target = EllipseArc((0, 0), (21875, 30625), .5, 1.)
        first = EllipseArc((-4537, 7680), (2, 1), -.1, .2)
        projection = conic_offset_projection(first, target, first_distance_m=1, second_distance_m=24389, side=1)
        self.assertEqual(_value(projection['equation'], F(0)), 0)
        root = AlgebraicRoot(RootSystem((0, 1)), (0, 0))
        self.assertEqual(root.radical_sign(projection['discriminant_rational'], projection['discriminant_radical'],
                                          projection['source_chart']['S']), 0)
        proof = _recover_target(root, projection, target, endpoint_width=F(1, 2**100))
        self.assertEqual(proof['pencil_root_multiplicity'], 3); self.assertEqual(proof['pencil_rank'], 2)
        self.assertEqual(proof['target_offset_speed_factor_sign'], 0)
        for value, box in zip((F(3, 5), F(4, 5)), proof['target_feet'][0]['target_local_box']):
            self.assertLessEqual(box[0], value); self.assertLessEqual(value, box[1])

    def test_opposite_hyperbola_branches_and_normal_sign(self):
        # Center zero meets both hyperbola vertices at distance 1; each declared
        # branch has the opposite oriented normal sign.
        first = EllipseArc((0, 0), (1, 2), -.5, 1.)
        for branch in (-1, 1):
            target = HyperbolaArc((0, 0), (1, 2), -.5, .5, branch=branch)
            result = classify(first, target, 1, branch)
            self.assertTrue(result['complete']); self.assertEqual(result['centers'], 1)
            row, = result['evidence']['intersections']
            self.assertEqual(row['target_local_box'], ((branch, branch), (0, 0)))
            wrong = classify(first, target, 1, -branch)
            self.assertTrue(wrong['complete']); self.assertEqual(wrong['centers'], 0)

    def test_exact_endpoint_and_reversal_and_scaled_known_contact(self):
        for unit in (2.**-40, 1., 2.**40):
            first = EllipseArc((0, 0), (2*unit, unit), 0., .5)
            target = EllipseArc((.5*unit, 0), (1.5*unit, .75*unit), 0., .5)
            for a, b, d, e, status in ((first, target, .25*unit, .25*unit, 'START'),
                    (replace(first, start_rad=.5, sweep_rad=-.5), replace(target, start_rad=.5, sweep_rad=-.5),
                     -.25*unit, -.25*unit, 'END')):
                result = classify(a, b, d, e)
                self.assertTrue(result['complete']); self.assertEqual(result['centers'], 1)
                row, = result['evidence']['intersections']
                self.assertEqual([m['status'] for m in row['membership']], [status, status])
                self.assertEqual(row['center_box_zr_m'], ((F(1.75*unit),)*2, (0, 0)))
        # One ULP away cannot preserve the exact vertex contact.
        changed = classify(first, target, .25*unit, math.nextafter(.25*unit, math.inf))
        self.assertTrue(changed['complete'])
        self.assertFalse(any(row['rational_parameter_interval'] == (0, 0) for row in changed['evidence']['intersections']))

    def test_identity_and_budget_limits_never_assert_a_total(self):
        first = EllipseArc((0, 0), (2, 1), -3., 6.)
        target = replace(first, semiaxes_m=(1, 2))
        for options in ({'max_root_boxes': 1}, {'max_refinements': 1}, {'max_series_terms': 1}):
            result = classify(first, target, **options)
            self.assertFalse(result['complete']); self.assertIsNone(result['centers'])
        result = classify(first, first)
        self.assertFalse(result['complete']); self.assertIsNone(result['centers'])
        for domains in (((0, 1), (1, 0)), ((0, 1), (True, 1))):
            with self.assertRaises(ValueError): classify(first, target, domains=domains)

    def test_public_version_twelve_cli_and_saved_version_eleven_replay(self):
        from copy import deepcopy
        import hashlib
        import json
        from pathlib import Path
        import tempfile
        from superfish_ng.cli import main
        from superfish_ng.conics import curve_to_dict
        from superfish_ng.offset_degeneracies import diagnose_offsets_document, _classify_offset_degeneracies_v11
        from superfish_ng.construction_diagnostics import diagnose_construction, replay_construction_diagnosis
        from superfish_ng.gui import tangent_document
        first = EllipseArc((0, 0), (2, 1), -.5, 1.)
        target = EllipseArc((.5, 0), (1.5, .75), -.5, 1.)
        self.assertFalse(_classify_offset_degeneracies_v11(first, target, first_distance_m=.25,
                                                          second_distance_m=.25)['finite_domain_complete'])
        request = dict(schema_version=1, curves=[curve_to_dict(c) for c in (first, target)],
                       controls=dict(first_distance_m=.25, second_distance_m=.25))
        expected = diagnose_offsets_document(request)
        self.assertEqual(expected['schema_version'], 13); self.assertEqual(expected['diagnosis']['finite_center_count'], 1)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'request.json'; output = Path(directory)/'diagnosis.json'
            source.write_text(json.dumps(request)+'\n')
            self.assertEqual(main(['diagnose-offsets', str(source), '--out', str(output)]), 0)
            self.assertEqual(json.loads(output.read_text()), expected)
            self.assertEqual(main(['diagnose-offsets', str(source), '--out', str(output)]), 2)
        for key, value in (('max_root_boxes', 2), ('support_tolerance', .1), ('second_interval', [0, 2])):
            bad = deepcopy(request); bad['controls'][key] = value
            with self.assertRaises(ValueError): diagnose_offsets_document(bad)
        fixture = Path(__file__).parent/'fixtures/offset_diagnosis_v11.json'; raw = fixture.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), 'c83656d570c532208b7a3c9910dc999b907eabfaedd570d73b1055327c09f44f')
        old = json.loads(raw); self.assertEqual(old['schema_version'], 11)
        self.assertEqual(replay_construction_diagnosis(old), old)
        self.assertEqual(tangent_document(old, replay=True)['offset_diagnosis'], old)
        new = diagnose_construction(old['construction'])
        self.assertEqual(new['schema_version'], 13); self.assertEqual(new['construction'], old['construction'])
        self.assertEqual(new['diagnosis'], old['diagnosis']); self.assertEqual(replay_construction_diagnosis(new), new)
        bad = deepcopy(new); bad['diagnosis']['finite_center_count'] = 100
        with self.assertRaisesRegex(ValueError, 'replay differs'): replay_construction_diagnosis(bad)
        self.assertEqual(fixture.read_bytes(), raw)


if __name__ == '__main__': unittest.main()
