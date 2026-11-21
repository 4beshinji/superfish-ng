# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
from functools import lru_cache
import unittest
from unittest.mock import patch
import numpy as np
from superfish_ng.planar_curved import PlanarCurvedCase
from superfish_ng.planar_curved_solver import solve_planar_curved, planar_curved_quantities
from superfish_ng.planar_curved_comparison import PlanarCurvedComparisonDomain
from superfish_ng.planar_curved_tracking import PlanarCurvedTrackingRequest, track_planar_curved_modes
from test_planar_curved import curved_ellipse


@lru_cache(maxsize=1)
def solutions():
    return tuple(solve_planar_curved(PlanarCurvedCase(curved_ellipse(16,axes=axes,shift=(0.,0.)),
        'te',modes=3,quadrature_order=16)) for axes in ((.020,.019),(.0195,.0195),(.019,.020),(.0188,.0202)))


def compare(a,b,groups=False):
    return PlanarCurvedTrackingRequest(PlanarCurvedComparisonDomain(a.case.domain,b.case.domain,'declared_quadratic'),
        previous_mode_ids=None if groups else ['odd-x','even-x'],
        previous_identity_groups=[dict(indices=[1,2],ids=['odd-x','even-x'])] if groups else None)


class PlanarCurvedIdentityRecoveryTests(unittest.TestCase):
    def test_original_reflection_parity_rank_exchange_and_following_inheritance(self):
        from superfish_ng.planar_curved_identity_recovery import PlanarCurvedIdentityRecoveryRequest, recover_planar_curved_modes
        anchor,circle,current,later = solutions()
        angle = np.pi/7
        rotation = np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
        for solution,expected in ((anchor,[-1.,1.]),(current,[1.,-1.]),(later,[1.,-1.])):
            points = solution.case.domain.points_xy_m
            reflected = points@rotation@np.diag([-1.,1.])@rotation.T
            distance = np.linalg.norm(reflected[:,None]-points[None,:],axis=2)
            permutation = np.argmin(distance,axis=1)
            self.assertLess(np.max(distance[np.arange(len(points)),permutation]),1e-16)
            c = solution.coefficients[:,:2]
            parity = np.sum(c*c[permutation],axis=0)/np.sum(c*c,axis=0)
            np.testing.assert_allclose(parity,expected,rtol=0,atol=1e-10)
        before = [(s.coefficients.tobytes(),s.frequencies_hz.tobytes(),
                  [planar_curved_quantities(s,i) for i in range(s.case.modes)]) for s in solutions()]
        report = recover_planar_curved_modes(anchor,circle,current,compare(circle,current,True),
            PlanarCurvedIdentityRecoveryRequest(0,compare(anchor,current)),current_snapshot_index=2)
        self.assertEqual(report['inherited']['status'],'PASS')
        self.assertEqual(report['inherited']['current_mode_ids'],[None,None])
        self.assertEqual(report['status'],'PASS',report['stop_reason'])
        self.assertEqual(report['assessment']['current_mode_ids'],['even-x','odd-x'])
        self.assertEqual(report['recovered_frequencies_hz'],dict(zip(['even-x','odd-x'],current.frequencies_hz[:2])))
        request = replace(compare(current,later),previous_mode_ids=report['assessment']['current_mode_ids'])
        following = track_planar_curved_modes(current,later,request)
        self.assertEqual(following['current_mode_ids'],['even-x','odd-x'])
        self.assertTrue(following['individual_ids_complete'])
        self.assertEqual(before,[(s.coefficients.tobytes(),s.frequencies_hz.tobytes(),
                  [planar_curved_quantities(s,i) for i in range(s.case.modes)]) for s in solutions()])

    def test_true_doublet_and_wrong_anchor_ids_keep_recovery_frequencies_null(self):
        from superfish_ng.planar_curved_identity_recovery import PlanarCurvedIdentityRecoveryRequest, recover_planar_curved_modes
        anchor,circle,current,_ = solutions()
        cases = [(circle,compare(circle,circle,True),compare(anchor,circle)),
                 (current,compare(circle,current,True),replace(compare(anchor,current),previous_mode_ids=['outside','even-x']))]
        for target,inherited,comparison in cases:
            report = recover_planar_curved_modes(anchor,circle,target,inherited,
                PlanarCurvedIdentityRecoveryRequest(0,comparison),current_snapshot_index=2)
            self.assertEqual(report['status'],'UNVERIFIED')
            self.assertIsNone(report['recovered_frequencies_hz'])
            self.assertEqual(report['assessment']['current_mode_ids'],[None,None])
            self.assertEqual(report['assessment']['current_identity_groups'],[dict(indices=[1,2],ids=['even-x','odd-x'])])
            self.assertEqual(report['assessment']['individual_ids_complete'],False)

    def test_inherited_guard_forbids_anchor_guard_and_budget_cannot_rescue_ids(self):
        from superfish_ng.planar_curved_identity_recovery import PlanarCurvedIdentityRecoveryRequest, recover_planar_curved_modes
        from superfish_ng.planar_curved_comparison import PlanarCurvedComparisonBudgetExceeded
        anchor,circle,current,_ = solutions()
        inherited = compare(circle,current,True)
        comparison = compare(anchor,current)
        bad = replace(inherited,controls=replace(inherited.controls,relative_cluster_gap=.9))
        with patch('superfish_ng.planar_curved_identity_recovery.track_planar_curved_modes',wraps=track_planar_curved_modes) as tracked:
            report = recover_planar_curved_modes(anchor,circle,current,bad,
                PlanarCurvedIdentityRecoveryRequest(0,comparison),current_snapshot_index=2)
            self.assertEqual(tracked.call_count,1)
        self.assertEqual(report['status'],'UNVERIFIED')
        self.assertIsNone(report['comparison']);self.assertIsNone(report['assessment']);self.assertIsNone(report['recovered_frequencies_hz'])
        guarded = replace(comparison,controls=replace(comparison.controls,relative_cluster_gap=.9))
        report = recover_planar_curved_modes(anchor,circle,current,inherited,
            PlanarCurvedIdentityRecoveryRequest(0,guarded),current_snapshot_index=2)
        self.assertEqual(report['status'],'UNVERIFIED');self.assertIsNone(report['recovered_frequencies_hz'])
        for which in ('inherited','anchor'):
            a,b = inherited,comparison
            if which=='inherited':a = replace(a,controls=replace(a.controls,max_field_sample_points=1))
            else:b = replace(b,controls=replace(b.controls,max_field_sample_points=1))
            with self.assertRaises(PlanarCurvedComparisonBudgetExceeded) as caught:
                recover_planar_curved_modes(anchor,circle,current,a,PlanarCurvedIdentityRecoveryRequest(0,b),current_snapshot_index=2)
            self.assertEqual(caught.exception.status,'UNVERIFIED')

    def test_complete_requests_snapshot_order_band_and_anchor_ids_are_strict(self):
        from superfish_ng.planar_curved_identity_recovery import PlanarCurvedIdentityRecoveryRequest, recover_planar_curved_modes
        anchor,circle,current,_ = solutions()
        inherited,comparison = compare(circle,current,True),compare(anchor,current)
        request = PlanarCurvedIdentityRecoveryRequest(0,comparison)
        self.assertEqual(request.to_dict(),PlanarCurvedIdentityRecoveryRequest.from_dict(request.to_dict()).to_dict())
        for key,value in (('recovery_version',True),('anchor_snapshot_index',True),('anchor_snapshot_index',-1),('extra',0)):
            bad = request.to_dict();bad[key] = value
            with self.assertRaises(ValueError):PlanarCurvedIdentityRecoveryRequest.from_dict(bad)
        with self.assertRaisesRegex(ValueError,'resolved'):
            PlanarCurvedIdentityRecoveryRequest(0,inherited)
        for index in (True,0):
            with self.assertRaises(ValueError):recover_planar_curved_modes(anchor,circle,current,inherited,request,current_snapshot_index=index)
        with self.assertRaisesRegex(ValueError,'precede'):
            recover_planar_curved_modes(anchor,circle,current,inherited,PlanarCurvedIdentityRecoveryRequest(2,comparison),current_snapshot_index=2)
        with self.assertRaisesRegex(ValueError,'same current band'):
            recover_planar_curved_modes(anchor,circle,current,inherited,
                PlanarCurvedIdentityRecoveryRequest(0,replace(comparison,current_mode_count=1)),current_snapshot_index=2)
        with self.assertRaisesRegex(ValueError,'unresolved individual'):
            recover_planar_curved_modes(anchor,current,current,compare(current,current),request,current_snapshot_index=2)


if __name__ == '__main__':unittest.main()
