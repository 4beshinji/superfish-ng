# SPDX-License-Identifier: Apache-2.0
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from functools import lru_cache
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from scipy.special import jn_zeros
from superfish_ng.constants import C0,TAU
from superfish_ng.planar_project import PlanarProject
from superfish_ng.planar_curved import PlanarCurvedCase
from superfish_ng.planar_curved_refinement import refine_planar_curved_domain
from superfish_ng.planar_affine_shape import PlanarAffineShapeLaw
from superfish_ng.planar_curved_shape import PlanarCurvedAffineShapeLaw
from superfish_ng.planar_curved_tracking import PlanarCurvedTrackingControls
from test_planar_curved import curved_ellipse


@contextmanager
def workspace(label):
    saved=os.environ.get('SUPERFISH_CURVED_TUNING_TEST_ROOT')
    if saved:
        root=Path(saved)/label;root.mkdir(parents=True,exist_ok=False);yield root
    else:
        with tempfile.TemporaryDirectory() as tmp:yield Path(tmp)


@lru_cache(maxsize=2)
def domain(axes):
    g=curved_ellipse(16,axes=axes,shift=(0.,0.))
    for _ in range(2):g=refine_planar_curved_domain(g,max_geometry_boxes=10000000).domain
    return g


def circle_request():
    project=PlanarProject(PlanarCurvedCase(domain((.02,.02)),'tm',modes=3,quadrature_order=16,
        max_geometry_boxes=10000000,normalization_j_per_m=1.3))
    law=PlanarCurvedAffineShapeLaw(PlanarAffineShapeLaw([[[0,1],[0]],[[0],[0,1]]],[[0],[0]],[1.,1.4]))
    target=C0/TAU*jn_zeros(0,1)[0]/(.02*1.2)
    return dict(format='superfish_ng_planar_curved_tune',schema_version=1,
        project=project.to_dict(),parameter='deformation',shape_law=law.to_dict(),bounds=[1.,1.4],
        target_hz=float(target),frequency_tolerance_hz=float(target*1e-3),parameter_tolerance=1e-8,
        max_trials=8,initial_ids=['TM-fundamental'],mode_id='TM-fundamental',
        controls=PlanarCurvedTrackingControls().to_dict(),refinement_levels=1,max_triangles=10000,
        max_dofs=20000,mesh_frequency_tolerance_hz=float(target*2e-4),identity_recovery=None)


def small_request(polarization='tm'):
    raw=circle_request()
    raw['project']=PlanarProject(PlanarCurvedCase(curved_ellipse(16,axes=(.02,.02),shift=(0.,0.)),
        polarization,modes=3,quadrature_order=16,normalization_j_per_m=1.3)).to_dict()
    if polarization=='te':raw.update(initial_ids=['a','b'],mode_id='a')
    return raw


def elliptical_request():
    from scipy.linalg import eigh
    from superfish_ng.planar_curved_solver import planar_curved_matrices
    from superfish_ng.planar_curved_tuning_trials import generate_planar_curved_trial
    project=PlanarProject(PlanarCurvedCase(domain((.018,.020)),'te',modes=3,quadrature_order=16,
        max_geometry_boxes=10000000,normalization_j_per_m=1.3))
    u=np.array([np.cos(np.pi/7),np.sin(np.pi/7)]);delta=.0208/.018-1
    law=PlanarCurvedAffineShapeLaw(PlanarAffineShapeLaw(
        [[[1,float(delta*u[0]**2)],[0,float(delta*u[0]*u[1])]],
         [[0,float(delta*u[0]*u[1])],[1,float(delta*u[1]**2)]]],[[0],[0]],[0.,1.]))
    final=generate_planar_curved_trial(project,law,1.,refinement_levels=1,max_triangles=10000,max_dofs=20000)
    _,k,m,_=planar_curved_matrices(final.project.case)
    values=eigh(k.toarray(),m.toarray(),eigvals_only=True,subset_by_index=[0,2])
    # Independent dense generalized spectrum includes the TE constant kernel.
    assert abs(values[0])<1e-7*values[1]
    target=C0/TAU*np.sqrt(values[1])
    raw=circle_request();raw.update(project=project.to_dict(),shape_law=law.to_dict(),bounds=[0.,1.],
        target_hz=float(target),frequency_tolerance_hz=float(target*1e-3),
        mesh_frequency_tolerance_hz=float(target*2e-4),initial_ids=['even-x','odd-x'],mode_id='odd-x',
        controls=replace(PlanarCurvedTrackingControls(),relative_cluster_gap=.08).to_dict(),
        identity_recovery=dict(anchor_selection='fixed_trial',anchor_trial_index=0,
            controls=PlanarCurvedTrackingControls().to_dict()))
    return raw


