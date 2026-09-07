# SPDX-License-Identifier: Apache-2.0
"""External meshes must preserve physical integrals under arbitrary numbering."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from superfish_ng import Case, solve
from superfish_ng.analytic import pillbox_tm010
from superfish_ng.io import save_run
from superfish_ng.mesh import make_mesh
from superfish_ng.mesh_input import mesh_from_dict, mesh_to_dict
from superfish_ng.rf import quantities
from superfish_ng.saved import read_solution
from superfish_ng.cli import main
from superfish_ng.symmetry import reflect_solution


class MeshInputTests(unittest.TestCase):
    def setUp(self):
        self.case = Case(((0., .08), (.12, .08)), nr=24, nz=32, modes=1)
        self.mesh = make_mesh(self.case)
        self.data = mesh_to_dict(self.mesh)

    def permuted(self):
        data = deepcopy(self.data)
        order = np.random.default_rng(17).permutation(len(self.mesh.points))
        inverse = np.argsort(order)
        data['points'] = self.mesh.points[order].tolist()
        data['triangles'] = inverse[self.mesh.triangles[::-1]].tolist()
        data['boundary_edges'] = inverse[self.mesh.boundary_edges[::-1, ::-1]].tolist()
        data['boundary_tags'] = self.mesh.boundary_tags[::-1].tolist()
        return data

    def test_node_and_cell_permutation_preserves_frequency_rf_and_axis(self):
        normal = quantities(self.case, solve(self.case))
        solution = solve(self.case, mesh_data=self.permuted())
        actual = quantities(self.case, solution)
        for key in ('frequency_hz', 'r_over_q_accelerator_ohm', 'geometry_factor_ohm',
                    'vacc_v', 'epk_surface_estimate_v_per_m'):
            self.assertLess(abs(actual[key]/normal[key]-1), 1e-9, key)
        axis = solution.mesh.points[solution.mesh.axis_nodes]
        self.assertTrue(np.all(np.diff(axis[:, 1]) > 0))
        self.assertTrue(np.all(axis[:, 0] == 0))
        exact = pillbox_tm010(.08, .12)
        self.assertLess(abs(actual['frequency_hz']/exact['frequency_hz']-1), 1e-4)
        self.assertLess(abs(actual['r_over_q_accelerator_ohm']/exact['r_over_q_accelerator_ohm']-1), .005)

    def test_missing_unknown_wrong_or_internal_boundary_tags_fail(self):
        for change in ('missing', 'unknown', 'wrong', 'internal'):
            with self.subTest(change=change):
                data = deepcopy(self.data)
                if change == 'missing':
                    data['boundary_edges'].pop()
                    data['boundary_tags'].pop()
                elif change == 'unknown':
                    data['boundary_tags'][0] = 'vacuum'
                elif change == 'wrong':
                    index = data['boundary_tags'].index('axis')
                    data['boundary_tags'][index] = 'pec'
                else:
                    data['boundary_edges'].append(list(self.mesh.triangles[0, [0, 2]]))
                    data['boundary_tags'].append('pec')
                with self.assertRaises(ValueError):
                    mesh_from_dict(self.case, data)

    def test_invalid_numbers_connectivity_and_units_fail(self):
        for change in ('units', 'order', 'index', 'float_index', 'boolean', 'negative',
                       'nan', 'duplicate', 'orphan', 'reversed', 'duplicate_cell', 'unknown_key'):
            with self.subTest(change=change):
                data = deepcopy(self.data)
                if change == 'units': data['length_unit'] = 'mm'
                elif change == 'order': data['coordinate_order'] = 'zr'
                elif change == 'index': data['triangles'][0][0] = len(data['points'])
                elif change == 'float_index': data['triangles'][0][0] = 0.0
                elif change == 'boolean': data['points'][0][0] = False
                elif change == 'negative': data['points'][1][0] = -.1
                elif change == 'nan': data['points'][0][0] = float('nan')
                elif change == 'duplicate': data['points'][1] = data['points'][0][:]
                elif change == 'orphan': data['points'].append([.03, .03])
                elif change == 'reversed': data['triangles'][0].reverse()
                elif change == 'duplicate_cell': data['triangles'].append(data['triangles'][0][:])
                else: data['material'] = 'iron'
                with self.assertRaises(ValueError):
                    mesh_from_dict(self.case, data)

    def test_wrong_geometry_and_symmetry_are_rejected(self):
        with self.assertRaises(ValueError):
            mesh_from_dict(replace(self.case, profile=((0., .09), (.12, .09))), self.data)
        half = replace(self.case, z_max='magnetic_symmetry')
        with self.assertRaises(ValueError):
            mesh_from_dict(half, self.data)
        data = mesh_to_dict(make_mesh(half))
        solution = solve(half, mesh_data=data)
        nodes = np.unique(solution.mesh.boundary_edges[solution.mesh.boundary_tags == 'magnetic_symmetry'])
        self.assertTrue(np.all(solution.u[nodes] == 0))

    def test_saved_external_mesh_is_reproducible_and_verified(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)/'result'
            result = save_run(self.case, solve(self.case, mesh_data=self.permuted()), out)
            data = json.loads((out/'mesh.json').read_text())
            self.assertIn('input_sha256', result['mesh'])
            replay = quantities(self.case, solve(self.case, mesh_data=data))
            self.assertAlmostEqual(replay['frequency_hz'], result['modes'][0]['frequency_hz'], delta=.001)
            read_solution(out)
            data['points'][0][0] += .001
            (out/'mesh.json').write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'mesh'):
                read_solution(out)

    def test_unstructured_delaunay_mesh_converges_against_analytic_rf(self):
        from scipy.spatial import Delaunay
        from superfish_ng.mesh import finish_mesh
        exact = pillbox_tm010(.08, .12)
        errors = []
        for n in (16, 32, 64):
            rng = np.random.default_rng(19)
            points = np.array([(r, z) for z in np.linspace(0, .12, n+1)
                               for r in np.linspace(0, .08, n+1)])
            interior = ((points[:, 0] > 0) & (points[:, 0] < .08)
                        & (points[:, 1] > 0) & (points[:, 1] < .12))
            points[interior] += rng.uniform(-.2, .2, (sum(interior), 2))*[.08/n, .12/n]
            mesh = finish_mesh(self.case, points, Delaunay(points).simplices,
                               np.flatnonzero(points[:, 0] == 0))
            row = quantities(self.case, solve(self.case, mesh_data=mesh_to_dict(mesh)))
            errors.append({key: abs(row[key]/exact[key]-1) for key in
                           ('frequency_hz', 'r_over_q_accelerator_ohm', 'geometry_factor_ohm')})
        for key in errors[0]:
            self.assertLess(errors[-1][key], errors[0][key], key)
            self.assertLess(errors[-1][key], 1e-4 if key == 'frequency_hz' else .005, key)

    def test_cli_replay_and_reflected_mesh_preserve_metadata(self):
        half = replace(self.case, z_max='magnetic_symmetry')
        data = mesh_to_dict(make_mesh(half))
        full, reflected = reflect_solution(half, solve(half, mesh_data=data))
        mesh_from_dict(full, reflected.mesh_input)
        self.assertAlmostEqual(quantities(full, reflected)['stored_energy_j'], 2.)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'case.json').write_text(json.dumps(half.to_dict()))
            (root/'mesh.json').write_text(json.dumps(data))
            args = ['solve', str(root/'case.json'), '--mesh', str(root/'mesh.json'),
                    '--reflect-full', '--out', str(root/'result')]
            self.assertEqual(main(args), 0)
            read_solution(root/'result')
            self.assertEqual(main(args), 2)
