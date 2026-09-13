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
import numpy as np
from superfish_ng.conics import EllipseArc, HyperbolaArc, LineSegment, rotation_cos_sin
from superfish_ng.algebraic_conic_fillet import algebraic_conic_fillet_candidates, connect_algebraic_conic_fillet
from superfish_ng.algebraic_offset_parameters import intersect_algebraic_line_offsets


ROOT = Path(__file__).resolve().parents[1]


def endpoint_request():
    return json.loads((ROOT/'examples/construction/algebraic_endpoint_fillet_request.json').read_text())


def controls(radius=.625, **extra):
    return dict(radius_m=radius, turn_direction=1, max_sweep_rad=math.pi,
                position_tolerance_m=1e-9, angle_tolerance_rad=1e-8, **extra)


class AlgebraicConicFilletTests(unittest.TestCase):
    def pair(self):
        return LineSegment((-1.125, -4.375), (4.875, 3.625)), EllipseArc((0, 0), (2, 1), 0., 1.)

    def test_all_pairs_are_ordered_and_exact_endpoint_retains_whole_arc(self):
        line, arc = self.pair()
        result = algebraic_conic_fillet_candidates(line, arc, **controls())
        self.assertEqual(result['status'], 'PASS'); self.assertEqual(len(result['candidates']), 2)
        self.assertLess(result['candidates'][0]['contact_fractions'][0], .5)
        built = connect_algebraic_conic_fillet(line, arc, candidate_index=1, **controls())
        self.assertEqual(built['curves'][2], arc)
        self.assertEqual(built['selected_candidate']['root']['parameter_box'], ((F(1, 2), F(1, 2)), (F(0), F(0))))
        np.testing.assert_allclose(built['curves'][1].center_zr_m, (1.375, 0), atol=1e-14)
        self.assertEqual(built['curves'][1].semiaxes_m, (.625, .625))
        self.assertAlmostEqual(built['selected_candidate']['requested_fillet_sweep_rad'], math.atan2(3, 4), places=13)

    def test_whole_line_reverse_and_empty_retained_piece(self):
        line, arc = self.pair(); line = LineSegment(line.start_zr_m, (1.875, -.375))
        result = connect_algebraic_conic_fillet(line, arc, candidate_index=1, **controls())
        self.assertEqual(result['curves'][0], line)
        reverse_arc = replace(arc, start_rad=1., sweep_rad=-1.)
        reverse_line = LineSegment(line.end_zr_m, line.start_zr_m)
        reverse_controls = controls(); reverse_controls['turn_direction'] = -1
        reverse = algebraic_conic_fillet_candidates(reverse_arc, reverse_line, **reverse_controls)
        endpoint = next(i for i, r in enumerate(reverse['candidates']) if r.get('contact_fractions', (None,))[0] == 1)
        built = connect_algebraic_conic_fillet(reverse_arc, reverse_line, candidate_index=endpoint, **reverse_controls)
        self.assertEqual(built['curves'][0], reverse_arc); self.assertEqual(built['curves'][2], reverse_line)
        for a, b in zip(result['curves'], reversed(built['curves'])):
            np.testing.assert_allclose(a.evaluate(.3)['points_zr_m'], b.evaluate(.7)['points_zr_m'], atol=1e-9)
        empty = LineSegment((1.875, -.375), (4.875, 3.625))
        report = algebraic_conic_fillet_candidates(empty, arc, **controls())
        self.assertEqual(report['status'], 'PASS')
        self.assertFalse(any(r['connection_direction'] == 'FORWARD' for r in report['candidates']))
        with self.assertRaisesRegex(ValueError, 'empty or reversed'):
            connect_algebraic_conic_fillet(empty, arc, candidate_index=0, **controls())

    def test_circle_hyperbola_and_nonparallel_cusp(self):
        cases = ((LineSegment((1.5, -2), (1.5, 2)), EllipseArc((0, 0), (2, 2), 0., math.pi), .5, (1., math.sqrt(5)/2)),
                 (LineSegment((2, -.7), (2, 1)), HyperbolaArc((1.75, -1.75), (2, 1), -.2, .3, rotation_rad=math.pi/2), .25, (1.75, 0)),
                 (LineSegment((1.75, -4.75), (7.75, 3.25)), EllipseArc((0, 0), (5, 2.5), -.5, 1.), 1.25, (3.75, 0)))
        for line, arc, radius, center in cases:
            report = algebraic_conic_fillet_candidates(line, arc, **controls(radius))
            self.assertEqual(report['status'], 'PASS', report['unresolved'])
            index = next(i for i, row in enumerate(report['candidates']) if row['connection_direction'] == 'FORWARD')
            built = connect_algebraic_conic_fillet(line, arc, candidate_index=index, **controls(radius))
            np.testing.assert_allclose(built['curves'][1].center_zr_m, center, atol=1e-9)
            if radius == 1.25:
                self.assertEqual(built['selected_candidate']['root']['source_contact_kind'], 'CUSP')

    def test_circle_charts_preserve_rotation_norm_reversed_radius_and_scale(self):
        with localcontext() as context:
            context.prec = 120
            for angle in (0., .3):
                c, s = map(D.from_float, rotation_cos_sin(angle)); norm = (c*c+s*s).sqrt()
                for distance in (.5, 3.):
                    for unit in (2.**-60, 1., 2.**60):
                        arc = EllipseArc((0, 0), (2*unit, 2*unit), -3., 6., angle)
                        line = LineSegment(((distance+.5)*unit, -3*unit), ((distance+.5)*unit, 3*unit))
                        height = ((2*norm-D.from_float(distance))**2-D('.25')).sqrt()*D.from_float(unit)
                        for exchange in (False, True):
                            report = intersect_algebraic_line_offsets(*( (arc, line) if exchange else (line, arc)),
                                first_distance_m=distance*unit, second_distance_m=distance*unit)
                            self.assertEqual(report['status'], 'PASS', report['unresolved'])
                            self.assertEqual(len(report['roots']), 2)
                            centers = [r['center_box_zr_m'] for r in report['roots']]
                            for y in (-height, height):
                                def enclosed(box):
                                    return all(D(lo.numerator)/D(lo.denominator)-D.from_float(unit)*D('1e-100') <= value <=
                                               D(hi.numerator)/D(hi.denominator)+D.from_float(unit)*D('1e-100')
                                               for (lo, hi), value in zip(box, (D('.5')*D.from_float(unit), y)))
                                self.assertTrue(any(enclosed(box) for box in centers))

    def test_shared_center_keeps_separate_pairs_and_ties_use_arc_fraction(self):
        line = LineSegment((2, -2), (2, 2)); arc = EllipseArc((0, 0), (2, 1), -.1, 3.4)
        report = intersect_algebraic_line_offsets(line, arc, first_distance_m=2., second_distance_m=2.)
        self.assertEqual(report['status'], 'PASS', report['unresolved'])
        self.assertEqual(len(report['roots']), 3)
        roots = report['roots']; self.assertNotEqual(roots[0]['center_group'], roots[1]['center_group'])
        self.assertEqual(roots[1]['center_group'], roots[2]['center_group'])
        self.assertEqual(roots[1]['parameter_box'][0], roots[2]['parameter_box'][0])
        self.assertLess(roots[1]['parameter_box'][1][1], roots[2]['parameter_box'][1][0])

    def test_exact_coincident_contacts_are_zero_length_before_float_trimming(self):
        line = LineSegment((2, -2), (2, 2)); arc = EllipseArc((0, 0), (2, 1), -.1, 3.4)
        settings = controls(2.); settings['max_sweep_rad'] = 6.
        report = algebraic_conic_fillet_candidates(line, arc, **settings)
        self.assertEqual(report['status'], 'PASS')
        zero = report['candidates'][1]
        self.assertEqual(zero['connection_direction'], 'ZERO_LENGTH')
        self.assertEqual(zero['contact_distance_m'], 0.)
        self.assertTrue(zero['root']['source_contacts_coincide'])
        with self.assertRaisesRegex(ValueError, 'coincide'):
            connect_algebraic_conic_fillet(line, arc, candidate_index=1, **settings)

    def test_explicit_extension_continuum_and_failed_precision(self):
        line = LineSegment((1.5, -2), (1.5, .5)); arc = EllipseArc((0, 0), (2, 2), 0., math.pi)
        finite = algebraic_conic_fillet_candidates(line, arc, **controls(.5))
        self.assertEqual(finite['status'], 'PASS'); self.assertEqual(finite['candidates'], [])
        extended = connect_algebraic_conic_fillet(line, arc, candidate_index=0, **controls(.5, allow_extension=True))
        self.assertTrue(extended['selected_candidate']['line_extended'])
        circle = EllipseArc((0, 0), (2, 2), 0., 1.)
        collapsed = intersect_algebraic_line_offsets(LineSegment((2, -1), (2, 1)), circle, first_distance_m=2., second_distance_m=2.)
        self.assertEqual(collapsed['status'], 'UNVERIFIED')
        self.assertTrue(collapsed['collapsed_circle_diagnosis']['infinite_parameter_pairs'])
        disjoint = intersect_algebraic_line_offsets(LineSegment((3, -1), (3, 1)), circle, first_distance_m=2., second_distance_m=2.)
        self.assertEqual(disjoint['status'], 'PASS'); self.assertEqual(disjoint['roots'], [])
        for extra in ({'max_root_boxes': 1}, {'max_refinements': 1}, {'max_fraction_steps': 1}):
            report = algebraic_conic_fillet_candidates(*self.pair(), **controls(**extra))
            self.assertEqual(report['status'], 'UNVERIFIED')
        order = algebraic_conic_fillet_candidates(*self.pair()[::-1], **controls(fraction_width=.75))
        self.assertEqual(order['status'], 'UNVERIFIED')
        self.assertTrue(any(r.get('stage') == 'candidate_order' for r in order['certificate']['unresolved']))
        exacting = controls(); exacting['position_tolerance_m'] = 1e-30
        report = algebraic_conic_fillet_candidates(*self.pair(), **exacting)
        self.assertFalse(any(r['connection_direction'] == 'FORWARD' for r in report['candidates']))

    def test_strict_version_seven_inputs_and_old_complete_replays(self):
        from superfish_ng.tangent_construction import construct_tangent_case, replay_construction
        fixture = ROOT/'tests/fixtures/fillet_construction_v5_v6.json'; raw = fixture.read_bytes()
        for old in json.loads(raw): self.assertEqual(replay_construction(old), old)
        self.assertEqual(fixture.read_bytes(), raw)
        for key, value in (('precision_bits', 96), ('max_boxes', 100), ('allow_extension', 1), ('max_refinements', True)):
            request = endpoint_request(); request['controls'][key] = value
            with self.assertRaises((ValueError, TypeError)): construct_tangent_case(request)
        for index in (None, True, -1, 99):
            with self.assertRaises(ValueError): connect_algebraic_conic_fillet(*self.pair(), candidate_index=index, **controls())

    def test_closed_case_independent_area_volume_save_cli_and_gui(self):
        from superfish_ng.tangent_construction import construct_tangent_case, replay_construction
        from superfish_ng.construction_diagnostics import diagnose_construction, replay_construction_diagnosis
        from superfish_ng.gui import tangent_document
        from superfish_ng.config import Case
        from superfish_ng.cli import main
        request = endpoint_request(); document = construct_tangent_case(request, candidate_index=0)
        self.assertEqual(document['status'], 'CASE_VALIDATED')
        self.assertEqual(document['case']['geometry']['curves'][5], request['case_template']['geometry']['curves'][4])
        case = Case.from_dict(document['case']); alpha = math.atan2(3, 4); unit = 1/32
        area = (13/4+1.5*math.pi+325/512+25*alpha/128)*unit**2
        volume = math.pi*(10+3*math.pi-1/2048-247/768+25*alpha/64)*unit**3
        self.assertAlmostEqual(case.curved_contour.area_m2, area, delta=1e-12)
        self.assertAlmostEqual(case.curved_contour.volume_m3, volume, delta=1e-12)
        self.assertEqual(replay_construction(document), document)
        diagnosis = diagnose_construction(document)
        self.assertEqual(replay_construction_diagnosis(diagnosis), diagnosis)
        gui = tangent_document(diagnosis, replay=True)
        self.assertEqual(gui['construction'], document); self.assertIsNotNone(gui['preview'])
        for key in ('case', 'enumeration', 'candidate_index'):
            changed = deepcopy(document); changed[key] = None
            with self.assertRaises(ValueError): replay_construction(changed)
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)/'request.json'; output = Path(temporary)/'construction.json'
            source.write_text(json.dumps(request)+'\n')
            self.assertEqual(main(['construct-tangent', str(source), '--out', str(output), '--candidate-index', '0']), 0)
            self.assertEqual(json.loads(output.read_text()), document)
            out = Path(temporary)/'case.json'
            self.assertEqual(main(['export-constructed-case', str(output), '--out', str(out)]), 0)
            self.assertEqual(json.loads(out.read_text()), document['case'])


if __name__ == '__main__': unittest.main()
