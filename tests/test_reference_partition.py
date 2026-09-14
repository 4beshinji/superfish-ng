# SPDX-License-Identifier: Apache-2.0
"""Independent coverage and integration for different initial triangulations."""
from fractions import Fraction as F
import unittest


OLD = [((0, 0), (1, 0), (1, 1)), ((0, 0), (1, 1), (0, 1))]
NEW = [((0, 0), (1, 0), (0, 1)), ((1, 0), (1, 1), (0, 1))]


class ReferencePartitionTests(unittest.TestCase):
    def build(self, a=OLD, b=NEW, **limits):
        from superfish_ng.reference_partition import intersect_reference_triangulations
        return intersect_reference_triangulations(a, b, **dict(max_pair_tests=100, max_triangles=100, **limits))

    def test_opposite_diagonals_cover_every_parent_and_integrate_quadratics(self):
        report = self.build()
        self.assertEqual(len(report['triangles']), 4)
        self.assertEqual(report['total_area'], [1, 1])
        for side in ('previous', 'current'):
            self.assertEqual(report[side+'_areas'], [[1, 2], [1, 2]])
            self.assertEqual(report[side+'_covered_areas'], report[side+'_areas'])
        # Integral of x^2 on the unit square is 1/3. Exact degree-two triangle rule.
        integral = F(0)
        for triangle in report['triangles']:
            vertices = [[F(*x) for x in p] for p in triangle['reference_vertices']]
            area = F(*triangle['determinant']) / 2
            integral += area * sum(((vertices[i][0]+vertices[j][0])/2)**2
                                   for i, j in ((0, 1), (1, 2), (2, 0))) / 3
            for side, parents in [('previous', OLD), ('current', NEW)]:
                parent = parents[triangle[side+'_cell']]
                for point, row in zip(vertices, triangle[side+'_barycentric']):
                    row = [F(*v) for v in row]
                    self.assertEqual(sum(row), 1)
                    self.assertGreaterEqual(min(row), 0)
                    self.assertEqual(point, [sum(row[i]*parent[i][k] for i in range(3)) for k in range(2)])
        self.assertEqual(integral, F(1, 3))

    def test_swapping_sides_and_cell_order_preserves_canonical_partition(self):
        a = self.build()
        b = self.build(NEW, OLD)
        c = self.build(list(reversed(OLD)), [x[1:]+x[:1] for x in NEW])
        for other in (b, c):
            self.assertEqual([t['reference_vertices'] for t in a['triangles']],
                             [t['reference_vertices'] for t in other['triangles']])
        self.assertEqual([t['previous_cell'] for t in a['triangles']], [t['current_cell'] for t in b['triangles']])

    def test_independent_boundary_subdivision_and_interior_vertex(self):
        from copy import deepcopy
        boundary = [(0, 0), (F(1, 2), 0), (1, 0), (1, 1), (0, 1)]
        center = (F(1, 2), F(1, 2))
        triangles = [(a, boundary[(i+1) % len(boundary)], center) for i, a in enumerate(boundary)]
        before = deepcopy(triangles)
        report = self.build(OLD, triangles)
        self.assertEqual(report['total_area'], [1, 1])
        self.assertEqual(report['current_areas'], [[1, 8], [1, 8], [1, 4], [1, 4], [1, 4]])
        self.assertEqual(report['current_covered_areas'], report['current_areas'])
        self.assertEqual(triangles, before)

    def test_overlaps_missing_domain_and_inverted_triangles_fail(self):
        for a, b in [(OLD+OLD[:1], NEW), (OLD, NEW[:1]),
                     ([OLD[0][::-1], OLD[1]], NEW)]:
            with self.subTest(a=a, b=b), self.assertRaises(ValueError):
                self.build(a, b)

    def test_strict_coordinates_and_budgets(self):
        for coordinate in (True, float('nan'), float('inf'), '0'):
            with self.subTest(coordinate=coordinate), self.assertRaises(ValueError):
                self.build([((coordinate, 0), (1, 0), (1, 1))], NEW)
        from superfish_ng.reference_partition import intersect_reference_triangulations
        for pairs, triangles in [(5, 100), (100, 3), (True, 100)]:
            with self.subTest(pairs=pairs, triangles=triangles), self.assertRaises(ValueError):
                intersect_reference_triangulations(OLD, NEW, max_pair_tests=pairs, max_triangles=triangles)
