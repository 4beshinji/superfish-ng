# SPDX-License-Identifier: Apache-2.0
"""Check validation scope and reporting without repeating numerical solves."""
from contextlib import ExitStack, redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import validate
from scripts.report_validation import test_summary


class ValidationWorkflowTests(unittest.TestCase):
    def invoke(self, out, arguments=(), returncode=0):
        frequencies = [row[0] for row in validate.pillbox_spectrum(.1, .2, 6)]
        with ExitStack() as stack:
            stack.enter_context(patch.object(sys, 'argv', ['validate.py', '--out', str(out), *arguments]))
            stack.enter_context(redirect_stdout(io.StringIO()))
            stack.enter_context(patch.object(validate.platform, 'platform', return_value='test-platform'))
            process = stack.enter_context(patch.object(validate.subprocess, 'run',
                return_value=subprocess.CompletedProcess([], returncode, '', '')))
            solve = stack.enter_context(patch.object(validate, 'solve',
                return_value=SimpleNamespace(frequencies_hz=frequencies, mesh=SimpleNamespace(points=[]))))
            stack.enter_context(patch.object(validate, 'save_run'))
            stack.enter_context(patch.object(validate, 'quantities', return_value={}))
            code = validate.main()
        return code, process, solve

    def test_numerical_only_and_both_full_modes_report_their_actual_scope(self):
        with tempfile.TemporaryDirectory() as temporary:
            for name, args, skip in [('numerical', ['--skip-tests'], True),
                                     ('serial', ['--test-workers', '1'], False),
                                     ('parallel', ['--test-workers', '2'], False)]:
                with self.subTest(name=name):
                    out = Path(temporary) / name
                    code, process, solve = self.invoke(out, args)
                    self.assertEqual(code, 0)
                    report = json.loads((out / 'validation.json').read_text())
                    names = [row['name'] for row in report['commands']]
                    self.assertEqual(names, ['convergence'] if skip else ['tests', 'convergence'])
                    self.assertEqual(process.call_count, len(names))
                    self.assertEqual(solve.call_count, 5)  # Same seed work in every mode.
                    self.assertTrue(report['passed'])
                    self.assertEqual(report['scope'], 'seed-numerics' if skip else 'full')
                    self.assertEqual(report['tests']['status'], 'NOT_RUN' if skip else 'PASS')
                    self.assertEqual('unittest suite (--skip-tests)' in report['not_performed'], skip)
                    if skip:
                        self.assertFalse((out / 'tests.log').exists())
                    else:
                        command = process.call_args_list[0].args[0]
                        self.assertIn('unittest' if name == 'serial' else str(validate.ROOT / 'scripts/run_tests.py'), command)

    def test_failed_command_stops_before_seed_solves_and_never_reports_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            for name, arguments in [('full', []), ('numerical', ['--skip-tests'])]:
                out = Path(temporary) / name
                code, process, solve = self.invoke(out, arguments, returncode=7)
                self.assertEqual(code, 7)
                self.assertEqual(process.call_count, 1)
                solve.assert_not_called()
                self.assertFalse((out / 'validation.json').exists())

    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)
            marker = out / 'mine'; marker.write_text('original')
            with self.assertRaises(FileExistsError):
                self.invoke(out, ['--skip-tests'])
            self.assertEqual(marker.read_text(), 'original')

    def test_report_distinguishes_missing_tests_serial_and_parallel_total(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertIn('未実行', test_summary(root, {'tests': {'status': 'NOT_RUN'}}))
            (root / 'tests.log').write_text('Ran 2 tests in 0.01s\nOK\n')
            self.assertIn('2件', test_summary(root, {}))  # Old serial report.
            (root / 'test-run').mkdir()
            (root / 'test-run/report.json').write_text(json.dumps({'tests_run': 17}))
            self.assertIn('17件', test_summary(root, {}))  # Not the first module's 2.


if __name__ == '__main__':
    unittest.main()
