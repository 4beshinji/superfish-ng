# SPDX-License-Identifier: Apache-2.0
import copy,unittest
import numpy as np
from scipy.linalg import eigh
from superfish_ng.material_hphi import MaterialHphiCase,solve_material_hphi
from superfish_ng.material_hphi_fem import material_hphi_matrices
from superfish_ng.material_hphi_spectral_resolution import material_hphi_spectral_resolution
from superfish_ng.constants import C0,TAU
from test_material_hphi_comparison import partition,request
from scripts.material_hphi_reference import layered_partition,layered_reference


class MaterialHphiSpectralResolutionTests(unittest.TestCase):
    def test_actual_material_spectrum_static_kernel_and_unchanged_source(self):
        for axis in (False,True):
            for order in (1,2):
                a,b=partition(1,1,axis),partition(2,1,axis,True)
                source=solve_material_hphi(MaterialHphiCase(a,modes=3,element_order=order))
                coefficients=source.coefficients.copy();frequencies=source.frequencies_hz.copy()
                report=material_hphi_spectral_resolution(source,request(a,b),comparison_order=order)
                _,k,m,_=material_hphi_matrices(b,order)
                values,basis=eigh(k.toarray(),m.toarray());fine=C0/TAU*np.sqrt(np.maximum(values,0))
                from superfish_ng.material_hphi_mass_projection import project_material_hphi_coefficients
                projected=project_material_hphi_coefficients(request(a,b),source.coefficients,previous_order=order,current_order=order).coefficients
                amplitudes=basis.T@(m@projected);shift=report['shift_per_m2']
                mu=1/((TAU*source.frequencies_hz/C0)**2+shift)
                independent=np.sqrt(np.sum((amplitudes*(1/(values[:,None]+shift)-mu))**2,axis=0)/np.sum(amplitudes**2,axis=0))
                np.testing.assert_allclose(report['inverse_residual_m2'],independent,rtol=1e-8,atol=1e-16)
                for low,high in report['nearby_comparison_frequency_intervals_hz']:
                    self.assertTrue(np.any((fine>=low)&(True if high is None else fine<=high)))
                if not axis:
                    ones=np.ones(m.shape[0]);self.assertLess(np.linalg.norm(k@ones)/(np.linalg.norm(k.data)*np.linalg.norm(ones)),1e-12)
                    self.assertIn('constant q retained',report['zero_mode'])
                np.testing.assert_array_equal(source.coefficients,coefficients);np.testing.assert_array_equal(source.frequencies_hz,frequencies)
                self.assertLess(max(report['linear_solve_relative_residual']),1e-10)
                self.assertNotIn('current_mode_ids',report)

    def test_independent_layered_tem_band_and_scale(self):
        reports=[]
        for scale in (1.,2.):
            a,b=layered_partition(1,12,scale),layered_partition(2,24,scale)
            source=solve_material_hphi(MaterialHphiCase(a,modes=3))
            report=material_hphi_spectral_resolution(source,request(a,b));reports.append(report)
            expected=np.array([layered_reference(i,scale)[0]['frequency_hz'] for i in range(1,4)])
            np.testing.assert_allclose(source.frequencies_hz,expected,rtol=.002)
            self.assertLess(expected[-1],layered_reference(3,scale)[0]['radial_mode_frequency_lower_bound_hz'])
            self.assertEqual(report['status'],'PASS')
        np.testing.assert_allclose(np.array(reports[1]['nearby_comparison_frequency_intervals_hz'])*2,reports[0]['nearby_comparison_frequency_intervals_hz'],rtol=1e-8)

    def test_invalid_declarations_original_and_projection_loss(self):
        a,b=partition(1,0,True),partition(2,0,True,True)
        source=solve_material_hphi(MaterialHphiCase(a,modes=2,element_order=1))
        report=material_hphi_spectral_resolution(source,request(a,b),comparison_order=1,maximum_relative_projection_error=1e-15)
        self.assertEqual(report['status'],'UNVERIFIED')
        self.assertTrue(any('projection loss' in reason for row in report['modes'] for reason in row['reasons']))
        with self.assertRaises(ValueError):material_hphi_spectral_resolution(source,request(a,a))
        with self.assertRaises(ValueError):material_hphi_spectral_resolution(source,request(b,b))
        from superfish_ng.hphi_geometry_mapping import HphiGeometryMapping
        with self.assertRaises(ValueError):material_hphi_spectral_resolution(source,request(a,b,HphiGeometryMapping(a.mesh,a.mesh)))
        for options in ({'max_dofs':1},{'max_sample_points':1},{'max_modes':1},{'comparison_order':True},{'maximum_relative_projection_error':1}):
            with self.assertRaises(ValueError):material_hphi_spectral_resolution(source,request(a,b),**options)
        bad=copy.deepcopy(source);bad.coefficients[:,0]*=1.01
        with self.assertRaises(ValueError):material_hphi_spectral_resolution(bad,request(a,b))


if __name__=='__main__':unittest.main()
