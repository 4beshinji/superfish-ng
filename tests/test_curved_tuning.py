# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import time
import unittest
from superfish_ng import solve
from superfish_ng.project import Project
from superfish_ng.tuning import _request,_project,execute_tune,replay_tune
from superfish_ng.saved import read_solution
from test_curve_partitions import partition_case


def curved_request():
    case=replace(partition_case(),curved_refinement_levels=1)
    initial=solve(case)
    return dict(schema_version=4,project=Project(case,mesh_data=initial.source_mesh_data).to_dict(),
        parameter='shape_scale',parameter_unit='1',affine_coefficients=dict(radial_scale=[0.,1.],axial_scale=[0.,1.],axial_shear=[0.]),
        rf_coordinates='axial',bounds=[1.,1.2],target_hz=float(initial.frequencies_hz[0])/1.1,
        frequency_tolerance_hz=5e4,parameter_tolerance=1e-8,max_trials=12,initial_ids=['A'],mode_id='A',
        controls=dict(mapping='affine_remesh',sample_order=5,minimum_overlap=.8,minimum_assignment_margin=.05,
            relative_cluster_gap=1e-6,minimum_relative_singular_value=1e-8),refinement_scale=2,mesh_frequency_tolerance_hz=5e4)


class CurvedTuningTests(unittest.TestCase):
    def test_native_fem_pause_resume_relative_tracking_and_fixed_geometry_refinement(self):
        r=curved_request();_request(r)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);first=execute_tune(r,root/'first',max_new_trials=2)
            final=execute_tune(r,root/'resumed',checkpoint=first)
            self.assertEqual(final['status'],'TUNED');self.assertAlmostEqual(final['decision']['value'],1.1)
            self.assertEqual(replay_tune(final),final)
            self.assertEqual(final['trial_sources_sha256'][:2],first['trial_sources_sha256'])
            for trial in final['trials'][1:]:
                parent=final['trials'][trial['parent_index']]
                mapping=trial['tracking']['request']['controls']['affine_map']
                self.assertAlmostEqual(mapping['radial_scale'],trial['value']/parent['value'])
                self.assertAlmostEqual(mapping['axial_scale'],trial['value']/parent['value'])
            last=read_solution(Path(final['trial_runs'][-1])/'solution')
            previous=read_solution(Path(final['trial_runs'][final['trials'][-1]['parent_index']])/'solution')
            self.assertEqual(len(last.space.geometry.cell_nodes),4*len(previous.space.geometry.cell_nodes))
            self.assertEqual(last.case.curved_contour,previous.case.curved_contour)
            self.assertEqual(last.source_mesh_data,previous.source_mesh_data)
            changed=deepcopy(first);changed['request']['affine_coefficients']['radial_scale']=[0.,1.01]
            with self.assertRaises(ValueError):replay_tune(changed)

    def test_strict_map_laws_and_refinement_contract(self):
        r=curved_request()
        for change in ({'affine_coefficients':{}},{'rf_coordinates':'auto'},{'refinement_scale':3},
                       {'controls':dict(r['controls'],affine_map={})}):
            with self.subTest(change=change),self.assertRaises(ValueError):_request(dict(r,**change))
        for coefficients in ([],None,[True],[float('inf')],[10**400],[1.],[0.,0.]):
            bad=deepcopy(r)
            for key in ('radial_scale','axial_scale'):bad['affine_coefficients'][key]=coefficients
            with self.subTest(coefficients=coefficients),self.assertRaises(ValueError):_request(bad)
        old=deepcopy(r);old['schema_version']=3
        with self.assertRaises(ValueError):_request(old)

    def test_invalid_interior_keeps_prior_native_checkpoints(self):
        r=curved_request();r['bounds']=[0.,1.]
        r['affine_coefficients']=dict(radial_scale=[1.,-5.,5.2],axial_scale=[1.,-5.,5.2],axial_shear=[0.])
        _request(r)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);first=execute_tune(r,root/'first',max_new_trials=2)
            self.assertEqual(first['decision']['next_trial']['value'],.5)
            with self.assertRaises(ValueError):execute_tune(r,root/'invalid',checkpoint=first)
            self.assertEqual(replay_tune(first),first)
            self.assertTrue((root/'invalid/failure-003.json').is_file())
            self.assertFalse((root/'invalid/checkpoint-003.json').exists())

    def test_dimensioned_parameter_reproduces_same_project(self):
        r=curved_request();length=deepcopy(r);length['parameter_unit']='m';length['bounds']=[.1,.12]
        for key in ('radial_scale','axial_scale'):length['affine_coefficients'][key]=[0.,10.]
        self.assertEqual(_project(r,1.,'search').to_dict(),_project(length,.1,'search').to_dict())

    def test_cli_pause_and_restarted_manager_resume_replay(self):
        from superfish_ng.cli import main
        from superfish_ng.jobs import JobManager
        from superfish_ng.tuning import read_tune
        r=curved_request()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);file=root/'request.json';file.write_text(json.dumps(r))
            self.assertEqual(main(['tune',str(file),'--out',str(root/'cli'),'--max-new-trials','2']),0)
            checkpoint=root/'cli/checkpoint-002.json'
            self.assertEqual(main(['replay-tune',str(checkpoint)]),0)
            manager=JobManager(root/'jobs')
            try:
                identifier=manager.start_tune(r,checkpoint=read_tune(checkpoint))
                deadline=time.monotonic()+60
                while manager.status(identifier)['status'] in ('queued','running') and time.monotonic()<deadline:
                    time.sleep(.025)
                self.assertEqual(manager.status(identifier,verify=True)['tuning_status'],'TUNED')
            finally:manager.close()
            manager=JobManager(root/'jobs')
            try:self.assertEqual(manager.status(identifier,verify=True)['tuning_status'],'TUNED')
            finally:manager.close()
