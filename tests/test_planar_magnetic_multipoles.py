# SPDX-License-Identifier: Apache-2.0
import copy,unittest
import numpy as np
from scripts.validate_planar_magnetic_multipoles import reference_field,relative,fourier_reference
from superfish_ng.planar_magnetic_multipoles import PlanarMagneticMultipoleFrame as Frame,PlanarMagneticMultipoleSeries as Series


class PlanarMagneticMultipoleTests(unittest.TestCase):
    def test_normal_skew_orders_and_global_field_signs_with_independent_Cartesian_powers(self):
        frame=Frame((0.,0.),.125,0.);points=np.array([[.0625,.03125],[-.025,.05],[0.,0.]])
        for count in range(1,9):
            for skew in (False,True):
                a=np.zeros(count);b=a.copy();(b if skew else a)[-1]=2.;s=Series(frame,a,b,'synthetic pure multipole')
                self.assertLess(relative(s.evaluate(points),reference_field(s,points)),1e-12)
        normal=Series(frame,(0.,1.),(0.,0.),'synthetic normal quadrupole');skew=Series(frame,(0.,0.),(0.,1.),'synthetic skew quadrupole')
        np.testing.assert_allclose(normal.evaluate(points),points[:,::-1]/.125,rtol=1e-14,atol=0.)
        np.testing.assert_allclose(skew.evaluate(points),np.column_stack((points[:,0],-points[:,1]))/.125,rtol=1e-14,atol=0.)
        self.assertFalse(normal.evaluate(points).flags.writeable)

    def test_explicit_feed_down_radius_and_passive_rotation_coefficients(self):
        source=Series(Frame((0.,0.),1.,0.),(1.,2.,3.),(0.,0.,0.),'synthetic mixed polynomial');delta=.25-.5j;angle=.3;target=Frame((delta.real,delta.imag),2.,angle);changed=source.in_frame(target)
        expected=np.array([1+2*delta+3*delta**2,2*(2+6*delta),12])*np.exp(1j*np.arange(1,4)*angle)
        np.testing.assert_allclose(np.array(changed.normal_t)+1j*np.array(changed.skew_t),expected,rtol=1e-13,atol=1e-13)
        self.assertLess(relative(expected,fourier_reference(source,target)),1e-12)
        quarter=Series(Frame((0.,0.),1.,0.),(0.,2.),(0.,0.),'synthetic normal quadrupole').in_frame(Frame((0.,0.),1.,np.pi/2))
        np.testing.assert_allclose(quarter.normal_t,(0.,-2.),rtol=1e-14,atol=1e-14)

    def test_transform_composition_inverse_and_zero_preserve_physical_fields_and_provenance(self):
        source=Series(Frame((.5,-.25),.2,.4),(1.,2.,-.5,.03),(.2,0.,.4,-.01),'synthetic combined field');target=Frame((.51,-.23),.15,-.3);second=Frame((.47,-.27),.1,.2);points=[[.51,-.2],[.45,-.28],[.5,-.25]]
        for changed in (source.in_frame(target),source.in_frame(target).in_frame(second),source.in_frame(second)):
            np.testing.assert_allclose(changed.evaluate(points),source.evaluate(points),rtol=1e-12,atol=1e-12);self.assertEqual(changed.provenance,source.provenance)
            back=changed.in_frame(source.frame);np.testing.assert_allclose(back.normal_t,source.normal_t,rtol=1e-12,atol=1e-12);np.testing.assert_allclose(back.skew_t,source.skew_t,rtol=1e-12,atol=1e-12)
        zero=Series(source.frame,(0.,)*4,(0.,)*4,'explicit zero field');np.testing.assert_array_equal(zero.in_frame(target).evaluate(points),0.)

    def test_strict_SI_schema_and_immutable_coefficient_input(self):
        normal=[1.,2.];s=Series(Frame((0.,0.),.1,0.),normal,[0.,0.],'synthetic');normal[0]=9.;self.assertEqual(s.normal_t[0],1.);self.assertEqual(Series.from_dict(s.to_dict()).to_dict(),s.to_dict())
        for change in (lambda d:d.update(schema_version=True),lambda d:d.update(coefficient_unit='relative_1e-4'),lambda d:d.update(interpretation='exact solved field'),lambda d:d.update(unknown=1),lambda d:d.update(provenance=''),lambda d:d['normal_t'].__setitem__(0,True),lambda d:d['skew_t'].__setitem__(0,1+0j),lambda d:d['frame'].update(reference_radius_m=0.),lambda d:d['frame'].update(rotation_rad=True)):
            raw=copy.deepcopy(s.to_dict());change(raw)
            with self.assertRaises(ValueError):Series.from_dict(raw)
        for n in (0,33):
            with self.assertRaises(ValueError):Series(s.frame,[0.]*n,[0.]*n,'synthetic')
        for points in ([[True,0.]],[[1+0j,0.]],[[float('inf'),0.]],[],[0.,0.]):
            with self.assertRaises(ValueError):s.evaluate(points)

    def test_extreme_radius_scale_invariant_and_unresolved_arithmetic_rejection(self):
        for radius in (1e-300,1e-320,5e-324,1e300):
            s=Series(Frame((0.,0.),radius,0.),(0.,1.),(0.,0.),'synthetic unit quadrupole at its reference radius')
            np.testing.assert_allclose(s.evaluate([[radius,0.]]),[[0.,1.]],rtol=1e-14,atol=0.)
        with self.assertRaises(ValueError):Frame((1e300,0.),1e-10,0.)
        huge=Series(Frame((0.,0.),1.,0.),(0.,1e308),(0.,0.),'overflow invariant')
        with self.assertRaises(ValueError):huge.evaluate([[2.,0.]])
        tiny=Series(Frame((0.,0.),1.,0.),(0.,1e-300),(0.,0.),'underflow invariant')
        with self.assertRaises(ValueError):tiny.evaluate([[1e-100,0.]])
        with self.assertRaises(ValueError):huge.in_frame(Frame((0.,0.),1e308,0.))
        angle=Series(Frame((0.,0.),1.,-1e308),(1.,),(0.,),'angle arithmetic')
        with self.assertRaises(ValueError):angle.in_frame(Frame((0.,0.),1.,1e308))
