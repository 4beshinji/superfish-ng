# SPDX-License-Identifier: Apache-2.0
"""Independent nonlinear shape points, actual comparison meshes and replay."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
import numpy as np
from superfish_ng.studies import Study,execute_study
from test_curved_harmonic_deformation import deformation_fixture,space


def harmonic_study_document(values=None):
    project,_=deformation_fixture()
    return dict(study_version=3,kind='curved_harmonic_sweep',project=project.to_dict(),parameter='shape_change',parameter_unit='1',
        values=[0.,1.] if values is None else values,rf_coordinates='fixed',minimum_corner_angle_deg=1.,geometry_coefficients={
            '/curves/1/center_zr_m/0':[.1,-.02],'/curves/2/center_zr_m/0':[.1,-.02],
            '/curves/1/semiaxes_m/0':[.1,.02],'/curves/2/semiaxes_m/0':[.1,-.02],
            '/curves/1/semiaxes_m/1':[.08,.01],'/curves/2/semiaxes_m/1':[.08,.01]})


def controls():
    return dict(mapping='piecewise_remesh',sample_order=5,minimum_overlap=.8,
        minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)


class CurvedHarmonicStudyTests(unittest.TestCase):
    def test_independent_shape_laws_preserve_geometry_moments_and_original_history(self):
        from scripts.validate_large_curved_mesh_selection import boundary_moments
        raw=harmonic_study_document([0.,.5,1.,0.]);before=deepcopy(raw)
        study=Study.from_dict(raw);projects=study.projects();self.assertEqual(study.to_dict(),raw)
        self.assertEqual(projects[0].to_dict(),projects[-1].to_dict());base=space(projects[0]);moments=boundary_moments(base)
        for value,project in zip(study.values,projects):
            geometry=space(project)
            np.testing.assert_array_equal(base.geometry.cell_nodes,geometry.geometry.cell_nodes)
            self.assertEqual(project.case.curved_refinement_steps,study.project.case.curved_refinement_steps)
            actual=boundary_moments(geometry);ratio=1+value/8
            self.assertAlmostEqual(actual['signed_area_m2']/moments['signed_area_m2'],ratio,places=12)
            self.assertAlmostEqual(actual['signed_volume_m3']/moments['signed_volume_m3'],ratio**2,places=12)
        self.assertEqual(raw,before)

    def test_actual_inserted_values_determine_comparison_meshes_and_units(self):
        from superfish_ng.study_shape_tracking import pair_controls
        study=Study.from_dict(harmonic_study_document())
        pair=pair_controls(study,controls(),0.,.5)
        projects=replace(study,values=[0.,.5]).projects()
        for document,project in zip(pair['comparison_meshes'],projects):
            self.assertEqual(document['source_mesh'],project.mesh_data)
            self.assertEqual(document['curved_refinement_steps'],project.case.to_dict()['mesh']['curved_refinement_steps'])
        endpoint=pair_controls(study,controls(),0.,1.)
        self.assertNotEqual(pair['comparison_meshes'][1],endpoint['comparison_meshes'][1])
        raw=harmonic_study_document([0.,.1]);raw['parameter_unit']='m'
        raw['geometry_coefficients']={p:[c[0],10*c[1]] for p,c in raw['geometry_coefficients'].items()}
        for a,b in zip(Study.from_dict(raw).projects(),Study.from_dict(harmonic_study_document()).projects()):
            np.testing.assert_allclose(a.mesh_data['points'],b.mesh_data['points'],rtol=0,atol=2e-15)
        with self.assertRaisesRegex(ValueError,'without comparison_meshes'):
            pair_controls(study,pair,0.,.5)

    def test_strict_versions_paths_laws_and_source_contracts(self):
        from test_curved_affine_study import affine_study_document
        raw=harmonic_study_document()
        invalid=[dict(raw,study_version=v) for v in (True,1,2,4)]
        invalid += [dict(raw,kind='curved_affine_sweep'),dict(raw,parameter=''),dict(raw,parameter_unit='mm'),
            dict(raw,rf_coordinates='axial'),dict(raw,minimum_corner_angle_deg=True),dict(raw,minimum_corner_angle_deg=60),
            dict(raw,affine_coefficients={}),dict(raw,geometry_coefficients={}),dict(raw,values=[True,1.]),dict(raw,values=[0.,10**400])]
        for path in ('/curves/-1/semiaxes_m/0','/curves/01/semiaxes_m/0','/curves/1/semiaxes_m/2','/curves/1/type','/curves/1/branch','/segments_per_curve/1','/chord_tolerance_m','/case/rf/beta'):
            invalid.append(dict(raw,geometry_coefficients={path:[1.,1.]}))
        for coeff in ([],[True,1.],[1.,float('nan')],[1.,10**400],[.08]):
            invalid.append(dict(raw,geometry_coefficients={'/curves/1/semiaxes_m/1':coeff}))
        missing=deepcopy(raw);del missing['minimum_corner_angle_deg'];invalid.append(missing)
        for bad in invalid:
            with self.subTest(bad=bad),self.assertRaises(ValueError):Study.from_dict(bad)
        self.assertEqual(Study.from_dict(affine_study_document()).to_dict()['study_version'],2)
        old=Study(Study.from_dict(raw).project,'fixed_geometry_convergence','additional_uniform_refinements',[0,1])
        self.assertEqual(old.to_dict()['study_version'],1);self.assertNotIn('geometry_coefficients',old.to_dict())
        unfrozen=deepcopy(raw)
        for step in unfrozen['project']['case']['mesh']['curved_refinement_steps']:step.pop('split_pattern',None)
        with self.assertRaisesRegex(ValueError,'freeze-curved-refinement'):Study.from_dict(unfrozen)

    def test_all_target_points_preflight_before_output_and_scalar_overflow_rejects(self):
        raw=harmonic_study_document([0.,-10.]);study=Study.from_dict(raw)
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'invalid'
            with self.assertRaises(ValueError):execute_study(study,target)
            self.assertFalse(target.exists())
        raw=harmonic_study_document([1.,1e100]);raw['geometry_coefficients']={'/curves/1/semiaxes_m/1':[0.,0.,0.,0.,1e100]}
        with self.assertRaisesRegex(ValueError,'finite range'):Study.from_dict(raw)

    def test_real_study_independent_spectra_and_derived_saved_tracking_replay(self):
        from superfish_ng.study_mode_tracking import build_study_mode_tracking,replay_study_mode_tracking
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);study=Study.from_dict(harmonic_study_document())
            report=execute_study(study,root/'study')
            self.assertEqual(report['numerical_status'],'UNVERIFIED');self.assertEqual(report['comparisons'],[])
            self.assertEqual(report['mode_tracking'],'not performed; independent spectra')
            self.assertIn('harmonic displacement',report['geometry_refinement'])
            request=dict(schema_version=1,study_run=str(root/'study'),initial_ids=['A'],step_controls=[controls()])
            tracked=build_study_mode_tracking(request)
            self.assertEqual(tracked['status'],'PASS');self.assertEqual(replay_study_mode_tracking(tracked),tracked)
            self.assertNotIn('comparison_meshes',tracked['request']['step_controls'][0])
            meshes=tracked['history']['steps'][0]['request']['controls']['comparison_meshes']
            self.assertNotEqual(meshes[0]['source_mesh']['points'],meshes[1]['source_mesh']['points'])
            bad=deepcopy(tracked);bad['history']['steps'][0]['request']['controls']['comparison_meshes'][1]['source_mesh']['points'][1][0]+=.001
            with self.assertRaises(ValueError):replay_study_mode_tracking(bad)

    def test_tracked_checkpoint_reuses_points_and_preserves_shape_laws(self):
        from superfish_ng.tracked_study import execute_tracked_study,replay_tracked_study
        request=dict(schema_version=1,study=harmonic_study_document(),initial_ids=['A'],step_controls=[controls()])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);first=execute_tracked_study(request,root/'first',max_new_points=1)
            self.assertEqual(first['status'],'PAUSED')
            final=execute_tracked_study(request,root/'rest',checkpoint=first)
            self.assertEqual(final['status'],'COMPLETE');self.assertEqual(final['point_runs'][0],first['point_runs'][0])
            self.assertEqual(replay_tracked_study(final),final)
            bad=deepcopy(request);bad['study']['geometry_coefficients']['/curves/1/semiaxes_m/1'][1]=.011
            with self.assertRaises(ValueError):execute_tracked_study(bad,root/'bad',checkpoint=first)
            self.assertFalse((root/'bad').exists())

    def test_adaptive_midpoint_is_derived_after_pause_without_reusing_endpoint_mesh(self):
        from superfish_ng.adaptive_study import execute_adaptive_study,replay_adaptive_study
        request=dict(schema_version=1,study=harmonic_study_document(),initial_ids=['A'],
            step_controls=[dict(controls(),minimum_overlap=1.)],adaptive=dict(max_depth=1,max_attempts=4,minimum_parameter_step=.001))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);first=execute_adaptive_study(request,root/'first',max_new_attempts=1)
            self.assertEqual(first['status'],'PAUSED');self.assertEqual(first['attempts'][0]['decision'],'BISECT')
            final=execute_adaptive_study(request,root/'rest',checkpoint=first)
            self.assertEqual(final['status'],'UNVERIFIED');self.assertEqual(final['points'][:2],first['points'])
            self.assertEqual(final['points'][2]['value'],.5);self.assertEqual(final['attempts'][1]['decision'],'STOP')
            endpoints=final['attempts'][0]['correspondence']['request']['controls']['comparison_meshes']
            midpoints=final['attempts'][1]['correspondence']['request']['controls']['comparison_meshes']
            self.assertEqual(endpoints[0],midpoints[0]);self.assertNotEqual(endpoints[1],midpoints[1])
            self.assertEqual(replay_adaptive_study(final),final)

    def test_quadratic_laws_and_metre_reparameterization_follow_independent_geometry(self):
        from scripts.validate_large_curved_mesh_selection import boundary_moments
        raw=harmonic_study_document([0.,.5,1.])
        raw['geometry_coefficients']={path:[cs[0],0.,cs[1]] for path,cs in raw['geometry_coefficients'].items()}
        study=Study.from_dict(raw);projects=study.projects();base=boundary_moments(space(projects[0]))
        unit=deepcopy(raw);unit['parameter_unit']='m';unit['values']=[x/10 for x in raw['values']]
        unit['geometry_coefficients']={path:[cs[0],0.,100*cs[2]] for path,cs in raw['geometry_coefficients'].items()}
        for x,project,metres in zip(study.values,projects,Study.from_dict(unit).projects()):
            radius=.08+.01*x*x
            self.assertAlmostEqual(project.case.curved_contour.curves[1].semiaxes_m[1],radius,places=15)
            moments=boundary_moments(space(project));ratio=radius/.08
            self.assertAlmostEqual(moments['signed_area_m2']/base['signed_area_m2'],ratio,places=12)
            self.assertAlmostEqual(moments['signed_volume_m3']/base['signed_volume_m3'],ratio**2,places=12)
            np.testing.assert_allclose(project.mesh_data['points'],metres.mesh_data['points'],rtol=0,atol=2e-15)
