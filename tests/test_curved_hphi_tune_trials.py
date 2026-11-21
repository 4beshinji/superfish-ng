# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import unittest
from unittest.mock import patch
import numpy as np
from test_curved_hphi_field_overlap import case
from superfish_ng.hphi_project import HphiProject
from superfish_ng.curved_hphi_shape_tuning import CurvedHphiShapeLaw
from superfish_ng.curved_hphi_comparison import CurvedHphiComparisonDomain,build_curved_hphi_comparison
from superfish_ng.curved_hphi_fem import curved_hphi_matrices
from superfish_ng.axis_hphi import AxisAccelerationPath


class CurvedHphiTuneTrialTests(unittest.TestCase):
    def test_two_levels_keep_root_charts_mass_and_acceleration(self):
        for axis in (False,True):
            p=HphiProject(case(axis,scale=.7))
            if axis:p=replace(p,case=replace(p.case,acceleration=AxisAccelerationPath(.02,.1,.8,.05)))
            g=p.case.geometry;law=CurvedHphiShapeLaw(1.,g.points_rz_m.tolist(),'transport_on_axis')
            from superfish_ng.curved_hphi_tune_trials import build_curved_hphi_tune_trial
            search=build_curved_hphi_tune_trial(p,law,1.3,phase='search',refinement_levels=2)
            fine=build_curved_hphi_tune_trial(p,law,1.3,phase='refinement',refinement_levels=2)
            reference=search.project.case.geometry
            self.assertEqual(len(fine.project.case.geometry.cell_nodes),16*len(reference.cell_nodes))
            self.assertEqual(fine.reference_geometry.to_dict(),reference.to_dict())
            self.assertEqual(fine.project.case.acceleration,search.project.case.acceleration)
            self.assertAlmostEqual(fine.project.case.geometry.volume_m3/g.volume_m3,1.3**3,places=11)
            d=CurvedHphiComparisonDomain(reference,reference,'same_vacuum',restriction_policy='binary64_roundoff')
            result=build_curved_hphi_comparison(reference,fine.project.case.geometry,d,current_cells=fine.native_cells)
            self.assertEqual(result.report['base_reference_areas'],[[1,2]]*len(reference.cell_nodes))
            _,_,mc,_=curved_hphi_matrices(reference);_,_,mf,_=curved_hphi_matrices(fine.project.case.geometry)
            transfer=fine.prolongation
            self.assertLess(np.linalg.norm((transfer.T@mf@transfer-mc).toarray())/np.linalg.norm(mc.toarray()),1e-10)
            np.testing.assert_allclose(transfer@np.ones(mc.shape[0]),1.,rtol=0,atol=1e-14)

    def test_budget_is_checked_before_shape_or_refinement(self):
        from superfish_ng.curved_hphi_tune_trials import build_curved_hphi_tune_trial
        p=HphiProject(case());law=CurvedHphiShapeLaw(1.,p.case.geometry.points_rz_m.tolist(),'transport_on_axis')
        with patch.object(CurvedHphiShapeLaw,'apply',side_effect=AssertionError('shape must not run')):
            for name,value in (('max_triangles',1),('max_dofs',1),('max_pair_tests',1),('refinement_levels',True),('phase','unknown')):
                with self.assertRaises(ValueError):build_curved_hphi_tune_trial(p,law,1.,**{name:value})

    def test_actual_hole_search_to_refinement_uses_original_fields(self):
        from superfish_ng.curved_hphi_tune_trials import build_curved_hphi_tune_trial,curved_hphi_trial_comparison
        from superfish_ng.curved_hphi import solve_curved_hphi
        from superfish_ng.curved_hphi_tracking import track_curved_hphi_modes
        p=HphiProject(case(n=2));g=p.case.geometry
        law=CurvedHphiShapeLaw(1.,g.points_rz_m.tolist(),'transport_on_axis')
        a=build_curved_hphi_tune_trial(p,law,1.05)
        b=build_curved_hphi_tune_trial(p,law,1.05,phase='refinement')
        solutions=[solve_curved_hphi(t.project.case) for t in (a,b)]
        before=[s.coefficients.copy() for s in solutions]
        q=curved_hphi_trial_comparison(a,b,previous_mode_ids=['first','second'])
        report=track_curved_hphi_modes(*solutions,q)
        self.assertEqual(report['status'],'PASS',report['verification_reasons'])
        self.assertEqual(report['current_mode_ids'],['first','second'])
        self.assertEqual(len(q.current_comparison_geometry.cell_nodes),16*len(g.cell_nodes))
        self.assertEqual(q.domain.current.to_dict(),a.reference_geometry.to_dict())
        for s,old in zip(solutions,before):np.testing.assert_array_equal(s.coefficients,old)
