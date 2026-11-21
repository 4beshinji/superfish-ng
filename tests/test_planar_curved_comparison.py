# SPDX-License-Identifier: Apache-2.0
"""Independent analytic patch moments on two non-nested curved partitions."""
from fractions import Fraction as F
from copy import deepcopy
import unittest
import numpy as np
from superfish_ng.planar_curved import PlanarCurvedDomain
from test_planar_curved import quadratic_nodes


def analytic_patch(inner=None, *, stretch=(1., 1.), displacement=(-.25, 0.)):
    """F=(tx+sx*l*x, ty+sy*l*(y+d*x*(1-x-y))), l=1/8,d=1/4."""
    vertices = [[0., 0.], [1., 0.], [0., 1.]]+([] if inner is None else [inner])
    cells = [[0, 1, 2]] if inner is None else [[0, 1, 3], [1, 2, 3], [2, 0, 3]]
    refs, cell_nodes, boundary = quadratic_nodes(vertices, cells, [0, 1, 2])
    x, y = refs.T
    points = np.column_stack((x, y+x*(1-x-y)/4))/8
    points = points*np.asarray(stretch)+displacement
    domain = PlanarCurvedDomain(points, cell_nodes, boundary)
    charts = [dict(base_cell=0, reference_vertices=[[[F(float(v)).numerator, F(float(v)).denominator]
               for v in point] for point in refs[cell[:3]]]) for cell in cell_nodes]
    return domain, charts


