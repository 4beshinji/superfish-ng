# SPDX-License-Identifier: Apache-2.0
"""Non-affine tuning: independent geometry moments and native trial ancestry."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
import json
import numpy as np
from superfish_ng.tuning import _request, _project, execute_tune, replay_tune
from test_curved_harmonic_study import harmonic_study_document, controls
from test_curved_harmonic_deformation import space


def harmonic_request():
    study=harmonic_study_document()
    return dict(schema_version=5,project=study['project'],parameter=study['parameter'],parameter_unit='1',
        geometry_coefficients=study['geometry_coefficients'],rf_coordinates='fixed',minimum_corner_angle_deg=1.,
        bounds=[0.,1.],target_hz=1.6e9,frequency_tolerance_hz=1e6,parameter_tolerance=1e-8,max_trials=12,
        initial_ids=['A'],mode_id='A',controls=controls(),refinement_scale=2,mesh_frequency_tolerance_hz=1e6)


class CurvedHarmonicTuningTests(unittest.TestCase):
    def test_nonaffine_quadratic_laws_obey_independent_area_volume_and_units(self):
        from scripts.validate_large_curved_mesh_selection import boundary_moments
        request=harmonic_request()
        request['geometry_coefficients']={p:[c[0],0.,c[1]] for p,c in request['geometry_coefficients'].items()}
        original=deepcopy(request);_request(request)
        base=boundary_moments(space(_project(request,0.,'search')))
        metres=deepcopy(request);metres.update(parameter_unit='m',bounds=[0.,.1])
        metres['geometry_coefficients']={p:[c[0],0.,100*c[2]] for p,c in request['geometry_coefficients'].items()}
        for value in (0.,.5,1.):
            project=_project(request,value,'search');geometry=space(project)
            moments=boundary_moments(geometry);ratio=1+value**2/8
            self.assertAlmostEqual(moments['signed_area_m2']/base['signed_area_m2'],ratio,places=12)
            self.assertAlmostEqual(moments['signed_volume_m3']/base['signed_volume_m3'],ratio**2,places=12)
            np.testing.assert_allclose(project.mesh_data['points'],_project(metres,value/10,'search').mesh_data['points'],rtol=0,atol=2e-15)
            self.assertEqual(project.case.to_dict()['mesh']['curved_refinement_steps'],request['project']['case']['mesh']['curved_refinement_steps'])
        self.assertEqual(request,original)

    def test_final_refinement_keeps_quadratic_domain_and_search_comparison_partition(self):
        from superfish_ng.curved_harmonic_tuning import pair_controls
        request=harmonic_request();coarse=_project(request,.5,'search');fine=_project(request,.5,'refinement')
        first,second=space(coarse),space(fine)
        from scripts.validate_large_curved_mesh_selection import boundary_moments
        for key in ('signed_area_m2','signed_volume_m3'):
            self.assertAlmostEqual(boundary_moments(first)[key],boundary_moments(second)[key],places=15)
        self.assertEqual(len(second.geometry.cell_nodes),4*len(first.geometry.cell_nodes))
        self.assertEqual(coarse.case.curved_contour,fine.case.curved_contour)
        self.assertEqual(coarse.mesh_data,fine.mesh_data)
        pair=pair_controls(request,coarse,fine)
        self.assertEqual(pair['comparison_meshes'][0],pair['comparison_meshes'][1])
        self.assertEqual(pair['comparison_meshes'][0]['curved_refinement_steps'],request['project']['case']['mesh']['curved_refinement_steps'])

    def test_strict_physics_laws_frozen_history_and_derived_controls(self):
        request=harmonic_request()
        invalid=[dict(request,schema_version=v) for v in (True,1,2,3,4,6)]
        invalid += [dict(request,geometry_coefficients={}),dict(request,rf_coordinates='axial'),
            dict(request,minimum_corner_angle_deg=True),dict(request,refinement_scale=3),
            dict(request,controls=dict(request['controls'],comparison_meshes=[])),
            dict(request,controls=dict(request['controls'],mapping='affine_remesh'))]
        for law in ({'/curves/01/semiaxes_m/1':[.08,.01]},
                    {'/curves/1/branch':[1,1]}, {'/curves/1/semiaxes_m/1':[.08,True]},
                    {'/curves/1/semiaxes_m/1':[.08,float('inf')]}):
            invalid.append(dict(request,geometry_coefficients=law))
        unfrozen=deepcopy(request)
        for step in unfrozen['project']['case']['mesh']['curved_refinement_steps']:step.pop('split_pattern',None)
        invalid.append(unfrozen)
        for bad in invalid:
            with self.subTest(bad=bad),self.assertRaises(ValueError):_request(bad)
        same=deepcopy(request)
        same['geometry_coefficients']={p:[c[0],c[1],-c[1]] for p,c in request['geometry_coefficients'].items()}
        with self.assertRaisesRegex(ValueError,'do not change'):_request(same)

    def test_real_endpoint_parent_refinement_replay_and_tamper_rejection(self):
        from superfish_ng import solve
        request=harmonic_request();initial=_project(request,0.,'search')
        request['target_hz']=float(solve(initial.case,mesh_data=initial.mesh_data).frequencies_hz[0])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);first=execute_tune(request,root/'first',max_new_trials=2)
            self.assertEqual(first['decision']['next_trial'],dict(value=0.,phase='refinement',parent_index=0))
            final=execute_tune(request,root/'resumed',checkpoint=first)
            self.assertEqual(final['status'],'TUNED');self.assertEqual(replay_tune(final),final)
            self.assertEqual(final['trial_sources_sha256'][:2],first['trial_sources_sha256'])
            meshes=final['trials'][-1]['tracking']['request']['controls']['comparison_meshes']
            self.assertEqual(meshes[0],meshes[1])
            self.assertNotEqual(meshes[0],first['trials'][1]['tracking']['request']['controls']['comparison_meshes'][1])
            for target in ('request','comparison','parent'):
                bad=deepcopy(final)
                if target=='request':bad['request']['geometry_coefficients']['/curves/1/semiaxes_m/1'][1]=.02
                elif target=='comparison':bad['trials'][-1]['tracking']['request']['controls']['comparison_meshes'][1]['source_mesh']['points'][1][0]+=.001
                else:bad['trials'][-1]['parent_index']=1
                with self.subTest(target=target),self.assertRaises(ValueError):replay_tune(bad)

    def test_gui_string_request_preserves_laws_and_rejects_duplicate_keys_before_launch(self):
        from superfish_ng.gui_tuning import tuning_response
        request=harmonic_request();manager=Mock();manager.start_tune.return_value='example-job'
        self.assertEqual(tuning_response(manager,'start-tune',dict(request=json.dumps(request),max_new_trials=1)),dict(id='example-job'))
        manager.start_tune.assert_called_once_with(request,max_new_trials=1)
        manager.reset_mock()
        duplicate=json.dumps(request).replace('"schema_version": 5','"schema_version": 5, "schema_version": 5',1)
        with self.assertRaisesRegex(ValueError,'duplicate'):tuning_response(manager,'start-tune',dict(request=duplicate))
        manager.start_tune.assert_not_called()
