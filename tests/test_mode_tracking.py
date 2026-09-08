# SPDX-License-Identifier: Apache-2.0
import json
import math
import unittest
import numpy as np
from superfish_ng.mode_tracking import track_sampled_mode_subspaces,tracked_frequency_hz

class ModeTrackingTests(unittest.TestCase):
    def track(self,a,b,f,g,ids=None,weights=None,**extra):
        controls=dict(comparison_description='common orthonormal test coordinates; real field; declared positive quadrature weights',
                      minimum_overlap=.98,minimum_assignment_margin=.05,relative_cluster_gap=1e-6)
        controls.update(extra)
        return track_sampled_mode_subspaces(a,b,np.ones(len(a)) if weights is None else weights,f,g,
                                           ids or [f'mode-{i}' for i in range(len(f))],**controls)

    def test_exact_crossing_keeps_identity_not_frequency_rank(self):
        def eig(t):return np.linalg.eigh(np.diag([1+t,1-t]))
        f,a=eig(-.2);g,b=eig(.2)
        r=self.track(a,b,f,g,['rising','falling'])
        self.assertEqual(r['status'],'PASS');self.assertEqual(r['current_mode_ids'],['falling','rising'])
        self.assertEqual(tracked_frequency_hz(r,'rising'),1.2)
        self.assertEqual(tracked_frequency_hz(r,'falling'),.8)
        self.assertEqual(json.loads(json.dumps(r,allow_nan=False)),r)

    def test_resolved_small_avoided_crossing_step(self):
        f,a=np.linalg.eigh([[1.,.2],[.2,1.]])
        g,b=np.linalg.eigh([[1.01,.2],[.2,.99]])
        r=self.track(a,b,f,g)
        self.assertEqual(r['status'],'PASS');self.assertTrue(r['individual_ids_complete'])
        self.assertGreater(min(x['minimum_principal_overlap'] for x in r['matches']),.999)

    def test_degenerate_basis_rotation_identifies_only_subspace(self):
        a=np.eye(3);angle=.713;c,s=math.cos(angle),math.sin(angle)
        b=np.array([[c,-s,0],[s,c,0],[0,0,-1.]])
        r=self.track(a,b,[1,1,3],[1,1,3],['x','y','z'])
        self.assertEqual(r['status'],'PASS');self.assertFalse(r['individual_ids_complete'])
        self.assertEqual(r['current_mode_ids'],[None,None,'z'])
        group=r['matches'][0];self.assertEqual(group['kind'],'SUBSPACE');self.assertEqual(group['previous_ids'],['x','y'])
        np.testing.assert_allclose(group['principal_overlaps'],[1,1],atol=1e-14)
        with self.assertRaisesRegex(ValueError,'subspace'):tracked_frequency_hz(r,'x')
        self.assertEqual(tracked_frequency_hz(r,'z'),3)

    def test_ambiguous_overlap_abstains_even_at_zero_requested_margin(self):
        c=math.sqrt(.5);b=np.array([[c,-c],[c,c]])
        for margin in (.05,0.):
            r=self.track(np.eye(2),b,[1,2],[1,2],minimum_overlap=.6,minimum_assignment_margin=margin)
            self.assertEqual(r['status'],'UNVERIFIED');self.assertEqual(r['current_mode_ids'],[None,None])
            self.assertTrue(r['unresolved'])
            with self.assertRaisesRegex(ValueError,'UNVERIFIED'):tracked_frequency_hz(r,'mode-0')

    def test_missing_mode_rank_loss_and_cluster_merge_abstain(self):
        a=np.eye(2)
        missing=self.track(a,a[:,:1],[1,2],[1])
        self.assertEqual(missing['status'],'UNVERIFIED');self.assertTrue(missing['unmatched_previous'])
        with self.assertRaises(ValueError):tracked_frequency_hz(missing,'mode-0')
        merged=self.track(a,a,[1,2],[1,1]);self.assertEqual(merged['status'],'UNVERIFIED')
        rank_loss=self.track(np.ones((3,2)),np.ones((3,2)),[1,1],[1,1])
        self.assertEqual(rank_loss['status'],'UNVERIFIED')
        self.assertIn('rank-deficient',rank_loss['unmatched_previous'][0]['reason'])
        zero=self.track(np.zeros((2,1)),np.ones((2,1)),[1],[1]);self.assertEqual(zero['status'],'UNVERIFIED')

    def test_positive_weights_row_permutation_sign_and_extreme_amplitudes(self):
        a=np.array([[1.,0],[0,.5],[1,0],[0,.5]])
        b=a[:,::-1]*[-1e200,1e-200];w=np.array([1.,4,2,3])
        r=self.track(a,b,[1,2],[1.1,2.1],['A','B'],weights=w)
        self.assertEqual(r['status'],'PASS');self.assertEqual(r['current_mode_ids'],['B','A'])
        permutation=[3,0,2,1]
        other=self.track(a[permutation],b[permutation],[1,2],[1.1,2.1],['A','B'],weights=w[permutation]*1e-200)
        self.assertEqual(other['current_mode_ids'],r['current_mode_ids'])
        np.testing.assert_allclose(other['overlap_matrix'],r['overlap_matrix'],atol=1e-14)

    def test_strict_inputs_and_declared_comparison(self):
        a=np.eye(2)
        for extra in ({'minimum_overlap':True},{'minimum_assignment_margin':-1},{'relative_cluster_gap':1},
                      {'comparison_description':''},{'minimum_relative_singular_value':0}):
            with self.assertRaises(ValueError):self.track(a,a,[1,2],[1,2],**extra)
        for weights in ([1,0],[1,-1],[True,True],[1,float('nan')]):
            with self.assertRaises(ValueError):self.track(a,a,[1,2],[1,2],weights=weights)
        with self.assertRaises(ValueError):self.track(a,a,[2,1],[1,2])
        with self.assertRaises(ValueError):self.track(a,a,[1,2],[1,2],['same','same'])
        with self.assertRaises(ValueError):self.track(a.astype(complex),a,[1,2],[1,2])

    def test_worst_principal_overlap_detects_a_lost_direction(self):
        a=np.eye(3)[:,:2];b=np.eye(3)[:,[0,2]]
        lost=self.track(a,b,[1,1],[1,1],minimum_overlap=.4)
        self.assertEqual(lost['status'],'UNVERIFIED')
        self.assertAlmostEqual(lost['overlap_matrix'][0][0],0.)
        changed_basis=a@np.array([[1.,2.],[0.,1.]])
        retained=self.track(a,changed_basis,[1,1],[1,1])
        self.assertEqual(retained['status'],'PASS')
        self.assertEqual(retained['matches'][0]['kind'],'SUBSPACE')

    def test_actual_cylinder_fem_crossing_after_saved_field_reload(self):
        from pathlib import Path
        import tempfile
        from superfish_ng import Case,solve
        from superfish_ng.io import save_run
        from superfish_ng.saved import read_solution
        from superfish_ng.analytic import tm0np_frequency
        from superfish_ng.mode_tracking import track_cylindrical_modes
        with tempfile.TemporaryDirectory() as tmp:
            solutions=[]
            for i,length in enumerate((.055,.075)):
                case=Case(((0.,.1),(length,.1)),nr=12,nz=12,modes=3,element_order=2)
                directory=Path(tmp)/str(i);save_run(case,solve(case),directory)
                solutions.append(read_solution(directory))
            previous,current=solutions
            for solution,labels in ((previous,((1,0),(2,0),(1,1))),(current,((1,0),(1,1),(2,0)))):
                for frequency,(n,p) in zip(solution.frequencies_hz,labels):
                    exact=tm0np_frequency(.1,solution.case.length,n,p)
                    self.assertLess(abs(frequency/exact-1),.002)
            for order in (12,18):
                r=track_cylindrical_modes(previous,current,['TM010','TM020','TM011'],mapping='normalized_cylinder',sample_order=order,
                    minimum_overlap=.98,minimum_assignment_margin=.05,relative_cluster_gap=1e-6)
                self.assertEqual(r['status'],'PASS');self.assertEqual(r['current_mode_ids'],['TM010','TM011','TM020'])
                self.assertEqual(tracked_frequency_hz(r,'TM020'),current.frequencies_hz[2])
            with self.assertRaises(ValueError):track_cylindrical_modes(previous,current,['a','b','c'],mapping='implicit',sample_order=12)

if __name__=='__main__':unittest.main()
