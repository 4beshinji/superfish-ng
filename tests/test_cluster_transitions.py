# SPDX-License-Identifier: Apache-2.0
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
import numpy as np
from scipy.special import jn_zeros
from superfish_ng import Case,solve
from superfish_ng.io import save_run
from superfish_ng.mode_tracking import track_sampled_mode_subspaces,tracked_frequency_hz
from superfish_ng.saved_mode_tracking import build_saved_mode_tracking
from superfish_ng.mode_tracking_history import start_mode_history,extend_mode_history,save_mode_history,read_mode_history

CONTROLS=dict(minimum_overlap=.98,minimum_assignment_margin=.05,relative_cluster_gap=1e-3,minimum_relative_singular_value=1e-8)
POLICY=dict(cluster_transition_policy='retain_subspace',minimum_cluster_link=.2)

class ClusterTransitionTests(unittest.TestCase):
    def track(self,a,b,f,g,ids=None,groups=None,**policy):
        return track_sampled_mode_subspaces(a,b,np.ones(len(a)),f,g,ids,previous_identity_groups=groups,
            comparison_description='common orthonormal analytic samples with unit measure',**CONTROLS,**policy)

    def test_merge_retains_union_and_refuses_individual_frequency(self):
        a=np.eye(3);b=a.copy();b[:2,:2]=np.array([[1,-1],[1,1]])/np.sqrt(2)
        self.assertEqual(self.track(a,b,[1,2,4],[1.5,1.5,4],['A','B','C'])['status'],'UNVERIFIED')
        result=self.track(a,b,[1,2,4],[1.5,1.5,4],['A','B','C'],**POLICY)
        self.assertEqual(result['status'],'PASS');self.assertEqual(result['current_mode_ids'],[None,None,'C'])
        self.assertEqual(result['cluster_transitions']['events'][0]['kind'],'MERGE')
        with self.assertRaisesRegex(ValueError,'subspace'):tracked_frequency_hz(result,'A')

    def test_split_retains_noncontiguous_identity_set_across_next_step(self):
        a=np.eye(3);b=a[:,[0,2,1]]
        groups=[dict(indices=[1,2],ids=['A','B']),dict(indices=[3],ids=['C'])]
        result=self.track(a,b,[1,1,4],[1,2,3],groups=groups,**POLICY)
        self.assertEqual(result['status'],'PASS');self.assertEqual(result['current_mode_ids'],[None,'C',None])
        self.assertEqual(result['cluster_transitions']['events'][0]['kind'],'SPLIT')
        inherited=sorted([dict(indices=m['current_indices'],ids=m['previous_ids']) for m in result['matches']],key=lambda x:x['indices'][0])
        self.assertEqual(inherited[0],dict(indices=[1,3],ids=['A','B']))
        again=self.track(b,b,[1,2,3],[1,2,3],groups=inherited,**POLICY)
        self.assertEqual(again['status'],'PASS');self.assertEqual(again['current_mode_ids'],[None,'C',None])

    def test_ambiguous_individual_mixing_is_not_hidden_by_union(self):
        a=np.eye(2);b=np.array([[1,-1],[1,1]])/np.sqrt(2)
        result=self.track(a,b,[1,2],[1,2],['A','B'],**POLICY)
        self.assertEqual(result['status'],'UNVERIFIED');self.assertEqual(result['cluster_transitions']['events'],[])

    def test_candidate_union_still_requires_full_rank_and_worst_overlap(self):
        for a,b in [(np.eye(3)[:,:2],np.array([[1,0],[0,.8],[0,.6]])),(np.array([[1,1],[0,0],[0,0]]),np.eye(3)[:,:2])]:
            result=self.track(a,b,[1,2],[1.5,1.5],['A','B'],**POLICY)
            self.assertEqual(result['status'],'UNVERIFIED')
            self.assertTrue(result['cluster_transitions']['events'])
            self.assertEqual(result['cluster_transitions']['events'][0]['status'],'UNVERIFIED')

    def test_explicit_policy_and_link_controls(self):
        for policy in [dict(minimum_cluster_link=.2),dict(cluster_transition_policy='guess',minimum_cluster_link=.2),dict(cluster_transition_policy='retain_subspace'),dict(cluster_transition_policy='retain_subspace',minimum_cluster_link=True)]:
            with self.assertRaises(ValueError):self.track(np.eye(2),np.eye(2),[1,2],[1,2],['A','B'],**policy)

class SavedClusterTransitionTests(unittest.TestCase):
    def test_actual_fem_degeneracy_merge_split_and_saved_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);zeros=jn_zeros(0,2);crossing=np.pi*.1/np.sqrt(zeros[1]**2-zeros[0]**2)
            for name,length in [('a',.055),('b',crossing),('c',.075)]:
                case=Case(((0.,.1),(length,.1)),nr=10,nz=10,modes=3,element_order=2);solution=solve(case);save_run(case,solution,root/name)
                if name=='b':self.assertLess(abs(solution.frequencies_hz[2]/solution.frequencies_hz[1]-1),1e-3)
            controls=dict(CONTROLS,mapping='normalized_cylinder',sample_order=12,**POLICY)
            seed=build_saved_mode_tracking(dict(schema_version=1,previous_run='a',current_run='a',previous_ids=['TM010','TM020','TM011'],controls=controls),base_directory=root)
            merged=extend_mode_history(start_mode_history(seed),dict(current_run='b',controls=controls),base_directory=root)
            self.assertEqual(merged['status'],'PASS');self.assertEqual(merged['steps'][-1]['tracking']['cluster_transitions']['events'][0]['kind'],'MERGE')
            path=root/'merged.json';save_mode_history(merged,path)
            split=extend_mode_history(read_mode_history(path),dict(current_run='c',controls=controls),base_directory=root)
            self.assertEqual(split['status'],'PASS');self.assertEqual(split['current_mode_ids'],['TM010',None,None])
            self.assertEqual(split['steps'][-1]['tracking']['cluster_transitions']['events'][0]['kind'],'SPLIT')
            self.assertEqual(split['current_identity_groups'][1],dict(indices=[2,3],ids=['TM011','TM020']))
            with self.assertRaisesRegex(ValueError,'subspace'):tracked_frequency_hz(split['steps'][-1]['tracking'],'TM011')
            changed=deepcopy(split);changed['steps'][-1]['tracking']['cluster_transitions']['events'][0]['status']='UNVERIFIED'
            with self.assertRaisesRegex(ValueError,'replay'):save_mode_history(changed,root/'changed.json')
