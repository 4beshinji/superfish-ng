# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from fractions import Fraction
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng.fem import triangle_quadrature
from superfish_ng.planar import solve_planar
from superfish_ng.planar_mesh import PlanarMesh
from superfish_ng.planar_polygon import PlanarPolygonCase
from superfish_ng.planar_refinement import refine_planar_mesh
from superfish_ng.planar_tracking_affine_remesh import (
    PolygonAffineRemeshMapping, polygon_affine_remesh_overlay)
from superfish_ng.planar_tracking_exact_affine import (
    exact_affine_polygon_overlay, _RationalTriangulation)
from superfish_ng.planar_tracking_fields import _electric_grams
from superfish_ng.planar_tracking_remesh import _candidate_pairs


def rectangle(nx, ny, width=1., height=1., flipped=False):
    points = np.array([(width*i/nx, height*j/ny)
                       for j in range(ny+1) for i in range(nx+1)])
    cells = []
    for j in range(ny):
        for i in range(nx):
            a = j*(nx+1)+i
            b, d = a+1, a+nx+1
            c = d+1
            cells.extend([(a, b, d), (b, c, d)] if flipped else [(a, b, c), (a, c, d)])
    polygon = [[0., 0.], [width, 0.], [width, height], [0., height]]
    return PlanarMesh.create(polygon, points, cells)


def overlay_for(a, b, mapping, **kwargs):
    return exact_affine_polygon_overlay(a, b, linear_xy=mapping.linear_xy,
        translation_xy_m=mapping.translation_xy_m, inverse=mapping.inverse, **kwargs)


