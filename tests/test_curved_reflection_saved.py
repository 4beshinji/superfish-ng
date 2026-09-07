# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from test_curved_reflection import half_case
import test_curved_saved
from superfish_ng import solve
from superfish_ng.symmetry import reflect_solution
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution


class CurvedReflectionSavedTests(unittest.TestCase):
    def test_both_sides_and_parities_roundtrip_without_eigensolve(self):
        for side in ('z_min', 'z_max'):
            for tag in ('electric_symmetry', 'magnetic_symmetry'):
                with self.subTest(side=side, tag=tag), tempfile.TemporaryDirectory() as temp:
                    case = replace(half_case(side, tag, 1), active_length_m=.07,
                                   voltage_interval_m=(0., .08) if side == 'z_min' else (.02, .1),
                                   phase_origin_m=.013)
                    half = solve(case)
                    with patch('superfish_ng.curved_solution.eigsh', side_effect=AssertionError('no solve')):
                        full, solution = reflect_solution(case, half)
                        directory = Path(temp)/'run'
                        result = save_run(full, solution, directory)
                        restored = read_solution(directory)
                        save_run(full, restored, Path(temp)/'resaved')
                        again = read_solution(Path(temp)/'resaved')
                    self.assertEqual(full.normalization_j, 2*case.normalization_j)
                    self.assertEqual(result['reflection']['source_case'], case.to_dict())
                    self.assertIn('NOT full-spectrum ranks', result['field_construction'])
                    np.testing.assert_array_equal(restored.u, solution.u)
                    np.testing.assert_array_equal(again.u, solution.u)
                    np.testing.assert_array_equal(restored.frequencies_hz, half.frequencies_hz)
                    self.assertLess(max(restored.residuals), 1e-7)
                    self.assertEqual(restored.reflection_source_case, case)
                    self.assertAlmostEqual(restored.case.active_length_m, .14)
                    self.assertAlmostEqual(restored.case.phase_origin_m, .113 if side == 'z_min' else .013)
                    for cell in (0, len(solution.space.geometry.cell_nodes)-1):
                        before = solution.fields_in_cell(cell, [[.2, .3]])
                        after = restored.fields_in_cell(cell, [[.2, .3]])
                        for key in before:
                            np.testing.assert_array_equal(before[key], after[key])

    def test_declarations_and_parity_are_revalidated_after_hash_refresh(self):
        case = half_case('z_max', 'magnetic_symmetry')
        full, solution = reflect_solution(case, solve(case))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = save_run(full, solution, root/'original')
            for change in ('version', 'side', 'parity', 'source', 'missing', 'construction', 'coefficients'):
                with self.subTest(change=change):
                    target = root/change
                    shutil.copytree(root/'original', target)
                    result = deepcopy(original)
                    if change == 'version':
                        result['reflection']['version'] = True
                    elif change == 'side':
                        result['reflection']['side'] = 'z_min'
                    elif change == 'parity':
                        result['reflection']['parity'] = 1
                    elif change == 'source':
                        result['reflection']['source_case']['rf']['normalization_j'] *= 2
                    elif change == 'missing':
                        del result['reflection']
                    elif change == 'construction':
                        result['field_construction'] = 'direct full-spectrum solve'
                    else:
                        with np.load(target/'fields.npz') as data:
                            arrays = {name: data[name] for name in data.files}
                        arrays['u_a_per_m2'][-1, 0] += 1.
                        np.savez_compressed(target/'fields.npz', **arrays)
                        test_curved_saved.CurvedSavedTests.refresh(target, 'fields.npz')
                    (target/'results.json').write_text(json.dumps(result))
                    test_curved_saved.CurvedSavedTests.refresh(target, 'results.json')
                    with self.assertRaises(ValueError):
                        read_solution(target)

    def test_cli_reflect_full(self):
        from superfish_ng.cli import main
        case = half_case('z_min', 'electric_symmetry')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'case.json').write_text(json.dumps(case.to_dict()))
            self.assertEqual(main(['solve', str(root/'case.json'), '--reflect-full', '--out', str(root/'run')]), 0)
            restored = read_solution(root/'run')
            self.assertEqual(restored.case.normalization_j, 2.)
            self.assertEqual(restored.reflection_source_case, case)

    def test_case_mismatch_and_second_reflection_rejected(self):
        case = half_case('z_min', 'electric_symmetry')
        half = solve(case)
        with self.assertRaisesRegex(ValueError, 'matching'):
            reflect_solution(replace(case, normalization_j=2), half)
        full, solution = reflect_solution(case, half)
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            reflect_solution(full, solution)
