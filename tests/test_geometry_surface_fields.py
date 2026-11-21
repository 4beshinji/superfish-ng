# SPDX-License-Identifier: Apache-2.0
"""Native field pairing retains amplitude, phase, mode ranks and sample coverage."""
from dataclasses import replace
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import json
import os
import shutil
import subprocess
import sys
import numpy as np

from superfish_ng import Case
from superfish_ng import solve
from superfish_ng.curved_space import case_curved_space
from superfish_ng.curved_solution import CurvedSolution
from superfish_ng.mesh import make_mesh
from superfish_ng.constants import EPS0, TAU
from superfish_ng.geometry_surface_fields import compare_geometry_surface_fields
from superfish_ng.curved_refinement import refine_curved_space
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution
from superfish_ng.geometry_surface_fields import (build_saved_geometry_surface_fields,
    save_geometry_surface_fields, read_geometry_surface_fields)


def manufactured_fields():
    # Polynomial u is an exact P2 kinematic fixture, never a claimed eigenmode.
    raw = Case.load('examples/curved_ellipse.json').to_dict()
    raw['mesh'].update(geometry_order=2)
    raw['mesh']['contour_mesh'].update(max_edge_m=.04, min_angle_deg=5.)
    raw['geometry']['chord_tolerance_m'] = .004
    raw['solver'].update(modes=1, quadrature_order=12)
    case = Case.from_dict(raw); space = case_curved_space(case, make_mesh(case))
    r, z = space.geometry.points_rz_m.T
    u = (2+3*r-4*z)[:, None]
    return CurvedSolution(case, space, None, None, np.array([1.]), np.array([1.e9]),
                          u, np.array([0.]), 0., 12, None)


