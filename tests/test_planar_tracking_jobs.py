# SPDX-License-Identifier: Apache-2.0
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from superfish_ng.planar import PlanarCase, solve_planar
from superfish_ng.planar_saved import save_planar_run
from superfish_ng.planar_tracking import PlanarTrackingRequest
from superfish_ng.planar_tracking_jobs import (
    execute_planar_tracking, read_planar_tracking, execute_prepared_planar_tracking,
    _prepare, _snapshot,
)
from superfish_ng.jobs import JobManager, read_job


class PlanarTrackingJobTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.paths = [self.root/'previous', self.root/'current']
        for path, width in zip(self.paths, (.18, .22)):
            case = PlanarCase(width, .2, nx=4, ny=4, modes=3)
            save_planar_run(case, solve_planar(case), path)
        self.request = PlanarTrackingRequest()

    def tearDown(self):
        self.temp.cleanup()

    def rehash(self, directory):
        path = directory/'manifest.json'; data = json.loads(path.read_text())
        data['files'] = {name: hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in data['files']}
        path.write_text(json.dumps(data))

    def test_portable_copied_native_replay_and_completed_reentry(self):
        directory = self.root/'run'
        result = execute_planar_tracking(*self.paths, self.request, directory)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['current_mode_ids'], ['mode-2', 'mode-1'])
        for source, side in zip(self.paths, ('previous', 'current')):
            self.assertEqual({p.name: p.read_bytes() for p in source.iterdir()},
                             {p.name: p.read_bytes() for p in (directory/side).iterdir()})
            shutil.rmtree(source)
        self.assertEqual(result, read_planar_tracking(directory))
        self.assertEqual(read_job(directory)['kind'], 'planar_tracking')
        before = _snapshot(directory)
        with self.assertRaises(ValueError): execute_prepared_planar_tracking(directory)
        self.assertEqual(before, _snapshot(directory))

    def test_rehashed_ids_phase_resolution_and_boolean_group_rejected(self):
        directory = self.root/'run'; execute_planar_tracking(*self.paths, self.request, directory)
        path = directory/'tracking-results.json'; original = path.read_bytes()
        for change in ('id', 'phase', 'resolution', 'boolean', 'extra'):
            data = json.loads(original)
            if change == 'id': data['current_mode_ids'][0] = 'invented'
            elif change == 'phase': data['matches'][0]['previous_phase_multiplier'] *= -1
            elif change == 'resolution': data['spectral_resolution'][0]['relative_inverse_residual'][0] = 0.
            elif change == 'boolean': data['matches'][0]['previous_indices'][0] = True
            else: data['extra'] = 'unrecognized'
            path.write_text(json.dumps(data)); self.rehash(directory)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'full native'):
                read_job(directory)

    def test_kind_downgrade_missing_native_and_changed_queued_input(self):
        directory = self.root/'run'; execute_planar_tracking(*self.paths, self.request, directory)
        saved = {name: (directory/name).read_bytes() for name in ('job.json', 'manifest.json')}
        for kind in (None, 'planar_solve', 'planar_study', 'planar_convergence', 'study'):
            for name, raw in saved.items():
                data = json.loads(raw)
                if kind is None: data.pop('kind')
                else: data['kind'] = kind
                (directory/name).write_text(json.dumps(data))
            with self.assertRaises(ValueError): read_job(directory)
        for name, raw in saved.items(): (directory/name).write_bytes(raw)
        (directory/'current/fields.npz').unlink()
        with self.assertRaises(ValueError): read_job(directory)
        queued = self.root/'queued'; _prepare(*self.paths, self.request, queued)
        path = queued/'tracking.json'; path.write_text(path.read_text()+' ')
        with patch('superfish_ng.planar_tracking_jobs.track_planar_modes', side_effect=AssertionError('must not compare')):
            with self.assertRaisesRegex(ValueError, 'changed'): execute_prepared_planar_tracking(queued)
        self.assertEqual(read_job(queued)['status'], 'failed')

    def test_source_mutation_during_copy_and_during_completion(self):
        original = shutil.copyfile
        def change_source(source, target):
            result = original(source, target)
            path = self.paths[0]/'case.json'
            path.write_text(path.read_text()+' ')
            return result
        with patch('superfish_ng.planar_tracking_jobs.shutil.copyfile', side_effect=change_source):
            with self.assertRaisesRegex(ValueError, 'changed'): _prepare(*self.paths, self.request, self.root/'copy')
        self.assertEqual(read_job(self.root/'copy')['status'], 'failed')

    def test_completion_mutation_is_not_published_as_complete(self):
        original = read_planar_tracking
        def change_after_read(directory):
            result = original(directory); path = directory/'tracking.json'
            path.write_text(path.read_text()+' '); return result
        with patch('superfish_ng.planar_tracking_jobs.read_planar_tracking', side_effect=change_after_read):
            with self.assertRaisesRegex(ValueError, 'changed'):
                execute_planar_tracking(*self.paths, self.request, self.root/'run')
        self.assertEqual(read_job(self.root/'run')['status'], 'failed')

    def test_actual_worker_cancel_restart_and_source_import(self):
        manager = JobManager(self.root/'workspace')
        try:
            cancelled = manager.start_planar_tracking(*self.paths, self.request)
            deadline = time.monotonic()+30
            while manager.status(cancelled)['status'] == 'queued' and time.monotonic() < deadline: time.sleep(.01)
            self.assertEqual(manager.status(cancelled)['status'], 'running')
            self.assertEqual(manager.cancel(cancelled)['status'], 'cancelled')
            self.assertIsNotNone(manager.processes[cancelled].poll())
            identifier = manager.start_planar_tracking(*self.paths, self.request)
            self.assertEqual(manager.processes[identifier].wait(timeout=60), 0)
            before = _snapshot(manager.directory(identifier))
            imported = manager.import_planar_result(manager.directory(identifier)/'current')
            self.assertEqual(before, _snapshot(manager.directory(identifier)))
            manager.close(); manager = JobManager(self.root/'workspace')
            self.assertEqual(manager.status(identifier, verify=True)['status'], 'complete')
            self.assertEqual(manager.status(imported, verify=True)['status'], 'complete')
        finally: manager.close()

    def test_cli_execution_and_replay(self):
        path = self.root/'request.json'; self.request.save(path); results = []
        for args in (['execute-planar-tracking', *map(str, self.paths), str(path), '--out', str(self.root/'run')],
                     ['replay-planar-tracking', str(self.root/'run')]):
            run = subprocess.run([sys.executable, '-m', 'superfish_ng', *args], capture_output=True, text=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stderr); results.append(json.loads(run.stdout))
        self.assertEqual(*results)
