# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng.constants import C0, EPS0, MU0
from superfish_ng.jobs import JobManager
from superfish_ng.planar import solve_planar, planar_quantities
from superfish_ng.planar_mesh import PlanarMesh
from superfish_ng.planar_polygon import PlanarPolygonCase
from superfish_ng.planar_saved import save_planar_run
from superfish_ng.planar_piecewise_mapping import PlanarPiecewiseMapping
from superfish_ng.planar_piecewise_overlap import planar_piecewise_overlay
from superfish_ng.planar_tracking import PlanarTrackingRequest, track_planar_modes
from superfish_ng.planar_tracking_fields import _electric_grams
from superfish_ng.planar_tracking_exact_mapping import PolygonExactAffineRemeshMapping
from superfish_ng.planar_tracking_jobs import execute_planar_tracking, read_planar_tracking, _snapshot
from superfish_ng.planar_tracking_history import PlanarTrackingHistoryRequest
from superfish_ng.planar_tracking_history_saved import execute_planar_history, read_planar_history
from test_planar_piecewise_mapping import strip_mapping
from test_planar_tracking_exact_affine import rectangle


def mild_piecewise_mapping():
    original = strip_mapping().previous_partition
    points = original.points_xy_m.copy()
    points[:, 1] *= .5
    previous = PlanarMesh.create(original.polygon_xy_m*[1., .5], points, original.triangles)
    mapped = points.copy()
    mapped[:, 0] += np.maximum(points[:, 0]-.5, 0.)/16
    current = PlanarMesh.create(mapped[[0, 2, 5, 3]], mapped, original.triangles)
    return PlanarPiecewiseMapping(previous, current)


