# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from scipy.linalg import eigvalsh
from scripts.validate_off_axis_bh_forms import partition,reference_forms,relative,analytic_partition,radial_energy_reference
from superfish_ng.off_axis_bh_fem import off_axis_bh_forms,off_axis_bh_state,_assemble
from superfish_ng.off_axis_bh_materials import OffAxisBHPartition
from superfish_ng.off_axis_magnetic_materials import OffAxisMagneticPartition
from superfish_ng.magnetic_materials import LinearMagneticMaterial
from superfish_ng.off_axis_magnetostatic_fem import off_axis_magnetostatic_forms
from superfish_ng.constants import MU0,TAU


class OffAxisBHFormTests(unittest.TestCase):
    def test_constant_psi_zero_field_nonzero_aphi_kernel_and_logarithmic_nonlinear_energy(self):
        for holes in (0,1,2):
            p=partition(holes,pattern=0);coeff=np.full(len(p.mesh.points_rz_m),.125);s,k,g,f,q=off_axis_bh_forms(p,coeff,dict(r0=0.),quadrature_order=4)
            np.testing.assert_array_equal(g,0.);np.testing.assert_array_equal(f,0.);self.assertEqual(q['energy_j'],0.);self.assertEqual(q['coenergy_j'],0.)
            self.assertTrue(q['constant_psi_kernel_retained']);self.assertFalse(q['axis_present']);eigen=eigvalsh(k.toarray());self.assertLess(abs(eigen[0]/eigen[-1]),1e-12);self.assertGreater(eigen[1],0.)
            cells=np.arange(len(p.mesh.triangles));state=off_axis_bh_state(s,coeff,cells,np.full((len(cells),3),1/3))
            np.testing.assert_array_equal(state['b_t'],0.);np.testing.assert_array_equal(state['h_a_per_m'],0.);np.testing.assert_array_equal(state['psi_wb'],.125)
            np.testing.assert_allclose(state['aphi_wb_per_m'],.125/state['radius_m'],rtol=0,atol=0)
            analytic=analytic_partition(holes);r,z=analytic.mesh.points_rz_m.T;c=.03125;values=-c*z
            ns,_,_,_,nq=off_axis_bh_forms(analytic,values,dict(r0=0.),quadrature_order=24);exact=radial_energy_reference(analytic,c)
            self.assertLess(relative([nq['energy_j'],nq['coenergy_j']],exact),1e-11);self.assertNotEqual(exact[0],exact[1])
            original=off_axis_bh_state(ns,values,cells,np.full((len(cells),3),1/3))
            np.testing.assert_allclose(original['b_t'][:,0],c/original['radius_m'],rtol=1e-13);np.testing.assert_allclose(original['b_t'][:,1],0.,atol=1e-14)

    def test_true_tangent_independent_forms_variations_covariance_gauge_and_linear_limit(self):
        p=partition(1);r,z=p.mesh.points_rz_m.T;coeff=.03*(-z+.3*r);current=dict(r0=2.,r1=-3.);s,k,g,f,q=off_axis_bh_forms(p,coeff,current,quadrature_order=12);rk,rg,rf,rq=reference_forms(p,coeff,current,12)
        for a,b in [(k.toarray(),rk),(g,rg),(f,rf),([q['energy_j'],q['coenergy_j']],rq[:2])]:self.assertLess(relative(a,b),1e-10)
        direction=np.cos(np.arange(len(coeff)));step=1e-10;_,gp,_,qp=_assemble(s,coeff+step*direction,np.array([2.,-3.]),12);_,gm,_,qm=_assemble(s,coeff-step*direction,np.array([2.,-3.]),12)
        self.assertLess(abs((qp['energy_j']-qm['energy_j'])/(2*step)-g@direction)/(np.linalg.norm(g)*np.linalg.norm(direction)),2e-6);self.assertLess(relative((gp-gm)/(2*step),k@direction),2e-6)
        large=partition(1,scale=2.,shift=-.25);_,lk,lg,lf,lq=off_axis_bh_forms(large,4*coeff,current,quadrature_order=12)
        for a,b in [(k.toarray(),2*lk.toarray()),(g,lg/2),(f,lf/4)]:self.assertLess(relative(a,b),1e-12)
        self.assertAlmostEqual(lq['energy_j']/q['energy_j'],8.,places=12)
        _,gk,gg,_,gq=off_axis_bh_forms(p,coeff+.125,current,quadrature_order=12)
        for a,b in [(k.toarray(),gk.toarray()),(g,gg),([q['energy_j'],q['coenergy_j']],[gq['energy_j'],gq['coenergy_j']])]:self.assertLess(relative(a,b),1e-11)
        permuted=OffAxisBHPartition(p.mesh,p.materials[::-1],p.regions[::-1]);_,pk,pg,pf,_=off_axis_bh_forms(permuted,coeff,current,quadrature_order=12)
        for a,b in [(k.toarray(),pk.toarray()),(g,pg),(f,pf)]:np.testing.assert_array_equal(a,b)
        linear=partition(1,linear=True);old=OffAxisMagneticPartition(linear.mesh,[LinearMagneticMaterial(m.id,1/(MU0*m.h_a_per_m[1]/m.b_t[1])) for m in linear.materials],linear.regions)
        _,nk,ng,nf,nq=off_axis_bh_forms(linear,coeff,current,quadrature_order=16);_,ok,of,_=off_axis_magnetostatic_forms(old,current,1,quadrature_order=16)
        self.assertLess(relative(nk.toarray(),ok.toarray()),1e-12);self.assertLess(relative(nf,of),1e-12);self.assertLess(relative(ng,nk@(coeff-coeff[0])),1e-12);self.assertAlmostEqual(nq['energy_j']/nq['coenergy_j'],1.,places=12)
        self.assertAlmostEqual(f.sum()/TAU,sum(current[v.id]*p.region_area_m2[i] for i,v in enumerate(p.regions)),places=13)

    def test_quadrature_difference_whole_cell_range_and_strict_inputs(self):
        p=partition(0);r,z=p.mesh.points_rz_m.T;coeff=-.045*z;current=dict(r0=0.,r1=0.);_,_,_,_,q=off_axis_bh_forms(p,coeff,current,quadrature_order=4)
        self.assertGreater(q['quadrature_comparison']['tangent_relative_difference'],1e-6);self.assertGreater(q['quadrature_comparison']['energy_relative_difference'],1e-8);self.assertEqual(q['quadrature_comparison']['orders'],[4,8])
        nodes=(np.polynomial.legendre.leggauss(4)[0]+1)/2;x=np.repeat(nodes,4);y=np.tile(nodes,4)*(1-x);bary=np.column_stack((1-x-y,x,y));quadrature_min=float((p.mesh.points_rz_m[p.mesh.triangles,0]@bary.T).min());minimum=float(r.min());c=4*(quadrature_min+minimum)/2;values=-c*z
        self.assertLess(c/quadrature_min,4.);self.assertGreater(c/minimum,4.)
        with self.assertRaisesRegex(ValueError,'outside the declared B-H table'):off_axis_bh_forms(p,values,current,quadrature_order=4)
        for bad in ([True]*len(r),np.ones(len(r)-1),[1+0j]*len(r)):
            with self.assertRaises(ValueError):off_axis_bh_forms(p,bad,current)
        for order,quad in [(2,4),(True,4),(1,True),(1,3),(1,33)]:
            with self.assertRaises(ValueError):off_axis_bh_forms(p,coeff,current,order,quadrature_order=quad)
        for bad in (dict(r0=0.),dict(current,extra=0.),dict(current,r0=True),dict(current,r0=float('inf')),dict(current,r0=5e-324)):
            with self.assertRaises(ValueError):off_axis_bh_forms(p,coeff,bad)
