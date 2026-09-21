# SPDX-License-Identifier: Apache-2.0
"""Process-boundary and ownership checks for Hphi tuning workers."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import time
import unittest

from superfish_ng.material_hphi_tuning_saved import read_material_hphi_tune
from superfish_ng.jobs import JobManager, read_job


from test_material_hphi_tuning_saved import request


class MaterialHphiTuningJobTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.manager = JobManager(self.root)
        self.addCleanup(self.manager.close)
        self.request = request()

    def wait(self, identifier, timeout=180):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            state = self.manager.status(identifier)
            if state["status"] not in ("queued", "running"):
                self.manager.processes[identifier].wait(timeout=10)
                return self.manager.status(identifier, verify=True)
            time.sleep(0.025)
        self.fail("Hphi tune worker did not finish within the test timeout")

    def test_real_worker_pause_resume_and_manager_restart(self):
        first = self.manager.start_material_hphi_tune(self.request, max_new_trials=1)
        state = self.wait(first)
        self.assertEqual(state["status"], "complete")
        self.assertEqual(state["kind"], "material_hphi_tune")
        self.assertEqual(state["tuning_status"], "PAUSED")
        self.assertEqual(state["computed_trials"], 1)
        checkpoint = read_material_hphi_tune(self.root / first / "execution/checkpoint-001.json")
        second = self.manager.start_material_hphi_tune(
            self.request, checkpoint=checkpoint, max_new_trials=1
        )
        state = self.wait(second)
        self.assertEqual(state["tuning_status"], "PAUSED")
        self.assertEqual(state["computed_trials"], 2)
        result = read_material_hphi_tune(self.root / second / "material-hphi-tune-results.json")
        self.assertEqual(len(result["trial_runs"]), 2)
        self.assertTrue((self.root / second / "execution/trial-001").is_dir())
        self.manager.close()
        # The resumed worker owns the whole prefix. Its original job may be
        # archived after completion without invalidating the new job.
        (self.root / first).rename(self.root / "original-moved")
        self.manager = JobManager(self.root)
        self.addCleanup(self.manager.close)
        self.assertEqual(read_material_hphi_tune(self.root / second / "material-hphi-tune-results.json"), result)
        self.assertEqual(self.manager.status(second, verify=True)["tuning_status"], "PAUSED")

        from superfish_ng.material_hphi_tuning_jobs import INPUT, _owned_input
        directory = self.root / second
        input_path = directory / INPUT
        original_input = input_path.read_bytes()
        submitted = json.loads(original_input)
        before = deepcopy(submitted)
        owned = _owned_input(submitted, directory / "execution")
        self.assertEqual(submitted, before)
        self.assertEqual(input_path.read_bytes(), original_input)
        self.assertEqual(owned["checkpoint"]["trial_runs"], result["trial_runs"][:1])
        for field in ("hash", "frequency", "decision", "path", "request"):
            changed = deepcopy(submitted)
            checkpoint = changed["checkpoint"]
            if field == "hash":
                checkpoint["trial_sources_sha256"][0]["project.json"] = "0" * 64
            elif field == "frequency":
                checkpoint["trials"][0]["frequency_hz"] += 1
            elif field == "decision":
                checkpoint["decision"]["next_trial"]["parent_index"] = 1
            elif field == "path":
                checkpoint["trial_runs"][0] = "trial-001"
            else:
                checkpoint["request"]["target_hz"] += 1
            with self.subTest(tampering=field), self.assertRaises(ValueError):
                _owned_input(changed, directory / "execution")

        # Native copies must still match the submitted hashes; a missing copy
        # or a link to the original must never be accepted as owned evidence.
        project_path = directory / "execution/trial-001/project.json"
        original_project = project_path.read_bytes()
        project_path.write_bytes(original_project + b"\n")
        try:
            with self.assertRaises(ValueError):
                _owned_input(submitted, directory / "execution")
        finally:
            project_path.write_bytes(original_project)
        trial = directory / "execution/trial-001"
        backup = directory / "execution/trial-backup"
        trial.rename(backup)
        try:
            with self.assertRaises(ValueError):
                _owned_input(submitted, directory / "execution")
            trial.symlink_to(self.root / "original-moved/execution/trial-001", target_is_directory=True)
            with self.assertRaises(ValueError):
                _owned_input(submitted, directory / "execution")
        finally:
            if trial.is_symlink():
                trial.unlink()
            backup.rename(trial)

    def test_invalid_submission_allocates_no_job(self):
        invalid = deepcopy(self.request)
        invalid["parameter"] = "stored_energy_j"
        with self.assertRaises(ValueError):
            self.manager.start_material_hphi_tune(invalid)
        self.assertEqual(self.manager.list(), [])

    def test_whole_worker_move_and_completion_manifest_tampering(self):
        identifier=self.manager.start_material_hphi_tune(self.request,max_new_trials=1)
        self.assertEqual(self.wait(identifier)['status'],'complete')
        self.manager.close()
        directory=self.root/identifier;relocated=self.root/'relocated';directory.rename(relocated)
        self.assertEqual(read_job(relocated)['tuning_status'],'PAUSED')
        manifest_path=relocated/'manifest.json';original=manifest_path.read_bytes()
        manifest=json.loads(original)
        manifest['files'].pop('execution/checkpoint-000.json')
        manifest_path.write_text(json.dumps(manifest))
        try:
            with self.assertRaises(ValueError):read_job(relocated)
        finally:manifest_path.write_bytes(original)
        prefix=relocated/'execution/checkpoint-000.json';before=prefix.read_bytes()
        bad=json.loads(before);bad['decision']['status']='TUNED';prefix.write_text(json.dumps(bad))
        # Even rehashing the changed prefix cannot replace physical replay.
        from superfish_ng.jobs import _digest
        manifest=json.loads(original);manifest['files']['execution/checkpoint-000.json']=_digest(prefix)
        manifest_path.write_text(json.dumps(manifest))
        try:
            with self.assertRaises(ValueError):read_job(relocated)
        finally:prefix.write_bytes(before);manifest_path.write_bytes(original)
        prefix.unlink()
        manifest=json.loads(original);manifest['files'].pop('execution/checkpoint-000.json')
        manifest_path.write_text(json.dumps(manifest))
        try:
            with self.assertRaises(ValueError):read_job(relocated)
        finally:prefix.write_bytes(before);manifest_path.write_bytes(original)

    def test_real_worker_cancel_preserves_checkpoint_for_new_job(self):
        # Obtain a measured first frequency so the second process is forced
        # past its first checkpoint and remains cancellable during bisection.
        first = self.manager.start_material_hphi_tune(self.request, max_new_trials=1)
        state = self.wait(first)
        frequency = read_material_hphi_tune(
            self.root / first / "execution/checkpoint-001.json"
        )["trials"][0]["frequency_hz"]
        running_request = deepcopy(self.request)
        running_request.update(
            target_hz=frequency / 1.0625,
            frequency_tolerance_hz=1.0,
            parameter_tolerance=1.0e-15,
            max_trials=60,
        )
        identifier = self.manager.start_material_hphi_tune(running_request)
        checkpoint_path = self.root / identifier / "execution/checkpoint-001.json"
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline and not checkpoint_path.is_file():
            time.sleep(0.025)
        self.assertTrue(checkpoint_path.is_file())
        self.assertEqual(self.manager.cancel(identifier)["status"], "cancelled")
        checkpoint = read_material_hphi_tune(checkpoint_path)
        self.assertEqual(checkpoint["status"], "PAUSED")
        resumed = self.manager.start_material_hphi_tune(
            running_request, checkpoint=checkpoint, max_new_trials=1
        )
        self.assertEqual(self.wait(resumed)["tuning_status"], "PAUSED")
        self.assertFalse((self.root / resumed / "manifest.json").is_symlink())

    def test_prepared_worker_failure_keeps_checkpoint_without_manifest(self):
        from unittest.mock import patch
        from superfish_ng.material_hphi_tuning_jobs import (
            INPUT,
            execute_prepared_material_hphi_tune,
        )

        directory = self.root / "prepared"
        directory.mkdir()
        input_path = directory / INPUT
        input_path.write_text(
            json.dumps(dict(request=self.request, max_new_trials=1, checkpoint=None)),
            encoding="utf-8",
        )
        (directory / "job.json").write_text(
            json.dumps(dict(status="queued", kind="material_hphi_tune", input_sha256={INPUT: ""})),
            encoding="utf-8",
        )
        from superfish_ng.jobs import _digest
        state_path = directory / "job.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["input_sha256"] = {INPUT: _digest(input_path)}
        state_path.write_text(json.dumps(state), encoding="utf-8")

        def fail(request_data, output, **kwargs):
            from superfish_ng.material_hphi_tuning_saved import execute_material_hphi_tune
            execute_material_hphi_tune(request_data, output, max_new_trials=1)
            raise RuntimeError("injected Hphi worker failure")

        with patch("superfish_ng.material_hphi_tuning_jobs.execute_material_hphi_tune", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "injected Hphi worker failure"):
                execute_prepared_material_hphi_tune(directory)
        self.assertEqual(read_job(directory)["status"], "failed")
        self.assertEqual(
            read_material_hphi_tune(directory / "execution/checkpoint-001.json")["status"],
            "PAUSED",
        )
        self.assertFalse((directory / "manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
