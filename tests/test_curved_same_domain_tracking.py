# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng import Case,solve
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution
from superfish_ng.curved_refinement import refine_curved_space
from superfish_ng.curved_same_domain_tracking import compare_quadratic_boundaries,track_curved_same_domain_modes
from superfish_ng.saved_mode_tracking import save_mode_tracking,read_mode_tracking,validate_tracking_controls

CONTROLS=dict(mapping='curved_same_domain',sample_order=3,minimum_overlap=.98,minimum_assignment_margin=.05,
    relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)

class CurvedSameDomainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data=Case.load('examples/curved_ellipse.json').to_dict()
        data['mesh'].update(geometry_order=2);data['mesh']['contour_mesh'].update(max_edge_m=.08,min_angle_deg=5.)
        data['geometry']['chord_tolerance_m']=.008
        cls.case=Case.from_dict(data);cls.coarse=solve(cls.case)
        cls.fine=solve(replace(cls.case,curved_refinement_levels=1))

    def test_boundary_polynomial_coincidence_survives_subdivision(self):
        result=compare_quadratic_boundaries(self.coarse,self.fine)
        self.assertLessEqual(result['maximum_coefficient_distance_m'],result['roundoff_tolerance_m'])
        self.assertEqual(result['common_interval_count'],len(self.fine.space.geometry.boundary_nodes))

    def test_identical_prolonged_field_has_unit_overlap(self):
        refinement=refine_curved_space(self.coarse.space)
        exact=replace(self.coarse,space=refinement.space,u=refinement.prolongation@self.coarse.u)
        result=track_curved_same_domain_modes(self.coarse,exact,['same field'],**CONTROLS)
        self.assertEqual(result['status'],'PASS')
        self.assertAlmostEqual(result['matches'][0]['minimum_principal_overlap'],1.,places=13)
        a,b=result['physical_mapping']['axisymmetric_volumes_m3'];self.assertAlmostEqual(a/b,1.,places=6)

    def test_matching_endpoints_do_not_hide_a_different_quadratic_edge(self):
        geometry=self.coarse.space.geometry;points=geometry.points_rz_m.copy()
        edge=geometry.boundary_nodes[np.flatnonzero(self.coarse.space.boundary_tags=='pec')[0]]
        points[edge[2],0]+=1e-5
        np.testing.assert_array_equal(points[geometry.boundary_nodes[:,:2]],geometry.points_rz_m[geometry.boundary_nodes[:,:2]])
        changed=replace(self.coarse,space=replace(self.coarse.space,geometry=replace(geometry,points_rz_m=points)))
        with self.assertRaisesRegex(ValueError,'quadratic boundary differs'):compare_quadratic_boundaries(self.coarse,changed)

    def test_same_analytic_curve_with_reprojection_is_rejected(self):
        other=solve(replace(self.case,curve_chord_tolerance_m=.004,contour=None))
        with self.assertRaisesRegex(ValueError,'quadratic boundary'):compare_quadratic_boundaries(self.coarse,other)

    def test_native_fem_reciprocity_and_saved_replay(self):
        forward=track_curved_same_domain_modes(self.coarse,self.fine,['A'],**CONTROLS)
        backward=track_curved_same_domain_modes(self.fine,self.coarse,['A'],**CONTROLS)
        self.assertEqual(forward['status'],'PASS');self.assertEqual(backward['status'],'PASS')
        self.assertAlmostEqual(forward['matches'][0]['minimum_principal_overlap'],backward['matches'][0]['minimum_principal_overlap'],places=13)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,s in [('a',self.coarse),('b',self.fine)]:save_run(s.case,s,root/name)
            request=dict(schema_version=1,previous_run='a',current_run='b',previous_ids=['A'],controls=CONTROLS)
            pair=save_mode_tracking(request,root/'pair.json',base_directory=root)
            self.assertEqual(read_mode_tracking(root/'pair.json'),pair);self.assertEqual(pair['status'],'PASS')

    def test_unsupported_geometry_controls_and_boundary_tags_fail(self):
        validate_tracking_controls(CONTROLS)
        with self.assertRaises(ValueError):validate_tracking_controls(dict(CONTROLS,sample_order=33))
        with self.assertRaises(ValueError):validate_tracking_controls(dict(CONTROLS,affine_map={}))
        with self.assertRaisesRegex(ValueError,'curved'):compare_quadratic_boundaries(self.coarse,object())
        space=replace(self.fine.space,boundary_tags=np.full(len(self.fine.space.boundary_tags),'magnetic_symmetry'))
        with self.assertRaisesRegex(ValueError,'PEC'):compare_quadratic_boundaries(self.coarse,replace(self.fine,space=space))
