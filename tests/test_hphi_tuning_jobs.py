# SPDX-License-Identifier: Apache-2.0
"""Process-boundary and ownership checks for Hphi tuning workers."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import time
import unittest

from superfish_ng.constants import C0
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_tuning_saved import read_hphi_tune
from superfish_ng.hphi_tracking import HphiTrackingControls
from superfish_ng.coaxial import CoaxialCase
from superfish_ng.jobs import JobManager, read_job


def request(*, modes=2, nr=2, nz=4):
    return dict(
        format="superfish_ng_hphi_tune",
        schema_version=1,
        project=HphiProject(
            CoaxialCase(0.01, 0.02, 0.04, nr=nr, nz=nz, modes=modes)
        ).to_dict(),
        parameter="uniform_scale",
        mapping=dict(kind="uniform_scale"),
        bounds=[1.0, 2.0],
        target_hz=C0 / (2 * 0.04 * 1.5),
        frequency_tolerance_hz=1.0e6,
        parameter_tolerance=1.0e-6,
        max_trials=20,
        initial_ids=["fundamental"],
        mode_id="fundamental",
        controls=HphiTrackingControls().to_dict(),
        refinement_levels=1,
        max_triangles=10000,
        max_dofs=10000,
        mesh_frequency_tolerance_hz=1.0e6,
    )


class HphiTuningJobTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.manager = JobManager(self.root)
        self.addCleanup(self.manager.close)
        self.request = request()

    def wait(self, identifier, timeout=60):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            state = self.manager.status(identifier)
            if state["status"] not in ("queued", "running"):
                self.manager.processes[identifier].wait(timeout=10)
                return self.manager.status(identifier, verify=True)
            time.sleep(0.025)
        self.fail("Hphi tune worker did not finish within the test timeout")

    def test_real_worker_pause_resume_and_manager_restart(self):
        first = self.manager.start_hphi_tune(self.request, max_new_trials=1)
        state = self.wait(first)
        self.assertEqual(state["status"], "complete")
        self.assertEqual(state["kind"], "hphi_tune")
        self.assertEqual(state["tuning_status"], "PAUSED")
        self.assertEqual(state["computed_trials"], 1)
        checkpoint = read_hphi_tune(self.root / first / "execution/checkpoint-001.json")
        second = self.manager.start_hphi_tune(
            self.request, checkpoint=checkpoint, max_new_trials=1
        )
        state = self.wait(second)
        self.assertEqual(state["tuning_status"], "PAUSED")
        self.assertEqual(state["computed_trials"], 2)
        result = read_hphi_tune(self.root / second / "hphi-tune-results.json")
        self.assertEqual(len(result["trial_runs"]), 2)
        self.assertTrue((self.root / second / "execution/trial-001").is_dir())
        self.manager.close()
        self.manager = JobManager(self.root)
        self.addCleanup(self.manager.close)
        self.assertEqual(self.manager.status(second, verify=True)["tuning_status"], "PAUSED")

    def test_invalid_submission_allocates_no_job(self):
        invalid = deepcopy(self.request)
        invalid["parameter"] = "stored_energy_j"
        with self.assertRaises(ValueError):
            self.manager.start_hphi_tune(invalid)
        self.assertEqual(self.manager.list(), [])

    def test_real_worker_cancel_preserves_checkpoint_for_new_job(self):
        # Obtain a measured first frequency so the second process is forced
        # past its first checkpoint and remains cancellable during bisection.
        first = self.manager.start_hphi_tune(self.request, max_new_trials=1)
        state = self.wait(first)
        frequency = read_hphi_tune(
            self.root / first / "execution/checkpoint-001.json"
        )["trials"][0]["frequency_hz"]
        running_request = deepcopy(self.request)
        running_request.update(
            target_hz=frequency * 0.75,
            frequency_tolerance_hz=1.0,
            parameter_tolerance=1.0e-15,
            max_trials=60,
        )
        identifier = self.manager.start_hphi_tune(running_request)
        checkpoint_path = self.root / identifier / "execution/checkpoint-001.json"
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline and not checkpoint_path.is_file():
            time.sleep(0.025)
        self.assertTrue(checkpoint_path.is_file())
        self.assertEqual(self.manager.cancel(identifier)["status"], "cancelled")
        checkpoint = read_hphi_tune(checkpoint_path)
        self.assertEqual(checkpoint["status"], "PAUSED")
        resumed = self.manager.start_hphi_tune(
            running_request, checkpoint=checkpoint, max_new_trials=1
        )
        self.assertEqual(self.wait(resumed)["tuning_status"], "PAUSED")
        self.assertFalse((self.root / resumed / "manifest.json").is_symlink())

    def test_prepared_worker_failure_keeps_checkpoint_without_manifest(self):
        from unittest.mock import patch
        from superfish_ng.hphi_tuning_jobs import (
            INPUT,
            execute_prepared_hphi_tune,
        )

        directory = self.root / "prepared"
        directory.mkdir()
        input_path = directory / INPUT
        input_path.write_text(
            json.dumps(dict(request=self.request, max_new_trials=1, checkpoint=None)),
            encoding="utf-8",
        )
        (directory / "job.json").write_text(
            json.dumps(dict(status="queued", kind="hphi_tune", input_sha256={INPUT: ""})),
            encoding="utf-8",
        )
        from superfish_ng.jobs import _digest
        state_path = directory / "job.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["input_sha256"] = {INPUT: _digest(input_path)}
        state_path.write_text(json.dumps(state), encoding="utf-8")

        def fail(request_data, output, **kwargs):
            from superfish_ng.hphi_tuning_saved import execute_hphi_tune
            execute_hphi_tune(request_data, output, max_new_trials=1)
            raise RuntimeError("injected Hphi worker failure")

        with patch("superfish_ng.hphi_tuning_jobs.execute_hphi_tune", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "injected Hphi worker failure"):
                execute_prepared_hphi_tune(directory)
        self.assertEqual(read_job(directory)["status"], "failed")
        self.assertEqual(
            read_hphi_tune(directory / "execution/checkpoint-001.json")["status"],
            "PAUSED",
        )
        self.assertFalse((directory / "manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
