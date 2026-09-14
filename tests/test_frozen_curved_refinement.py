# SPDX-License-Identifier: Apache-2.0
"""Material split identity, affine commutation and native saved reconstruction."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng import solve,make_mesh
from superfish_ng.project import Project
from superfish_ng.curved_refinement_steps import CurvedRefinementStep as Step
from superfish_ng.curved_split_pattern import CurvedSplitPattern
from superfish_ng.curved_space import case_curved_space
from superfish_ng.curved_saved import geometry_arrays
from superfish_ng.curved_fem import assemble_curved
from superfish_ng.curved_project_transform import transform_curved_project
from superfish_ng.frozen_curved_refinement import freeze_curved_refinement
from superfish_ng.mesh_input import mesh_from_dict
from superfish_ng.io import save_run
from superfish_ng.saved import read_solution
from test_curve_partitions import partition_case


def marked_project():
    return Project(replace(partition_case(),curved_refinement_steps=(Step('marked',(0,),1.),Step('uniform'),Step('marked',(0,),1.))))


def native_space(project):
    return case_curved_space(project.case,make_mesh(project.case) if project.mesh_data is None else mesh_from_dict(project.case,project.mesh_data))


class FrozenCurvedRefinementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=marked_project();cls.frozen=freeze_curved_refinement(cls.source)

    def test_capture_preserves_every_array_and_is_idempotent(self):
        before=self.source.to_dict()
        first,second=geometry_arrays(native_space(self.source)),geometry_arrays(native_space(self.frozen))
        for key in first:np.testing.assert_array_equal(first[key],second[key])
        self.assertEqual(freeze_curved_refinement(self.frozen).to_dict(),self.frozen.to_dict())
        self.assertEqual(self.source.to_dict(),before)
        self.assertTrue(all(step.split_pattern is not None for step in self.frozen.case.curved_refinement_steps if step.kind=='marked'))
        self.assertEqual(Project.from_dict(self.frozen.to_dict()).to_dict(),self.frozen.to_dict())

    def test_affine_restriction_commutes_and_retains_mass_measure(self):
        affine=dict(radial_scale=2.,axial_scale=.5,axial_shear=0.)
        with self.assertRaisesRegex(ValueError,'connectivity'):
            transform_curved_project(self.source,affine,rf_coordinates='axial')
        target=transform_curved_project(self.frozen,affine,rf_coordinates='axial')
        a,b=native_space(self.frozen),native_space(target)
        for key in ('cell_nodes','boundary_nodes','boundary_curve_indices'):
            np.testing.assert_array_equal(getattr(a.geometry,key),getattr(b.geometry,key))
        np.testing.assert_allclose(a.geometry.points_rz_m*[2.,.5],b.geometry.points_rz_m,rtol=0,atol=1e-15)
        # The exact r^3 dr dz mass measure scales by radial_scale^4*axial_scale.
        _,old=assemble_curved(a,quadrature_order=12);_,new=assemble_curved(b,quadrature_order=12)
        self.assertLess(np.linalg.norm((new-8*old).toarray())/np.linalg.norm((8*old).toarray()),1e-12)
        self.assertEqual(target.case.curved_refinement_steps,self.frozen.case.curved_refinement_steps)

    def test_reconstruction_rejects_wrong_topology_and_incomplete_choices(self):
        original=self.frozen.to_dict()
        bad=deepcopy(original);bad['case']['mesh']['curved_refinement_steps'][0]['split_pattern']['parent_topology_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'topology'):native_space(Project.from_dict(bad))
        bad=deepcopy(original);bad['case']['mesh']['curved_refinement_steps'].insert(0,{'kind':'uniform'})
        with self.assertRaisesRegex(ValueError,'topology'):native_space(Project.from_dict(bad))
        for key in ('split_edges','transition_diagonals'):
            bad=deepcopy(original);pattern=bad['case']['mesh']['curved_refinement_steps'][0]['split_pattern']
            if pattern[key]:pattern[key].pop()
            else:pattern[key]=[[0,0]]
            with self.subTest(key=key),self.assertRaises(ValueError):native_space(Project.from_dict(bad))

    def test_versioned_pattern_is_strict_and_bound_to_requested_cells(self):
        data=self.frozen.case.curved_refinement_steps[0].to_dict()
        for change in ({'schema_version':2},{'schema_version':True},{'unknown':1},{'marked_cells':[True]},
                       {'split_edges':[[0,True]]},{'transition_diagonals':[[0,2]]},{'parent_topology_sha256':'bad'}):
            bad=deepcopy(data);bad['split_pattern'].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):Step.from_dict(bad)
        bad=deepcopy(data);bad['marked_cells']=[1]
        with self.assertRaisesRegex(ValueError,'marked_cells'):Step.from_dict(bad)
        with self.assertRaises(ValueError):Step.from_dict(dict(kind='uniform',split_pattern=data['split_pattern']))
        with self.assertRaises(ValueError):Step.from_dict(dict(data,split_pattern=None))
        self.assertEqual(CurvedSplitPattern.from_dict(data['split_pattern']).to_dict(),data['split_pattern'])
        self.assertNotIn('split_pattern',Step('marked',(0,),1.).to_dict())

    def test_current_quality_and_triangle_budget_are_not_bypassed(self):
        steps=tuple(replace(step,minimum_corner_angle_deg=59.) if step.kind=='marked' else step for step in self.frozen.case.curved_refinement_steps)
        with self.assertRaisesRegex(ValueError,'corner angle'):native_space(replace(self.frozen,case=replace(self.frozen.case,curved_refinement_steps=steps)))
        case=replace(self.frozen.case,contour_mesh=replace(self.frozen.case.contour_mesh,max_triangles=5))
        with self.assertRaisesRegex(ValueError,'max_triangles'):native_space(replace(self.frozen,case=case))
        with self.assertRaisesRegex(ValueError,'marked'):freeze_curved_refinement(Project(partition_case()))

    def test_saved_native_fields_rebuild_the_frozen_choices(self):
        solution=solve(self.frozen.case,mesh_data=self.frozen.mesh_data)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'solution';saved=save_run(self.frozen.case,solution,out)
            restored=read_solution(out)
            self.assertEqual(restored.case,self.frozen.case)
            np.testing.assert_array_equal(restored.u,solution.u)
            np.testing.assert_array_equal(restored.space.geometry.cell_nodes,solution.space.geometry.cell_nodes)
            self.assertEqual(saved['field_space']['curved_refinement_steps'],self.frozen.case.to_dict()['mesh']['curved_refinement_steps'])

    def test_nested_tracking_replays_an_appended_frozen_marked_step(self):
        from superfish_ng.nested_curved_tracking import track_nested_curved_modes
        current=freeze_curved_refinement(replace(self.frozen,case=replace(self.frozen.case,
            curved_refinement_steps=(*self.frozen.case.curved_refinement_steps,Step('marked',(1,),1.)))))
        old=solve(self.frozen.case,mesh_data=self.frozen.mesh_data)
        new=solve(current.case,mesh_data=current.mesh_data)
        result=track_nested_curved_modes(old,new,['A'],mapping='nested_curved',minimum_overlap=.9,
            minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(result['physical_mapping']['ancestry']['appended_steps'],[current.case.curved_refinement_steps[-1].to_dict()])

    def test_cli_creates_a_new_project_and_never_overwrites_existing_output(self):
        import contextlib
        import io
        from superfish_ng.cli import main
        with tempfile.TemporaryDirectory() as tmp,contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            root=Path(tmp);source=root/'source.json';out=root/'frozen.json';self.source.save(source)
            original=source.read_bytes()
            self.assertEqual(main(['freeze-curved-refinement',str(source),'--out',str(out)]),0)
            self.assertEqual(Project.load(out).to_dict(),self.frozen.to_dict())
            saved=out.read_bytes()
            self.assertNotEqual(main(['freeze-curved-refinement',str(source),'--out',str(out)]),0)
            self.assertEqual(out.read_bytes(),saved);self.assertEqual(source.read_bytes(),original)
