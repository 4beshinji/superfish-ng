# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from superfish_ng.constants import C0
from superfish_ng.planar_tracking import PlanarTrackingControls
from superfish_ng.planar_tuning import execute_planar_tune, replay_planar_tune, validate_planar_tune
from test_planar_tuning import request


def recovery_request():
    raw=request()
    raw.update(schema_version=3,bounds=[.18,.214],target_hz=C0/(2*.214),
               controls=PlanarTrackingControls(relative_cluster_gap=.08).to_dict(),
               identity_recovery=dict(anchor_selection='fixed_trial',anchor_trial_index=0,
                                      controls=PlanarTrackingControls().to_dict()))
    return raw


class PlanarTuneRecoveryTests(unittest.TestCase):
    def test_actual_search_and_final_refinement_recover_from_earlier_field(self):
        raw=recovery_request()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            first=execute_planar_tune(raw,root/'first',max_new_trials=2)
            self.assertEqual(first['status'],'PAUSED')
            self.assertEqual(first['trials'][1]['tracking']['current_mode_ids'],[None,None])
            self.assertEqual(first['trials'][1]['current_mode_ids'],['x','y'])
            final=execute_planar_tune(raw,root/'final',checkpoint=first)
            self.assertEqual(final['status'],'TUNED')
            for trial in final['trials'][1:]:
                event=trial['identity_recovery']
                self.assertEqual(event['status'],'PASS')
                self.assertEqual(event['anchor_trial_index'],0)
                self.assertEqual(trial['current_mode_ids'],['x','y'])
                self.assertLess(abs(trial['frequency_hz']/raw['target_hz']-1),1e-4)
            self.assertEqual(final['trials'][-1]['identity_recovery']['parent_trial_index'],1)
            self.assertTrue(final['decision']['mesh_difference_met'])
            self.assertEqual(replay_planar_tune(final),final)
            modified=deepcopy(final);modified['trials'][-1]['identity_recovery']['anchor_trial_index']=1
            with self.assertRaisesRegex(ValueError,'replay'):replay_planar_tune(modified)

    def test_true_degenerate_initial_or_current_and_unavailable_anchor_stop(self):
        initial=recovery_request();initial['bounds']=[.2,.22]
        current=recovery_request();current['bounds']=[.18,.2]
        missing=recovery_request();missing['identity_recovery']['anchor_trial_index']=5
        with tempfile.TemporaryDirectory() as tmp:
            for name,raw,count in [('initial',initial,1),('current',current,2),('missing',missing,2)]:
                result=execute_planar_tune(raw,Path(tmp)/name)
                self.assertEqual(result['status'],'UNVERIFIED')
                self.assertEqual(len(result['trials']),count)
                self.assertIsNone(result['trials'][-1]['frequency_hz'])
                self.assertIsNone(result['trials'][-1]['target_error_hz'])
                self.assertFalse(result['can_resume'])

    def test_strict_policy_and_polynomial_version_three(self):
        from superfish_ng.planar_affine_shape import PlanarAffineShapeLaw
        raw=recovery_request()
        for policy in ({'anchor_selection':'rank','controls':{}},
                       dict(raw['identity_recovery'],anchor_trial_index=True),
                       dict(raw['identity_recovery'],anchor_trial_index=raw['max_trials']),
                       dict(raw['identity_recovery'],extra=True)):
            with self.assertRaises(ValueError):validate_planar_tune(dict(raw,identity_recovery=policy))
        law=PlanarAffineShapeLaw([[[1,(.214/.18)-1],[0]],[[0],[1]]],[[0],[0]],[0,1])
        raw.update(parameter='deformation',bounds=[0.,1.],shape_law=law.to_dict())
        raw['identity_recovery']=dict(anchor_selection='latest_resolved_trial',controls=PlanarTrackingControls().to_dict())
        with tempfile.TemporaryDirectory() as tmp:
            result=execute_planar_tune(raw,Path(tmp)/'polynomial')
            self.assertEqual(result['status'],'TUNED')
            self.assertEqual([t['identity_recovery']['anchor_trial_index'] for t in result['trials'][1:]],[0,1])
            self.assertEqual(result['trials'][-1]['tracking']['result_version'],8)
            self.assertEqual(replay_planar_tune(result),result)


if __name__=='__main__':unittest.main()
