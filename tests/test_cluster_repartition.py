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

class ClusterRepartitionTests(unittest.TestCase):
    def track(self,a,b,f=None,g=None,policy='retain_connected_subspace',weights=None):
        return track_sampled_mode_subspaces(a,b,np.ones(len(a)) if weights is None else weights,
            [1,1,2,2] if f is None else f,[1,1,2,2] if g is None else g,[f'ID{i}' for i in range(a.shape[1])],
            comparison_description='weighted orthonormal direct-sum samples',minimum_overlap=.98,minimum_assignment_margin=.05,
            relative_cluster_gap=.001,minimum_relative_singular_value=1e-8,cluster_transition_policy=policy,minimum_cluster_link=.2)

    def test_repartition_requires_new_explicit_policy(self):
        a=np.eye(4);b=a[:,[0,2,1,3]]
        self.assertEqual(self.track(a,b,policy='retain_subspace')['status'],'UNVERIFIED')
        result=self.track(a,b);self.assertEqual(result['status'],'PASS');self.assertEqual(result['current_mode_ids'],[None]*4)
        self.assertEqual(result['cluster_transitions']['events'][0]['kind'],'REPARTITION')
        self.assertEqual(result['matches'][0]['previous_ids'],['ID0','ID1','ID2','ID3'])
        with self.assertRaisesRegex(ValueError,'subspace'):tracked_frequency_hz(result,'ID0')

    def test_basis_rotation_sign_scale_and_weight_invariance(self):
        weights=np.array([1.,2.,3.,5.]);a=np.diag(1/np.sqrt(weights));b=a[:,[0,2,1,3]]
        angle=.43;rotation=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
        change=np.zeros((4,4));change[:2,:2]=rotation;change[2:,2:]=rotation.T
        first=self.track(a,b,weights=weights);second=self.track(a@change@np.diag([-3,2,.4,-.7]),b@change.T,weights=weights)
        self.assertEqual(second['status'],'PASS')
        np.testing.assert_allclose(first['cluster_transitions']['link_matrix'],second['cluster_transitions']['link_matrix'],atol=2e-14)
        self.assertEqual(first['matches'][0]['previous_ids'],second['matches'][0]['previous_ids'])
        self.assertAlmostEqual(second['matches'][0]['minimum_principal_overlap'],1.,places=14)

    def test_noncontiguous_union_preserves_unrelated_individual(self):
        a=np.eye(5);b=a[:,[0,3,2,1,4]]
        result=self.track(a,b,[1,1,2,3,3],[1,1,2,3,3])
        self.assertEqual(result['status'],'PASS');self.assertEqual(result['current_mode_ids'],[None,None,'ID2',None,None])
        event=result['cluster_transitions']['events'][0]
        self.assertEqual(event['previous_indices'],[1,2,4,5]);self.assertEqual(event['current_indices'],[1,2,4,5])

    def test_individual_ambiguity_is_never_hidden(self):
        angle=np.pi/4;a=np.eye(2);b=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
        result=self.track(a,b,[1,2],[1,2]);self.assertEqual(result['status'],'UNVERIFIED');self.assertEqual(result['cluster_transitions']['events'],[])

    def test_union_still_rejects_loss_rank_deficiency_and_dimension_change(self):
        a=np.eye(5)[:,:4];b=a[:,[0,2,1,3]].copy();b[:,3]=.8*b[:,3]+.6*np.eye(5)[:,4]
        result=self.track(a,b);self.assertEqual(result['status'],'UNVERIFIED');self.assertEqual(result['cluster_transitions']['events'][0]['status'],'UNVERIFIED')
        b=a[:,[0,2,1,3]].copy();b[:,3]=b[:,2]
        self.assertEqual(self.track(a,b)['status'],'UNVERIFIED')
        b=np.eye(5)[:,[0,2,1,3,4]];result=self.track(a,b,g=[1,1,2,2,2])
        self.assertEqual(result['status'],'UNVERIFIED');self.assertEqual(result['cluster_transitions']['events'],[])

    def test_native_saved_seeded_sets_repartition_and_history_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);z=jn_zeros(0,2);length=2*np.pi*.1/np.sqrt(z[1]**2-z[0]**2)
            case=Case(((0.,.1),(length,.1)),nr=12,nz=16,modes=5,element_order=2);save_run(case,solve(case),root/'native')
            groups=[dict(indices=[1],ids=['fundamental']),dict(indices=[2,3],ids=['A','B']),dict(indices=[4,5],ids=['C','D'])]
            controls=dict(mapping='normalized_cylinder',sample_order=12,minimum_overlap=.98,minimum_assignment_margin=.05,
                relative_cluster_gap=.001,minimum_relative_singular_value=1e-8,cluster_transition_policy='retain_connected_subspace',minimum_cluster_link=.2)
            request=dict(schema_version=2,previous_run='native',current_run='native',previous_groups=groups,controls=controls)
            pair=build_saved_mode_tracking(request,base_directory=root)
            self.assertEqual(pair['status'],'PASS');self.assertEqual(pair['tracking']['cluster_transitions']['events'][0]['kind'],'REPARTITION')
            history=extend_mode_history(start_mode_history(pair),dict(current_run=str(root/'native'),controls=controls))
            self.assertEqual(history['current_identity_groups'],[dict(indices=[1],ids=['fundamental']),dict(indices=[2,3,4,5],ids=['A','B','C','D'])])
            save_mode_history(history,root/'history.json');self.assertEqual(read_mode_history(root/'history.json'),history)
            changed=deepcopy(history);changed['steps'][0]['tracking']['cluster_transitions']['events'][0]['kind']='MERGE'
            with self.assertRaisesRegex(ValueError,'replay'):save_mode_history(changed,root/'changed.json')
