# SPDX-License-Identifier: Apache-2.0
"""Fixed fresh native execution: real ancestry, complete samples and failures."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from superfish_ng.curved_rf_goal_efficiency_plan import build_curved_rf_goal_efficiency_plan
from superfish_ng.curved_rf_goal_efficiency_worker import execute_curved_rf_goal_efficiency_worker


class RFGoalWorkerInputTests(unittest.TestCase):
    def test_nonfixed_row_invalid_development_limit_and_existing_output_fail_before_fem(self):
        row=build_curved_rf_goal_efficiency_plan()['executions'][0]
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'new';bad=deepcopy(row);bad['repetition']=True
            with patch('superfish_ng.curved_rf_adaptive_refinement.solve') as solve:
                with self.assertRaises(ValueError):execute_curved_rf_goal_efficiency_worker(bad,out)
                for limit in (True,0,1.5):
                    with self.assertRaises(ValueError):execute_curved_rf_goal_efficiency_worker(row,out,max_new_events=limit)
                with self.assertRaises(ValueError):execute_curved_rf_goal_efficiency_worker(row,out,submission_origin=float('nan'))
                with self.assertRaises(FileExistsError):execute_curved_rf_goal_efficiency_worker(row,Path(tmp))
                solve.assert_not_called()
            self.assertFalse(out.exists())


class RFGoalWorkerMetricBindingsTests(unittest.TestCase):
    def test_actual_native_peak_metadata_uses_both_intervals_not_estimate_keys(self):
        from superfish_ng.curved_rf_goal_efficiency_metrics import assess_rf_goal_pair
        from test_curved_rf_goal_efficiency_metrics import data
        a=data();b=data()
        for sample in (a,b):
            for key in ('epk_over_eacc','bpk_over_eacc_mt_per_mv_per_m'):
                sample['quantities'][key+'_estimate']=sample['quantities'].pop(key)
        result=assess_rf_goal_pair(a,b)
        self.assertEqual(result['status'],'PASS')
        b['peak_intervals']['epk_over_eacc']=[1.,1.02]
        result=assess_rf_goal_pair(a,b)
        self.assertEqual(result['status'],'FAIL')
        self.assertGreaterEqual(result['relative_errors']['epk_over_eacc'],.02)


class RFGoalWorkerDecisionTests(unittest.TestCase):
    def test_unverified_uniform_quantities_and_original_native_stops_remain_non_success(self):
        from superfish_ng.curved_rf_goal_efficiency_worker import _stop_status
        from test_curved_rf_goal_efficiency_metrics import fixture
        events,_=fixture(['initial','uniform_confirmation'],[None,0]);event=events[-1]
        event['confirmation_comparison']=dict(verified=True,passed=True)
        args=dict(initial_identity=True,same_moments=True,ritz=True,native_status=None,completed_events=2,max_events=8)
        assessment=dict(status='NOT_CONFIRMED')
        self.assertEqual(_stop_status(event,assessment,**args),'PAUSED')
        event['confirmation_comparison']['verified']=False
        self.assertEqual(_stop_status(event,assessment,**args),'QUANTITY_UNVERIFIED')
        event['confirmation_comparison']['verified']=True
        for status in ('LEVEL_LIMIT','REFINEMENT_LIMIT','TRACKING_BUDGET','ZERO_INDICATOR','QUADRATURE_UNVERIFIED','QUANTITY_UNVERIFIED'):
            self.assertEqual(_stop_status(event,assessment,**dict(args,native_status=status)),status)
        self.assertEqual(_stop_status(event,assessment,**dict(args,native_status='TARGETS_MET')),'PAUSED')
        self.assertEqual(_stop_status(event,dict(status='CONFIRMED'),**args),'TARGETS_MET')
        self.assertEqual(_stop_status(event,assessment,**dict(args,completed_events=8)),'LEVEL_LIMIT')
        for key,status in [('initial_identity','INITIAL_IDENTITY_UNVERIFIED'),('same_moments','GEOMETRY_MOMENTS_UNVERIFIED'),('ritz','RITZ_UNVERIFIED')]:
            self.assertEqual(_stop_status(event,dict(status='CONFIRMED'),**dict(args,**{key:False})),status)

    def test_final_fixed_request_recheck_refuses_changed_case_and_rechecks_bound_bytes(self):
        from superfish_ng.curved_rf_goal_efficiency_worker import _verify_fixed_request
        from superfish_ng.curved_rf_goal_efficiency_plan import request_for_curved_rf_goal_efficiency_execution
        row=build_curved_rf_goal_efficiency_plan()['executions'][0]
        request=request_for_curved_rf_goal_efficiency_execution(row)
        _verify_fixed_request(row,request)
        bad=deepcopy(request);bad['max_levels']+=1
        with self.assertRaises(ValueError):_verify_fixed_request(row,bad)
        error=ValueError('fixed request source changed during execution')
        with patch('superfish_ng.curved_rf_goal_efficiency_worker.request_for_curved_rf_goal_efficiency_execution',side_effect=error):
            with self.assertRaises(ValueError) as caught:_verify_fixed_request(row,request)
            self.assertIs(caught.exception,error)


if __name__=='__main__':unittest.main()
