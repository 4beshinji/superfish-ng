# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from fractions import Fraction
import unittest
import numpy as np
from superfish_ng.planar_affine_shape import PlanarAffineShapeLaw
from superfish_ng.planar_project import PlanarProject
from superfish_ng.planar_polygon import PlanarPolygonCase
from superfish_ng.planar import PlanarCase, solve_planar
from superfish_ng.planar_study import PlanarStudy
from test_planar_tracking_exact_affine import rectangle


class PlanarAffineShapeTests(unittest.TestCase):
    def test_closed_interval_rejects_interior_even_root_and_endpoints(self):
        # det=(p-3/8)^2: positive at both endpoints, but singular inside.
        for coefficients in ([9/64, -3/4, 1], [0, 1], [-1, 1], [0]):
            with self.subTest(coefficients=coefficients), self.assertRaisesRegex(ValueError, 'determinant'):
                PlanarAffineShapeLaw([[coefficients, [0]], [[0], [1]]], [[0], [0]], [0, 1])
        law = PlanarAffineShapeLaw([[[9/64+2**-40, -3/4, 1], [0]], [[0], [1]]], [[0], [0]], [0, 1])
        self.assertEqual(law.exact_transform(.375)[0][0][0], Fraction(1, 2**40))

    def test_original_project_area_shear_reflection_and_serialization(self):
        project = PlanarProject(PlanarPolygonCase(rectangle(4, 4, .25, .5), modes=3,
                                                normalization_j_per_m=3.))
        original = deepcopy(project.to_dict())
        law = PlanarAffineShapeLaw([[[1, 1], [0, .25]], [[0], [-1]]],
                                  [[.125, .25], [-.25]], [-.5, 1])
        self.assertEqual(PlanarAffineShapeLaw.from_dict(law.to_dict()), law)
        for value in (1., -.5, 0., 1.):
            mapped = law.project(project, value)
            matrix, translation = law.exact_transform(value)
            expected = [[float(sum(matrix[i][j]*Fraction(float(p[j])) for j in range(2))+translation[i])
                         for i in range(2)] for p in project.case.mesh.points_xy_m]
            np.testing.assert_array_equal(mapped.case.mesh.points_xy_m, expected)
            self.assertAlmostEqual(mapped.case.mesh.area_m2, (1+value)*project.case.mesh.area_m2)
            self.assertEqual(mapped.case.normalization_j_per_m, 3.)
            self.assertEqual(mapped.display_length_unit, project.display_length_unit)
        self.assertEqual(project.to_dict(), original)
        bad = law.to_dict(); bad['parameter_unit'] = 'm'
        with self.assertRaises(ValueError): PlanarAffineShapeLaw.from_dict(bad)
        with self.assertRaises(ValueError): law.project(project, 2.)
        with self.assertRaises(ValueError): law.exact_transform(True)
        with self.assertRaises(ValueError): PlanarAffineShapeLaw([[[True], [0]], [[0], [1]]], [[0], [0]], [0,1])
        with self.assertRaises(ValueError): law.project(PlanarProject(PlanarCase(.25, .5)), .5)
        # An exact nonsingular map can still collapse after coordinate rounding.
        # That is unresolved geometry, not permission to merge vertices.
        collapsed = PlanarAffineShapeLaw([[[1], [0]], [[0], [1]]], [[1e30], [1e30]], [0, 1])
        with self.assertRaises(ValueError): collapsed.project(project, .5)

    def test_real_fem_rotation_and_uniform_scale_fixed_energy_per_length(self):
        project = PlanarProject(PlanarPolygonCase(rectangle(4, 4, .25, .5), modes=3,
                                                normalization_j_per_m=2.))
        # 90 degree rotation times p, plus translation; no fitted field values.
        law = PlanarAffineShapeLaw([[[0], [0, -1]], [[0, 1], [0]]], [[.125], [-.25]], [1, 2])
        base = solve_planar(project.case)
        mapped = solve_planar(law.project(project, 2.).case)
        np.testing.assert_allclose(mapped.frequencies_hz, base.frequencies_hz/2, rtol=2e-12)
        self.assertEqual(mapped.case.normalization_j_per_m, base.case.normalization_j_per_m)
        # Compare a second construction against the existing uniform Study.
        scaling = PlanarAffineShapeLaw([[[0, 1], [0]], [[0], [0, 1]]], [[0], [0]], [1, 2])
        expected = PlanarStudy(project, 'uniform_scale', [1., 2.]).projects()[1]
        self.assertEqual(scaling.project(project, 2.).to_dict(), expected.to_dict())


if __name__ == '__main__':
    unittest.main()
