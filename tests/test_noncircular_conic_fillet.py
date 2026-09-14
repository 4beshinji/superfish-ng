# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest

from superfish_ng.conics import EllipseArc, HyperbolaArc, LineSegment, curve_from_dict, curve_to_dict
from superfish_ng.noncircular_conic_fillet import (intersect_algebraic_noncircular_offsets,
    noncircular_conic_fillet_candidates, connect_noncircular_conic_fillet)

ROOT = Path(__file__).resolve().parents[1]


def controls(radius=2., turn=1, **extra):
    return dict(radius_m=radius, turn_direction=turn, max_sweep_rad=4., position_tolerance_m=1e-10,
                angle_tolerance_rad=1e-8, **extra)


def branches():
    return HyperbolaArc((0, 2), (2, 1), -.5, .5), HyperbolaArc((0, 2), (2, 1), .5, -.5, branch=-1)


class NoncircularConicFilletTests(unittest.TestCase):
    def test_exact_opposite_branch_semicircle_from_previously_unresolved_projection(self):
        a, b = branches()
        result = noncircular_conic_fillet_candidates(a, b, **controls())
        self.assertEqual(result['status'], 'PASS'); candidate, = result['candidates']
        self.assertEqual(candidate['connection_direction'], 'FORWARD')
        self.assertEqual(candidate['root']['parameter_box'], ((F(1, 2), F(1, 2)),)*2)
        self.assertEqual(candidate['root']['center_box_zr_m'], ((0, 0), (2, 2)))
        self.assertEqual(candidate['contacts_zr_m'], ((2., 2.), (-2., 2.)))
        self.assertEqual(candidate['root']['source_contact_kind'], 'REGULAR_TANGENCY')
        self.assertEqual(candidate['trimmed_curves'][1]['semiaxes_m'], [2., 2.])
        self.assertLessEqual(max(candidate['fillet_contact_error_bounds_m']), F(1e-10))
        self.assertEqual(len(connect_noncircular_conic_fillet(a, b, candidate_index=0, **controls())['curves']), 3)

    def test_whole_endpoints_and_empty_retained_arcs_are_distinct(self):
        a, b = branches(); a = replace(a, end_parameter=0.); b = replace(b, start_parameter=0.)
        result = noncircular_conic_fillet_candidates(a, b, **controls())
        row, = result['candidates']; self.assertEqual(row['connection_direction'], 'FORWARD')
        self.assertEqual(row['root']['parameter_box'], ((1, 1), (0, 0)))
        self.assertEqual(row['trimmed_curves'][0], curve_to_dict(a)); self.assertEqual(row['trimmed_curves'][2], curve_to_dict(b))
        for first, second in ((replace(a, start_parameter=0., end_parameter=.5), b),
                               (a, replace(b, start_parameter=.5, end_parameter=0.))):
            result = noncircular_conic_fillet_candidates(first, second, **controls())
            self.assertEqual(result['status'], 'PASS'); row, = result['candidates']
            self.assertEqual(row['connection_direction'], 'UNVERIFIED'); self.assertIn('retained arc is empty', row['construction_reason'])
            with self.assertRaisesRegex(ValueError, 'retained arc is empty'):
                connect_noncircular_conic_fillet(first, second, candidate_index=0, **controls())

    def test_four_generic_roots_keep_lexicographic_source_order_and_sweep_limit(self):
        a = EllipseArc((0, 0), (2, 1), -3., 6.); b = replace(a, semiaxes_m=(1, 2))
        settings = controls(.25); settings['max_sweep_rad'] = math.pi
        result = noncircular_conic_fillet_candidates(a, b, **settings)
        self.assertEqual(result['status'], 'PASS'); self.assertEqual(len(result['candidates']), 4)
        self.assertEqual([r['connection_direction'] for r in result['candidates']], ['SWEEP_LIMIT', 'FORWARD', 'SWEEP_LIMIT', 'FORWARD'])
        for left, right in zip(result['candidates'], result['candidates'][1:]):
            self.assertLess(left['root']['parameter_box'][0][1], right['root']['parameter_box'][0][0])
        coarse = intersect_algebraic_noncircular_offsets(a, b, first_distance_m=.25, second_distance_m=.25, fraction_width=F(9, 10))
        self.assertEqual(coarse['status'], 'UNVERIFIED'); self.assertTrue(any(r['stage'] == 'candidate_order' for r in coarse['unresolved']))

    def test_shared_endpoint_and_reflection_share_first_fraction_and_center(self):
        a = EllipseArc((0, 0), (2, 1), -2., 2.); b = replace(a, start_rad=0., sweep_rad=4.)
        result = noncircular_conic_fillet_candidates(a, b, **controls())
        self.assertEqual(result['status'], 'PASS'); first, second = result['candidates']
        self.assertEqual([first['connection_direction'], second['connection_direction']], ['ZERO_LENGTH', 'FORWARD'])
        self.assertEqual(first['root']['source_parameter_identity'], second['root']['source_parameter_identity'])
        self.assertEqual(first['root']['center_group'], second['root']['center_group'])
        self.assertEqual(first['root']['parameter_box'], ((1, 1), (0, 0)))
        self.assertEqual(second['root']['parameter_box'][0], (1, 1)); self.assertTrue(first['root']['source_contacts_coincide'])
        self.assertFalse(second['root']['source_contacts_coincide']); self.assertEqual(first['contact_distance_m'], 0.)

    def test_rank_one_four_source_pairs_preserve_two_exact_zero_length_pairs(self):
        a = EllipseArc((0, 0), (2, 3), -.1, 3.5); b = replace(a, semiaxes_m=(2, 1))
        result = noncircular_conic_fillet_candidates(a, b, **controls())
        self.assertEqual(result['status'], 'PASS'); self.assertEqual(len(result['candidates']), 4)
        rows = [r['root'] for r in result['candidates']]
        self.assertEqual(len({r['center_group'] for r in rows}), 1)
        self.assertEqual(rows[0]['source_parameter_identity'], rows[1]['source_parameter_identity'])
        self.assertEqual(rows[2]['source_parameter_identity'], rows[3]['source_parameter_identity'])
        self.assertNotEqual(rows[0]['source_parameter_identity'], rows[2]['source_parameter_identity'])
        self.assertEqual(sum(r['source_contacts_coincide'] for r in rows), 2)
        self.assertEqual(sum(r['connection_direction'] == 'ZERO_LENGTH' for r in result['candidates']), 2)
        self.assertEqual(sum(r['connection_direction'] == 'FORWARD' for r in result['candidates']), 2)
        for left, right in ((rows[0], rows[1]), (rows[2], rows[3])):
            self.assertEqual(left['parameter_box'][0], right['parameter_box'][0])
            self.assertLess(left['parameter_box'][1][1], right['parameter_box'][1][0])

    def test_same_support_reflections_in_original_ellipse_and_hyperbola_frames(self):
        a = EllipseArc((0, 0), (2, 1), -1.5, 1.3); b = replace(a, start_rad=.2)
        h = HyperbolaArc((0, 0), (2, 1), -2., -.1)
        target = replace(h, start_parameter=-.1, end_parameter=-2., branch=-1, rotation_rad=math.pi)
        for first, second, distance in ((a, b, .75), (h, target, -.75)):
            result = noncircular_conic_fillet_candidates(first, second, **controls(abs(distance), 1 if distance > 0 else -1))
            self.assertEqual(result['status'], 'PASS'); row, = result['candidates']
            self.assertEqual(row['connection_direction'], 'FORWARD'); self.assertEqual(row['root']['source_contact_kind'], 'TRANSVERSE')
            self.assertFalse(row['root']['source_contacts_coincide'])

    def test_source_and_target_cusp_keep_the_same_quarter_circle_contact(self):
        a = EllipseArc((0, 0), (2, 1), -.5, 1.)
        b = EllipseArc((1.5, -1), (1, 1.5), 0., 2.)
        for first, second in ((a, b), (b, a)):
            settings = controls(.5); settings['max_sweep_rad'] = 6.
            result = noncircular_conic_fillet_candidates(first, second, **settings)
            self.assertEqual(result['status'], 'PASS')
            cusps = [r for r in result['candidates'] if r['root']['source_contact_kind'] == 'CUSP']
            self.assertEqual(len(cusps), 1); row, = cusps
            self.assertEqual(row['connection_direction'], 'FORWARD'); self.assertFalse(row['root']['source_contacts_coincide'])
            for value, bounds in zip((F(3, 2), F(0)), row['root']['center_box_zr_m']):
                self.assertLessEqual(bounds[0], value); self.assertLessEqual(value, bounds[1])

    def test_infinite_pairs_and_precision_failure_never_enable_selection(self):
        a, b = branches()
        identical = noncircular_conic_fillet_candidates(a, a, **controls())
        self.assertEqual(identical['status'], 'UNVERIFIED'); self.assertEqual(identical['candidates'], [])
        self.assertTrue(any(r['stage'] == 'infinite_source_pairs' for r in identical['unresolved']))
        with self.assertRaisesRegex(ValueError, 'UNVERIFIED'):
            connect_noncircular_conic_fillet(a, a, candidate_index=0, **controls())
        low = noncircular_conic_fillet_candidates(a, b, **controls(max_series_terms=1))
        self.assertEqual(low['status'], 'UNVERIFIED')
        settings = controls(); settings['position_tolerance_m'] = 1e-30
        precise = noncircular_conic_fillet_candidates(a, b, **settings)
        self.assertEqual(precise['status'], 'PASS'); row, = precise['candidates']
        self.assertEqual(row['connection_direction'], 'UNVERIFIED'); self.assertIn('error bound', row['construction_reason'])
        for extra in ({'max_root_boxes': True}, {'max_fraction_steps': 0}, {'fraction_width': 1}):
            with self.assertRaises(ValueError): noncircular_conic_fillet_candidates(a, b, **controls(**extra))
        with self.assertRaises(ValueError): intersect_algebraic_noncircular_offsets(a, b, first_distance_m=0, second_distance_m=2)
        with self.assertRaises(ValueError): noncircular_conic_fillet_candidates(LineSegment((0, 0), (1, 1)), b, **controls())

    def test_saved_nine_new_ten_cli_gui_and_full_case_validation(self):
        from superfish_ng.tangent_construction import construct_tangent_case, replay_construction
        from superfish_ng.construction_diagnostics import diagnose_construction, replay_construction_diagnosis, _from_replayed_construction
        from superfish_ng.gui import tangent_document
        from superfish_ng.cli import main
        old_path = ROOT/'tests/fixtures/circular_fillet_v9.json'; raw = old_path.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), 'ad2b9fe40c302939192954ed55e6bc5fd8f4e900089549847985db02191f642d')
        old = json.loads(raw); self.assertEqual(replay_construction(old), old); self.assertEqual(tangent_document(old, replay=True)['construction'], old)
        request = json.loads((ROOT/'examples/construction/noncircular_conic_fillet_request.json').read_text())
        preview = construct_tangent_case(request); self.assertEqual(preview['schema_version'], 10); self.assertIsNone(preview['case'])
        selected = construct_tangent_case(request, candidate_index=0); self.assertEqual(selected['status'], 'CASE_VALIDATED')
        self.assertEqual(replay_construction(selected), selected)
        diagnosis = diagnose_construction(selected); self.assertEqual(diagnosis['schema_version'], 13)
        self.assertEqual(replay_construction_diagnosis(diagnosis), diagnosis)
        self.assertEqual(tangent_document(selected, replay=True)['offset_diagnosis'], diagnosis)
        with self.assertRaisesRegex(ValueError, 'requires diagnosis schema version 13'):
            _from_replayed_construction(selected, schema_version=12)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)/'request.json'; output = Path(directory)/'constructed.json'
            source.write_text(json.dumps(request)+'\n')
            self.assertEqual(main(['construct-tangent', str(source), '--candidate-index', '0', '--out', str(output)]), 0)
            self.assertEqual(json.loads(output.read_text()), selected)
            self.assertEqual(main(['construct-tangent', str(source), '--candidate-index', '0', '--out', str(output)]), 2)
        invalid = deepcopy(request); invalid['case_template']['rf']['beta'] = 0
        self.assertIsNone(construct_tangent_case(invalid)['case'])
        with self.assertRaises(ValueError): construct_tangent_case(invalid, candidate_index=0)
        for key, value in (('allow_extension', True), ('max_boxes', 8), ('support_tolerance', .001)):
            invalid = deepcopy(request); invalid['controls'][key] = value
            with self.assertRaises(ValueError): construct_tangent_case(invalid)
        tampered = deepcopy(selected); tampered['enumeration']['candidates'][0]['root']['source_contacts_coincide'] = True
        with self.assertRaises(ValueError): replay_construction(tampered)
        self.assertEqual(old_path.read_bytes(), raw)


if __name__ == '__main__': unittest.main()
