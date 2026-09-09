# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng import solve
from superfish_ng.project import Project
from superfish_ng.curved_project_transform import transform_curved_project, relative_affine_map
from superfish_ng.curved_refinement_steps import CurvedRefinementStep
from superfish_ng.affine_remesh_tracking import track_affine_remesh_modes
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution
from superfish_ng.rf import quantities
from test_curve_partitions import partition_case


def mapping(a=1., c=1., b=0.):
    return dict(radial_scale=a, axial_scale=c, axial_shear=b)


class CurvedProjectTransformTests(unittest.TestCase):
    def test_same_source_mesh_and_uniform_history_affine_saved_tracking(self):
        case=replace(partition_case(),curved_refinement_levels=1)
        project=Project(case);before=project.to_dict();old=solve(case)
        target=transform_curved_project(project,mapping(2.,.5),rf_coordinates='axial')
        self.assertEqual(project.to_dict(),before)
        self.assertEqual(target.case.curve_segments_per_curve,(1,4))
        for name in ('triangles','boundary_edges','boundary_tags'):
            self.assertEqual(target.mesh_data[name],old.source_mesh_data[name])
        with patch('superfish_ng.curved_solution.make_mesh',side_effect=AssertionError('must use transported mesh')):
            new=solve(target.case,mesh_data=target.mesh_data)
        np.testing.assert_allclose(new.space.geometry.points_rz_m,old.space.geometry.points_rz_m*[2.,.5],rtol=0,atol=1e-15)
        report=track_affine_remesh_modes(old,new,['A'],mapping='affine_remesh',affine_map=mapping(2.,.5),sample_order=5,
            minimum_overlap=.8,minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)
        self.assertEqual(report['status'],'PASS')
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'project.json';target.save(file);loaded=Project.load(file)
            self.assertEqual(loaded.to_dict(),target.to_dict())
            save_run(loaded.case,new,Path(tmp)/'solution');saved=read_solution(Path(tmp)/'solution')
            np.testing.assert_array_equal(saved.space.geometry.points_rz_m,new.space.geometry.points_rz_m)

    def test_similarity_with_explicit_rf_lengths_and_fixed_physical_constraints(self):
        case=replace(partition_case(),active_length_m=.15,voltage_interval_m=(.02,.18),phase_origin_m=.03)
        project=Project(case);old=solve(case);rf=quantities(case,old)
        target=transform_curved_project(project,mapping(2.,2.),rf_coordinates='axial')
        new=solve(target.case,mesh_data=target.mesh_data);q=quantities(target.case,new)
        self.assertEqual(target.case.acceleration_parameters,(.3,(.04,.36),.06))
        self.assertEqual(target.case.contour_mesh,case.contour_mesh)
        self.assertEqual(target.case.curved_contour.minimum_gap_m,case.curved_contour.minimum_gap_m)
        for key in ('frequency_hz','r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm'):
            self.assertLess(abs(q[key]*(2 if key=='frequency_hz' else 1)/rf[key]-1),1e-11)
        fixed=transform_curved_project(project,mapping(2.,2.),rf_coordinates='fixed')
        self.assertEqual(fixed.case.acceleration_parameters,case.acceleration_parameters)
        with self.assertRaisesRegex(ValueError,'voltage_interval'):
            transform_curved_project(Project(partition_case()),mapping(1.,.5),rf_coordinates='fixed')

    def test_relative_mapping_composes_and_inverts_independent_points(self):
        rng=np.random.default_rng(103);points=rng.normal(size=(20,2))
        first=mapping(2.,.5,.3);second=mapping(.7,3.,-.4)
        def apply(p,m):return p@np.array([[m['radial_scale'],m['axial_shear']],[0,m['axial_scale']]])
        relative=relative_affine_map(first,second)
        np.testing.assert_allclose(apply(apply(points,first),relative),apply(points,second),rtol=1e-14,atol=1e-14)
        back=relative_affine_map(second,first)
        np.testing.assert_allclose(apply(apply(points,relative),back),points,rtol=1e-14,atol=1e-14)

    def test_invalid_maps_constraints_and_mutation_are_rejected(self):
        p=Project(partition_case())
        for m in (mapping(0.),mapping(b=float('inf')),dict(mapping(),unknown=1)):
            with self.subTest(m=m),self.assertRaises(ValueError):transform_curved_project(p,m,rf_coordinates='axial')
        with self.assertRaisesRegex(ValueError,'rf_coordinates'):transform_curved_project(p,mapping(),rf_coordinates='auto')
        with self.assertRaises(ValueError):transform_curved_project(p,mapping(b=.3),rf_coordinates='axial')
        valid=transform_curved_project(p,mapping(),rf_coordinates='axial');bad=deepcopy(valid)
        bad.mesh_data['boundary_tags'][0]='invalid'
        with self.assertRaises(ValueError):transform_curved_project(bad,mapping(),rf_coordinates='axial')
        curve=replace(p.case.curved_contour,minimum_meridional_radius_m=.03)
        constrained=Project(replace(p.case,curved_contour=curve))
        with self.assertRaisesRegex(ValueError,'minimum_meridional_radius'):
            transform_curved_project(constrained,mapping(.1,.1),rf_coordinates='axial')

    def test_marked_history_keeps_identity_and_refuses_changed_cell_correspondence(self):
        case=replace(partition_case(),curved_refinement_steps=(CurvedRefinementStep('marked',(0,),1.),))
        p=Project(case)
        same=transform_curved_project(p,mapping(),rf_coordinates='axial')
        self.assertEqual(same.case.curved_refinement_steps,case.curved_refinement_steps)
        with self.assertRaisesRegex(ValueError,'refinement changes connectivity'):
            transform_curved_project(p,mapping(2.,.5),rf_coordinates='axial')

    def test_reflected_projects_keep_both_symmetry_tags_and_axial_rf_interval(self):
        from test_curved_reflection import half_case
        from superfish_ng.jobs import execute_project
        for side in ('z_min','z_max'):
            for tag in ('electric_symmetry','magnetic_symmetry'):
                with self.subTest(side=side,tag=tag),tempfile.TemporaryDirectory() as tmp:
                    p=Project(half_case(side,tag),reflect_full=True)
                    target=transform_curved_project(p,mapping(2.,2.),rf_coordinates='axial')
                    self.assertTrue(target.reflect_full)
                    self.assertEqual(getattr(target.case,side),tag)
                    run=Path(tmp)/'run';execute_project(target,run)
                    full=read_solution(run/'solution')
                    self.assertAlmostEqual(full.case.length,.4)
                    self.assertEqual(full.case.acceleration_parameters,(.4,(0.,.4),0.))
                    explicit=transform_curved_project(replace(p,case=replace(p.case,phase_origin_m=.01)),
                        mapping(2.,2.),rf_coordinates='axial')
                    self.assertAlmostEqual(explicit.case.reflected_acceleration_parameters(side)['phase_origin_m'],
                        .22 if side=='z_min' else .02)
