# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import unittest
from unittest.mock import patch
import numpy as np
from scripts.validate_coaxial import radial_roots
from superfish_ng.constants import C0
from superfish_ng.hphi_project import HphiProject
from superfish_ng.curved_hphi_shape_tuning import CurvedHphiShapeLaw
from superfish_ng.hphi_tracking import HphiTrackingControls
from test_curved_hphi_tracking_crossing import coax
from test_curved_hphi_tuning import request as base_request


def request(exact=False,shear=0.):
    kr=radial_roots(.0625,.125,1)[0];length=np.pi/kr
    p=HphiProject(coax(length,shear=shear));points=p.case.geometry.points_rz_m
    displacement=np.column_stack((np.zeros(len(points)),points[:,1]))
    q=base_request();upper=1.2 if exact else 1.18
    q.update(project=p.to_dict(),shape_law=CurvedHphiShapeLaw(1.,displacement.tolist(),'transport_on_axis').to_dict(),
        bounds=[.8,upper],target_hz=float(C0/(2*length*((.8+upper)/2))),initial_ids=['radial','TEM'],mode_id='TEM')
    q['controls']['relative_cluster_gap']=.04
    q['identity_recovery']=dict(anchor_selection='latest_resolved_trial',controls=HphiTrackingControls().to_dict())
    return q


class CurvedHphiTuneRecoveryTests(unittest.TestCase):
    def test_actual_analytic_tem_recovery_and_future_anchor_refusal(self):
        from superfish_ng.curved_hphi_tuning import run_curved_hphi_tune,_recover_trial
        q=request();run=run_curved_hphi_tune(q)
        self.assertEqual(run.report['status'],'TUNED',run.report['decision'])
        trials=run.report['trials'];self.assertEqual(len(trials),4)
        self.assertEqual([t['parent_index'] for t in trials[2:]],[0,2])
        self.assertEqual([t['identity_recovery']['anchor_trial_index'] for t in trials[2:]],[1,2])
        for t,s in zip(trials,run.solutions):
            self.assertAlmostEqual(t['frequency_hz']/(C0/(2*s.case.length_m)),1.,delta=1e-3)
            actual=s.coefficients[:,t['current_mode_ids'].index('TEM')]
            exact=np.cos(np.pi*s.space.dof_points[:,1]/s.case.length_m);mass=s.mass
            overlap=abs(actual@(mass@exact))/np.sqrt((actual@(mass@actual))*(exact@(mass@exact)))
            self.assertGreater(overlap,.999)
        for t in trials[2:]:
            self.assertEqual(t['tracking']['current_mode_ids'],[None,None])
            self.assertEqual(t['identity_recovery']['status'],'PASS')
        bad=deepcopy(q);bad['identity_recovery'].update(anchor_selection='fixed_trial',anchor_trial_index=2)
        with patch('superfish_ng.curved_hphi_tuning._compare',side_effect=AssertionError('future anchor comparison')):
            result=_recover_trial(bad,trials[:2],run.trial_records[:2],run.solutions[:2],
                run.trial_records[2],run.solutions[2],trials[2],trials[2]['tracking'])
        self.assertEqual(result['status'],'UNVERIFIED');self.assertIn('earlier',result['stop_reason'])

    def test_exact_degeneracy_remains_unverified(self):
        from superfish_ng.curved_hphi_tuning import run_curved_hphi_tune
        q=request(exact=True);q['identity_recovery']['controls']['relative_cluster_gap']=0.
        run=run_curved_hphi_tune(q);last=run.report['trials'][-1]
        self.assertEqual(run.report['status'],'UNVERIFIED')
        self.assertIsNone(last['frequency_hz']);self.assertIsNone(last['target_error_hz'])
        self.assertEqual(last['identity_recovery']['status'],'UNVERIFIED')

    def test_genuinely_curved_recovery_keeps_original_tem_like_field(self):
        from superfish_ng.curved_hphi_tuning import run_curved_hphi_tune
        from superfish_ng.curved_hphi import solve_curved_hphi
        shear=1/64;q=request(shear=shear);q['bounds']=[.8,1.12]
        # Conservatively group a wider neighborhood; anchor controls remain unchanged.
        q['controls']['relative_cluster_gap']=.06
        middle=q['bounds'][0]/2+q['bounds'][1]/2
        project=HphiProject.from_dict(q['project']);law=CurvedHphiShapeLaw.from_dict(q['shape_law'])
        target=solve_curved_hphi(law.apply(project,middle).project.case)
        root_length=np.pi/radial_roots(.0625,.125,1)[0]
        r,z=target.space.dof_points.T;expected=np.cos(np.pi*(z-middle*shear*r*r)/(root_length*middle))
        overlaps=[]
        for actual in target.coefficients.T:
            overlaps.append(abs(actual@(target.mass@expected))/np.sqrt((actual@(target.mass@actual))*(expected@(target.mass@expected))))
        self.assertGreater(max(overlaps),.999)
        # The curved frequency is an independent FEM target, not the exact straight TEM formula.
        q['target_hz']=float(target.frequencies_hz[int(np.argmax(overlaps))])
        run=run_curved_hphi_tune(q)
        self.assertEqual(run.report['status'],'TUNED',run.report['decision'])
        trials=run.report['trials']
        self.assertEqual([t['identity_recovery']['anchor_trial_index'] for t in trials[2:]],[1,2])
        for trial,s in zip(trials,run.solutions):
            length=root_length*trial['value'];r,z=s.space.dof_points.T
            # Independent straight TEM pulled through the declared small shear;
            # an approximate physical comparison, never an eigensolve substitute.
            expected=np.cos(np.pi*(z-trial['value']*shear*r*r)/length)
            actual=s.coefficients[:,trial['current_mode_ids'].index('TEM')];mass=s.mass
            overlap=abs(actual@(mass@expected))/np.sqrt((actual@(mass@actual))*(expected@(mass@expected)))
            self.assertGreater(overlap,.999)
            self.assertAlmostEqual(trial['frequency_hz']/(C0/(2*length)),1.,delta=1e-3)
            g=s.case.geometry;nv=len(g.base_mesh.points_rz_m)
            self.assertGreater(np.max(abs(g.points_rz_m[nv:]-g.base_mesh.points_rz_m[g.edge_vertices].mean(axis=1))),0.)
