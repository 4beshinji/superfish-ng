# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from scipy.linalg import eigvalsh
from superfish_ng.constants import MU0,TAU
from superfish_ng.magnetostatic_fem import axis_magnetostatic_forms
from superfish_ng.axis_magnetic_materials import AxisMagneticPartition
from test_axis_magnetic_materials import partition


def moment(p,a,b,region,scale=1.):
    value=0.
    for polygon,sign in [(p.mesh.outer_rz_m,1),*((h,-1) for h in p.mesh.holes_rz_m)]:
        r0,z0=polygon.min(axis=0);r1,z1=polygon.max(axis=0)
        if region=='bottom':z1=min(z1,scale/16)
        elif region=='top':z0=max(z0,scale/16)
        if z1>z0:value+=sign*TAU*(r1**(a+2)-r0**(a+2))/(a+2)*(z1**(b+1)-z0**(b+1))/(b+1)
    return value


class AxisMagneticFormTests(unittest.TestCase):
    def test_uniform_axial_field_is_not_gauge_and_polynomial_energy_current_work(self):
        for holes in (0,1,2):
            for order in (1,2):
                p=partition(holes=holes);current={'bottom':2.,'top':-3.};space,k,f,report=axis_magnetostatic_forms(p,current,order)
                eigen=eigvalsh(k.toarray());self.assertGreater(eigen[0]/eigen[-1],1e-9);self.assertGreater(len(space.axis_dofs),0)
                self.assertGreater(np.linalg.norm(k@np.ones(k.shape[0]))/np.linalg.norm(k.data),.01)
                r,z=space.dof_points.T;polynomials=[(0,0),(1,0),(0,1)]+([(2,0),(1,1),(0,2)] if order==2 else [])
                for a,b in polynomials:
                    c=r**a*z**b
                    energy=sum((1./MU0)/mu*((a+2)**2*moment(p,2*a,2*b,region)+(b*b*moment(p,2*a+2,2*b-2,region) if b else 0.)) for mu,region in ((2.,'bottom'),(5.,'top')))
                    work=sum(density*moment(p,a+1,b,region) for region,density in current.items())
                    self.assertAlmostEqual(float(c@k@c)/energy,1.,places=11);self.assertAlmostEqual(float(c@f)/work,1.,places=11)
                expected=sum(density*moment(p,1,0,region) for region,density in current.items())
                self.assertAlmostEqual(f.sum()/expected,1.,places=12)
                self.assertAlmostEqual(report['total_source_current_a'],sum(current[region.id]*area for region,area in zip(p.regions,p.region_area_m2)),places=13)
                self.assertEqual(report['stiffness_unit'],'m^4/H');self.assertEqual(report['load_unit'],'A m^2');self.assertEqual(report['energy_unit'],'J')
                self.assertFalse(report['constant_a_is_gauge']);self.assertFalse(report['boundary_conditions_applied'])

    def test_current_reversal_mu_inverse_geometry_scaling_and_region_permutation(self):
        for order in (1,2):
            original=None
            for scale in (.5,2.):
                p=partition(holes=2,scale=scale);current={'bottom':2.,'top':-3.};space,k,f,_=axis_magnetostatic_forms(p,current,order)
                if original is None:original=k,f
                else:
                    self.assertLess(np.linalg.norm((k/64-original[0]).data)/np.linalg.norm(original[0].data),1e-12)
                    np.testing.assert_allclose(f/256,original[1],rtol=1e-12,atol=1e-20)
                reverse=AxisMagneticPartition(p.mesh,p.materials[::-1],p.regions[::-1]);_,rk,rf,_=axis_magnetostatic_forms(reverse,current,order)
                np.testing.assert_array_equal(k.toarray(),rk.toarray());np.testing.assert_array_equal(f,rf)
                _,_,negative,_=axis_magnetostatic_forms(p,{key:-v for key,v in current.items()},order);np.testing.assert_array_equal(negative,-f)
                _,_,zero,_=axis_magnetostatic_forms(p,dict(bottom=0.,top=0.),order);np.testing.assert_array_equal(zero,0.)
                moments=[moment(p,1,0,name,scale) for name in ('bottom','top')];balanced=dict(bottom=1.,top=-moments[0]/moments[1])
                _,_,cancel,diagnostic=axis_magnetostatic_forms(p,balanced,order)
                self.assertLess(abs(cancel.sum())/sum(moments),1e-13);self.assertLess(diagnostic['current_work_relative_difference'],1e-13);self.assertGreater(np.linalg.norm(cancel),0.)
                raw=p.to_dict()
                for material in raw['materials']:material['mu_r']*=7
                _,scaled,unchanged,_=axis_magnetostatic_forms(AxisMagneticPartition.from_dict(raw),current,order)
                self.assertLess(np.linalg.norm((scaled*7-k).data)/np.linalg.norm(k.data),1e-12);np.testing.assert_array_equal(unchanged,f)

    def test_strict_source_controls_and_axis_geometry(self):
        p=partition(holes=2);current=dict(bottom=1.,top=-1.)
        for bad in (True,float('nan'),float('inf'),1+0j,[1.],10**1000):
            with self.assertRaises(ValueError):axis_magnetostatic_forms(p,dict(bottom=bad,top=0.))
        for bad in (dict(bottom=0.),dict(current,extra=0.),[0.,0.]):
            with self.assertRaises(ValueError):axis_magnetostatic_forms(p,bad)
        for order,quadrature in ((True,4),(3,4),(2,True),(2,3),(2,33)):
            with self.assertRaises(ValueError):axis_magnetostatic_forms(p,current,order,quadrature_order=quadrature)
        with self.assertRaises(ValueError):axis_magnetostatic_forms(p.to_dict(),current)
