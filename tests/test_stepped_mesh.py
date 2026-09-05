# SPDX-License-Identifier: Apache-2.0
"""Conforming stepped-wall mesh: topology, exact domain integrals and physics."""
from dataclasses import replace
import unittest
import numpy as np
from superfish_ng import Case, make_mesh, solve
from superfish_ng.fem import assemble
from superfish_ng.mesh import element_geometry
from superfish_ng.rf import quantities


PROFILE = ((0., .05), (.03, .05), (.03, .02), (.04, .02), (.04, .05), (.08, .05))


class SteppedMeshTests(unittest.TestCase):
    def test_explicit_geometry_schema_and_invalid_walls(self):
        case = Case(PROFILE, geometry_type='stepped_profile')
        self.assertEqual(case.to_dict()['schema_version'], 2)
        self.assertEqual(Case.from_dict(case.to_dict()), case)
        with self.assertRaises(ValueError):
            Case(PROFILE)
        data = dict(case.to_dict(), schema_version=1)
        with self.assertRaises(ValueError):
            Case.from_dict(data)
        for profile in [((0., .05), (.04, .05), (.03, .02), (.08, .02)),
                        ((0., .05), (.03, .05), (.03, .02), (.03, .03), (.08, .03)),
                        ((0., .05), (0., .02), (.08, .02)),
                        ((0., .05), (.08, .05), (.08, .02)),
                        ((0., .05), (.03, .05), (.03, .05), (.08, .02))]:
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                Case(profile, geometry_type='stepped_profile')

    def test_stepped_domain_topology_area_and_exact_constant_integrals(self):
        case = Case(PROFILE, geometry_type='stepped_profile', nr=12, nz=18)
        mesh = make_mesh(case)
        _, det, _ = element_geometry(mesh)
        self.assertAlmostEqual(det.sum()/2, .07*.05+.01*.02, places=13)
        for z in (.03, .04):
            vertical = mesh.boundary_edges[np.all(mesh.points[mesh.boundary_edges, 1] == z, axis=1)]
            self.assertGreater(len(vertical), 0)
            lengths = np.linalg.norm(np.diff(mesh.points[vertical], axis=1)[:, 0], axis=1)
            self.assertAlmostEqual(lengths.sum(), .03, places=13)
        # Every boundary vertex has degree two; no cracks/T-junction boundaries.
        _, counts = np.unique(mesh.boundary_edges, return_counts=True)
        np.testing.assert_array_equal(counts, 2)
        k, m = assemble(mesh)
        one = np.ones(len(mesh.points))
        self.assertAlmostEqual(one @ (m @ one), (.07*.05**4+.01*.02**4)/4, places=17)
        self.assertAlmostEqual(one @ (k @ one), 2*(.07*.05**2+.01*.02**2), places=13)
        self.assertTrue(np.all(np.diff(mesh.points[mesh.axis_nodes, 1]) > 0))

    def test_sloped_wall_with_step_has_no_missing_boundary(self):
        profile = ((0., .04), (.03, .06), (.03, .02), (.06, .025), (.06, .05), (.08, .04))
        case = Case(profile, geometry_type='stepped_profile', nr=15, nz=22)
        mesh = make_mesh(case)
        _, det, _ = element_geometry(mesh)
        expected = sum((b[0]-a[0])*(a[1]+b[1])/2 for a, b in zip(profile, profile[1:]))
        self.assertAlmostEqual(det.sum()/2, expected, places=13)
        wall = mesh.points[mesh.boundary_edges[mesh.boundary_tags == 'pec']]
        length = np.linalg.norm(wall[:, 1]-wall[:, 0], axis=1).sum()
        exact = profile[0][1]+profile[-1][1]+sum(np.linalg.norm(np.subtract(b, a)) for a, b in zip(profile, profile[1:]))
        self.assertAlmostEqual(length, exact, places=12)

    def test_pillbox_spectrum_rf_and_symmetry_remain_correct(self):
        base = Case(((0., .075), (.08, .075)), nr=20, nz=22, modes=2)
        reference = solve(base)
        wall = replace(base, geometry_type='stepped_profile')
        actual = solve(wall)
        for index in (0, 1):
            a, b = quantities(base, reference, index), quantities(wall, actual, index)
            for key in ('frequency_hz', 'q0', 'r_over_q_accelerator_ohm'):
                self.assertLess(abs(a[key]/b[key]-1), 1e-10)
        symmetric = replace(wall, z_min='magnetic_symmetry')
        sol = solve(symmetric)
        self.assertEqual(set(sol.mesh.boundary_tags), {'axis', 'pec', 'magnetic_symmetry'})
        np.testing.assert_array_equal(sol.u[sol.mesh.points[:, 1] == 0], 0.)

    def test_disk_is_excluded_from_field_sampling_and_bad_boundary_rejected(self):
        from superfish_ng.sampling import FieldSampler
        from superfish_ng.mesh import validate_profile_mesh
        case = Case(PROFILE, geometry_type='stepped_profile', nr=12, nz=18, modes=1)
        sol = solve(case)
        sampler = FieldSampler(sol.mesh.points, sol.mesh.triangles, sol.u, sol.frequencies_hz)
        probes = np.array([[.03, .035], [.015, .035], [.03, .02], [.03, .05]])
        sampled = sampler.evaluate(probes, outside='nan')
        np.testing.assert_array_equal(sampled['inside'], [False, True, True, True])
        bad = replace(sol.mesh, boundary_edges=sol.mesh.boundary_edges[:-1])
        with self.assertRaises(ValueError):
            validate_profile_mesh(case, bad)


if __name__ == '__main__':
    unittest.main()
