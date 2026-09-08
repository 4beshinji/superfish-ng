# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import unittest
import numpy as np
from superfish_ng import solve
from superfish_ng.curved_refinement_steps import CurvedRefinementStep as Step
from test_curved_reflection import half_case


class CurvedRFGoalIndicatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case=replace(half_case('z_min','electric_symmetry'),modes=2,quadrature_order=12)
        cls.a=solve(cls.case)
        cls.b=solve(replace(cls.case,curved_refinement_steps=(Step('uniform'),)))

    def test_local_global_action_and_named_conventions(self):
        from superfish_ng.curved_rf_goal_indicator import curved_rf_goal_indicator
        r=curved_rf_goal_indicator(self.a,self.b)
        self.assertEqual(len(r['parent_priority_ohm']),len(self.a.space.geometry.cell_nodes))
        self.assertLess(r['local_global_relative_difference'],1e-11)
        np.testing.assert_array_equal(r['parent_priority_ohm'],abs(np.array(r['parent_signed_accelerator_ohm'])))
        np.testing.assert_array_equal(r['parent_signed_circuit_ohm'],np.array(r['parent_signed_accelerator_ohm'])/2)
        self.assertAlmostEqual(sum(r['parent_signed_accelerator_ohm']),r['estimated_accelerator_change_ohm'],places=12)
        self.assertLess(abs(r['removed_parent_action_ohm']),1e-7)
        self.assertIsNone(r['physical_error_bound'])

    def test_sign_amplitude_invariance_and_actual_mode_tracking(self):
        from superfish_ng.curved_rf_goal_indicator import curved_rf_goal_indicator
        r=curved_rf_goal_indicator(self.a,self.b,mode=1)
        flipped=replace(self.b,u=self.b.u*[-3.,7.])
        other=curved_rf_goal_indicator(replace(self.a,u=-2*self.a.u),flipped,mode=1)
        self.assertEqual(other['current_mode_index'],1)
        np.testing.assert_allclose(other['parent_signed_accelerator_ohm'],r['parent_signed_accelerator_ohm'],rtol=2e-8,atol=1e-10)

    def test_invalid_history_and_mode_are_rejected(self):
        from superfish_ng.curved_rf_goal_indicator import curved_rf_goal_indicator
        for mode in (True,-1,2):
            with self.assertRaises(ValueError):curved_rf_goal_indicator(self.a,self.b,mode=mode)
        with self.assertRaisesRegex(ValueError,'extend'):curved_rf_goal_indicator(self.a,self.a)
        wrong=replace(self.b,u=self.b.u[:,::-1])
        with self.assertRaisesRegex(ValueError,'eigenpair'):curved_rf_goal_indicator(self.a,wrong)
        marked=solve(replace(self.case,curved_refinement_steps=(Step('marked',(0,),5.),)))
        with self.assertRaisesRegex(ValueError,'one uniform'):curved_rf_goal_indicator(self.a,marked)

    def test_selected_parent_cells_drive_real_local_refinement(self):
        from superfish_ng.curved_rf_goal_indicator import curved_rf_goal_indicator
        r=curved_rf_goal_indicator(self.a,self.b,bulk_fraction=.5)
        selected=r['marked_parent_cells'];scores=np.asarray(r['parent_priority_ohm'])
        self.assertTrue(selected)
        self.assertGreaterEqual(float(sum(scores[selected])),.5*float(sum(scores)))
        if len(selected)>1:self.assertLess(float(sum(scores[selected[:-1]])),.5*float(sum(scores)))
        local=solve(replace(self.case,curved_refinement_steps=(Step('marked',tuple(selected),5.),)))
        self.assertGreater(len(local.space.geometry.cell_nodes),len(self.a.space.geometry.cell_nodes))
        self.assertLess(local.frequencies_hz[0],self.a.frequencies_hz[0])
        for fraction in (True,0,1.1,float('nan')):
            with self.assertRaisesRegex(ValueError,'fraction'):curved_rf_goal_indicator(self.a,self.b,bulk_fraction=fraction)
