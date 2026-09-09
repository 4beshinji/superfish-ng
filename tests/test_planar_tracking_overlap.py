# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from superfish_ng.fem import triangle_quadrature
from superfish_ng.planar import PlanarCase, planar_matrices, solve_planar
from superfish_ng.planar_tracking_overlap import rectangle_tracking_overlay
from superfish_ng.constants import EPS0


class PlanarTrackingOverlayTests(unittest.TestCase):
    def test_reference_partition_parent_maps_and_exact_moments(self):
        for previous, current in (((2, 2), (2, 2)), ((3, 4), (5, 2)), ((4, 3), (8, 6)), ((7, 3), (2, 5))):
            overlay = rectangle_tracking_overlay(previous, current)
            for grid, cells, bary in (
                    (previous, overlay.previous_cells, overlay.previous_vertex_barycentric),
                    (current, overlay.current_cells, overlay.current_vertex_barycentric)):
                space, _, _, _ = planar_matrices(PlanarCase(1., 1., nx=grid[0], ny=grid[1]))
                reconstructed = np.einsum('nij,njk->nik', bary, space.points_xy_m[space.triangles[cells]])
                np.testing.assert_allclose(reconstructed, overlay.reference_vertices, atol=2e-15, rtol=0)
            for px in range(5):
                for py in range(5-px):
                    integral = 0.
                    for bary, weight in triangle_quadrature(4):
                        points = np.einsum('j,tjk->tk', bary, overlay.reference_vertices)
                        integral += weight*(overlay.reference_determinants @ (points[:, 0]**px * points[:, 1]**py))
                    self.assertAlmostEqual(integral, 1/((px+1)*(py+1)), places=13)
            self.assertFalse(overlay.previous_cells.flags.writeable)
            self.assertFalse(overlay.reference_vertices.flags.writeable)

    def test_original_electric_energy_on_independent_grids(self):
        grids = ((4, 3), (5, 7))
        overlay = rectangle_tracking_overlay(*grids)
        for polarization in ('te', 'tm'):
            for order in (1, 2):
                for grid, cells, vertex_bary in (
                        (grids[0], overlay.previous_cells, overlay.previous_vertex_barycentric),
                        (grids[1], overlay.current_cells, overlay.current_vertex_barycentric)):
                    case = PlanarCase(.31, .2, nx=grid[0], ny=grid[1], polarization=polarization,
                                      element_order=order, modes=2)
                    solution = solve_planar(case)
                    gram = np.zeros((2, 2))
                    for bary, weight in triangle_quadrature(3):
                        mapped = np.einsum('j,njk->nk', bary, vertex_bary)
                        fields = [solution.fields_in_cells(cells, mapped, mode) for mode in range(2)]
                        for key in fields[0]:
                            if key.startswith('E'):
                                values = np.column_stack([f[key] for f in fields])
                                gram += values.T @ ((weight*overlay.reference_determinants)[:, None]*values)
                    # Each eigenmode has electric energy U'/2; this independent
                    # invariant failed by 28% with whole-rectangle Gauss points.
                    np.testing.assert_allclose(gram*EPS0*case.width_m*case.height_m/2,
                                               np.eye(2), rtol=1e-11, atol=1e-11)

    def test_reversed_overlay_has_the_same_measure(self):
        a = rectangle_tracking_overlay((3, 4), (5, 2))
        b = rectangle_tracking_overlay((5, 2), (3, 4))
        # The fan diagonal need not coincide, but each parent intersection area must.
        def areas(overlay, reverse=False):
            result = {}
            for old, new, det in zip(overlay.previous_cells, overlay.current_cells, overlay.reference_determinants):
                key = (new, old) if reverse else (old, new)
                result[key] = result.get(key, 0.) + det/2
            return result
        x, y = areas(a), areas(b, True)
        self.assertEqual(x.keys(), y.keys())
        np.testing.assert_allclose(list(x.values()), [y[k] for k in x], rtol=1e-14, atol=1e-15)

    def test_strict_budget_and_grid(self):
        for grid in ((True, 3), (2., 3), (0, 3), (2,), '3,4'):
            with self.assertRaises(ValueError):
                rectangle_tracking_overlay(grid, (3, 4))
        with self.assertRaises(ValueError):
            rectangle_tracking_overlay((3, 4), (5, 2), max_overlay_triangles=True)
        with self.assertRaisesRegex(ValueError, 'exceeds'):
            rectangle_tracking_overlay((1000, 2), (2, 1000), max_overlay_triangles=100)
        with self.assertRaisesRegex(ValueError, 'intersections exceed'):
            rectangle_tracking_overlay((3, 4), (5, 2), max_overlay_triangles=56)
