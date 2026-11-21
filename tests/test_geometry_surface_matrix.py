# SPDX-License-Identifier: Apache-2.0
"""Separate geometry, field identity, quadrature and uncertain peak gates."""
from copy import deepcopy
from fractions import Fraction
import unittest
from dataclasses import replace
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch
import numpy as np

from superfish_ng.geometry_surface_numerics import (quantity_changes, boundary_error,
    mapped_moments, quantity_intervals, quadrature_check, ellipsoid_moments)
from superfish_ng.geometry_surface_matrix import (assess_matrix_evidence,
    build_geometry_surface_matrix, save_geometry_surface_matrix, read_geometry_surface_matrix)
from superfish_ng.surface_convergence import LIMITS
from superfish_ng import Case, solve
from superfish_ng.curved_space import case_curved_space
from superfish_ng.mesh import make_mesh
from superfish_ng.curved_fem import assemble_curved
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT/'docs/n01_geometry_surface_cases.json'


def evidence():
    groups = []
    for i in range(3):
        groups.append(dict(rows=[dict(intervals={n: [1., 1.] for n in LIMITS}, quadrature=dict(status='PASS')) for _ in range(3)],
                           field_comparisons=[dict(status='PASS'), dict(status='PASS')],
                           fixed_moments=True, boundary_coincidence=True, ritz=True,
                           geometry_diagnostic=dict(status='SMOOTH_WITHIN_TOLERANCE'),
                           boundary_error_bound_m=10.**(-3-i), relative_area_error=10.**(-3-2*i),
                           relative_volume_error=2*10.**(-3-2*i)))
    return groups, [dict(status='PASS'), dict(status='PASS')]


