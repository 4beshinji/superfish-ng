# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng.planar_affine_shape import PlanarAffineShapeLaw, explicit_planar_project
from superfish_ng.planar_affine_shape_mapping import PlanarAffineShapeMapping, affine_shape_overlay
from superfish_ng.planar_project import PlanarProject
from superfish_ng.planar_polygon import PlanarPolygonCase
from superfish_ng.planar_refinement import refine_planar_mesh
from superfish_ng.planar_tracking import PlanarTrackingRequest, track_planar_modes
from superfish_ng.planar_tracking_fields import _electric_grams
from superfish_ng.planar import PlanarCase, solve_planar
from superfish_ng.planar_tuning import validate_planar_tune, trial_planar_project, execute_planar_tune, replay_planar_tune
from test_planar_tracking_exact_affine import rectangle
from test_planar_tuning import request


class PlanarAffineShapeMappingTests(unittest.TestCase):
    def test_strict_new_request_units_arrays_and_bounds_before_trial(self):
        law = PlanarAffineShapeLaw([[[1, .25], [0]], [[0], [1]]], [[0], [0]], [0, 1])
        raw = request()
        raw.update(schema_version=2, parameter='deformation', bounds=[0., 1.], shape_law=law.to_dict())
        changes = [lambda r: r['shape_law'].update(bounds=(0., 1.)),
                   lambda r: r['shape_law'].update(linear_xy_coefficients=(((1.,), (0.,)), ((0.,), (1.,)))),
                   lambda r: r['shape_law'].update(translation_coefficient_unit='mm'),
                   lambda r: r.update(bounds=[0., .5]),
                   lambda r: r.update(parameter='uniform_scale'),
                   lambda r: r.update(schema_version=True),
                   lambda r: r.update(extra='ignored')]
        for change in changes:
            bad = deepcopy(raw); change(bad)
            with self.assertRaises(ValueError): validate_planar_tune(bad)
        self.assertEqual(PlanarAffineShapeLaw.from_dict(law.to_dict()), law)

    def test_te_tm_original_fields_rotation_scale_and_fixed_energy_per_length(self):
        law = PlanarAffineShapeLaw([[[1, -1], [0, -2]], [[0, 2], [1, -1]]],
                                  [[0, .125], [0, .25]], [0, 1])
        rotation = np.array([[0., -1.], [1., 0.]])
        for polarization in ('te', 'tm'):
            project = PlanarProject(PlanarPolygonCase(rectangle(4, 4, .25, .5), modes=3,
                                                     polarization=polarization, normalization_j_per_m=3.))
            a, b = [solve_planar(law.project(project, p).case) for p in (0., 1.)]
            cells = np.arange(len(a.case.mesh.triangles))
            bary = np.tile([.2, .3, .5], (len(cells), 1))
            fa, fb = [s.fields_in_cells(cells, bary, 0) for s in (a, b)]
            scalar = 'Hz_real_A_per_m' if polarization == 'te' else 'Ez_real_V_per_m'
            vector = ('Ex_quadrature_V_per_m', 'Ey_quadrature_V_per_m') if polarization == 'te' else ('Hx_quadrature_A_per_m', 'Hy_quadrature_A_per_m')
            sign = np.sign(fa[scalar] @ fb[scalar])
            self.assertLess(np.linalg.norm(sign*2*fb[scalar]-fa[scalar])/np.linalg.norm(fa[scalar]), 2e-11)
            expected = np.column_stack([fa[k] for k in vector]) @ rotation.T / 2
            actual = sign*np.column_stack([fb[k] for k in vector])
            self.assertLess(np.linalg.norm(actual-expected)/np.linalg.norm(expected), 2e-11)
            self.assertAlmostEqual(b.frequencies_hz[0]/a.frequencies_hz[0], .5, delta=2e-12)
            self.assertEqual(b.case.normalization_j_per_m, 3.)
            overlay, transport = affine_shape_overlay(a.case.mesh, b.case.mesh, PlanarAffineShapeMapping(project, law, 0., 1.))
            aa, ab, bb = _electric_grams(a, b, overlay, 5, current_to_previous_rotation=transport)
            self.assertAlmostEqual(abs(ab[0, 0])/np.sqrt(aa[0, 0]*bb[0, 0]), 1., delta=2e-12)

    def test_nested_partitions_area_transport_and_exact_regeneration(self):
        project = PlanarProject(PlanarPolygonCase(rectangle(2, 2, .25, .5), modes=3))
        law = PlanarAffineShapeLaw([[[1, .25], [0, .125]], [[0], [1]]], [[.03125], [-.125]], [0, 1])
        a = law.project(project, 0.).case.mesh
        b = refine_planar_mesh(law.project(project, 1.).case.mesh)
        for reverse in (False, True):
            old, new = (b, a) if reverse else (a, b)
            mapping = PlanarAffineShapeMapping(project, law, float(reverse), float(not reverse),
                                              int(reverse), int(not reverse))
            overlay, transform = affine_shape_overlay(old, new, mapping)
            self.assertAlmostEqual(overlay.reference_determinants.sum()/2, old.area_m2)
            matrix = np.array([[1.25, .125], [0., 1.]])
            if reverse: matrix = np.linalg.inv(matrix)
            expected = np.linalg.det(matrix)*np.linalg.inv(matrix)
            np.testing.assert_allclose(transform, np.tile(expected, (len(transform), 1, 1)), atol=1e-14)
            for mesh, cells, bary in ((old, overlay.previous_cells, overlay.previous_vertex_barycentric),
                                      (new, overlay.current_cells, overlay.current_vertex_barycentric)):
                vertices = bary @ mesh.points_xy_m[mesh.triangles[cells]]
                u, v = vertices[:, 1]-vertices[:, 0], vertices[:, 2]-vertices[:, 0]
                area = (u[:, 0]*v[:, 1]-u[:, 1]*v[:, 0])/2
                original = mesh.points_xy_m[mesh.triangles]
                u, v = original[:, 1]-original[:, 0], original[:, 2]-original[:, 0]
                np.testing.assert_allclose(np.bincount(cells, weights=area),
                                           (u[:, 0]*v[:, 1]-u[:, 1]*v[:, 0])/2, atol=1e-15)
            with self.assertRaisesRegex(ValueError, 'exceeds'):
                affine_shape_overlay(old, new, mapping, max_overlay_triangles=1)
        changed = deepcopy(b); object.__setattr__(changed, 'points_xy_m', b.points_xy_m.copy())
        changed.points_xy_m[0, 0] = np.nextafter(changed.points_xy_m[0, 0], np.inf)
        with self.assertRaisesRegex(ValueError, 'differs'):
            affine_shape_overlay(a, changed, PlanarAffineShapeMapping(project, law, 0., 1., 0, 1))

    def test_actual_electric_grams_match_existing_exact_affine_comparison(self):
        from superfish_ng.planar_tracking_exact_mapping import PolygonExactAffineRemeshMapping, polygon_exact_affine_remesh_overlay
        project = PlanarProject(PlanarPolygonCase(rectangle(4, 4, .25, .5), modes=3))
        law = PlanarAffineShapeLaw([[[1], [0, .25]], [[0], [1]]], [[0], [0]], [0, 1])
        a, b = [solve_planar(law.project(project, p).case) for p in (0., 1.)]
        overlay, transform = affine_shape_overlay(a.case.mesh, b.case.mesh, PlanarAffineShapeMapping(project, law, 0., 1.))
        exact = PolygonExactAffineRemeshMapping([[1., .25], [0., 1.]])
        independent = polygon_exact_affine_remesh_overlay(a.case.mesh, b.case.mesh, exact)
        actual = _electric_grams(a, b, overlay, 5, current_to_previous_rotation=transform)
        expected = _electric_grams(a, b, independent, 5, current_to_previous_rotation=exact.current_to_previous_linear)
        norms = [np.sqrt(np.diag(actual[0])), np.sqrt(np.diag(actual[2]))]
        for x, y, left, right in zip(actual, expected, (norms[0], norms[0], norms[1]),
                                     (norms[0], norms[1], norms[1])):
            np.testing.assert_allclose((x-y)/left[:, None]/right[None, :], 0., atol=2e-12)

    def test_real_tune_rectangle_equivalence_and_saved_refinement(self):
        raw = request()
        law = PlanarAffineShapeLaw([[[1, 1/4], [0]], [[0], [1]]], [[0], [0]], [0, 1])
        raw.update(schema_version=2, parameter='deformation', bounds=[0., 1.], shape_law=law.to_dict())
        # Same physical upper width as the existing dimension request.
        raw['project'] = PlanarProject(PlanarCase(.176, .2, nx=6, ny=6, modes=3)).to_dict()
        validate_planar_tune(raw)
        original = PlanarProject.from_dict(raw['project'])
        expected = solve_planar(replace(original.case, width_m=.22))
        candidate = trial_planar_project(raw, 1., 'search')
        actual = solve_planar(candidate.case)
        np.testing.assert_allclose(actual.frequencies_hz, expected.frequencies_hz, rtol=2e-12)
        with tempfile.TemporaryDirectory() as tmp:
            first = execute_planar_tune(raw, Path(tmp)/'first', max_new_trials=2)
            self.assertEqual(first['status'], 'PAUSED')
            final = execute_planar_tune(raw, Path(tmp)/'final', checkpoint=first)
            self.assertEqual(final['status'], 'TUNED')
            self.assertEqual(replay_planar_tune(final), final)
            self.assertEqual(final['trials'][-1]['tracking']['result_version'], 8)
            self.assertTrue(final['decision']['mesh_difference_met'])
            self.assertLess(abs(final['trials'][-1]['frequency_hz']/raw['target_hz']-1), 1e-4)
            bad = deepcopy(raw); bad['shape_law']['linear_xy_coefficients'][0][0] = [9/64, -.75, 1]
            with self.assertRaisesRegex(ValueError, 'determinant'):
                execute_planar_tune(bad, Path(tmp)/'invalid')
            self.assertFalse((Path(tmp)/'invalid').exists())


if __name__ == '__main__': unittest.main()
