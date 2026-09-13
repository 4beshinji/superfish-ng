# SPDX-License-Identifier: Apache-2.0
import copy,json,unittest
import numpy as np
from superfish_ng.bh_curve import MonotoneBHCurve
from superfish_ng.constants import MU0


def curve():return MonotoneBHCurve('synthetic',[0.,.25,.5,1.,2.],[0.,100.,250.,1500.,25000.],'Synthetic monotone saturation-like table; no measured material')


class BHCurveTests(unittest.TestCase):
    def test_strict_table_schema_units_provenance_and_finite_slopes(self):
        material=curve();data=material.to_dict();self.assertEqual(MonotoneBHCurve.from_dict(json.loads(json.dumps(data))).to_dict(),data)
        with self.assertRaises(ValueError):material._b[1]=.2
        b=[0.,1.];h=[0.,10.];m=MonotoneBHCurve('copy',b,h,'synthetic');b[1]=2.;h[1]=20.;self.assertEqual(m.b_t,(0.,1.));self.assertEqual(m.h_a_per_m,(0.,10.))
        for key,value in [('schema_version',True),('type','hysteretic'),('interpolation','spline'),('extrapolation','linear'),('provenance',' '),('id',''),('b_t',[0.,True,2.]),('h_a_per_m',[0.,100.,99.,500.,600.]),('b_t',[0.,1.,1.,2.,3.]),('h_a_per_m',[1.,100.,250.,1500.,25000.]),('b_t',[0.,'1',2.,3.,4.]),('b_t',[0.,1+0j,2.,3.,4.]),('b_t',[0.,float('nan')]),('h_a_per_m',[0.,float('inf')])]:
            bad=copy.deepcopy(data);bad[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):MonotoneBHCurve.from_dict(bad)
        for key in ('remanent_b_t','temperature_k','mu_r','loss_tangent'):
            bad=copy.deepcopy(data);bad[key]=0.
            with self.assertRaises(ValueError):MonotoneBHCurve.from_dict(bad)
        for b,h in [([0.,1e-310],[0.,1e300]),([0.,1e300],[0.,1e300]),([0.,1e-300],[0.,1e-300])]:
            with self.assertRaisesRegex(ValueError,'finite SI'):MonotoneBHCurve('invalid',b,h,'synthetic')

    def test_linear_limit_energy_coenergy_original_H_and_zero_tangent(self):
        nu=1/(7*MU0);m=MonotoneBHCurve('linear',[0.,.2,1.,3.],[0.,.2*nu,nu,3*nu],'synthetic linear permeability')
        for dim in (2,3):
            b=np.zeros((4,dim));b[1,0]=.1;b[2,:2]=(.3,-.4);b[3,0]=-1.5;state=m.evaluate_vectors(b)
            np.testing.assert_allclose(state['h_a_per_m'],nu*b,rtol=2e-15,atol=1e-12)
            np.testing.assert_allclose(state['tangent_reluctivity_m_per_h'],np.tile(nu*np.eye(dim),(4,1,1)),rtol=2e-15,atol=1e-10)
            expected=.5*nu*np.sum(b*b,axis=1)
            for key in ('energy_density_j_per_m3','coenergy_density_j_per_m3'):np.testing.assert_allclose(state[key],expected,rtol=2e-15)
            np.testing.assert_allclose(m.induction_magnitudes(np.linalg.norm(state['h_a_per_m'],axis=1)),np.linalg.norm(b,axis=1),rtol=2e-15)

    def test_piecewise_integrals_inverse_and_one_sided_node_tangents(self):
        m=curve();b=np.array([0.,.125,.25,.375,.5,.75,1.,1.5,2.]);state=m.evaluate_magnitudes(b)
        np.testing.assert_array_equal(state['interval_indices'],[0,0,1,1,2,2,3,3,3])
        np.testing.assert_array_equal(state['differential_reluctivity_m_per_h'],[400,400,600,600,2500,2500,23500,23500,23500])
        np.testing.assert_allclose(state['h_a_per_m'],[0,50,100,175,250,875,1500,13250,25000],rtol=0,atol=0)
        np.testing.assert_allclose(state['energy_density_j_per_m3'],[0,3.125,12.5,29.6875,56.25,196.875,493.75,4181.25,13743.75],rtol=0,atol=0)
        np.testing.assert_allclose(state['energy_density_j_per_m3']+state['coenergy_density_j_per_m3'],b*state['h_a_per_m'],rtol=2e-15)
        np.testing.assert_allclose(m.induction_magnitudes(state['h_a_per_m']),b,rtol=2e-15)
        vector=m.evaluate_vectors([.5,0.]);np.testing.assert_allclose(np.diag(vector['tangent_reluctivity_m_per_h']),[2500.,500.],rtol=0,atol=0)

    def test_rotation_reversal_and_independent_energy_gradient_and_H_tangent(self):
        m=curve();angle=.713;q=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]]);b=np.array([.36,.48]);state=m.evaluate_vectors(b);rotated=m.evaluate_vectors(q@b);reversed=m.evaluate_vectors(-b)
        np.testing.assert_allclose(rotated['h_a_per_m'],q@state['h_a_per_m'],rtol=2e-14,atol=1e-12)
        np.testing.assert_allclose(rotated['tangent_reluctivity_m_per_h'],q@state['tangent_reluctivity_m_per_h']@q.T,rtol=2e-14,atol=1e-11)
        np.testing.assert_array_equal(reversed['h_a_per_m'],-state['h_a_per_m']);np.testing.assert_array_equal(reversed['tangent_reluctivity_m_per_h'],state['tangent_reluctivity_m_per_h'])
        self.assertEqual(reversed['energy_density_j_per_m3'],state['energy_density_j_per_m3'])
        step=1e-6;gradient=[];tangent=[]
        for axis in np.eye(2):
            plus=m.evaluate_vectors(b+step*axis);minus=m.evaluate_vectors(b-step*axis)
            gradient.append((plus['energy_density_j_per_m3']-minus['energy_density_j_per_m3'])/(2*step));tangent.append((plus['h_a_per_m']-minus['h_a_per_m'])/(2*step))
        np.testing.assert_allclose(gradient,state['h_a_per_m'],rtol=1e-6);np.testing.assert_allclose(np.array(tangent).T,state['tangent_reluctivity_m_per_h'],rtol=2e-6)
        self.assertTrue(np.all(np.linalg.eigvalsh(state['tangent_reluctivity_m_per_h'])>0.))

    def test_range_endpoints_zero_and_unsupported_query_types(self):
        m=curve();self.assertEqual(m.evaluate_magnitudes(2.)['h_a_per_m'],25000.);self.assertEqual(m.induction_magnitudes(25000.),2.)
        np.testing.assert_array_equal(m.evaluate_vectors([0.,0.,0.])['h_a_per_m'],0.)
        for value in (-1e-300,np.nextafter(2.,np.inf),False,[0.,True],[1+0j],['.1'],[float('nan')],[],1e-300):
            with self.subTest(value=value),self.assertRaises(ValueError):m.evaluate_magnitudes(value)
        for value in (-1.,np.nextafter(25000.,np.inf),np.nextafter(0.,1.),[False,100.],float('inf')):
            with self.assertRaises(ValueError):m.induction_magnitudes(value)
        for value in (1.,[1.],[[0.,0.,0.,0.]],[[False,0.]],[[float('inf'),0.]]):
            with self.assertRaises(ValueError):m.evaluate_vectors(value)