class GeometrySurfaceMatrixInvariantTests(unittest.TestCase):
    def test_equal_peak_estimates_do_not_hide_interval_nonconvergence(self):
        previous = {name: [1., 1.] for name in LIMITS}
        current = deepcopy(previous)
        previous['epk_over_eacc'] = current['epk_over_eacc'] = [.9, 1.]
        report = quantity_changes(previous, current)
        self.assertEqual(report['status'], 'NOT_CONVERGED')
        self.assertFalse(report['gates']['epk_over_eacc'])
        self.assertGreaterEqual(Fraction(report['relative_changes']['epk_over_eacc']),
                                Fraction(1)/Fraction(.9)-1)
        self.assertTrue(report['gates']['frequency_hz'])

    def test_each_quantity_both_fem_and_geometry_intervals_required(self):
        groups, fields = evidence()
        self.assertEqual(assess_matrix_evidence(groups, fields, finite_peak_required=True)['status'], 'PASS')
        for name in LIMITS:
            changed = deepcopy(groups); changed[1]['rows'][0]['intervals'][name] = [.8, .8]
            report = assess_matrix_evidence(changed, fields, finite_peak_required=True)
            self.assertEqual(report['status'], 'FAIL')
            self.assertFalse(report['fixed_geometry_assessments'][1]['changes'][0]['gates'][name])
            self.assertTrue(report['fixed_geometry_assessments'][1]['changes'][1]['gates'][name])
            changed = deepcopy(groups)
            for row in changed[0]['rows']: row['intervals'][name] = [.8, .8]
            report = assess_matrix_evidence(changed, fields, finite_peak_required=True)
            self.assertEqual(report['status'], 'FAIL')
            self.assertFalse(report['geometry_changes'][0]['gates'][name])
            self.assertTrue(report['geometry_changes'][1]['gates'][name])
        changed = deepcopy(groups); changed[2]['rows'][2]['intervals']['epk_over_eacc'] = None
        self.assertEqual(assess_matrix_evidence(changed, fields, finite_peak_required=True)['status'], 'UNVERIFIED')
        for value in ([2., 1.], [True, 2.], [0., 1.], [float('inf'), float('inf')]):
            previous = {n: [1., 1.] for n in LIMITS}; current = deepcopy(previous)
            current['epk_over_eacc'] = value
            self.assertEqual(quantity_changes(previous, current)['status'], 'UNVERIFIED')

    def test_field_geometry_quadrature_and_ritz_cannot_substitute_for_peaks(self):
        groups, fields = evidence()
        for name in ('fixed_moments', 'boundary_coincidence', 'ritz'):
            altered = deepcopy(groups); altered[0][name] = False
            self.assertEqual(assess_matrix_evidence(altered, fields, finite_peak_required=True)['status'], 'FAIL')
        altered = deepcopy(groups); altered[1]['field_comparisons'][0]['status'] = 'FAIL'
        self.assertEqual(assess_matrix_evidence(altered, fields, finite_peak_required=True)['status'], 'FAIL')
        altered = deepcopy(groups); altered[2]['rows'][1]['quadrature']['status'] = 'FAIL'
        self.assertEqual(assess_matrix_evidence(altered, fields, finite_peak_required=True)['status'], 'FAIL')
        altered = deepcopy(groups); altered[0]['geometry_diagnostic']['status'] = 'UNVERIFIED_GEOMETRY'
        report = assess_matrix_evidence(altered, fields, finite_peak_required=True)
        self.assertEqual(report['status'], 'UNVERIFIED')
        self.assertIsNone(report['gates']['native_geometry'])
        for name in ('boundary_error_bound_m', 'relative_area_error', 'relative_volume_error'):
            altered = deepcopy(groups); altered[1][name] = altered[0][name]
            self.assertEqual(assess_matrix_evidence(altered, fields, finite_peak_required=True)['status'], 'FAIL')
        altered = deepcopy(groups)
        for g in altered:
            g['algebraic_residual'] = 1e-14
            for row in g['rows']: row['intervals']['epk_over_eacc'] = [.9, 1.]
        self.assertEqual(assess_matrix_evidence(altered, fields, finite_peak_required=True)['status'], 'FAIL')

    def test_singular_control_never_requires_or_certifies_finite_peaks(self):
        groups, fields = evidence()
        for g in groups:
            g['geometry_diagnostic']['status'] = 'SINGULAR_GEOMETRY'
            for row in g['rows']:
                row['intervals']['epk_over_eacc'] = row['intervals']['bpk_over_eacc_mt_per_mv_per_m'] = None
        report = assess_matrix_evidence(groups, fields, finite_peak_required=False)
        self.assertEqual(report['status'], 'SINGULAR_GEOMETRY')
        self.assertEqual(report['numerical_status'], 'PASS')
        self.assertEqual(report['physical_acceptance_status'], 'UNVERIFIED')
        self.assertIsNone(report['physical_error_bound'])
        with self.assertRaisesRegex(ValueError, '3x3'):
            assess_matrix_evidence(groups[:2], fields, finite_peak_required=False)

    def test_all_five_boundary_references_and_independent_green_moments(self):
        catalog = json.loads(CATALOG.read_text())
        sys.path.insert(0, str(ROOT/'scripts'))
        try:
            old = importlib.import_module('validate_geometry_surface_convergence')
            for record in catalog['records']:
                case = Case.from_dict(record['base_case']); space = case_curved_space(case, make_mesh(case))
                reference = boundary_error(space, case.curved_contour)
                self.assertEqual(reference, old.boundary_error(space, case.curved_contour))
                area, volume = mapped_moments(space)
                q, w = np.polynomial.legendre.leggauss(3); t = (q+1)/2; w = w/2
                basis = np.column_stack(((2*t-1)*(t-1), t*(2*t-1), 4*t*(1-t)))
                derivative = np.column_stack((4*t-3, 4*t-1, 4-8*t))
                areas, volumes = [], []
                for nodes, (lo, hi) in zip(space.geometry.boundary_nodes, space.geometry.boundary_parameters):
                    p = space.geometry.points_rz_m[nodes]; r = (basis@p)[:, 0]; dz = (derivative@p)[:, 1]
                    sign = 1 if hi > lo else -1
                    areas.append(-sign*float(np.dot(w, r*dz)))
                    volumes.append(-sign*math.pi*float(np.dot(w, r*r*dz)))
                self.assertAlmostEqual(area/math.fsum(areas), 1., places=12)
                self.assertAlmostEqual(volume/math.fsum(volumes), 1., places=12)
                worst = max(range(len(reference['edges'])), key=lambda i: reference['edges'][i]['boundary_error_bound_m'])
                points = space.geometry.points_rz_m.copy(); points[space.geometry.boundary_nodes[worst, 2], 0] += .00025
                altered = replace(space, geometry=replace(space.geometry, points_rz_m=points))
                perturbed = boundary_error(altered, case.curved_contour)
                self.assertGreater(perturbed['maximum_boundary_error_bound_m'], reference['maximum_boundary_error_bound_m'])
            self.assertAlmostEqual(ellipsoid_moments(.1, .08)[1]/(4*math.pi*.1*.08**2/3), 1., places=14)
        finally:
            sys.path.remove(str(ROOT/'scripts'))

    def test_same_polynomial_quadrature_never_calls_an_eigensolver(self):
        from test_geometry_surface_fields import manufactured_fields
        s = manufactured_fields(); k, m = assemble_curved(s.space, quadrature_order=12)
        s = replace(s, stiffness=k, mass=m)
        original = s.u.copy()
        with (patch('superfish_ng.solve', side_effect=AssertionError('quadrature cannot solve')),
              patch('superfish_ng.curved_solution.eigsh', side_effect=AssertionError('quadrature cannot diagonalize'))):
            report = quadrature_check(s, 0)
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual([r['order'] for r in report['rows']], [12, 16, 24])
        self.assertEqual(report['new_eigensolves'], 0)
        np.testing.assert_array_equal(s.u, original)
        self.assertTrue(all(r['rf_by_wall_order']['8']['r_over_q_accelerator_ohm'] == 2*r['rf_by_wall_order']['8']['r_over_q_circuit_ohm'] for r in report['rows']))
        q = dict(frequency_hz=1., r_over_q_accelerator_ohm=1., geometry_factor_ohm=1., eacc_v_per_m=0.,
                 epk_over_eacc_estimate=None, bpk_over_eacc_estimate_mt_per_mv_per_m=None)
        self.assertIsNone(quantity_intervals(q)['epk_over_eacc'])


