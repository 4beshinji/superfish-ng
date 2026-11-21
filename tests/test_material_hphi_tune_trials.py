# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from unittest.mock import patch
import unittest
import numpy as np
from superfish_ng.material_hphi_tune_trials import build_material_hphi_tune_trial,material_hphi_trial_comparison
from superfish_ng.material_hphi_shape_tuning import MaterialHphiShapeLaw
from superfish_ng.material_hphi_fem import material_hphi_matrices
from superfish_ng.material_hphi import MaterialHphiCase,solve_material_hphi
from superfish_ng.material_hphi_tracking import track_material_hphi_modes
from superfish_ng.hphi_project import HphiProject
from test_material_hphi_comparison import partition


class MaterialHphiTuneTrialTests(unittest.TestCase):
    def test_two_levels_preserve_materials_and_scalar_mass(self):
        for axis in (False,True):
            root=HphiProject(MaterialHphiCase(partition(1,1,axis),modes=3))
            law=MaterialHphiShapeLaw('uniform_scale')
            a=build_material_hphi_tune_trial(root,law,1.5)
            b=build_material_hphi_tune_trial(root,law,1.5,phase='refinement',refinement_levels=2)
            old=a.project.case.partition;new=b.project.case.partition
            self.assertEqual(len(new.mesh.triangles),16*len(old.mesh.triangles))
            self.assertEqual(b.reference_partition.to_dict(),old.to_dict())
            np.testing.assert_array_equal(new.cell_region_indices,old.cell_region_indices[b.root_cells])
            _,k,m,_=material_hphi_matrices(old);_,kf,mf,_=material_hphi_matrices(new)
            for source,fine in ((k,kf),(m,mf)):
                difference=(b.prolongation.T@fine@b.prolongation-source).toarray()
                self.assertLess(np.linalg.norm(difference)/np.linalg.norm(source.toarray()),1e-10)
            self.assertFalse(b.root_cells.flags.writeable);self.assertFalse(b.prolongation.data.flags.writeable)
            self.assertEqual(root.to_dict(),b.root_project.to_dict())

    def test_budget_precedes_shape_and_strict_original_binding(self):
        root=HphiProject(MaterialHphiCase(partition(),modes=3));law=MaterialHphiShapeLaw('uniform_scale')
        with patch.object(MaterialHphiShapeLaw,'apply',side_effect=AssertionError('budget first')):
            for options in ({'max_dofs':1},{'max_triangles':1},{'max_candidate_tests':1},{'refinement_levels':True},{'phase':'unknown'}):
                with self.assertRaises(ValueError):build_material_hphi_tune_trial(root,law,1.,**options)
        a=build_material_hphi_tune_trial(root,law,1.)
        other=HphiProject(replace(root.case,name='different root'))
        b=build_material_hphi_tune_trial(other,law,1.)
        with self.assertRaises(ValueError):material_hphi_trial_comparison(a,b,previous_mode_ids=['a','b'])

    def test_nonuniform_axis_trial_preserves_acceleration_and_tracks_final(self):
        from superfish_ng.rf_materials import RFMaterialPartition,LinearRFMaterial
        from superfish_ng.axis_hphi import AxisAccelerationPath
        p=partition(1,1,True);p=RFMaterialPartition(p.mesh,[LinearRFMaterial('a',1.,1.),p.materials[1]],p.regions)
        root=HphiProject(MaterialHphiCase(p,modes=3,acceleration=AxisAccelerationPath(.005,.025,.7,.07)))
        points=p.mesh.points_rz_m;shift=np.column_stack((np.zeros(len(points)),points[:,1]))
        shift[(points[:,0]==1/32)&(points[:,1]==1/32),1]+=1/512
        law=MaterialHphiShapeLaw('general_piecewise_affine',1.,shift)
        a=build_material_hphi_tune_trial(root,law,1.)
        b=build_material_hphi_tune_trial(root,law,1.125,phase='refinement')
        path=b.project.case.acceleration
        np.testing.assert_allclose([path.z_start_m,path.z_end_m,path.phase_origin_m],1.125*np.array([.005,.025,.07]),rtol=1e-14)
        self.assertEqual(path.beta,.7)
        expected=law.apply(root,1.125).project.case.acceleration;self.assertEqual(path,expected)
        q=material_hphi_trial_comparison(a,b,previous_mode_ids=['a','b'])
        left,right=[solve_material_hphi(t.project.case) for t in (a,b)]
        report=track_material_hphi_modes(left,right,q)
        self.assertEqual(report['status'],'PASS',report['verification_reasons'])
        self.assertEqual(report['current_mode_ids'],['a','b'])
        with self.assertRaises(ValueError):material_hphi_trial_comparison(a,b,previous_mode_ids=['a','b'],max_sample_points=1)

    def test_actual_search_to_final_refinement_tracks_original_modes(self):
        root=HphiProject(MaterialHphiCase(partition(1,1),modes=3));law=MaterialHphiShapeLaw('uniform_scale')
        a=build_material_hphi_tune_trial(root,law,1.5)
        b=build_material_hphi_tune_trial(root,law,1.5,phase='refinement')
        left,right=[solve_material_hphi(t.project.case) for t in (a,b)]
        request=material_hphi_trial_comparison(a,b,previous_mode_ids=['a','b'])
        result=track_material_hphi_modes(left,right,request)
        self.assertEqual(result['status'],'PASS',result['verification_reasons'])
        self.assertEqual(result['current_mode_ids'],['a','b'])
        self.assertGreater(len(request.current_resolution.current_partition.mesh.triangles),len(b.project.case.partition.mesh.triangles))


if __name__=='__main__':unittest.main()
