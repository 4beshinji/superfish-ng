# SPDX-License-Identifier: Apache-2.0
"""Declared Hphi tune recovery separates search/refinement parents and anchors."""
from copy import deepcopy
import unittest
import numpy as np
from scripts.validate_coaxial import radial_roots
from superfish_ng.coaxial import CoaxialCase
from superfish_ng.constants import C0
from superfish_ng.hphi_tracking import HphiTrackingControls
from superfish_ng.hphi_tuning import run_hphi_tune, assess_hphi_tune, validate_hphi_tune
from test_hphi_tuning import request as base_request


def request(*, recovery=True, exact_degeneracy=False):
    kr=radial_roots(.0625,.125,1)[0]
    length=np.pi/kr
    upper=1.2 if exact_degeneracy else 1.18
    target_length=(.8+upper)*length/2
    q=base_request(CoaxialCase(.0625,.125,length,nr=8,nz=8,modes=3,quadrature_order=12))
    q.update(schema_version=2,parameter='length_m',mapping=dict(kind='coaxial_dimensions'),
             bounds=[.8*length,upper*length],target_hz=C0/(2*target_length),
             initial_ids=['radial','TEM'],mode_id='TEM')
    # The ordinary path conservatively groups this nearby pair. Recovery uses
    # independently declared controls plus the same finite spectral diagnostics.
    q['controls']['relative_cluster_gap']=.04
    if recovery:
        q.update(schema_version=3,identity_recovery=dict(anchor_selection='latest_resolved_trial',
                  controls=HphiTrackingControls().to_dict()))
    return q


class HphiTuneRecoveryTests(unittest.TestCase):
    def test_independent_tem_recovery_for_search_and_final_refinement(self):
        ordinary=run_hphi_tune(request(recovery=False))
        self.assertEqual(ordinary.report['status'],'UNVERIFIED')
        self.assertEqual(len(ordinary.report['trials']),3)
        last=ordinary.report['trials'][-1]
        self.assertEqual(last['tracking']['status'],'PASS')
        self.assertFalse(last['tracking']['individual_ids_complete'])
        self.assertIsNone(last['frequency_hz'])
        run=run_hphi_tune(request())
        self.assertEqual(run.report['status'],'TUNED',run.report['decision'])
        trials=run.report['trials']
        self.assertEqual([t['phase'] for t in trials],['search','search','search','refinement'])
        self.assertEqual([t['parent_index'] for t in trials[2:]],[0,2])
        self.assertEqual([t['identity_recovery']['anchor_trial_index'] for t in trials[2:]],[1,2])
        for trial,solution in zip(trials,run.solutions):
            self.assertAlmostEqual(trial['frequency_hz']/(C0/(2*solution.case.length_m)),1.,delta=3e-4)
            mode=trial['current_mode_ids'].index('TEM')
            exact=np.cos(np.pi*solution.space.dof_points[:,1]/solution.case.length_m)
            actual=solution.coefficients[:,mode];mass=solution.mass
            overlap=abs(actual@(mass@exact))/np.sqrt((actual@(mass@actual))*(exact@(mass@exact)))
            self.assertGreater(overlap,.999)
        for trial in trials[2:]:
            self.assertEqual(trial['tracking']['current_mode_ids'],[None,None])
            self.assertEqual(trial['identity_recovery']['status'],'PASS')
            self.assertEqual(trial['current_mode_ids'],['radial','TEM'])
        fixed=request();fixed['identity_recovery'].update(anchor_selection='fixed_trial',anchor_trial_index=0)
        replay=assess_hphi_tune(fixed,run.solutions)
        self.assertEqual(replay.report['status'],'TUNED')
        self.assertEqual([t['identity_recovery']['anchor_trial_index'] for t in replay.report['trials'][2:]],[0,0])
        self.assertEqual([t['frequency_hz'] for t in replay.report['trials']],[t['frequency_hz'] for t in trials])

    def test_strict_policy_and_future_anchor_do_not_evaluate_unconfirmed_frequency(self):
        q=request();validate_hphi_tune(q)
        for policy in ({'anchor_selection':'nearest_frequency','controls':q['controls']},
                       {'anchor_selection':'fixed_trial','anchor_trial_index':True,'controls':q['controls']},
                       {'anchor_selection':'latest_resolved_trial','anchor_trial_index':0,'controls':q['controls']},
                       {'anchor_selection':'fixed_trial','anchor_trial_index':q['max_trials'],'controls':q['controls']}):
            bad=deepcopy(q);bad['identity_recovery']=policy
            with self.assertRaises(ValueError):validate_hphi_tune(bad)
        q['identity_recovery'].update(anchor_selection='fixed_trial',anchor_trial_index=2)
        result=run_hphi_tune(q).report
        self.assertEqual(result['status'],'UNVERIFIED')
        self.assertIsNone(result['trials'][-1]['frequency_hz'])
        self.assertIn('earlier',result['trials'][-1]['identity_recovery']['stop_reason'])

    def test_true_degeneracy_is_not_resolved_by_changing_cluster_gap(self):
        q=request(exact_degeneracy=True)
        q['identity_recovery']['controls']['relative_cluster_gap']=0.
        result=run_hphi_tune(q).report
        self.assertEqual(result['status'],'UNVERIFIED')
        last=result['trials'][-1]
        self.assertIsNone(last['frequency_hz'])
        self.assertIsNone(last['target_error_hz'])
        self.assertEqual(last['identity_recovery']['status'],'UNVERIFIED')

    def test_inherited_guard_does_not_call_anchor_recovery(self):
        from unittest.mock import patch
        q=request();q['controls']['relative_cluster_gap']=.9
        with patch('superfish_ng.hphi_tuning_identity_recovery.recover_tune_trial',side_effect=AssertionError('guard bypass')):
            result=run_hphi_tune(q).report
        self.assertEqual(result['status'],'UNVERIFIED')
        self.assertEqual(len(result['trials']),1)
        self.assertIsNone(result['trials'][0]['identity_recovery'])
        self.assertIsNone(result['trials'][0]['frequency_hz'])

    def test_uniform_scale_does_not_request_unnecessary_recovery(self):
        q=base_request();q.update(schema_version=3,identity_recovery=dict(
            anchor_selection='latest_resolved_trial',controls=HphiTrackingControls().to_dict()))
        result=run_hphi_tune(q).report
        self.assertEqual(result['status'],'TUNED')
        self.assertEqual(result['scope'],'vacuum_uniform_scale')
        self.assertEqual(result['parameter_unit'],'dimensionless')
        self.assertTrue(all(t['identity_recovery'] is None for t in result['trials']))

    def test_geometry_protocol_and_recovery_budget_preserve_base_projects(self):
        from superfish_ng.hphi_tuning import trial_hphi_project
        from test_hphi_shape_tuning import mesh_request
        for base in (base_request(),request(recovery=False),mesh_request(),mesh_request(axis=True)):
            q=deepcopy(base);q.update(schema_version=3,identity_recovery=dict(
                anchor_selection='latest_resolved_trial',controls=HphiTrackingControls().to_dict()))
            value=sum(q['bounds'])/2
            for phase in ('search','refinement'):
                self.assertEqual(trial_hphi_project(q,value,phase).to_dict(),trial_hphi_project(base,value,phase).to_dict())
            for name,value in (('max_dofs',2),('max_gram_modes',1)):
                bad=deepcopy(q);bad['identity_recovery']['controls'][name]=value
                with self.assertRaises(ValueError):validate_hphi_tune(bad)
