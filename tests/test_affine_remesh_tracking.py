# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng import Case,solve
from superfish_ng.affine_remesh_tracking import track_affine_remesh_modes,validate_affine_map
from superfish_ng.io import save_run
from superfish_ng.saved_mode_tracking import save_mode_tracking,read_mode_tracking,validate_tracking_controls
from superfish_ng.mode_tracking_history import start_mode_history,extend_mode_history

AFFINE=dict(radial_scale=1.2,axial_scale=.8,axial_shear=0.)
CONTROLS=dict(mapping='affine_remesh',affine_map=AFFINE,sample_order=3,minimum_overlap=.98,
    minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)

class AffineRemeshTests(unittest.TestCase):
    def pair(self,order=2):
        a=Case(((0.,.1),(.08,.1)),nr=6,nz=7,modes=1,element_order=order)
        b=replace(a,profile=((0.,.12),(.064,.12)),nr=9,nz=11)
        return [(c,solve(c)) for c in (a,b)]

    def test_native_anisotropic_remesh_and_inverse_reciprocity(self):
        (_,a),(_,b)=self.pair();forward=track_affine_remesh_modes(a,b,['A'],**CONTROLS)
        inverse=dict(radial_scale=1/1.2,axial_scale=1/.8,axial_shear=0.)
        backward=track_affine_remesh_modes(b,a,['A'],**dict(CONTROLS,affine_map=inverse))
        self.assertEqual(forward['status'],'PASS');self.assertEqual(backward['status'],'PASS')
        self.assertAlmostEqual(forward['matches'][0]['minimum_principal_overlap'],backward['matches'][0]['minimum_principal_overlap'],places=14)
        self.assertAlmostEqual(forward['physical_mapping']['physical_volume_ratio'],1.2**2*.8,places=14)
        self.assertNotEqual(*forward['physical_mapping']['triangle_counts'])

    def test_exact_polynomial_pullback_is_independent_of_mesh(self):
        for order in (1,2):
            (_,a),(_,b)=self.pair(order)
            x=a.space.dof_points if order==2 else a.mesh.points
            y=b.space.dof_points if order==2 else b.mesh.points
            a.u[:,0]=1+x[:,1];b.u[:,0]=-3*(1+y[:,1]/.8)
            result=track_affine_remesh_modes(a,b,['polynomial'],**CONTROLS)
            self.assertAlmostEqual(result['matches'][0]['minimum_principal_overlap'],1.,places=14)

    def test_strict_map_rejects_wrong_shape_axis_orientation_and_overflow(self):
        for values in (dict(AFFINE,radial_scale=0),dict(AFFINE,axial_scale=-1),dict(AFFINE,axial_shear=True),
                       dict(AFFINE,axial_shear=float('nan')),dict(AFFINE,radial_scale=1e300),dict(AFFINE,translation=1),{}):
            with self.assertRaises(ValueError):validate_affine_map(values)
        (_,a),(_,b)=self.pair()
        with self.assertRaisesRegex(ValueError,'boundary'):track_affine_remesh_modes(a,b,['A'],**dict(CONTROLS,affine_map=dict(AFFINE,radial_scale=1.1)))

    def test_identity_map_preserves_same_domain_overlap(self):
        (_,a),(_,b)=self.pair()
        from superfish_ng.same_domain_tracking import track_same_domain_modes
        b=solve(Case(((0.,.1),(.08,.1)),nr=9,nz=11,modes=1,element_order=2))
        identity=dict(radial_scale=1.,axial_scale=1.,axial_shear=0.)
        result=track_affine_remesh_modes(a,b,['A'],**dict(CONTROLS,affine_map=identity))
        plain={k:v for k,v in CONTROLS.items() if k!='affine_map'};plain['mapping']='same_domain'
        expected=track_same_domain_modes(a,b,['A'],**plain)
        self.assertEqual(result['overlap_matrix'],expected['overlap_matrix'])

    def test_saved_history_replays_declared_forward_and_inverse_maps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,(case,solution) in zip(('a','b'),self.pair()):save_run(case,solution,root/name)
            request=dict(schema_version=1,previous_run='a',current_run='b',previous_ids=['A'],controls=CONTROLS)
            pair=save_mode_tracking(request,root/'pair.json',base_directory=root)
            self.assertEqual(read_mode_tracking(root/'pair.json'),pair)
            inverse=dict(radial_scale=1/1.2,axial_scale=1/.8,axial_shear=0.)
            history=extend_mode_history(start_mode_history(pair),dict(current_run='a',controls=dict(CONTROLS,affine_map=inverse)),base_directory=root)
            self.assertEqual(history['status'],'PASS');self.assertEqual(history['current_mode_ids'],['A'])

    def test_saved_controls_require_map_and_reject_unrelated_fields(self):
        validate_tracking_controls(CONTROLS)
        for changed in ({k:v for k,v in CONTROLS.items() if k!='affine_map'},dict(CONTROLS,vertex_pairs=[]),dict(CONTROLS,sample_order=33)):
            with self.assertRaises(ValueError):validate_tracking_controls(changed)
