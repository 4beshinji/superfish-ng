# SPDX-License-Identifier: Apache-2.0
"""Explicit curved finite spectra checked by independent dense eigensolves."""
from dataclasses import replace
import unittest
import numpy as np
from scipy.linalg import eigh
from test_curved_hphi_field_overlap import case
from superfish_ng.curved_hphi import solve_curved_hphi
from superfish_ng.curved_hphi_fem import curved_hphi_matrices
from superfish_ng.curved_hphi_refinement import refine_curved_hphi_geometry
from superfish_ng.curved_hphi_comparison import CurvedHphiComparisonDomain
from superfish_ng.constants import C0,TAU


class CurvedHphiSpectralResolutionTests(unittest.TestCase):
    def test_intervals_contain_independent_finite_spectrum(self):
        for axis in (False,True):
            s=solve_curved_hphi(case(axis,scale=.7));g=s.case.geometry
            fine=refine_curved_hphi_geometry(g)
            _,k,m,_=curved_hphi_matrices(fine.geometry)
            if not axis:
                ones=np.ones(m.shape[0])
                self.assertLess(np.linalg.norm(k@ones)/np.linalg.norm(k.data),1e-13)
            frequencies=C0/TAU*np.sqrt(np.maximum(eigh(k.toarray(),m.toarray(),eigvals_only=True),0.))
            from superfish_ng.curved_hphi_spectral_resolution import curved_hphi_spectral_resolution
            domain=CurvedHphiComparisonDomain(g,g,'same_vacuum',restriction_policy='binary64_roundoff')
            before=s.coefficients.copy();original=s.frequencies_hz.copy()
            report=curved_hphi_spectral_resolution(s,fine.geometry,domain,comparison_cells=fine.native_cells)
            for a,b in report['nearby_comparison_frequency_intervals_hz']:
                self.assertTrue(np.any((frequencies>=a)&(True if b is None else frequencies<=b)))
            self.assertLess(max(report['projection']['relative_mass_error']),1e-9)
            self.assertNotIn('current_mode_ids',report)
            np.testing.assert_array_equal(s.coefficients,before)
            np.testing.assert_array_equal(s.frequencies_hz,original)

    def test_two_scale_frequency_and_interval_invariant(self):
        from superfish_ng.curved_hphi_spectral_resolution import curved_hphi_spectral_resolution
        for axis in (False,True):
            reports=[]
            for scale in (1.,2.):
                s=solve_curved_hphi(case(axis,scale=scale));g=s.case.geometry;fine=refine_curved_hphi_geometry(g)
                d=CurvedHphiComparisonDomain(g,g,'same_vacuum')
                reports.append(curved_hphi_spectral_resolution(s,fine.geometry,d,comparison_cells=fine.native_cells))
            a,b=reports
            np.testing.assert_allclose(b['original_frequencies_hz'],np.array(a['original_frequencies_hz'])/2,rtol=1e-9)
            np.testing.assert_allclose(b['nearby_comparison_frequency_intervals_hz'],np.array(a['nearby_comparison_frequency_intervals_hz'])/2,rtol=1e-8)
            np.testing.assert_allclose(b['relative_inverse_residual'],a['relative_inverse_residual'],rtol=1e-8)
            self.assertAlmostEqual(b['shift_per_m2']/a['shift_per_m2'],.25,places=12)

    def test_domain_controls_native_tampering_and_projection_guard(self):
        from superfish_ng.curved_hphi_spectral_resolution import curved_hphi_spectral_resolution
        s=solve_curved_hphi(case());g=s.case.geometry;fine=refine_curved_hphi_geometry(g)
        d=CurvedHphiComparisonDomain(g,g,'same_vacuum')
        for controls in ({'comparison_order':True},{'comparison_order':1},{'max_dofs':1},{'max_sample_points':1},
                         {'maximum_relative_projection_error':True},{'maximum_relative_projection_error':1}):
            with self.assertRaises(ValueError):
                curved_hphi_spectral_resolution(s,fine.geometry,d,comparison_cells=fine.native_cells,**controls)
        with self.assertRaises(ValueError):curved_hphi_spectral_resolution(s,g,d)
        mapped=CurvedHphiComparisonDomain(g,g,'declared_quadratic')
        with self.assertRaises(ValueError):curved_hphi_spectral_resolution(s,fine.geometry,mapped,comparison_cells=fine.native_cells)
        changed=replace(s,coefficients=s.coefficients*1.01)
        with self.assertRaises(ValueError):curved_hphi_spectral_resolution(changed,fine.geometry,d,comparison_cells=fine.native_cells)
        report=curved_hphi_spectral_resolution(s,fine.geometry,d,comparison_cells=fine.native_cells,
            maximum_relative_projection_error=1e-18)
        self.assertEqual(report['status'],'UNVERIFIED')
        self.assertTrue(any('projection loss' in reason for row in report['modes'] for reason in row['reasons']))

    def test_p1_p2_straight_limit_matches_existing_finite_diagnostic(self):
        from superfish_ng.curved_hphi_spectral_resolution import curved_hphi_spectral_resolution
        from superfish_ng.hphi_spectral_resolution import hphi_spectral_resolution
        from superfish_ng.axis_hphi import AxisHphiCase,solve_axis_hphi
        from superfish_ng.hphi_mesh import HphiMeshCase,solve_hphi_mesh
        for axis in (False,True):
            for order in (1,2):
                s=solve_curved_hphi(replace(case(axis,shear=0.),element_order=order));g=s.case.geometry
                fine=refine_curved_hphi_geometry(g,element_order=order)
                d=CurvedHphiComparisonDomain(g,g,'same_vacuum')
                actual=curved_hphi_spectral_resolution(s,fine.geometry,d,comparison_order=order,comparison_cells=fine.native_cells)
                old=(solve_axis_hphi(AxisHphiCase(g.base_mesh,modes=3,element_order=order)) if axis else
                     solve_hphi_mesh(HphiMeshCase(g.base_mesh,modes=3,element_order=order,quadrature_order=12)))
                expected=hphi_spectral_resolution(old,fine.geometry.base_mesh,comparison_order=order)
                np.testing.assert_allclose(actual['nearby_comparison_frequency_intervals_hz'],
                    expected['nearby_comparison_frequency_intervals_hz'],rtol=1e-8)
                self.assertEqual(actual['status'],expected['status'])
