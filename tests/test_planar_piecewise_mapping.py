# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import json
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng.fem import triangle_quadrature
from superfish_ng.planar_mesh import PlanarMesh
from superfish_ng.planar_piecewise_mapping import (
    PlanarPiecewiseMapping, verify_planar_piecewise_domains)
from superfish_ng.planar_tracking_exact_mapping import PolygonExactAffineRemeshMapping
from test_planar_tracking_exact_affine import rectangle


def strip_mapping(scale=1., shear=0.):
    polygon = np.array([[0., 0.], [1., 0.], [1., 1.], [0., 1.]])*scale
    points = np.array([[0., 0.], [.5, 0.], [1., 0.],
                       [0., 1.], [.5, 1.], [1., 1.]])*scale
    cells = [[0, 1, 4], [0, 4, 3], [1, 2, 5], [1, 5, 4]]
    previous = PlanarMesh.create(polygon, points, cells)
    current_points = points.copy()
    current_points[:, 0] += np.maximum(points[:, 0]-.5*scale, 0.)
    current_points[:, 1] += shear*np.maximum(points[:, 0]-.5*scale, 0.)
    # The piecewise shear has genuine corners on the horizontal boundaries.
    current_polygon = current_points[[0, 1, 2, 5, 4, 3]]
    current = PlanarMesh.create(current_polygon, current_points, cells)
    return PlanarPiecewiseMapping(previous, current)