class ExactAffineGeometryTests(unittest.TestCase):
    def test_independent_boundary_density_without_rounding_the_image(self):
        a = rectangle(3, 3)
        mapping = PolygonAffineRemeshMapping([[1., .25], [0., 1.]])
        b = mapping.transform_mesh(rectangle(4, 4, flipped=True))
        with self.assertRaisesRegex(ValueError, 'boundary cycle'):
            polygon_affine_remesh_overlay(a, b, mapping)
        exact = Fraction(float(a.points_xy_m[5, 0]))+Fraction(1, 4)*Fraction(float(a.points_xy_m[5, 1]))
        self.assertNotEqual(exact, Fraction(float(exact)))
        overlay = overlay_for(a, b, mapping)
        self.assertNotEqual(len(a.boundary_edges), len(b.boundary_edges))
        self.assertAlmostEqual(sum(overlay.reference_determinants)/2, 1., places=14)

    def test_cell_coverage_original_coordinates_and_polynomial_moments(self):
        for matrix in ([[1., .25], [0., 2.]], [[-1., .25], [0., 2.]]):
            mapping = PolygonAffineRemeshMapping(matrix, (.125, -.25))
            for scale in (2.**-12, 1., 2.**12):
                a = rectangle(3, 3, scale, scale)
                b = mapping.transform_mesh(rectangle(4, 4, scale, scale, True))
                for previous, current, direction in ((a, b, mapping), (b, a, replace(mapping, inverse=True))):
                    overlay = overlay_for(previous, current, direction)
                    effective, translation = direction._effective(False)
                    determinant = abs(np.linalg.det(effective))
                    for cells, bary, mesh, factor, is_previous in (
                        (overlay.previous_cells, overlay.previous_vertex_barycentric, previous, determinant, True),
                        (overlay.current_cells, overlay.current_vertex_barycentric, current, 1., False)):
                        vertices = mesh.points_xy_m[mesh.triangles]
                        det = np.linalg.det(np.stack((vertices[:, 1]-vertices[:, 0], vertices[:, 2]-vertices[:, 0]), axis=-1))
                        np.testing.assert_allclose(np.bincount(cells, weights=overlay.reference_determinants),
                                                   factor*det, rtol=3e-12, atol=0.)
                        reconstructed = np.einsum('nij,njk->nik', bary, vertices[cells])
                        if is_previous:
                            reconstructed = reconstructed@effective.T+translation
                        np.testing.assert_allclose(reconstructed, overlay.reference_vertices, rtol=3e-12, atol=1e-12*scale)
                        self.assertFalse(bary.flags.writeable)
                    # Integrate powers on the original unit square by pulling
                    # current coordinates back through the known shear.
                    for px, py in ((0, 0), (1, 0), (0, 1), (2, 1), (2, 2)):
                        value = 0.
                        for bary, weight in triangle_quadrature(5):
                            xy = np.einsum('j,njk->nk', bary, overlay.reference_vertices)
                            if current is b:
                                xy = (xy-np.array(mapping.translation_xy_m))@np.linalg.inv(mapping.matrix).T
                            unit = xy/scale
                            value += np.sum(weight*overlay.reference_determinants*unit[:, 0]**px*unit[:, 1]**py)
                        expected = current.area_m2/((px+1)*(py+1))
                        self.assertAlmostEqual(value/expected, 1., places=11)

    def test_inverse_with_non_binary_rational_coordinates(self):
        mapping = PolygonAffineRemeshMapping([[3., 0.], [0., 1.]], inverse=True)
        a, b = rectangle(5, 3, 3.), rectangle(4, 4, flipped=True)
        overlay = overlay_for(a, b, mapping)
        self.assertAlmostEqual(sum(overlay.reference_determinants)/2, 1., places=14)
        # Forward and inverse declarations denote the same geometric map.
        reverse = overlay_for(b, a, replace(mapping, inverse=False))
        self.assertAlmostEqual(sum(reverse.reference_determinants)/2, 3., places=13)

    def test_concavity_collinear_corners_and_independent_numbering(self):
        points = np.array([[0., 0.], [2., 0.], [2., 1.], [1., 1.], [1., 2.], [0., 2.]])
        a = PlanarMesh.create(points, points, [[0, 1, 3], [1, 2, 3], [0, 3, 5], [3, 4, 5]])
        mapping = PolygonAffineRemeshMapping([[-1., .5], [0., 1.]], (.25, -.5))
        b = mapping.transform_mesh(refine_planar_mesh(a))
        permutation = np.arange(len(b.points_xy_m))[::-1]
        b = PlanarMesh.create(np.roll(b.polygon_xy_m, 2, axis=0), b.points_xy_m[permutation],
                             np.argsort(permutation)[b.triangles[::-1]])
        overlay = overlay_for(a, b, mapping)
        self.assertAlmostEqual(sum(overlay.reference_determinants)/2, 3., places=14)
        a = rectangle(3, 3)
        polygon = np.insert(a.polygon_xy_m, 1, [1/3, 0.], axis=0)
        a = PlanarMesh.create(polygon, a.points_xy_m, a.triangles)
        b = mapping.transform_mesh(rectangle(4, 4, flipped=True))
        self.assertAlmostEqual(sum(overlay_for(a, b, mapping).reference_determinants)/2, 1., places=14)

    def test_rational_bvh_retains_sub_ulp_intersections(self):
        delta = Fraction(1, 2**100)
        points = np.array([(Fraction(1)-delta, 0), (Fraction(2), 0), (Fraction(1)-delta, 1)], dtype=object)
        a = _RationalTriangulation(points, np.array([[0, 1, 2]]))
        b = _RationalTriangulation(np.array([(0, 0), (1, 0), (1, 1)], dtype=object), np.array([[0, 1, 2]]))
        self.assertEqual(set(_candidate_pairs(a, b, 100)), {(0, 0)})
        rounded = _RationalTriangulation(points.astype(float), a.triangles)
        self.assertEqual(set(_candidate_pairs(rounded, b, 100)), set())
        # Compare a full multi-leaf rational BVH with independent all-pairs bounds.
        mesh = rectangle(4, 4)
        rational = np.array([[Fraction(float(x)), Fraction(float(y))] for x, y in mesh.points_xy_m], dtype=object)
        left = _RationalTriangulation(rational, mesh.triangles)
        right = _RationalTriangulation(rational+delta, mesh.triangles[::-1])
        va, vb = rational[left.triangles], right.points_xy_m[right.triangles]
        expected = {(i, j) for i, x in enumerate(va) for j, y in enumerate(vb)
                    if all(min(x[:, k]) < max(y[:, k]) and min(y[:, k]) < max(x[:, k]) for k in (0, 1))}
        self.assertEqual(set(_candidate_pairs(left, right, 10000)), expected)

    def test_strict_geometry_and_resource_refusals(self):
        a = rectangle(3, 3)
        identity = [[1., 0.], [0., 1.]]
        b = rectangle(4, 4, flipped=True)
        for changes in ({'linear_xy': [[1., 1.], [1., 1.]]}, {'linear_xy': [[True, 0.], [0., 1.]]},
                        {'linear_xy': [[float('nan'), 0.], [0., 1.]]}, {'inverse': 1},
                        {'translation_xy_m': [float('inf'), 0.]}, {'max_candidate_tests': True},
                        {'max_overlay_triangles': 0}):
            with self.assertRaises(ValueError):
                exact_affine_polygon_overlay(a, b, **dict({'linear_xy': identity}, **changes))
        with self.assertRaisesRegex(ValueError, 'input meshes'):
            exact_affine_polygon_overlay(a, b, linear_xy=identity, max_overlay_triangles=2)
        with self.assertRaisesRegex(ValueError, 'max_candidate_tests'):
            exact_affine_polygon_overlay(a, b, linear_xy=identity, max_candidate_tests=1)
        with self.assertRaisesRegex(ValueError, 'intersections exceed'):
            exact_affine_polygon_overlay(a, b, linear_xy=identity, max_overlay_triangles=32)
        with self.assertRaisesRegex(ValueError, 'PlanarMesh'):
            exact_affine_polygon_overlay(a, None, linear_xy=identity)
        with self.assertRaisesRegex(ValueError, 'exact rational affine images'):
            exact_affine_polygon_overlay(a, rectangle(4, 4, np.nextafter(1., 2.)), linear_xy=identity)
        # PlanarMesh permits construction roundoff. This stricter API must
        # reject a one-ULP bent boundary even when both meshes share it.
        points = b.points_xy_m.copy()
        points[9, 0] = np.nextafter(1., 2.)
        bent = PlanarMesh.create(b.polygon_xy_m, points, b.triangles)
        with self.assertRaisesRegex(ValueError, 'boundary edges exactly'):
            exact_affine_polygon_overlay(bent, bent, linear_xy=identity)
        rounded = PolygonAffineRemeshMapping([[.8, .3], [-.2, 1.1]])
        with self.assertRaisesRegex(ValueError, 'rounded'):
            overlay_for(rectangle(1, 1), rounded.transform_mesh(rectangle(1, 1)), rounded)

    def test_missing_or_duplicate_intersections_cannot_pass_area_verification(self):
        a, b = rectangle(2, 2), rectangle(3, 3)
        for pairs in ([], [(0, 0), (0, 0)]):
            with patch('superfish_ng.planar_tracking_exact_affine._candidate_pairs', return_value=iter(pairs)):
                with self.assertRaisesRegex(ValueError, 'every original element'):
                    exact_affine_polygon_overlay(a, b, linear_xy=[[1., 0.], [0., 1.]])


