# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from pathlib import Path
import unittest
import numpy as np
from superfish_ng import Case, solve
from superfish_ng.constants import EPS0, TAU
from superfish_ng.curved_surface import CurvedSurfaceSampler, sampled_surface_summary


class CurvedSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.solution = solve(replace(Case.load(Path(__file__).resolve().parents[1]/'examples/curved_ellipse.json'), geometry_order=2))

    def test_manufactured_field_projection_and_outward_normal(self):
        solution = self.solution
        p = solution.space.geometry.points_rz_m
        u = solution.u.copy()
        u[:, 0] = 1+2*p[:, 0]+3*p[:, 1]
        sampler = CurvedSurfaceSampler(replace(solution, u=u))
        omega = TAU*solution.frequencies_hz[0]
        for edge in range(len(sampler.owners)):
            field = sampler.evaluate(edge, [0., .25, .75, 1.])
            r, z = field['points_rz_m'].T
            expected = np.column_stack((-3*r, 2*(1+2*r+3*z)+2*r))/(omega*EPS0)
            np.testing.assert_allclose(field['En_quadrature_V_per_m'], np.sum(expected*field['normal_rz'], axis=1), atol=1e-12)
            np.testing.assert_allclose(field['Et_quadrature_V_per_m'], np.sum(expected*field['tangent_rz'], axis=1), atol=1e-12)
            np.testing.assert_allclose(np.sum(field['normal_rz']**2, axis=1), 1.)
            # Ellipse centre is inside this convex test domain: normals point away.
            outward = field['points_rz_m']-np.array([.01, solution.case.length/2])
            self.assertTrue(np.all(np.sum(outward*field['normal_rz'], axis=1) > 0))

    def test_reversing_stored_boundary_does_not_reverse_outward_normal(self):
        solution = self.solution
        geometry = solution.space.geometry
        reversed_geometry = replace(geometry, boundary_nodes=geometry.boundary_nodes[:, [1, 0, 2]])
        reversed_solution = replace(solution, space=replace(solution.space, geometry=reversed_geometry))
        first, second = CurvedSurfaceSampler(solution), CurvedSurfaceSampler(reversed_solution)
        for edge in range(len(first.owners)):
            a, b = first.evaluate(edge, [.2, .8]), second.evaluate(edge, [.8, .2])
            for key in a:
                np.testing.assert_allclose(a[key], b[key], atol=1e-8, rtol=1e-12)

    def test_sample_summary_and_strict_parameters(self):
        sampler = CurvedSurfaceSampler(self.solution)
        for parameters in ([True], [], [-.1], [1.1], [float('nan')], [[.5]]):
            with self.assertRaises(ValueError):
                sampler.evaluate(0, parameters)
        for edge in (True, -1, len(sampler.owners)):
            with self.assertRaises(ValueError):
                sampler.evaluate(edge, [.5])
        summary = sampled_surface_summary(self.solution)
        self.assertIn('sampled estimates', summary['status'])
        for key in ('E_abs_V_per_m', 'Hphi_A_per_m', 'Et_quadrature_V_per_m'):
            self.assertEqual(self.solution.space.boundary_tags[summary[key]['boundary_index']], 'pec')
        with self.assertRaises(ValueError):
            sampled_surface_summary(self.solution, samples_per_edge=True)

    def test_corner_derivatives_are_not_averaged(self):
        solution = self.solution
        u = np.random.default_rng(20260908).normal(size=solution.u.shape)
        sampler = CurvedSurfaceSampler(replace(solution, u=u))
        by_node = {}
        for edge, nodes in enumerate(solution.space.geometry.boundary_nodes):
            field = sampler.evaluate(edge, [0., 1.])
            for endpoint, node in enumerate(nodes[:2]):
                value = np.array([field['Er_quadrature_V_per_m'][endpoint], field['Ez_quadrature_V_per_m'][endpoint]])
                by_node.setdefault(int(node), []).append(value)
        jumps = [np.linalg.norm(values[0]-values[1]) for values in by_node.values() if len(values) == 2]
        self.assertGreater(max(jumps), 1e-3)
