# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng import Case,solve
from superfish_ng.io import save_run
from superfish_ng.same_domain_tracking import track_same_domain_modes
from superfish_ng.saved_mode_tracking import save_mode_tracking,read_mode_tracking,validate_tracking_controls
from superfish_ng.mode_tracking_history import start_mode_history,extend_mode_history

CONTROLS=dict(mapping='same_domain',sample_order=3,minimum_overlap=.98,minimum_assignment_margin=.05,
    relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)

class SameDomainTrackingTests(unittest.TestCase):
    def pair(self,order=2):
        case=Case(((0.,.1),(.08,.1)),nr=5,nz=6,modes=2,element_order=order)
        a=solve(case);a.case=case
        case=replace(case,nr=7,nz=9);b=solve(case);b.case=case
        return a,b

    def test_exact_polynomial_field_and_axisymmetric_volume_on_unrelated_meshes(self):
        a,b=self.pair(1)
        for s in (a,b):
            s.u[:,:]=1+s.mesh.points[:,1,None]
            s.u=s.u[:,:1];s.frequencies_hz=s.frequencies_hz[:1]
        result=track_same_domain_modes(a,b,['polynomial'],**CONTROLS)
        self.assertEqual(result['status'],'PASS')
        self.assertAlmostEqual(result['matches'][0]['minimum_principal_overlap'],1.,places=14)
        for volume in result['physical_mapping']['axisymmetric_volumes_m3']:
            self.assertAlmostEqual(volume,np.pi*.1**2*.08,places=15)
        self.assertNotEqual(*result['physical_mapping']['triangle_counts'])

    def test_native_fem_reciprocity_and_p1_p2_comparison(self):
        a,_=self.pair(1);_,b=self.pair(2)
        forward=track_same_domain_modes(a,b,['A','B'],**CONTROLS)
        backward=track_same_domain_modes(b,a,['A','B'],**CONTROLS)
        self.assertEqual(forward['status'],'PASS');self.assertEqual(backward['status'],'PASS')
        np.testing.assert_allclose(forward['overlap_matrix'],np.array(backward['overlap_matrix']).T,atol=2e-14)

    def test_changed_boundary_and_boundary_tags_are_rejected(self):
        a,b=self.pair();b=solve(replace(b.case,profile=((0.,.10001),(.08,.10001))))
        with self.assertRaisesRegex(ValueError,'boundary'):track_same_domain_modes(a,b,['A','B'],**CONTROLS)
        a,b=self.pair();b.mesh.boundary_tags[0]='magnetic_symmetry'
        with self.assertRaisesRegex(ValueError,'PEC'):track_same_domain_modes(a,b,['A','B'],**CONTROLS)

    def test_strict_order_budget_and_curved_rejection(self):
        a,b=self.pair()
        for value in (True,1,33):
            with self.assertRaises(ValueError):track_same_domain_modes(a,b,['A','B'],**dict(CONTROLS,sample_order=value))
        large=solve(replace(b.case,nr=20,nz=20))
        with self.assertRaisesRegex(ValueError,'samples'):track_same_domain_modes(a,large,['A','B'],**dict(CONTROLS,sample_order=32))
        from superfish_ng.curved_solution import CurvedSolution
        with self.assertRaisesRegex(ValueError,'straight'):track_same_domain_modes(a,object.__new__(CurvedSolution),['A','B'],**CONTROLS)

    def test_saved_replay_and_history_across_mesh_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);a,b=self.pair()
            for name,s in [('a',a),('b',b)]:save_run(s.case,s,root/name)
            request=dict(schema_version=1,previous_run='a',current_run='b',previous_ids=['A','B'],controls=CONTROLS)
            document=save_mode_tracking(request,root/'pair.json',base_directory=root)
            self.assertEqual(read_mode_tracking(root/'pair.json'),document)
            history=extend_mode_history(start_mode_history(document),dict(current_run='a',controls=CONTROLS),base_directory=root)
            self.assertEqual(history['status'],'PASS');self.assertEqual(history['current_mode_ids'],['A','B'])

    def test_saved_controls_reject_unrelated_mapping_fields(self):
        validate_tracking_controls(CONTROLS)
        with self.assertRaises(ValueError):validate_tracking_controls(dict(CONTROLS,vertex_pairs=[]))
        with self.assertRaises(ValueError):validate_tracking_controls(dict(CONTROLS,sample_order=33))
