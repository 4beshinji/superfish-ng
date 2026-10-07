# SPDX-License-Identifier: Apache-2.0
"""Independent geometry specifications must be bound before any FEM work."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import math
import os
import subprocess
import sys

from scipy.optimize import brentq
from scipy.special import spherical_jn

from superfish_ng import Case
from superfish_ng.constants import C0
from superfish_ng.geometry_surface_plan import (build_geometry_surface_plan,
    save_geometry_surface_plan, read_geometry_surface_plan)

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT/'docs/n01_geometry_surface_cases.json'


class GeometrySurfacePlanTests(unittest.TestCase):
    def request(self, path=CATALOG, ids=None):
        return dict(schema_version=1, document_type='geometry_surface_plan_request',
                    catalog=str(path), catalog_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                    case_ids=ids or ['N01-'+s for s in ('sphere-control', 'ellipse-archive', 'prolate-new',
                                                     'rounded-two-lobe', 'sharp-two-lobe')])

    def write_catalog(self, root, catalog):
        path = root/'catalog.json'
        path.write_text(json.dumps(catalog, allow_nan=False))
        return path

    def test_independent_moment_mismatch_rejected_before_fem(self):
        catalog = json.loads(CATALOG.read_text())
        catalog['records'][3]['independent_rotational_volume_m3'] *= 1.01
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'catalog.json'
            path.write_text(json.dumps(catalog))
            request = dict(schema_version=1, document_type='geometry_surface_plan_request',
                           catalog=str(path), catalog_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                           case_ids=['N01-rounded-two-lobe'])
            with self.assertRaisesRegex(ValueError, 'independent.*moment'):
                build_geometry_surface_plan(request, base_directory=ROOT)

    def test_complete_plan_analytic_invariant_and_no_fem(self):
        with patch('superfish_ng.solve', side_effect=AssertionError('no FEM in input plan')):
            plan = build_geometry_surface_plan(self.request(), base_directory=ROOT)
        self.assertEqual(plan['new_fem_solves'], 0)
        self.assertEqual(plan['planned_fem_solves'], 45)
        self.assertEqual(plan['numerical_acceptance_status'], 'NOT_RUN')
        self.assertEqual(plan['physical_acceptance_status'], 'UNVERIFIED')
        self.assertEqual([r['status'] for r in plan['historical_reports']], ['VERIFIED_HISTORY']*4)
        self.assertTrue(all(r['independent_maxwell_reference'] is False for r in plan['historical_reports']))
        root = brentq(lambda x: spherical_jn(1, x)+x*spherical_jn(1, x, derivative=True), 2., 3.)
        sphere = plan['cases'][0]
        q = sphere['physical_reference']['rf_values']
        self.assertAlmostEqual(q['frequency_hz']/(C0*root/(2*math.pi*.08)), 1., places=12)
        self.assertEqual(q['r_over_q_accelerator_ohm'], 2*q['r_over_q_circuit_ohm'])
        for record in plan['cases']:
            self.assertEqual(len(record['matrix']), 3)
            curves = None
            for g, group in enumerate(record['matrix']):
                self.assertEqual([row['fem_uniform_level'] for row in group], [0, 1, 2])
                for row in group:
                    case = Case.from_dict(row['case'])
                    self.assertEqual(case.curved_refinement_levels, row['fem_uniform_level'])
                    self.assertEqual(row['geometry_index'], g)
                    self.assertEqual(case.modes, 3)
                    native = case.curved_contour.to_dict()
                    if curves is None:
                        curves = native
                    self.assertEqual(native, curves)
            self.assertIsNone(record['physical_error_bound'])
            self.assertFalse(record['historical_ng_baseline_is_independent_reference'])
        self.assertEqual(plan['cases'][-1]['geometry_diagnostic']['status'], 'SINGULAR_GEOMETRY')
        self.assertEqual(plan['cases'][-1]['discrete_peak_convergence'], 'NOT_APPLICABLE_SINGULAR')
        self.assertEqual(plan['cases'][1]['physical_reference']['status'], 'UNVERIFIED')

    def test_independent_two_lobe_scaling_and_whole_curve_binding(self):
        catalog = json.loads(CATALOG.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = build_geometry_surface_plan(self.request(ids=['N01-rounded-two-lobe']), base_directory=ROOT)
            record = catalog['records'][3]
            factor = .5
            for key in record['geometry_parameters']:
                record['geometry_parameters'][key] *= factor
            raw = record['base_case']
            for curve in raw['geometry']['curves']:
                for key in ('start_zr_m', 'end_zr_m', 'center_zr_m', 'semiaxes_m'):
                    if key in curve:
                        curve[key] = [x*factor for x in curve[key]]
            raw['geometry']['chord_tolerance_m'] *= factor
            raw['mesh']['contour_mesh']['max_edge_m'] *= factor
            record['geometry_chord_tolerances_m'] = [x*factor for x in record['geometry_chord_tolerances_m']]
            record['independent_meridian_area_m2'] *= factor**2
            record['independent_rotational_volume_m3'] *= factor**3
            path = self.write_catalog(root, catalog)
            scaled = build_geometry_surface_plan(self.request(path, [record['id']]), base_directory=ROOT)
            for key, power in (('meridian_area_m2', 2), ('rotational_volume_m3', 3)):
                self.assertAlmostEqual(scaled['cases'][0]['independent_geometry'][key]/
                    original['cases'][0]['independent_geometry'][key], factor**power, places=13)
            record['geometry_parameters']['fillet_radius_m'] *= 1.01
            path = self.write_catalog(root, catalog)
            with self.assertRaisesRegex(ValueError, 'fillet_center_radius_m'):
                build_geometry_surface_plan(self.request(path, [record['id']]), base_directory=ROOT)

    def test_strict_contract_unknown_fields_and_no_weakened_gates(self):
        catalog = json.loads(CATALOG.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mutations = [lambda c: c.update(unsupported_physics='te'),
                         lambda c: c['records'][0].update(force_pass=True),
                         lambda c: c['quantity_change_limits'].update(frequency_hz=.01),
                         lambda c: c['native_tracking_controls'].update(minimum_overlap=.1),
                         lambda c: c['quadrature'].update(relative_tolerance=.1),
                         lambda c: c['records'][0].update(initial_ids=['target']*3),
                         lambda c: c['records'][0].update(fem_uniform_levels=[0, 1, True]),
                         lambda c: c['records'][-1].update(finite_peak_required=True),
                         lambda c: c['records'][0]['base_case']['model'].update(polarization='te'),
                         lambda c: c['records'][0]['base_case']['rf'].update(normalization_j=2.),
                         lambda c: c['records'][0]['geometry_parameters'].update(unused_dimension_m=1.)]
            for mutate in mutations:
                altered = deepcopy(catalog); mutate(altered)
                path = self.write_catalog(root, altered)
                with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                    build_geometry_surface_plan(self.request(path), base_directory=ROOT)
            for ids in (['missing'], ['N01-sphere-control']*2):
                with self.subTest(ids=ids), self.assertRaisesRegex(ValueError, 'case_ids'):
                    build_geometry_surface_plan(self.request(ids=ids), base_directory=ROOT)

    def test_reference_absence_and_own_fem_reference_rejection(self):
        catalog = json.loads(CATALOG.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self.write_catalog(root, catalog)
            request = self.request(path)
            request['reference_directory'] = str(root)
            plan = build_geometry_surface_plan(request)
            self.assertEqual([r['status'] for r in plan['historical_reports']], ['UNVERIFIED']*4)
            self.assertEqual(plan['cases'][0]['physical_reference']['status'], 'AVAILABLE')
            for record in plan['cases'][1:]:
                self.assertEqual(record['physical_reference']['status'], 'UNVERIFIED')
                self.assertIsNone(record['physical_reference']['rf_values'])
            mutations = [lambda c: c['records'][1]['physical_reference'].update(
                            status='NG_FINEST_REFERENCE', field_source='own/results.json'),
                         lambda c: c['records'][1]['physical_reference'].update(
                            rf_values=c['records'][1]['historical_ng_baseline']['finest_geometry_fem_intervals']),
                         lambda c: c['records'][1]['physical_reference'].update(status='ANALYTICAL_REFERENCE_AVAILABLE'),
                         lambda c: c['records'][0]['physical_reference']['rf_values'].update(frequency_hz=1.)]
            for mutate in mutations:
                altered = deepcopy(catalog); mutate(altered)
                path = self.write_catalog(root, altered)
                with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                    build_geometry_surface_plan(self.request(path), base_directory=ROOT)

    def test_historical_sha_status_and_original_intervals(self):
        catalog = json.loads(CATALOG.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = catalog['reference_reports'][1]
            data = (ROOT/original['path']).read_bytes()
            report_path = root/'report.json'; report_path.write_bytes(data)
            replacement = dict(original, path=str(report_path))
            catalog['reference_reports'][1] = replacement
            catalog['records'][1]['physical_reference']['prior_report'] = replacement
            baseline = catalog['records'][1]['historical_ng_baseline']
            baseline.update(report=str(report_path))
            path = self.write_catalog(root, catalog)
            plan = build_geometry_surface_plan(self.request(path), base_directory=ROOT)
            self.assertEqual(plan['historical_reports'][1]['status'], 'VERIFIED_HISTORY')
            report_path.write_bytes(data+b' ')
            with self.assertRaisesRegex(ValueError, 'sha256 mismatch'):
                build_geometry_surface_plan(self.request(path), base_directory=ROOT)
            report_path.write_bytes(data)
            baseline['finest_geometry_fem_intervals']['frequency_hz'][0] *= .99
            path = self.write_catalog(root, catalog)
            with self.assertRaisesRegex(ValueError, 'baseline intervals'):
                build_geometry_surface_plan(self.request(path), base_directory=ROOT)
            baseline['finest_geometry_fem_intervals']['frequency_hz'][0] /= .99
            failed = json.loads(data); failed['status'] = 'FAIL'
            report_path.write_text(json.dumps(failed))
            replacement['sha256'] = hashlib.sha256(report_path.read_bytes()).hexdigest()
            baseline['report_sha256'] = replacement['sha256']
            path = self.write_catalog(root, catalog)
            with self.assertRaisesRegex(ValueError, 'not accepted'):
                build_geometry_surface_plan(self.request(path), base_directory=ROOT)

    def test_exclusive_save_full_replay_symlink_and_late_mutation(self):
        from superfish_ng import geometry_surface_plan as module
        catalog = json.loads(CATALOG.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.write_catalog(root, catalog)
            request = self.request(source, ['N01-sharp-two-lobe', 'N01-sphere-control'])
            target = root/'plan.json'
            plan = save_geometry_surface_plan(request, target, base_directory=ROOT)
            self.assertEqual(read_geometry_surface_plan(target), plan)
            self.assertEqual([r['id'] for r in plan['cases']], request['case_ids'])
            before = target.read_bytes()
            with self.assertRaises(FileExistsError):
                save_geometry_surface_plan(request, target, base_directory=ROOT)
            self.assertEqual(target.read_bytes(), before)
            changed = deepcopy(plan); changed['cases'][0]['discrete_peak_convergence'] = 'PASS'
            target.write_text(json.dumps(changed))
            with self.assertRaisesRegex(ValueError, 'replay differs'):
                read_geometry_surface_plan(target)
            target.write_bytes(before)
            link = root/'catalog-link.json'; link.symlink_to(source)
            with self.assertRaisesRegex(ValueError, 'symlink'):
                build_geometry_surface_plan(self.request(link), base_directory=ROOT)
            original_bytes = source.read_bytes()
            real = module._physical_reference
            def late_change(*args):
                result = real(*args)
                source.write_bytes(original_bytes+b' ')
                return result
            with patch.object(module, '_physical_reference', side_effect=late_change):
                with self.assertRaisesRegex(ValueError, 'sources changed'):
                    build_geometry_surface_plan(request, base_directory=ROOT)
            source.write_bytes(original_bytes)
            self.assertEqual(read_geometry_surface_plan(target), plan)

    def test_cli_explicit_input_only_and_existing_output_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output = root/'planned'
            runner = [sys.executable, str(ROOT/'scripts/validate_geometry_surface_convergence.py')]
            command = runner+['--catalog', str(CATALOG), '--catalog-sha256', self.request()['catalog_sha256'],
                              '--case', 'N01-rounded-two-lobe', 'N01-sharp-two-lobe',
                              '--plan-only', '--out', str(output)]
            env = dict(os.environ, PYTHONPATH=str(ROOT/'src'))
            completed = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stdout+completed.stderr)
            self.assertIn('planned FEM 18 new FEM 0', completed.stdout)
            plan = read_geometry_surface_plan(output/'plan.json')
            self.assertEqual(plan['new_fem_solves'], 0)
            before = (output/'plan.json').read_bytes()
            completed = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn('FileExistsError', completed.stderr)
            self.assertEqual((output/'plan.json').read_bytes(), before)
            missing = subprocess.run([arg for arg in command if arg != '--plan-only'],
                cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(missing.returncode, 2)
            self.assertIn('numerical catalog execution is not implemented', missing.stderr)
            self.assertEqual((output/'plan.json').read_bytes(), before)
            invalid_archive = subprocess.run(runner+['--archive', str(root/'missing-archive'),
                '--plan-only', '--out', str(root/'bad')], cwd=ROOT, env=env, capture_output=True, text=True)
            self.assertEqual(invalid_archive.returncode, 2)
            self.assertFalse((root/'bad').exists())
