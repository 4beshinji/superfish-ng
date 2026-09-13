# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import json
import math
from pathlib import Path
import tempfile
import unittest

from superfish_ng.conics import EllipseArc, HyperbolaArc, curve_to_dict
from superfish_ng.offset_degeneracies import classify_offset_degeneracies, diagnose_offsets_document
from superfish_ng.reparameterized_conic_offsets import _support_map, classify_reparameterized_conic_offsets

ROOT = Path(__file__).resolve().parents[1]


def diagnose(a, b, d, e, **settings):
    return classify_offset_degeneracies(a, b, first_distance_m=d, second_distance_m=e, **settings)


class ReparameterizedConicOffsetTests(unittest.TestCase):
    def test_axis_exchange_overlap_with_zero_and_nonzero_offsets(self):
        a = EllipseArc((0, 0), (2, 1), 0., 1.)
        b = EllipseArc((0, 0), (1, 2), -1.5, 1., math.pi/2)
        # The second image is t in [pi/2-1.5, pi/2-.5], which overlaps [0,1].
        for distance in (0., .25, -.75, .75, 2.):
            r = diagnose(a, b, distance, distance)
            self.assertTrue(r['finite_domain_complete']); self.assertTrue(r['infinite_parameter_pairs'])
            self.assertIsNone(r['finite_center_count'])
            self.assertEqual(r['evidence']['support_map']['second_to_first'], ((0, -1), (1, 0)))
        r = diagnose(a, b, 0., 0., first_interval=(0., .0625))
        self.assertTrue(r['finite_domain_complete']); self.assertEqual(r['classification'], 'DISJOINT')

    def test_reflected_points_in_original_frames_and_all_source_pairs(self):
        a = EllipseArc((0, 0), (2, 1), .5, .5)
        b = replace(a, start_rad=2., rotation_rad=math.pi)
        r = diagnose(a, b, .75, .75)
        self.assertTrue(r['finite_domain_complete']); self.assertEqual(r['finite_center_count'], 1)
        row = next(row for row in r['evidence']['self_contacts'] if row['parameter_pair_in_domain'])
        self.assertEqual(len(row['included_parameter_pairs']), 1)
        for first, second in zip(*row['contacts_in_original_frames']):
            self.assertEqual(second, tuple((-hi, -lo) for lo, hi in first))
            x, y = (sum(box)/2 for box in first)
            self.assertAlmostEqual(float(y*y), 5/12, places=15)
            self.assertAlmostEqual(float(x*x), 7/12, places=15)
        # A wider pair contains both reflected source orders; neither is lost.
        r = diagnose(replace(a, start_rad=-3., sweep_rad=6.),
                     replace(b, start_rad=-3., sweep_rad=6.), .75, .75)
        present = [row for row in r['evidence']['self_contacts'] if row['parameter_pair_in_domain']]
        self.assertTrue(present); self.assertTrue(all(row['included_parameter_pairs'] == [(0, 1), (1, 0)] for row in present))

    def test_hyperbola_branch_reversal_endpoints_and_deduplication(self):
        a = HyperbolaArc((0, 0), (2, 1), .25, .75)
        b = replace(a, branch=-1, rotation_rad=math.pi)
        r = diagnose(a, b, -.75, .75)
        self.assertTrue(r['finite_domain_complete']); self.assertEqual(r['finite_center_count'], 1)
        row = next(row for row in r['evidence']['self_contacts'] if row['parameter_pair_in_domain'])
        for point in row['contacts']:
            self.assertAlmostEqual(float((sum(point[1])/2)**2), .25, places=15)
        a = replace(a, start_parameter=0., end_parameter=1.)
        b = replace(b, start_parameter=0., end_parameter=1.)
        for d, count in ((0., 1), (-.5, 1), (-.75, 2)):
            r = diagnose(a, b, d, -d)
            self.assertTrue(r['finite_domain_complete']); self.assertEqual(r['finite_center_count'], count)
            self.assertEqual(r['evidence']['diagonal']['shared_endpoints'], [F(0)])
        # Mapping t1=-t2 turns [0,1] and [-1,0] into exactly the same image.
        r = diagnose(a, replace(b, start_parameter=-1., end_parameter=0.), -.75, .75)
        self.assertTrue(r['finite_domain_complete']); self.assertTrue(r['infinite_parameter_pairs'])

    def test_binary_pi_is_not_a_shared_parameter_endpoint(self):
        a = EllipseArc((0, 0), (2, 1), 0., math.pi/2)
        b = EllipseArc((0, 0), (1, 2), 0., .25, math.pi/2)
        # The stored sweep pi/2 is strictly smaller than mathematical pi/2.
        r = diagnose(a, b, 0., 0.)
        self.assertTrue(r['finite_domain_complete']); self.assertEqual(r['classification'], 'DISJOINT')
        r = diagnose(replace(a, sweep_rad=math.nextafter(math.pi/2, math.inf)), b, 0., 0.)
        self.assertTrue(r['finite_domain_complete']); self.assertTrue(r['infinite_parameter_pairs'])
        self.assertEqual(r['evidence']['diagonal']['shared_endpoints'], [])

    def test_scale_translation_orientation_exchange_and_exact_support(self):
        for scale in (2.**-100, 1., 2.**100):
            for branch in (-1, 1):
                a = HyperbolaArc((3*scale, 4*scale), (2*scale, scale), .25, .75, branch=branch)
                b = replace(a, branch=-branch, rotation_rad=math.pi)
                for reverse in (False, True):
                    second = replace(b, start_parameter=b.end_parameter, end_parameter=b.start_parameter) if reverse else b
                    distances = [-branch*.75*scale, branch*.75*scale*(-1 if reverse else 1)]
                    for exchange in (False, True):
                        curves = [a, second]
                        ds = distances
                        if exchange: curves, ds = curves[::-1], ds[::-1]
                        r = diagnose(*curves, *ds)
                        self.assertTrue(r['finite_domain_complete']); self.assertEqual(r['finite_center_count'], 1)
        a = EllipseArc((0, 0), (2, 1), 0., 1.)
        b = replace(a, rotation_rad=math.pi)
        for other in (replace(b, rotation_rad=math.nextafter(math.pi, math.inf)),
                      replace(b, semiaxes_m=(math.nextafter(2., math.inf), 1)),
                      replace(b, center_zr_m=(math.nextafter(0., 1.), 0))):
            self.assertIsNone(_support_map(a, other))
        # A numerical addition of pi to a general binary rotation does not
        # prove equality of its stored cosine/sine coefficients.
        self.assertIsNone(_support_map(replace(a, rotation_rad=.7), replace(b, rotation_rad=.7+math.pi)))
        mapping = _support_map(replace(a, rotation_rad=.3), replace(b, rotation_rad=.3+math.pi))
        self.assertEqual(mapping['second_to_first'], ((-1, 0), (0, -1)))
        self.assertNotEqual(mapping['first_rotation_square'], 1)
        self.assertIsNone(classify_reparameterized_conic_offsets((a, b), (.25, .5), ((0, 1), (0, 1)),
                          endpoint_width=F(1, 2**100), max_series_terms=96))

    def test_budget_keeps_unknown_counts_and_strict_cli_and_saved_version_ten(self):
        from superfish_ng.cli import main
        from superfish_ng.construction_diagnostics import diagnose_construction, replay_construction_diagnosis
        from superfish_ng.gui import tangent_document
        a = EllipseArc((0, 0), (2, 1), .5, .5); b = replace(a, start_rad=2., rotation_rad=math.pi)
        r = diagnose(a, b, .75, .75, max_series_terms=1)
        self.assertFalse(r['finite_domain_complete']); self.assertIsNone(r['finite_center_count'])
        request = dict(schema_version=1, curves=[curve_to_dict(c) for c in (a, b)],
                       controls=dict(first_distance_m=.75, second_distance_m=.75))
        report = diagnose_offsets_document(request)
        self.assertEqual(report['schema_version'], 13); self.assertEqual(report['diagnosis']['finite_center_count'], 1)
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'request.json'; out = Path(tmp)/'diagnosis.json'
            source.write_text(json.dumps(request)+'\n')
            self.assertEqual(main(['diagnose-offsets', str(source), '--out', str(out)]), 0)
            self.assertEqual(json.loads(out.read_text()), report)
            self.assertEqual(main(['diagnose-offsets', str(source), '--out', str(out)]), 2)
        for key, value in (('max_root_boxes', 10), ('support_tolerance', .001), ('first_interval', [0, 2])):
            bad = deepcopy(request); bad['controls'][key] = value
            with self.assertRaises(ValueError): diagnose_offsets_document(bad)
        raw = (ROOT/'tests/fixtures/offset_diagnosis_v10.json').read_bytes(); old = json.loads(raw)
        self.assertEqual(old['schema_version'], 10); self.assertEqual(replay_construction_diagnosis(old), old)
        self.assertEqual(tangent_document(old, replay=True)['offset_diagnosis'], old)
        new = diagnose_construction(old['construction'])
        self.assertEqual(new['schema_version'], 13); self.assertEqual(new['construction'], old['construction'])
        self.assertEqual(new['diagnosis'], old['diagnosis']); self.assertEqual(replay_construction_diagnosis(new), new)
        bad = deepcopy(new); bad['diagnosis']['finite_center_count'] = 100
        with self.assertRaisesRegex(ValueError, 'replay differs'): replay_construction_diagnosis(bad)
        self.assertEqual((ROOT/'tests/fixtures/offset_diagnosis_v10.json').read_bytes(), raw)


if __name__ == '__main__':
    unittest.main()
