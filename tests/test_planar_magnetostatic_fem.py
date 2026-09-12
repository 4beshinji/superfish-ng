# SPDX-License-Identifier: Apache-2.0
import unittest
import numpy as np
from scipy.linalg import eigvalsh
from superfish_ng.constants import MU0
from superfish_ng.magnetic_materials import PlanarMagneticPartition
from superfish_ng.planar_magnetostatic_fem import planar_magnetostatic_forms
from test_magnetic_materials import partition


def moment(concave,a,b,region):
    rectangles=[(-1.,1.,-1.,1.,1)]
    if concave:rectangles.append((0.,1.,0.,1.,-1))
    result=0.
    for x0,x1,y0,y1,sign in rectangles:
        if region=='bottom':y1=min(y1,0.)
        else:y0=max(y0,0.)
        if y1>y0:result+=sign*(x1**(a+1)-x0**(a+1))/(a+1)*(y1**(b+1)-y0**(b+1))/(b+1)/32**(a+b+2)
    return result


class PlanarMagnetostaticFormTests(unittest.TestCase):
    def test_all_dofs_and_constant_kernel_with_independent_polynomial_integrals(self):
        for concave in (False,True):
            for order in (1,2):
                p=partition(concave);current=dict(bottom=2.,top=-3.);space,k,f,report=planar_magnetostatic_forms(p,current,order)
                self.assertEqual(k.shape,(len(space.dof_points_xy_m),)*2);self.assertFalse(hasattr(space,'axis_dofs'))
                self.assertGreater(np.count_nonzero(space.dof_points_xy_m[:,0]==0),0)
                self.assertLess(np.linalg.norm(k@np.ones(k.shape[0]))/np.linalg.norm(k.data),1e-12)
                spectrum=eigvalsh(k.toarray());self.assertLess(abs(spectrum[0])/spectrum[-1],1e-12);self.assertGreater(spectrum[1]/spectrum[-1],1e-6)
                x,y=space.dof_points_xy_m.T;polynomials=[(x,1,0,[(1.,0,0)]),(y,0,1,[(1.,0,0)])]
                if order==2:polynomials += [(x*x,2,0,[(4.,2,0)]),(x*y,1,1,[(1.,2,0),(1.,0,2)]),(y*y,0,2,[(4.,0,2)])]
                for c,a,b,terms in polynomials:
                    energy=(1/MU0)*sum((1/mu)*sum(v*moment(concave,i,j,region) for v,i,j in terms) for mu,region in ((2.,'bottom'),(5.,'top')))
                    work=sum(value*moment(concave,a,b,region) for region,value in current.items())
                    self.assertAlmostEqual(float(c@k@c)/energy,1.,places=12)
                    self.assertLess(abs(c@f-work)/(np.max(abs(c))*sum(abs(value)*moment(concave,0,0,region) for region,value in current.items())),1e-12)
                uniform=.125+2*x-3*y;expected_energy=.5*13/MU0*sum(moment(concave,0,0,region)/mu for mu,region in ((2.,'bottom'),(5.,'top')))
                self.assertAlmostEqual(float(.5*uniform@k@uniform)/expected_energy,1.,places=11)
                current=sum(value*moment(concave,0,0,region) for region,value in current.items());self.assertAlmostEqual(f.sum()/current,1.,places=12)
                self.assertEqual(report['stiffness_unit'],'m/H');self.assertEqual(report['load_unit'],'A');self.assertFalse(report['boundary_conditions_applied'])

    def test_planar_scale_rigid_motion_mu_and_signed_current_invariants(self):
        rotations=[np.eye(2),np.array([[0.,-1.],[1.,0.]]),np.array([[.6,-.8],[.8,.6]])]
        for concave in (False,True):
            for order in (1,2):
                current=dict(bottom=2.,top=-3.);base=planar_magnetostatic_forms(partition(concave),current,order)
                for scale in (.5,2.):
                    for rotation in rotations:
                        p=partition(concave,scale,rotation,[-.375,.25]);space,k,f,_=planar_magnetostatic_forms(p,current,order)
                        self.assertLess(np.linalg.norm((k-base[1]).data)/np.linalg.norm(base[1].data),1e-12)
                        self.assertLess(np.linalg.norm(f/scale**2-base[2])/np.linalg.norm(base[2]),1e-12)
                p=partition(concave);raw=p.to_dict();raw['materials'].reverse();raw['regions'].reverse()
                _,k,f,_=planar_magnetostatic_forms(PlanarMagneticPartition.from_dict(raw),current,order)
                np.testing.assert_array_equal(k.toarray(),base[1].toarray());np.testing.assert_array_equal(f,base[2])
                for material in raw['materials']:material['mu_r']*=7
                _,k,_,_=planar_magnetostatic_forms(PlanarMagneticPartition.from_dict(raw),current,order)
                self.assertLess(np.linalg.norm((k*7-base[1]).data)/np.linalg.norm(base[1].data),1e-12)
                _,_,negative,_=planar_magnetostatic_forms(p,{key:-value for key,value in current.items()},order);np.testing.assert_array_equal(negative,-base[2])
                _,_,zero,_=planar_magnetostatic_forms(p,dict(bottom=0.,top=0.),order);np.testing.assert_array_equal(zero,0.)
                balanced=dict(bottom=1.,top=-2./(1 if concave else 2));_,_,f,report=planar_magnetostatic_forms(p,balanced,order)
                self.assertLess(abs(f.sum())/p.mesh.area_m2,1e-13);self.assertGreater(np.linalg.norm(f),0.)

    def test_strict_source_controls_and_no_axisymmetric_partition(self):
        p=partition();current=dict(bottom=1.,top=0.)
        for bad in (True,float('inf'),float('nan'),1+1j,10**1000,[1]):
            with self.assertRaises(ValueError):planar_magnetostatic_forms(p,dict(bottom=bad,top=0.))
        for bad in (dict(bottom=0.),dict(current,extra=0.),[0.,0.]):
            with self.assertRaises(ValueError):planar_magnetostatic_forms(p,bad)
        for order,quadrature in ((True,4),(3,4),(2,True),(2,3),(2,33)):
            with self.assertRaises(ValueError):planar_magnetostatic_forms(p,current,order,quadrature_order=quadrature)
        with self.assertRaises(ValueError):planar_magnetostatic_forms(p.to_dict(),current)
        from scripts.electrostatic_reference import parallel_plate
        with self.assertRaises(ValueError):planar_magnetostatic_forms(parallel_plate()[0].partition,current)
