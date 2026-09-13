# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from scipy.linalg import eigvalsh
from superfish_ng.off_axis_recoil_fem import off_axis_recoil_forms
from superfish_ng.off_axis_recoil_materials import OffAxisRecoilPartition
from superfish_ng.off_axis_magnetic_materials import OffAxisMagneticPartition
from superfish_ng.magnetic_materials import LinearMagneticMaterial,MagneticRegion
from superfish_ng.off_axis_magnetostatic_fem import off_axis_magnetostatic_forms
from test_off_axis_recoil_materials import partition


class OffAxisRecoilFormTests(unittest.TestCase):
    def test_constant_psi_kernel_and_P2_uniform_axial_remanence_zero_H(self):
        for holes in (0,1,2):
            for order in (1,2):
                p=partition(holes,pattern=0);s,k,f,m,q=off_axis_recoil_forms(p,dict(r0=0.),order);ones=np.ones(len(s.dof_points))
                self.assertLess(np.linalg.norm(k@ones)/np.linalg.norm(k.data),1e-12)
                self.assertLess(abs(m.sum())/np.linalg.norm(m,1),1e-12);np.testing.assert_array_equal(f,0.)
                eigen=eigvalsh(k.toarray());self.assertLess(abs(eigen[0]/eigen[-1]),1e-12);self.assertGreater(eigen[1]/eigen[-1],1e-9)
                self.assertFalse(hasattr(s,'axis_dofs'));self.assertFalse(q['axis_present']);self.assertEqual(q['stiffness_unit'],'1/H');self.assertEqual(q['load_unit'],'A');self.assertEqual(q['potential_unit'],'J')
                if order==2:
                    c=.05*s.dof_points[:,0]**2;self.assertLess(np.linalg.norm(k@c-m)/np.linalg.norm(m),1e-12)
                    u=float(c@k@c/2);work=float(c@m);constant=q['remanent_reference_constant_j']
                    self.assertAlmostEqual(u/constant,1.,places=11);self.assertAlmostEqual(work/constant,2.,places=11)
                    self.assertLess(abs(u-work+constant)/constant,1e-11)
                    self.assertLess(np.linalg.norm(k@(c+.125)-m)/np.linalg.norm(m),1e-10)

    def test_geometry_mu_and_source_scaling_permutation_and_isotropic_zero_remanence_limit(self):
        for order in (1,2):
            p=partition(2);current=dict(r0=2.,r1=-3.,r2=7.);s,k,f,m,q=off_axis_recoil_forms(p,current,order)
            _,lk,lf,lm,lq=off_axis_recoil_forms(partition(2,scale=2.),current,order)
            for old,new,factor in ((k.toarray(),lk.toarray(),.5),(f,lf,4.),(m,lm,2.)):
                self.assertLess(np.linalg.norm(new/factor-old)/np.linalg.norm(old),1e-12)
            self.assertAlmostEqual(lq['remanent_reference_constant_j']/q['remanent_reference_constant_j'],8.,places=12)
            _,pk,pf,pm,_=off_axis_recoil_forms(OffAxisRecoilPartition(p.mesh,p.materials[::-1],p.regions[::-1]),current,order)
            for a,b in ((k.toarray(),pk.toarray()),(f,pf),(m,pm)):np.testing.assert_array_equal(a,b)
            raw=p.to_dict()
            for material in raw['materials']:
                material['mu_r_principal']=[7*v for v in material['mu_r_principal']];material['remanent_b_local_t']=[-v for v in material['remanent_b_local_t']]
            _,nk,nf,nm,nq=off_axis_recoil_forms(OffAxisRecoilPartition.from_dict(raw),{a:-b for a,b in current.items()},order)
            self.assertLess(np.linalg.norm((nk*7-k).data)/np.linalg.norm(k.data),1e-12);self.assertLess(np.linalg.norm(nm*7+m)/np.linalg.norm(m),1e-12);np.testing.assert_array_equal(nf,-f)
            self.assertAlmostEqual(nq['remanent_reference_constant_j']*7/q['remanent_reference_constant_j'],1.,places=12)
            raw=p.to_dict()
            for material in raw['materials']:material['mu_r_principal']=[3.,3.];material['remanent_b_local_t']=[0.,0.]
            for region in raw['regions']:region['orientation_rad']=0.
            old=OffAxisMagneticPartition(p.mesh,[LinearMagneticMaterial(x.id,3.) for x in p.materials],[MagneticRegion(x.id,x.material,x.cell_indices) for x in p.regions])
            _,ik,if_,im,_=off_axis_recoil_forms(OffAxisRecoilPartition.from_dict(raw),current,order);_,ok,of,_=off_axis_magnetostatic_forms(old,current,order)
            self.assertLess(np.linalg.norm((ik-ok).data)/np.linalg.norm(ok.data),1e-13);np.testing.assert_array_equal(if_,of);np.testing.assert_array_equal(im,0.)

    def test_strict_source_controls_and_constitutive_directional_derivative(self):
        p=partition();current=dict(r0=2.,r1=-3.,r2=7.)
        for bad in (dict(r0=1.),dict(current,extra=0.),[1.,2.,3.]):
            with self.assertRaises(ValueError):off_axis_recoil_forms(p,bad)
        for bad in (True,float('nan'),float('inf'),1+0j,[1.]):
            with self.assertRaises(ValueError):off_axis_recoil_forms(p,dict(current,r0=bad))
        for order,q in ((True,16),(3,16),(2,True),(2,3),(2,33)):
            with self.assertRaises(ValueError):off_axis_recoil_forms(p,current,order,quadrature_order=q)
        with self.assertRaises(ValueError):off_axis_recoil_forms(p.to_dict(),current)
        _,k,f,m,_=off_axis_recoil_forms(p,current);a=np.linspace(-.02,.03,k.shape[0]);direction=np.linspace(.01,-.015,k.shape[0]);step=1e-4
        potential=lambda x:float(x@k@x/2-x@m);difference=(potential(a+step*direction)-potential(a-step*direction))/(2*step);derivative=float(direction@(k@a-m))
        self.assertLess(abs(difference-derivative)/abs(derivative),1e-9)