class PlanarCurvedTuningTests(unittest.TestCase):
    def test_malformed_checkpoint_is_rejected_before_field_reconstruction(self):
        from superfish_ng.planar_curved_tuning import replay_planar_curved_tune
        for document in ({},[],None,dict(request={})):
            with self.subTest(document=document),self.assertRaises(ValueError):
                replay_planar_curved_tune(document)

    def test_real_circle_tm_two_frequency_gates_and_full_native_replay(self):
        from superfish_ng.planar_curved_tuning import execute_planar_curved_tune,replay_planar_curved_tune
        raw=circle_request()
        with workspace('circle') as root:
            first=execute_planar_curved_tune(raw,root/'first',max_new_trials=2)
            self.assertEqual(first['status'],'PAUSED')
            before={str(p):p.read_bytes() for run in first['trial_runs'] for p in Path(run).rglob('*') if p.is_file()}
            final=execute_planar_curved_tune(raw,root/'rest',checkpoint=first)
            self.assertEqual(final['status'],'TUNED',final['decision'])
            self.assertTrue(final['decision']['refined_target_met']);self.assertTrue(final['decision']['mesh_difference_met'])
            self.assertEqual(final['trials'][-1]['phase'],'refinement')
            self.assertLess(abs(final['trials'][-1]['frequency_hz']/raw['target_hz']-1),1e-4)
            self.assertEqual(replay_planar_curved_tune(final),final)
            from superfish_ng.tuning import _decision
            strict=deepcopy(raw);strict['mesh_frequency_tolerance_hz']=1.
            gate=_decision(strict,final['trials'])
            self.assertEqual(gate['status'],'REFINEMENT_FAILED')
            self.assertTrue(gate['refined_target_met']);self.assertFalse(gate['mesh_difference_met'])
            for p,b in before.items():self.assertEqual(Path(p).read_bytes(),b)

    def test_real_nonuniform_te_rank_exchange_and_owned_earlier_anchor(self):
        from superfish_ng.planar_curved_tuning import execute_planar_curved_tune,_native,_trial,read_planar_curved_tune
        raw=elliptical_request()
        with workspace('ellipse') as root:
            reuse=os.environ.get('SUPERFISH_CURVED_TUNING_REUSE_REPORT')
            final=read_planar_curved_tune(reuse) if reuse else execute_planar_curved_tune(raw,root/'run')
            self.assertEqual(final['request'],raw)
            self.assertEqual(final['status'],'TUNED',final['decision'])
            self.assertTrue(final['decision']['refined_target_met']);self.assertTrue(final['decision']['mesh_difference_met'])
            for trial in final['trials'][1:]:
                self.assertFalse(trial['tracking']['individual_ids_complete'])
                self.assertEqual(trial['tracking']['current_mode_ids'],[None,None])
                self.assertEqual(trial['identity_recovery']['status'],'PASS')
                self.assertEqual(trial['identity_recovery']['anchor_trial_index'],0)
                self.assertEqual(trial['current_mode_ids'],['odd-x','even-x'])
            angle=np.pi/7;r=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
            reflection=r@np.diag([-1.,1.])@r.T
            for trial,run in zip(final['trials'],final['trial_runs']):
                solution,_=_native(run,_trial(raw,trial['value'],trial['phase']).project)
                points=solution.case.domain.points_xy_m
                from scipy.spatial import cKDTree
                distance,permutation=cKDTree(points).query(points@reflection.T)
                self.assertLess(float(max(distance)),1e-15)
                for rank,identity in enumerate(trial['current_mode_ids']):
                    sign=-1 if identity=='odd-x' else 1
                    c=solution.coefficients[:,rank]
                    relative=np.linalg.norm(c[permutation]-sign*c)/np.linalg.norm(c)
                    self.assertLess(relative,1e-10)

    def test_true_initial_te_doublet_has_no_frequency_or_anchor_bypass(self):
        from superfish_ng.planar_curved_tuning import execute_planar_curved_tune
        raw=small_request('te');raw['identity_recovery']=dict(anchor_selection='latest_resolved_trial',
            controls=PlanarCurvedTrackingControls().to_dict())
        with workspace('doublet') as root:
            report=execute_planar_curved_tune(raw,root/'run')
            self.assertEqual(report['status'],'UNVERIFIED')
            self.assertEqual(len(report['trials']),1)
            trial=report['trials'][0]
            self.assertIsNone(trial['frequency_hz']);self.assertIsNone(trial['target_error_hz'])
            self.assertEqual(trial['current_mode_ids'],[None,None]);self.assertIsNone(trial['identity_recovery'])

    def test_initial_upper_guard_overlap_never_becomes_a_frequency(self):
        from superfish_ng.planar_curved_tuning import execute_planar_curved_tune
        raw=small_request()
        raw['controls']=replace(PlanarCurvedTrackingControls(),relative_cluster_gap=.9).to_dict()
        raw['identity_recovery']=dict(anchor_selection='latest_resolved_trial',
            controls=PlanarCurvedTrackingControls().to_dict())
        with workspace('guard') as root:
            report=execute_planar_curved_tune(raw,root/'run')
            self.assertEqual(report['status'],'UNVERIFIED')
            trial=report['trials'][0]
            self.assertTrue(any(trial['tracking']['guard_overlap']))
            self.assertIsNone(trial['frequency_hz']);self.assertIsNone(trial['target_error_hz'])
            self.assertIsNone(trial['identity_recovery'])

    def test_strict_request_and_complete_budget_before_output_or_fem(self):
        from superfish_ng.planar_curved_tuning import execute_planar_curved_tune
        raw=small_request()
        changes=[('schema_version',True),('parameter','radius_m'),('extra',0),('bounds',[1.,1.3]),
            ('refinement_levels',0),('mode_id','absent'),('initial_ids',['a','a']),('initial_ids',['a','b','c']),('target_hz',True),
            ('max_triangles',1),('max_dofs',1)]
        for field in ('max_field_sample_points','max_enrichment_sample_points_per_side',
                      'max_refined_triangles_per_side','max_dofs_per_side','max_pair_tests_per_comparison'):
            controls=deepcopy(raw['controls']);controls[field]=1;changes.append(('controls',controls))
        with workspace('strict') as root,patch('superfish_ng.planar_curved_tuning.execute_planar_project') as fem:
            for index,(field,value) in enumerate(changes):
                with self.subTest(field=field):
                    altered=deepcopy(raw);altered[field]=value;destination=root/str(index)
                    with self.assertRaises(ValueError):execute_planar_curved_tune(altered,destination)
                    self.assertFalse(destination.exists())
            fem.assert_not_called()

    def test_failed_new_trial_keeps_accepted_checkpoint_and_raw_prefix(self):
        from superfish_ng.planar_curved_tuning import execute_planar_curved_tune,_reconstruct
        raw=small_request()
        with workspace('failure') as root:
            first=execute_planar_curved_tune(raw,root/'first',max_new_trials=1)
            self.assertEqual(first['status'],'PAUSED')
            before={str(p):p.read_bytes() for p in (root/'first').rglob('*') if p.is_file()}
            with patch('superfish_ng.planar_curved_tuning._reconstruct',wraps=_reconstruct) as replay,patch(
                    'superfish_ng.planar_curved_tuning.execute_planar_project',side_effect=RuntimeError('measured test failure')):
                with self.assertRaisesRegex(RuntimeError,'measured test failure'):
                    execute_planar_curved_tune(raw,root/'rest',checkpoint=first)
                self.assertEqual(replay.call_count,1)
            failure=json.loads((root/'rest'/'failure-002.json').read_text())
            self.assertEqual(failure['preceding_trial_runs'],first['trial_runs'])
            self.assertNotIn('frequency_hz',failure)
            self.assertFalse((root/'rest'/'checkpoint-002.json').exists())
            for p,b in before.items():self.assertEqual(Path(p).read_bytes(),b)

    def test_valid_native_still_requires_the_regenerated_trial_project(self):
        from superfish_ng.planar_curved_tuning import execute_planar_curved_tune,_native,_trial,replay_planar_curved_tune
        raw=small_request()
        with workspace('binding') as root:
            report=execute_planar_curved_tune(raw,root/'run',max_new_trials=1)
            with self.assertRaisesRegex(ValueError,'regenerated trial'):
                _native(report['trial_runs'][0],_trial(raw,1.4,'search').project)
            for field,value in (('schema_version',True),('extra',0)):
                altered=deepcopy(report);altered[field]=value
                with self.assertRaises(ValueError):replay_planar_curved_tune(altered)
            altered=deepcopy(report);altered['trials'][0]['frequency_hz']+=1
            with self.assertRaisesRegex(ValueError,'complete original native replay'):
                replay_planar_curved_tune(altered)
