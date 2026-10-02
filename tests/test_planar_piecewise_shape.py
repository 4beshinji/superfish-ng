# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng.planar import solve_planar, planar_quantities
from superfish_ng.planar_mesh import PlanarMesh
from superfish_ng.planar_polygon import PlanarPolygonCase
from superfish_ng.planar_project import PlanarProject
from superfish_ng.planar_piecewise_shape import PlanarPiecewiseShapeLaw
from superfish_ng.planar_piecewise_shape_mapping import PlanarPiecewiseShapeMapping, piecewise_shape_overlay
from superfish_ng.planar_piecewise_mapping import PlanarPiecewiseMapping
from superfish_ng.planar_piecewise_overlap import planar_piecewise_overlay
from superfish_ng.planar_refinement import refine_planar_mesh
from superfish_ng.planar_tracking import PlanarTrackingRequest, track_planar_modes
from superfish_ng.planar_tracking_fields import _electric_grams
from superfish_ng.planar_tuning import validate_planar_tune, trial_planar_project, planar_tune_mapping
from test_planar_tracking_exact_affine import rectangle
from test_planar_tuning import request


def law_for(mesh, displacement, bounds=(0., 1.)):
    return PlanarPiecewiseShapeLaw(mesh, displacement, bounds)


def nonaffine_law(mesh):
    displacement = []
    for x, _ in mesh.points_xy_m:
        offset = float(max(x-.5, 0.))
        displacement.append([[0., offset/8], [0., offset/4]])
    return law_for(mesh, displacement)


