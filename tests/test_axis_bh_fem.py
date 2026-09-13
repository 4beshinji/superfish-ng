# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from scipy.linalg import eigvalsh
from scripts.validate_axis_bh_forms import partition,reference_forms,relative
from scripts.validate_bh_curve import decimal_reference
from superfish_ng.axis_bh_fem import axis_bh_forms,axis_bh_state,_assemble
from superfish_ng.axis_bh_materials import AxisBHPartition
from superfish_ng.axis_magnetic_materials import AxisMagneticPartition
from superfish_ng.magnetic_materials import LinearMagneticMaterial
from superfish_ng.magnetostatic_fem import axis_magnetostatic_forms
from superfish_ng.constants import MU0


class AxisBHFormTests(unittest.TestCase):
    def test_constant_a_has_uniform_nonlinear_axial_field_energy_and_no_gauge_kernel(self):
        for holes in (0,1,2):
            p=partition(holes,pattern=0);coeff=np.full(len(p.mesh.points_rz_m),.375);s,k,g,f,q=axis_bh_forms(p,coeff,dict(r0=0.),quadrature_order=4);volume=p.mesh.volume_m3
            h,u,co,slope,_=decimal_reference(p.materials[0],.75)
            self.assertAlmostEqual(q['energy_j']/(u*volume),1.,places=12);self.assertAlmostEqual(q['coenergy_j']/(co*volume),1.,places=12)
            self.assertAlmostEqual(g.sum()/(2*h*volume),1.,places=12);self.assertAlmostEqual(np.ones(len(g))@k@np.ones(len(g))/(4*slope*volume),1.,places=12)
            self.assertGreater(abs(q['energy_j']-q['coenergy_j']),0.);self.assertFalse(q['constant_a_is_gauge']);self.assertGreater(eigvalsh(k.toarray())[0],0.);np.testing.assert_array_equal(f,0.)
            cells=[];bary=[]
            for cell,triangle in enumerate(p.mesh.triangles):
                for i,node in enumerate(triangle):
                    if p.mesh.points_rz_m[node,0]==0.:cells.append(cell);bary.append(np.eye(3)[i])
            state=axis_bh_state(s,coeff,cells,bary)
            np.testing.assert_array_equal(state['aphi_wb_per_m'],0.);np.testing.assert_array_equal(state['b_t'][:,0],0.);np.testing.assert_array_equal(state['h_a_per_m'][:,0],0.);np.testing.assert_allclose(state['b_t'][:,1],.75,rtol=1e-14)
            _,zg,zf,zq=_assemble(s,np.zeros(len(coeff)),np.zeros(1),4);np.testing.assert_array_equal(zg,0.);np.testing.assert_array_equal(zf,0.);self.assertEqual(zq['energy_j'],0.);self.assertEqual(zq['coenergy_j'],0.)

    def test_true_nonlinear_tangent_independent_forms_variations_scaling_and_linear_limit(self):
        p=partition(1);r,z=p.mesh.points_rz_m.T;coeff=.17*(1+.4*r+.3*z);current=dict(r0=2.,r1=-3.);s,k,g,f,q=axis_bh_forms(p,coeff,current,quadrature_order=8);rk,rg,rf,rq=reference_forms(p,coeff,current,8)
        for a,b in [(k.toarray(),rk),(g,rg),(f,rf),([q['energy_j'],q['coenergy_j']],rq[:2])]:self.assertLess(relative(a,b),1e-10)
        direction=np.cos(np.arange(len(coeff)));step=1e-7;_,gp,_,qp=_assemble(s,coeff+step*direction,np.array([2.,-3.]),8);_,gm,_,qm=_assemble(s,coeff-step*direction,np.array([2.,-3.]),8)
        self.assertLess(abs((qp['energy_j']-qm['energy_j'])/(2*step)-g@direction)/(np.linalg.norm(g)*np.linalg.norm(direction)),2e-6);self.assertLess(relative((gp-gm)/(2*step),k@direction),2e-6)
        large=partition(1,scale=2.,shift=-.25);_,lk,lg,lf,lq=axis_bh_forms(large,coeff,current,quadrature_order=8)
        for a,b in [(k.toarray(),lk.toarray()/8),(g,lg/8),(f,lf/16)]:self.assertLess(relative(a,b),1e-12)
        self.assertAlmostEqual(lq['energy_j']/q['energy_j'],8.,places=12)
        permuted=AxisBHPartition(p.mesh,p.materials[::-1],p.regions[::-1]);_,pk,pg,pf,_=axis_bh_forms(permuted,coeff,current,quadrature_order=8)
        for a,b in [(k.toarray(),pk.toarray()),(g,pg),(f,pf)]:np.testing.assert_array_equal(a,b)
        linear=partition(1,linear=True);old=AxisMagneticPartition(linear.mesh,[LinearMagneticMaterial(m.id,1/(MU0*m.h_a_per_m[1]/m.b_t[1])) for m in linear.materials],linear.regions)
        _,nk,ng,nf,nq=axis_bh_forms(linear,coeff,current,quadrature_order=4);_,ok,of,_=axis_magnetostatic_forms(old,current,1)
        self.assertLess(relative(nk.toarray(),ok.toarray()),1e-12);self.assertLess(relative(nf,of),1e-12);self.assertLess(relative(ng,nk@coeff),1e-12);self.assertAlmostEqual(nq['energy_j']/nq['coenergy_j'],1.,places=12)

    def test_quadrature_difference_and_vertex_range_are_separate_from_strict_inputs(self):
        p=partition(0);r,z=p.mesh.points_rz_m.T;coeff=.1+.9*r+.6*z;current=dict(r0=0.,r1=0.);_,_,_,_,q=axis_bh_forms(p,coeff,current,quadrature_order=4)
        self.assertGreater(q['quadrature_comparison']['tangent_relative_difference'],1e-6);self.assertGreater(q['quadrature_comparison']['energy_relative_difference'],1e-8);self.assertEqual(q['quadrature_comparison']['orders'],[4,8])
        nodes=(np.polynomial.legendre.leggauss(4)[0]+1)/2;x=np.repeat(nodes,4);y=np.tile(nodes,4)*(1-x);bary=np.column_stack((1-x-y,x,y));quadrature_max=float((p.mesh.points_rz_m[p.mesh.triangles,0]@bary.T).max());maximum=float(r.max());slope=3.5/(3*(quadrature_max+maximum)/2);values=.25+slope*r
        self.assertLess(.5+3*slope*quadrature_max,4.);self.assertGreater(.5+3*slope*maximum,4.)
        with self.assertRaisesRegex(ValueError,'outside the declared B-H table'):axis_bh_forms(p,values,current,quadrature_order=4)
        for bad in ([True]*len(r),np.ones(len(r)-1),[1+0j]*len(r)):
            with self.assertRaises(ValueError):axis_bh_forms(p,bad,current)
        for order,quad in [(2,4),(True,4),(1,True),(1,3),(1,33)]:
            with self.assertRaises(ValueError):axis_bh_forms(p,coeff,current,order,quadrature_order=quad)
        for bad in (dict(r0=0.),dict(current,extra=0.),dict(current,r0=True),dict(current,r0=float('inf'))):
            with self.assertRaises(ValueError):axis_bh_forms(p,coeff,bad)
