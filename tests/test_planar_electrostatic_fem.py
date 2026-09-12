# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from scipy.linalg import eigvalsh
from superfish_ng.constants import EPS0
from superfish_ng.planar_dielectrics import PlanarDielectricPartition
from superfish_ng.planar_electrostatic_fem import planar_electrostatic_forms
from test_planar_dielectrics import partition


def moment(concave,a,b,region):
    rectangles=[(-1.,1.,-1.,1.,1)]
    if concave:rectangles.append((0.,1.,0.,1.,-1))
    result=0.
    for x0,x1,y0,y1,sign in rectangles:
        if region=='bottom':y1=min(y1,0.)
        else:y0=max(y0,0.)
        if y1>y0:result+=sign*(x1**(a+1)-x0**(a+1))/(a+1)*(y1**(b+1)-y0**(b+1))/(b+1)/32**(a+b+2)
    return result


class PlanarElectrostaticFormTests(unittest.TestCase):
    def test_all_dofs_and_constant_kernel_with_independent_polynomial_integrals(self):
        for concave in (False,True):
            for order in (1,2):
                p=partition(concave);rho=dict(bottom=2.,top=-3.);space,k,f,report=planar_electrostatic_forms(p,rho,order)
                self.assertEqual(k.shape,(len(space.dof_points_xy_m),)*2);self.assertFalse(hasattr(space,'axis_dofs'))
                self.assertGreater(np.count_nonzero(space.dof_points_xy_m[:,0]==0),0)
                self.assertLess(np.linalg.norm(k@np.ones(k.shape[0]))/np.linalg.norm(k.data),1e-12)
                spectrum=eigvalsh(k.toarray());self.assertLess(abs(spectrum[0])/spectrum[-1],1e-12);self.assertGreater(spectrum[1]/spectrum[-1],1e-6)
                x,y=space.dof_points_xy_m.T;polynomials=[(x,1,0,[(1.,0,0)]),(y,0,1,[(1.,0,0)])]
                if order==2:polynomials += [(x*x,2,0,[(4.,2,0)]),(x*y,1,1,[(1.,2,0),(1.,0,2)]),(y*y,0,2,[(4.,0,2)])]
                for c,a,b,terms in polynomials:
                    energy=EPS0*sum(eps*sum(v*moment(concave,i,j,region) for v,i,j in terms) for eps,region in ((2.,'bottom'),(5.,'top')))
                    work=sum(value*moment(concave,a,b,region) for region,value in rho.items())
                    self.assertAlmostEqual(float(c@k@c)/energy,1.,places=12)
                    self.assertLess(abs(c@f-work)/(np.max(abs(c))*sum(abs(value)*moment(concave,0,0,region) for region,value in rho.items())),1e-12)
                charge=sum(value*moment(concave,0,0,region) for region,value in rho.items());self.assertAlmostEqual(f.sum()/charge,1.,places=12)
                self.assertEqual(report['stiffness_unit'],'F/m');self.assertEqual(report['load_unit'],'C/m');self.assertFalse(report['boundary_conditions_applied'])

    def test_planar_scale_rigid_motion_epsilon_and_signed_charge_invariants(self):
        rotations=[np.eye(2),np.array([[0.,-1.],[1.,0.]]),np.array([[.6,-.8],[.8,.6]])]
        for concave in (False,True):
            for order in (1,2):
                rho=dict(bottom=2.,top=-3.);base=planar_electrostatic_forms(partition(concave),rho,order)
                for scale in (.5,2.):
                    for rotation in rotations:
                        p=partition(concave,scale,rotation,[-.375,.25]);space,k,f,_=planar_electrostatic_forms(p,rho,order)
                        self.assertLess(np.linalg.norm((k-base[1]).data)/np.linalg.norm(base[1].data),1e-12)
                        self.assertLess(np.linalg.norm(f/scale**2-base[2])/np.linalg.norm(base[2]),1e-12)
                p=partition(concave);raw=p.to_dict();raw['materials'].reverse();raw['regions'].reverse()
                _,k,f,_=planar_electrostatic_forms(PlanarDielectricPartition.from_dict(raw),rho,order)
                np.testing.assert_array_equal(k.toarray(),base[1].toarray());np.testing.assert_array_equal(f,base[2])
                for material in raw['materials']:material['epsilon_r']*=7
                _,k,_,_=planar_electrostatic_forms(PlanarDielectricPartition.from_dict(raw),rho,order)
                self.assertLess(np.linalg.norm((k/7-base[1]).data)/np.linalg.norm(base[1].data),1e-12)
                _,_,negative,_=planar_electrostatic_forms(p,{key:-value for key,value in rho.items()},order);np.testing.assert_array_equal(negative,-base[2])
                _,_,zero,_=planar_electrostatic_forms(p,dict(bottom=0.,top=0.),order);np.testing.assert_array_equal(zero,0.)
                balanced=dict(bottom=1.,top=-2./(1 if concave else 2));_,_,f,report=planar_electrostatic_forms(p,balanced,order)
                self.assertLess(abs(f.sum())/p.mesh.area_m2,1e-13);self.assertGreater(np.linalg.norm(f),0.)

    def test_strict_source_controls_and_no_axisymmetric_partition(self):
        p=partition();rho=dict(bottom=1.,top=0.)
        for bad in (True,float('inf'),float('nan'),1+1j,10**1000,[1]):
            with self.assertRaises(ValueError):planar_electrostatic_forms(p,dict(bottom=bad,top=0.))
        for bad in (dict(bottom=0.),dict(rho,extra=0.),[0.,0.]):
            with self.assertRaises(ValueError):planar_electrostatic_forms(p,bad)
        for order,quadrature in ((True,4),(3,4),(2,True),(2,3),(2,33)):
            with self.assertRaises(ValueError):planar_electrostatic_forms(p,rho,order,quadrature_order=quadrature)
        with self.assertRaises(ValueError):planar_electrostatic_forms(p.to_dict(),rho)
