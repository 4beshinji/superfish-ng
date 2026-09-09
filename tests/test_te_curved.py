# SPDX-License-Identifier: Apache-2.0
import contextlib
import io
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
import numpy as np
from superfish_ng import Case, solve
from superfish_ng.cli import main
from superfish_ng.completion import digest
from superfish_ng.constants import MU0, TAU
from superfish_ng.curved_solution import solve_curved
from superfish_ng.io import save_run
from superfish_ng.model import Model
from superfish_ng.te import TEFieldSampler, te_quantities
from superfish_ng.te_curved import wall_integral
from superfish_ng.te_saved import read_te_run
import test_curved_solution

ROOT = Path(__file__).resolve().parents[1]


def sphere(level=0):
    data = json.loads((ROOT/'examples/optimization/curved_rf.json').read_text())['project']['case']
    data['model']['polarization'] = 'te'
    return replace(Case.from_dict(data), curved_refinement_levels=level)


class CurvedTETests(unittest.TestCase):
    def test_straight_limit_preserves_te_constraints_and_rf(self):
        for tag in ('pec', 'electric_symmetry', 'magnetic_symmetry'):
            c = replace(test_curved_solution.CurvedSolutionTests().case(tag), model=Model(polarization='te'))
            straight, curved = solve(c), solve_curved(c)
            np.testing.assert_allclose(curved.frequencies_hz, straight.frequencies_hz, rtol=1e-11)
            np.testing.assert_allclose(curved.coefficients_v_per_m2, straight.coefficients_v_per_m2, rtol=1e-8, atol=1e-4)
            for mode in range(c.modes):
                a, b = te_quantities(straight, mode), te_quantities(curved, mode)
                for key in ('stored_energy_j', 'wall_loss_w', 'geometry_factor_ohm', 'q0'):
                    self.assertAlmostEqual(a[key]/b[key], 1., places=9)

    def test_mapped_linear_physical_field_and_axis(self):
        s = solve(sphere())
        p = s.space.geometry.points_rz_m
        s.coefficients_v_per_m2[:, 0] = 1+2*p[:, 0]+3*p[:, 1]
        cells = np.arange(len(s.space.geometry.cell_nodes))
        bary = np.tile([.5, .2, .3], (len(cells), 1))
        fields = s.fields_in_cells(cells, bary)
        points = np.array([m.evaluate([[.2, .3]])['points_rz_m'][0] for m in s.space.geometry.local_maps])
        r, z = points.T; v = 1+2*r+3*z; omega = TAU*s.frequencies_hz[0]
        for name, expected in dict(Ephi_V_per_m=r*v, Hr_quadrature_A_per_m=-3*r/(omega*MU0), Hz_quadrature_A_per_m=(2*v+2*r)/(omega*MU0)).items():
            np.testing.assert_allclose(fields[name], expected, rtol=1e-11, atol=1e-14)
        axis = TEFieldSampler(s).evaluate([[0., .08], [0., .04]])
        self.assertTrue(np.all(axis['Ephi_V_per_m']==0))
        self.assertTrue(np.all(axis['Hr_quadrature_A_per_m']==0))
        self.assertTrue(np.all(axis['Hz_quadrature_A_per_m']>0))
        self.assertFalse(TEFieldSampler(s).evaluate([[1., 1.]], outside='nan')['inside'][0])
        with self.assertRaisesRegex(ValueError, 'outside'):
            TEFieldSampler(s).evaluate([[1., 1.]])

    def test_wall_side_orientation_quadrature_and_scaling(self):
        s = solve(sphere(1)); expected = wall_integral(s, 0)
        self.assertAlmostEqual(wall_integral(s, 0, 16)/expected, 1., places=10)
        g = s.space.geometry; edges = g.boundary_nodes.copy(); edges[:, :2] = edges[:, 1::-1]
        reverse = replace(s, space=replace(s.space, geometry=replace(g, boundary_nodes=edges)))
        self.assertAlmostEqual(wall_integral(reverse, 0)/expected, 1., places=12)
        doubled = replace(s, coefficients_v_per_m2=2*s.coefficients_v_per_m2)
        a, b = te_quantities(s), te_quantities(doubled)
        for key in ('stored_energy_j', 'wall_loss_w'):
            self.assertAlmostEqual(b[key]/a[key], 4., places=11)
        for key in ('q0', 'geometry_factor_ohm'):
            self.assertAlmostEqual(b[key]/a[key], 1., places=11)
        for mode in (True, -1, s.case.modes):
            with self.assertRaises(ValueError): wall_integral(s, mode)
        for order in (True, 1, 2.5):
            with self.assertRaises(ValueError): wall_integral(s, 0, order)

    def test_cli_saved_actual_geometry_and_forged_geometry_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); c = sphere(1); casefile = root/'case.json'
            casefile.write_text(json.dumps(c.to_dict()))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['solve', str(casefile), '--out', str(root/'run')]), 0)
                self.assertEqual(main(['replay-te', str(root/'run')]), 0)
            s = read_te_run(root/'run'); fresh = solve(c)
            np.testing.assert_array_equal(s.coefficients_v_per_m2, fresh.coefficients_v_per_m2)
            result = json.loads((root/'run/results.json').read_text())
            self.assertEqual(result['schema_version'], 3)
            self.assertEqual(result['field_space']['geometry_order'], 2)
            vtk = (root/'run/mode_001.vtk').read_text()
            self.assertIn(f'POINTS {len(s.space.geometry.points_rz_m)} double', vtk)
            self.assertIn(f'CELL_TYPES {len(s.space.geometry.cell_nodes)}\n22\n', vtk)
            path = root/'run/geometry.npz'
            with np.load(path) as data: arrays = {key:data[key] for key in data.files}
            arrays['points_rz_m'][0, 1] += 1e-8
            np.savez_compressed(path, **arrays)
            marker = json.loads((root/'run/te_complete.json').read_text()); marker['files']['geometry.npz'] = digest(path)
            (root/'run/te_complete.json').write_text(json.dumps(marker))
            with self.assertRaisesRegex(ValueError, 'geometry differs'): read_te_run(root/'run')

    def test_local_refinement_history_reconstructs_actual_space(self):
        from superfish_ng.curved_refinement_steps import CurvedRefinementStep
        c = replace(sphere(), curved_refinement_steps=(CurvedRefinementStep('marked', (0,), 1.), CurvedRefinementStep('uniform')))
        s = solve(c)
        self.assertGreater(len(s.space.geometry.cell_nodes), len(s.mesh.triangles)*4)
        tags = s.space.boundary_tags
        constrained = np.unique(s.space.geometry.boundary_nodes[np.isin(tags, ['pec', 'electric_symmetry'])])
        np.testing.assert_array_equal(s.space.constrained_dofs, constrained)
        self.assertTrue(np.all(s.coefficients_v_per_m2[constrained]==0))
        with tempfile.TemporaryDirectory() as tmp:
            save_run(c, s, Path(tmp)/'run'); saved = read_te_run(Path(tmp)/'run')
            np.testing.assert_array_equal(saved.space.geometry.cell_nodes, s.space.geometry.cell_nodes)
            np.testing.assert_array_equal(saved.coefficients_v_per_m2, s.coefficients_v_per_m2)
