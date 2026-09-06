# SPDX-License-Identifier: Apache-2.0
import tempfile
import unittest
from pathlib import Path
import numpy as np
from superfish_ng.config import Case
from superfish_ng.solver import solve
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution, analyze_band


class SavedTests(unittest.TestCase):
    def test_saved_field_consistency_and_corrupt_axis_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "run"
            case = Case(((0, 0.06), (0.09, 0.06)), nr=8, nz=10, modes=2)
            save_run(case, solve(case), path)
            self.assertEqual(read_solution(path).case, case)
            axis = np.loadtxt(path / "axis_001.csv", delimiter=",", skiprows=1)
            axis[:, 1] *= 2
            np.savetxt(
                path / "axis_001.csv", axis, delimiter=",", header="z,ez", comments=""
            )
            with self.assertRaisesRegex(ValueError, "disagree"):
                read_solution(path)

    def test_full_end_and_nonperiodic_geometry_do_not_receive_phase_labels(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "run"
            case = Case(((0, 0.06), (0.04, 0.08), (0.1, 0.04)), nr=8, nz=10, modes=3)
            save_run(case, solve(case), path)
            with self.assertRaisesRegex(ValueError, "end planes"):
                analyze_band(path, [0.01, 0.05, 0.09])
            with self.assertRaisesRegex(ValueError, "nonperiodic"):
                analyze_band(path, [0, 0.05, 0.1])

    def test_probe_preserves_axis_and_physical_b_relation(self):
        from superfish_ng.saved import export_radial_probe
        from superfish_ng.constants import MU0

        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "run"
            case = Case(((0, 0.06), (0.09, 0.06)), nr=12, nz=18, modes=1)
            save_run(case, solve(case), path)
            output = Path(root) / "radial.csv"
            export_radial_probe(path, output, 0.03)
            values = np.loadtxt(output, delimiter=",", skiprows=1)
            self.assertEqual(values.shape, (401, 6))
            self.assertEqual(values[0, 2], 0)
            np.testing.assert_allclose(
                values[:, 5], MU0 * values[:, 4], rtol=1e-14, atol=0
            )
            axis = np.loadtxt(path / "axis_001.csv", delimiter=",", skiprows=1)
            self.assertAlmostEqual(
                values[0, 3] / np.interp(0.03, axis[:, 0], axis[:, 1]), 1, places=12
            )
            with self.assertRaises(FileExistsError):
                export_radial_probe(path, output, 0.03)
            with self.assertRaises(ValueError):
                export_radial_probe(path, Path(root) / "bad.csv", -0.01)
            self.assertFalse((Path(root) / "bad.csv").exists())

    def test_short_cylinder_labels_follow_fields_not_requested_mode_number(self):
        from superfish_ng.saved import compare_pillbox

        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "run"
            case = Case(((0, 0.075), (0.04, 0.075)), nr=32, nz=40, modes=3)
            save_run(case, solve(case), path)
            reference = compare_pillbox(path)
            self.assertEqual(
                [m["label"] for m in reference["modes"]], ["TM010", "TM020", "TM011"]
            )
