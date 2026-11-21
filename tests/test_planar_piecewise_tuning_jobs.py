# SPDX-License-Identifier: Apache-2.0
"""Queued ownership and real stopped/resumed Cartesian shape-tuning workers."""
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from superfish_ng.constants import C0
from superfish_ng.jobs import JobManager, _digest, read_job
from superfish_ng.planar_tuning import execute_planar_tune, read_planar_tune
from superfish_ng.planar_tuning_jobs import (
    INPUT, RESULT, ANCESTRY, execute_prepared_planar_tune,
    read_planar_tune_job_checkpoint,
)
from superfish_ng.planar_tuning_saved import _snapshot_trial
from test_planar_piecewise_tuning import shape_request, crossing_request, save


class PlanarPiecewiseTuneJobTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.manager = JobManager(self.root/'workspace'); self.addCleanup(self.manager.close)

    def wait(self, identifier):
        process = self.manager.processes[identifier]
        self.assertNotEqual(process.pid, os.getpid())
        self.assertEqual(process.wait(timeout=360), 0,
                         (self.manager.directory(identifier)/'log.txt').read_text())
        return self.manager.status(identifier, verify=True)

    def queue(self, raw, previous, limit=1):
        with patch('superfish_ng.planar_tuning_jobs.subprocess.Popen', return_value=Mock()):
            identifier = self.manager.start_planar_tune(raw, checkpoint=previous, max_new_trials=limit)
        self.manager.processes.pop(identifier)
        return self.manager.directory(identifier)

    def test_queued_ownership_source_move_completion_restart_and_worker_move(self):
        raw = shape_request(nx=4)
        previous = execute_planar_tune(raw, self.root/'source', max_new_trials=1)
        checkpoint_bytes = (self.root/'source/checkpoint-001.json').read_bytes()
        directory = self.queue(raw, previous)
        submitted = json.loads((directory/INPUT).read_text())
        self.assertEqual(submitted['checkpoint'], previous)
        state = read_job(directory, verify=False)
        self.assertEqual(state['input_sha256'][f'{ANCESTRY}/trial-001/project.json'],
                         previous['trial_sources_sha256'][0]['project.json'])
        self.assertEqual(_snapshot_trial(directory/ANCESTRY/'trial-001'), previous['trial_sources_sha256'][0])
        (self.root/'source').rename(self.root/'source-moved')
        result = execute_prepared_planar_tune(directory)
        self.assertEqual(result['status'], 'PAUSED')
        self.assertEqual(result['trials'][:1], previous['trials'])
        self.assertEqual(result['trial_sources_sha256'][:1], previous['trial_sources_sha256'])
        self.assertEqual(checkpoint_bytes, (self.root/'source-moved/checkpoint-001.json').read_bytes())
        self.assertEqual(read_job(directory)['tuning_status'], 'PAUSED')
        self.assertEqual(read_planar_tune_job_checkpoint(directory, 1)['trials'], previous['trials'])
        self.manager.close(); self.manager = JobManager(self.root/'workspace'); self.addCleanup(self.manager.close)
        self.assertEqual(self.manager.status(directory.name, verify=True)['tuning_status'], 'PAUSED')
        self.manager.close()
        target = self.root/'worker-moved'; directory.rename(target)
        self.assertEqual(read_job(target)['tuning_status'], 'PAUSED')
        moved = read_planar_tune(target/RESULT)
        self.assertEqual(moved['trials'], result['trials'])
        self.assertEqual(moved['trial_runs'], [str(target/'execution'/f'trial-{i+1:03d}') for i in range(2)])

    def test_actual_cancel_select_prefix_move_resume_and_manager_restart(self):
        raw = shape_request(nx=4)
        raw.update(target_hz=C0/(2*1.08), frequency_tolerance_hz=1e-5,
                   parameter_tolerance=1e-15, max_trials=60)
        identifier = self.manager.start_planar_tune(raw)
        directory = self.manager.directory(identifier)
        path = directory/'execution/checkpoint-001.json'
        deadline = time.monotonic()+120
        while not path.is_file() and time.monotonic() < deadline:
            self.assertIsNone(self.manager.processes[identifier].poll())
            time.sleep(.01)
        self.assertTrue(path.is_file())
        self.assertIsNone(self.manager.processes[identifier].poll())
        self.assertEqual(self.manager.cancel(identifier)['status'], 'cancelled')
        previous = read_planar_tune_job_checkpoint(directory, 1)
        self.assertEqual(previous['trials'][0]['initial_tracking']['status'], 'PASS')
        self.assertEqual(read_planar_tune(path), previous)
        saved = path.read_bytes()
        resumed = self.manager.start_planar_tune(raw, checkpoint=previous, max_new_trials=1)
        # The cancelled process is already reaped; stop tracking its old
        # workspace path before relocating that completed source directory.
        self.manager.processes.pop(identifier)
        moved = self.root/'cancelled-moved'; directory.rename(moved)
        self.assertEqual(self.wait(resumed)['tuning_status'], 'PAUSED')
        target = self.manager.directory(resumed)
        result = read_planar_tune(target/RESULT)
        self.assertEqual(result['trials'][:1], previous['trials'])
        self.assertEqual(_snapshot_trial(target/'execution/trial-001'), previous['trial_sources_sha256'][0])
        self.assertEqual(saved, (moved/'execution/checkpoint-001.json').read_bytes())
        self.assertEqual(read_planar_tune_job_checkpoint(target, 1)['trials'], previous['trials'])
        self.manager.close(); self.manager = JobManager(self.root/'workspace'); self.addCleanup(self.manager.close)
        self.assertEqual(self.manager.status(resumed, verify=True)['tuning_status'], 'PAUSED')

    def test_real_recovered_final_refinement_preserves_native_and_analytic_cutoff(self):
        raw = crossing_request()
        first = execute_planar_tune(raw, self.root/'search', max_new_trials=2)
        self.assertEqual(first['trials'][-1]['identity_recovery']['status'], 'PASS')
        identifier = self.manager.start_planar_tune(raw, checkpoint=self.root/'search/checkpoint-002.json')
        (self.root/'search').rename(self.root/'search-moved')
        self.assertEqual(self.wait(identifier)['tuning_status'], 'TUNED')
        result = read_planar_tune(self.manager.directory(identifier)/RESULT)
        self.assertEqual(result['trial_sources_sha256'][:2], first['trial_sources_sha256'])
        final = result['trials'][-1]
        self.assertEqual(final['identity_recovery']['status'], 'PASS')
        self.assertEqual((final['identity_recovery']['parent_trial_index'], final['identity_recovery']['anchor_trial_index']), (1, 0))
        self.assertEqual(final['current_mode_ids'], ['x', 'y'])
        self.assertLess(abs(final['frequency_hz']/raw['target_hz']-1), 3e-6)
        self.assertTrue(result['decision']['mesh_difference_met'])
        self.assertTrue(result['decision']['refined_target_met'])
        for i, hashes in enumerate(first['trial_sources_sha256']):
            self.assertEqual(_snapshot_trial(self.root/'search-moved'/f'trial-{i+1:03d}'), hashes)

    def test_unverified_worker_keeps_null_frequency_and_refuses_resume(self):
        raw = shape_request(.2, .2, .22, nonaffine=False, nx=4)
        raw.update(initial_ids=['y', 'x'], mode_id='x')
        identifier = self.manager.start_planar_tune(raw)
        self.assertEqual(self.wait(identifier)['tuning_status'], 'UNVERIFIED')
        directory = self.manager.directory(identifier)
        result = read_planar_tune_job_checkpoint(directory, 1)
        self.assertIsNone(result['trials'][-1]['frequency_hz'])
        self.assertIsNone(result['trials'][-1]['target_error_hz'])
        self.assertFalse(result['can_resume'])
        with self.assertRaisesRegex(ValueError, 'PAUSED'):
            self.manager.start_planar_tune(raw, checkpoint=result)

    def test_queued_copy_mutation_failure_prefix_and_rehashed_completion_tampering(self):
        raw = shape_request(nx=4)
        previous = execute_planar_tune(raw, self.root/'source', max_new_trials=1)
        directory = self.queue(raw, previous)
        path = directory/ANCESTRY/'trial-001/project.json'
        original = path.read_bytes(); path.write_bytes(original+b' ')
        with self.assertRaisesRegex(ValueError, 'input changed'):
            execute_prepared_planar_tune(directory)
        self.assertFalse((directory/'manifest.json').exists())
        self.assertFalse((directory/'execution').exists())
        path.write_bytes(original)
        directory = self.queue(raw, previous)
        with patch('superfish_ng.planar_tuning_saved.execute_planar_project', side_effect=RuntimeError('injected new solve failure')):
            with self.assertRaisesRegex(RuntimeError, 'injected'):
                execute_prepared_planar_tune(directory)
        self.assertFalse((directory/'manifest.json').exists())
        result = read_planar_tune_job_checkpoint(directory, 1)
        self.assertEqual(result['trials'], previous['trials'])
        failure = json.loads((directory/'execution/failure-002.json').read_text())
        self.assertNotIn('frequency_hz', failure)
        complete = self.queue(raw, previous)
        execute_prepared_planar_tune(complete)
        originals = {p: p.read_bytes() for p in complete.rglob('*') if p.is_file()}
        for kind in ('prefix', 'ancestry', 'request', 'undeclared', 'budget'):
            with self.subTest(kind=kind):
                if kind == 'prefix':
                    path = complete/'execution/checkpoint-001.json'
                    value = json.loads(path.read_text()); value['trials'][0]['frequency_hz'] *= 1.001
                    save(path, value)
                elif kind == 'ancestry':
                    path = complete/ANCESTRY/'trial-001/project.json'; path.write_bytes(path.read_bytes()+b' ')
                elif kind == 'request':
                    path = complete/'execution/request.json'; value = json.loads(path.read_text())
                    value['target_hz'] *= 1.001; save(path, value)
                elif kind == 'budget':
                    path = complete/INPUT; value = json.loads(path.read_text()); value['max_new_trials'] = 2; save(path, value)
                else:
                    path = complete/'execution/extra.txt'; path.write_text('undeclared')
                manifest = json.loads((complete/'manifest.json').read_text())
                manifest['files'][path.relative_to(complete).as_posix()] = _digest(path)
                save(complete/'manifest.json', manifest)
                if kind in ('ancestry', 'budget'):
                    state = json.loads((complete/'job.json').read_text())
                    state['input_sha256'][path.relative_to(complete).as_posix()] = _digest(path)
                    save(complete/'job.json', state)
                with self.assertRaises(ValueError): read_job(complete)
                for p, content in originals.items(): p.write_bytes(content)
                if kind == 'undeclared': path.unlink()
        self.assertEqual(read_job(complete)['tuning_status'], 'PAUSED')


if __name__ == '__main__':
    unittest.main()
