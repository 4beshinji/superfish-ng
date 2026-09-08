# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import json
import math
from pathlib import Path
import tempfile
import unittest
from superfish_ng.config import Case
from superfish_ng.conics import EllipseArc, LineSegment, curve_to_dict
from superfish_ng.tangent_construction import construct_tangent_case, save_construction, read_construction


def capsule_request():
    case = json.loads((Path(__file__).resolve().parents[1]/'examples/curved_ellipse.json').read_text())
    case['name'] = 'synthetic tangent capsule'
    case['geometry']['join_tolerance_m'] = 1e-12
    case['geometry']['curves'] = [curve_to_dict(c) for c in (
        LineSegment((0., 0.), (.6, 0.)),
        EllipseArc((.5, 0.), (.1, .1), 0., math.pi),
        EllipseArc((.1, 0.), (.1, .1), 0., math.pi))]
    case['geometry']['edge_tags'] = ['axis', 'pec', 'pec']
    return dict(schema_version=1, case_template=case, pair_start=1,
                controls=dict(position_tolerance_m=1e-12, angle_tolerance_rad=1e-8,
                              parameter_guard=1e-8, normal_width=2.**-44, max_boxes=10000,
                              residual_tolerance=1e-10))


class TangentConstructionTests(unittest.TestCase):
    def test_capsule_geometry_is_independent_and_request_unchanged(self):
        request = capsule_request()
        original = deepcopy(request)
        preview = construct_tangent_case(request)
        self.assertIsNone(preview['case'])
        self.assertEqual(preview['status'], 'CANDIDATES')
        selection = next(i for i, c in enumerate(preview['enumeration']['candidates'])
                         if c['connection_direction'] == 'FORWARD')
        built = construct_tangent_case(request, candidate_index=selection)
        self.assertEqual(request, original)
        self.assertEqual(built['status'], 'CASE_VALIDATED')
        case = Case.from_dict(built['case'])
        contour = case.curved_contour
        self.assertAlmostEqual(contour.area_m2, .4*.1+math.pi*.1**2/2, places=12)
        self.assertAlmostEqual(contour.volume_m3, math.pi*.1**2*.4+4*math.pi*.1**3/3, places=12)
        self.assertEqual(contour.edge_tags, ('axis', 'pec', 'pec', 'pec'))

    def test_serialization_replays_and_detects_changed_case_or_selection(self):
        request = capsule_request()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'construction.json'
            saved = save_construction(request, path, candidate_index=0)
            loaded = read_construction(path)
            self.assertEqual(saved, loaded)
            with self.assertRaises(FileExistsError):
                save_construction(request, path, candidate_index=0)
            bad = deepcopy(saved)
            bad['case']['rf']['normalization_j'] = 2.
            path.write_text(json.dumps(bad))
            with self.assertRaisesRegex(ValueError, 'replay'):
                read_construction(path)
            path.write_text('{"schema_version":1,"schema_version":1}')
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                read_construction(path)

    def test_reject_unknown_request_bad_pair_and_globally_invalid_contour(self):
        for mutate in (
            lambda r: r.update(unknown=1),
            lambda r: r.update(pair_start=True),
            lambda r: r.update(pair_start=2),
            lambda r: r['controls'].update(unknown=1),
            lambda r: r['case_template']['geometry']['curves'][1].update(unknown=1),
            lambda r: r['case_template']['geometry']['edge_tags'].__setitem__(1, 'axis'),
        ):
            request = capsule_request(); mutate(request)
            with self.assertRaises(ValueError): construct_tangent_case(request)
        request = capsule_request()
        request['case_template']['geometry']['curves'][0]['end_zr_m'] = [.59, 0.]
        with self.assertRaises(ValueError): construct_tangent_case(request, candidate_index=0)

    def test_cli_preview_and_explicit_case_export(self):
        from superfish_ng.cli import main
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); source = root/'request.json'; target = root/'construction.json'
            source.write_text(json.dumps(capsule_request()))
            self.assertEqual(main(['construct-tangent', str(source), '--out', str(target),
                                   '--candidate-index', '0']), 0)
            case_path = root/'case.json'
            self.assertEqual(main(['export-constructed-case', str(target), '--out', str(case_path)]), 0)
            Case.load(case_path)
            self.assertEqual(main(['export-constructed-case', str(target), '--out', str(case_path)]), 2)

    def test_constructed_case_fem_obeys_length_frequency_and_rf_scaling(self):
        from superfish_ng.solver import solve
        from superfish_ng.rf import quantities
        request = capsule_request()
        request['case_template']['mesh']['contour_mesh']['max_edge_m'] = .04
        base = Case.from_dict(construct_tangent_case(request, candidate_index=0)['case'])
        scaled = deepcopy(request)
        geometry = scaled['case_template']['geometry']
        for curve in geometry['curves']:
            for key in ('start_zr_m', 'end_zr_m', 'center_zr_m', 'semiaxes_m'):
                if key in curve: curve[key] = [2*x for x in curve[key]]
        for key in ('join_tolerance_m', 'minimum_gap_m', 'chord_tolerance_m'):
            geometry[key] *= 2
        scaled['case_template']['mesh']['contour_mesh']['max_edge_m'] *= 2
        scaled['controls']['position_tolerance_m'] *= 2
        large = Case.from_dict(construct_tangent_case(scaled, candidate_index=0)['case'])
        first, second = solve(base), solve(large)
        a, b = quantities(base, first), quantities(large, second)
        self.assertAlmostEqual(b['frequency_hz']/a['frequency_hz'], .5, places=10)
        for key in ('r_over_q_accelerator_ohm', 'r_over_q_circuit_ohm', 'geometry_factor_ohm',
                    'transit_time_factor_abs'):
            self.assertAlmostEqual(b[key]/a[key], 1., places=9)

    def test_unverified_preview_is_saved_but_cannot_export_a_case(self):
        from superfish_ng.cli import main
        request = capsule_request()
        # Identical supports have an unresolved infinite/degenerate family.
        request['case_template']['geometry']['curves'][2] = deepcopy(request['case_template']['geometry']['curves'][1])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); source = root/'request.json'; target = root/'preview.json'
            source.write_text(json.dumps(request))
            self.assertEqual(main(['construct-tangent', str(source), '--out', str(target)]), 1)
            self.assertEqual(read_construction(target)['status'], 'UNVERIFIED')
            exported = root/'case.json'
            self.assertEqual(main(['export-constructed-case', str(target), '--out', str(exported)]), 2)
            self.assertFalse(exported.exists())

    def test_invalid_case_settings_never_create_an_export(self):
        request = capsule_request()
        request['case_template']['solver']['ignored_option'] = True
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)/'construction.json'
            with self.assertRaises(ValueError): save_construction(request, target, candidate_index=0)
            self.assertFalse(target.exists())
