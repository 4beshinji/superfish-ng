# SPDX-License-Identifier: Apache-2.0
"""A pending preflight must not prevent another worker's cancellation or closure."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from superfish_ng.jobs import JobManager,_state
from superfish_ng.rf_optimization_jobs import _job_input


class RFOptimizationStartConcurrencyTests(unittest.TestCase):
    def test_status_cancel_and_close_during_preflight_prevent_late_launch(self):
        request=json.loads(Path('examples/optimization/curved_rf.json').read_text())
        entered=threading.Event();release=threading.Event();responded=threading.Event()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);manager=JobManager(root);directory=manager.directory('other');directory.mkdir()
            _state(directory,'running',kind='solve')
            # A real local process is sufficient to test cancellation; it is not a FEM result.
            process=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'])
            manager.processes['other']=process
            def validation(data):
                entered.set()
                if not release.wait(10):raise RuntimeError('test preflight was not released')
                return _job_input(data)
            def probe():
                state=manager.status('other');cancelled=manager.cancel('other');manager.close();responded.set()
                return state,cancelled
            try:
                with patch('superfish_ng.rf_optimization_jobs._job_input',side_effect=validation), patch(
                        'superfish_ng.rf_optimization_jobs.subprocess.Popen',side_effect=AssertionError('unexpected late worker')) as launch:
                    with ThreadPoolExecutor(max_workers=2) as pool:
                        starting=pool.submit(manager.start_rf_optimization,request)
                        self.assertTrue(entered.wait(2))
                        probing=pool.submit(probe)
                        try:responsive=responded.wait(2)
                        finally:release.set()
                        states=probing.result(timeout=10)
                        error=starting.exception(timeout=10)
                    self.assertTrue(responsive,'preflight blocked status/cancel/close on another worker')
                    self.assertEqual(states[0]['status'],'running');self.assertEqual(states[1]['status'],'cancelled')
                    self.assertIsInstance(error,ValueError);self.assertIn('closed',str(error))
                    launch.assert_not_called()
                    self.assertFalse(list(root.glob('*/rf-optimization-request.json')))
                    self.assertIsNotNone(process.poll())
            finally:
                release.set();manager.close()
                if process.poll() is None:process.terminate();process.wait(timeout=5)

    def test_already_closed_manager_does_not_read_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager=JobManager(tmp);manager.close()
            with patch('superfish_ng.rf_optimization_jobs._job_input') as validation:
                with self.assertRaisesRegex(ValueError,'closed'):manager.start_rf_optimization({})
                validation.assert_not_called()
