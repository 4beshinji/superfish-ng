# SPDX-License-Identifier: Apache-2.0
import tempfile
import unittest
from pathlib import Path
from superfish_ng.project import Project
from superfish_ng.studies import Study, execute_study


def base():
    return Project.from_dict(
        {
            "schema_version": 1,
            "geometry": {"type": "pillbox", "radius_m": 0.06, "length_m": 0.08},
            "mesh": {"nr": 10, "nz": 12},
            "solver": {"modes": 2},
        }
    )


class StudyTests(unittest.TestCase):
    def test_pillbox_length_sweep_obeys_independent_tm010_invariant(self):
        project = base().to_dict()
        project["case"]["mesh"] = {"nr": 64, "nz": 96}
        study = Study(
            Project.from_dict(project),
            "sweep",
            "/case/geometry/points_zr_m/1/0",
            [0.04, 0.08, 0.12],
        )
        with tempfile.TemporaryDirectory() as root:
            report = execute_study(study, Path(root) / "study")
            frequencies = [p["modes"][0]["frequency_hz"] for p in report["points"]]
            self.assertLess(max(frequencies) / min(frequencies) - 1, 1e-9)
            self.assertEqual(
                report["mode_tracking"], "not performed; independent spectra"
            )
            self.assertEqual(len(report["points"]), 3)

    def test_refinement_contract_and_serialization(self):
        s = Study(base(), "mesh_convergence", "mesh_scale", [1, 2])
        self.assertEqual(Study.from_dict(s.to_dict()).to_dict(), s.to_dict())
        self.assertEqual([p.case.nr for p in s.projects()], [10, 20])
        self.assertEqual([p.case.nz for p in s.projects()], [12, 24])
        with self.assertRaises(ValueError):
            Study(base(), "mesh_convergence", "/case/rf/beta", [0.8, 1])
        with self.assertRaises(ValueError):
            Study(base(), "mesh_convergence", "mesh_scale", [2, 1])
        with self.assertRaises(ValueError):
            Study(base(), "sweep", "/case/unsupported", [1, 2]).projects()

    def test_convergence_separates_field_frequency_and_rf(self):
        with tempfile.TemporaryDirectory() as root:
            r = execute_study(
                Study(base(), "mesh_convergence", "mesh_scale", [1, 2]),
                Path(root) / "study",
            )
            self.assertEqual(len(r["comparisons"]), 1)
            c = r["comparisons"][0]
            self.assertIn(c["status"], ["PASS", "FAIL", "UNVERIFIED"])
            self.assertEqual(
                c["pairing"], "same geometry; sampled magnetic-field overlap"
            )
            self.assertIn("frequency", c["modes"][0]["gates"])
            self.assertIn("axis_field", c["modes"][0]["gates"])
            self.assertIn("rf", c["modes"][0]["gates"])
            self.assertEqual(
                c["surface_field"], "not certified; P1 peak estimates retained"
            )