class PlanarPiecewiseTrackingTests(unittest.TestCase):
    def test_joint_original_cell_coverage_and_point_reconstruction(self):
        for scale in (2.**-12, 1., 2.**12):
            mapping = strip_mapping(scale)
            previous = rectangle(3, 4, scale, scale, True)
            current = rectangle(5, 3, 1.5*scale, scale)
            for old, new, declaration in ((previous, current, mapping), (current, previous, mapping.reversed())):
                joint = planar_piecewise_overlay(old, new, declaration)
                overlay = joint.overlay
                np.testing.assert_array_equal(joint.current_to_previous_linear,
                                               declaration.current_to_previous_linear[joint.mapping_cells])
                for mesh, cells, bary, factor in (
                        (old, overlay.previous_cells, overlay.previous_vertex_barycentric, np.ones(len(joint.mapping_cells))),
                        (new, overlay.current_cells, overlay.current_vertex_barycentric,
                         declaration.jacobian_determinants[joint.mapping_cells])):
                    vertices = mesh.points_xy_m[mesh.triangles]
                    u, v = vertices[:, 1]-vertices[:, 0], vertices[:, 2]-vertices[:, 0]
                    expected = u[:, 0]*v[:, 1]-u[:, 1]*v[:, 0]
                    np.testing.assert_allclose(np.bincount(cells,
                        weights=overlay.reference_determinants*factor), expected, rtol=3e-14, atol=0.)
                    physical = np.einsum('nij,njk->nik', bary, vertices[cells])
                    if mesh is new:
                        x = overlay.reference_vertices/scale
                        expected_points = (np.stack((np.where(x[:, :, 0] <= .5, x[:, :, 0],
                            2*x[:, :, 0]-.5), x[:, :, 1]), axis=2)*scale if old is previous else
                            np.stack((np.where(x[:, :, 0] <= .5, x[:, :, 0],
                            (x[:, :, 0]+.5)/2), x[:, :, 1]), axis=2)*scale)
                    else:
                        expected_points = overlay.reference_vertices
                    np.testing.assert_allclose(physical, expected_points, rtol=0., atol=8e-16*scale)
                self.assertFalse(joint.mapping_cells.flags.writeable)

    def test_manufactured_scalar_and_curl_grams_on_original_p1_p2_cells(self):
        mapping = strip_mapping()
        old_mesh, new_mesh = rectangle(4, 3, flipped=True), rectangle(6, 4, width=1.5)
        joint = planar_piecewise_overlay(old_mesh, new_mesh, mapping)
        for pol in ('te', 'tm'):
            for old_order, new_order in ((1, 2), (2, 1)):
                old = solve_planar(PlanarPolygonCase(old_mesh, pol, old_order, 1))
                new = solve_planar(PlanarPolygonCase(new_mesh, pol, new_order, 1))
                def scalar(points, inverse=False):
                    x, y = points.T
                    if inverse:
                        x = np.where(x <= .5, x, (x+.5)/2)
                    return (1+x+.25*y)[:, None]
                old = replace(old, coefficients=scalar(old.space.dof_points_xy_m))
                new = replace(new, coefficients=scalar(new.space.dof_points_xy_m, True),
                              frequencies_hz=old.frequencies_hz)
                # These are manufactured polynomials, not claimed eigenmodes.
                expected = 131/48 if pol == 'tm' else 17/16/(2*np.pi*old.frequencies_hz[0]*EPS0)**2
                for order in (3, 5):
                    grams = _electric_grams(old, new, joint.overlay, order,
                        current_to_previous_rotation=joint.current_to_previous_linear)
                    for gram in grams:
                        self.assertAlmostEqual(gram[0, 0]/expected, 1., places=11)

    def test_real_affine_limit_similarity_fields_frequency_rf_and_phase(self):
        base = rectangle(2, 2, .5, .25)
        target = PlanarMesh.create(base.polygon_xy_m*2, base.points_xy_m*2, base.triangles)
        mapping = PlanarPiecewiseMapping(base, target)
        for pol in ('te', 'tm'):
            previous = solve_planar(PlanarPolygonCase(rectangle(12, 12, .5, .25), pol, 2, 3))
            current = solve_planar(PlanarPolygonCase(rectangle(16, 16, 1., .5, True), pol, 2, 3))
            original_rf = [planar_quantities(s) for s in (previous, current)]
            request = PlanarTrackingRequest(1, 1, ['fundamental'], mapping=mapping)
            result = track_planar_modes(previous, current, request)
            self.assertEqual(result['result_version'], 9)
            self.assertEqual(result['status'], 'PASS')
            self.assertEqual(result['current_mode_ids'], ['fundamental'])
            analytic = C0/2*np.hypot(2., 4. if pol == 'tm' else 0.)
            self.assertLess(abs(previous.frequencies_hz[0]/analytic-1), .003)
            self.assertLess(abs(2*current.frequencies_hz[0]/analytic-1), .003)
            if pol == 'tm':
                # E scalar at fixed U′ scales 1/s; previous-area norm = 1/s².
                expected_norm = 2/EPS0/4
            else:
                # adj(sI)=sI restores the fixed-U′ transverse amplitude.
                expected_norm = 2/EPS0
            self.assertAlmostEqual(result['physical_mapping']['electric_gram_current'][0][0]/expected_norm, 1., places=10)
            native_current = current.coefficients.copy()
            negative = replace(current, coefficients=-native_current)
            opposite = track_planar_modes(previous, negative, request)
            self.assertEqual(opposite['current_mode_ids'], result['current_mode_ids'])
            self.assertEqual(opposite['matches'][0]['previous_phase_multiplier'],
                             -result['matches'][0]['previous_phase_multiplier'])
            np.testing.assert_array_equal(current.coefficients, native_current)
            exact = track_planar_modes(previous, current, replace(request,
                mapping=PolygonExactAffineRemeshMapping([[2., 0.], [0., 2.]])))
            for key in ('electric_gram_previous', 'electric_gram_cross', 'electric_gram_current'):
                np.testing.assert_allclose(np.array(exact['physical_mapping'][key])/4,
                                           result['physical_mapping'][key], rtol=3e-12, atol=1e-3)
            for solution, before in zip((previous, current), original_rf):
                rf = planar_quantities(solution)
                self.assertEqual(rf, before)
                self.assertAlmostEqual(rf['electric_energy_j_per_m'], .5, places=10)
                self.assertAlmostEqual(rf['magnetic_energy_j_per_m'], .5, places=10)
                width, height = solution.case.width_m, solution.case.height_m
                omega = 2*np.pi*solution.frequencies_hz[0]
                if pol == 'te':
                    g = omega*MU0*width*height*.5/(2*height+width)
                else:
                    kx, ky = np.pi/width, np.pi/height
                    g = omega*MU0*(kx*kx+ky*ky)*width*height/(4*(height*kx*kx+width*ky*ky))
                self.assertLess(abs(rf['geometry_factor_ohm']/g-1), .03)
                self.assertIsNone(rf['r_over_q_accelerator_ohm'])
                self.assertIsNone(rf['r_over_q_circuit_ohm'])

    def test_strict_request_roundtrip_guard_and_incomplete_partition_rejected(self):
        mapping = strip_mapping()
        request = PlanarTrackingRequest(1, 1, ['first'], mapping=mapping)
        self.assertEqual(PlanarTrackingRequest.from_dict(request.to_dict()).to_dict(), request.to_dict())
        for version in (1, 2, 3, 4, 5, 6, 7, 8, True, 9., 10):
            with self.subTest(version=version), self.assertRaises(ValueError):
                PlanarTrackingRequest.from_dict(dict(request.to_dict(), tracking_version=version))
        square = rectangle(4, 4)
        solution = solve_planar(PlanarPolygonCase(square, 'te', 2, 3))
        identity = PlanarPiecewiseMapping(square, square)
        result = track_planar_modes(solution, solution, replace(request, mapping=identity))
        self.assertEqual(result['status'], 'UNVERIFIED')
        self.assertIn('guard mode', ' '.join(result['verification_reasons']))
        self.assertEqual(result['current_mode_ids'], [None])
        with self.assertRaisesRegex(ValueError, 'max_overlay_triangles'):
            planar_piecewise_overlay(mapping.previous_partition, mapping.current_partition, mapping,
                                     max_overlay_triangles=3)
        from superfish_ng.planar_piecewise_overlap import _candidate_pairs
        def drop_pairs(a, b, budget):
            pairs = list(_candidate_pairs(a, b, budget))
            return iter(pairs[1:])
        with patch('superfish_ng.planar_piecewise_overlap._candidate_pairs', side_effect=drop_pairs):
            with self.assertRaisesRegex(ValueError, 'exactly cover'):
                planar_piecewise_overlay(mapping.previous_partition, mapping.current_partition, mapping)

    def test_real_nonaffine_independent_refinements_and_original_rf_unchanged(self):
        mapping = mild_piecewise_mapping()
        for pol in ('te', 'tm'):
            frequencies = []
            for grid in (4, 8):
                old = solve_planar(PlanarPolygonCase(rectangle(grid, grid, 1., .5), pol, 2, 3))
                new = solve_planar(PlanarPolygonCase(rectangle(grid+2, grid+2, 1.03125, .5, True), pol, 2, 3))
                coefficients = [s.coefficients.copy() for s in (old, new)]
                rf = [planar_quantities(s) for s in (old, new)]
                request = PlanarTrackingRequest(1, 1, ['fundamental'], mapping=mapping)
                result = track_planar_modes(old, new, request)
                self.assertEqual(result['status'], 'PASS')
                self.assertEqual(result['current_mode_ids'], ['fundamental'])
                for solution, before, quantities in zip((old, new), coefficients, rf):
                    np.testing.assert_array_equal(solution.coefficients, before)
                    self.assertEqual(planar_quantities(solution), quantities)
                exact = C0/2*np.hypot(1/1.03125, 2. if pol == 'tm' else 0.)
                frequencies.append(float(new.frequencies_hz[0]))
                self.assertLess(abs(frequencies[-1]/exact-1), .003)
            self.assertLess(abs(frequencies[1]/frequencies[0]-1), .003)

    def test_owned_pair_history_move_cli_and_rehashed_result_rejected(self):
        mapping = mild_piecewise_mapping()
        request = PlanarTrackingRequest(1, 1, ['fundamental'], mapping=mapping)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = [root/'old', root/'new']
            originals = []
            for path, mesh in zip(paths, (rectangle(4, 4, 1., .5), rectangle(6, 6, 1.03125, .5, True))):
                solution = solve_planar(PlanarPolygonCase(mesh, 'te', 2, 3))
                save_planar_run(solution.case, solution, path)
                originals.append({p.name: p.read_bytes() for p in path.iterdir()})
            result = execute_planar_tracking(*paths, request, root/'pair')
            self.assertEqual(result['status'], 'PASS')
            for data, side in zip(originals, ('previous', 'current')):
                self.assertEqual({p.name: p.read_bytes() for p in (root/'pair'/side).iterdir()}, data)
            history = execute_planar_history([root/'pair'], PlanarTrackingHistoryRequest(1), root/'history')
            self.assertEqual(history['current_mode_ids'], ['fundamental'])
            shutil.move(root/'pair', root/'moved')
            for path in paths:
                shutil.rmtree(path)
            self.assertEqual(read_planar_tracking(root/'moved'), result)
            self.assertEqual(read_planar_history(root/'history'), history)
            run = subprocess.run([sys.executable, '-m', 'superfish_ng', 'replay-planar-tracking',
                                  str(root/'moved')], capture_output=True, text=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(run.stdout), result)
            data = json.loads((root/'moved'/'tracking-results.json').read_text())
            data['physical_mapping']['mapping_cells'][0] += 1
            (root/'moved'/'tracking-results.json').write_text(json.dumps(data))
            manifest = json.loads((root/'moved'/'manifest.json').read_text())
            manifest['files']['tracking-results.json'] = hashlib.sha256((root/'moved'/'tracking-results.json').read_bytes()).hexdigest()
            (root/'moved'/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'full native'):
                read_planar_tracking(root/'moved')

    def test_real_worker_cancel_restart_and_native_preservation(self):
        mapping = mild_piecewise_mapping()
        request = PlanarTrackingRequest(1, 1, ['fundamental'], mapping=mapping)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = [root/'old', root/'new']
            for path, mesh in zip(paths, (rectangle(4, 4, 1., .5), rectangle(6, 6, 1.03125, .5, True))):
                solution = solve_planar(PlanarPolygonCase(mesh, 'te', 2, 3))
                save_planar_run(solution.case, solution, path)
            originals = [{p.name: p.read_bytes() for p in path.iterdir()} for path in paths]
            manager = JobManager(root/'workspace')
            try:
                cancelled = manager.start_planar_tracking(*paths, request)
                deadline = time.monotonic()+30
                while manager.status(cancelled)['status'] == 'queued' and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertEqual(manager.status(cancelled)['status'], 'running')
                self.assertEqual(manager.cancel(cancelled)['status'], 'cancelled')
                self.assertIsNotNone(manager.processes[cancelled].poll())
                identifier = manager.start_planar_tracking(*paths, request)
                self.assertEqual(manager.processes[identifier].wait(timeout=60), 0)
                self.assertEqual(manager.status(identifier, verify=True)['status'], 'complete')
                manager.close()
                manager = JobManager(root/'workspace')
                self.assertEqual(manager.status(identifier, verify=True)['status'], 'complete')
                self.assertEqual(read_planar_tracking(manager.directory(identifier))['current_mode_ids'], ['fundamental'])
                self.assertEqual([{p.name: p.read_bytes() for p in path.iterdir()} for path in paths], originals)
            finally:
                manager.close()


if __name__ == '__main__':
    unittest.main()