class SavedGeometrySurfaceMatrixTests(unittest.TestCase):
    def request(self):
        return dict(schema_version=1, document_type='geometry_surface_matrix_request',
                    plan_request=dict(schema_version=1, document_type='geometry_surface_plan_request',
                        catalog=str(CATALOG), catalog_sha256=hashlib.sha256(CATALOG.read_bytes()).hexdigest(),
                        case_ids=['N01-prolate-new'], reference_directory=str(ROOT)), runs=[[None]*3 for _ in range(3)])

    def test_partial_matrix_preserves_every_unknown_without_solving(self):
        with patch('superfish_ng.solve', side_effect=AssertionError('saved matrix cannot solve')):
            report = build_geometry_surface_matrix(self.request())
        self.assertEqual(report['status'], 'UNVERIFIED')
        self.assertEqual(report['supplied_native_points'], 0)
        self.assertEqual(report['planned_native_points'], 9)
        self.assertEqual(report['new_fem_solves'], 0)
        self.assertIsNone(report['independent_reference']['rf_values'])
        for group in report['geometry_groups']:
            self.assertIsNone(group['fixed_moments'])
            self.assertIsNone(group['boundary_error_bound_m'])
            for row in group['rows']:
                self.assertTrue(all(v is None for v in row['intervals'].values()))
                self.assertIsNone(row['rf_values'])
        self.assertTrue(all(v is None for v in report['assessment']['gates'].values()
                            if v is not True))

    def test_exclusive_save_full_replay_and_actual_cli_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); saved = root/'matrix.json'
            report = save_geometry_surface_matrix(self.request(), saved)
            self.assertEqual(read_geometry_surface_matrix(saved), report)
            with self.assertRaises(FileExistsError):
                save_geometry_surface_matrix(self.request(), saved)
            request = root/'request.json'; request.write_text(json.dumps(self.request()))
            process = subprocess.run([sys.executable, 'scripts/validate_geometry_surface_convergence.py',
                '--matrix-request', str(request), '--out', str(root/'cli')], cwd=ROOT,
                capture_output=True, text=True)
            self.assertEqual(process.returncode, 3, process.stderr)
            self.assertEqual(json.loads((root/'cli/matrix.json').read_text()), report)
            altered = deepcopy(report); altered['status'] = 'PASS'; saved.write_text(json.dumps(altered))
            with self.assertRaisesRegex(ValueError, 'replay differs'):
                read_geometry_surface_matrix(saved)

    def test_strict_matrix_shape_paths_case_and_archive_pin(self):
        request = self.request()
        for mutation in ('extra', 'shape', 'duplicate', 'multi-case'):
            bad = deepcopy(request)
            if mutation == 'extra': bad['unchecked'] = True
            elif mutation == 'shape': bad['runs'][0].pop()
            elif mutation == 'duplicate': bad['runs'][0][:2] = ['same', 'same']
            else: bad['plan_request']['case_ids'].append('N01-sphere-control')
            with self.assertRaises(ValueError): build_geometry_surface_matrix(bad)
        bad = dict(schema_version=2, document_type='historical_ellipse_surface_matrix_request',
                   archive_report=dict(path='counterfeit.json', sha256='0'*64))
        with self.assertRaisesRegex(ValueError, 'historical ellipse source SHA'):
            build_geometry_surface_matrix(bad)
        # An actual native Case cannot be substituted into an unsolved plan slot.
        fixture = ROOT/'out/n02-surface-fields-20261007/native-fixture/level-0'
        if fixture.exists():
            bad = deepcopy(request); bad['runs'][0][0] = str(fixture)
            with self.assertRaisesRegex(ValueError, 'complete native matrix Case'):
                build_geometry_surface_matrix(bad)

    def test_implementation_drift_during_assessment_is_rejected(self):
        import superfish_ng.geometry_surface_matrix as matrix
        original = matrix._source_hashes()
        with patch.object(matrix, '_source_hashes', side_effect=[original, dict(original, counterfeit='0'*64)]):
            with self.assertRaisesRegex(ValueError, 'sources changed'):
                matrix.build_geometry_surface_matrix(self.request())

    def test_version_three_declares_resources_without_promoting_unknown_nodes(self):
        request=self.request();request['schema_version']=3
        request['native_tracking_resources']=dict(sample_budget=8388608,sampling='uniform_parent_p2')
        report=build_geometry_surface_matrix(request)
        self.assertEqual(report['status'],'UNVERIFIED')
        self.assertEqual(report['request']['native_tracking_resources'],request['native_tracking_resources'])
        self.assertEqual(report['new_fem_solves'],0)
        self.assertIsNone(report['physical_error_bound'])
        for bad in (dict(sample_budget=True,sampling='uniform_parent_p2'),dict(sample_budget=8388608,sampling='inverse'),
                    dict(sample_budget=8388608,sampling='uniform_parent_p2',minimum_overlap=.9)):
            altered=deepcopy(request);altered['native_tracking_resources']=bad
            with self.assertRaises(ValueError):build_geometry_surface_matrix(altered)
        # Resource controls are an explicit new request version, never silently
        # inserted into an existing source-bound version-one or archive request.
        request['schema_version']=1
        with self.assertRaises(ValueError):build_geometry_surface_matrix(request)

    def test_version_three_save_replay_and_cli_keep_declared_resources(self):
        request=self.request();request['schema_version']=3
        request['native_tracking_resources']=dict(sample_budget=8388608,sampling='uniform_parent_p2')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);path=root/'matrix.json'
            report=save_geometry_surface_matrix(request,path)
            self.assertEqual(read_geometry_surface_matrix(path),report)
            source=root/'request.json';source.write_text(json.dumps(request))
            process=subprocess.run([sys.executable,'scripts/validate_geometry_surface_convergence.py',
                '--matrix-request',str(source),'--out',str(root/'cli')],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(process.returncode,3,process.stderr)
            self.assertEqual(json.loads((root/'cli/matrix.json').read_text()),report)
            mutated=deepcopy(report);mutated['request']['native_tracking_resources']['sample_budget']=262144
            path.write_text(json.dumps(mutated))
            with self.assertRaisesRegex(ValueError,'replay differs'):
                read_geometry_surface_matrix(path)
