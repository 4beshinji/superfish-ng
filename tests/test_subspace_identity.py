# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
import unittest
import numpy as np
import test_mode_tracking_history as fixtures
from superfish_ng.mode_tracking import track_sampled_mode_subspaces,tracked_frequency_hz
from superfish_ng.mode_tracking_history import start_mode_history,extend_mode_history,replay_mode_history,save_mode_history,read_mode_history

class SubspaceIdentityTests(unittest.TestCase):
    def track(self,a,b,f,g,groups):
        return track_sampled_mode_subspaces(a,b,np.ones(3),f,g,None,previous_identity_groups=groups,
            comparison_description='same orthonormal sample coordinates and unit measure',minimum_overlap=.99,
            minimum_assignment_margin=.1,relative_cluster_gap=1e-6)

    def test_rotating_basis_and_rank_crossing_over_three_snapshots(self):
        a=np.eye(3);theta=.71;r=np.array([[np.cos(theta),-np.sin(theta),0],[np.sin(theta),np.cos(theta),0],[0,0,1]])
        b=(a@r)[:,[2,0,1]]
        groups=[dict(indices=[1,2],ids=['A','B']),dict(indices=[3],ids=['C'])]
        first=self.track(a,b,[1,1,3],[.5,2,2],groups)
        inherited=sorted([dict(indices=m['current_indices'],ids=m['previous_ids']) for m in first['matches']],key=lambda x:x['indices'][0])
        second=self.track(b,a,[.5,2,2],[1,1,3],inherited)
        self.assertEqual(first['status'],'PASS');self.assertEqual(second['status'],'PASS')
        self.assertEqual(first['current_mode_ids'],['C',None,None]);self.assertEqual(second['current_mode_ids'],[None,None,'C'])
        self.assertEqual(tracked_frequency_hz(second,'C'),3)
        with self.assertRaisesRegex(ValueError,'subspace'):tracked_frequency_hz(second,'A')
        self.assertIsNone(second['previous_mode_ids'])

    def test_split_does_not_assign_old_group_ids_to_individual_modes(self):
        report=self.track(np.eye(3),np.eye(3),[1,1,3],[1,2,3],[dict(indices=[1,2],ids=['A','B']),dict(indices=[3],ids=['C'])])
        self.assertEqual(report['status'],'UNVERIFIED');self.assertEqual(report['current_mode_ids'],[None,None,'C'])

    def test_strict_identity_partition(self):
        bad=[[dict(indices=[1,2],ids=['A','B'])],
             [dict(indices=[1,2,3],ids=['A','A','C'])],
             [dict(indices=[True,2,3],ids=['A','B','C'])],
             [dict(indices=[1,3,2],ids=['A','B','C'])],
             [dict(indices=[1,2,3],ids=['A','B','C'],extra=1)]]
        for groups in bad:
            with self.assertRaises(ValueError):self.track(np.eye(3),np.eye(3),[1,1,3],[1,1,3],groups)

class SavedSubspaceHistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):fixtures.ModeHistoryTests.setUpClass.__func__(cls)

    def pair(self):return fixtures.ModeHistoryTests.pair(self,controls=dict(self.controls,relative_cluster_gap=.9))

    def test_native_subspace_history_resume_and_tamper(self):
        first=start_mode_history(self.pair());controls=dict(self.controls,relative_cluster_gap=.9)
        second=extend_mode_history(first,dict(current_run='c',controls=controls),base_directory=self.root)
        self.assertEqual(second['schema_version'],2);self.assertTrue(second['can_extend']);self.assertEqual(second['status'],'PASS')
        self.assertFalse(second['individual_ids_complete']);self.assertEqual(second['current_mode_ids'],[None]*3)
        self.assertEqual(second['current_identity_groups'],[dict(indices=[1,2,3],ids=['TM010','TM011','TM020'])])
        path=self.root/'subspace.json';save_mode_history(second,path);self.assertEqual(read_mode_history(path),second)
        changed=deepcopy(second);changed['current_identity_groups'][0]['ids'][0]='fake'
        with self.assertRaisesRegex(ValueError,'replay'):replay_mode_history(changed)
        split=extend_mode_history(first,dict(current_run='c',controls=self.controls),base_directory=self.root)
        self.assertEqual(split['status'],'UNVERIFIED');self.assertFalse(split['can_extend'])

    def test_version_one_history_replays_with_original_stop_semantics(self):
        pair=self.pair()
        old=dict(schema_version=1,document_type='mode_tracking_history',steps=[pair],status='UNVERIFIED',can_extend=False,
            stop_reason='last correspondence is unverified or only a subspace; individual IDs cannot be propagated',
            current_run=pair['request']['current_run'],current_mode_ids=[None]*3,
            scope='ordered saved-field comparisons; sampled steps do not prove a continuous physical branch between samples')
        self.assertEqual(replay_mode_history(old),old)
        with self.assertRaisesRegex(ValueError,'unresolved'):extend_mode_history(old,dict(current_run='c',controls=self.controls),base_directory=self.root)
        self.assertTrue(start_mode_history(pair)['can_extend'])
