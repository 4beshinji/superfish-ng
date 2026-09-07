# SPDX-License-Identifier: Apache-2.0
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from superfish_ng.project import Project
from superfish_ng.jobs import execute_project, read_job, JobManager


def project(n=8):
    return Project.from_dict(
        {
            "schema_version": 1,
            "geometry": {"type": "pillbox", "radius_m": 0.06, "length_m": 0.09},
            "mesh": {"nr": n, "nz": n},
            "solver": {"modes": 2},
        }
    )


class JobTests(unittest.TestCase):
    def test_complete_manifest_detects_missing_output_and_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            out = Path(root) / "run"
            execute_project(project(), out)
            self.assertEqual(read_job(out)["status"], "complete")
            with self.assertRaises(FileExistsError):
                execute_project(project(), out)
            (out / "solution" / "fields.npz").unlink()
            with self.assertRaisesRegex(ValueError, "missing|integrity"):
                read_job(out)

    def test_save_failure_never_completes(self):
        with tempfile.TemporaryDirectory() as root:
            out = Path(root) / "run"
            with patch(
                "superfish_ng.jobs.save_run", side_effect=OSError("disk failure")
            ):
                with self.assertRaises(OSError):
                    execute_project(project(), out)
            state = read_job(out)
            self.assertEqual(state["status"], "failed")
            self.assertIn("disk failure", state["error"])
            self.assertFalse((out / "manifest.json").exists())

    def test_background_cancel_and_retry(self):
        with tempfile.TemporaryDirectory() as root:
            manager = JobManager(root)
            first = manager.start(project(300))
            manager.cancel(first)
            self.assertEqual(manager.status(first)["status"], "cancelled")
            second = manager.start(project())
            deadline = time.monotonic() + 15
            while (
                manager.status(second)["status"] in ("queued", "running")
                and time.monotonic() < deadline
            ):
                time.sleep(0.05)
            self.assertEqual(manager.status(second)["status"], "complete")
            self.assertNotEqual(first, second)
            manager.close()

    def test_abandoned_running_is_not_success(self):
        with tempfile.TemporaryDirectory() as root:
            out = Path(root) / "abandoned"
            out.mkdir()
            (out / "job.json").write_text(json.dumps({"status": "running"}))
            manager = JobManager(root)
            self.assertEqual(manager.status("abandoned")["status"], "interrupted")
            manager.close()

    def test_history_uses_creation_time_not_random_id_order(self):
        with tempfile.TemporaryDirectory() as root:
            for suffix, created in (("ffff", 1.0), ("0000", 1.1)):
                directory = Path(root) / f"20260906-120000-{suffix}"
                directory.mkdir()
                (directory / "job.json").write_text(
                    json.dumps({"status": "cancelled", "created_unix": created})
                )
            manager = JobManager(root)
            self.assertEqual(
                [item["id"] for item in manager.list()],
                ["20260906-120000-0000", "20260906-120000-ffff"],
            )
            manager.close()

    def test_legacy_import_checks_files_without_a_new_solve(self):
        from superfish_ng.io import save_run
        from superfish_ng.solver import solve

        with tempfile.TemporaryDirectory() as root:
            source = Path(root) / "legacy"
            case = project().case
            save_run(case, solve(case), source)
            # Exercise a genuinely historical layout, without direct-save markers.
            old_result = json.loads((source / 'results.json').read_text())
            old_result.pop('save_protocol_version')
            (source / 'results.json').write_text(json.dumps(old_result))
            (source / 'save_protocol.json').unlink()
            (source / 'save_complete.json').unlink()
            original = (source / "fields.npz").read_bytes()
            manager = JobManager(Path(root) / "workspace")
            try:
                with patch(
                    "superfish_ng.jobs.solve",
                    side_effect=AssertionError("must not solve"),
                ):
                    identifier = manager.import_result(source)
                state = manager.status(identifier, verify=True)
                self.assertEqual(state["origin"], "imported")
                self.assertIn(
                    "no original completion manifest", state["source_completion"]
                )
                self.assertEqual((source / "fields.npz").read_bytes(), original)
                self.assertEqual(
                    (
                        manager.directory(identifier) / "solution" / "fields.npz"
                    ).read_bytes(),
                    original,
                )
            finally:
                manager.close()

    def test_background_study_finishes_with_verified_manifest(self):
        from superfish_ng.studies import Study

        with tempfile.TemporaryDirectory() as root:
            manager = JobManager(root)
            try:
                identifier = manager.start_study(
                    Study(project(), "mesh_convergence", "mesh_scale", [1, 2])
                )
                deadline = time.monotonic() + 15
                while (
                    manager.status(identifier)["status"] in ("queued", "running")
                    and time.monotonic() < deadline
                ):
                    time.sleep(0.05)
                state = manager.status(identifier, verify=True)
                self.assertEqual(state["status"], "complete")
                self.assertEqual(state["kind"], "study")
            finally:
                manager.close()
