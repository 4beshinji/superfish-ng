# SPDX-License-Identifier: Apache-2.0
"""Whole-field amplitudes and actual accepted parent chains, without FEM."""
from copy import deepcopy
import unittest
import numpy as np
from superfish_ng.adaptive_efficiency_accuracy import LIMITS, assess_efficiency_samples
from superfish_ng.curved_rf_goal_efficiency_metrics import (
    assess_rf_goal_pair, assess_rf_goal_orders, assess_rf_goal_history)


def data(order=16):
    n=3 if order==16 else 5
    return dict(fields=np.ones((n,3)),axis_ez=np.ones(2),weights=np.ones(n),axis_weights=np.ones(2),
                quantities=dict(frequency_hz=1.,r_over_q_accelerator_ohm=2.,r_over_q_circuit_ohm=1.,
                                geometry_factor_ohm=1.,epk_over_eacc=1.,bpk_over_eacc_mt_per_mv_per_m=1.),
                peak_intervals=dict(epk_over_eacc=[1.,1.],bpk_over_eacc_mt_per_mv_per_m=[1.,1.]))


def reference_orders(error=0.):
    result=[]
    for order in (16,24):
        x=data(order);other=x['fields'].copy();other[:,0]*=1+error
        r=assess_efficiency_samples(x['fields'],other,x['weights'],x['axis_ez'],x['axis_ez'],x['axis_weights'],
                                   x['quantities'],x['quantities'],x['peak_intervals'])
        result.append(dict(order=order,accuracy=r))
    return result


def fixture(kinds, parents, accepted=None):
    events=[];observations=[]
    for i,(kind,parent) in enumerate(zip(kinds,parents)):
        events.append(dict(index=i,parent_event_index=parent,refinement_kind=kind,
                           accepted=True if accepted is None else accepted[i],status='INITIAL' if i==0 else 'PASS',
                           current_mode_ids=['target','guard-2','guard-3'],mode_index=0,quadrature_check=dict(passed=True)))
        observations.append(dict(index=i,source_domain_identity_status='PASS',reference_orders=reference_orders(),
                                 parent_change=None if parent is None else dict(parent_event_index=parent,orders=reference_orders())))
    return events,observations


