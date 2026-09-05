# SPDX-License-Identifier: Apache-2.0
"""Reflection-neutral triangulation has independent geometry/physics invariants."""
from dataclasses import replace
from pathlib import Path
import unittest
import numpy as np
from superfish_ng import Case, make_mesh, solve
from superfish_ng.mesh import element_geometry
from superfish_ng.fem import assemble


class CrossedMeshTests(unittest.TestCase):
    def test_periodic_cell_amplitudes_do_not_have_axial_ramp(self):
        # Identical half-end cells: the 0/pi band ends have equal lobe magnitudes.
        # The previous one-direction diagonals gave ~1% ramp at nr=64.
        from superfish_ng.modes import identify_cell_band
        case = replace(Case.load(Path(__file__).resolve().parents[1]/'examples/seminar_7cell_rounded.json'),
                       nr=16, nz=84, triangulation='crossed')
        sol = solve(case)
        z = sol.mesh.points[sol.mesh.axis_nodes, 1]
        modes = identify_cell_band(z, sol.u[sol.mesh.axis_nodes], np.linspace(0., case.length, 7))
        for p in (0, 6):
            np.testing.assert_allclose(np.abs(modes[p]['cell_amplitudes_normalized']), 1., rtol=0, atol=1e-7)

    def test_pillbox_frequency_field_and_rf_against_analytic_solution(self):
        from superfish_ng.analytic import pillbox_tm_mode
        from superfish_ng.rf import quantities
        case = Case(((0., .075), (.08, .075)), nr=64, nz=70, modes=2, triangulation='crossed')
        sol = solve(case)
        for p in (0, 1):
            expected = pillbox_tm_mode(.075, .08, p=p)
            actual = quantities(case, sol, p)
            for key in ('frequency_hz', 'q0', 'geometry_factor_ohm', 'wall_loss_w',
                        'r_over_q_accelerator_ohm', 'transit_time_factor_abs'):
                self.assertLess(abs(actual[key]/expected[key]-1), .001 if key == 'frequency_hz' else .005)
            z = sol.mesh.points[sol.mesh.axis_nodes, 1]
            field = sol.u[sol.mesh.axis_nodes, p]
            reference = np.cos(p*np.pi*z/.08)
            field = field*np.sign(field @ reference)/np.max(np.abs(field))
            self.assertLess(np.linalg.norm(field-reference)/np.linalg.norm(reference), .005)

    def test_schema_roundtrip_and_legacy_default(self):
        base = Case(((0., .075), (.08, .075)))
        self.assertNotIn('triangulation', base.to_dict()['mesh'])
        case = replace(base, triangulation='crossed')
        self.assertEqual(case.to_dict()['schema_version'], 2)
        self.assertEqual(Case.from_dict(case.to_dict()), case)
        with self.assertRaises(ValueError):
            replace(base, triangulation='invalid')
        with self.assertRaises(ValueError):
            Case.from_dict(dict(case.to_dict(), schema_version=1))

    def test_exact_domain_integrals_and_reflection_invariance(self):
        for kind in ('profile', 'stepped_profile'):
            case = Case(((0., .075), (.08, .075)), nr=8, nz=10,
                        geometry_type=kind, triangulation='crossed', modes=2)
            mesh = make_mesh(case)
            _, det, _ = element_geometry(mesh)
            self.assertEqual(len(mesh.triangles), 4*8*10)
            self.assertAlmostEqual(det.sum()/2, .075*.08, places=14)
            self.assertEqual(len(mesh.axis_nodes), 11)
            k, m = assemble(mesh)
            one = np.ones(len(mesh.points))
            self.assertAlmostEqual(one @ (m @ one), .08*.075**4/4, places=17)
            # Match every reflected vertex and triangle: no preferred axial diagonal.
            lookup = {tuple(np.round(p, 13)): i for i, p in enumerate(mesh.points)}
            mirror = np.array([lookup[tuple(np.round([r, .08-z], 13))] for r, z in mesh.points])
            original = {tuple(sorted(t)) for t in mesh.triangles}
            self.assertEqual(original, {tuple(sorted(mirror[t])) for t in mesh.triangles})
            sol = solve(case)
            for mode, parity in ((0, 1), (1, -1)):
                self.assertLess(np.linalg.norm(sol.u[mirror, mode]-parity*sol.u[:, mode]) /
                                np.linalg.norm(sol.u[:, mode]), 1e-8)


if __name__ == '__main__':
    unittest.main()
