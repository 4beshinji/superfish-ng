# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import unittest
import numpy as np
from superfish_ng.mode_tracking import track_sampled_mode_subspaces


class IdentityRecoveryInvariantTests(unittest.TestCase):
    def comparison(self, permutation):
        return track_sampled_mode_subspaces(np.eye(3),np.eye(3)[:,permutation],np.array([1.,2.,3.]),
            [1.,2.,3.],[1.,2.,3.],['A','B','C'],comparison_description='independent separated coordinate eigenspaces',
            minimum_overlap=.99,minimum_assignment_margin=.1,relative_cluster_gap=1e-6)

    def test_separated_eigenspaces_recover_identity_not_frequency_rank(self):
        from superfish_ng.mode_identity_recovery import assess_identity_recovery
        groups=[dict(indices=[1,2,3],ids=['A','B','C'])]
        result=assess_identity_recovery(self.comparison([2,0,1]),groups)
        self.assertEqual(result['status'],'PASS')
        self.assertEqual(result['current_mode_ids'],['C','A','B'])
        self.assertEqual(result['current_identity_groups'],[
            dict(indices=[1],ids=['C']),dict(indices=[2],ids=['A']),dict(indices=[3],ids=['B'])])

    def test_globally_clear_match_must_not_cross_existing_identity_sets(self):
        from superfish_ng.mode_identity_recovery import assess_identity_recovery
        groups=[dict(indices=[1,2],ids=['A','B']),dict(indices=[3],ids=['C'])]
        result=assess_identity_recovery(self.comparison([2,0,1]),groups)
        self.assertEqual(result['status'],'UNVERIFIED')
        self.assertEqual(result['current_identity_groups'],groups)
        self.assertEqual(result['current_mode_ids'],[None,None,'C'])
        self.assertTrue(any(not check['consistent'] for check in result['group_checks']))


class SavedIdentityRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from pathlib import Path
        import tempfile
        from scipy.special import jn_zeros
        from superfish_ng import Case,solve
        from superfish_ng.io import save_run
        from superfish_ng.saved_mode_tracking import build_saved_mode_tracking
        from superfish_ng.mode_tracking_history import start_mode_history,extend_mode_history
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);cls.root=Path(cls.tmp.name)
        zeros=jn_zeros(0,2);length=np.pi*.1/np.sqrt(zeros[1]**2-zeros[0]**2)
        for name,size in [('a',.055),('b',length),('c',.075)]:
            case=Case(((0.,.1),(size,.1)),nr=8,nz=8,modes=3,element_order=2)
            save_run(case,solve(case),cls.root/name)
        cls.controls=dict(mapping='normalized_cylinder',sample_order=12,minimum_overlap=.98,
            minimum_assignment_margin=.05,relative_cluster_gap=.001,minimum_relative_singular_value=1e-8)
        retained=dict(cls.controls,cluster_transition_policy='retain_subspace',minimum_cluster_link=.2)
        cls.merged=start_mode_history(build_saved_mode_tracking(dict(schema_version=1,previous_run='a',current_run='b',
            previous_ids=['TM010','TM020','TM011'],controls=retained),base_directory=cls.root))
        cls.split=extend_mode_history(cls.merged,dict(current_run='c',controls=retained),base_directory=cls.root)
        cls.request=dict(anchor_snapshot_index=0,controls=cls.controls)

    def test_native_split_recovers_ids_and_extends_without_relabeling_sources(self):
        from superfish_ng.mode_identity_recovery import recover_mode_history
        from superfish_ng.mode_tracking_history import extend_mode_history,save_mode_history,read_mode_history
        from superfish_ng.completion import digest
        before={str(p):digest(p) for p in self.root.rglob('*') if p.is_file()}
        original=deepcopy(self.split);recovered=recover_mode_history(original,self.request)
        self.assertEqual(recovered['schema_version'],3);self.assertTrue(recovered['individual_ids_complete'])
        self.assertEqual(recovered['current_mode_ids'],['TM010','TM011','TM020'])
        self.assertEqual(recovered['steps'],original['steps']);self.assertEqual(original,self.split)
        extended=extend_mode_history(recovered,dict(current_run='a',controls=self.controls),base_directory=self.root)
        self.assertEqual(extended['current_mode_ids'],['TM010','TM020','TM011'])
        path=self.root/'recovered-extended.json';save_mode_history(extended,path)
        self.assertEqual(read_mode_history(path),extended)
        for name,value in before.items():self.assertEqual(digest(name),value)
        with self.assertRaises(FileExistsError):save_mode_history(extended,path)

    def test_still_degenerate_or_ambiguous_anchor_match_retains_failed_event(self):
        from superfish_ng.mode_identity_recovery import recover_mode_history
        from superfish_ng.mode_tracking_history import extend_mode_history,replay_mode_history
        for history,request in [(self.merged,self.request),(self.split,dict(self.request,controls=dict(self.controls,minimum_overlap=1.)))]:
            result=recover_mode_history(history,request)
            self.assertEqual(result['status'],'UNVERIFIED');self.assertFalse(result['can_extend'])
            self.assertEqual(result['current_identity_groups'],history['current_identity_groups'])
            self.assertEqual(result['current_mode_ids'],history['current_mode_ids'])
            self.assertEqual(replay_mode_history(result),result)
            with self.assertRaisesRegex(ValueError,'unresolved'):extend_mode_history(result,dict(current_run='a',controls=self.controls))

    def test_multiple_recoveries_can_use_a_previously_recovered_anchor(self):
        from superfish_ng.mode_identity_recovery import recover_mode_history
        from superfish_ng.mode_tracking_history import extend_mode_history,replay_mode_history
        recovered=recover_mode_history(self.split,self.request)
        retained=dict(self.controls,cluster_transition_policy='retain_subspace',minimum_cluster_link=.2)
        merged=extend_mode_history(recovered,dict(current_run='b',controls=retained),base_directory=self.root)
        split=extend_mode_history(merged,dict(current_run='c',controls=retained),base_directory=self.root)
        again=recover_mode_history(split,dict(self.request,anchor_snapshot_index=2))
        self.assertEqual(again['current_mode_ids'],['TM010','TM011','TM020'])
        self.assertEqual([e['after_step_index'] for e in again['identity_recoveries']],[1,3])
        self.assertEqual(replay_mode_history(again),again)
        bad=deepcopy(again);bad['identity_recoveries'].pop(0)
        with self.assertRaisesRegex(ValueError,'continuity'):replay_mode_history(bad)

    def test_strict_anchor_controls_and_already_resolved_history(self):
        from superfish_ng.mode_identity_recovery import recover_mode_history
        for request in [dict(self.request,anchor_snapshot_index=True),dict(self.request,anchor_snapshot_index=-1),
            dict(self.request,anchor_snapshot_index=2),dict(self.request,anchor_snapshot_index=1),
            dict(self.request,extra=True),dict(self.request,controls=dict(self.controls,cluster_transition_policy='retain_subspace',minimum_cluster_link=.2))]:
            with self.assertRaises(ValueError):recover_mode_history(self.split,request)
        recovered=recover_mode_history(self.split,self.request)
        with self.assertRaises(ValueError):recover_mode_history(recovered,self.request)

    def test_recovery_event_and_ancestry_tampering_are_rejected(self):
        from superfish_ng.mode_identity_recovery import recover_mode_history
        from superfish_ng.mode_tracking_history import replay_mode_history
        result=recover_mode_history(self.split,self.request)
        for change in ['assessment','request','placement','comparison','unknown']:
            bad=deepcopy(result);event=bad['identity_recoveries'][0]
            if change=='assessment':event['assessment']['current_mode_ids'][1]='forged'
            elif change=='request':event['request']['anchor_snapshot_index']=1
            elif change=='placement':event['after_step_index']=0
            elif change=='comparison':event['comparison']['sources'][0]['sha256']['fields.npz']='0'*64
            else:event['extra']=True
            with self.assertRaises(ValueError):replay_mode_history(bad)

    def test_source_change_during_anchor_comparison_is_not_blessed(self):
        from unittest.mock import patch
        from superfish_ng import mode_identity_recovery as recovery
        original=recovery.build_saved_mode_tracking;path=self.root/'a/case.json';raw=path.read_bytes()
        def changed(*args,**kwargs):
            result=original(*args,**kwargs);path.write_bytes(raw+b'\n');return result
        try:
            with patch.object(recovery,'build_saved_mode_tracking',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'sources changed'):recovery.recover_mode_history(self.split,self.request)
        finally:path.write_bytes(raw)

    def test_cli_and_gui_share_strict_history_replay(self):
        import json
        from superfish_ng.cli import main
        from superfish_ng.jobs import JobManager
        from superfish_ng.gui_mode_tracking import tracking_response
        from superfish_ng.mode_tracking_history import save_mode_history,read_mode_history
        history=self.root/'cli-source.json';save_mode_history(self.split,history)
        request=self.root/'recovery-request.json';request.write_text(json.dumps(self.request))
        output=self.root/'cli-recovered.json'
        self.assertEqual(main(['recover-mode-identities',str(history),str(request),'--out',str(output)]),0)
        self.assertEqual(main(['replay-mode-history',str(output)]),0)
        expected=read_mode_history(output)
        manager=JobManager(self.root/'gui-workspace')
        try:
            response=tracking_response(manager,'recover-mode-identities',dict(document=history.read_text(),request_document=request.read_text()))
            self.assertEqual(response['document'],expected)
            self.assertEqual(tracking_response(manager,'replay-mode-tracking',dict(document=response['serialized'])),response)
            bad=request.read_text().replace('"anchor_snapshot_index": 0','"anchor_snapshot_index": 0, "anchor_snapshot_index": 1')
            with self.assertRaises(ValueError):tracking_response(manager,'recover-mode-identities',dict(document=history.read_text(),request_document=bad))
        finally:manager.close()