class RFGoalMetricTests(unittest.TestCase):
    def test_parent_norm_amplitude_and_single_sign_are_physical(self):
        a=data();b=deepcopy(a);b['fields']*=-1;b['axis_ez']*=-1
        before=deepcopy(b);r=assess_rf_goal_pair(a,b)
        self.assertEqual(r['status'],'PASS');self.assertEqual(r['common_hphi_sign'],-1)
        np.testing.assert_array_equal(b['fields'],before['fields'])
        b=deepcopy(a);b['fields']*=1.02;b['axis_ez']*=1.02
        r=assess_rf_goal_pair(a,b);self.assertEqual(r['status'],'FAIL')
        for name in ('electric_relative_l2','magnetic_relative_l2','axis_ez_relative_l2'):
            self.assertAlmostEqual(r['relative_errors'][name],.02,places=14)
        b=deepcopy(a);b['fields'][:,:2]*=-1
        self.assertGreater(assess_rf_goal_pair(a,b)['relative_errors']['electric_relative_l2'],1.9)

    def test_all_rf_conventions_and_both_peak_endpoints_are_required(self):
        a=data();b=deepcopy(a)
        for key in ('frequency_hz','geometry_factor_ohm'):
            b=deepcopy(a);b['quantities'][key]*=1.02
            self.assertAlmostEqual(assess_rf_goal_pair(a,b)['relative_errors'][key],.02)
        b=deepcopy(a)
        for key in ('r_over_q_accelerator_ohm','r_over_q_circuit_ohm'):b['quantities'][key]*=1.02
        self.assertEqual(assess_rf_goal_pair(a,b)['status'],'FAIL')
        b['quantities']['r_over_q_circuit_ohm']/=2
        self.assertEqual(assess_rf_goal_pair(a,b)['status'],'UNVERIFIED')
        for key in a['peak_intervals']:
            previous=deepcopy(a);previous['peak_intervals'][key]=[.98,1.02]
            r=assess_rf_goal_pair(previous,a)
            self.assertGreater(r['relative_errors'][key],.02);self.assertEqual(r['status'],'FAIL')
            for bad in ([1.,0.], [0.,1.], [1.,float('nan')], [1.], [True,1.]):
                previous['peak_intervals'][key]=bad
                self.assertEqual(assess_rf_goal_pair(previous,a)['status'],'UNVERIFIED')

    def test_missing_nodes_zero_weights_axis_and_mismatched_grids_are_unverified(self):
        a=data()
        for key,value in [('fields',np.ones((2,3))),('weights',np.array([1.,1.,0.])),
                          ('weights',np.array([1.,1.,2.])),('axis_ez',np.zeros(2)),
                          ('axis_weights',np.array([1.,2.])),('fields',np.full((3,3),np.nan))]:
            b=deepcopy(a);b[key]=value
            with self.subTest(key=key):self.assertEqual(assess_rf_goal_pair(a,b)['status'],'UNVERIFIED')
        b=deepcopy(a);b.pop('quantities')
        self.assertEqual(assess_rf_goal_pair(a,b)['status'],'UNVERIFIED')

    def test_orders_require_both_complete_scalar_gates_and_reject_forged_pass(self):
        orders=reference_orders();before=deepcopy(orders);r=assess_rf_goal_orders(orders)
        self.assertEqual(r['status'],'PASS');self.assertEqual(orders,before)
        # The grids have different sample counts; only their scalar errors are compared.
        bad=deepcopy(orders);bad[1]['accuracy']['relative_errors']['electric_relative_l2']=.02
        with self.assertRaises(ValueError):assess_rf_goal_orders(bad)
        for malformed in (orders[:1],orders[::-1],orders+orders[:1], [dict(orders[0],order=True),orders[1]]):
            with self.assertRaises(ValueError):assess_rf_goal_orders(malformed)
        a=data();a['weights'][0]=0
        r=assess_efficiency_samples(a['fields'],a['fields'],a['weights'],a['axis_ez'],a['axis_ez'],a['axis_weights'],a['quantities'],a['quantities'],a['peak_intervals'])
        self.assertEqual(assess_rf_goal_orders([dict(order=16,accuracy=r),orders[1]])['status'],'UNVERIFIED')
        failed=reference_orders(.02);result=assess_rf_goal_orders(failed)
        self.assertEqual(result['status'],'FAIL');self.assertIsNotNone(result['order_error_differences'])


