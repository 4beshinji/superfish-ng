# SPDX-License-Identifier: Apache-2.0
"""GUI transport checks for the owned Hphi tuning workflow."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

from superfish_ng.gui_hphi import hphi_response
from superfish_ng.jobs import JobManager
from test_hphi_tuning_jobs import request


class HphiTuningGuiTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.manager = JobManager(self.root / "jobs")
        self.addCleanup(self.manager.close)
        self.lock = threading.Lock()
        self.raw = request()

    def call(self, action, **data):
        return hphi_response(
            self.manager, action, data, self.lock, self.root / "cache"
        )[0]

    def wait(self, identifier, timeout=60):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            state = self.manager.status(identifier)
            if state["status"] not in ("queued", "running"):
                self.manager.processes[identifier].wait(timeout=10)
                return self.manager.status(identifier, verify=True)
            time.sleep(0.025)
        self.fail("Hphi tune worker did not finish within the test timeout")

    def test_normalize_checkpoint_resume_and_target_field_import(self):
        self.assertEqual(
            self.call("hphi-normalize-tune", request=json.dumps(self.raw)), self.raw
        )
        first = self.call(
            "hphi-start-tune", request=self.raw, max_new_trials=1
        )["id"]
        self.wait(first)
        result = self.call("hphi-tune-result", id=first)
        self.assertEqual(result["document"]["status"], "PAUSED")
        self.assertEqual(
            self.call("hphi-tune-checkpoints", id=first)["indices"], [1]
        )
        checkpoint = self.call("hphi-open-tune-checkpoint", id=first, index=1)
        self.assertEqual(len(checkpoint["document"]["trials"]), 1)
        imported = self.call(
            "hphi-tune-trial", document=checkpoint["serialized"], index=1
        )
        self.assertEqual(imported["mode"], 1)
        resumed = self.call(
            "hphi-resume-tune",
            document=checkpoint["serialized"],
            max_new_trials=1,
        )["id"]
        self.wait(resumed)
        final = self.call("hphi-tune-result", id=resumed)
        self.assertEqual(final["document"]["status"], "PAUSED")
        self.assertEqual(
            self.call("hphi-replay-tune", document=final["serialized"]), final
        )
        indices = self.call("hphi-tune-checkpoints", id=resumed)["indices"]
        self.assertEqual(indices, [1, 2])
        for index in indices:
            with self.subTest(checkpoint=index):
                opened = self.call("hphi-open-tune-checkpoint", id=resumed, index=index)
                for key in ("trial_runs", "trial_sources_sha256", "trials"):
                    self.assertEqual(opened["document"][key], final["document"][key][:index])
        self.assertNotEqual(
            checkpoint["document"]["trial_runs"], final["document"]["trial_runs"][:1]
        )
        for key in ("trial_sources_sha256", "trials"):
            self.assertEqual(checkpoint["document"][key], final["document"][key][:1])
        source = self.manager.directory(first)
        moved = self.root / "original-moved"
        source.rename(moved)
        try:
            self.assertEqual(self.call("hphi-tune-result", id=resumed), final)
            for index in indices:
                with self.subTest(moved_source_checkpoint=index):
                    opened = self.call("hphi-open-tune-checkpoint", id=resumed, index=index)
                    self.assertEqual(opened["document"]["trials"], final["document"]["trials"][:index])
        finally:
            moved.rename(source)

    def test_strict_transport_and_foreign_checkpoint_rejection(self):
        with self.assertRaises(ValueError):
            self.call("hphi-normalize-tune", request={**self.raw, "extra": 1})
        with self.assertRaises(ValueError):
            self.call("hphi-start-tune", request=self.raw, max_new_trials=True)
        first = self.call(
            "hphi-start-tune", request=self.raw, max_new_trials=1
        )["id"]
        self.wait(first)
        second = self.call(
            "hphi-start-tune", request=self.raw, max_new_trials=1
        )["id"]
        self.wait(second)
        source = self.manager.directory(first) / "execution/checkpoint-001.json"
        target = self.manager.directory(second) / "execution/checkpoint-001.json"
        original = target.read_bytes()
        target.write_bytes(source.read_bytes())
        with self.assertRaisesRegex(ValueError, "another Hphi tune job"):
            self.call("hphi-open-tune-checkpoint", id=second, index=1)
        target.write_bytes(original)
        changed = deepcopy(self.call("hphi-open-tune-checkpoint", id=first, index=1))
        changed["document"]["trials"][0]["frequency_hz"] = 1.0
        with self.assertRaises(ValueError):
            self.call("hphi-replay-tune", document=changed["document"])


if __name__ == "__main__":
    unittest.main()
