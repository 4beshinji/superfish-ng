# SPDX-License-Identifier: Apache-2.0
"""A stopped checkpoint cannot fabricate a terminal measurement or process cost."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('rf_measurement_recovery', ROOT / 'scripts/recover_curved_rf_goal_measurements.py')
recovery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recovery)
b = recovery.benchmark


class RFMeasurementRecoveryTests(unittest.TestCase):
    def fixture(self, root):
        run = root / 'original'
        run.mkdir()
        plan = b.build_curved_rf_goal_efficiency_plan()
        write = b.publish_rf_goal_json
        write(run / 'plan.json', plan)
        write(run / 'sources-before.json', {'old': 'fixed'})
        execution = plan['executions'][0]
        target = run / execution['id']
        target.mkdir()
        for name in ('sources-before.json', 'sources-after.json'):
            write(target / name, {'old': 'fixed'})
        bundle = dict(status='PROCESS_FAILED', source_audit=dict(status='UNCHANGED'),
                      process=dict(status='PROCESS_FAILED', exit_code=7, wall_seconds=1., peak_rss_bytes=1024))
        write(target / 'manifest.json', bundle)
        row = b.summarize_execution(execution, bundle, None)
        row.update(bundle=dict(path=str(target / 'manifest.json'), sha256=b.transport.digest(target / 'manifest.json')), journal=None)
        write(run / 'row-001.json', row)
        active = run / plan['executions'][1]['id']
        (active / 'native').mkdir(parents=True)
        # This is deliberately not a valid public measurement. Recovery must not read it.
        write(active / 'native/checkpoint-003.json', dict(status='TARGETS_MET', assessment=dict(status='CONFIRMED')))
        stop = root / 'stop.json'
        write(stop, dict(status='STOPPED_AFTER_USER_CLEARED_GOAL', closed_measurement_rows=1,
                         last_active_execution=plan['executions'][1]['id']))
        return run, stop, plan

    def recover(self, run, out, stop):
        with patch.object(b, 'source_hashes', return_value={'old': 'fixed', 'new': 'analysis'}), \
             patch.object(b.transport, 'run_invocation', side_effect=AssertionError('recovery must never execute FEM')):
            return recovery.recover_measurements(run, out, stop, b.transport.digest(stop))

    def test_partial_checkpoint_stays_unreported_and_original_bytes_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run, stop, plan = self.fixture(root)
            before = {p: p.read_bytes() for p in run.rglob('*') if p.is_file()}
            result = self.recover(run, root / 'recovered', stop)
            self.assertEqual(result['completed_measurement_rows'], 1)
            self.assertEqual(result['observed_execution_directories'], 2)
            self.assertEqual(result['unreported_execution_ids'], [plan['executions'][1]['id']])
            self.assertEqual(len(result['not_run_execution_ids']), 34)
            self.assertEqual(result['confirmed_executions'], 0)
            self.assertEqual(result['unreported_row_terminal_cost_status'], 'UNKNOWN')
            self.assertEqual(result['whole_run_source_endpoint_status'], 'UNKNOWN')
            self.assertEqual(result['current_analysis_source_difference']['added'], ['new'])
            self.assertEqual(result['rows'][0]['process_wall_seconds'], 1.)
            self.assertEqual(before, {p: p.read_bytes() for p in run.rglob('*') if p.is_file()})
            self.assertEqual(len((root / 'recovered/errors-vs-dofs-and-time.csv').read_text().splitlines()), 1)
            with self.assertRaises(FileExistsError):
                self.recover(run, root / 'recovered', stop)

    def test_changed_row_decision_and_bundle_bytes_are_rejected_before_publication(self):
        for change in ('decision', 'bundle'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                run, stop, plan = self.fixture(root)
                if change == 'decision':
                    path = run / 'row-001.json'
                    value = json.loads(path.read_text())
                    value['confirmed'] = True
                    path.write_text(json.dumps(value))
                else:
                    (run / plan['executions'][0]['id'] / 'manifest.json').write_text('{}')
                with self.assertRaises(ValueError):
                    self.recover(run, root / 'recovered', stop)
                self.assertFalse((root / 'recovered').exists())

    def test_gaps_receipt_mismatch_source_change_and_foreign_binding_are_rejected(self):
        for change in ('row-gap', 'attempt-gap', 'receipt', 'source', 'binding', 'plan'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                run, stop, plan = self.fixture(root)
                if change == 'row-gap':
                    (run / 'row-001.json').rename(run / 'row-002.json')
                elif change == 'attempt-gap':
                    (run / plan['executions'][2]['id']).mkdir()
                    (run / plan['executions'][1]['id']).rename(root / 'moved')
                elif change == 'receipt':
                    value = json.loads(stop.read_text())
                    value['closed_measurement_rows'] = 2
                    stop.write_text(json.dumps(value))
                elif change == 'source':
                    (run / plan['executions'][0]['id'] / 'sources-after.json').write_text('{}')
                elif change == 'binding':
                    path = run / 'row-001.json'
                    value = json.loads(path.read_text())
                    value['bundle']['path'] = str(stop)
                    path.write_text(json.dumps(value))
                else:
                    value = json.loads((run / 'plan.json').read_text())
                    value['executions'].reverse()
                    (run / 'plan.json').write_text(json.dumps(value))
                with self.assertRaises(ValueError):
                    self.recover(run, root / 'recovered', stop)
                self.assertFalse((root / 'recovered').exists())

    def test_no_output_may_be_written_inside_original_measurements(self):
        with tempfile.TemporaryDirectory() as tmp:
            run, stop, _ = self.fixture(Path(tmp))
            for out in (run / 'recovery', Path(tmp) / 'unused/../original/recovery'):
                with self.subTest(out=out), self.assertRaisesRegex(ValueError, 'outside'):
                    self.recover(run, out, stop)
            self.assertFalse((run / 'recovery').exists())


if __name__ == '__main__':
    unittest.main()
