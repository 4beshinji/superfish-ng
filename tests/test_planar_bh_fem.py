# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from test_planar_bh_materials import partition
from superfish_ng.planar_bh_fem import planar_bh_forms,planar_bh_cell_state
from superfish_ng.magnetic_materials import PlanarMagneticPartition,LinearMagneticMaterial
from superfish_ng.planar_magnetostatic_fem import planar_magnetostatic_forms
from superfish_ng.constants import MU0


class PlanarBHFormTests(unittest.TestCase):
    def test_nonlinear_work_uses_energy_plus_coenergy_and_has_constant_gauge_kernel(self):
        p,local=partition(uniform=True);a=.75*local[:,1];space,k,g,j,q=planar_bh_forms(p,a,dict(r0=2.))
        area=p.mesh.area_m2;self.assertAlmostEqual(q['energy_j_per_m']/area,196.875,places=11);self.assertAlmostEqual(q['coenergy_j_per_m']/area,459.375,places=11)
        self.assertAlmostEqual(q['internal_work_j_per_m']/area,.75*875,places=10)
        self.assertGreater(abs(q['internal_work_j_per_m']-2*q['energy_j_per_m'])/q['internal_work_j_per_m'],.1)
        self.assertLess(np.linalg.norm(k@np.ones(len(a)))/np.linalg.norm(k.data),1e-12);self.assertLess(abs(g.sum())/np.linalg.norm(g),1e-12);self.assertAlmostEqual(j.sum(),2*area,places=14)
        _,shifted,gg,jj,qq=planar_bh_forms(p,a+.125,dict(r0=2.));np.testing.assert_array_equal(shifted.toarray(),k.toarray());np.testing.assert_array_equal(gg,g);np.testing.assert_array_equal(jj,j);self.assertEqual(qq,q)
        self.assertFalse(q['boundary_conditions_applied']);self.assertFalse(q['nonlinear_iteration_performed'])
        state=planar_bh_cell_state(space,a);np.testing.assert_allclose(state['b_t'],np.tile([.75,0.],(len(p.mesh.triangles),1)),rtol=0,atol=0)

    def test_energy_gradient_internal_load_tangent_and_geometric_material_scaling(self):
        baseline=None
        for scale,angle,shift,hscale in ((.5,0.,(0.,0.),1.),(2.,.713,(-.25,.125),7.)):
            p,local=partition(concave=True,scale=scale,angle=angle,shift=shift,h_scale=hscale);x,y=(local/scale).T;a=scale*(.2*x+.8*y+3*x*x+2*x*y)
            current={v.id:(i+1)*hscale/scale for i,v in enumerate(p.regions)};space,k,g,j,q=planar_bh_forms(p,a,current)
            normalized=(k.toarray()/hscale,g/(scale*hscale),j/(scale*hscale),np.array([q['energy_j_per_m'],q['coenergy_j_per_m']])/(scale**2*hscale))
            if baseline is None:baseline=normalized
            else:
                for left,right in zip(normalized,baseline):np.testing.assert_allclose(left,right,rtol=1e-11,atol=1e-11)
            direction=np.sin(np.arange(len(a))+.3);step=1e-7*scale
            _,_,gp,_,qp=planar_bh_forms(p,a+step*direction,current);_,_,gm,_,qm=planar_bh_forms(p,a-step*direction,current)
            self.assertAlmostEqual((qp['energy_j_per_m']-qm['energy_j_per_m'])/(2*step)/(direction@g),1.,places=6)
            np.testing.assert_allclose((gp-gm)/(2*step),k@direction,rtol=2e-6,atol=1e-7)
            _,negative,ng,nj,nq=planar_bh_forms(p,-a,{name:-v for name,v in current.items()});np.testing.assert_array_equal(negative.toarray(),k.toarray());np.testing.assert_array_equal(ng,-g);np.testing.assert_array_equal(nj,-j);self.assertEqual(nq['energy_j_per_m'],q['energy_j_per_m'])

    def test_linear_limit_zero_field_and_strict_P1_source_coefficient_contract(self):
        p,local=partition(linear=True);a=.3*local[:,0]+.4*local[:,1];current=dict(r0=2.,r1=-3.);space,k,g,j,q=planar_bh_forms(p,a,current)
        old=PlanarMagneticPartition(p.mesh,[LinearMagneticMaterial(m.id,1/(MU0*(m.h_a_per_m[1]/m.b_t[1]))) for m in p.materials],p.regions)
        _,ok,oj,_=planar_magnetostatic_forms(old,current,1)
        np.testing.assert_allclose(k.toarray(),ok.toarray(),rtol=2e-14,atol=1e-11);np.testing.assert_allclose(g,k@a,rtol=1e-13,atol=1e-11);np.testing.assert_allclose(j,oj,rtol=2e-15,atol=1e-16)
        self.assertAlmostEqual(q['energy_j_per_m'],q['coenergy_j_per_m'],places=12)
        _,zk,zg,_,zq=planar_bh_forms(p,np.full(len(a),.125),current);np.testing.assert_array_equal(zg,0.);self.assertEqual(zq['energy_j_per_m'],0.);np.testing.assert_allclose(zk.toarray(),k.toarray(),rtol=2e-14,atol=1e-11)
        for values,sources,order in [(a,{},1),(a,dict(r0=True,r1=0.),1),(a,current,True),(a,current,2),(a[:-1],current,1),([False,*a[1:]],current,1),(100*a,current,1)]:
            with self.assertRaises(ValueError):planar_bh_forms(p,values,sources,order)
