# SPDX-License-Identifier: Apache-2.0
"""Independent regenerated interiors on the identical native quadratic boundary."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
import numpy as np
from test_curved_project_remesh import remesh_fixture
from test_curved_harmonic_deformation import space
from superfish_ng.curved_project_remesh import remesh_curved_project
from superfish_ng.mesh_input import mesh_from_dict


def generation_settings(area=.0006):
    return dict(schema_version=1,max_chord_edge_m=.08,max_chord_triangle_area_m2=area,
                minimum_corner_angle_deg=1.,max_triangles=10000,max_rounds=20,curved_refinement_levels=1)


class CurvedRemeshGenerationTests(unittest.TestCase):
    def test_regeneration_depends_on_boundary_not_old_interior_or_numbering(self):
        from superfish_ng.curved_remesh_generation import generate_curved_remesh_plan
        source,other_plan,_=remesh_fixture();other=remesh_curved_project(source,other_plan)
        data=other.to_dict();count=len(data['mesh_data']['points'])
        # Remove the obsolete history when independently renumbering its base.
        data['case']['mesh'].pop('curved_refinement_steps');mesh=data['mesh_data']
        mesh['points'].reverse();mesh['triangles'].reverse();mesh['boundary_edges'].reverse();mesh['boundary_tags'].reverse()
        for key in ('triangles','boundary_edges'):mesh[key]=[[count-1-i for i in row] for row in mesh[key]]
        from superfish_ng.project import Project
        other=Project.from_dict(data);before=deepcopy(source.to_dict());settings=generation_settings()
        first=generate_curved_remesh_plan(source,settings);second=generate_curved_remesh_plan(other,settings)
        self.assertEqual(first,second);self.assertEqual(source.to_dict(),before)
        self.assertNotEqual(first['source_mesh']['triangles'],source.mesh_data['triangles'])
        self.assertEqual(settings,generation_settings())

    def test_requested_area_and_independent_green_geometry_survive_remeshing(self):
        from superfish_ng.curved_remesh_generation import generate_curved_remesh_plan
        from scripts.validate_large_curved_mesh_selection import boundary_moments
        source,_,_=remesh_fixture();old=boundary_moments(space(source));counts=[]
        for area in (.0009,.0003):
            settings=generation_settings(area);plan=generate_curved_remesh_plan(source,settings)
            target=remesh_curved_project(source,plan);mesh=mesh_from_dict(target.case,target.mesh_data)
            points=mesh.points[mesh.triangles];u,v=points[:,1]-points[:,0],points[:,2]-points[:,0]
            areas=(u[:,0]*v[:,1]-u[:,1]*v[:,0])/2
            self.assertGreater(float(areas.min()),0.)
            self.assertLessEqual(float(areas.max()),area*(1+1e-12))
            counts.append(len(areas))
            np.testing.assert_allclose(list(boundary_moments(space(target)).values()),list(old.values()),rtol=2e-13,atol=0.)
            old_boundary={tuple(sorted(tuple(p) for p in np.asarray(source.mesh_data['points'])[e])) for e in source.mesh_data['boundary_edges']}
            new_boundary={tuple(sorted(tuple(p) for p in mesh.points[e])) for e in mesh.boundary_edges}
            self.assertEqual(old_boundary,new_boundary)
        self.assertGreater(counts[1],counts[0])

    def test_similarity_generation_and_known_field_mass(self):
        from superfish_ng.curved_remesh_generation import generate_curved_remesh_plan
        from superfish_ng.curved_project_transform import transform_curved_project
        from superfish_ng.curved_fem import assemble_curved
        source,_,_=remesh_fixture();settings=generation_settings();a=generate_curved_remesh_plan(source,settings)
        large=transform_curved_project(source,dict(radial_scale=2.,axial_scale=2.,axial_shear=0.),rf_coordinates='axial')
        large=replace(large,case=replace(large.case,contour_mesh=replace(large.case.contour_mesh,max_edge_m=.16)))
        scaled=dict(settings,max_chord_edge_m=.16,max_chord_triangle_area_m2=4*settings['max_chord_triangle_area_m2'])
        b=generate_curved_remesh_plan(large,scaled)
        self.assertEqual(a['source_mesh']['triangles'],b['source_mesh']['triangles'])
        np.testing.assert_allclose(np.asarray(b['source_mesh']['points']),2*np.asarray(a['source_mesh']['points']),rtol=0,atol=2e-15)
        masses=[]
        for project in (remesh_curved_project(source,a),remesh_curved_project(large,b)):
            native=space(project);_,mass=assemble_curved(native,quadrature_order=12);one=np.ones(mass.shape[0])
            actual=float(one@mass@one);edges=native.geometry.points_rz_m[native.geometry.boundary_nodes]
            t,w=np.polynomial.legendre.leggauss(6);t=(t+1)/2;w=w/2
            left,right,mid=edges.transpose(1,0,2);linear=4*mid-3*left-right;quad=2*(left+right-2*mid)
            points=left[:,None]+linear[:,None]*t[None,:,None]+quad[:,None]*t[None,:,None]**2
            dz=linear[:,1,None]+2*quad[:,1,None]*t
            expected=abs(float(np.sum(points[:,:,0]**4*dz*w)/4))
            self.assertAlmostEqual(actual/expected,1.,places=12);masses.append(actual)
        self.assertAlmostEqual(masses[1]/masses[0],32.,places=11)

    def test_strict_settings_and_unsupported_physics(self):
        from superfish_ng.curved_remesh_generation import generate_curved_remesh_plan
        source,_,_=remesh_fixture();settings=generation_settings()
        invalid=[dict(settings,schema_version=True),dict(settings,schema_version=2),dict(settings,unknown=1),
                 dict(settings,curved_refinement_steps=[]),dict(settings,curved_refinement_levels=True)]
        for name in ('max_chord_edge_m','max_chord_triangle_area_m2','minimum_corner_angle_deg'):
            invalid.extend(dict(settings,**{name:value}) for value in (True,0.,-1.,float('nan'),float('inf'),10**400))
        invalid += [dict(settings,max_triangles=True),dict(settings,max_rounds=0),dict(settings,max_rounds=1.5)]
        missing=deepcopy(settings);del missing['curved_refinement_levels'];invalid.append(missing)
        for bad in invalid:
            with self.subTest(bad=bad),self.assertRaises(ValueError):generate_curved_remesh_plan(source,bad)
        raw=source.case.to_dict();raw['model']['polarization']='te'
        from superfish_ng import Case
        with self.assertRaisesRegex(ValueError,'TM'):
            generate_curved_remesh_plan(replace(source,case=Case.from_dict(raw)),settings)

    def test_fixed_boundary_incompatible_size_and_generation_history_budgets(self):
        from superfish_ng.curved_remesh_generation import generate_curved_remesh_plan
        source,_,_=remesh_fixture();settings=generation_settings()
        invalid=[(dict(settings,max_chord_edge_m=.001),'fixed quadratic boundary'),
                 (dict(settings,max_triangles=3),'max_triangles'),
                 (dict(settings,max_triangles=1000000),'original Case limit'),
                 (dict(settings,max_triangles=30),'max_triangles'),
                 (dict(settings,max_triangles=50),'max_triangles'),
                 (dict(settings,max_chord_triangle_area_m2=1e-8,max_rounds=1),'max_rounds')]
        for bad,message in invalid:
            with self.subTest(bad=bad),self.assertRaisesRegex(ValueError,message):generate_curved_remesh_plan(source,bad)

    def test_explicit_new_marked_choices_are_frozen_and_old_pattern_is_rejected(self):
        from superfish_ng.curved_remesh_generation import generate_curved_remesh_plan
        source,_,_=remesh_fixture();settings=generation_settings();del settings['curved_refinement_levels']
        settings['curved_refinement_steps']=[dict(kind='marked',marked_cells=[0],minimum_corner_angle_deg=1.),dict(kind='uniform')]
        plan=generate_curved_remesh_plan(source,settings)
        self.assertIn('split_pattern',plan['curved_refinement_steps'][0])
        self.assertNotEqual(plan['curved_refinement_steps'][0]['split_pattern'],source.to_dict()['case']['mesh']['curved_refinement_steps'][0]['split_pattern'])
        self.assertNotIn('split_pattern',settings['curved_refinement_steps'][0])
        settings['curved_refinement_steps']=source.to_dict()['case']['mesh']['curved_refinement_steps']
        with self.assertRaises(ValueError):generate_curved_remesh_plan(source,settings)

    def test_cli_plan_roundtrip_and_exclusive_output(self):
        import json
        from superfish_ng.cli import main
        from superfish_ng.curved_remesh_generation import generate_curved_remesh_plan
        source,_,_=remesh_fixture();settings=generation_settings()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source.save(root/'source.json');(root/'settings.json').write_text(json.dumps(settings));before=(root/'source.json').read_bytes()
            args=['generate-curved-remesh-plan',str(root/'source.json'),'--settings',str(root/'settings.json'),'--out',str(root/'plan.json')]
            self.assertEqual(main(args),0);data=(root/'plan.json').read_bytes();plan=json.loads(data)
            self.assertEqual(plan,generate_curved_remesh_plan(source,settings))
            self.assertEqual(main(args),2);self.assertEqual((root/'plan.json').read_bytes(),data);self.assertEqual((root/'source.json').read_bytes(),before)
            (root/'settings.json').write_text('{"schema_version":1,"schema_version":1}');args[-1]=str(root/'invalid.json')
            self.assertEqual(main(args),2);self.assertFalse((root/'invalid.json').exists())

    def test_reentrant_native_line_boundary_preserves_independent_rectangle_moments(self):
        import math
        from superfish_ng import Case
        from superfish_ng.project import Project
        from superfish_ng.conics import LineSegment
        from superfish_ng.curved_contour import CurvedContour
        from superfish_ng.mesh_controls import ContourMeshControls
        from superfish_ng.curved_remesh_generation import generate_curved_remesh_plan
        from scripts.validate_large_curved_mesh_selection import boundary_moments
        vertices=[(z*.1,r*.1) for z,r in ((0,0),(3,0),(3,2),(1,2),(1,1),(2,1),(2,.5),(0,.5))]
        curves=tuple(LineSegment(a,b) for a,b in zip(vertices,vertices[1:]+vertices[:1]))
        case=Case((),curved_contour=CurvedContour(curves,('axis',)+('pec',)*7,1e-14),geometry_order=2,element_order=2,
                  curve_chord_tolerance_m=.001,contour_mesh=ContourMeshControls(.06,min_angle_deg=5.))
        source=Project(case);settings=dict(generation_settings(.0006),max_chord_edge_m=.06,curved_refinement_levels=0)
        target=remesh_curved_project(source,generate_curved_remesh_plan(source,settings));moments=boundary_moments(space(target))
        self.assertAlmostEqual(abs(moments['signed_area_m2'])/.04,1.,places=12)
        self.assertAlmostEqual(abs(moments['signed_volume_m3'])/(7.5*math.pi*.001),1.,places=12)
        for triangle in np.asarray(target.mesh_data['points'])[target.mesh_data['triangles']]:
            r,z=triangle.mean(axis=0)/.1
            self.assertFalse(1<z<2 and .5<r<1)

    def test_coarsening_budget_applies_to_new_mesh_even_if_old_mesh_is_larger(self):
        from superfish_ng.curved_remesh_generation import generate_curved_remesh_plan
        source,_,_=remesh_fixture()
        fine=remesh_curved_project(source,generate_curved_remesh_plan(source,generation_settings(.0003)))
        settings=dict(generation_settings(.0009),max_triangles=50,curved_refinement_levels=0)
        plan=generate_curved_remesh_plan(fine,settings)
        self.assertGreater(len(fine.mesh_data['triangles']),50)
        self.assertLess(len(plan['source_mesh']['triangles']),len(fine.mesh_data['triangles']))
        self.assertLessEqual(len(plan['source_mesh']['triangles']),50)
        self.assertEqual(plan,generate_curved_remesh_plan(source,settings))
