# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from scipy.linalg import eigvalsh
from superfish_ng.constants import EPS0,TAU
from superfish_ng.electrostatic_fem import axisymmetric_electrostatic_forms
from superfish_ng.dielectrics import AxisymmetricDielectricPartition
from test_dielectrics import partition


def moment(p,a,b,region,scale=1.):
    value=0.
    for polygon,sign in [(p.mesh.outer_rz_m,1),*((h,-1) for h in p.mesh.holes_rz_m)]:
        r0,z0=polygon.min(axis=0);r1,z1=polygon.max(axis=0)
        if region=='bottom':z1=min(z1,scale/16)
        elif region=='top':z0=max(z0,scale/16)
        if z1>z0:value+=sign*TAU*(r1**(a+2)-r0**(a+2))/(a+2)*(z1**(b+1)-z0**(b+1))/(b+1)
    return value


class ElectrostaticFormTests(unittest.TestCase):
    def test_constant_potential_kernel_and_independent_polynomial_energy_and_charge_work(self):
        for axis in (False,True):
            for holes in (0,1,2):
                for order in (1,2):
                    p=partition(axis,holes);rho={'bottom':2.,'top':-3.};space,k,f,report=axisymmetric_electrostatic_forms(p,rho,order)
                    self.assertLess(np.linalg.norm(k@np.ones(k.shape[0]))/np.linalg.norm(k.data),1e-12)
                    eigen=eigvalsh(k.toarray());self.assertLess(abs(eigen[0])/eigen[-1],1e-12);self.assertGreater(eigen[1]/eigen[-1],1e-6)
                    if axis:self.assertGreater(len(space.axis_dofs),0)
                    r,z=space.dof_points.T
                    polynomials=[(r,1,0,[(1.,0,0)]),(z,0,1,[(1.,0,0)])]
                    if order==2:polynomials += [(r*r,2,0,[(4.,2,0)]),(r*z,1,1,[(1.,2,0),(1.,0,2)]),(z*z,0,2,[(4.,0,2)])]
                    for coefficients,a,b,gradient_square in polynomials:
                        energy=EPS0*sum(eps*sum(c*moment(p,x,y,region) for c,x,y in gradient_square) for eps,region in ((2.,'bottom'),(5.,'top')))
                        work=sum(density*moment(p,a,b,region) for region,density in rho.items())
                        self.assertAlmostEqual(float(coefficients@k@coefficients)/energy,1.,places=11)
                        self.assertAlmostEqual(float(coefficients@f)/work,1.,places=12)
                    charge=sum(density*moment(p,0,0,region) for region,density in rho.items())
                    self.assertAlmostEqual(f.sum()/charge,1.,places=12)
                    self.assertEqual(report['stiffness_unit'],'F');self.assertFalse(report['boundary_conditions_applied'])

    def test_signed_charge_epsilon_and_spatial_scaling_and_region_reordering(self):
        for axis in (False,True):
            for order in (1,2):
                original=None
                for scale in (.5,2.):
                    p=partition(axis,2,scale=scale);rho={'bottom':2.,'top':-3.}
                    space,k,f,_=axisymmetric_electrostatic_forms(p,rho,order)
                    if original is None:original=k,f
                    else:
                        np.testing.assert_allclose(k.toarray(),original[0].toarray()*4,rtol=1e-12,atol=1e-25)
                        np.testing.assert_allclose(f,original[1]*64,rtol=1e-12,atol=1e-16)
                    reverse=AxisymmetricDielectricPartition(p.mesh,p.materials[::-1],p.regions[::-1])
                    _,rk,rf,_=axisymmetric_electrostatic_forms(reverse,rho,order)
                    np.testing.assert_array_equal(k.toarray(),rk.toarray());np.testing.assert_array_equal(f,rf)
                    _,_,negative,_=axisymmetric_electrostatic_forms(p,{key:-v for key,v in rho.items()},order)
                    np.testing.assert_array_equal(negative,-f)
                    _,_,zero,_=axisymmetric_electrostatic_forms(p,dict(bottom=0.,top=0.),order);np.testing.assert_array_equal(zero,0.)
                    volumes=[moment(p,0,0,name,scale) for name in ('bottom','top')]
                    balanced=dict(bottom=1.,top=-volumes[0]/volumes[1])
                    _,_,cancel,diagnostic=axisymmetric_electrostatic_forms(p,balanced,order)
                    self.assertLess(abs(cancel.sum())/sum(volumes),1e-13)
                    self.assertLess(diagnostic['charge_conservation_relative_difference'],1e-13)
                    self.assertGreater(np.linalg.norm(cancel),0.)
                    raw=p.to_dict()
                    for m in raw['materials']:m['epsilon_r']*=7
                    _,scaled,_,_=axisymmetric_electrostatic_forms(AxisymmetricDielectricPartition.from_dict(raw),rho,order)
                    np.testing.assert_allclose(scaled.toarray(),k.toarray()*7,rtol=1e-12,atol=1e-25)

    def test_strict_signed_region_charge_and_controls(self):
        p=partition(True,2);rho=dict(bottom=1.,top=-1.)
        for bad in (True,float('nan'),float('inf'),1+0j,[1.],10**1000):
            with self.assertRaises(ValueError):axisymmetric_electrostatic_forms(p,dict(bottom=bad,top=0.))
        for bad in (dict(bottom=0.),dict(rho,extra=0.),[0.,0.]):
            with self.assertRaises(ValueError):axisymmetric_electrostatic_forms(p,bad)
        for order,quadrature in ((True,4),(3,4),(2,True),(2,3),(2,33)):
            with self.assertRaises(ValueError):axisymmetric_electrostatic_forms(p,rho,order,quadrature_order=quadrature)
        with self.assertRaises(ValueError):axisymmetric_electrostatic_forms(p.to_dict(),rho)
