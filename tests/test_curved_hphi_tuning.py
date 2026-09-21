# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import unittest
from unittest.mock import patch
import numpy as np
from test_curved_hphi_field_overlap import case
from superfish_ng.hphi_project import HphiProject
from superfish_ng.curved_hphi import solve_curved_hphi
from superfish_ng.curved_hphi_shape_tuning import CurvedHphiShapeLaw
from superfish_ng.hphi_tracking import HphiTrackingControls


def request(n=2):
    p=HphiProject(case(n=n));law=CurvedHphiShapeLaw(1.,p.case.geometry.points_rz_m.tolist(),'transport_on_axis')
    frequency=float(solve_curved_hphi(p.case).frequencies_hz[0])
    return dict(format='superfish_ng_curved_hphi_tune',schema_version=1,project=p.to_dict(),
        parameter='deformation',shape_law=law.to_dict(),bounds=[1.,1.2],target_hz=frequency/1.1,
        frequency_tolerance_hz=frequency*.001,mesh_frequency_tolerance_hz=frequency*.001,
        parameter_tolerance=1e-6,max_trials=8,initial_ids=['first','second'],mode_id='first',
        controls=HphiTrackingControls().to_dict(),refinement_levels=1,max_triangles=10000,max_dofs=10000,
        max_sample_points=2000000,identity_recovery=None)


class CurvedHphiTuningTests(unittest.TestCase):
    def test_strict_request_and_preflight_budgets(self):
        q=request()
        from superfish_ng.curved_hphi_tuning import validate_curved_hphi_tune
        validate_curved_hphi_tune(q)
        for key,value in (('schema_version',True),('parameter','energy'),('bounds',[1.,False]),('initial_ids',['a','a']),
                          ('mode_id','missing'),('extra',1),('target_hz',np.float64(1.)),('max_sample_points',1),
                          ('max_triangles',1),('max_dofs',1),('refinement_levels',9)):
            bad=deepcopy(q);bad[key]=value
            with self.assertRaises(ValueError):validate_curved_hphi_tune(bad)
        bad=deepcopy(q);bad['controls']['max_dofs']=1
        with patch.object(CurvedHphiShapeLaw,'apply',side_effect=AssertionError('must reject before shape')):
            with self.assertRaises(ValueError):validate_curved_hphi_tune(bad)
        for policy in ({'anchor_selection':'guess','controls':q['controls']},
                       {'anchor_selection':'fixed_trial','anchor_trial_index':True,'controls':q['controls']},
                       {'anchor_selection':'latest_resolved_trial','anchor_trial_index':0,'controls':q['controls']}):
            bad=deepcopy(q);bad['identity_recovery']=policy
            with self.assertRaises(ValueError):validate_curved_hphi_tune(bad)

    def test_actual_hole_tune_and_separate_refinement_gate(self):
        from superfish_ng.curved_hphi_tuning import run_curved_hphi_tune,curved_hphi_tune_decision
        q=request();before=deepcopy(q);run=run_curved_hphi_tune(q)
        self.assertEqual(run.report['status'],'REFINEMENT_FAILED',run.report['decision'])
        self.assertFalse(run.report['decision']['refined_target_met'])
        self.assertFalse(run.report['decision']['mesh_difference_met'])
        trials=run.report['trials']
        self.assertEqual([t['value'] for t in trials],[1.,1.2,1.1,1.1])
        self.assertEqual([t['parent_index'] for t in trials],[None,0,0,2])
        original=trials[0]['frequency_hz']
        for t in trials[:3]:self.assertAlmostEqual(t['frequency_hz']*t['value']/original,1.,delta=1e-9)
        self.assertTrue(all(t['tracking']['individual_ids_complete'] for t in trials))
        self.assertEqual(q,before)
        self.assertEqual(run.projects[2].case.acceleration,run.projects[3].case.acceleration)
        # Isolate the two acceptance gates on the same measured final trial.
        altered=deepcopy(trials);altered[-1]['target_error_hz']=0.
        decision=curved_hphi_tune_decision(q,altered)
        self.assertEqual(decision['status'],'REFINEMENT_FAILED')
        self.assertTrue(decision['refined_target_met']);self.assertFalse(decision['mesh_difference_met'])

    def test_unverified_guard_never_evaluates_frequency_or_recovers(self):
        from superfish_ng.curved_hphi_tuning import run_curved_hphi_tune
        q=request();q['controls']['relative_cluster_gap']=.9
        q['identity_recovery']=dict(anchor_selection='latest_resolved_trial',controls=HphiTrackingControls().to_dict())
        with patch('superfish_ng.curved_hphi_tuning._recover_trial',side_effect=AssertionError('guard bypass')):
            run=run_curved_hphi_tune(q)
        self.assertEqual(run.report['status'],'UNVERIFIED')
        self.assertEqual(len(run.report['trials']),1)
        self.assertIsNone(run.report['trials'][0]['frequency_hz'])
        self.assertIsNone(run.report['trials'][0]['identity_recovery'])

    def test_public_reader_and_reassessment_reject_modified_originals(self):
        from dataclasses import replace
        from pathlib import Path
        import json,tempfile
        from superfish_ng.curved_hphi_tuning import read_curved_hphi_tune_request,assess_curved_hphi_tune,trial_curved_hphi_project
        q=request()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'request.json';p.write_text(json.dumps(q))
            self.assertEqual(read_curved_hphi_tune_request(p),q)
            p.write_text(json.dumps(q)[:-1]+',"max_trials":8}')
            with self.assertRaises(ValueError):read_curved_hphi_tune_request(p)
        empty=assess_curved_hphi_tune(q,[])
        self.assertEqual(empty.report['status'],'PAUSED');self.assertEqual(empty.solutions,())
        project=trial_curved_hphi_project(q,1.,'search');solution=solve_curved_hphi(project.case)
        for bad in (replace(solution,coefficients=solution.coefficients*1.01),
                    replace(solution,frequencies_hz=solution.frequencies_hz*1.01),{'frequency_hz':q['target_hz']}):
            with self.assertRaises(ValueError):assess_curved_hphi_tune(q,[bad])
        with self.assertRaises(ValueError):trial_curved_hphi_project(q,1.3,'search')

    def test_nonuniform_curved_hole_tune_preserves_explicit_geometry(self):
        from superfish_ng.curved_hphi_tuning import run_curved_hphi_tune
        q=request(n=5);q['bounds']=[1.,1.1];q['max_sample_points']=4000000
        p=HphiProject.from_dict(q['project']);g=p.case.geometry
        displacement=np.column_stack((np.zeros(len(g.points_rz_m)),g.points_rz_m[:,1]))
        law=CurvedHphiShapeLaw(1.,displacement.tolist(),'transport_on_axis');q['shape_law']=law.to_dict()
        target=law.apply(p,1.05).project
        q['target_hz']=float(solve_curved_hphi(target.case).frequencies_hz[0])
        run=run_curved_hphi_tune(q)
        self.assertEqual(run.report['status'],'TUNED',(run.report['decision'],
            [(t['value'],t['status'],t['tracking'].get('verification_reasons')) for t in run.report['trials']]))
        self.assertEqual([t['value'] for t in run.report['trials']],[1.,1.1,1.05,1.05])
        for t,project in zip(run.report['trials'],run.projects):
            self.assertAlmostEqual(project.case.geometry.volume_m3/g.volume_m3,t['value'],places=11)
            self.assertEqual(t['tracking']['physical_mapping']['previous_frequency_scale'],1.)
        self.assertEqual(run.trial_records[-1].reference_geometry.to_dict(),target.case.geometry.to_dict())
