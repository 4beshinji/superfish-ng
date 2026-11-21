# SPDX-License-Identifier: Apache-2.0
"""Replay reuse must preserve native ownership and every prefix decision."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from superfish_ng import curved_hphi_tuning_jobs as jobs
from superfish_ng import curved_hphi_tuning_saved as saved
from superfish_ng import curved_hphi_tuning_prefix_replay as prefix
from superfish_ng import owned_tuning_worker as worker
from superfish_ng.jobs import JobManager
from support.curved_hphi_tuning_fixtures import curved_tune_request


class CurvedHphiPrefixReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.manager = JobManager(cls.root)
        try:
            identifier = cls.manager.start_curved_hphi_tune(curved_tune_request(), max_new_trials=2)
            process = cls.manager.processes[identifier]
            if process.wait(timeout=180) != 0:
                raise AssertionError('real fixture worker failed')
            cls.directory = cls.root / identifier
            cls.result_path = cls.directory / jobs.RESULT
            cls.state = json.loads((cls.directory / 'job.json').read_text())
            cls.manifest = json.loads((cls.directory / 'manifest.json').read_text())
            cls.expected = saved.read_curved_hphi_tune(cls.result_path)
            cls.first_path = cls.directory / 'execution/checkpoint-001.json'
            cls.first = json.loads(cls.first_path.read_text())
        except BaseException:
            cls.manager.close()
            cls.temporary.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        cls.manager.close()
        cls.temporary.cleanup()

    def setUp(self):
        self.before = self.fingerprints()
        self.addCleanup(lambda: self.assertEqual(self.fingerprints(), self.before))
        prohibition = patch.object(saved, 'solve_curved_hphi', side_effect=AssertionError('replay solved a new trial'))
        prohibition.start()
        self.addCleanup(prohibition.stop)

    def fingerprints(self):
        return {str(p.relative_to(self.directory)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.directory.rglob('*') if p.is_file()}

    def current(self):
        return jobs.verify_curved_hphi_tune_job(self.directory, self.state,
                                               json.loads((self.directory / 'manifest.json').read_text()))

    def original(self):
        return worker.verify_tuning_worker(
            self.directory, self.state, json.loads((self.directory / 'manifest.json').read_text()),
            contract=jobs._contract(), validate_owned_submission=jobs._owned_input,
            read_result=jobs.read_curved_hphi_tune, snapshot_trial=jobs._snapshot_trial,
            validate_checkpoints=jobs._verify_checkpoint_files)

    @contextmanager
    def changed_file(self, path, raw):
        original = path.read_bytes()
        try:
            path.write_bytes(raw)
            yield
        finally:
            path.write_bytes(original)

    def test_complete_worker_reuses_only_its_fresh_full_replay(self):
        with patch.object(saved, '_recompute', wraps=saved._recompute) as original_calls:
            old = self.original()
        with patch.object(saved, '_recompute', wraps=saved._recompute) as current_calls:
            new = self.current()
        self.assertEqual(old, self.expected)
        self.assertEqual(new, old)
        self.assertEqual([len(call.args[1]) for call in original_calls.call_args_list], [2, 0, 1, 2])
        self.assertEqual([len(call.args[1]) for call in current_calls.call_args_list], [2])
        with patch.object(saved, '_recompute', wraps=saved._recompute) as repeated:
            self.assertEqual(self.current(), old)
            self.assertEqual(self.current(), old)
        self.assertEqual([len(call.args[1]) for call in repeated.call_args_list], [2, 2])

    def test_rehashed_prefix_changes_cannot_replace_native_replay(self):
        for field in ('frequency', 'parent', 'request', 'source_hash', 'status', 'format'):
            document = deepcopy(self.first)
            if field == 'frequency':
                document['trials'][0]['frequency_hz'] += 1
            elif field == 'parent':
                document['trials'][0]['parent_index'] = 1
            elif field == 'request':
                document['request']['target_hz'] += 1
            elif field == 'source_hash':
                document['trial_sources_sha256'][0]['project.json'] = '0' * 64
            elif field == 'status':
                document['decision']['status'] = document['status'] = 'TUNED'
                document['can_resume'] = False
            else:
                document['format'] = 'superfish_ng_hphi_tune_checkpoint'
            raw = json.dumps(document).encode()
            manifest = deepcopy(self.manifest)
            manifest['files']['execution/checkpoint-001.json'] = hashlib.sha256(raw).hexdigest()
            with self.subTest(field=field), self.changed_file(self.first_path, raw), self.changed_file(
                    self.directory / 'manifest.json', json.dumps(manifest).encode()):
                with self.assertRaises(ValueError):
                    self.original()
                with self.assertRaises(ValueError):
                    self.current()

    def test_native_byte_change_invalidates_even_an_active_verified_context(self):
        context = prefix._VerifiedCurvedTuningPrefixes(self.directory, jobs.RESULT)
        with context:
            context.read_result(self.result_path)
            fields = Path(self.expected['trial_runs'][0]) / 'solution/fields.npz'
            with self.changed_file(fields, fields.read_bytes() + b'changed'):
                with self.assertRaisesRegex(ValueError, 'changed'):
                    context.replay_prefix(self.first, base_directory=self.directory / 'execution')
            with self.assertRaisesRegex(RuntimeError, 'completed native replay'):
                context.replay_prefix(self.first, base_directory=self.directory / 'execution')
            context.read_result(self.result_path)
            self.assertEqual(context.replay_prefix(self.first, base_directory=self.directory / 'execution'),
                             saved.read_curved_hphi_tune(self.first_path))

    def test_failed_fresh_read_and_context_end_drop_verified_state(self):
        context = prefix._VerifiedCurvedTuningPrefixes(self.directory, jobs.RESULT)
        with context:
            with self.assertRaisesRegex(RuntimeError, 'completed native replay'):
                context.replay_prefix(self.first, base_directory=self.directory / 'execution')
            context.read_result(self.result_path)
            with self.assertRaises(ValueError):
                context.read_result(self.directory / 'other-result.json')
            with self.assertRaisesRegex(RuntimeError, 'completed native replay'):
                context.replay_prefix(self.first, base_directory=self.directory / 'execution')
            context.read_result(self.result_path)
        with self.assertRaisesRegex(RuntimeError, 'active worker verification'):
            context.replay_prefix(self.first, base_directory=self.directory / 'execution')
        with context:
            with self.assertRaisesRegex(RuntimeError, 'completed native replay'):
                context.replay_prefix(self.first, base_directory=self.directory / 'execution')

    def test_owned_request_change_invalidates_the_verified_prefix(self):
        context = prefix._VerifiedCurvedTuningPrefixes(self.directory, jobs.RESULT)
        with context:
            context.read_result(self.result_path)
            request_path = self.directory / 'execution/request.json'
            request = json.loads(request_path.read_text())
            request['target_hz'] += 1
            with self.changed_file(request_path, json.dumps(request).encode()):
                with self.assertRaises(ValueError):
                    context.replay_prefix(self.first, base_directory=self.directory / 'execution')
            with self.assertRaises(RuntimeError):
                context.replay_prefix(self.first, base_directory=self.directory / 'execution')

    def test_implementation_change_rejects_context_and_clears_it(self):
        context = prefix._VerifiedCurvedTuningPrefixes(self.directory, jobs.RESULT)
        with patch.object(prefix, '_implementation_hashes', side_effect=[{'own.py': '0' * 64}, {'own.py': '1' * 64}]):
            with self.assertRaisesRegex(RuntimeError, 'implementation changed'):
                with context:
                    context.read_result(self.result_path)
                    context.replay_prefix(self.first, base_directory=self.directory / 'execution')
        with self.assertRaisesRegex(RuntimeError, 'active worker verification'):
            context.read_result(self.result_path)


if __name__ == '__main__':
    unittest.main()
