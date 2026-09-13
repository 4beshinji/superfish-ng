# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from fractions import Fraction as F
import math
import unittest

from superfish_ng.conics import EllipseArc, HyperbolaArc, rotation_cos_sin
from superfish_ng.equal_distance_conic_branches import classify_equal_distance_conic_branches


def classify(a, b, d, e=None, domains=((0, 1), (0, 1)), **settings):
    return classify_equal_distance_conic_branches((a, b), (d, d if e is None else e), domains,
        endpoint_width=F(1, 2**100), max_series_terms=settings.pop('max_series_terms', 96), **settings)


class EqualDistanceConicBranchTests(unittest.TestCase):
    def branches(self):
        return HyperbolaArc((0, 0), (2, 1), -.5, .5), HyperbolaArc((0, 0), (2, 1), .5, -.5, branch=-1)

    def test_exact_branch_gap_has_zero_one_or_two_centers_without_snapping(self):
        a, b = self.branches()
        for distance, count in ((1., 0), (math.nextafter(2., 0.), 0), (2., 1),
                                 (math.nextafter(2., math.inf), 2), (2.25, 2)):
            result = classify(a, b, distance)
            self.assertTrue(result['complete']); self.assertEqual(result['centers'], count)
            self.assertEqual(result['infinite'], False)
            for row in result['evidence']['intersections']:
                self.assertEqual(row['contact_kind'], 'REGULAR_TANGENCY' if distance == 2 else 'TRANSVERSE')
                self.assertFalse(row['source_contacts_coincide'])
                self.assertEqual(row['center_box_zr_m'][0], (0, 0))
            if distance == 2.25:
                self.assertEqual(result['evidence']['normalized_transverse_coordinate_squared'], F(17, 320))
                # The shared center is (0, ±sqrt(85/64)).
                for row in result['evidence']['intersections']:
                    lo, hi = sorted(x*x for x in row['center_box_zr_m'][1])
                    self.assertLessEqual(lo, F(85, 64)); self.assertLessEqual(F(85, 64), hi)

    def test_cross_branch_signs_require_both_outward_normals(self):
        a, b = self.branches()
        for d, e, count in ((2.25, 2.25, 2), (2.25, -2.25, 0), (-2.25, 2.25, 0), (-2.25, -2.25, 0)):
            result = classify(a, b, d, e)
            self.assertTrue(result['complete']); self.assertEqual(result['centers'], count)

    def test_opposite_sides_of_one_convex_boundary_are_disjoint_even_after_overshoot(self):
        for a in (EllipseArc((0, 0), (2, 1), -3., 6.), HyperbolaArc((0, 0), (2, 1), -2., 2.),
                  HyperbolaArc((0, 0), (2, 1), -2., 2., branch=-1)):
            for distance in (.25, 2., 20.):
                result = classify(a, a, distance, -distance)
                self.assertTrue(result['complete']); self.assertEqual(result['classification'], 'DISJOINT')
                self.assertIn('unique nearest', result['evidence']['proof'])
            self.assertIsNone(classify(a, a, 2.))  # The existing equal-offset classifier owns this case.

    def test_parameter_domains_endpoints_and_branch_reparameterization(self):
        a, b = self.branches()
        tangent = classify(replace(a, start_parameter=0.), replace(b, end_parameter=0.), 2.)
        row, = tangent['evidence']['intersections']
        self.assertEqual([m['status'] for m in row['membership']], ['START', 'END'])
        for domains, count in ((((.5, 1), (0, 1)), 1), (((.5, 1), (.5, 1)), 0),
                                (((.5, 1), (0, .5)), 1)):
            result = classify(a, b, 2.25, domains=domains)
            self.assertTrue(result['complete']); self.assertEqual(result['centers'], count)
        # A half turn swaps the physical branch and reverses the original t.
        b = HyperbolaArc((0, 0), (2, 1), -.5, .5, rotation_rad=math.pi)
        result = classify(a, b, 2.25)
        self.assertEqual(result['centers'], 2)
        self.assertEqual(result['evidence']['support_map']['parameter_orientation'], -1)
        for row in result['evidence']['intersections']:
            self.assertEqual(row['source_local_box'][0], row['target_local_box'][0])
            self.assertEqual(row['source_local_box'][1], tuple(-x for x in reversed(row['target_local_box'][1])))

    def test_binary_rotation_norm_translation_scale_reversal_and_exchange(self):
        for unit in (2.**-40, 1., 2.**40):
            a = HyperbolaArc((unit, 3*unit), (2*unit, unit), -.5, .5, rotation_rad=.3)
            b = replace(a, start_parameter=.5, end_parameter=-.5, branch=-1)
            c, s = map(F, rotation_cos_sin(.3)); n = c*c+s*s
            for first, second, distance in ((a, b, 2.25*unit), (b, a, 2.25*unit),
                    (replace(a, start_parameter=.5, end_parameter=-.5), replace(b, start_parameter=-.5, end_parameter=.5), -2.25*unit)):
                result = classify(first, second, distance)
                self.assertTrue(result['complete']); self.assertEqual(result['centers'], 2)
                self.assertEqual(result['evidence']['support_map']['first_rotation_square'], n)
            at_binary_radius = classify(a, b, 2.*unit)
            self.assertEqual(at_binary_radius['centers'], 0 if n > 1 else 2 if n < 1 else 1)

    def test_budget_and_distinct_supports_do_not_acquire_a_total(self):
        a, b = self.branches()
        result = classify(a, b, 2.25, max_series_terms=1)
        self.assertFalse(result['complete']); self.assertIsNone(result['centers'])
        self.assertTrue(result['evidence']['unresolved'])
        for changed in (replace(b, center_zr_m=(math.nextafter(0., 1.), 0)),
                        replace(b, semiaxes_m=(2., math.nextafter(1., 2.))), replace(b, rotation_rad=.1)):
            self.assertIsNone(classify(a, changed, 2.25))
        self.assertIsNone(classify(a, b, 2.25, math.nextafter(2.25, 3.)))
        self.assertIsNone(classify(a, b, 0))

    def test_mapped_same_boundary_preserves_normal_orientation(self):
        ellipse = EllipseArc((0, 0), (2, 1), -3., 6.)
        swapped = replace(ellipse, semiaxes_m=(1, 2), rotation_rad=math.pi/2)
        self.assertEqual(classify(ellipse, swapped, .75, -.75)['classification'], 'DISJOINT')
        self.assertIsNone(classify(ellipse, swapped, .75, .75))
        hyperbola = HyperbolaArc((0, 0), (2, 1), -2., 2.)
        mapped = replace(hyperbola, branch=-1, rotation_rad=math.pi)
        self.assertEqual(classify(hyperbola, mapped, .75, .75)['classification'], 'DISJOINT')
        self.assertIsNone(classify(hyperbola, mapped, .75, -.75))

    def test_public_thirteen_cli_and_twelve_replay_keep_original_construction(self):
        from copy import deepcopy
        import hashlib
        import json
        from pathlib import Path
        import tempfile
        from superfish_ng.cli import main
        from superfish_ng.conics import curve_to_dict
        from superfish_ng.offset_degeneracies import diagnose_offsets_document, _classify_offset_degeneracies_v12
        from superfish_ng.construction_diagnostics import diagnose_construction, replay_construction_diagnosis, _from_replayed_construction
        from superfish_ng.tangent_construction import construct_tangent_case
        from superfish_ng.gui import tangent_document
        a, b = self.branches()
        self.assertFalse(_classify_offset_degeneracies_v12(a, b, first_distance_m=2., second_distance_m=2.)['finite_domain_complete'])
        request = dict(schema_version=1, curves=[curve_to_dict(c) for c in (a, b)],
                       controls=dict(first_distance_m=2., second_distance_m=2.))
        expected = diagnose_offsets_document(request)
        self.assertEqual(expected['schema_version'], 13); self.assertEqual(expected['diagnosis']['finite_center_count'], 1)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'request.json'; output = Path(directory)/'diagnosis.json'
            source.write_text(json.dumps(request)+'\n')
            self.assertEqual(main(['diagnose-offsets', str(source), '--out', str(output)]), 0)
            self.assertEqual(json.loads(output.read_text()), expected)
            self.assertEqual(main(['diagnose-offsets', str(source), '--out', str(output)]), 2)
        for key, value in (('gap_tolerance', .1), ('max_root_boxes', 2), ('second_interval', [1, 0])):
            bad = deepcopy(request); bad['controls'][key] = value
            with self.assertRaises(ValueError): diagnose_offsets_document(bad)
        fixtures = Path(__file__).parent/'fixtures'; path = fixtures/'offset_diagnosis_v12.json'; raw = path.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), '4d71a33e63253e19ebc3de2ce9b0745eb936c8539fbc80e48cd49413f11efe86')
        old = json.loads(raw); self.assertEqual(old['schema_version'], 12)
        self.assertEqual(replay_construction_diagnosis(old), old)
        self.assertEqual(tangent_document(old, replay=True)['offset_diagnosis'], old)
        current = diagnose_construction(old['construction'])
        self.assertEqual(current['schema_version'], 13); self.assertEqual(current['construction'], old['construction'])
        self.assertEqual(current['diagnosis'], old['diagnosis']); self.assertEqual(path.read_bytes(), raw)
        template = json.loads((fixtures/'offset_diagnosis_v3_same_conics.json').read_text())[0]['construction']['request']
        template['case_template']['geometry']['curves'][1:3] = request['curves']
        template['controls']['radius_m'] = 2.
        construction = construct_tangent_case(template)
        old = _from_replayed_construction(construction, schema_version=12)
        self.assertEqual(old['diagnosis']['classification'], 'UNVERIFIED')
        self.assertEqual(replay_construction_diagnosis(old), old)
        current = diagnose_construction(construction)
        self.assertEqual(current['diagnosis']['finite_center_count'], 1)
        self.assertEqual(current['construction'], old['construction']); self.assertIsNone(current['construction']['case'])
        relabeled = deepcopy(old); relabeled['schema_version'] = 13
        with self.assertRaisesRegex(ValueError, 'replay differs'): replay_construction_diagnosis(relabeled)
        tampered = deepcopy(current); tampered['diagnosis']['finite_center_count'] = 2
        with self.assertRaisesRegex(ValueError, 'replay differs'): replay_construction_diagnosis(tampered)


if __name__ == '__main__': unittest.main()
