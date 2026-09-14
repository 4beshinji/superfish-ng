# SPDX-License-Identifier: Apache-2.0
"""Common reference integration partitions across different local histories."""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import unittest
import numpy as np
from superfish_ng.curved_refinement_steps import CurvedRefinementStep as Step
from test_curved_selection_transfer import triangle_project


def local_projects():
    base=triangle_project()
    return [replace(base,case=replace(base.case,curved_refinement_steps=(Step('uniform'),Step('marked',(cell,),1.)))) for cell in (0,1)]


class CurvedOverlayGeometryTests(unittest.TestCase):
    def test_independent_histories_have_exact_common_cell_coverage(self):
        from superfish_ng.curved_comparison_overlay import build_curved_comparison_overlay
        projects=local_projects();before=[p.to_dict() for p in projects]
        overlay=build_curved_comparison_overlay(*projects,boundary_pairing='same_curve_fractions',max_pair_tests=10000,max_triangles=1000)
        report=overlay.report
        self.assertGreater(len(report['triangles']),max(report['final_cell_counts']))
        self.assertEqual(report['base_reference_areas'],[[1,2]])
        self.assertEqual([p.to_dict() for p in projects],before)
        for side in ('previous','current'):
            self.assertEqual([r['covered_reference_area'] for r in report[side+'_cell_coverage']],
                             [r['reference_area'] for r in report[side+'_cell_coverage']])
        # Physical determinant of this independent straight fixture is .02.
        area=sum(float(F(*r['reference_determinant']))/2*.02 for r in report['triangles'])
        self.assertAlmostEqual(area,.01,places=15)

    def test_reversing_sides_preserves_the_reference_quadrature_partition(self):
        from superfish_ng.curved_comparison_overlay import build_curved_comparison_overlay
        projects=local_projects();kwargs=dict(boundary_pairing='same_curve_fractions',max_pair_tests=10000,max_triangles=1000)
        a=build_curved_comparison_overlay(*projects,**kwargs);b=build_curved_comparison_overlay(*projects[::-1],**kwargs)
        self.assertEqual([(t['base_cell'],t['reference_vertices']) for t in a.report['triangles']],
                         [(t['base_cell'],t['reference_vertices']) for t in b.report['triangles']])
        self.assertEqual([t['previous_cell'] for t in a.report['triangles']],[t['current_cell'] for t in b.report['triangles']])

    def test_independent_numbering_preserves_the_same_material_partition(self):
        from superfish_ng.curved_comparison_overlay import build_curved_comparison_overlay
        from superfish_ng.curved_comparison_correspondence import infer_curved_comparison_correspondence
        from superfish_ng.curved_space import case_curved_space
        from superfish_ng.mesh_input import mesh_from_dict
        from test_curved_comparison_correspondence import renumber_source
        projects=local_projects();changed=[]
        for side,project in enumerate(projects):
            mesh,_=renumber_source(project.mesh_data,seed=213+side)
            prefix=replace(project.case,curved_refinement_steps=(Step('uniform'),))
            spaces=[case_curved_space(prefix,mesh_from_dict(prefix,m)) for m in (project.mesh_data,mesh)]
            pairing=infer_curved_comparison_correspondence((prefix,prefix),spaces,boundary_pairing='same_curve_fractions')
            marked=project.case.curved_refinement_steps[1]
            step=replace(marked,marked_cells=tuple(pairing['current_cell_for_previous'][i] for i in marked.marked_cells))
            changed.append(replace(project,mesh_data=mesh,case=replace(project.case,curved_refinement_steps=(Step('uniform'),step))))
        kwargs=dict(boundary_pairing='same_curve_fractions',max_pair_tests=10000,max_triangles=1000)
        a=build_curved_comparison_overlay(*projects,**kwargs);b=build_curved_comparison_overlay(*changed,**kwargs)
        self.assertEqual([t['reference_vertices'] for t in a.report['triangles']],[t['reference_vertices'] for t in b.report['triangles']])
        for side in (0,1):
            for x,y in zip(a.evaluate(side,np.array([[.2,.3],[.4,.2]])),b.evaluate(side,np.array([[.2,.3],[.4,.2]]))):
                np.testing.assert_allclose(x['points_rz_m'],y['points_rz_m'],rtol=2e-14,atol=1e-16)
                np.testing.assert_allclose(x['determinant_m2'],y['determinant_m2'],rtol=2e-14,atol=0)

    def test_frozen_split_patterns_keep_the_exact_common_partition(self):
        from superfish_ng.curved_comparison_overlay import build_curved_comparison_overlay
        from superfish_ng.frozen_curved_refinement import freeze_curved_refinement
        projects=local_projects();frozen=[freeze_curved_refinement(p) for p in projects]
        self.assertTrue(all(p.case.curved_refinement_steps[1].split_pattern for p in frozen))
        kwargs=dict(boundary_pairing='same_curve_fractions',max_pair_tests=10000,max_triangles=1000)
        self.assertEqual(build_curved_comparison_overlay(*projects,**kwargs).report,
                         build_curved_comparison_overlay(*frozen,**kwargs).report)

class CurvedOverlayTrackingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from superfish_ng import solve
        cls.projects=local_projects()
        cls.solutions=[solve(p.case,mesh_data=p.mesh_data) for p in cls.projects]
        cls.maps=[dict(schema_version=4,source_mesh=p.mesh_data,curved_refinement_steps=[s.to_dict() for s in p.case.curved_refinement_steps],
            boundary_pairing='same_curve_fractions',max_pair_tests=10000) for p in cls.projects]
        from test_curved_piecewise_remesh_tracking import CONTROLS
        cls.controls=dict(CONTROLS,comparison_meshes=cls.maps,sample_order=4)

    def test_known_field_has_exact_mass_and_unit_self_overlap(self):
        from superfish_ng.piecewise_remesh_tracking import track_piecewise_remesh_modes
        adapters=[replace(s,u=np.ones_like(s.u)) for s in self.solutions]
        result=track_piecewise_remesh_modes(*adapters,['Hphi=r adapter'],**self.controls)
        self.assertEqual(result['status'],'PASS')
        self.assertAlmostEqual(result['matches'][0]['minimum_principal_overlap'],1.,places=14)
        # Independent triangle integral: volume = 2pi * area * centroid radius.
        np.testing.assert_allclose(result['physical_mapping']['axisymmetric_volumes_m3'],[2*np.pi*.01*.1/3]*2,rtol=2e-14)
        self.assertGreater(result['physical_mapping']['comparison_triangle_count'],max(len(s.space.geometry.cell_nodes) for s in self.solutions))

    def test_strict_version_pair_budget_and_sample_budget(self):
        from superfish_ng.saved_mode_tracking import validate_tracking_controls
        from superfish_ng.piecewise_remesh_tracking import track_piecewise_remesh_modes
        validate_tracking_controls(self.controls)
        for change in ({'max_pair_tests':True},{'max_pair_tests':0},{'max_pair_tests':1.5},{'max_pair_tests':20000},
                       {'boundary_pairing':'guess'},{'schema_version':True},{'unknown':0}):
            maps=deepcopy(self.maps);maps[0].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):validate_tracking_controls(dict(self.controls,comparison_meshes=maps))
        maps=deepcopy(self.maps);del maps[0]['max_pair_tests']
        with self.assertRaises(ValueError):validate_tracking_controls(dict(self.controls,comparison_meshes=maps))
        maps=[dict(m,max_pair_tests=1) for m in self.maps]
        with self.assertRaisesRegex(ValueError,'max_pair_tests'):
            track_piecewise_remesh_modes(*self.solutions,['A'],**dict(self.controls,comparison_meshes=maps))
        from superfish_ng.curved_comparison_overlay import build_curved_comparison_overlay
        with self.assertRaisesRegex(ValueError,'(max_triangles|samples)'):
            build_curved_comparison_overlay(*self.projects,boundary_pairing='same_curve_fractions',max_pair_tests=10000,max_triangles=10)
        maps=deepcopy(self.maps)
        for m in maps:del m['curved_refinement_steps'];m['curved_refinement_levels']=5
        with self.assertRaisesRegex(ValueError,'(max_triangles|samples|budget)'):
            track_piecewise_remesh_modes(*self.solutions,['A'],**dict(self.controls,comparison_meshes=maps,sample_order=32))
        maps=[dict(m,schema_version=3) for m in self.maps]
        for m in maps:del m['max_pair_tests']
        with self.assertRaises(ValueError):track_piecewise_remesh_modes(*self.solutions,['A'],**dict(self.controls,comparison_meshes=maps))

    def test_saved_partition_is_reconstructed_and_tampering_rejected(self):
        import json,tempfile
        from pathlib import Path
        from superfish_ng.io import save_run
        from superfish_ng.saved_mode_tracking import save_mode_tracking,read_mode_tracking
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,s in zip(('old','new'),self.solutions):save_run(s.case,s,root/name)
            request=dict(schema_version=1,previous_run='old',current_run='new',previous_ids=['A'],controls=self.controls)
            result=save_mode_tracking(request,root/'pair.json',base_directory=root)
            self.assertEqual(read_mode_tracking(root/'pair.json'),result)
            altered=deepcopy(result);altered['tracking']['physical_mapping']['common_reference_partition']['triangles'][0]['reference_determinant']=[1,1]
            (root/'changed.json').write_text(json.dumps(altered))
            with self.assertRaises(ValueError):read_mode_tracking(root/'changed.json')


if __name__=='__main__':unittest.main()
