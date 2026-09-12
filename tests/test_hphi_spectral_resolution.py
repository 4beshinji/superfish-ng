# SPDX-License-Identifier: Apache-2.0
import copy,unittest
import numpy as np
from scipy.linalg import eigh
from superfish_ng.axis_hphi import AxisHphiCase,solve_axis_hphi
from superfish_ng.hphi_mesh import HphiMeshCase,solve_hphi_mesh,hphi_mesh_matrices
from superfish_ng.axis_connected_fem import axis_connected_matrices
from superfish_ng.hphi_spectral_resolution import hphi_spectral_resolution
from superfish_ng.constants import C0,TAU
from test_hphi_mass_projection import declared


class HphiSpectralResolutionTests(unittest.TestCase):
    def test_intervals_locate_actual_comparison_eigenvalues_and_preserve_original(self):
        for axis in (False,True):
            source=declared(1,1,axis);fine=declared(2,1,axis,19)
            solution=solve_axis_hphi(AxisHphiCase(source,modes=3)) if axis else solve_hphi_mesh(HphiMeshCase(source,modes=3,quadrature_order=12))
            original=solution.coefficients.copy();frequency=solution.frequencies_hz.copy()
            report=hphi_spectral_resolution(solution,fine)
            if axis:_,k,m=axis_connected_matrices(fine,2)
            else:_,k,m,_=hphi_mesh_matrices(HphiMeshCase(fine,quadrature_order=12))
            values=eigh(k.toarray(),m.toarray(),eigvals_only=True);frequencies=C0/TAU*np.sqrt(np.maximum(values,0.))
            for a,b in report['nearby_comparison_frequency_intervals_hz']:
                self.assertTrue(np.any((frequencies>=a)&(True if b is None else frequencies<=b)))
            np.testing.assert_array_equal(solution.coefficients,original);np.testing.assert_array_equal(solution.frequencies_hz,frequency)
            self.assertLess(max(report['linear_solve_relative_residual']),1e-10)

    def test_projection_loss_is_unverified_and_no_rank_identity_is_claimed(self):
        source=declared(1,0,True);fine=declared(2,0,True,31)
        solution=solve_axis_hphi(AxisHphiCase(source,modes=3,element_order=1))
        report=hphi_spectral_resolution(solution,fine,comparison_order=1,maximum_relative_projection_error=1e-15)
        self.assertEqual(report['status'],'UNVERIFIED')
        self.assertTrue(any('projection loss' in reason for row in report['modes'] for reason in row['reasons']))
        self.assertNotIn('current_mode_ids',report)

    def test_invalid_comparison_controls_and_modified_original_are_rejected(self):
        source=declared();fine=declared(2);solution=solve_axis_hphi(AxisHphiCase(source,modes=2))
        for bad in (source,declared(2,1),declared(2,axis=False),declared(2,scale=2)):
            with self.assertRaises(ValueError):hphi_spectral_resolution(solution,bad)
        for controls in ({'comparison_order':True},{'comparison_order':1},{'maximum_relative_projection_error':True},
                {'maximum_relative_projection_error':1},{'max_dofs':1},{'max_overlay_triangles':1}):
            with self.assertRaises(ValueError):hphi_spectral_resolution(solution,fine,**controls)
        changed=copy.deepcopy(solution);changed.coefficients[:,0]*=1.01
        with self.assertRaises(ValueError):hphi_spectral_resolution(changed,fine)


if __name__=='__main__':unittest.main()