class ExactAffineFieldTests(unittest.TestCase):
    def test_original_p1_p2_te_tm_polynomials_and_adjugate_transport(self):
        mapping = PolygonAffineRemeshMapping([[-1., .25], [0., 2.]], (.125, -.25))
        for polarization in ('te', 'tm'):
            for orders in ((1, 1), (1, 2), (2, 1), (2, 2)):
                with self.subTest(polarization=polarization, orders=orders):
                    a = solve_planar(PlanarPolygonCase(rectangle(3, 3), polarization, orders[0], 2))
                    b = solve_planar(PlanarPolygonCase(mapping.transform_mesh(rectangle(4, 4, flipped=True)), polarization, orders[1], 2))
                    nonlinear = min(orders) == 2
                    def values(xy):
                        x, y = xy.T
                        return np.column_stack((1+x+.25*y+(x*y if nonlinear else 0),
                                                .25-x+y+(y*y if nonlinear else 0)))
                    a = replace(a, coefficients=values(a.space.dof_points_xy_m))
                    pullback = (b.space.dof_points_xy_m-np.array(mapping.translation_xy_m))@np.linalg.inv(mapping.matrix).T
                    # Same angular frequencies isolate the coefficient/gradient
                    # law. These test polynomials are not claimed as eigenmodes.
                    b = replace(b, coefficients=values(pullback), frequencies_hz=a.frequencies_hz)
                    overlay = overlay_for(a.case.mesh, b.case.mesh, mapping)
                    grams = _electric_grams(a, b, overlay, 3,
                        current_to_previous_rotation=mapping.current_to_previous_linear)
                    higher = _electric_grams(a, b, overlay, 5,
                        current_to_previous_rotation=mapping.current_to_previous_linear)
                    norm = np.sqrt(np.diag(grams[0]))
                    scale = norm[:, None]*norm[None, :]
                    for gram in (*grams[1:], *higher):
                        np.testing.assert_allclose(gram/scale, grams[0]/scale,
                                                   rtol=3e-12, atol=3e-12)


if __name__ == '__main__':
    unittest.main()
