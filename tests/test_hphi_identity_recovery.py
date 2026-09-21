# SPDX-License-Identifier: Apache-2.0
"""Independent coaxial TEM/radial crossing and conservative Hphi recovery."""
from dataclasses import replace
import unittest
import numpy as np
from scripts.validate_coaxial import radial_roots
from superfish_ng.constants import C0
from superfish_ng.coaxial import CoaxialCase, solve_coaxial
from superfish_ng.hphi_field_overlap import _declared_mesh
from superfish_ng.hphi_geometry_mapping import coaxial_dimension_mapping
from superfish_ng.hphi_tracking import HphiTrackingRequest, track_mapped_hphi_modes
from superfish_ng.hphi_tuning import _refine_mesh


class HphiIdentityRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        a,b=.0625,.125
        root=radial_roots(a,b,1)[0]
        cls.solutions=[]
        for factor in (1.15,1.,.85):
            length=factor*np.pi/root
            solution=solve_coaxial(CoaxialCase(a,b,length,nr=8,nz=8,modes=3,quadrature_order=12))
            expected=sorted([C0/(2*length),C0*root/(2*np.pi)])
            np.testing.assert_allclose(solution.frequencies_hz[:2],expected,rtol=1e-4)
            cls.solutions.append(solution)
        cls.anchor,cls.degenerate,cls.current=cls.solutions
        cls.meshes=[_refine_mesh(_declared_mesh(s)) for s in cls.solutions]
        cls.groups=[dict(indices=[1,2],ids=['radial','TEM'])]
        cls.inherited=HphiTrackingRequest(cls.meshes[1],cls.meshes[2],
            previous_mode_ids=None,previous_identity_groups=cls.groups)
        cls.comparison=HphiTrackingRequest(cls.meshes[0],cls.meshes[2],previous_mode_ids=['TEM','radial'])
        cls.inherited_map=coaxial_dimension_mapping(cls.degenerate.case,cls.current.case)
        cls.anchor_map=coaxial_dimension_mapping(cls.anchor.case,cls.current.case)

    def recover(self, *, inherited=None, comparison=None, anchor=None, current=None, mapping=None):
        from superfish_ng.hphi_identity_recovery import HphiIdentityRecoveryRequest, recover_hphi_modes
        request=HphiIdentityRecoveryRequest(0, comparison or self.comparison, mapping or self.anchor_map)
        return recover_hphi_modes(anchor or self.anchor,self.degenerate,current or self.current,
            inherited or self.inherited,request,current_snapshot_index=2,inherited_mapping=self.inherited_map)

    def test_analytic_rank_exchange_recovers_only_with_declared_anchor(self):
        baseline=track_mapped_hphi_modes(self.degenerate,self.current,self.inherited,self.inherited_map)
        self.assertEqual(baseline['status'],'PASS',baseline['verification_reasons'])
        self.assertFalse(baseline['individual_ids_complete'])
        self.assertEqual(baseline['current_mode_ids'],[None,None])
        before=[(s.coefficients.copy(),s.frequencies_hz.copy()) for s in self.solutions]
        report=self.recover()
        self.assertEqual(report['status'],'PASS',report)
        self.assertEqual(report['assessment']['current_mode_ids'],['radial','TEM'])
        self.assertTrue(all(c['consistent'] for c in report['assessment']['group_checks']))
        for solution,(field,frequency) in zip(self.solutions,before):
            np.testing.assert_array_equal(solution.coefficients,field)
            np.testing.assert_array_equal(solution.frequencies_hz,frequency)

    def test_unverified_inherited_guard_cannot_be_bypassed(self):
        from unittest.mock import patch
        from superfish_ng import hphi_identity_recovery as module
        inherited=replace(self.inherited,controls=replace(self.inherited.controls,relative_cluster_gap=.9))
        with patch.object(module,'_anchor_comparison',side_effect=AssertionError('must not compare anchor')):
            report=self.recover(inherited=inherited)
        self.assertEqual(report['status'],'UNVERIFIED')
        self.assertIsNone(report['comparison'])
        self.assertIsNone(report['assessment'])

    def test_ambiguous_anchor_and_outside_identity_set_fail(self):
        ambiguous=replace(self.comparison,previous_comparison_mesh=self.meshes[1])
        for comparison,anchor,mapping in (
            (ambiguous,self.degenerate,self.inherited_map),
            (replace(self.comparison,previous_mode_ids=['TEM','outside']),self.anchor,self.anchor_map)):
            report=self.recover(comparison=comparison,anchor=anchor,mapping=mapping)
            self.assertEqual(report['status'],'UNVERIFIED')
            self.assertEqual(report['assessment']['current_mode_ids'],[None,None])
            self.assertFalse(report['assessment']['individual_ids_complete'])

    def test_strict_request_indices_and_identity_declaration(self):
        from superfish_ng.hphi_identity_recovery import HphiIdentityRecoveryRequest, recover_hphi_modes
        request=HphiIdentityRecoveryRequest(0,self.comparison,self.anchor_map)
        self.assertEqual(HphiIdentityRecoveryRequest.from_dict(request.to_dict()).to_dict(),request.to_dict())
        for change in ({'extra':1},{'recovery_version':True},{'anchor_snapshot_index':True},{'anchor_snapshot_index':-1}):
            with self.assertRaises(ValueError):HphiIdentityRecoveryRequest.from_dict({**request.to_dict(),**change})
        with self.assertRaises(ValueError):HphiIdentityRecoveryRequest(0,self.inherited,self.anchor_map)
        for index in (0,True,-1):
            with self.assertRaises(ValueError):recover_hphi_modes(self.anchor,self.degenerate,self.current,
                self.inherited,request,current_snapshot_index=index,inherited_mapping=self.inherited_map)

    def test_independent_tem_bessel_fields_and_degenerate_span(self):
        from scipy.special import jv, yv
        kr=radial_roots(.0625,.125,1)[0]
        for index,solution in enumerate(self.solutions):
            r,z=solution.space.dof_points.T
            exact=np.column_stack((np.cos(np.pi*z/solution.case.length_m),
                r*(yv(0,kr*.0625)*jv(1,kr*r)-jv(0,kr*.0625)*yv(1,kr*r))))
            actual=solution.coefficients[:,:2]
            mass=solution.mass
            ga=actual.T@(mass@actual);gx=exact.T@(mass@exact)
            cross=actual.T@(mass@exact)
            whitened=np.linalg.solve(np.linalg.cholesky(ga),cross)
            whitened=np.linalg.solve(np.linalg.cholesky(gx),whitened.T).T
            self.assertGreater(np.linalg.svd(whitened,compute_uv=False).min(),.999)
            if index!=1:
                expected_ranks=[0,1] if index==0 else [1,0]
                for field,rank in enumerate(expected_ranks):
                    overlap=abs(cross[rank,field])/np.sqrt(ga[rank,rank]*gx[field,field])
                    self.assertGreater(overlap,.999)

    def test_each_identity_set_boundary_is_enforced(self):
        from superfish_ng.hphi_identity_recovery import _assess
        comparison=dict(status='PASS',individual_ids_complete=True,current_mode_ids=['a','c','b'])
        groups=[dict(indices=[1,2],ids=['a','b']),dict(indices=[3],ids=['c'])]
        result=_assess(comparison,groups,3)
        self.assertEqual(result['status'],'UNVERIFIED')
        self.assertEqual(result['current_mode_ids'],[None,None,'c'])
        self.assertFalse(any(c['consistent'] for c in result['group_checks']))

    def test_anchor_guard_cannot_claim_recovered_ids(self):
        comparison=replace(self.comparison,controls=replace(self.comparison.controls,relative_cluster_gap=.9))
        result=self.recover(comparison=comparison)
        self.assertEqual(result['inherited']['status'],'PASS')
        self.assertEqual(result['comparison']['status'],'UNVERIFIED')
        self.assertEqual(result['status'],'UNVERIFIED')
        self.assertEqual(result['assessment']['current_mode_ids'],[None,None])


