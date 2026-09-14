# SPDX-License-Identifier: Apache-2.0
"""Boundary parameter correspondence and harmonic mesh displacement invariants."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng.project import Project
from superfish_ng.curved_refinement_steps import CurvedRefinementStep as Step
from superfish_ng.frozen_curved_refinement import freeze_curved_refinement
from superfish_ng.curved_project_transform import transform_curved_project
from superfish_ng.curved_space import case_curved_space
from superfish_ng.mesh_input import mesh_from_dict
from test_curved_piecewise_remesh_tracking import curved_comparison_fixture


def deformation_fixture():
    cases,meshes=curved_comparison_fixture()
    source=freeze_curved_refinement(Project(replace(cases[0],curved_refinement_steps=(
        Step('marked',(0,),1.),Step('uniform'),Step('marked',(0,),1.))),mesh_data=meshes[0]['source_mesh']))
    return source,cases[1].to_dict()['geometry']


def folded_deformation_fixture():
    from superfish_ng import Case
    raw=Case.load('examples/curved_ellipse.json').to_dict();raw['mesh']['geometry_order']=2
    raw['mesh']['contour_mesh'].update(max_edge_m=.025,min_angle_deg=5.)
    vertices=[[0.,0.],[.2,0.],[.2,.1],[.1,.1],[0.,.1]]
    curves=[dict(type='line',start_zr_m=a,end_zr_m=b) for a,b in zip(vertices,vertices[1:]+vertices[:1])]
    raw['geometry']=dict(type='curved_contour',curves=curves,edge_tags=['axis']+['pec']*4,
        join_tolerance_m=1e-14,chord_tolerance_m=.002)
    project=Project(Case.from_dict(raw));geometry=deepcopy(raw['geometry'])
    geometry['curves'][2]['end_zr_m'][1]=.04;geometry['curves'][3]['start_zr_m'][1]=.04
    # Both contours are valid. The concave target folds this mesh extension.
    Case.from_dict(dict(raw,geometry=geometry))
    return project,geometry


def space(project):return case_curved_space(project.case,mesh_from_dict(project.case,project.mesh_data))


class CurvedHarmonicDeformationTests(unittest.TestCase):
    def test_harmonic_extension_reproduces_affine_coordinates_on_every_frozen_level(self):
        from superfish_ng.curved_harmonic_deformation import deform_curved_project
        source,_=deformation_fixture()
        expected=transform_curved_project(source,dict(radial_scale=1.125,axial_scale=1.25,axial_shear=0.),rf_coordinates='axial')
        target=deform_curved_project(source,expected.case.to_dict()['geometry'],rf_coordinates='axis_fraction',minimum_corner_angle_deg=1.)
        np.testing.assert_allclose(target.mesh_data['points'],np.asarray(source.mesh_data['points'])*[1.125,1.25],rtol=0,atol=2e-15)
        for end in range(4):
            a,b=[space(replace(p,case=replace(p.case,curved_refinement_steps=p.case.curved_refinement_steps[:end]))) for p in (expected,target)]
            np.testing.assert_array_equal(a.geometry.cell_nodes,b.geometry.cell_nodes)
            np.testing.assert_allclose(a.geometry.points_rz_m,b.geometry.points_rz_m,rtol=0,atol=2e-15)
        self.assertEqual(target.case.acceleration_parameters,expected.case.acceleration_parameters)

    def test_nonaffine_target_preserves_declared_boundaries_and_frozen_parent_numbers(self):
        from superfish_ng.curved_harmonic_deformation import deform_curved_project
        source,geometry=deformation_fixture();before=deepcopy(source.to_dict())
        target=deform_curved_project(source,geometry,rf_coordinates='fixed',minimum_corner_angle_deg=1.)
        a,b=space(source),space(target)
        self.assertEqual(source.to_dict(),before)
        self.assertEqual(target.case.curved_refinement_steps,source.case.curved_refinement_steps)
        for key in ('cell_nodes','boundary_nodes','boundary_curve_indices'):
            np.testing.assert_array_equal(getattr(a.geometry,key),getattr(b.geometry,key))
        np.testing.assert_allclose(a.geometry.boundary_parameters,b.geometry.boundary_parameters,rtol=0,atol=2e-14)
        # Independent Green integral on the represented P2 boundary. The two half
        # ellipses keep their total axial extent, while their radius scales 1.125.
        from scripts.validate_large_curved_mesh_selection import boundary_moments
        old,new=boundary_moments(a),boundary_moments(b)
        self.assertAlmostEqual(new['signed_area_m2']/old['signed_area_m2'],1.125,places=12)
        self.assertAlmostEqual(new['signed_volume_m3']/old['signed_volume_m3'],1.125**2,places=12)
        # Three non-collinear points fix an affine map; all moved nodes cannot
        # satisfy a single such map for this two-centre target.
        x=np.c_[np.asarray(source.mesh_data['points']),np.ones(len(source.mesh_data['points']))]
        y=np.asarray(target.mesh_data['points']);fit=np.linalg.lstsq(x,y,rcond=None)[0]
        self.assertGreater(np.linalg.norm(x@fit-y),1e-3)

    def test_displacement_stationarity_against_independent_cotangent_energy(self):
        from superfish_ng.curved_harmonic_deformation import deform_curved_project
        source,geometry=deformation_fixture()
        target=deform_curved_project(source,geometry,rf_coordinates='fixed',minimum_corner_angle_deg=1.)
        x=np.asarray(source.mesh_data['points']);d=np.asarray(target.mesh_data['points'])-x
        stiffness=np.zeros((len(x),len(x)))
        for triangle in source.mesh_data['triangles']:
            for i in range(3):
                a,b,c=[triangle[(i+j)%3] for j in range(3)]
                u,v=x[a]-x[c],x[b]-x[c]
                weight=.5*float(u@v)/abs(u[0]*v[1]-u[1]*v[0])
                stiffness[a,a]+=weight;stiffness[b,b]+=weight
                stiffness[a,b]-=weight;stiffness[b,a]-=weight
        boundary=np.unique(source.mesh_data['boundary_edges']);free=np.setdiff1d(np.arange(len(x)),boundary)
        self.assertGreater(len(free),0)
        np.testing.assert_allclose((stiffness@d)[free],0.,rtol=0,atol=1e-15)
        # A nonzero zero-boundary perturbation increases this convex quadratic
        # energy. This checks displacement, not harmonic coordinates or graph weights.
        perturb=np.zeros_like(d);perturb[free]=np.random.default_rng(12).normal(size=(len(free),2))*.001
        energy=lambda y:float(np.einsum('ij,ij->',y,stiffness@y))
        self.assertGreater(energy(d+perturb),energy(d))
        identity=deform_curved_project(source,source.case.to_dict()['geometry'],rf_coordinates='fixed',minimum_corner_angle_deg=1.)
        np.testing.assert_allclose(identity.mesh_data['points'],x,rtol=0,atol=2e-15)

    def test_strict_correspondence_quality_and_source_physics(self):
        from superfish_ng.curved_harmonic_deformation import deform_curved_project
        source,geometry=deformation_fixture()
        call=lambda p,g,**kw:deform_curved_project(p,g,**dict(dict(rf_coordinates='fixed',minimum_corner_angle_deg=1.),**kw))
        for bad in (dict(geometry,unknown=1),dict(geometry,segments_per_curve=None),
                    dict(geometry,segments_per_curve=[True,3,3]),dict(geometry,segments_per_curve=[1,4,3]),
                    dict(geometry,curves=geometry['curves'][:2]),dict(geometry,edge_tags=['axis','axis','pec'])):
            with self.subTest(bad=bad),self.assertRaises(ValueError):call(source,bad)
        for floor in (True,0,60,float('inf'),float('nan'),10**400):
            with self.subTest(floor=floor),self.assertRaisesRegex(ValueError,'minimum_corner_angle'):call(source,geometry,minimum_corner_angle_deg=floor)
        with self.assertRaisesRegex(ValueError,'minimum corner angle'):call(source,geometry,minimum_corner_angle_deg=59.)
        with self.assertRaisesRegex(ValueError,'rf_coordinates'):call(source,geometry,rf_coordinates='automatic')
        steps=tuple(replace(s,split_pattern=None) if s.kind=='marked' else s for s in source.case.curved_refinement_steps)
        with self.assertRaisesRegex(ValueError,'freeze-curved-refinement'):call(replace(source,case=replace(source.case,curved_refinement_steps=steps)),geometry)
        from superfish_ng.model import Model
        with self.assertRaisesRegex(ValueError,'TM'):call(replace(source,case=replace(source.case,model=replace(Model(),polarization='te'))),geometry)
        small=replace(source,case=replace(source.case,contour_mesh=replace(source.case.contour_mesh,max_triangles=5)))
        with self.assertRaisesRegex(ValueError,'max_triangles'):call(small,geometry)

    def test_rf_coordinates_are_explicit_and_shortening_does_not_hide_invalid_fixed_interval(self):
        from superfish_ng.curved_harmonic_deformation import deform_curved_project
        source,_=deformation_fixture()
        source=replace(source,case=replace(source.case,phase_origin_m=.07))
        expected=transform_curved_project(source,dict(radial_scale=1.,axial_scale=.8,axial_shear=0.),rf_coordinates='axial')
        geometry=expected.case.to_dict()['geometry']
        with self.assertRaisesRegex(ValueError,'voltage_interval'):deform_curved_project(source,geometry,rf_coordinates='fixed',minimum_corner_angle_deg=1.)
        result=deform_curved_project(source,geometry,rf_coordinates='axis_fraction',minimum_corner_angle_deg=1.)
        np.testing.assert_allclose(result.case.acceleration_parameters[1],expected.case.acceleration_parameters[1],rtol=0,atol=1e-16)
        self.assertAlmostEqual(result.case.phase_origin_m,.056)

    def test_saved_native_and_declared_nonlinear_tracking_replay(self):
        from superfish_ng.curved_harmonic_deformation import deform_curved_project
        from superfish_ng import solve
        from superfish_ng.io import save_run
        from superfish_ng.saved import read_solution
        from superfish_ng.saved_mode_tracking import save_mode_tracking,read_mode_tracking
        from test_curved_piecewise_remesh_tracking import CONTROLS
        source,geometry=deformation_fixture()
        target=deform_curved_project(source,geometry,rf_coordinates='fixed',minimum_corner_angle_deg=1.)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name,project in (('source',source),('target',target)):
                solution=solve(project.case,mesh_data=project.mesh_data);save_run(project.case,solution,root/name)
                restored=read_solution(root/name)
                np.testing.assert_array_equal(restored.u,solution.u)
                self.assertEqual(restored.case,project.case)
            meshes=[dict(schema_version=2,source_mesh=p.mesh_data,curved_refinement_steps=p.case.to_dict()['mesh']['curved_refinement_steps']) for p in (source,target)]
            report=save_mode_tracking(dict(schema_version=1,previous_run='source',current_run='target',previous_ids=['A'],
                controls=dict(CONTROLS,comparison_meshes=meshes)),root/'tracking.json',base_directory=root)
            self.assertEqual(report['status'],'PASS');self.assertEqual(read_mode_tracking(root/'tracking.json'),report)

    def test_cli_preflights_folded_target_and_never_overwrites_source_or_output(self):
        import contextlib,io,json
        from superfish_ng.cli import main
        source,geometry=deformation_fixture()
        with tempfile.TemporaryDirectory() as tmp,contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            root=Path(tmp);src=root/'source.json';geo=root/'geometry.json';out=root/'target.json';source.save(src)
            geo.write_text(json.dumps(geometry));original=src.read_bytes()
            command=['deform-curved-project',str(src),'--geometry',str(geo),'--rf-coordinates','fixed','--minimum-corner-angle-deg','1','--out',str(out)]
            self.assertEqual(main(command),0);saved=out.read_bytes();Project.load(out)
            self.assertNotEqual(main(command),0);self.assertEqual(out.read_bytes(),saved)
            folded,invalid=folded_deformation_fixture();folded.save(root/'fold-source.json')
            geo.write_text(json.dumps(invalid));command[1]=str(root/'fold-source.json');command[-1]=str(root/'invalid.json')
            from superfish_ng.curved_harmonic_deformation import deform_curved_project
            with self.assertRaisesRegex(ValueError,'Jacobian'):
                deform_curved_project(folded,invalid,rf_coordinates='fixed',minimum_corner_angle_deg=1.)
            self.assertNotEqual(main(command),0);self.assertFalse((root/'invalid.json').exists())
            self.assertEqual(src.read_bytes(),original)

    def test_chord_interior_boundary_vertices_and_initial_uniform_levels(self):
        from superfish_ng import make_mesh
        from superfish_ng.curved_space import curved_space
        from superfish_ng.curved_harmonic_deformation import deform_curved_project
        source,geometry=deformation_fixture()
        case=replace(source.case,contour_mesh=replace(source.case.contour_mesh,max_edge_m=.025),
            curved_refinement_steps=(),curved_refinement_levels=1)
        source=Project(case);mesh=make_mesh(case);a=curved_space(case,mesh)
        fractions=a.geometry.boundary_parameters[a.geometry.boundary_curve_indices==1].ravel()
        self.assertTrue(any(abs(3*x-round(3*x))>.1 for x in fractions))
        target=deform_curved_project(source,geometry,rf_coordinates='fixed',minimum_corner_angle_deg=1.)
        b=curved_space(target.case,mesh_from_dict(target.case,target.mesh_data))
        np.testing.assert_array_equal(a.geometry.cell_nodes,b.geometry.cell_nodes)
        np.testing.assert_allclose(a.geometry.boundary_parameters,b.geometry.boundary_parameters,rtol=0,atol=2e-14)
        for nodes,owner,pair in zip(b.geometry.boundary_nodes,b.geometry.boundary_curve_indices,b.geometry.boundary_parameters):
            expected=target.case.curved_contour.curves[owner].evaluate([*pair,float(np.mean(pair))])['points_zr_m'][:,::-1]
            np.testing.assert_allclose(b.geometry.points_rz_m[nodes],expected,rtol=0,atol=2e-15)
        self.assertEqual(target.case.curved_refinement_levels,1)
        self.assertEqual(len(space(target).geometry.cell_nodes),4*len(mesh.triangles))
