# SPDX-License-Identifier: Apache-2.0
"""Direct curved API versus the public Project, worker and CLI paths."""
from dataclasses import replace
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng.planar_curved import PlanarCurvedCase
from superfish_ng.planar_curved_solver import solve_planar_curved, PlanarCurvedFieldSampler
from superfish_ng.planar_curved_saved import planar_curved_result
from superfish_ng.planar_polygon import planar_case_from_dict
from superfish_ng.planar_project import PlanarProject
from test_planar_curved import curved_ellipse


class PlanarCurvedOperationsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.solutions = {pol: solve_planar_curved(PlanarCurvedCase(curved_ellipse(16), pol, modes=4))
                         for pol in ('te', 'tm')}

    def test_project_and_dispatch_preserve_actual_case_and_solution(self):
        for pol, original in self.solutions.items():
            with self.subTest(polarization=pol):
                self.assertEqual(planar_case_from_dict(original.case.to_dict()), original.case)
                project = PlanarProject(original.case, 'm')
                self.assertEqual(PlanarProject.from_dict(project.to_dict()), project)
                from superfish_ng.planar_solve import solve_planar_case
                solved = solve_planar_case(project.case)
                self.assertEqual(planar_curved_result(solved), planar_curved_result(original))
                self.assertEqual(solved.coefficients.tobytes(), original.coefficients.tobytes())
                with tempfile.TemporaryDirectory() as temporary:
                    path = Path(temporary)/'project.json'
                    project.save(path)
                    self.assertEqual(PlanarProject.load(path), project)

    def test_shared_parser_rejects_unsupported_physics_and_version_geometry(self):
        original = self.solutions['te'].case.to_dict()
        for section, key, value in (
                ('model', 'material', 'dielectric'), ('model', 'boundary', 'pmc'),
                ('model', 'propagation_constant_per_m', 1),
                ('model', 'propagation_constant_per_m', False),
                ('model', 'polarization', 'tem'), ('geometry', 'type', 'polygon'),
                ('mesh', 'element_order', 1)):
            data = json.loads(json.dumps(original))
            data[section][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                planar_case_from_dict(data)
        for version in (1, 2, True, 4):
            data = json.loads(json.dumps(original))
            data['schema_version'] = version
            with self.subTest(version=version), self.assertRaises(ValueError):
                planar_case_from_dict(data)

    def test_common_native_preserves_all_original_arrays_and_rf(self):
        from superfish_ng.planar_saved import save_planar_run, read_planar_run, planar_result
        with tempfile.TemporaryDirectory() as temporary:
            for pol, original in self.solutions.items():
                folder = Path(temporary)/pol
                result = save_planar_run(original.case, original, folder)
                before = {p.name: p.read_bytes() for p in folder.iterdir()}
                restored = read_planar_run(folder)
                self.assertEqual(result, planar_curved_result(original))
                self.assertEqual(result, planar_result(restored))
                for name in ('coefficients', 'frequencies_hz'):
                    self.assertEqual(getattr(restored, name).tobytes(), getattr(original, name).tobytes())
                self.assertEqual(before, {p.name: p.read_bytes() for p in folder.iterdir()})

    def test_actual_cli_solve_replay_and_original_si_probe(self):
        from superfish_ng.planar_saved import read_planar_run
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for pol, original in self.solutions.items():
                case_path = root/f'{pol}.json'
                case_path.write_text(json.dumps(original.case.to_dict()))
                folder = root/pol
                base = [sys.executable, '-m', 'superfish_ng']
                done = subprocess.run([*base, 'solve-planar', str(case_path), '--out', str(folder)],
                                      capture_output=True, text=True, timeout=30)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertEqual(json.loads(done.stdout), planar_curved_result(original))
                restored = read_planar_run(folder)
                for name in ('coefficients', 'frequencies_hz'):
                    self.assertEqual(getattr(restored, name).tobytes(), getattr(original, name).tobytes())
                before = {p.name: p.read_bytes() for p in folder.iterdir()}
                done = subprocess.run([*base, 'replay-planar', str(folder)], capture_output=True, text=True, timeout=30)
                self.assertEqual(done.returncode, 0, done.stderr)
                self.assertIn('J/m; loss W/m', done.stdout)
                points = np.vstack([original.case.domain.elements[cell].evaluate([[.2, .3]])['points_xy_m']
                                    for cell in (0, 3, 7, 15)])
                path = root/f'{pol}-points.json'
                path.write_text(json.dumps(points.tolist()))
                output = root/f'{pol}-probe.csv'
                done = subprocess.run([*base, 'probe-planar', str(folder), '--mode', '3', '--points', str(path), '--out', str(output)],
                                      capture_output=True, text=True, timeout=30)
                self.assertEqual(done.returncode, 0, done.stderr)
                rows = list(csv.DictReader(io.StringIO(output.read_text())))
                expected = PlanarCurvedFieldSampler(original).evaluate(points, 2)
                for name, values in expected.items():
                    np.testing.assert_array_equal([float(row[name]) for row in rows], values)
                metadata = json.loads(output.with_suffix('.csv.json').read_text())
                self.assertEqual(metadata['quantities'], planar_curved_result(original)['modes'][2])
                self.assertEqual(before, {p.name: p.read_bytes() for p in folder.iterdir()})

    def test_display_samples_use_original_quadratic_map_and_curved_walls(self):
        from superfish_ng.planar_display import display_planar_fields, planar_boundary_segments
        for original in self.solutions.values():
            for mode in range(original.case.modes):
                display = display_planar_fields(original, mode)
                cells, bary = display['parent_cells'], display['barycentric']
                actual = original.fields_at_reference(cells, bary[:, 1:], mode)
                for name in actual:
                    np.testing.assert_array_equal(display['fields'][name], actual[name])
                # Independent coordinate Vandermonde evaluation on reference
                # centres differs from interpolating physical triangle corners.
                refs = bary[:, 1:]
                x, y = refs.T
                basis = np.column_stack(((1-x-y)*(1-2*x-2*y), x*(2*x-1), y*(2*y-1),
                                         4*x*(1-x-y), 4*x*y, 4*y*(1-x-y)))
                mapped = np.einsum('qi,qia->qa', basis, original.space.points_xy_m[original.space.cell_nodes[cells]])
                chord_centres = display['points_xy_m'][display['triangles']].mean(axis=1)
                self.assertGreater(np.max(abs(mapped-chord_centres)), 1e-6)
                np.testing.assert_array_equal(display['points_xy_m'], original.space.points_xy_m)
            segments = planar_boundary_segments(original)
            self.assertEqual(segments.shape, (16*32, 2, 2))
            middle = segments[:32, 0][16]
            np.testing.assert_array_equal(middle, original.case.domain.boundary_evaluate(0, [.5])['points_xy_m'][0])
            first, last, mid = original.space.boundary_nodes[0]
            self.assertGreater(np.linalg.norm(middle-(original.space.points_xy_m[first]+original.space.points_xy_m[last])/2), 1e-5)

    def test_independent_study_scaling_and_rf_sweeps(self):
        from superfish_ng.planar_study import PlanarStudy
        from superfish_ng.planar_study_jobs import execute_planar_study, read_planar_study
        from superfish_ng.planar_saved import read_planar_run
        from superfish_ng.planar_solve import solve_planar_case
        with tempfile.TemporaryDirectory() as temporary:
            for pol, original in self.solutions.items():
                project = PlanarProject(original.case)
                study = PlanarStudy(project, 'uniform_scale', [1., 2.])
                points = study.projects()
                np.testing.assert_array_equal(points[1].case.domain.points_xy_m, original.space.points_xy_m*2)
                for name in ('cell_nodes', 'boundary_nodes'):
                    np.testing.assert_array_equal(getattr(points[1].case.domain, name), getattr(original.case.domain, name))
                folder = Path(temporary)/pol
                execute_planar_study(study, folder)
                read_planar_study(folder)
                scaled = read_planar_run(folder/'point-0001/solution')
                np.testing.assert_allclose(scaled.frequencies_hz*2, original.frequencies_hz, rtol=1e-11)
                # Independently solved real eigenvectors have arbitrary phase.
                # This checks the scale covariance of each isolated frequency;
                # the independent sweep does not claim persistent mode IDs.
                cross = np.sum(original.coefficients*(original.mass@scaled.coefficients), axis=0)
                norms = np.sqrt(np.sum(original.coefficients*(original.mass@original.coefficients), axis=0)
                                * np.sum(scaled.coefficients*(original.mass@scaled.coefficients), axis=0))
                np.testing.assert_allclose(abs(cross)/norms, 1., rtol=1e-11)
                phase = np.sign(cross)
                first = original.all_fields_at_reference([0, 5], [[.2, .3], [.3, .1]])
                second = scaled.all_fields_at_reference([0, 5], [[.2, .3], [.3, .1]])
                for name in first:
                    np.testing.assert_allclose(second[name]*2*phase, first[name], rtol=1e-10, atol=1e-8)
                for q, r in zip(planar_curved_result(original)['modes'], planar_curved_result(scaled)['modes']):
                    self.assertAlmostEqual(r['stored_energy_j_per_m']/q['stored_energy_j_per_m'], 1., places=10)
                    self.assertAlmostEqual(r['geometry_factor_ohm']/q['geometry_factor_ohm'], 1., places=10)
                    self.assertAlmostEqual(r['q0']/q['q0'], np.sqrt(2), places=10)
                    self.assertAlmostEqual(r['wall_loss_w_per_m']/q['wall_loss_w_per_m'], 2**(-1.5), places=10)
                for parameter, value in (('/case/rf/stored_energy_j_per_m', 3.), ('/case/rf/conductivity_s_per_m', 4*original.case.conductivity_s_per_m)):
                    derived = PlanarStudy(project, parameter, [value, value]).projects()[0]
                    self.assertEqual(derived.case.domain, original.case.domain)
                    changed = planar_curved_result(solve_planar_case(derived.case))['modes'][0]
                    reference = planar_curved_result(original)['modes'][0]
                    if 'energy' in parameter:
                        self.assertAlmostEqual(changed['stored_energy_j_per_m']/reference['stored_energy_j_per_m'], 3., places=10)
                        self.assertAlmostEqual(changed['wall_loss_w_per_m']/reference['wall_loss_w_per_m'], 3., places=10)
                    else:
                        self.assertAlmostEqual(changed['wall_loss_w_per_m']/reference['wall_loss_w_per_m'], .5, places=10)
                        self.assertAlmostEqual(changed['q0']/reference['q0'], 2., places=10)
                with self.assertRaisesRegex(ValueError, 'rectangle width/height'):
                    PlanarStudy(project, '/case/geometry/width_m', [.02, .04])

    def test_real_worker_cancel_restart_and_owned_import(self):
        from superfish_ng.jobs import JobManager
        from superfish_ng.planar_curved_refinement import refine_planar_curved_domain
        from superfish_ng.planar_saved import read_planar_run, save_planar_run
        original = self.solutions['tm']
        domain = original.case.domain
        for _ in range(3):
            domain = refine_planar_curved_domain(domain).domain
        large = PlanarProject(replace(original.case, domain=domain))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager = JobManager(root/'workspace')
            try:
                first = manager.start_planar(large)
                process = manager.processes[first]
                deadline = time.monotonic()+30
                while manager.status(first)['status'] == 'queued' and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertEqual(manager.status(first)['status'], 'running')
                self.assertIsNone(process.poll())
                self.assertEqual(manager.cancel(first)['status'], 'cancelled')
                self.assertIsNotNone(process.poll())
                self.assertFalse((manager.directory(first)/'manifest.json').exists())
                second = manager.start_planar(PlanarProject(original.case))
                self.assertEqual(manager.processes[second].wait(timeout=30), 0)
                self.assertEqual(manager.status(second, verify=True)['status'], 'complete')
                folder = manager.directory(second)/'solution'
                self.assertEqual(planar_curved_result(read_planar_run(folder)), planar_curved_result(original))
                before = {p.name: p.read_bytes() for p in folder.iterdir()}
                source = root/'native'
                save_planar_run(original.case, original, source)
                with patch('superfish_ng.planar_jobs.solve_planar', side_effect=AssertionError('import is not a new solve')):
                    direct = manager.import_planar_result(source)
                    managed = manager.import_planar_result(manager.directory(second))
                for identifier in (direct, managed):
                    target = manager.directory(identifier)/'solution'
                    self.assertEqual(before, {p.name: p.read_bytes() for p in target.iterdir()})
                    self.assertEqual(manager.status(identifier, verify=True)['origin'], 'imported')
                manager.close()
                manager = JobManager(root/'workspace')
                self.assertEqual(manager.status(managed, verify=True)['status'], 'complete')
                self.assertEqual(before, {p.name: p.read_bytes() for p in folder.iterdir()})
            finally:
                manager.close()

    def test_gui_api_original_native_rf_probe_and_plot(self):
        from superfish_ng.gui_planar import planar_response
        from superfish_ng.jobs import JobManager
        import threading
        original = self.solutions['te']
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manager = JobManager(root/'workspace')
            lock = threading.Lock()
            cache = root/'plot-cache'
            cache.mkdir()

            def request(action, **data):
                return planar_response(manager, action, data, lock, cache)

            try:
                project = PlanarProject(original.case)
                self.assertEqual(request('planar-normalize', document=project.to_dict())[0], project.to_dict())
                identifier = request('planar-start', document=project.to_dict())[0]['id']
                self.assertEqual(manager.processes[identifier].wait(timeout=30), 0)
                result = request('planar-result', id=identifier)[0]
                self.assertEqual(result['result'], planar_curved_result(original))
                folder = manager.directory(identifier)/'solution'
                before = {p.name: p.read_bytes() for p in folder.iterdir()}
                for name, raw in before.items():
                    self.assertEqual(request('planar-download', id=identifier, file=name)[0], raw)
                points = original.case.domain.elements[0].evaluate([[.2, .3], [.3, .2]])['points_xy_m']
                raw, _ = request('planar-probe', id=identifier, mode=2, points_xy_m=points.tolist())
                rows = list(csv.DictReader(io.StringIO(raw.decode())))
                for name, values in PlanarCurvedFieldSampler(original).evaluate(points, 1).items():
                    np.testing.assert_array_equal([float(row[name]) for row in rows], values)
                with self.assertRaises(ValueError):
                    request('planar-probe', id=identifier, points_xy_m=[[1., 1.]])
                import importlib.util
                if importlib.util.find_spec('matplotlib') is not None:
                    png, media = request('planar-plot', id=identifier, mode=2, mesh=True, length_unit='mm')
                    self.assertTrue(png.startswith(b'\x89PNG'))
                    self.assertEqual(media, 'image/png')
                self.assertEqual(before, {p.name: p.read_bytes() for p in folder.iterdir()})
            finally:
                manager.close()

    def test_unimplemented_comparison_and_tuning_reject_before_output(self):
        from superfish_ng.planar_convergence import PlanarConvergence
        from superfish_ng.planar_affine_shape import explicit_planar_project
        from superfish_ng.planar_tuning import validate_planar_tune, trial_planar_project
        from superfish_ng.planar_tracking_jobs import execute_planar_tracking
        from superfish_ng.planar_tracking import PlanarTrackingRequest
        from superfish_ng.planar_saved import save_planar_run
        from test_planar_tuning import request as tune_request
        original = self.solutions['te']
        project = PlanarProject(original.case)
        for action in (lambda: PlanarConvergence(project), lambda: explicit_planar_project(project)):
            with self.assertRaisesRegex(ValueError, 'does not yet support curved'):
                action()
        raw = tune_request()
        raw['project'] = project.to_dict()
        for action in (lambda: validate_planar_tune(raw), lambda: trial_planar_project(raw, 1., 'search')):
            with self.assertRaisesRegex(ValueError, 'does not yet support curved'):
                action()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            save_planar_run(original.case, original, root/'native')
            with self.assertRaisesRegex(ValueError, 'does not yet support curved'):
                execute_planar_tracking(root/'native', root/'native', PlanarTrackingRequest(), root/'comparison')
            self.assertFalse((root/'comparison').exists())
