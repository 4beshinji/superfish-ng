# SPDX-License-Identifier: Apache-2.0
"""Independent-domain invariants for explicit initial mesh replacement."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng.project import Project
from superfish_ng.curved_space import case_curved_space
from superfish_ng.mesh_input import mesh_from_dict
from test_curved_harmonic_deformation import deformation_fixture,space


def remesh_fixture():
    source,geometry=deformation_fixture();data=deepcopy(source.mesh_data)
    boundary=set(i for edge in data['boundary_edges'] for i in edge)
    cell=next((i for i,t in enumerate(data['triangles']) if not set(t)&boundary),0)
    a,b,c=data['triangles'].pop(cell);node=len(data['points'])
    data['points'].append(np.asarray(data['points'])[[a,b,c]].mean(axis=0).tolist())
    data['triangles'].extend([[a,b,node],[b,c,node],[c,a,node]])
    plan=dict(schema_version=1,source_mesh=data,minimum_corner_angle_deg=1.,
        curved_refinement_steps=[dict(kind='marked',marked_cells=[len(data['triangles'])-1],minimum_corner_angle_deg=1.),dict(kind='uniform')])
    return source,plan,geometry


class CurvedProjectRemeshTests(unittest.TestCase):
    def test_new_mesh_and_explicit_history_keep_the_entire_quadratic_domain(self):
        from superfish_ng.curved_project_remesh import remesh_curved_project
        from scripts.validate_large_curved_mesh_selection import boundary_moments
        source,plan,_=remesh_fixture();before=deepcopy(source.to_dict());request=deepcopy(plan)
        target=remesh_curved_project(source,plan)
        self.assertEqual(source.to_dict(),before);self.assertEqual(plan,request)
        self.assertEqual(target.mesh_data,plan['source_mesh'])
        self.assertNotEqual(target.mesh_data['triangles'],source.mesh_data['triangles'])
        self.assertEqual(len(target.case.curved_refinement_steps),2)
        self.assertEqual(target.case.curved_refinement_steps[0].marked_cells,tuple(plan['curved_refinement_steps'][0]['marked_cells']))
        self.assertIsNotNone(target.case.curved_refinement_steps[0].split_pattern)
        self.assertNotEqual(target.case.curved_refinement_steps[0].split_pattern,source.case.curved_refinement_steps[0].split_pattern)
        old,new=boundary_moments(space(source)),boundary_moments(space(target))
        np.testing.assert_allclose(list(new.values()),list(old.values()),rtol=2e-13,atol=0)
        a,b=source.case.to_dict(),target.case.to_dict()
        for raw in (a,b):
            raw['mesh'].pop('curved_refinement_steps',None);raw['mesh'].pop('curved_refinement_levels',None)
        self.assertEqual(a,b)

    def test_independent_constant_field_mass_is_unchanged_by_the_initial_connectivity(self):
        from superfish_ng.curved_project_remesh import remesh_curved_project
        from superfish_ng.curved_fem import assemble_curved
        source,plan,_=remesh_fixture();target=remesh_curved_project(source,dict(plan,curved_refinement_steps=[{'kind':'uniform'}]))
        values=[]
        for project in (source,target):
            _,mass=assemble_curved(space(project),quadrature_order=project.case.quadrature_order)
            one=np.ones(mass.shape[0]);actual=float(one@mass@one)
            g=space(project).geometry;edges=g.points_rz_m[g.boundary_nodes]
            # Green: integral r^3 dr dz = 1/4 integral r^4 dz, with orientation.
            t,w=np.polynomial.legendre.leggauss(6);t=(t+1)/2;w=w/2
            a,b,m=edges.transpose(1,0,2);linear=4*m-3*a-b;quad=2*(a+b-2*m)
            points=a[:,None]+linear[:,None]*t[None,:,None]+quad[:,None]*t[None,:,None]**2
            dz=linear[:,1,None]+2*quad[:,1,None]*t
            expected=abs(float(np.sum(points[:,:,0]**4*dz*w)/4))
            self.assertAlmostEqual(actual/expected,1.,places=12);values.append(actual)
        self.assertAlmostEqual(values[0]/values[1],1.,places=12)

    def test_same_analytic_curve_with_reprojected_boundary_is_rejected(self):
        from superfish_ng.curved_project_remesh import remesh_curved_project
        from superfish_ng.contour_mesh import refine_contour
        from superfish_ng.mesh_input import mesh_to_dict
        from scripts.validate_large_curved_mesh_selection import boundary_moments
        source,_,_=remesh_fixture();case=replace(source.case,curved_refinement_steps=())
        mesh=refine_contour(case,mesh_from_dict(case,source.mesh_data),.04)
        candidate=replace(source,case=case,mesh_data=mesh_to_dict(mesh))
        old,new=boundary_moments(space(source)),boundary_moments(space(candidate))
        self.assertGreater(abs(new['signed_volume_m3']/old['signed_volume_m3']-1),1e-6)
        plan=dict(schema_version=1,source_mesh=candidate.mesh_data,curved_refinement_levels=0,minimum_corner_angle_deg=1.)
        with self.assertRaisesRegex(ValueError,'quadratic boundary differs'):
            remesh_curved_project(source,plan)

    def test_replacement_history_supports_later_nonaffine_shape_deformation(self):
        from superfish_ng.curved_project_remesh import remesh_curved_project
        from superfish_ng.curved_harmonic_deformation import deform_curved_project
        from superfish_ng.curved_same_domain_tracking import compare_quadratic_space_boundaries
        source,plan,geometry=remesh_fixture();target=remesh_curved_project(source,plan)
        moved=[deform_curved_project(p,geometry,rf_coordinates='fixed',minimum_corner_angle_deg=1.) for p in (source,target)]
        report=compare_quadratic_space_boundaries(moved[0].case,space(moved[0]),moved[1].case,space(moved[1]))
        self.assertLessEqual(report['maximum_coefficient_distance_m'],report['roundoff_tolerance_m'])
        self.assertEqual(moved[1].case.curved_refinement_steps,target.case.curved_refinement_steps)
        self.assertNotEqual(moved[0].mesh_data['triangles'],moved[1].mesh_data['triangles'])

    def test_independent_interior_positions_and_renumbering_do_not_inherit_old_ids(self):
        from superfish_ng.curved_project_remesh import remesh_curved_project
        from scripts.validate_large_curved_mesh_selection import boundary_moments
        source,plan,_=remesh_fixture();data=plan['source_mesh'];count=len(data['points'])
        # Move the newly inserted interior point, then independently renumber
        # nodes and cells. Boundary coordinates, tags and orientation stay fixed.
        data['points'][-1][0]+=.0002;data['points'][-1][1]-=.0003
        data['points'].reverse();data['triangles'].reverse()
        for key in ('triangles','boundary_edges'):data[key]=[[count-1-i for i in row] for row in data[key]]
        plan['curved_refinement_steps'][0]['marked_cells']=[0]
        target=remesh_curved_project(source,plan)
        self.assertEqual(target.mesh_data,data)
        self.assertEqual(target.case.curved_refinement_steps[0].marked_cells,(0,))
        self.assertNotEqual(target.case.curved_refinement_steps[0].split_pattern.parent_topology_sha256,
                            source.case.curved_refinement_steps[0].split_pattern.parent_topology_sha256)
        np.testing.assert_allclose(list(boundary_moments(space(source)).values()),
                                   list(boundary_moments(space(target)).values()),rtol=2e-13,atol=0)

    def test_history_is_explicit_strict_and_bound_to_the_replacement_mesh(self):
        from superfish_ng.curved_project_remesh import remesh_curved_project
        source,plan,_=remesh_fixture()
        bad=[]
        for change in ({'schema_version':True},{'schema_version':2},{'unknown':1},{'source_mesh':None},
                       {'curved_refinement_levels':0},{'curved_refinement_steps':[]},
                       {'minimum_corner_angle_deg':True},{'minimum_corner_angle_deg':0},{'minimum_corner_angle_deg':60},
                       {'minimum_corner_angle_deg':10**400}):bad.append(dict(plan,**change))
        missing=deepcopy(plan);del missing['curved_refinement_steps'];bad.append(missing)
        stale=deepcopy(plan);stale['curved_refinement_steps']=source.case.to_dict()['mesh']['curved_refinement_steps'];bad.append(stale)
        outside=deepcopy(plan);outside['curved_refinement_steps'][0]['marked_cells']=[len(plan['source_mesh']['triangles'])];bad.append(outside)
        for value in bad:
            with self.subTest(value=value),self.assertRaises(ValueError):remesh_curved_project(source,value)
        levels=dict(schema_version=1,source_mesh=plan['source_mesh'],curved_refinement_levels=0,minimum_corner_angle_deg=1.)
        reset=remesh_curved_project(source,levels)
        self.assertEqual(reset.case.curved_refinement_steps,());self.assertEqual(reset.case.curved_refinement_levels,0)
        raw=reset.case.to_dict();raw['model']['polarization']='te'
        from superfish_ng.config import Case
        te=remesh_curved_project(replace(reset,case=Case.from_dict(raw)),levels)
        self.assertEqual(te.case.model.polarization,'te')
        self.assertEqual(te.case.curved_refinement_steps,())

    def test_quality_and_element_budgets_are_checked_before_result_publication(self):
        from superfish_ng.curved_project_remesh import remesh_curved_project
        source,plan,_=remesh_fixture()
        with self.assertRaisesRegex(ValueError,'minimum corner angle'):
            remesh_curved_project(source,dict(plan,minimum_corner_angle_deg=59.))
        source=replace(source,case=replace(source.case,curved_refinement_steps=(),contour_mesh=replace(source.case.contour_mesh,max_triangles=27)))
        with self.assertRaisesRegex(ValueError,'max_triangles=27'):remesh_curved_project(source,plan)
        unchanged=dict(schema_version=1,source_mesh=source.mesh_data,curved_refinement_levels=10**100,minimum_corner_angle_deg=1.)
        with self.assertRaisesRegex(ValueError,'max_triangles=27'):remesh_curved_project(source,unchanged)

    def test_cli_validates_before_writing_and_preserves_existing_files(self):
        from superfish_ng.cli import main
        import json
        source,plan,_=remesh_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source.save(root/'source.json');(root/'plan.json').write_text(json.dumps(plan))
            before=(root/'source.json').read_bytes()
            args=['remesh-curved-project',str(root/'source.json'),'--plan',str(root/'plan.json'),'--out',str(root/'target.json')]
            self.assertEqual(main(args),0)
            target=(root/'target.json').read_bytes();self.assertEqual(main(args),2)
            self.assertEqual((root/'target.json').read_bytes(),target);self.assertEqual((root/'source.json').read_bytes(),before)
            (root/'plan.json').write_text('{"schema_version":1,"schema_version":1}')
            args[-1]=str(root/'invalid.json');self.assertEqual(main(args),2);self.assertFalse((root/'invalid.json').exists())
