# SPDX-License-Identifier: Apache-2.0
"""Runner contracts; control records are never numerical benchmark evidence."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('efficiency_validator',ROOT/'scripts/validate_adaptive_efficiency.py')
validator=importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class AdaptiveEfficiencyValidatorTests(unittest.TestCase):
    def test_zero_process_exit_and_first_hit_do_not_imply_confirmation(self):
        execution=validator.build_adaptive_efficiency_plan()['executions'][0]
        process=dict(status='PROCESS_EXITED',wall_seconds=12.,peak_rss_bytes=100)
        record=dict(status='PAUSED',development_level_limit=None,first_accuracy_hit_index=0,
                    confirmed_accuracy_hit_index=None,levels=[dict(dofs=85,triangles=40,observed_prefix_cost={})])
        row=validator.summarize(execution,process,record)
        self.assertFalse(row['confirmed']);self.assertEqual(row['first_accuracy_hit']['dofs'],85)
        self.assertIsNone(row['confirmed_accuracy_hit'])

    def test_resource_failure_and_development_limit_veto_native_target(self):
        execution=validator.build_adaptive_efficiency_plan()['executions'][0]
        record=dict(status='TARGETS_MET',development_level_limit=None,first_accuracy_hit_index=0,
                    confirmed_accuracy_hit_index=0,levels=[dict(dofs=85,triangles=40,observed_prefix_cost={})])
        for status in ('MEMORY_LIMIT','WALL_LIMIT','PROCESS_FAILED','MEMORY_UNVERIFIED'):
            row=validator.summarize(execution,dict(status=status,wall_seconds=10.,peak_rss_bytes=None),record)
            self.assertFalse(row['confirmed']);self.assertIsNone(row['confirmed_accuracy_hit'])
        record['development_level_limit']=3
        self.assertFalse(validator.summarize(execution,dict(status='PROCESS_EXITED',wall_seconds=10.,peak_rss_bytes=100),record)['confirmed'])

    def test_comparison_requires_all_four_precision_matched_repetitions(self):
        rows=[]
        for repetition in (1,2):
            for method in ('uniform','adaptive'):
                rows.append(dict(case_id='cylinder',method=method,repetition=repetition,confirmed=True,
                    confirmed_accuracy_hit=dict(dofs=100+repetition,native_path_cumulative_seconds=4.+repetition,
                                                submission_prefix_wall_seconds=8.+repetition),
                    process_wall_seconds=10.+repetition,peak_rss_bytes=1000+repetition))
        comparison=validator.comparisons(rows)[0]
        self.assertEqual(comparison['status'],'PRECISION_MATCHED_REPETITIONS')
        self.assertEqual(comparison['methods']['uniform']['dofs'],dict(values=[101,102],range=[101,102]))
        rows[-1]['confirmed']=False
        self.assertEqual(validator.comparisons(rows)[0]['status'],'UNVERIFIED')
        self.assertEqual(validator.comparisons(rows)[0]['methods'],{})
        self.assertEqual(validator.comparisons(rows[:-1])[0]['status'],'UNVERIFIED')

    def test_latest_checkpoint_and_terminal_result_preserve_partial_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self.assertIsNone(validator.load_worker_record(root))
            validator.write_json(root/'checkpoint-001.json',dict(status='PAUSED',levels=[1]))
            validator.write_json(root/'checkpoint-002.json',dict(status='PAUSED',levels=[1,2]))
            self.assertEqual(validator.load_worker_record(root)['levels'],[1,2])
            validator.write_json(root/'result.json',dict(status='REFINEMENT_LIMIT',levels=[1,2]))
            self.assertEqual(validator.load_worker_record(root)['status'],'REFINEMENT_LIMIT')
            with self.assertRaises(FileExistsError):validator.write_json(root/'result.json',{})

    def test_csv_keeps_all_nine_quantities_both_orders_and_missing_errors(self):
        execution=validator.build_adaptive_efficiency_plan()['executions'][0]
        accuracy=dict(relative_errors={k:None for k in validator.LIMITS},gates={k:False for k in validator.LIMITS})
        row=dict(index=0,dofs=85,triangles=40,observed_prefix_cost=dict(native_path_cumulative_seconds=2.,submission_prefix_wall_seconds=4.),
                 end_of_level_status='QUADRATURE_UNVERIFIED',reference_accuracy=[dict(order=q,accuracy=accuracy) for q in (16,24)])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'errors.csv';validator.export_errors(path,[execution],[dict(levels=[row])])
            import csv
            with path.open() as stream:records=list(csv.DictReader(stream))
            self.assertEqual(len(records),18)
            self.assertEqual({r['quantity'] for r in records},set(validator.LIMITS))
            self.assertEqual({r['gauss_order'] for r in records},{'16','24'})
            self.assertTrue(all(r['relative_error']=='' and r['gate']=='False' for r in records))

    def test_twelve_supervised_rows_serial_order_limits_and_fresh_native_paths(self):
        plan=validator.build_adaptive_efficiency_plan();calls=[]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);manifest=root/'manifest.json'
            validator.write_json(manifest,dict(shared_preparation_observed_cost=dict(wall_seconds=7.)))
            bindings=dict(analytic_manifest=validator.binding(manifest),rounded_manifest=validator.binding(manifest))
            def process(argv,out,**kwargs):
                calls.append((argv,Path(out),kwargs))
                return dict(status='PROCESS_FAILED',wall_seconds=1.,peak_rss_bytes=100)
            with patch.object(validator,'load_efficiency_reference',return_value={}),patch.object(validator,'verify_reference_bytes'), \
                 patch.object(validator,'source_hashes',return_value={'control': 'sha'}),patch.object(validator,'environment',return_value={}), \
                 patch.object(validator,'run_measured_process',side_effect=process):
                result=validator.run_benchmark(root/'out',bindings)
            self.assertEqual(len(calls),12)
            self.assertEqual([p.parent.name for _,p,_ in calls],[r['id'] for r in plan['executions']])
            self.assertTrue(all(k['wall_limit_seconds']==3600 and k['memory_limit_bytes']==32*1024**3 for _,_,k in calls))
            native=[a[a.index('--out')+1] for a,_,_ in calls]
            self.assertEqual(len(set(native)),12)
            self.assertTrue(all('--submission-origin' in a for a,_,_ in calls))
            self.assertEqual(result['actual_native_executions'],12)
            self.assertTrue(all(r['native_status'] is None and not r['confirmed'] for r in result['executions']))
            self.assertTrue(all(c['status']=='UNVERIFIED' for c in result['comparisons']))
            with self.assertRaises(FileExistsError):validator.run_benchmark(root/'out',bindings)


if __name__=='__main__':unittest.main()
