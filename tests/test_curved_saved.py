# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng import Case, solve
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution
from superfish_ng.sampling import FieldSampler
from superfish_ng.rf import quantities
from superfish_ng.completion import digest


class CurvedSavedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = replace(Case.load(Path(__file__).resolve().parents[1]/'examples/curved_ellipse.json'),
                           geometry_order=2)
        cls.solution = solve(cls.case)

    def test_native_roundtrip_and_fields_without_eigensolve(self):
        case = self.case
        self.assertEqual(Case.from_dict(case.to_dict()), case)
        self.assertEqual(case.to_dict()['mesh']['geometry_order'], 2)
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)/'run'
            save_run(case, self.solution, directory)
            with patch('superfish_ng.curved_solution.eigsh', side_effect=AssertionError('must not solve')):
                restored = read_solution(directory)
            np.testing.assert_array_equal(restored.u, self.solution.u)
            np.testing.assert_array_equal(restored.frequencies_hz, self.solution.frequencies_hz)
            points = self.solution.fields_in_cell(0, [[.2, .3], [.1, .1]])['points_rz_m']
            before = FieldSampler.from_solution(self.solution).evaluate(points)
            after = FieldSampler.from_solution(restored).evaluate(points)
            for name in before:
                np.testing.assert_array_equal(before[name], after[name])
            self.assertEqual(quantities(case, restored), quantities(case, self.solution))
            vtk = (directory/'mode_001.vtk').read_text()
            self.assertIn('four display triangles', vtk)
            with self.assertRaises(FileExistsError):
                save_run(case, self.solution, directory)
            with self.assertRaisesRegex(ValueError, 'high-order'):
                read_solution(directory, allow_quadratic=False)
            (directory/'save_complete.json').unlink()
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                read_solution(directory)

    def test_strict_native_controls(self):
        original = self.case.to_dict()
        for field, value in (('geometry_order', True), ('geometry_order', 3),
                             ('quadrature_order', True), ('quadrature_order', 1),
                             ('element_order', 1)):
            data = deepcopy(original)
            data['mesh' if field == 'geometry_order' else 'solver'][field] = value
            with self.assertRaises(ValueError):
                Case.from_dict(data)
        data = deepcopy(original)
        data['mesh']['geometry_order'] = 1
        with self.assertRaisesRegex(ValueError, 'quadrature_order'):
            Case.from_dict(data)
        with self.assertRaisesRegex(ValueError, 'curved_contour'):
            replace(Case(((0., .1), (.1, .1))), geometry_order=2, element_order=2)
        default = replace(self.case, geometry_order=1)
        self.assertNotIn('geometry_order', default.to_dict()['mesh'])
        self.assertNotIn('quadrature_order', default.to_dict()['solver'])

    def test_reconstructed_geometry_and_coefficients_reject_tampering(self):
        # Update the manifest too: checksums alone must not authorize invalid fields.
        for name in ('points_rz_m', 'boundary_parameters', 'u_a_per_m2', 'frequencies_hz'):
            with self.subTest(array=name), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)/'run'
                save_run(self.case, self.solution, directory)
                with np.load(directory/'fields.npz') as data:
                    arrays = {key: data[key] for key in data.files}
                if name == 'u_a_per_m2':
                    arrays[name] *= 1.1
                elif name == 'frequencies_hz':
                    arrays[name] *= 1.01
                else:
                    arrays[name].flat[0] += .001
                np.savez_compressed(directory/'fields.npz', **arrays)
                self.refresh(directory, 'fields.npz')
                with self.assertRaisesRegex(ValueError, 'geometry|normalization|residual'):
                    read_solution(directory)

    def test_rf_and_declaration_revalidation(self):
        for change in ('rf', 'declaration'):
            with tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)/'run'
                save_run(self.case, self.solution, directory)
                result = json.loads((directory/'results.json').read_text())
                if change == 'rf':
                    result['modes'][0]['wall_loss_w'] *= 1.1
                else:
                    result['field_space']['geometry_order'] = 1
                (directory/'results.json').write_text(json.dumps(result))
                self.refresh(directory, 'results.json')
                with self.assertRaisesRegex(ValueError, 'RF|declaration'):
                    read_solution(directory)

    @staticmethod
    def refresh(directory, name):
        path = directory/'save_complete.json'
        marker = json.loads(path.read_text())
        marker['files'][name] = digest(directory/name)
        path.write_text(json.dumps(marker))
