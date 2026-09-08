# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng import Case,solve
from superfish_ng.fem import triangle_quadrature
from superfish_ng.high_order import basis_p2
from superfish_ng.mesh import element_geometry
from superfish_ng.mesh_input import mesh_to_dict
from superfish_ng.marked_refinement import refine_marked_cells
from superfish_ng.nested_affine_tracking import track_nested_affine_modes,_mass_features
from superfish_ng.mode_tracking import track_sampled_mode_subspaces
from superfish_ng.saved_mode_tracking import build_saved_mode_tracking,replay_mode_tracking
from superfish_ng.io import save_run

CONTROLS=dict(mapping='nested_affine',minimum_overlap=.95,minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)


class NestedAffineTrackingTests(unittest.TestCase):
    def pair(self,order=2):
        case=Case(((0.,.1),(.2,.1)),nr=4,nz=5,modes=2,element_order=order)
        a=solve(case);a.case=case;marked=[3,14,25]
        refinement=refine_marked_cells(case,a.mesh,marked);b=solve(case,mesh_data=mesh_to_dict(refinement.mesh));b.case=case
        return case,a,b,marked,refinement.prolongation

    def test_mass_features_match_independent_polynomial_quadrature(self):
        for order in (1,2):
            _,a,b,_,p=self.pair(order)
            x=np.column_stack((p@a.u,b.u));x/=np.max(abs(x),axis=0)
            features,scale=_mass_features(x,b.mass)
            vertices,det,grad=element_geometry(b.mesh);dofs=b.space.cell_dofs if order==2 else b.mesh.triangles
            gram=np.zeros((4,4))
            for n,w in triangle_quadrature(order=6):
                values=basis_p2(n,grad)[0] if order==2 else n
                fields=np.einsum('tjm,j->tm',x[dofs],values)
                radius=vertices[:,:,0]@n
                gram+=fields.T@((w*det*radius**3)[:,None]*fields)
            np.testing.assert_allclose(features.T@features*scale,gram,rtol=1e-11,atol=np.max(abs(gram))*1e-13)

    def test_same_fields_sign_permutation_and_rank_deficiency(self):
        _,a,b,marked,p=self.pair();b.u=(p@a.u)[:,::-1]*[-3.,7.]
        result=track_nested_affine_modes(a,b,['A','B'],marked_cells=marked,**CONTROLS)
        self.assertEqual(result['current_mode_ids'],['B','A'])
        self.assertEqual(result['status'],'PASS')
        a.u[:,1]=a.u[:,0];b.u=p@a.u
        result=track_nested_affine_modes(a,b,['A','B'],marked_cells=marked,**dict(CONTROLS,relative_cluster_gap=.9))
        self.assertEqual(result['status'],'UNVERIFIED')

    def test_native_saved_replay_and_wrong_ancestry_rejection(self):
        case,a,b,marked,_=self.pair()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);save_run(case,a,root/'old');save_run(case,b,root/'new')
            pair=build_saved_mode_tracking(dict(schema_version=1,previous_run=str(root/'old'),current_run=str(root/'new'),previous_ids=['A','B'],controls=dict(CONTROLS,marked_cells=marked)))
            self.assertEqual(pair['status'],'PASS');self.assertEqual(replay_mode_tracking(pair),pair)
            bad=deepcopy(pair);bad['request']['controls']['marked_cells']=[0]
            with self.assertRaises(ValueError):replay_mode_tracking(bad)
        for marks in ([],[True],[0,0],[10000]):
            with self.assertRaises(ValueError):track_nested_affine_modes(a,b,['A','B'],marked_cells=marks,**CONTROLS)
        with self.assertRaises(ValueError):track_nested_affine_modes(a,b,['A','B'],marked_cells=marked,**dict(CONTROLS,minimum_assignment_margin=-1.))
        c=replace(b,mesh=a.mesh);c.case=case
        with self.assertRaises(ValueError):track_nested_affine_modes(a,c,['A','B'],marked_cells=marked,**CONTROLS)
