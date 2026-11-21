# SPDX-License-Identifier: Apache-2.0
"""Fixed serial execution and preservation of terminal failures, without FEM."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('rf_goal_benchmark',ROOT/'scripts/validate_curved_rf_goal_efficiency.py')
benchmark=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(benchmark)


class RFGoalBenchmarkTests(unittest.TestCase):
    def test_exact_36_order_serial_terminal_failures_and_exclusive_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'new';calls=[]
            def execute(invocation,target):
                calls.append(invocation['execution']['id']);target.mkdir()
                state='WALL_LIMIT' if len(calls)==2 else 'PROCESS_FAILED'
                bundle=dict(status=state,source_audit=dict(status='UNCHANGED'),
                    process=dict(status=state,exit_code=-15 if len(calls)==2 else 7,wall_seconds=1.,peak_rss_bytes=1024))
                benchmark.publish_rf_goal_json(target/'manifest.json',bundle)
                return bundle
            with patch.object(benchmark,'prepare_references',return_value={'status':'VERIFIED','bound_inputs':{}}), \
                 patch.object(benchmark.transport,'run_invocation',side_effect=execute), \
                 patch.object(benchmark,'source_hashes',return_value={'source':'fixed'}):
                result=benchmark.run_benchmark(out,{})
                self.assertEqual(calls,[r['id'] for r in benchmark.build_curved_rf_goal_efficiency_plan()['executions']])
                self.assertEqual(result['actual_native_executions'],36)
                self.assertEqual(result['status'],'FIXED_RUNS_RECORDED_WITH_UNMET_TARGETS')
                self.assertEqual(len(list(out.glob('row-*.json'))),36)
                self.assertEqual(result['rows'][1]['process_status'],'WALL_LIMIT')
                self.assertTrue(all(not r['confirmed'] for r in result['rows']))
                with self.assertRaises(FileExistsError):benchmark.run_benchmark(out,{})
                self.assertEqual(len(calls),36)

    def test_source_change_stops_later_rows_and_retains_all_completed_measurements(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'new';calls=[]
            def execute(invocation,target):
                calls.append(invocation['execution']['id']);target.mkdir()
                value=dict(status='SOURCE_CHANGED',source_audit=dict(status='CHANGED'),
                    process=dict(status='PROCESS_EXITED',exit_code=0,wall_seconds=1.,peak_rss_bytes=100))
                benchmark.publish_rf_goal_json(target/'manifest.json',value);return value
            with patch.object(benchmark,'prepare_references',return_value={'status':'VERIFIED','bound_inputs':{}}), \
                 patch.object(benchmark.transport,'run_invocation',side_effect=execute), \
                 patch.object(benchmark,'source_hashes',side_effect=[{'a':'before'},{'a':'before'},{'a':'after'}]):
                result=benchmark.run_benchmark(out,{})
            self.assertEqual(len(calls),1);self.assertEqual(result['status'],'SOURCE_CHANGED')
            self.assertEqual(result['not_run_execution_ids'],[r['id'] for r in benchmark.build_curved_rf_goal_efficiency_plan()['executions'][1:]])
            self.assertTrue((out/'row-001.json').is_file());self.assertTrue((out/'summary.json').is_file())

    def test_reference_failure_occurs_before_output_or_any_native_worker(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'new';error=ValueError('original reference missing')
            with patch.object(benchmark,'prepare_references',side_effect=error),patch.object(benchmark.transport,'run_invocation') as run:
                with self.assertRaises(ValueError) as caught:benchmark.run_benchmark(out,{})
                self.assertIs(caught.exception,error);run.assert_not_called();self.assertFalse(out.exists())

    def test_preflight_source_change_and_reporting_error_never_hide_attempted_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'new'
            with patch.object(benchmark,'prepare_references',return_value={'status':'VERIFIED','bound_inputs':{}}), \
                 patch.object(benchmark,'source_hashes',side_effect=[{'a':'old'},{'a':'new'}]), \
                 patch.object(benchmark.transport,'run_invocation') as run:
                with self.assertRaises(ValueError):benchmark.run_benchmark(out,{})
                run.assert_not_called();self.assertFalse(out.exists())
            def execute(invocation,target):
                target.mkdir();return dict(status='PROCESS_FAILED',source_audit=dict(status='UNCHANGED'),process=None)
            with patch.object(benchmark,'prepare_references',return_value={'status':'VERIFIED','bound_inputs':{}}), \
                 patch.object(benchmark,'source_hashes',return_value={}), \
                 patch.object(benchmark.transport,'run_invocation',side_effect=execute), \
                 patch.object(benchmark,'load_record',side_effect=ValueError('invalid saved measurement')):
                with self.assertRaises(ValueError):benchmark.run_benchmark(out,{})
            summary=json.loads((out/'summary.json').read_text())
            self.assertEqual(summary['actual_native_executions'],1);self.assertEqual(summary['completed_measurement_rows'],0)
            self.assertEqual(len(summary['not_run_execution_ids']),35);self.assertEqual(len(summary['unreported_execution_ids']),1)

    def test_error_csv_exports_nulls_as_missing_instead_of_zero(self):
        from test_curved_rf_goal_efficiency_summary import report
        execution,bundle,journal=report();journal['observations'][1]['reference_orders'][0]['accuracy']['relative_errors']['frequency_hz']=None
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'errors.csv';benchmark.export_errors(path,[(execution,journal)])
            import csv
            with path.open() as stream:rows=list(csv.DictReader(stream))
            row=next(r for r in rows if r['event_index']=='1' and r['gauss_order']=='16' and r['quantity']=='frequency_hz')
            self.assertEqual(row['relative_error'],'');self.assertEqual(len(rows),90)


if __name__=='__main__':unittest.main()