class HphiSameVacuumRecoveryTests(unittest.TestCase):
    def test_axis_and_positive_radius_same_vacuum_with_distinct_meshes(self):
        from test_hphi_tracking import pair
        from superfish_ng.hphi_identity_recovery import HphiIdentityRecoveryRequest, recover_hphi_modes
        for axis in (False,True):
            with self.subTest(axis=axis):
                (a,b),comparison=pair(axis)
                request=HphiIdentityRecoveryRequest(0,comparison)
                self.assertEqual(HphiIdentityRecoveryRequest.from_dict(request.to_dict()).to_dict(),request.to_dict())
                with self.assertRaises(ValueError):HphiIdentityRecoveryRequest.from_dict({**request.to_dict(),'mapping':'infer'})
                inherited=replace(comparison,previous_mode_ids=None,
                    previous_identity_groups=[dict(indices=[1,2],ids=['mode-1','mode-2'])])
                report=recover_hphi_modes(a,a,b,inherited,request,current_snapshot_index=2)
                self.assertEqual(report['status'],'PASS')
                self.assertEqual(report['assessment']['current_mode_ids'],['mode-1','mode-2'])
                with self.assertRaisesRegex(ValueError,'unresolved individual ID set'):
                    recover_hphi_modes(a,a,b,comparison,request,current_snapshot_index=2)
