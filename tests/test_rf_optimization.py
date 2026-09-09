# SPDX-License-Identifier: Apache-2.0
import json
import math
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from superfish_ng import Case
from superfish_ng.conics import LineSegment,EllipseArc
from superfish_ng.curved_contour import CurvedContour
from superfish_ng.mesh_controls import ContourMeshControls
from superfish_ng.project import Project
from superfish_ng.rf_optimization import (validate_optimization_request,execute_rf_optimization,
    replay_rf_optimization,read_rf_optimization)
from superfish_ng.rf_optimization_search import decision,improves,restoration_value


def request():
    r=.08
    case=Case((),name='synthetic_optimization',curved_contour=CurvedContour(
        (LineSegment((0,0),(2*r,0)),EllipseArc((r,0),(r,r),0,math.pi)),('axis','pec'),1e-14),
        curve_chord_tolerance_m=.0016,contour_mesh=ContourMeshControls(.064,min_angle_deg=5.),
        element_order=2,geometry_order=2,modes=1)
    return dict(schema_version=1,project=Project(case).to_dict(),
        variables=[dict(name=name,lower=1.,upper=1.01,initial=1.,step=.01,tolerance=.01)
                   for name in ('radial_scale','axial_scale')],
        criteria=dict(schema_version=1,objective=dict(quantity='frequency_hz',direction='minimize'),
            constraints=[dict(quantity='r_over_q_accelerator_ohm',lower=1.,upper=1e4),
                         dict(quantity='epk_over_eacc',upper=100.)]),
        constraint_scales=dict(r_over_q_accelerator_ohm=100.,epk_over_eacc=1.),
        objective_improvement=1.,max_trials=4,initial_ids=['fundamental'],mode_id='fundamental',
        controls=dict(mapping='affine_remesh',sample_order=3,minimum_overlap=.98,
            minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8),rf_coordinates='axial')


def assessment(value=10.,violation=0.):
    return dict(status='CRITERIA_MET' if not violation else 'CONSTRAINTS_VIOLATED',refinement_status='TARGETS_MET',
        constraints=[dict(constraint=dict(quantity='epk_over_eacc',upper=100.),observed_envelope=[100.+violation]*2)],
        objective=dict(eligible_value=value if not violation else None))


class RFOptimizationTests(unittest.TestCase):
    def test_failed_solve_is_terminal_recorded_and_not_an_objective(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'failed'
            with patch('superfish_ng.rf_optimization.execute_project',side_effect=RuntimeError('injected solver failure')):
                with self.assertRaisesRegex(RuntimeError,'injected solver failure'):
                    execute_rf_optimization(request(),out)
            failure=json.loads((out/'failure-001.json').read_text())
            self.assertEqual(failure['status'],'FAILED');self.assertEqual(failure['fem_calls_attempted'],1)
            self.assertFalse(list(out.glob('checkpoint-*.json')))

    def test_two_variable_poll_reserved_final_and_no_false_optimum(self):
        r=request();trials=[]
        for value in (10.,8.,6.,5.):
            next_trial=decision(r,trials)['next_trial'];trials.append(dict(**next_trial,assessment=assessment(value)))
        self.assertEqual([t['values'] for t in trials],[[1.,1.],[1.01,1.],[1.01,1.01],[1.01,1.01]])
        self.assertEqual([t['phase'] for t in trials],['search','search','search','final'])
        result=decision(r,trials);self.assertEqual(result['status'],'SEARCH_COMPLETE')
        self.assertEqual(result['search_stop'],'TRIAL_LIMIT')
        self.assertEqual(result['incumbent_index'],2)
        trials[-1]['assessment']=None
        self.assertEqual(decision(r,trials)['status'],'FINAL_UNVERIFIED')

    def test_restoration_units_and_unverified_cannot_win(self):
        r=request();bad=assessment(violation=4.);better=assessment(violation=2.)
        self.assertTrue(improves(r,better,bad));self.assertTrue(improves(r,assessment(),bad))
        self.assertFalse(improves(r,bad,assessment()))
        better['status']='UNVERIFIED'
        self.assertIsNone(restoration_value(r,better));self.assertFalse(improves(r,better,bad))
        a=assessment(violation=4.);score=restoration_value(r,a)
        a['constraints'][0]['observed_envelope']=[104000.,104000.]
        a['constraints'][0]['constraint']['upper']=100000.;r['constraint_scales']['epk_over_eacc']=1000.
        self.assertEqual(restoration_value(r,a),score)

    def test_exhausted_poll_and_strict_request(self):
        r=request();r['max_trials']=20;trials=[]
        for _ in range(20):
            state=decision(r,trials)
            if state['status']!='PAUSED':break
            trials.append(dict(**state['next_trial'],assessment=assessment()))
        self.assertEqual(state['search_stop'],'PARAMETER_LIMIT')
        self.assertEqual(state['status'],'SEARCH_COMPLETE')
        validate_optimization_request(r)
        for change in ({'max_trials':True},{'schema_version':2},{'variables':[]},{'constraint_scales':{}},
                       {'objective_improvement':-1.},{'rf_coordinates':'auto'}):
            with self.subTest(change=change),self.assertRaises(ValueError):validate_optimization_request(dict(r,**change))

    def test_actual_fem_pause_resume_final_refinement_and_replay(self):
        r=request();r['max_trials']=3
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);first=execute_rf_optimization(r,root/'first',max_new_trials=1)
            self.assertEqual(first['status'],'PAUSED');self.assertEqual(first['completed_fem_solves'],3)
            final=execute_rf_optimization(r,root/'resume',checkpoint=first)
            self.assertEqual(final['status'],'SEARCH_COMPLETE');self.assertEqual(final['completed_fem_solves'],9)
            self.assertEqual(final['trials'][-1]['assessment']['assessment']['rows'][0]['refinement_level'],1)
            self.assertEqual(final['trial_sources_sha256'][0],first['trial_sources_sha256'][0])
            self.assertEqual(read_rf_optimization(root/'resume/checkpoint-003.json'),final)
            modified=deepcopy(first);modified['trials'][0]['values'][0]=1.001
            with self.assertRaisesRegex(ValueError,'differs'):replay_rf_optimization(modified)
            with self.assertRaisesRegex(ValueError,'PAUSED'):execute_rf_optimization(r,root/'terminal',checkpoint=final)
            self.assertFalse((root/'terminal').exists())
