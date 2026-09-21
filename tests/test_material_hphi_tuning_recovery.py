# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from unittest.mock import patch
import unittest
import numpy as np
from scripts.validate_coaxial import radial_roots
from superfish_ng.constants import C0
from superfish_ng.material_hphi import MaterialHphiCase
from superfish_ng.material_hphi_shape_tuning import MaterialHphiShapeLaw
from superfish_ng.material_hphi_tuning import run_material_hphi_tune,material_hphi_tune_decision,_recover_trial
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_tracking import HphiTrackingControls
from test_material_hphi_tracking_crossing import material
from test_material_hphi_tuning import request as base_request


def request(exact=False,n=6):
    length=np.pi/radial_roots(.0625,.125,1)[0]
    p=HphiProject(MaterialHphiCase(material(length,n=n),modes=3));points=p.case.partition.mesh.points_rz_m
    displacement=np.column_stack((np.zeros(len(points)),points[:,1]))
    q=base_request();upper=1.2 if exact else 1.18
    q.update(project=p.to_dict(),shape_law=MaterialHphiShapeLaw('general_piecewise_affine',1.,displacement).to_dict(),
        bounds=[.8,upper],target_hz=float(C0/(12*length*((.8+upper)/2))),initial_ids=['radial','TEM'],mode_id='TEM',
        frequency_tolerance_hz=float(C0/(12*length)*.001),mesh_frequency_tolerance_hz=float(C0/(12*length)*.001))
    q['controls']['relative_cluster_gap']=.04
    q['identity_recovery']=dict(anchor_selection='latest_resolved_trial',controls=HphiTrackingControls().to_dict())
    return q


class MaterialHphiTuneRecoveryTests(unittest.TestCase):
    def test_actual_material_tem_anchor_recovery_and_separate_final_gate(self):
        q=request();run=run_material_hphi_tune(q);trials=run.report['trials']
        self.assertEqual(run.report['status'],'TUNED',run.report['decision']);self.assertEqual(len(trials),4)
        self.assertEqual([t['parent_index'] for t in trials[2:]],[0,2])
        self.assertEqual([t['identity_recovery']['anchor_trial_index'] for t in trials[2:]],[1,2])
        for t,s in zip(trials,run.solutions):
            self.assertAlmostEqual(t['frequency_hz']/(C0/(12*s.case.length_m)),1.,delta=1e-3)
            actual=s.coefficients[:,t['current_mode_ids'].index('TEM')]
            exact=np.cos(np.pi*s.space.dof_points[:,1]/s.case.length_m);mass=s.mass
            overlap=abs(actual@(mass@exact))/np.sqrt((actual@(mass@actual))*(exact@(mass@exact)))
            self.assertGreater(overlap,.999)
        for t in trials[2:]:
            self.assertEqual(t['tracking']['current_mode_ids'],[None,None]);self.assertEqual(t['identity_recovery']['status'],'PASS')
        # Reuse the measured final trials; only tighten the mesh gate.
        strict=deepcopy(q);difference=abs(trials[-1]['frequency_hz']-trials[-2]['frequency_hz'])
        self.assertGreater(difference,0.);strict['mesh_frequency_tolerance_hz']=difference/2
        decision=material_hphi_tune_decision(strict,trials)
        self.assertEqual(decision['status'],'REFINEMENT_FAILED');self.assertTrue(decision['refined_target_met']);self.assertFalse(decision['mesh_difference_met'])
        bad=deepcopy(q);bad['identity_recovery'].update(anchor_selection='fixed_trial',anchor_trial_index=2)
        with patch('superfish_ng.material_hphi_tuning._compare',side_effect=AssertionError('future anchor')):
            result=_recover_trial(bad,trials[:2],run.trial_records[:2],run.solutions[:2],run.trial_records[2],run.solutions[2],trials[2],trials[2]['tracking'])
        self.assertEqual(result['status'],'UNVERIFIED');self.assertIn('earlier',result['stop_reason'])

    def test_true_material_degeneracy_cannot_be_recovered(self):
        q=request(exact=True,n=4);q['identity_recovery']['controls']['relative_cluster_gap']=0.
        run=run_material_hphi_tune(q);last=run.report['trials'][-1]
        self.assertEqual(run.report['status'],'UNVERIFIED')
        self.assertIsNone(last['frequency_hz']);self.assertIsNone(last['target_error_hz'])
        self.assertEqual(last['identity_recovery']['status'],'UNVERIFIED')


if __name__=='__main__':unittest.main()
