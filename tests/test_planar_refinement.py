# SPDX-License-Identifier: Apache-2.0
"""Physical domain and nested finite-element invariants, independent of solves."""
import unittest
import numpy as np
from scipy.sparse.linalg import norm
from superfish_ng.planar_mesh import PlanarMesh
from superfish_ng.planar import planar_mesh_matrices
from superfish_ng.planar_refinement import (
    refine_planar_mesh, planar_refinement_relation, planar_prolongation,
)


class PlanarRefinementTests(unittest.TestCase):
    def meshes(self):
        for polygon, cells in (
            ([[0., 0.], [2., 0.], [2., 1.], [0., 1.]], [[0, 1, 2], [0, 2, 3]]),
            ([[0., 0.], [1., 0.], [1., 1.]], [[0, 1, 2]]),
            ([[0., 0.], [2., 0.], [2., 1.], [1., 1.], [1., 2.], [0., 2.]],
             [[0, 1, 3], [1, 2, 3], [0, 3, 5], [3, 4, 5]]),
        ):
            for angle in (0., .37):
                rotation = np.array([[np.cos(angle), -np.sin(angle)],
                                     [np.sin(angle), np.cos(angle)]])
                for scale in (1., 2.):
                    points = np.asarray(polygon) @ rotation.T * scale + [-.4, .7]
                    yield PlanarMesh.create(points, points, cells)

    def test_area_parent_map_and_original_nodes(self):
        for coarse in self.meshes():
            fine = refine_planar_mesh(coarse)
            parents, bary = planar_refinement_relation(coarse, fine)
            np.testing.assert_array_equal(fine.points_xy_m[:len(coarse.points_xy_m)], coarse.points_xy_m)
            np.testing.assert_array_equal(fine.polygon_xy_m, coarse.polygon_xy_m)
            np.testing.assert_allclose(
                fine.points_xy_m[fine.triangles],
                np.einsum('nij,njk->nik', bary, coarse.points_xy_m[coarse.triangles[parents]]),
                rtol=1e-14, atol=1e-15)
            self.assertAlmostEqual(fine.area_m2 / coarse.area_m2, 1., places=14)
            self.assertFalse(parents.flags.writeable)
            self.assertFalse(bary.flags.writeable)

    def test_nested_mass_stiffness_polynomials_and_pec(self):
        for coarse in self.meshes():
            # Two refinements provide interior PEC nodes even for one triangle.
            coarse = refine_planar_mesh(refine_planar_mesh(coarse))
            fine = refine_planar_mesh(coarse)
            for order in (1, 2):
                for polarization in ('te', 'tm'):
                    with self.subTest(order=order, polarization=polarization):
                        a, ka, ma, free = planar_mesh_matrices(coarse, order, polarization)
                        b, kb, mb, _ = planar_mesh_matrices(fine, order, polarization)
                        transfer = planar_prolongation(coarse, fine, order, polarization)
                        self.assertLess(norm(transfer.T @ mb @ transfer - ma) / norm(ma), 1e-12)
                        self.assertLess(norm(transfer.T @ kb @ transfer - ka) / norm(ka), 1e-12)
                        np.testing.assert_array_equal(transfer @ np.ones(len(a.dof_points_xy_m)),
                                                      np.ones(len(b.dof_points_xy_m)))
                        np.testing.assert_allclose(transfer @ a.dof_points_xy_m, b.dof_points_xy_m,
                                                   rtol=1e-14, atol=1e-15)
                        if order == 2:
                            x, y = a.dof_points_xy_m.T
                            xx, yy = b.dof_points_xy_m.T
                            np.testing.assert_allclose(transfer @ (x*x + x*y + 3*y*y),
                                                       xx*xx + xx*yy + 3*yy*yy, rtol=1e-14, atol=1e-15)
                        if polarization == 'tm':
                            self.assertGreater(len(free), 0)
                            self.assertEqual(transfer[np.unique(b.boundary_dofs)][:, free].nnz, 0)

    def test_changed_domain_and_undeclared_refinement_rejected(self):
        coarse = next(self.meshes())
        fine = refine_planar_mesh(coarse)
        wrong = PlanarMesh.create(fine.polygon_xy_m * 2, fine.points_xy_m * 2, fine.triangles)
        for mesh in (coarse, wrong, refine_planar_mesh(fine)):
            with self.assertRaisesRegex(ValueError, 'same physical domain'):
                planar_prolongation(coarse, mesh)
        # An equivalent reordered mesh is not the declared parent-major refinement.
        reordered = PlanarMesh.create(fine.polygon_xy_m, fine.points_xy_m, fine.triangles[::-1])
        with self.assertRaisesRegex(ValueError, 'same physical domain'):
            planar_refinement_relation(coarse, reordered)

    def test_strict_parameters_and_budget(self):
        coarse = next(self.meshes())
        fine = refine_planar_mesh(coarse, max_triangles=8)
        for value in (True, 0, -1, 8., '8', 7):
            with self.subTest(value=value), self.assertRaises(ValueError):
                refine_planar_mesh(coarse, max_triangles=value)
        for order in (True, 0, 3, 2.):
            with self.subTest(order=order), self.assertRaises(ValueError):
                planar_prolongation(coarse, fine, order)
        with self.assertRaises(ValueError):
            planar_prolongation(coarse, fine, polarization='axisymmetric')
        with self.assertRaises(ValueError):
            refine_planar_mesh(coarse.to_dict())


if __name__ == '__main__':
    unittest.main()