class RFGoalBranchTests(unittest.TestCase):
    def test_rejected_probe_and_local_step_cannot_form_two_uniform_edges(self):
        events,observations=fixture(['initial','uniform_probe','rf_local','uniform_probe','uniform_probe'],
                                    [None,0,0,2,3],[True,False,True,True,True])
        observations[0]['reference_orders']=reference_orders(.02)
        before=deepcopy((events,observations));r=assess_rf_goal_history(events[:4],observations[:4])
        self.assertEqual(r['first_rejected_accuracy_hit_index'],1)
        self.assertEqual(r['first_accuracy_hit_index'],2)
        self.assertIsNone(r['confirmed_accuracy_hit_index'])
        r=assess_rf_goal_history(events,observations)
        self.assertEqual(r['confirmed_accuracy_hit_index'],4)
        self.assertEqual(r['confirmation_event_indices'],[2,3,4])
        self.assertEqual((events,observations),before)

    def test_all_three_accepted_events_and_both_edges_need_every_gate(self):
        events,observations=fixture(['initial','uniform_confirmation','uniform_confirmation'],[None,0,1])
        self.assertEqual(assess_rf_goal_history(events,observations)['status'],'CONFIRMED')
        for index in range(3):
            bad=deepcopy(observations);bad[index]['reference_orders']=reference_orders(.02)
            self.assertIsNone(assess_rf_goal_history(events,bad)['confirmed_accuracy_hit_index'])
            bad=deepcopy(observations);bad[index]['source_domain_identity_status']='UNVERIFIED'
            self.assertIsNone(assess_rf_goal_history(events,bad)['confirmed_accuracy_hit_index'])
        for index in (1,2):
            bad=deepcopy(observations);bad[index]['parent_change']['orders']=reference_orders(.02)
            self.assertIsNone(assess_rf_goal_history(events,bad)['confirmed_accuracy_hit_index'])
        bad=deepcopy(events);bad[1]['quadrature_check']['passed']=False
        self.assertIsNone(assess_rf_goal_history(bad,observations)['confirmed_accuracy_hit_index'])

    def test_wrong_parent_reordered_or_missing_observation_and_bool_index_are_rejected(self):
        events,observations=fixture(['initial','uniform_probe','rf_local'],[None,0,0],[True,False,True])
        changes=[(1,'parent_event_index',1),(2,'parent_event_index',1),(2,'index',True),
                 (2,'refinement_kind','uniform_probe'),(1,'accepted',1),(2,'current_mode_ids',['target','target'])]
        for index,key,value in changes:
            bad=deepcopy(events);bad[index][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):assess_rf_goal_history(bad,observations)
        bad=deepcopy(observations);bad[2]['parent_change']['parent_event_index']=1
        with self.assertRaises(ValueError):assess_rf_goal_history(events,bad)
        with self.assertRaises(ValueError):assess_rf_goal_history(events,observations[:2])
        with self.assertRaises(ValueError):assess_rf_goal_history(events,observations[::-1])
        with self.assertRaises(ValueError):assess_rf_goal_history(events,tuple(observations))

    def test_unresolved_individual_ids_stay_unverified_and_never_confirm(self):
        events,observations=fixture(['initial','uniform_probe'],[None,0])
        events[1].update(status='UNVERIFIED',accepted=False,current_mode_ids=[None,None,'guard-3'],
                         mode_index=None,quadrature_check=None)
        observations[1]['source_domain_identity_status']='UNVERIFIED'
        r=assess_rf_goal_history(events,observations)
        self.assertEqual(r['status'],'NOT_CONFIRMED')
        self.assertFalse(r['events'][1]['independent_accuracy_passed'])
        self.assertIsNone(r['first_rejected_accuracy_hit_index'])
        self.assertEqual(events[1]['current_mode_ids'],[None,None,'guard-3'])
        bad=deepcopy(events);bad[1]['status']='PASS'
        with self.assertRaises(ValueError):assess_rf_goal_history(bad,observations)
        bad=deepcopy(events);bad[1]['current_mode_ids']=['guard-3',None,'guard-3']
        with self.assertRaises(ValueError):assess_rf_goal_history(bad,observations)

    def test_native_terminal_label_and_surface_progress_do_not_certify_physics(self):
        events,observations=fixture(['initial','uniform_probe','uniform_probe'],[None,0,1])
        events[-1]['native_status']='TARGETS_MET';events[-1]['uniform_confirmations']=2
        observations[0]['reference_orders']=reference_orders(.02)
        self.assertEqual(assess_rf_goal_history(events,observations)['status'],'NOT_CONFIRMED')
        observations[0]['reference_orders']=reference_orders()
        observations[1]['parent_change']['orders']=reference_orders(.02)
        self.assertEqual(assess_rf_goal_history(events,observations)['status'],'NOT_CONFIRMED')
        empty=assess_rf_goal_history([],[])
        self.assertIsNone(empty['first_accuracy_hit_index']);self.assertEqual(empty['status'],'NOT_CONFIRMED')


if __name__=='__main__':unittest.main()
