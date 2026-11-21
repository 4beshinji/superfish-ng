# SPDX-License-Identifier: Apache-2.0
"""Offline reference-preparation guards; no Wine or synthetic reference PASS."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from prepare_planar_superfish_comparison import candidate_inputs, prepare
from superfish_ng.planar import PlanarCase
from superfish_ng import Case


class PlanarReferencePreparationTests(unittest.TestCase):
    def test_unknown_reference_cannot_be_promoted_by_preparation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            out = root / 'out' / 'prepared'
            report = prepare(out, project_root=root)
            self.assertEqual(report['status'], 'UNVERIFIED')
            self.assertFalse(report['passed'])
            self.assertEqual((report['new_ng_solves'], report['new_legacy_runs']), (0, 0))
            self.assertIsNone(report['reference_version']['observed'])
            self.assertEqual(len(report['cases']), 6)
            self.assertEqual(json.loads((out / 'comparison.json').read_text()), report)
            for item in report['cases']:
                self.assertTrue(all(g['status'] == 'UNVERIFIED' for g in item['gates'].values()))
                self.assertTrue(all(g['status'] == 'UNVERIFIED' for g in item['acceptance_axes'].values()))
                self.assertIsNone(item['mode_correspondence']['ng_mode_index'])
                self.assertIsNone(item['mode_correspondence']['reference_mode'])
                self.assertEqual(item['legacy_polarization_candidate']['status'], 'UNVERIFIED')
                self.assertEqual(item['both_sides_refinement']['status'], 'UNVERIFIED')
                for level in item['levels']:
                    for solver in ('ng_run', 'reference_run'):
                        self.assertEqual(level[solver]['status'], 'NOT_RUN')
                        self.assertIsNone(level[solver]['exit_code'])
            self.assertEqual(len(report['files']), 90)
            for name, digest in report['files'].items():
                self.assertEqual(hashlib.sha256((out / name).read_bytes()).hexdigest(), digest)

    def test_cartesian_si_inputs_and_two_scales_do_not_become_axisymmetric(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); out = root / 'out' / 'prepared'
            report = prepare(out, project_root=root)
            grouped = {}
            for item in report['cases']:
                grouped.setdefault(tuple([item['polarization'], *item['analytic_label']]), []).append(item)
                for level in item['levels']:
                    folder = out / level['path']
                    case = PlanarCase.load(folder / 'ng-case.json')
                    self.assertEqual(case.normalization_j_per_m, 1)
                    self.assertEqual(case.modes, 4)
                    with self.assertRaises(ValueError):
                        Case.from_dict(case.to_dict())
                    lines = (folder / 'cavity.af').read_text()
                    self.assertIn('icylin=0, conv=1', lines)
                    self.assertIn(f'x={case.width_m * 100:.12g}, y={case.height_m * 100:.12g}', lines)
                    command = level['ng_run']['expected_command']
                    self.assertTrue((root / command[-3]).is_file())
                    self.assertFalse((root / command[-1]).exists())
            for pair in grouped.values():
                self.assertAlmostEqual(pair[0]['analytic_target_hz'] / pair[1]['analytic_target_hz'], 2)
                first = PlanarCase.load(out / pair[0]['levels'][0]['path'] / 'ng-case.json')
                second = PlanarCase.load(out / pair[1]['levels'][0]['path'] / 'ng-case.json')
                self.assertEqual(second.width_m, first.width_m * 2)
                self.assertEqual(second.height_m, first.height_m * 2)

    def test_existing_output_and_boundary_escape_preserve_user_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); out = root / 'out' / 'prepared'
            prepare(out, project_root=root)
            original = {p.relative_to(out): p.read_bytes() for p in out.rglob('*') if p.is_file()}
            with self.assertRaises(FileExistsError):
                prepare(out, project_root=root)
            for path, contents in original.items():
                self.assertEqual((out / path).read_bytes(), contents)
            for bad in (root / 'outside', root / 'out', root / 'out' / '..' / 'escaped'):
                with self.subTest(path=bad), self.assertRaisesRegex(ValueError, 'subdirectory'):
                    prepare(bad, project_root=root)
            self.assertFalse((root / 'outside').exists())
            self.assertFalse((root / 'escaped').exists())

    def test_unsupported_case_static_mode_and_invalid_controls_rejected(self):
        case = PlanarCase(.31, .2, 'tm')
        for bad_case in (Case(((0., .1), (.2, .1))), case.to_dict()):
            with self.assertRaisesRegex(ValueError, 'Cartesian rectangle'):
                candidate_inputs(bad_case, (1, 1), .1, 1e9)
        for indices in ((0, 0), (1, 0), (-1, 1), (True, 1)):
            with self.subTest(indices=indices), self.assertRaises(ValueError):
                candidate_inputs(case, indices, .1, 1e9)
        for dx, freq in ((0, 1e9), (float('nan'), 1e9), (.1, float('inf'))):
            with self.assertRaises(ValueError):
                candidate_inputs(case, (1, 1), dx, freq)

    def test_cli_requires_explicit_preparation_and_never_starts_legacy(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / 'must-not-exist'
            for flags in (['--planar'], ['--prepare-only'], ['--planar', '--prepare-only', '--run-legacy']):
                result = subprocess.run([sys.executable, str(ROOT / 'scripts/compare_superfish.py'),
                    '--out', str(out), *flags], capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn('UNVERIFIED', result.stderr)
                self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
