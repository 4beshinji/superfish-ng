# SPDX-License-Identifier: Apache-2.0
"""Generated TE interiors preserve boundaries, sectors and physical measure."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng.project import Project
from superfish_ng.curved_remesh_generation import generate_curved_remesh_plan
from superfish_ng.curved_project_remesh import remesh_curved_project
from superfish_ng.studies import Study,execute_study
from test_te_symmetry_partition_workflows import fixture
from test_te_symmetry_harmonic_workflows import symmetry_harmonic_study
from test_curved_harmonic_deformation import space
from test_curved_harmonic_study import controls


def settings():
    return dict(schema_version=1,max_chord_edge_m=.2,max_chord_triangle_area_m2=.0008,
                minimum_corner_angle_deg=1.,max_triangles=1000,max_rounds=20,curved_refinement_levels=1)


def boundary(mesh):
    return {(tuple(sorted(tuple(mesh['points'][i]) for i in edge)),tag)
            for edge,tag in zip(mesh['boundary_edges'],mesh['boundary_tags'])}


class TERemeshGenerationTests(unittest.TestCase):
    def test_all_sectors_preserve_boundary_and_independent_volume(self):
        from scripts.validate_large_curved_mesh_selection import boundary_moments
        from superfish_ng.curved_reflection import reflect_curved_space
        from superfish_ng.fem import triangle_quadrature
        rule=list(triangle_quadrature(5));q=np.array([b[1:] for b,w in rule]);weights=np.array([w for b,w in rule])
        expected=np.pi*.08**2*.1
        for side in ('z_min','z_max'):
            for tag in ('magnetic_symmetry','electric_symmetry'):
                for reflected in (False,True):
                    with self.subTest(side=side,tag=tag,reflected=reflected):
                        base,_,_=fixture(reflected,tag,side);before=base.to_dict()
                        plan=generate_curved_remesh_plan(base,settings());target=remesh_curved_project(base,plan)
                        self.assertEqual(base.to_dict(),before)
                        self.assertEqual(boundary(base.mesh_data),boundary(target.mesh_data))
                        self.assertNotEqual(base.mesh_data['triangles'],target.mesh_data['triangles'])
                        self.assertEqual(target.case.model,base.case.model);self.assertEqual(target.reflect_full,reflected)
                        self.assertEqual(getattr(target.case,side),tag)
                        native=space(target)
                        self.assertAlmostEqual(-boundary_moments(native)['signed_volume_m3']/expected,1.,places=12)
                        if reflected:
                            full=reflect_curved_space(target.case,native,coefficient_parity=1 if tag=='magnetic_symmetry' else -1).space
                            volume=sum(2*np.pi*(m.evaluate(q)['points_rz_m'][:,0]*m.evaluate(q)['determinant_m2'])@weights for m in full.geometry.local_maps)
                            self.assertAlmostEqual(volume/(2*expected),1.,places=12)

    def test_old_interior_and_numbering_do_not_select_the_generated_plan(self):
        base,_,_=fixture();first=generate_curved_remesh_plan(base,settings())
        other=remesh_curved_project(base,first).to_dict();mesh=other['mesh_data'];n=len(mesh['points'])
        mesh['points'].reverse();mesh['triangles'].reverse();mesh['boundary_edges'].reverse();mesh['boundary_tags'].reverse()
        for key in ('triangles','boundary_edges'):mesh[key]=[[n-1-i for i in row] for row in mesh[key]]
        self.assertEqual(first,generate_curved_remesh_plan(Project.from_dict(other),settings()))

    def test_real_generated_study_tracks_full_electric_field(self):
        from superfish_ng.study_mode_tracking import build_study_mode_tracking,replay_study_mode_tracking
        base,_,_=fixture();plan=generate_curved_remesh_plan(base,settings())
        raw=symmetry_harmonic_study();raw.update(study_version=4,kind='curved_remesh_sweep',project=base.to_dict(),values=[0.,.25],
            mesh_schedule=dict(schema_version=1,breakpoints=[.125],plans=[dict(kind='original'),dict(kind='replace',plan=plan)]))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);execute_study(Study.from_dict(raw),root/'study')
            result=build_study_mode_tracking(dict(schema_version=1,study_run=str(root/'study'),initial_ids=['TE'],step_controls=[controls()]))
            self.assertEqual(result['status'],'PASS');self.assertEqual(replay_study_mode_tracking(result),result)
            mapping=result['history']['steps'][0]['tracking']['physical_mapping']
            self.assertEqual(mapping['field'],'Ephi_V_per_m');self.assertTrue(mapping['symmetry_sector']['reflected'])
            np.testing.assert_allclose(mapping['axisymmetric_volumes_m3'],[2*np.pi*.1*.08**2*(1+.08*x+(.08*x)**2/3) for x in (0.,.25)],rtol=1e-12)

    def test_marked_history_is_frozen_and_invalid_requests_still_fail(self):
        base,_,_=fixture();marked=settings();marked.pop('curved_refinement_levels')
        marked['curved_refinement_steps']=[dict(kind='marked',marked_cells=[0],minimum_corner_angle_deg=1.)]
        plan=generate_curved_remesh_plan(base,marked)
        self.assertTrue(plan['curved_refinement_steps'][0]['split_pattern'])
        self.assertTrue(remesh_curved_project(base,plan).reflect_full)
        for invalid in (dict(settings(),max_chord_edge_m=.05),dict(settings(),max_triangles=1),dict(settings(),unknown=True)):
            with self.assertRaises(ValueError):generate_curved_remesh_plan(base,invalid)
        raw=base.to_dict();raw['case']['geometry']['edge_tags'][-1]='electric_symmetry';raw['mesh_data']['boundary_tags'][-1]='electric_symmetry'
        with self.assertRaisesRegex(ValueError,'one symmetry'):generate_curved_remesh_plan(Project.from_dict(raw),settings())
