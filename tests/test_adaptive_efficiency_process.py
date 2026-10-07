# SPDX-License-Identifier: Apache-2.0
"""Actual fresh-process budget stops; no FEM or efficiency claims."""
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from superfish_ng import adaptive_efficiency_process as runner


@unittest.skipUnless(sys.platform == 'linux', 'Linux wait4 and /proc budget monitor')
class AdaptiveEfficiencyProcessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / 'fresh'

    def run_child(self, code, **kwargs):
        return runner.run_measured_process([sys.executable, '-c', code], self.out,
                                           poll_seconds=0.01, **kwargs)

    def assert_reaped(self, receipt):
        with self.assertRaises(ChildProcessError):
            os.waitpid(receipt['pid'], os.WNOHANG)
        self.assertFalse(Path(f"/proc/{receipt['pid']}").exists())

    def test_actual_process_exit_logs_terminal_peak_and_exclusive_output(self):
        result = self.run_child("import resource,sys; print('hello'); "
                                "print(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024); "
                                "print('diagnostic',file=sys.stderr)")
        self.assertEqual(result['status'], 'PROCESS_EXITED')
        self.assertEqual(result['exit_code'], 0)
        stdout = (self.out / 'stdout.log').read_text().splitlines()
        self.assertEqual(stdout[0], 'hello')
        self.assertGreaterEqual(result['terminal_peak_rss_bytes'], int(stdout[1]))
        self.assertGreater(result['wall_seconds'], 0)
        self.assertEqual((self.out / 'stderr.log').read_text(), 'diagnostic\n')
        self.assertEqual(json.loads((self.out / 'process.json').read_text()), result)
        before = {p.name: p.read_bytes() for p in self.out.iterdir()}
        with self.assertRaises(FileExistsError):
            self.run_child('raise Exception("must not execute")')
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.out.iterdir()})
        self.assert_reaped(result)

    def test_real_failure_preserves_logs_exit_and_cost(self):
        result = self.run_child("import sys; print('before failure',flush=True); sys.exit(7)")
        self.assertEqual((result['status'], result['exit_code']), ('PROCESS_FAILED', 7))
        self.assertEqual((self.out / 'stdout.log').read_text(), 'before failure\n')
        self.assertGreater(result['peak_rss_bytes'], 0)
        self.assert_reaped(result)

    def test_wall_stop_kills_term_ignoring_worker_and_reaps(self):
        result = self.run_child("import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); "
                                "print('ready',flush=True); time.sleep(30)",
                                wall_limit_seconds=0.4, terminate_grace_seconds=0.05)
        self.assertEqual(result['status'], 'WALL_LIMIT')
        self.assertEqual(result['exit_code'], -9)
        self.assertIn('ready', (self.out / 'stdout.log').read_text())
        self.assertGreaterEqual(result['wall_seconds'], 0.4)
        self.assertLess(result['wall_seconds'], 5)
        self.assert_reaped(result)

    def test_actual_rss_excess_is_non_success_and_preserves_artifacts(self):
        result = self.run_child("import time; a=bytearray(128*1024**2); "
                                "print('allocated',flush=True); time.sleep(30)",
                                memory_limit_bytes=96 * 1024**2, terminate_grace_seconds=0.05)
        self.assertEqual(result['status'], 'MEMORY_LIMIT')
        self.assertGreater(result['peak_rss_bytes'], 96 * 1024**2)
        self.assertNotEqual(result['exit_code'], 0)
        self.assert_reaped(result)

    def test_terminal_peak_detects_excess_even_with_missing_live_samples(self):
        with patch.object(runner, 'process_peak_rss_bytes', return_value=None):
            result = self.run_child('pass', memory_limit_bytes=1)
        self.assertEqual((result['status'], result['exit_code']), ('MEMORY_LIMIT', 0))
        self.assertGreater(result['terminal_peak_rss_bytes'], 1)
        self.assertIsNone(result['sampled_peak_rss_bytes'])
        self.assert_reaped(result)

    def test_missing_memory_stays_unknown_not_zero(self):
        original_wait = runner._wait
        def missing_usage(*args, **kwargs):
            value = original_wait(*args, **kwargs)
            return None if value is None else SimpleNamespace(ru_maxrss=0)
        with patch.object(runner, '_wait', side_effect=missing_usage), \
                patch.object(runner, 'process_peak_rss_bytes', return_value=None):
            result = self.run_child('pass')
        self.assertEqual(result['memory_status'], 'UNKNOWN')
        self.assertEqual(result['status'], 'MEMORY_UNVERIFIED')
        self.assertIsNone(result['peak_rss_bytes'])
        self.assert_reaped(result)

    def test_wall_stop_signals_owned_group_and_worker_reaps_descendant(self):
        code = ("import subprocess,sys,signal,time\n"
                "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'])\n"
                "def stop(sig,frame):\n child.wait(); sys.exit(0)\n"
                "signal.signal(signal.SIGTERM,stop)\n"
                "print(child.pid,flush=True)\n"
                "time.sleep(30)\n")
        result = self.run_child(code, wall_limit_seconds=0.4, terminate_grace_seconds=0.5)
        child_pid = int((self.out / 'stdout.log').read_text().strip())
        self.assertEqual(result['status'], 'WALL_LIMIT')
        self.assertEqual(result['exit_code'], 0)
        self.assertFalse(Path(f'/proc/{child_pid}').exists())
        self.assert_reaped(result)

    def test_start_failure_preserves_exception_and_unknown_cost(self):
        with self.assertRaises(FileNotFoundError):
            runner.run_measured_process([str(Path(self.temp.name) / 'missing-command')], self.out)
        result = json.loads((self.out / 'process.json').read_text())
        self.assertEqual(result['status'], 'SUPERVISOR_FAILED')
        self.assertEqual(result['exception_type'], 'FileNotFoundError')
        self.assertIsNone(result['pid'])
        self.assertIsNone(result['exit_code'])
        self.assertIsNone(result['peak_rss_bytes'])

    def test_terminal_high_water_can_include_reaped_descendant_and_labels_scope(self):
        child = ("import resource; a=bytearray(128*1024**2); "
                 "print(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)")
        code = ("import subprocess,sys,resource,json\n"
                f"value=subprocess.check_output([sys.executable,'-c',{child!r}],text=True)\n"
                "print(json.dumps({'worker_self':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,"
                "'descendant':int(value)}))\n")
        result = self.run_child(code)
        measured = json.loads((self.out / 'stdout.log').read_text())
        self.assertGreater(measured['descendant'], measured['worker_self'])
        self.assertGreaterEqual(result['terminal_peak_rss_bytes'], measured['descendant'])
        self.assertEqual(result['sampled_memory_scope'], 'worker-only VmHWM including threads')
        self.assertEqual(result['terminal_memory_scope'],
                         'Linux wait4 high-water maximum; may include descendants reaped by worker; not concurrent tree RSS')
        self.assert_reaped(result)

    def test_interrupt_is_recorded_and_original_exception_reraised_after_reap(self):
        with patch.object(runner, 'process_peak_rss_bytes', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.run_child('import time; time.sleep(30)', terminate_grace_seconds=0.05)
        result = json.loads((self.out / 'process.json').read_text())
        self.assertEqual(result['status'], 'INTERRUPTED')
        self.assertEqual(result['exception_type'], 'KeyboardInterrupt')
        self.assertNotEqual(result['exit_code'], 0)
        self.assert_reaped(result)

    def test_invalid_budget_does_not_start_or_reserve_output(self):
        for kwargs in ({'wall_limit_seconds': float('nan')}, {'wall_limit_seconds': True},
                       {'memory_limit_bytes': True}, {'memory_limit_bytes': 0},
                       {'poll_seconds': 0.001}, {'terminate_grace_seconds': -1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                runner.run_measured_process([sys.executable, '-c', 'pass'], self.out, **kwargs)
            self.assertFalse(self.out.exists())


if __name__ == '__main__':
    unittest.main()
