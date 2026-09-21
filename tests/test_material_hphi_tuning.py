# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from dataclasses import replace
from unittest.mock import patch
import unittest
import numpy as np
from scripts.material_hphi_reference import layered_partition,layered_reference
from superfish_ng.material_hphi import MaterialHphiCase,solve_material_hphi
from superfish_ng.hphi_project import HphiProject
from superfish_ng.material_hphi_shape_tuning import MaterialHphiShapeLaw
from superfish_ng.hphi_tracking import HphiTrackingControls
from superfish_ng.material_hphi_tuning import validate_material_hphi_tune,run_material_hphi_tune,assess_material_hphi_tune,trial_material_hphi_project


def request():
    p=HphiProject(MaterialHphiCase(layered_partition(1,12),modes=3))
    frequency=float(layered_reference(1)[0]['frequency_hz'])
    return dict(format='superfish_ng_material_hphi_tune',schema_version=1,project=p.to_dict(),
        parameter='deformation',shape_law=MaterialHphiShapeLaw('uniform_scale').to_dict(),bounds=[1.,1.2],target_hz=frequency/1.1,
        frequency_tolerance_hz=frequency*.001,mesh_frequency_tolerance_hz=frequency*.001,
        parameter_tolerance=1e-6,max_trials=8,initial_ids=['first','second'],mode_id='first',
        controls=HphiTrackingControls().to_dict(),refinement_levels=1,max_triangles=10000,max_dofs=10000,
        max_sample_points=2000000,max_interface_tests=2000000,max_interface_pieces=250000,identity_recovery=None)


class MaterialHphiTuningTests(unittest.TestCase):
    def test_strict_request_and_preflight(self):
        q=request();validate_material_hphi_tune(q)
        for name,value in (('schema_version',True),('target_hz',np.float64(1.)),('extra',1),('max_sample_points',1),('max_dofs',1),
                           ('max_triangles',1),('refinement_levels',9),('initial_ids',['a','a']),('max_interface_tests',False)):
            bad=deepcopy(q);bad[name]=value
            with self.assertRaises(ValueError):validate_material_hphi_tune(bad)
        bad=deepcopy(q);bad['controls']['max_dofs']=1
        with patch.object(MaterialHphiShapeLaw,'apply',side_effect=AssertionError('budget first')):
            with self.assertRaises(ValueError):validate_material_hphi_tune(bad)

    def test_independent_two_layer_actual_tune_and_final_refinement(self):
        q=request();before=deepcopy(q);run=run_material_hphi_tune(q)
        self.assertEqual(run.report['status'],'TUNED',run.report['decision'])
        trials=run.report['trials'];self.assertEqual([t['value'] for t in trials],[1.,1.2,1.1,1.1])
        self.assertEqual([t['parent_index'] for t in trials],[None,0,0,2])
        self.assertTrue(run.report['decision']['refined_target_met']);self.assertTrue(run.report['decision']['mesh_difference_met'])
        self.assertTrue(all(t['tracking']['individual_ids_complete'] for t in trials))
        self.assertEqual(q,before)
        for trial,project in zip(trials,run.projects):
            np.testing.assert_allclose(trial['frequency_hz'],layered_reference(1,trial['value'])[0]['frequency_hz'],rtol=.001)
            self.assertEqual([(m.epsilon_r,m.mu_r) for m in project.case.partition.materials],[(1.,1.),(4.,1.)])

    def test_guard_never_evaluates_frequency_or_recovers(self):
        q=request();q['controls']['relative_cluster_gap']=.9
        q['identity_recovery']=dict(anchor_selection='latest_resolved_trial',controls=HphiTrackingControls().to_dict())
        with patch('superfish_ng.material_hphi_tuning._recover_trial',side_effect=AssertionError('guard bypass')):
            run=run_material_hphi_tune(q)
        self.assertEqual(run.report['status'],'UNVERIFIED');self.assertEqual(len(run.report['trials']),1)
        self.assertIsNone(run.report['trials'][0]['frequency_hz']);self.assertIsNone(run.report['trials'][0]['identity_recovery'])

    def test_reader_duplicate_keys_and_recovery_policy(self):
        import json,tempfile
        from pathlib import Path
        from superfish_ng.material_hphi_tuning import read_material_hphi_tune_request
        q=request()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'request.json';path.write_text(json.dumps(q))
            self.assertEqual(read_material_hphi_tune_request(path),q)
            path.write_text(json.dumps(q)[:-1]+',"max_trials":8}')
            with self.assertRaises(ValueError):read_material_hphi_tune_request(path)
        for policy in ({'anchor_selection':'guess','controls':q['controls']},
                       {'anchor_selection':'fixed_trial','anchor_trial_index':True,'controls':q['controls']},
                       {'anchor_selection':'latest_resolved_trial','anchor_trial_index':0,'controls':q['controls']}):
            bad=deepcopy(q);bad['identity_recovery']=policy
            with self.assertRaises(ValueError):validate_material_hphi_tune(bad)

    def test_reassessment_requires_original_material_solution(self):
        q=request();empty=assess_material_hphi_tune(q,[])
        self.assertEqual(empty.report['status'],'PAUSED')
        p=trial_material_hphi_project(q,1.,'search');s=solve_material_hphi(p.case)
        for bad in (replace(s,coefficients=s.coefficients*1.01),replace(s,frequencies_hz=s.frequencies_hz*1.01),{'frequency_hz':q['target_hz']}):
            with self.assertRaises(ValueError):assess_material_hphi_tune(q,[bad])
        with self.assertRaises(ValueError):trial_material_hphi_project(q,1.3,'search')


if __name__=='__main__':unittest.main()