class GeometrySurfaceFieldTests(unittest.TestCase):
    def test_physical_polynomial_amplitude_not_hidden_by_unit_overlap(self):
        previous = manufactured_fields()
        current = replace(previous, u=previous.u*1.02)
        report = compare_geometry_surface_fields(previous, current, ['target'], mapping='analytic_geometry_approximations')
        mode = report['modes'][0]
        self.assertAlmostEqual(mode['field_overlap'], 1., places=12)
        self.assertAlmostEqual(mode['hphi_sample_relative_l2'], .02, places=12)
        self.assertAlmostEqual(mode['electric_meridian_sample_relative_l2'], .02, places=12)
        self.assertAlmostEqual(mode['axis_relative_l2'], .02, places=12)
        self.assertEqual(report['status'], 'FAIL')
        self.assertFalse(mode['gates']['axis_field'])

    def test_known_signed_maxwell_fields_and_one_global_sign(self):
        previous = manufactured_fields()
        current = replace(previous, u=-previous.u)
        report = compare_geometry_surface_fields(previous, current, ['target'], mapping='analytic_geometry_approximations')
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['modes'][0]['single_hphi_sign'], -1)
        points = np.array(report['sampling']['points_rz_m']); r, z = points.T
        expected = dict(Hphi_A_per_m=r*(2+3*r-4*z),
                        Er_quadrature_V_per_m=4*r/(2*math.pi*1.e9*EPS0),
                        Ez_quadrature_V_per_m=(4+9*r-8*z)/(2*math.pi*1.e9*EPS0))
        for name, values in expected.items():
            sampled = np.array(report['sampling']['previous_fields'][name])[:, 0]
            np.testing.assert_allclose(sampled, values, rtol=2e-13, atol=2e-13)
        self.assertLess(report['modes'][0]['electric_meridian_sample_relative_l2'], 1e-13)
        self.assertFalse(report['sampling']['whole_domain_coverage_proven'])

    def test_individual_ids_follow_field_rank_exchange_in_fixed_domain(self):
        previous = manufactured_fields(); r, z = previous.space.geometry.points_rz_m.T
        maps = previous.space.geometry.local_maps
        data = [m.evaluate([[1/3, 1/3]]) for m in maps]
        rc = np.concatenate([d['points_rz_m'][:, 0] for d in data])
        zc = np.concatenate([d['points_rz_m'][:, 1] for d in data])
        # Orthogonality is built from an independent explicit H=r*u centroid
        # measure, not the comparator's assignment output.
        measure = np.array([d['determinant_m2'][0] for d in data])*rc**3
        mean = float(np.dot(measure, zc)/sum(measure))
        u = np.column_stack((np.ones(len(r)), 20*(z-mean)))
        f = np.array([1.e9, 1.0001e9])
        previous = replace(previous, case=replace(previous.case, modes=2), u=u, frequencies_hz=f)
        current = replace(previous, u=u[:, ::-1]*(f/f[::-1]))
        report = compare_geometry_surface_fields(previous, current, ['first', 'second'], mapping='curved_same_domain')
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['current_ids'], ['second', 'first'])
        self.assertEqual([m['current_mode_index'] for m in report['modes']], [2, 1])
        self.assertTrue(report['native_fixed_geometry_tracking']['individual_ids_complete'])
        for m in report['modes']:
            self.assertLess(m['axis_relative_l2'], 2e-12)
            self.assertLess(m['electric_meridian_sample_relative_l2'], 2e-12)
            self.assertAlmostEqual(m['hphi_sample_relative_l2'], abs(f[m['current_mode_index']-1]/f[m['previous_mode_index']-1]-1), places=12)

    def test_missing_centroid_retained_and_common_only_pass_not_promoted(self):
        from superfish_ng import geometry_surface_fields as module
        previous = manufactured_fields(); current = replace(previous, u=previous.u.copy())
        real = module.FieldSampler.from_solution
        class MissingProbe:
            def __init__(self, sampler): self.sampler = sampler
            def evaluate(self, points, *args, **kwargs):
                values = self.sampler.evaluate(points, *args, **kwargs)
                if np.all(points[:, 0] > 0):
                    for name in module.FIELDS: values[name][0] = np.nan
                return values
        def factory(solution):
            sampler = real(solution)
            return MissingProbe(sampler) if solution is current else sampler
        with patch.object(module.FieldSampler, 'from_solution', side_effect=factory):
            report = compare_geometry_surface_fields(previous, current, ['target'], mapping='analytic_geometry_approximations')
        self.assertEqual(report['status'], 'UNVERIFIED')
        self.assertEqual(report['sampling']['missing_indices'], [0])
        self.assertGreater(report['sampling']['missing_weight_fraction'], 0)
        self.assertIsNone(report['sampling']['current_fields']['Hphi_A_per_m'][0][0])
        self.assertEqual(len(report['sampling']['points_rz_m']), len(previous.space.geometry.cell_nodes))
        json.dumps(report, allow_nan=False)

    def test_zero_axis_or_zero_mode_does_not_become_verified(self):
        previous = manufactured_fields(); r = previous.space.geometry.points_rz_m[:, 0]
        zero_axis = replace(previous, u=r[:, None])
        report = compare_geometry_surface_fields(zero_axis, zero_axis, ['target'], mapping='analytic_geometry_approximations')
        self.assertIsNone(report['modes'][0]['axis_relative_l2'])
        self.assertEqual(report['status'], 'UNVERIFIED')
        zero = replace(previous, u=np.zeros_like(previous.u))
        report = compare_geometry_surface_fields(zero, zero, ['target'], mapping='analytic_geometry_approximations')
        self.assertEqual(report['status'], 'UNVERIFIED')
        json.dumps(report, allow_nan=False)

    def test_native_sample_budget_keeps_strong_controls_and_null_ids(self):
        from superfish_ng import geometry_surface_fields as module
        previous = manufactured_fields(); space, u = previous.space, previous.u
        for _ in range(3):
            refinement = refine_curved_space(space)
            space, u = refinement.space, refinement.prolongation@u
        current = replace(previous, case=replace(previous.case, curved_refinement_levels=3), space=space, u=u)
        with patch.object(module, 'track_curved_same_domain_modes', side_effect=AssertionError('budget must stop before quadrature tracking')):
            report = compare_geometry_surface_fields(previous, current, ['target'], mapping='curved_same_domain')
        self.assertEqual(report['status'], 'UNVERIFIED')
        self.assertEqual(report['current_ids'], [None])
        self.assertEqual(report['native_controls']['sample_order'], 10)
        self.assertGreater(report['native_fixed_geometry_tracking']['planned_samples'], 262144)
        self.assertIsNotNone(report['quadratic_boundary_coincidence'])

    def test_orthogonal_mismatch_degeneracy_and_physics_failures(self):
        previous = manufactured_fields(); r, z = previous.space.geometry.points_rz_m.T
        maps = previous.space.geometry.local_maps
        data = [m.evaluate([[1/3, 1/3]]) for m in maps]
        rc = np.concatenate([d['points_rz_m'][:, 0] for d in data])
        zc = np.concatenate([d['points_rz_m'][:, 1] for d in data])
        measure = np.array([d['determinant_m2'][0] for d in data])*rc**3
        mean = float(np.dot(measure, zc)/sum(measure))
        constant = replace(previous, u=np.ones_like(previous.u))
        mismatch = replace(previous, u=(z-mean)[:, None])
        report = compare_geometry_surface_fields(constant, mismatch, ['target'], mapping='analytic_geometry_approximations')
        self.assertEqual(report['status'], 'UNVERIFIED')
        self.assertLess(report['modes'][0]['field_overlap'], 2e-13)
        two = replace(previous, case=replace(previous.case, modes=2), u=np.column_stack((r, z)), frequencies_hz=np.array([1.e9, 1.e9]))
        report = compare_geometry_surface_fields(two, two, ['a', 'b'], mapping='analytic_geometry_approximations')
        self.assertEqual(report['status'], 'UNVERIFIED')
        self.assertEqual(report['current_ids'], [None, None])
        with patch('superfish_ng.geometry_surface_fields._samples', side_effect=AssertionError('reject unsupported physical case before sampling')):
            for changes in (dict(beta=.9), dict(z_min='electric_symmetry'),
                            dict(model=replace(previous.case.model, polarization='te'))):
                with self.assertRaises(ValueError):
                    altered = replace(previous, case=replace(previous.case, **changes))
                    compare_geometry_surface_fields(previous, altered, ['target'], mapping='analytic_geometry_approximations')
        for ids in (['target', 'extra'], ['']):
            with self.assertRaises(ValueError):
                compare_geometry_surface_fields(previous, previous, ids, mapping='analytic_geometry_approximations')
        with self.assertRaisesRegex(ValueError, 'mapping'):
            compare_geometry_surface_fields(previous, previous, ['target'], mapping='frequency_rank')


class SavedGeometrySurfaceFieldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = None
        location = os.environ.get('SUPERFISH_NG_N02_FIELDS_ACCEPTANCE_DIR')
        if location:
            cls.root = Path(location).resolve()
            cls.root.mkdir(parents=True, exist_ok=True)
        else:
            cls.tmp = tempfile.TemporaryDirectory()
            cls.root = Path(cls.tmp.name)
        raw = Case.load('examples/curved_ellipse.json').to_dict()
        raw['mesh'].update(geometry_order=2)
        raw['mesh']['contour_mesh'].update(max_edge_m=.08, min_angle_deg=5.)
        raw['geometry']['chord_tolerance_m'] = .008
        raw['solver'].update(modes=3, quadrature_order=12)
        cls.case = Case.from_dict(raw)
        cls.paths = [cls.root/f'level-{i}' for i in (0, 1)]
        source_mesh = None
        for level, path in enumerate(cls.paths):
            case = replace(cls.case, curved_refinement_levels=level)
            if path.exists():
                # Interrupted harness runs reuse only fully validated native
                # inputs with the exact original Case; never solve again.
                saved = read_solution(path)
                if saved.case.to_dict() != case.to_dict():
                    raise ValueError('retained field fixture Case differs')
            else:
                saved = solve(case, mesh_data=source_mesh)
                save_run(case, saved, path)
            source_mesh = saved.source_mesh_data

    @classmethod
    def tearDownClass(cls):
        if cls.tmp is not None: cls.tmp.cleanup()

    def request(self, same=False):
        return dict(schema_version=1, document_type='geometry_surface_field_request',
                    previous_run=str(self.paths[0]), current_run=str(self.paths[0] if same else self.paths[1]),
                    previous_ids=['target', 'guard-2', 'guard-3'], mapping='analytic_geometry_approximations')

    def test_actual_native_legacy_comparison_full_save_replay(self):
        from superfish_ng.studies import compare_refinement
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'fields.json'
            report = save_geometry_surface_fields(self.request(), path)
            self.assertEqual(read_geometry_surface_fields(path), report)
            self.assertEqual(report['comparison']['legacy_comparison'], compare_refinement(*self.paths))
            self.assertTrue(report['native_eigenpairs_revalidated'])
            self.assertEqual(report['new_fem_solves'], 0)
            self.assertTrue(all('mode_003.vtk' in r['sha256'] for r in report['sources']))
            before = path.read_bytes()
            with self.assertRaises(FileExistsError): save_geometry_surface_fields(self.request(), path)
            self.assertEqual(path.read_bytes(), before)
            altered = json.loads(before)
            altered['comparison']['sampling']['whole_domain_coverage_proven'] = True
            path.write_text(json.dumps(altered))
            with self.assertRaisesRegex(ValueError, 'replay differs'):
                read_geometry_surface_fields(path)
            path.write_bytes(before)
            self.assertEqual(read_geometry_surface_fields(path), report)
            if os.environ.get('SUPERFISH_NG_N02_FIELDS_ACCEPTANCE_DIR'):
                (self.root/'retained-comparison.json').write_bytes(before)

    def test_strict_request_corrupt_field_and_late_export_mutation(self):
        from superfish_ng import geometry_surface_fields as module
        bad = self.request(); bad['minimum_overlap'] = .1
        with self.assertRaisesRegex(ValueError, 'unknown keys'):
            build_saved_geometry_surface_fields(bad)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); copy = root/'copy'; shutil.copytree(self.paths[0], copy)
            link = root/'linked'; link.symlink_to(copy, target_is_directory=True)
            linked = self.request(same=True); linked['previous_run'] = str(link)
            with self.assertRaisesRegex(ValueError, 'symlink'):
                build_saved_geometry_surface_fields(linked)
            request = self.request(same=True); request['previous_run'] = request['current_run'] = str(copy)
            original = (copy/'fields.npz').read_bytes()
            with np.load(copy/'fields.npz', allow_pickle=False) as data:
                arrays = {n: data[n] for n in data.files}
            arrays['u_a_per_m2'] *= 1.01
            np.savez_compressed(copy/'fields.npz', **arrays)
            with self.assertRaisesRegex(ValueError, 'completion manifest'):
                build_saved_geometry_surface_fields(request)
            (copy/'fields.npz').write_bytes(original)
            export = copy/'axis_003.csv'; old = export.read_bytes()
            real = module.compare_geometry_surface_fields
            def late_change(*args, **kwargs):
                result = real(*args, **kwargs)
                export.write_bytes(old+b' ')
                return result
            with patch.object(module, 'compare_geometry_surface_fields', side_effect=late_change):
                with self.assertRaisesRegex(ValueError, 'completion manifest'):
                    build_saved_geometry_surface_fields(request)
            export.write_bytes(old)
            clean = build_saved_geometry_surface_fields(request)
            self.assertEqual(clean['status'], 'PASS')

    def test_cli_saved_pair_and_api_equal_existing_output_preserved(self):
        project = Path(__file__).resolve().parents[1]
        request = self.request(same=True)
        expected = build_saved_geometry_surface_fields(request)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root/'request.json'; source.write_text(json.dumps(request))
            target = root/'out'
            command = [sys.executable, str(project/'scripts/validate_geometry_surface_convergence.py'),
                       '--field-pair-request', str(source), '--out', str(target)]
            env = dict(os.environ, PYTHONPATH=str(project/'src'))
            result = subprocess.run(command, cwd=project, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            self.assertIn('PASS new FEM 0', result.stdout)
            actual = json.loads((target/'fields.json').read_text())
            self.assertEqual(actual, expected)
            before = (target/'fields.json').read_bytes()
            result = subprocess.run(command, cwd=project, env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('FileExistsError', result.stderr)
            self.assertEqual((target/'fields.json').read_bytes(), before)
            request['field_reference'] = 'own/results.json'; source.write_text(json.dumps(request))
            new_target = root/'bad'
            result = subprocess.run(command[:-1]+[str(new_target)], cwd=project, env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(new_target.exists())
