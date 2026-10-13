# SPDX-License-Identifier: Apache-2.0
"""Finite confirmation and honest costs: rejected probes and missing data count."""
from copy import deepcopy
import unittest

from superfish_ng.curved_rf_goal_efficiency_summary import summarize_execution, compare_repetitions, error_rows
from superfish_ng.curved_rf_goal_efficiency_metrics import assess_rf_goal_history
from test_curved_rf_goal_efficiency_metrics import fixture, reference_orders


def report():
    events,observations=fixture(['initial','uniform_probe','rf_local','uniform_probe','uniform_confirmation'],[None,0,0,2,3],[True,False,True,True,True])
    observations[0]['reference_orders']=reference_orders(.02)
    execution=dict(id='case-repetition-1-rf_goal',case_id='case',method='rf_goal',repetition=1,status='NOT_RUN')
    phases=[]
    for i in range(5):
        root=len(phases)
        phases.extend([dict(index=root,name='native_event',parent_index=None,inclusive_seconds=10.,exclusive_seconds=4.),
                       dict(index=root+1,name='native_solve_and_normalization',parent_index=root,inclusive_seconds=6.,exclusive_seconds=4.),
                       dict(index=root+2,name='eigenproblem',parent_index=root+1,inclusive_seconds=2.,exclusive_seconds=2.)])
    records=[dict(index=i,observed_prefix_cost=dict(native_path_cumulative_seconds=(i+1)*10.,
                 recorder_prefix_wall_seconds=(i+1)*12.,submission_prefix_wall_seconds=(i+1)*12.+1.)) for i in range(5)]
    for i,event in enumerate(events):event.update(dofs=(i+1)*100,triangles=(i+1)*50)
    journal=dict(schema_version=1,document_type='curved_rf_goal_efficiency_worker_checkpoint',execution=execution,
        status='TARGETS_MET',native_status='TARGETS_MET',events=events,observations=observations,event_records=records,
        development_event_limit=None,observed_cost=dict(phases=phases),assessment=assess_rf_goal_history(events,observations))
    bundle=dict(status='PROCESS_EXITED',source_audit=dict(status='UNCHANGED'),
        process=dict(status='PROCESS_EXITED',exit_code=0,wall_seconds=65.,peak_rss_bytes=1024))
    return execution,bundle,journal


class RFGoalSummaryTests(unittest.TestCase):
    def test_confirmation_uses_actual_accepted_ancestry_and_includes_rejected_probe_cost(self):
        execution,bundle,journal=report();row=summarize_execution(execution,bundle,journal)
        self.assertTrue(row['confirmed']);self.assertEqual(row['confirmation_event_indices'],[2,3,4])
        hit=row['confirmed_accuracy_hit'];self.assertEqual(hit['dofs'],500)
        self.assertEqual(hit['native_path_cumulative_seconds'],50.)
        self.assertEqual(hit['native_solve_cumulative_seconds'],30.)
        self.assertEqual(hit['eigenproblem_cumulative_seconds'],10.)
        self.assertEqual(row['maximum_event_dofs'],500)
        self.assertEqual(row['first_rejected_accuracy_hit']['event_index'],1)

    def test_native_success_development_resume_and_failed_process_do_not_become_benchmark_success(self):
        execution,bundle,journal=report()
        for field,value in [('status','LEVEL_LIMIT'),('development_event_limit',5),('schema_version',2)]:
            bad=deepcopy(journal);bad[field]=value
            self.assertFalse(summarize_execution(execution,bundle,bad)['confirmed'])
        for state,code in [('MEMORY_LIMIT',0),('WALL_LIMIT',-15),('PROCESS_FAILED',1)]:
            bad=deepcopy(bundle);bad['status']=state;bad['process'].update(status=state,exit_code=code)
            row=summarize_execution(execution,bad,journal);self.assertFalse(row['confirmed'])
            self.assertIsNone(row['confirmed_accuracy_hit'])
        bad=deepcopy(journal);bad['events'][4]['quadrature_check']['passed']=False
        bad['assessment']=assess_rf_goal_history(bad['events'],bad['observations'])
        self.assertFalse(summarize_execution(execution,bundle,bad)['confirmed'])

    def test_no_journal_or_missing_phase_costs_stay_unknown_and_preserve_process_wall(self):
        execution,bundle,journal=report();row=summarize_execution(execution,bundle,None)
        self.assertIsNone(row['benchmark_status']);self.assertIsNone(row['first_accuracy_hit'])
        self.assertEqual(row['process_wall_seconds'],65.);self.assertIsNone(row['maximum_event_dofs'])
        del journal['observed_cost'];row=summarize_execution(execution,bundle,journal)
        self.assertIsNone(row['confirmed_accuracy_hit']['native_solve_cumulative_seconds'])

    def test_forged_assessment_or_nonfinite_costs_are_rejected(self):
        execution,bundle,journal=report();bad=deepcopy(journal);bad['assessment']['first_accuracy_hit_index']=0
        with self.assertRaises(ValueError):summarize_execution(execution,bundle,bad)
        bad=deepcopy(journal);bad['event_records'][3]['observed_prefix_cost']['native_path_cumulative_seconds']=float('nan')
        with self.assertRaises(ValueError):summarize_execution(execution,bundle,bad)

    def test_both_repetitions_are_required_and_each_failed_pair_has_null_ratios(self):
        execution,bundle,journal=report();rows=[]
        for method in ('uniform','rf_goal','uniform_when_rf_passes'):
            for repetition in (1,2):
                e=dict(execution,id=f'{method}-{repetition}',method=method,repetition=repetition)
                j=deepcopy(journal);j['execution']=e
                rows.append(summarize_execution(e,bundle,j))
        result=compare_repetitions(rows)[0];self.assertEqual(result['status'],'PRECISION_MATCHED_REPETITIONS')
        self.assertEqual(result['ratios']['rf_goal']['full_process_uniform_over_method'],[1.,1.])
        rows[3]['confirmed']=False;rows[3]['confirmed_accuracy_hit']=None
        result=compare_repetitions(rows)[0];self.assertIsNone(result['ratios']['rf_goal'])
        self.assertIsNotNone(result['ratios']['uniform_when_rf_passes'])
        self.assertEqual(result['methods']['rf_goal']['confirmed'],[True,False])
        with self.assertRaises(ValueError):compare_repetitions(rows+[rows[0]])

    def test_error_export_keeps_both_orders_all_quantities_and_rejected_events(self):
        execution,bundle,journal=report();rows=list(error_rows(execution,journal))
        self.assertEqual(len(rows),5*2*9)
        rejected=[r for r in rows if r['event_index']==1]
        self.assertEqual(len(rejected),18);self.assertTrue(all(not r['accepted'] for r in rejected))
        self.assertEqual({r['gauss_order'] for r in rows},{16,24})
        self.assertTrue(all(r['physical_error_bound'] is None for r in rows))


if __name__=='__main__':unittest.main()
