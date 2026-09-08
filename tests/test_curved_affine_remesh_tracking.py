# SPDX-License-Identifier: Apache-2.0
"""Independent polynomial, volume and native FEM affine-pullback invariants."""
import copy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng import Case,solve
from superfish_ng.affine_remesh_tracking import track_affine_remesh_modes
from superfish_ng.curved_same_domain_tracking import track_curved_same_domain_modes
from superfish_ng.quadratic_geometry import QuadraticTriangle
from superfish_ng.io import save_run
from superfish_ng.saved_mode_tracking import save_mode_tracking,read_mode_tracking
from superfish_ng.mode_tracking_history import start_mode_history,extend_mode_history

AFFINE=dict(radial_scale=1.2,axial_scale=.8,axial_shear=0.)
CONTROLS=dict(mapping='affine_remesh',affine_map=AFFINE,sample_order=5,minimum_overlap=.98,
    minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)

class CurvedAffineRemeshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw=Case.load('examples/curved_ellipse.json').to_dict()
        raw['mesh']['geometry_order']=2;raw['mesh']['contour_mesh'].update(max_edge_m=.08,min_angle_deg=5.)
        raw['geometry']['chord_tolerance_m']=.008
        cls.case=Case.from_dict(raw);cls.old=solve(cls.case)
        cls.fine=solve(replace(cls.case,curved_refinement_levels=1))
        new=copy.deepcopy(raw);g=new['geometry']
        g['curves'][0]['end_zr_m'][0]*=.8;g['curves'][1]['center_zr_m'][0]*=.8
        g['curves'][1]['semiaxes_m'][0]*=.8;g['curves'][1]['semiaxes_m'][1]*=1.2
        g['chord_tolerance_m']*=1.2;new['mesh']['curved_refinement_levels']=1
        mesh=copy.deepcopy(cls.old.source_mesh_data);mesh['points']=(np.array(mesh['points'])*[1.2,.8]).tolist()
        cls.new=solve(Case.from_dict(new),mesh_data=mesh)

    def test_polynomial_field_and_volume_under_scale_and_shear(self):
        # Synthetic field adapter test, not an eigenmode or saved native solve.
        for shear in (0.,.15):
            g=self.fine.space.geometry;points=g.points_rz_m@np.array([[1.2,shear],[0.,.8]])
            geometry=replace(g,points_rz_m=points,local_maps=tuple(QuadraticTriangle(points[n]) for n in g.cell_nodes))
            current=replace(self.fine,space=replace(self.fine.space,geometry=geometry),u=(-3*(1+g.points_rz_m[:,1]))[:,None])
            previous=replace(self.old,u=(1+self.old.space.geometry.points_rz_m[:,1])[:,None])
            report=track_affine_remesh_modes(previous,current,['polynomial'],**dict(CONTROLS,affine_map=dict(AFFINE,axial_shear=shear)))
            self.assertEqual(report['status'],'PASS')
            self.assertAlmostEqual(report['matches'][0]['minimum_principal_overlap'],1.,places=13)
            p=report['physical_mapping'];v=p['physical_axisymmetric_volumes_m3'];ref=p['reference_axisymmetric_volumes_m3']
            self.assertAlmostEqual(v[1]/v[0],1.2**2*.8,places=13)
            self.assertAlmostEqual(ref[1]/ref[0],1.,places=13)

    def test_native_forward_inverse_and_saved_history(self):
        inverse=dict(radial_scale=1/1.2,axial_scale=1/.8,axial_shear=0.)
        forward=track_affine_remesh_modes(self.old,self.new,['A'],**CONTROLS)
        backward=track_affine_remesh_modes(self.new,self.old,['A'],**dict(CONTROLS,affine_map=inverse))
        self.assertEqual(forward['status'],'PASS');self.assertEqual(backward['status'],'PASS')
        self.assertAlmostEqual(forward['matches'][0]['minimum_principal_overlap'],backward['matches'][0]['minimum_principal_overlap'],places=13)
        self.assertNotEqual(*forward['physical_mapping']['triangle_counts'])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,s in [('a',self.old),('b',self.new)]:save_run(s.case,s,root/name)
            pair=save_mode_tracking(dict(schema_version=1,previous_run='a',current_run='b',previous_ids=['A'],controls=CONTROLS),root/'pair.json',base_directory=root)
            self.assertEqual(read_mode_tracking(root/'pair.json'),pair)
            history=extend_mode_history(start_mode_history(pair),dict(current_run='a',controls=dict(CONTROLS,affine_map=inverse)),base_directory=root)
            self.assertEqual(history['status'],'PASS');self.assertEqual(history['current_mode_ids'],['A'])

    def test_identity_agrees_with_same_domain(self):
        identity=dict(radial_scale=1.,axial_scale=1.,axial_shear=0.)
        actual=track_affine_remesh_modes(self.old,self.fine,['A'],**dict(CONTROLS,affine_map=identity))
        controls={k:v for k,v in CONTROLS.items() if k!='affine_map'};controls['mapping']='curved_same_domain'
        expected=track_curved_same_domain_modes(self.old,self.fine,['A'],**controls)
        np.testing.assert_allclose(actual['overlap_matrix'],expected['overlap_matrix'],rtol=0,atol=2e-15)

    def test_wrong_map_midpoint_reprojection_and_unsupported_boundary_fail(self):
        with self.assertRaisesRegex(ValueError,'boundary'):
            track_affine_remesh_modes(self.old,self.new,['A'],**dict(CONTROLS,affine_map=dict(AFFINE,radial_scale=1.1)))
        g=self.new.space.geometry;points=g.points_rz_m.copy()
        mid=g.boundary_nodes[np.flatnonzero(self.new.space.boundary_tags=='pec')[0],2];points[mid,0]+=1e-5
        changed=replace(self.new,space=replace(self.new.space,geometry=replace(g,points_rz_m=points)))
        with self.assertRaisesRegex(ValueError,'quadratic boundary'):
            track_affine_remesh_modes(self.old,changed,['A'],**CONTROLS)
        reprojected=solve(replace(self.new.case,curve_chord_tolerance_m=.0024,contour=None,curved_refinement_levels=0))
        with self.assertRaisesRegex(ValueError,'quadratic boundary'):
            track_affine_remesh_modes(self.old,reprojected,['A'],**CONTROLS)
        space=replace(self.new.space,boundary_tags=np.full(len(g.boundary_nodes),'magnetic_symmetry'))
        with self.assertRaisesRegex(ValueError,'PEC'):
            track_affine_remesh_modes(self.old,replace(self.new,space=space),['A'],**CONTROLS)
        with self.assertRaisesRegex(ValueError,'curved'):
            track_affine_remesh_modes(self.old,object(),['A'],**CONTROLS)
