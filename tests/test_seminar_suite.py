# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from seminar_suite import job_success, portal, wait_for_reference_files


class SeminarSuiteTests(unittest.TestCase):
    def test_reference_wait_is_not_success_for_missing_or_empty_files(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'raw'
            self.assertFalse(wait_for_reference_files([path], 0))
            path.touch()
            self.assertFalse(wait_for_reference_files([path], 0))
            path.write_text('data')
            self.assertTrue(wait_for_reference_files([path], 0))
            self.assertTrue(wait_for_reference_files([path], .1, interval_s=.001))

    def test_child_exit_and_explicit_boolean_gate_are_both_required(self):
        self.assertTrue(job_success(0, {'passed': True}))
        for code, data in [(1, {'passed': True}), (0, {'passed': False}), (0, None),
                           (0, {}), (0, {'passed': 'true'}), (0, {'passed': 1})]:
            self.assertFalse(job_success(code, data))

    def test_failed_job_is_visible_and_not_linked_to_missing_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            portal(root, [{'name': 'failed', 'label': '<unsafe>', 'status': 'FAIL', 'report_file': 'comparison.json'}], False)
            text = (root/'index.html').read_text()
            self.assertIn('FAIL / INCOMPLETE', text)
            self.assertIn('&lt;unsafe&gt;', text)
            self.assertIn('数値記録なし', text)
            self.assertNotIn('href="failed/comparison.json"', text)


if __name__ == '__main__':
    unittest.main()
