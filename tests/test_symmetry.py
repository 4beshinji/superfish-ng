# SPDX-License-Identifier: Apache-2.0
"""Independent half-domain invariants: spectrum, physical loss and parity."""
from dataclasses import replace
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng import Case, solve
from superfish_ng.analytic import pillbox_tm_mode
from superfish_ng.rf import quantities


class SymmetryTests(unittest.TestCase):
    def test_boundary_schema_is_explicit_and_strict(self):
        base = Case(((0., .075), (.04, .075)))
        self.assertEqual(base.to_dict()['schema_version'], 1)
        for side in ('z_min', 'z_max'):
            for boundary in ('electric_symmetry', 'magnetic_symmetry'):
                case = replace(base, **{side: boundary})
                data = case.to_dict()
                self.assertEqual(data['schema_version'], 2)
                self.assertEqual(Case.from_dict(data), case)
                data['schema_version'] = 1
                with self.assertRaises(ValueError):
                    Case.from_dict(data)
        for value in ('PMC', 'open', None, [], True):
            with self.assertRaises(ValueError):
                replace(base, z_min=value)
        data = dict(base.to_dict(), schema_version=2, boundaries={'radial': 'magnetic_symmetry'})
        with self.assertRaises(ValueError):
            Case.from_dict(data)

    def test_half_frequency_loss_and_essential_axis_endpoint(self):
        for side in ('z_min', 'z_max'):
            for p, boundary in enumerate(('electric_symmetry', 'magnetic_symmetry')):
                with self.subTest(side=side, p=p):
                    case = Case(((0., .075), (.04, .075)), nr=32, nz=22, modes=1,
                                normalization_j=.5, **{side: boundary})
                    solution = solve(case)
                    q = quantities(case, solution)
                    exact = pillbox_tm_mode(.075, .08, p=p)
                    self.assertLess(abs(q['frequency_hz']/exact['frequency_hz']-1), .001)
                    self.assertLess(abs(q['q0']/exact['q0']-1), .004)
                    self.assertLess(abs(2*q['wall_loss_w']/exact['wall_loss_w']-1), .004)
                    self.assertLess(q['energy_balance_relative'], 1e-10)
                    tags = solution.mesh.boundary_tags
                    self.assertEqual(set(tags), {'axis', 'pec', boundary})
                    end = 0. if side == 'z_min' else case.length
                    nodes = np.flatnonzero(solution.mesh.points[:, 1] == end)
                    if p == 1:
                        np.testing.assert_array_equal(solution.u[nodes], 0.)
                    else:
                        self.assertGreater(np.max(np.abs(solution.u[nodes])), 1.)
                    other_axis = solution.mesh.axis_nodes[1:-1]
                    self.assertTrue(np.all(np.abs(solution.u[other_axis]) > 1.))

    def test_reflected_fields_energy_and_full_voltage(self):
        from superfish_ng.symmetry import reflect_solution
        from superfish_ng.sampling import FieldSampler
        for side in ('z_min', 'z_max'):
            for p, boundary in enumerate(('electric_symmetry', 'magnetic_symmetry')):
                with self.subTest(side=side, p=p):
                    half = Case(((0., .075), (.04, .075)), nr=28, nz=24, modes=1,
                                normalization_j=.5, **{side: boundary})
                    solution = solve(half)
                    full, reflected = reflect_solution(half, solution)
                    self.assertEqual(full.length, .08)
                    self.assertEqual(full.normalization_j, 1.)
                    self.assertEqual(set(reflected.mesh.boundary_tags), {'axis', 'pec'})
                    qh, qf = quantities(half, solution), quantities(full, reflected)
                    for key in ('stored_energy_j', 'wall_loss_w'):
                        self.assertAlmostEqual(qf[key]/qh[key], 2., places=10)
                    self.assertAlmostEqual(qf['q0']/qh['q0'], 1., places=10)
                    exact = pillbox_tm_mode(.075, .08, p=p)
                    for key in ('r_over_q_accelerator_ohm', 'transit_time_factor_abs'):
                        self.assertLess(abs(qf[key]/exact[key]-1), .006)
                    self.assertLess(max(reflected.residuals), 1e-7)
                    sampler = FieldSampler(reflected.mesh.points, reflected.mesh.triangles,
                                           reflected.u, reflected.frequencies_hz)
                    a = sampler.evaluate(np.array([[.0241, .0101], [.0511, .0251]]))
                    b = sampler.evaluate(np.array([[.0241, .0699], [.0511, .0549]]))
                    for key, parity in [('Hphi_A_per_m', (-1)**p),
                                        ('Ez_quadrature_V_per_m', (-1)**p),
                                        ('Er_quadrature_V_per_m', -(-1)**p)]:
                        np.testing.assert_allclose(a[key], parity*b[key], rtol=1e-8, atol=1e-5)

    def test_reflection_requires_exactly_one_symmetry_end(self):
        from superfish_ng.symmetry import reflect_solution
        base = Case(((0., .075), (.04, .075)), nr=4, nz=4, modes=1)
        for case in (base, replace(base, z_min='electric_symmetry', z_max='electric_symmetry')):
            with self.assertRaises(ValueError):
                reflect_solution(case, solve(case))

    def test_cli_reflection_preserves_source_and_normalization(self):
        from superfish_ng.cli import main
        half = Case(((0., .075), (.04, .075)), nr=6, nz=5, modes=1,
                    normalization_j=.5, z_min='magnetic_symmetry')
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            root = Path(temp)
            (root/'input.json').write_text(json.dumps(half.to_dict()))
            self.assertEqual(main(['solve', str(root/'input.json'), '--reflect-full', '--out', str(root/'full')]), 0)
            saved = json.loads((root/'full/results.json').read_text())
            self.assertEqual(saved['reflection_source_case'], half.to_dict())
            self.assertIn('NOT full-spectrum ranks', saved['field_construction'])
            self.assertAlmostEqual(saved['modes'][0]['stored_energy_j'], 1., places=10)


if __name__ == '__main__':
    unittest.main()
