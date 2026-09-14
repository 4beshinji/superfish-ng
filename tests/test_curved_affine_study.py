# SPDX-License-Identifier: Apache-2.0
"""Declared shape sweeps preserve reference ancestry and derive pair maps."""
from copy import deepcopy
from dataclasses import replace
import tempfile
from pathlib import Path
import unittest
import numpy as np
from superfish_ng.studies import Study,execute_study
from superfish_ng.frozen_curved_refinement import freeze_curved_refinement
from superfish_ng.curved_project_transform import transform_curved_project
from superfish_ng.saved import read_solution
from test_frozen_curved_refinement import marked_project,native_space


def affine_study_document(values=None):
    return dict(study_version=2,project=freeze_curved_refinement(marked_project()).to_dict(),
        kind='curved_affine_sweep',parameter='shape_scale',parameter_unit='1',
        values=[1.,2.] if values is None else values,
        affine_coefficients=dict(radial_scale=[0.,2.],axial_scale=[0.,.5],axial_shear=[0.]),
        rf_coordinates='axial')


def controls():
    return dict(mapping='affine_remesh',sample_order=5,minimum_overlap=.8,
        minimum_assignment_margin=.05,relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8)


class CurvedAffineStudyTests(unittest.TestCase):
    def test_independent_points_preserve_frozen_restrictions_and_exact_affine_coordinates(self):
        raw=affine_study_document([1.,2.,1.]);before=deepcopy(raw)
        study=Study.from_dict(raw);self.assertEqual(study.to_dict(),raw)
        projects=study.projects();self.assertEqual(projects[0].to_dict(),projects[2].to_dict())
        base=native_space(study.project)
        for value,project in zip(study.values,projects):
            space=native_space(project)
            self.assertEqual(project.case.curved_refinement_steps,study.project.case.curved_refinement_steps)
            np.testing.assert_array_equal(base.geometry.cell_nodes,space.geometry.cell_nodes)
            np.testing.assert_allclose(space.geometry.points_rz_m,base.geometry.points_rz_m*[2*value,.5*value],rtol=0,atol=2e-15)
        self.assertEqual(raw,before)

    def test_real_independent_spectra_obey_maxwell_scaling_without_false_convergence(self):
        study=Study.from_dict(affine_study_document())
        with tempfile.TemporaryDirectory() as tmp:
            report=execute_study(study,Path(tmp)/'study')
            self.assertEqual(report['comparisons'],[]);self.assertEqual(report['numerical_status'],'UNVERIFIED')
            self.assertEqual(report['mode_tracking'],'not performed; independent spectra')
            self.assertIn('declared affine',report['geometry_refinement'])
            a,b=[point['modes'][0] for point in report['points']]
            self.assertLess(abs(2*b['frequency_hz']/a['frequency_hz']-1),1e-10)
            for key in ('r_over_q_accelerator_ohm','r_over_q_circuit_ohm','geometry_factor_ohm','transit_time_factor_abs'):
                self.assertLess(abs(b[key]/a[key]-1),1e-9)
            for point,project in zip(report['points'],study.projects()):
                native=read_solution(Path(tmp)/'study'/point['directory']/'solution')
                self.assertEqual(native.case,project.case)

    def test_strict_version_laws_units_and_physics(self):
        raw=affine_study_document()
        variants=[dict(raw,study_version=True),dict(raw,study_version=1),dict(raw,study_version=3),
            dict(raw,kind='sweep'),dict(raw,parameter=''),dict(raw,parameter_unit='mm'),
            dict(raw,rf_coordinates='automatic'),dict(raw,unknown=0),dict(raw,affine_coefficients=None),
            dict(raw,values=[True,1]),dict(raw,values=[0,10**400]),
            dict(raw,affine_coefficients=dict(radial_scale=[1],axial_scale=[1],axial_shear=[0])),
            dict(raw,affine_coefficients=dict(raw['affine_coefficients'],radial_scale=[True,1]))]
        missing=deepcopy(raw);del missing['rf_coordinates'];variants.append(missing)
        te=deepcopy(raw)
        from superfish_ng.model import Model
        te['project']['case']['model']=replace(Model(),polarization='te').to_dict();variants.append(te)
        for bad in variants:
            with self.subTest(bad=bad),self.assertRaises(ValueError):Study.from_dict(bad)
        previous=Study(marked_project(),'fixed_geometry_convergence','additional_uniform_refinements',[0,1])
        self.assertEqual(previous.to_dict()['study_version'],1)
        self.assertNotIn('affine_coefficients',previous.to_dict())

    def test_polynomial_units_and_pair_maps_are_independently_consistent(self):
        from superfish_ng.curved_affine_study import pair_controls,value_map
        raw=affine_study_document([1.,1.25,2.]);raw['affine_coefficients']['radial_scale']=[0.,0.,2.]
        raw['affine_coefficients']['axial_shear']=[-.125,.125]
        study=Study.from_dict(raw)
        for x in study.values:
            m=value_map(study,x)
            self.assertEqual(m,dict(radial_scale=2*x*x,axial_scale=.5*x,axial_shear=.125*(x-1)))
        a,b=[value_map(study,x) for x in (1.25,2.)]
        def matrix(m):return np.array([[m['radial_scale'],0],[m['axial_shear'],m['axial_scale']]])
        control=pair_controls(study,controls(),1.25,2.)
        np.testing.assert_allclose(matrix(control['affine_map'])@matrix(a),matrix(b),rtol=0,atol=2e-15)
        raw=affine_study_document([.1,.2]);raw['parameter_unit']='m'
        raw['affine_coefficients']=dict(radial_scale=[0.,20.],axial_scale=[0.,5.],axial_shear=[0.])
        for a,b in zip(Study.from_dict(raw).projects(),Study.from_dict(affine_study_document()).projects()):
            self.assertEqual(a.to_dict(),b.to_dict())
        with self.assertRaisesRegex(ValueError,'without affine_map'):
            pair_controls(study,dict(controls(),affine_map=value_map(study,1.)),1.,2.)

    def test_invalid_point_and_unfrozen_connectivity_are_rejected_before_output(self):
        study=Study.from_dict(affine_study_document())
        study.affine_coefficients['axial_scale']=[1.,-1.]
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'invalid'
            with self.assertRaises(ValueError):execute_study(study,target)
            self.assertFalse(target.exists())
        raw=affine_study_document();raw['project']=marked_project().to_dict()
        with self.assertRaisesRegex(ValueError,'connectivity'):Study.from_dict(raw).projects()
        raw=affine_study_document();raw['rf_coordinates']='fixed'
        with self.assertRaises(ValueError):Study.from_dict(raw).projects()

    def test_completed_study_tracking_uses_declared_adjacent_maps_and_replays(self):
        from superfish_ng.study_mode_tracking import build_study_mode_tracking,replay_study_mode_tracking
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);study=Study.from_dict(affine_study_document([1.,2.,1.]))
            execute_study(study,root/'study')
            request=dict(schema_version=1,study_run=str(root/'study'),initial_ids=['A'],step_controls=[controls(),controls()])
            result=build_study_mode_tracking(request)
            self.assertEqual(result['status'],'PASS');self.assertEqual(replay_study_mode_tracking(result),result)
            maps=[step['request']['controls']['affine_map'] for step in result['history']['steps']]
            self.assertEqual([m['radial_scale'] for m in maps],[2.,.5])
            self.assertNotIn('affine_map',result['request']['step_controls'][0])
            bad=deepcopy(result);bad['request']['step_controls'][0]['affine_map']=maps[0]
            with self.assertRaisesRegex(ValueError,'without affine_map'):replay_study_mode_tracking(bad)

    def test_tracked_and_adaptive_pause_resume_preserve_laws_and_actual_pair_values(self):
        from superfish_ng.tracked_study import execute_tracked_study,replay_tracked_study
        from superfish_ng.adaptive_study import execute_adaptive_study,replay_adaptive_study
        request=dict(schema_version=1,study=affine_study_document([1.,1.1,1.2]),initial_ids=['A'],step_controls=[controls(),controls()])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            first=execute_tracked_study(request,root/'first',max_new_points=1)
            self.assertEqual(first['status'],'PAUSED')
            result=execute_tracked_study(request,root/'rest',checkpoint=first)
            self.assertEqual(result['status'],'COMPLETE');self.assertEqual(replay_tracked_study(result),result)
            adaptive=dict(request,adaptive=dict(max_depth=3,max_attempts=8,minimum_parameter_step=.001))
            first=execute_adaptive_study(adaptive,root/'adaptive-first',max_new_attempts=1)
            self.assertEqual(first['status'],'PAUSED')
            result=execute_adaptive_study(adaptive,root/'adaptive-rest',checkpoint=first)
            self.assertEqual(result['status'],'COMPLETE');self.assertEqual(replay_adaptive_study(result),result)
            for attempt in result['attempts']:
                a,b=[result['points'][attempt[key]]['value'] for key in ('previous_point','current_point')]
                self.assertAlmostEqual(attempt['correspondence']['request']['controls']['affine_map']['radial_scale'],b/a)
