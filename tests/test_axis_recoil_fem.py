# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from scipy.linalg import eigvalsh
from superfish_ng.axis_recoil_fem import axis_recoil_forms
from superfish_ng.axis_recoil_materials import AxisRecoilPartition
from superfish_ng.axis_magnetic_materials import AxisMagneticPartition
from superfish_ng.magnetic_materials import LinearMagneticMaterial,MagneticRegion
from superfish_ng.magnetostatic_fem import axis_magnetostatic_forms
from test_axis_recoil_materials import partition


class AxisRecoilFormTests(unittest.TestCase):
    def test_uniform_remanence_is_zero_H_equilibrium_with_nonzero_B_and_potential_reference(self):
        for holes in (0,1,2):
            for order in (1,2):
                p=partition(holes,pattern=0);s,k,f,m,q=axis_recoil_forms(p,dict(r0=0.),order)
                c=np.full(len(s.dof_points),.05);scale=np.linalg.norm(m)
                self.assertLess(np.linalg.norm(k@c-m)/scale,1e-12);np.testing.assert_array_equal(f,0.)
                # Omitting remanence would leave Kc nonzero and H=nu*B nonzero.
                self.assertGreater(np.linalg.norm(k@c),0.);self.assertGreater(np.linalg.norm(p.remanent_h_a_per_m),0.)
                u=float(c@k@c/2);coupling=float(c@m);constant=q['remanent_reference_constant_j']
                self.assertAlmostEqual(u/constant,1.,places=12);self.assertAlmostEqual(coupling/constant,2.,places=12)
                self.assertAlmostEqual((u-coupling)/constant,-1.,places=12)
                self.assertLess(abs(u-coupling+constant)/constant,1e-12)
                eigen=eigvalsh(k.toarray());self.assertGreater(eigen[0]/eigen[-1],1e-9)
                self.assertGreater(len(s.axis_dofs),0);self.assertFalse(q['constant_a_is_gauge'])
                self.assertEqual(q['coefficient_unit'],'T');self.assertEqual(q['load_unit'],'A m^2');self.assertEqual(q['potential_unit'],'J')

    def test_geometric_and_mu_scaling_reversal_permutation_and_zero_remanence_limit(self):
        for order in (1,2):
            p=partition(2);current=dict(r0=2.,r1=-3.,r2=7.);s,k,f,m,q=axis_recoil_forms(p,current,order)
            large=partition(2,scale=2.);_,lk,lf,lm,lq=axis_recoil_forms(large,current,order)
            for old,new,power in ((k.toarray(),lk.toarray(),3),(f,lf,4),(m,lm,3)):
                self.assertLess(np.linalg.norm(new/(2**power)-old)/np.linalg.norm(old),1e-12)
            self.assertAlmostEqual(lq['remanent_reference_constant_j']/q['remanent_reference_constant_j'],8.,places=12)
            _,pk,pf,pm,_=axis_recoil_forms(AxisRecoilPartition(p.mesh,p.materials[::-1],p.regions[::-1]),current,order)
            for a,b in ((k.toarray(),pk.toarray()),(f,pf),(m,pm)):np.testing.assert_array_equal(a,b)
            raw=p.to_dict()
            for material in raw['materials']:
                material['mu_r_principal']=[7*v for v in material['mu_r_principal']]
                material['remanent_b_local_t']=[-v for v in material['remanent_b_local_t']]
            _,nk,nf,nm,nq=axis_recoil_forms(AxisRecoilPartition.from_dict(raw),{a:-b for a,b in current.items()},order)
            self.assertLess(np.linalg.norm((nk*7-k).data)/np.linalg.norm(k.data),1e-12)
            self.assertLess(np.linalg.norm(nm*7+m)/np.linalg.norm(m),1e-12);np.testing.assert_array_equal(nf,-f)
            self.assertAlmostEqual(nq['remanent_reference_constant_j']*7/q['remanent_reference_constant_j'],1.,places=12)
            raw=p.to_dict()
            for material in raw['materials']:material['mu_r_principal']=[3.,3.];material['remanent_b_local_t']=[0.,0.]
            for region in raw['regions']:region['orientation_rad']=0.
            isotropic=AxisRecoilPartition.from_dict(raw)
            old=AxisMagneticPartition(p.mesh,[LinearMagneticMaterial(x.id,3.) for x in p.materials],[MagneticRegion(x.id,x.material,x.cell_indices) for x in p.regions])
            _,ik,if_,im,_=axis_recoil_forms(isotropic,current,order);_,ok,of,_=axis_magnetostatic_forms(old,current,order)
            self.assertLess(np.linalg.norm((ik-ok).data)/np.linalg.norm(ok.data),1e-13);np.testing.assert_array_equal(if_,of);np.testing.assert_array_equal(im,0.)

    def test_strict_source_controls_and_positive_constitutive_differential(self):
        p=partition();current=dict(r0=2.,r1=-3.,r2=7.)
        for bad in (dict(r0=1.),dict(current,extra=0.),[1.,2.,3.]):
            with self.assertRaises(ValueError):axis_recoil_forms(p,bad)
        for bad in (True,float('nan'),float('inf'),1+0j,[1.]):
            with self.assertRaises(ValueError):axis_recoil_forms(p,dict(current,r0=bad))
        for order,q in ((True,4),(3,4),(2,True),(2,3),(2,33)):
            with self.assertRaises(ValueError):axis_recoil_forms(p,current,order,quadrature_order=q)
        with self.assertRaises(ValueError):axis_recoil_forms(p.to_dict(),current)
        _,k,f,m,_=axis_recoil_forms(p,current);a=np.linspace(-.02,.03,k.shape[0]);direction=np.linspace(.01,-.015,k.shape[0]);step=1e-4
        potential=lambda x:float(x@k@x/2-x@m)
        difference=(potential(a+step*direction)-potential(a-step*direction))/(2*step)
        derivative=float(direction@(k@a-m));self.assertLess(abs(difference-derivative)/abs(derivative),1e-9)