class PlanarPiecewiseShapeTests(unittest.TestCase):
    def test_closed_interval_jacobian_roots_sign_and_small_positive_contrast(self):
        mesh = rectangle(2, 2)
        # x is scaled by (p-3/8)^2: endpoints are positive but the interior
        # even-multiplicity root cannot be detected by sign-change sampling.
        def stretch(coefficients):
            return [[[float(x)*v for v in coefficients], [0.]] for x, _ in mesh.points_xy_m]
        for coefficients in ((9/64-1, -.75, 1.), (-1., 1.), (-2.,)):
            with self.subTest(coefficients=coefficients), self.assertRaisesRegex(ValueError, 'Jacobian'):
                law_for(mesh, stretch(coefficients))
        positive = law_for(mesh, stretch((9/64-1+2.**-48, -.75, 1.)))
        points = positive.exact_points(.375)
        for original, actual in zip(mesh.points_xy_m, points):
            self.assertEqual(actual[0], Fraction(float(original[0]))*Fraction(2)**-48)
            self.assertEqual(actual[1], Fraction(float(original[1])))

    def test_nonaffine_area_all_boundary_vertices_and_original_regeneration(self):
        mesh = rectangle(4, 4, 1., .5)
        project = PlanarProject(PlanarPolygonCase(mesh, modes=3), 'm')
        law = nonaffine_law(mesh)
        original = project.to_dict()
        end = law.project(project, 1.)
        self.assertEqual(len(end.case.mesh.polygon_xy_m), len(mesh.boundary_edges))
        self.assertEqual(end.display_length_unit, 'm')
        self.assertEqual(end.case.normalization_j_per_m, project.case.normalization_j_per_m)
        for p in (1., .25, .75, 0., 1.):
            candidate = law.project(project, p)
            # det(left)=1; det(right)=1+p/8, with half of the area each.
            self.assertAlmostEqual(candidate.case.mesh.area_m2, .5*(1+p/16), places=14)
        self.assertEqual(law.project(project, 1.).to_dict(), end.to_dict())
        self.assertEqual(project.to_dict(), original)
        with self.assertRaisesRegex(ValueError, 'interval'):
            law.project(project, 1.01)

    def test_positive_local_jacobians_do_not_override_global_boundary_intersection(self):
        # A thin C-shaped ribbon has positive cells throughout this linear
        # motion. Its lower end nevertheless crosses the other end's boundary.
        lower = [[0., 0.], [1., 0.], [1., 1.], [0., 1.], [0., .2]]
        upper = [[0., .1], [.9, .1], [.9, .9], [.1, .9], [.1, .2]]
        points = np.array(lower+upper)
        cells = [cell for i in range(4) for cell in ((i, i+1, i+6), (i, i+6, i+5))]
        boundary = list(range(5))+list(range(9, 4, -1))
        mesh = PlanarMesh.create(points[boundary], points, cells)
        displacement = [[[0.], [0.]] for _ in points]
        for i in (4, 9):
            displacement[i][1] = [0., -.15]
        law = law_for(mesh, displacement)  # Whole-interval local test passes.
        project = PlanarProject(PlanarPolygonCase(mesh))
        law.project(project, 0.)
        with self.assertRaisesRegex(ValueError, 'intersect|overlap|T junction'):
            law.project(project, 1.)

    def test_strict_declaration_project_binding_and_preconstruction_budget(self):
        mesh = rectangle(2, 2)
        law = nonaffine_law(mesh)
        self.assertEqual(PlanarPiecewiseShapeLaw.from_dict(law.to_dict()).to_dict(), law.to_dict())
        for change in ({'kind': 'polynomial_affine_xy'}, {'parameter_unit': 'm'},
                       {'displacement_coefficient_unit': 'mm'}, {'bounds': (0., 1.)},
                       {'max_triangles': True}, {'extra': 1}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                PlanarPiecewiseShapeLaw.from_dict(dict(law.to_dict(), **change))
        for coefficient in (True, '0', float('nan'), 10**400):
            data = law.to_dict()
            data['displacement_xy_m_coefficients'][0][0] = [coefficient]
            with self.subTest(coefficient=coefficient), self.assertRaises(ValueError):
                PlanarPiecewiseShapeLaw.from_dict(data)
        data = law.to_dict(); data['max_triangles'] = 1
        with patch.object(PlanarMesh, 'create', side_effect=AssertionError('too late')):
            with self.assertRaisesRegex(ValueError, 'exceeds'):
                PlanarPiecewiseShapeLaw.from_dict(data)
        other = PlanarProject(PlanarPolygonCase(rectangle(2, 2, 2., 1.)))
        with self.assertRaisesRegex(ValueError, 'differs'):
            law.project(other, 0.)
        tiny = [[[0.], [0.]] for _ in mesh.points_xy_m]
        tiny[0][0] = [0., 2.**-1074]
        underflow = law_for(mesh, tiny)
        project = PlanarProject(PlanarPolygonCase(mesh))
        with self.assertRaisesRegex(ValueError, 'binary64'):
            underflow.project(project, .25)

    def test_parent_partition_transport_matches_exact_nonaffine_overlay_and_tamper_rejected(self):
        project = PlanarProject(PlanarPolygonCase(rectangle(4, 4, 1., .5), modes=3))
        law = nonaffine_law(project.case.mesh)
        old = law.project(project, 0.).case.mesh
        new_base = law.project(project, 1.).case.mesh
        new = refine_planar_mesh(new_base)
        declaration = PlanarPiecewiseMapping(old, new_base)
        for reverse in (False, True):
            a, b = (new, old) if reverse else (old, new)
            mapping = PlanarPiecewiseShapeMapping(project, law, float(reverse), float(not reverse),
                                                int(reverse), int(not reverse))
            request_ = PlanarTrackingRequest(1, 1, ['first'], mapping=mapping)
            self.assertEqual(request_.to_dict()['tracking_version'], 10)
            self.assertEqual(PlanarTrackingRequest.from_dict(request_.to_dict()).to_dict(), request_.to_dict())
            for version in (9, 10., True, 11):
                with self.subTest(version=version), self.assertRaises(ValueError):
                    PlanarTrackingRequest.from_dict(dict(request_.to_dict(), tracking_version=version))
            overlay, transport = piecewise_shape_overlay(a, b, mapping)
            exact = planar_piecewise_overlay(a, b, declaration.reversed() if reverse else declaration)
            self.assertAlmostEqual(sum(overlay.reference_determinants)/2, a.area_m2, places=14)
            for mesh, cells, bary in ((a, overlay.previous_cells, overlay.previous_vertex_barycentric),
                                      (b, overlay.current_cells, overlay.current_vertex_barycentric)):
                original = mesh.points_xy_m[mesh.triangles]
                children = bary @ original[cells]
                u, v = children[:, 1]-children[:, 0], children[:, 2]-children[:, 0]
                child_area2 = u[:, 0]*v[:, 1]-u[:, 1]*v[:, 0]
                u, v = original[:, 1]-original[:, 0], original[:, 2]-original[:, 0]
                np.testing.assert_allclose(np.bincount(cells, weights=child_area2),
                    u[:, 0]*v[:, 1]-u[:, 1]*v[:, 0], rtol=2e-14, atol=0.)
            for pol in ('te', 'tm'):
                sa, sb = [solve_planar(PlanarPolygonCase(mesh, pol, 2, 3)) for mesh in (a, b)]
                actual = _electric_grams(sa, sb, overlay, 5, current_to_previous_rotation=transport)
                expected = _electric_grams(sa, sb, exact.overlay, 5,
                                           current_to_previous_rotation=exact.current_to_previous_linear)
                norms = (np.sqrt(np.diag(actual[0])), np.sqrt(np.diag(actual[2])))
                for x, y, left, right in zip(actual, expected, (norms[0], norms[0], norms[1]),
                                             (norms[0], norms[1], norms[1])):
                    np.testing.assert_allclose((x-y)/left[:, None]/right[None, :], 0., atol=3e-12)
            changed_points = b.points_xy_m.copy()
            changed_points[1, 0] = np.nextafter(changed_points[1, 0], np.inf)
            changed = replace(b, points_xy_m=changed_points)
            with self.assertRaisesRegex(ValueError, 'differs|boundary|polygon'):
                piecewise_shape_overlay(a, changed, mapping)
            with self.assertRaisesRegex(ValueError, 'max_overlay_triangles'):
                piecewise_shape_overlay(a, b, mapping, max_overlay_triangles=1)

    def test_real_similarity_rotation_frequency_original_fields_and_rf(self):
        rotation = np.array([[0., -1.], [1., 0.]])
        mesh = rectangle(4, 4, .25, .5)
        displacement = [[[0., float(-x-2*y)], [0., float(2*x-y)]] for x, y in mesh.points_xy_m]
        law = law_for(mesh, displacement)
        for pol in ('te', 'tm'):
            project = PlanarProject(PlanarPolygonCase(mesh, pol, 2, 3, normalization_j_per_m=3.))
            old, new = [solve_planar(law.project(project, value).case) for value in (0., 1.)]
            cells = np.arange(len(mesh.triangles)); bary = np.tile([.2, .3, .5], (len(cells), 1))
            fa, fb = [solution.fields_in_cells(cells, bary, 0) for solution in (old, new)]
            scalar = 'Hz_real_A_per_m' if pol == 'te' else 'Ez_real_V_per_m'
            vector = ('Ex_quadrature_V_per_m', 'Ey_quadrature_V_per_m') if pol == 'te' else ('Hx_quadrature_A_per_m', 'Hy_quadrature_A_per_m')
            sign = np.sign(fa[scalar] @ fb[scalar])
            np.testing.assert_allclose(sign*2*fb[scalar], fa[scalar], rtol=2e-11, atol=2e-10*np.max(abs(fa[scalar])))
            expected = np.column_stack([fa[key] for key in vector]) @ rotation.T / 2
            np.testing.assert_allclose(sign*np.column_stack([fb[key] for key in vector]), expected,
                                       rtol=2e-11, atol=2e-10*np.max(abs(expected)))
            self.assertAlmostEqual(new.frequencies_hz[0]/old.frequencies_hz[0], .5, delta=2e-12)
            before, after = [planar_quantities(s) for s in (old, new)]
            self.assertAlmostEqual(after['geometry_factor_ohm']/before['geometry_factor_ohm'], 1., delta=2e-11)
            self.assertAlmostEqual(after['q0']/before['q0'], np.sqrt(2), delta=2e-11)
            self.assertAlmostEqual(after['electric_energy_j_per_m'], 1.5, places=11)
            self.assertAlmostEqual(after['magnetic_energy_j_per_m'], 1.5, places=11)
            result = track_planar_modes(old, new, PlanarTrackingRequest(1, 1, ['first'],
                mapping=PlanarPiecewiseShapeMapping(project, law, 0., 1.)))
            self.assertEqual(result['status'], 'PASS')
            self.assertEqual(result['result_version'], 10)
            self.assertEqual(result['physical_mapping']['name'], 'polynomial_piecewise_xy_reference')

    def test_new_tune_request_trial_generation_refinement_and_old_version_refusal(self):
        project = PlanarProject(PlanarPolygonCase(rectangle(4, 4, 1., .5), modes=3))
        law = nonaffine_law(project.case.mesh)
        raw = request()
        raw.update(schema_version=4, parameter='deformation', project=project.to_dict(), bounds=[0., 1.],
                   shape_law=law.to_dict(), initial_ids=['first'], mode_id='first',
                   identity_recovery=dict(anchor_selection='latest_resolved_trial', controls=raw['controls']))
        validate_planar_tune(raw)
        old = trial_planar_project(raw, 0., 'search')
        new = trial_planar_project(raw, 1., 'refinement')
        self.assertEqual(len(new.case.mesh.triangles), 4*len(old.case.mesh.triangles))
        mapping = planar_tune_mapping(raw, dict(phase='search', value=0.), dict(phase='refinement', value=1.))
        piecewise_shape_overlay(old.case.mesh, new.case.mesh, mapping)
        for key, value in (('schema_version', True), ('schema_version', 3), ('parameter', 'uniform_scale'),
                           ('bounds', [0., .5]), ('max_triangles', 1), ('extra', 1)):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                validate_planar_tune(dict(raw, **{key: value}))
        bad = deepcopy(raw); bad['identity_recovery']['anchor_selection'] = 'rank'
        with self.assertRaises(ValueError):
            validate_planar_tune(bad)


if __name__ == '__main__':
    unittest.main()