class PlanarPiecewiseMappingTests(unittest.TestCase):
    def test_known_nonlinear_map_area_and_polynomial_integrals(self):
        # Analytic F=(x,y) for x<=1/2; F=(2x-1/2,y) otherwise.
        # This is a globally non-affine homeomorphism with J=1 or 2.
        for scale in (2.**-12, 1., 2.**12):
            mapping = strip_mapping(scale)
            np.testing.assert_array_equal(mapping.jacobian_determinants, [1., 1., 2., 2.])
            old_vertices = mapping.previous_partition.points_xy_m[mapping.previous_partition.triangles]
            new_vertices = mapping.current_partition.points_xy_m[mapping.current_partition.triangles]
            edge1, edge2 = old_vertices[:, 1]-old_vertices[:, 0], old_vertices[:, 2]-old_vertices[:, 0]
            area2 = edge1[:, 0]*edge2[:, 1]-edge1[:, 1]*edge2[:, 0]
            for px, py in ((0, 0), (1, 0), (0, 1), (2, 1), (2, 2), (3, 1)):
                old_moment = new_moment = 0.
                for bary, weight in triangle_quadrature(5):
                    xy = np.einsum('j,njk->nk', bary, old_vertices)/scale
                    uv = np.einsum('j,njk->nk', bary, new_vertices)/scale
                    measure = weight*area2*mapping.jacobian_determinants
                    old_moment += np.sum(measure*xy[:, 0]**px*xy[:, 1]**py)
                    new_moment += np.sum(measure*uv[:, 0]**px*uv[:, 1]**py)
                self.assertAlmostEqual(old_moment/scale**2,
                    (2.-.5**(px+1))/((px+1)*(py+1)), places=12)
                self.assertAlmostEqual(new_moment/scale**2,
                    1.5**(px+1)/((px+1)*(py+1)), places=12)
            points = np.array([[.25, .125], [.5, .25], [.75, .25]])*scale
            image = mapping.map_points(points, [0, 0, 2])
            np.testing.assert_array_equal(image/scale, [[.25, .125], [.5, .25], [1., .25]])
            np.testing.assert_array_equal(mapping.reversed().map_points(image, [0, 0, 2]), points)
            self.assertFalse(image.flags.writeable)

    def test_interface_continuity_inverse_and_xy_curl_transport(self):
        mapping = strip_mapping(shear=.25)
        # Each point is on a shared edge and must have one image.
        for cells, xy in (([0, 3], [.5, .25]), ([0, 1], [.25, .5]),
                          ([2, 3], [.75, .5])):
            image = mapping.map_points([xy, xy], cells)
            np.testing.assert_array_equal(image[0], image[1])
            np.testing.assert_array_equal(mapping.reversed().map_points(image, cells), [xy, xy])
        rotation = np.array([[0., 1.], [-1., 0.]])
        gradient = np.array([.75, -.5])  # H=x*.75-y*.5; E proportional to curl H.
        inverse = mapping.reversed()
        for a, b, det, reverse_a, reverse_b in zip(mapping.linear_xy,
                mapping.current_to_previous_linear, mapping.jacobian_determinants,
                inverse.linear_xy, inverse.current_to_previous_linear):
            # grad_current=A^-T grad_previous; adj(A) E_current=E_previous.
            current_e = rotation@np.linalg.solve(a.T, gradient)
            np.testing.assert_allclose(b@current_e, rotation@gradient, rtol=1e-14, atol=0.)
            np.testing.assert_allclose(reverse_a@a, np.eye(2), rtol=0., atol=0.)
            np.testing.assert_allclose(reverse_b@b, np.eye(2), rtol=0., atol=0.)
            self.assertEqual(np.linalg.det(a), det)
        for array in (mapping.linear_xy, mapping.current_to_previous_linear, mapping.jacobian_determinants):
            self.assertFalse(array.flags.writeable)

    def test_affine_limit_matches_existing_exact_transport(self):
        previous = rectangle(2, 2)
        a = np.array([[1., .25], [.5, 2.]])
        translation = np.array([.125, -.25])
        current = PlanarMesh.create(previous.polygon_xy_m@a.T+translation,
                                   previous.points_xy_m@a.T+translation, previous.triangles)
        mapping = PlanarPiecewiseMapping(previous, current)
        exact = PolygonExactAffineRemeshMapping(a.tolist(), tuple(map(float, translation)))
        np.testing.assert_array_equal(mapping.linear_xy, np.broadcast_to(a, mapping.linear_xy.shape))
        np.testing.assert_array_equal(mapping.current_to_previous_linear,
            np.broadcast_to(exact.current_to_previous_linear, mapping.linear_xy.shape))
        indices = np.arange(len(previous.triangles))
        points = previous.points_xy_m[previous.triangles[:, 0]]
        np.testing.assert_array_equal(mapping.map_points(points, indices), points@a.T+translation)

    def test_independent_native_meshes_every_cell_and_same_area_wrong_domain(self):
        mapping = strip_mapping()
        previous = rectangle(3, 4, flipped=True)
        current = rectangle(5, 3, width=1.5)
        for a, b, direction in ((previous, current, mapping), (current, previous, mapping.reversed())):
            partitions = verify_planar_piecewise_domains(a, b, direction)
            for overlay, mesh, declared in ((partitions.previous, a, direction.previous_partition),
                                           (partitions.current, b, direction.current_partition)):
                vertices = mesh.points_xy_m[mesh.triangles]
                u, v = vertices[:, 1]-vertices[:, 0], vertices[:, 2]-vertices[:, 0]
                expected = u[:, 0]*v[:, 1]-u[:, 1]*v[:, 0]
                np.testing.assert_allclose(np.bincount(overlay.current_cells,
                    weights=overlay.reference_determinants), expected, rtol=3e-14)
                reconstructed = np.einsum('nij,njk->nik', overlay.current_vertex_barycentric,
                                         vertices[overlay.current_cells])
                other = np.einsum('nij,njk->nik', overlay.previous_vertex_barycentric,
                                 declared.points_xy_m[declared.triangles[overlay.previous_cells]])
                np.testing.assert_allclose(reconstructed, other, rtol=0., atol=5e-16)
                self.assertAlmostEqual(sum(overlay.reference_determinants)/2, mesh.area_m2, places=13)
        shifted = PlanarMesh.create(current.polygon_xy_m+[.125, 0.],
                                   current.points_xy_m+[.125, 0.], current.triangles)
        self.assertEqual(shifted.area_m2, current.area_m2)
        with self.assertRaisesRegex(ValueError, 'polygons'):
            verify_planar_piecewise_domains(previous, shifted, mapping)

    def test_missing_duplicate_reversed_and_folded_partitions_fail(self):
        mapping = strip_mapping()
        for defect in ('missing', 'duplicate', 'reversed', 'folded'):
            data = mapping.to_dict()
            mesh = data['current_partition']
            if defect == 'missing':
                mesh['triangles'].pop()
            elif defect == 'duplicate':
                mesh['triangles'].append(mesh['triangles'][0])
            elif defect == 'reversed':
                mesh['triangles'][0] = mesh['triangles'][0][::-1]
            else:
                mesh['points_xy_m'][1] = [1.75, .25]
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                PlanarPiecewiseMapping.from_dict(data)
        reordered = replace(mapping.current_partition, triangles=mapping.current_partition.triangles[::-1])
        with self.assertRaisesRegex(ValueError, 'connectivity'):
            PlanarPiecewiseMapping(mapping.previous_partition, reordered)

    def test_roundoff_boundary_departure_rejected_exactly(self):
        mapping = strip_mapping()
        points = mapping.previous_partition.points_xy_m.copy()
        points[1, 1] = 2.**-54
        # Existing local mesh geometry permits construction roundoff here.
        bowed = PlanarMesh.create(mapping.previous_partition.polygon_xy_m, points,
                                  mapping.previous_partition.triangles)
        with self.assertRaisesRegex(ValueError, 'boundary'):
            PlanarPiecewiseMapping(bowed, mapping.current_partition)
        with self.assertRaisesRegex(ValueError, 'boundary'):
            verify_planar_piecewise_domains(bowed, mapping.current_partition, mapping)

    def test_strict_declaration_budget_and_point_errors(self):
        mapping = strip_mapping()
        self.assertEqual(PlanarPiecewiseMapping.from_dict(json.loads(json.dumps(mapping.to_dict()))).to_dict(), mapping.to_dict())
        for change in ({'mapping_version': True}, {'mapping_version': 1.}, {'mapping_version': 2},
                       {'name': 'nonlinear'}, {'extra': 1}, {'max_partition_triangles': True},
                       {'max_candidate_tests': 0}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                PlanarPiecewiseMapping.from_dict(dict(mapping.to_dict(), **change))
        data = mapping.to_dict()
        data['max_partition_triangles'] = 3
        with patch.object(PlanarMesh, 'create', side_effect=AssertionError('too late')):
            with self.assertRaisesRegex(ValueError, 'max_partition_triangles'):
                PlanarPiecewiseMapping.from_dict(data)
            with self.assertRaisesRegex(ValueError, 'max_partition_triangles'):
                PlanarPiecewiseMapping(mapping.previous_partition, mapping.current_partition, 3)
        for options in ({'max_overlay_triangles': 3},):
            with self.assertRaisesRegex(ValueError, 'max_overlay_triangles'):
                verify_planar_piecewise_domains(mapping.previous_partition, mapping.current_partition, mapping, **options)
        with self.assertRaisesRegex(ValueError, 'max_candidate_tests'):
            verify_planar_piecewise_domains(mapping.previous_partition, mapping.current_partition,
                                           replace(mapping, max_candidate_tests=1))
        for xy, cells in (([[True, 0.]], [0]), ([[float('inf'), 0.]], [0]),
                          ([[10**400, 0.]], [0]), ([[0., 0.]], [True]),
                          ([[0., 0.]], [4]), ([[0., 0.]], [.5]),
                          ([[.75, .25]], [0]), ([[0., 0.]], [])):
            with self.subTest(xy=xy, cells=cells), self.assertRaises(ValueError):
                mapping.map_points(xy, cells)
        self.assertEqual(mapping.map_points(np.empty((0, 2)), []).shape, (0, 2))


if __name__ == '__main__':
    unittest.main()
