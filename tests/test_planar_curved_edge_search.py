# SPDX-License-Identifier: Apache-2.0
"""Closed quadratic edge bounds cannot omit contacts during bounded search."""
import unittest
import numpy as np
from superfish_ng.planar_curved_geometry import check_planar_edges, _overlapping_edge_boxes, GeometryBudget


class PlanarCurvedEdgeSearchTests(unittest.TestCase):
    def test_graded_parallel_edges_are_separated_with_a_linear_search_budget(self):
        count = 1024
        heights = (np.arange(count)/(count-1))**3
        points = np.array([[x, y] for y in heights for x in (0., 1., .5)])
        incidence = {(3*i, 3*i+1): [(i, 3*i, 3*i+1, 3*i+2, 0)] for i in range(count)}
        # All x boxes overlap, while independent horizontal lines are strictly
        # disjoint. The smallest gap is >1e-10, safely above the same padding.
        self.assertGreater(np.min(np.diff(heights)), 1e-10)
        report = check_planar_edges(points, incidence, 32*count)
        self.assertEqual(report['status'], 'PASS')
        self.assertEqual(report['overlapping_box_pairs'], 0)
        self.assertLess(report['boxes_checked'], 32*count)

    def test_closed_candidates_match_exhaustive_pairs_without_duplicates(self):
        rng = np.random.default_rng(4207)
        low = rng.uniform(-2, 2, size=(97, 2))
        high = low+rng.uniform(0, 2, size=(97, 2))
        low[:5] = [[0, 0], [1, 0], [1, 1], [0, 1], [np.nextafter(1., np.inf), 0]]
        high[:5] = [[1, 1], [1, 1], [2, 2], [1, 1], [2, 1]]
        bounds = np.stack((low, high), axis=1)
        keys = [(2*i, 2*i+1) for i in range(len(bounds))]
        expected = {(i, j) for i in range(len(bounds)) for j in range(i+1, len(bounds))
                    if np.all(high[i] >= low[j]) and np.all(high[j] >= low[i])}
        direct = list(_overlapping_edge_boxes(bounds, GeometryBudget(100000), keys))
        self.assertEqual(set(direct), expected)
        self.assertEqual(len(direct), len(set(direct)))
        self.assertIn((0, 1), expected)  # A zero-width box touches a closed side.
        self.assertIn((0, 2), expected)  # A single shared corner remains a candidate.
        self.assertNotIn((0, 4), expected)  # One-ULP strict gap is provably disjoint.
        self.assertEqual(direct, list(_overlapping_edge_boxes(bounds, GeometryBudget(100000), keys)))

    def test_box_search_and_narrow_phase_share_the_strict_budget(self):
        low = np.column_stack((np.zeros(32), np.arange(32)))
        bounds = np.stack((low, low+.25), axis=1)
        keys = [(2*i, 2*i+1) for i in range(len(bounds))]
        budget = GeometryBudget(3)
        with self.assertRaisesRegex(ValueError, 'exhausted after 3 checks'):
            list(_overlapping_edge_boxes(bounds, budget, keys))
        self.assertEqual(budget.checked, 3)
        # No tree is needed for two edges; their first closed-box test consumes
        # the same budget before the curve contact check can start.
        points = np.array([[0., 0.], [2., 0.], [1., 1.], [0., 1.], [2., 1.], [1., 1.]])
        incidence = {(0, 1): [(0, 0, 1, 2, 0)], (3, 4): [(1, 3, 4, 5, 0)]}
        with self.assertRaisesRegex(ValueError, 'exhausted after 1 checks'):
            check_planar_edges(points, incidence, 1)

    def test_quadratic_interior_contact_and_unresolved_gap_remain_rejected(self):
        for height in (1., 1.+1e-14):
            points = np.array([[0., 0.], [2., 0.], [1., 1.], [0., height], [2., height], [1., height]])
            incidence = {(0, 1): [(0, 0, 1, 2, 0)], (3, 4): [(1, 3, 4, 5, 0)]}
            with self.subTest(height=height), self.assertRaisesRegex(ValueError, 'contact|intersection|UNVERIFIED'):
                check_planar_edges(points, incidence, 100000)


if __name__ == '__main__':
    unittest.main()