class PlanarCurvedComparisonTests(unittest.TestCase):
    def test_non_nested_patch_area_moments_and_inverse(self):
        from superfish_ng.planar_curved_comparison import (PlanarCurvedComparisonDomain,
            build_planar_curved_comparison)
        base, _ = analytic_patch()
        left, ca = analytic_patch((.25, .25))
        right, cb = analytic_patch((.5, .25))
        domain = PlanarCurvedComparisonDomain(base, base, 'same_domain')
        forward = build_planar_curved_comparison(left, right, domain, previous_cells=ca, current_cells=cb)
        backward = build_planar_curved_comparison(right, left, domain.inverse(), previous_cells=cb, current_cells=ca)
        self.assertGreater(len(forward.triangles), 3)
        # Independent tensor Gauss over x=u,y=(1-u)*v.
        t, w = np.polynomial.legendre.leggauss(5)
        t, w = (t+1)/2, w/2
        u, v = np.meshgrid(t, t, indexing='ij')
        q = np.column_stack((u.ravel(), ((1-u)*v).ravel()))
        weights = (np.outer(w, w)*(1-u)).ravel()
        length, d = 1/8, 1/4
        area = length**2*(.5-d/6)
        xmoment = -.25*area+length**3*(1/6-d/12)
        ymoment = length**3*(1/6-d*d/60)
        for side in (0, 1):
            rows = forward.evaluate(side, q)
            self.assertAlmostEqual(sum(weights@row['determinant_m2'] for row in rows)/area, 1., places=13)
            for axis, expected in enumerate((xmoment, ymoment)):
                actual = sum(weights@(row['points_xy_m'][:, axis]*row['determinant_m2']) for row in rows)
                self.assertAlmostEqual(actual/expected, 1., places=13)
            for first, second in zip(rows, backward.evaluate(1-side, q)):
                np.testing.assert_array_equal(first['points_xy_m'], second['points_xy_m'])
                np.testing.assert_array_equal(first['determinant_m2'], second['determinant_m2'])
        self.assertEqual(forward.report['status'], 'GEOMETRY_VERIFIED')
        self.assertEqual(forward.report['base_reference_areas'], [[1, 2]])

    def test_declared_nonuniform_map_preserves_each_actual_native_area(self):
        from superfish_ng.planar_curved_comparison import PlanarCurvedComparisonDomain, build_planar_curved_comparison
        base_a, _ = analytic_patch()
        base_b, _ = analytic_patch(stretch=(2., 3.), displacement=(.1, -.2))
        a, ca = analytic_patch((.25, .25))
        b, cb = analytic_patch((.5, .25), stretch=(2., 3.), displacement=(.1, -.2))
        # The decimal translation introduces roundoff in restrictions, so the
        # permission and measured complete polynomial bound must be explicit.
        domain = PlanarCurvedComparisonDomain(base_a, base_b, 'declared_quadratic', 'binary64_roundoff')
        overlay = build_planar_curved_comparison(a, b, domain, previous_cells=ca, current_cells=cb)
        q = [[.2, .3], [0., 0.], [1., 0.], [0., 1.]]
        for old, new in zip(overlay.evaluate(0, q), overlay.evaluate(1, q)):
            np.testing.assert_allclose((old['points_xy_m']-[-.25, 0.])*[2., 3.]+[.1, -.2],
                                       new['points_xy_m'], rtol=0, atol=1e-16)
            np.testing.assert_allclose(new['determinant_m2'], old['determinant_m2']*6, rtol=2e-14)
        self.assertEqual(domain.to_dict(), PlanarCurvedComparisonDomain.from_dict(domain.to_dict()).to_dict())
        self.assertTrue(all(v <= 512*np.finfo(float).eps for v in overlay.report['maximum_original_map_relative_bounds']))

    def test_equal_vertices_do_not_establish_same_quadratic_domain(self):
        from superfish_ng.planar_curved_comparison import PlanarCurvedComparisonDomain, build_planar_curved_comparison
        base, _ = analytic_patch()
        points = base.points_xy_m.copy()
        points[base.boundary_nodes[0, 2], 1] += 1/4096
        changed = PlanarCurvedDomain(points, base.cell_nodes, base.boundary_nodes)
        np.testing.assert_array_equal(base.points_xy_m[base.cell_nodes[:, :3]], changed.points_xy_m[changed.cell_nodes[:, :3]])
        with self.assertRaisesRegex(ValueError, 'same_domain'):
            PlanarCurvedComparisonDomain(base, changed, 'same_domain')
        for policy in ('exact', 'binary64_roundoff'):
            domain = PlanarCurvedComparisonDomain(base, base, 'same_domain', policy)
            with self.assertRaises(ValueError):
                build_planar_curved_comparison(base, changed, domain)

    def test_complete_boundary_restriction_and_explicit_roundoff(self):
        from superfish_ng.planar_curved_comparison import PlanarCurvedComparisonDomain, build_planar_curved_comparison
        from superfish_ng.planar_curved_refinement import refine_planar_curved_domain
        from test_planar_curved import curved_ellipse
        base = curved_ellipse(8)
        restriction = refine_planar_curved_domain(base)
        charts = [dict(base_cell=int(owner), reference_vertices=[[[F(float(v)).numerator, F(float(v)).denominator]
                  for v in point] for point in vertices])
                  for owner, vertices in zip(restriction.parent_cells, restriction.parent_reference_vertices)]
        with self.assertRaisesRegex(ValueError, 'exact quadratic restriction'):
            build_planar_curved_comparison(base, restriction.domain,
                PlanarCurvedComparisonDomain(base, base), current_cells=charts)
        domain = PlanarCurvedComparisonDomain(base, base, restriction_policy='binary64_roundoff')
        overlay = build_planar_curved_comparison(base, restriction.domain, domain, current_cells=charts)
        self.assertFalse(overlay.report['exact_native_restrictions'])
        self.assertLessEqual(max(overlay.report['maximum_original_map_relative_bounds']), 512*np.finfo(float).eps)
        self.assertEqual(overlay.report['base_reference_areas'], [[1, 2]]*8)
        # Every boundary node comes from the original map, including midpoints.
        self.assertEqual(overlay.report['triangle_count'], len(restriction.domain.cell_nodes))

    def test_cell_permutation_and_local_rotation_retain_original_owners(self):
        from superfish_ng.planar_curved_comparison import PlanarCurvedComparisonDomain, build_planar_curved_comparison
        base, _ = analytic_patch()
        a, ca = analytic_patch((.25, .25))
        b, cb = analytic_patch((.5, .25))
        cells = b.cell_nodes[::-1][:, [1, 2, 0, 4, 5, 3]]
        reordered = PlanarCurvedDomain(b.points_xy_m, cells, b.boundary_nodes)
        charts = [dict(base_cell=row['base_cell'], reference_vertices=row['reference_vertices'][1:]+row['reference_vertices'][:1]) for row in cb[::-1]]
        domain = PlanarCurvedComparisonDomain(base, base)
        original = build_planar_curved_comparison(a, b, domain, previous_cells=ca, current_cells=cb)
        changed = build_planar_curved_comparison(a, reordered, domain, previous_cells=ca, current_cells=charts)
        for side in (0, 1):
            for old, new in zip(original.evaluate(side, [[.2, .3]]), changed.evaluate(side, [[.2, .3]])):
                np.testing.assert_allclose(old['points_xy_m'], new['points_xy_m'], rtol=0, atol=1e-16)
                np.testing.assert_allclose(old['determinant_m2'], new['determinant_m2'], rtol=1e-14)
                np.testing.assert_array_equal(old['reference_points_xy_m'], new['reference_points_xy_m'])
                if side == 1:
                    self.assertEqual(new['native_cell'], 2-old['native_cell'])

    def test_partial_reference_domain_and_invalid_declarations_are_rejected(self):
        from superfish_ng.planar_curved_comparison import PlanarCurvedComparisonDomain, build_planar_curved_comparison
        from superfish_ng.planar_curved_refinement import refine_planar_curved_domain
        base, _ = analytic_patch()
        fine = refine_planar_curved_domain(base)
        nodes = fine.domain.cell_nodes[0]
        partial = PlanarCurvedDomain(fine.domain.points_xy_m[nodes], [[0, 1, 2, 3, 4, 5]], [[0, 1, 3], [1, 2, 4], [2, 0, 5]])
        declaration = [dict(base_cell=0, reference_vertices=[[[F(float(v)).numerator, F(float(v)).denominator]
                         for v in point] for point in fine.parent_reference_vertices[0]])]
        domain = PlanarCurvedComparisonDomain(base, base)
        with self.assertRaisesRegex(ValueError, 'completely cover'):
            build_planar_curved_comparison(base, partial, domain, current_cells=declaration)
        a, charts = analytic_patch((.25, .25))
        for key, value in (('base_cell', True), ('base_cell', 9), ('extra', 0),
                           ('reference_vertices', [[[0, 0], [0, 1]]]*3),
                           ('reference_vertices', [[[2, 1], [0, 1]], [[1, 1], [0, 1]], [[0, 1], [1, 1]]])):
            bad = deepcopy(charts)
            bad[0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                build_planar_curved_comparison(a, base, domain, previous_cells=bad)
        for key, value in (('schema_version', True), ('mapping', 'guess'), ('restriction_policy', 'tolerance'),
                           ('max_geometry_boxes_per_domain', True), ('extra', 0)):
            bad = domain.to_dict()
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                PlanarCurvedComparisonDomain.from_dict(bad)

    def test_global_pair_and_triangle_budgets_are_not_reset_by_owner(self):
        from superfish_ng.planar_curved_comparison import (PlanarCurvedComparisonDomain,
            build_planar_curved_comparison, PlanarCurvedComparisonBudgetExceeded)
        from test_planar_curved import curved_ellipse
        base = curved_ellipse(8)
        domain = PlanarCurvedComparisonDomain(base, base)
        # Each reference owner has one pair, but the total budget is seven.
        for controls in ({'max_pair_tests': 7}, {'max_triangles': 7}):
            with self.assertRaises(PlanarCurvedComparisonBudgetExceeded) as caught:
                build_planar_curved_comparison(base, base, domain, **controls)
            self.assertEqual(caught.exception.status, 'UNVERIFIED')
        complete = build_planar_curved_comparison(base, base, domain, max_pair_tests=8, max_triangles=8)
        self.assertEqual(complete.report['pair_tests'], 8)
        with self.assertRaises(ValueError):
            complete.evaluate(True, [[.2, .3]])
        for q in ([[.8, .3]], [[True, .2]], [[.5, np.nextafter(.5, 1.)]]):
            with self.assertRaises(ValueError):
                complete.evaluate(0, q)
