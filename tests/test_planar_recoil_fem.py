# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from test_recoil_materials import partition
from superfish_ng.recoil_materials import PlanarRecoilPartition
from superfish_ng.planar_recoil_fem import planar_recoil_forms
from superfish_ng.constants import MU0


class PlanarRecoilFormTests(unittest.TestCase):
    def test_zero_H_remanence_equilibrium_and_two_constitutive_potentials(self):
        for order in (1,2):
            p=partition(uniform=True);space,k,j,m,report=planar_recoil_forms(p,dict(all=0.),order)
            x,y=space.dof_points_xy_m.T;remanent=p.remanent_b_t[0];coefficient=remanent[0]*y-remanent[1]*x
            self.assertLess(np.linalg.norm(k@coefficient-m)/np.linalg.norm(m),1e-12)
            self.assertLess(np.linalg.norm(k@np.ones(len(x)))/np.linalg.norm(k.data),1e-12);self.assertLess(abs(m.sum())/np.linalg.norm(m),1e-12)
            material=p.materials[0];angle=p.regions[0].orientation_rad;c,s=np.cos(angle),np.sin(angle);rotation=np.array([[c,-s],[s,c]])
            inverse=rotation@np.diag(1/(MU0*np.asarray(material.mu_r_principal)))@rotation.T
            for factor in (.5,1.,-1.):
                coeff=factor*coefficient;b=factor*remanent;area=p.mesh.area_m2
                w0=float(.5*coeff@k@coeff-coeff@m);shifted=w0+report['remanent_reference_constant_j_per_m']
                expected=(.5*b@inverse@b-b@inverse@remanent)*area
                self.assertAlmostEqual(w0/expected,1.,places=12)
                expected_shift=.5*(b-remanent)@inverse@(b-remanent)*area
                self.assertLess(abs(shifted-expected_shift)/report['remanent_reference_constant_j_per_m'],1e-12)
                if factor==.5:self.assertLess(w0,0.);self.assertGreater(shifted,0.)
            np.testing.assert_array_equal(j,0.);self.assertFalse(report['boundary_conditions_applied'])

    def test_rotation_translation_scale_mu_inverse_and_source_reversal(self):
        for order in (1,2):
            baseline=None
            for scale,angle,shift in ((.5,0.,(0.,0.)),(2.,.7,(-.25,.125))):
                p=partition(concave=True,scale=scale,angle=angle,shift=shift);current=dict(bottom=2.,top=-3.)
                space,k,j,m,report=planar_recoil_forms(p,current,order)
                values=k,j/scale**2,m/scale
                if baseline is None:baseline=values
                else:
                    self.assertLess(np.linalg.norm((k-baseline[0]).data)/np.linalg.norm(k.data),1e-12)
                    for left,right in zip(values[1:],baseline[1:]):self.assertLess(np.linalg.norm(left-right)/np.linalg.norm(right),1e-12)
                raw=p.to_dict()
                for material in raw['materials']:material['mu_r_principal']=[7*v for v in material['mu_r_principal']]
                _,scaled,same,rm,_=planar_recoil_forms(PlanarRecoilPartition.from_dict(raw),current,order)
                self.assertLess(np.linalg.norm((7*scaled-k).data)/np.linalg.norm(k.data),1e-12);np.testing.assert_array_equal(same,j)
                self.assertLess(np.linalg.norm(7*rm-m)/np.linalg.norm(m),1e-12)
                raw=p.to_dict()
                for material in raw['materials']:material['remanent_b_local_t']=[-v for v in material['remanent_b_local_t']]
                _,unchanged,negative_j,negative_m,_=planar_recoil_forms(PlanarRecoilPartition.from_dict(raw),{key:-v for key,v in current.items()},order)
                np.testing.assert_array_equal(unchanged.toarray(),k.toarray());np.testing.assert_array_equal(negative_j,-j);np.testing.assert_array_equal(negative_m,-m)

    def test_isotropic_zero_remanence_limit_and_strict_source_controls(self):
        from superfish_ng.magnetic_materials import PlanarMagneticPartition,LinearMagneticMaterial,MagneticRegion
        from superfish_ng.planar_magnetostatic_fem import planar_magnetostatic_forms
        p=partition();raw=p.to_dict()
        for material in raw['materials']:material.update(mu_r_principal=[3.,3.],remanent_b_local_t=[0.,0.])
        p=PlanarRecoilPartition.from_dict(raw);current=dict(bottom=2.,top=-3.)
        old=PlanarMagneticPartition(p.mesh,[LinearMagneticMaterial(m.id,3.) for m in p.materials],[MagneticRegion(v.id,v.material,v.cell_indices) for v in p.regions])
        for order in (1,2):
            _,k,j,m,report=planar_recoil_forms(p,current,order);_,ok,oj,_=planar_magnetostatic_forms(old,current,order)
            self.assertLess(np.linalg.norm((k-ok).data)/np.linalg.norm(ok.data),1e-12);np.testing.assert_array_equal(j,oj);np.testing.assert_array_equal(m,0.)
            self.assertEqual(report['remanent_reference_constant_j_per_m'],0.)
        for bad in ({},dict(bottom=True,top=0.),dict(current,extra=0.)):
            with self.assertRaises(ValueError):planar_recoil_forms(p,bad)
        for order,q in ((True,4),(3,4),(2,True),(2,3),(2,33)):
            with self.assertRaises(ValueError):planar_recoil_forms(p,current,order,quadrature_order=q)
        with self.assertRaises(ValueError):planar_recoil_forms(old,current)
