# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import unittest
import numpy as np
from superfish_ng.axis_connected_mesh import AxisConnectedMesh
from superfish_ng.axis_hphi import AxisHphiCase, AxisAccelerationPath, solve_axis_hphi, axis_hphi_quantities
from superfish_ng.config import Case
from superfish_ng.constants import EPS0, TAU
from superfish_ng.mesh import make_mesh
from superfish_ng.solver import solve
from superfish_ng.rf import quantities, cell_fields
import test_axis_connected_mesh as geometry_tests


def rectangular_case(order=2):
    old=Case(((0.,.1),(.18,.1)),nr=8,nz=12,modes=4,element_order=order)
    original=make_mesh(old)
    declared=AxisConnectedMesh([[0.,0.],[.1,0.],[.1,.18],[0.,.18]],[],original.points,original.triangles)
    return old,AxisHphiCase(declared,element_order=order,modes=4,
        acceleration=AxisAccelerationPath(0.,.18,1.,0.))


class AxisHphiTests(unittest.TestCase):
    def test_canonical_spectrum_normalization_rf_and_axis_retained(self):
        for order in (1,2):
            canonical,case=rectangular_case(order);old=solve(canonical);new=solve_axis_hphi(case)
            np.testing.assert_allclose(new.frequencies_hz,old.frequencies_hz,rtol=2e-12)
            np.testing.assert_allclose(new.stiffness.toarray(),old.stiffness.toarray(),rtol=0,atol=0)
            np.testing.assert_allclose(new.mass.toarray(),old.mass.toarray(),rtol=0,atol=0)
            np.testing.assert_allclose(abs(new.coefficients),abs(old.u),rtol=1e-8,atol=1e-6)
            self.assertGreater(np.linalg.norm(new.coefficients[new.space.axis_dofs,0]),0.)
            for mode in range(case.modes):
                old_er,old_ez,old_h=cell_fields(old,mode)
                cells=np.arange(len(new.space.mesh.triangles))
                fields=new.fields_in_cells(cells,np.full((len(cells),3),1/3),mode)
                sign=np.sign(np.dot(old_h,fields['Hphi_real_A_per_m']))
                # Canonical cell_fields documents Ephasor=-i*Eamplitude;
                # the new explicit phasor stores real+i*quadrature.
                for key,values in (('Hphi_real_A_per_m',old_h),('Er_quadrature_V_per_m',-old_er),('Ez_quadrature_V_per_m',-old_ez)):
                    np.testing.assert_allclose(sign*fields[key],values,rtol=1e-8,atol=1e-6)
                actual=axis_hphi_quantities(new,mode);expected=quantities(canonical,old,mode)
                for key in ('frequency_hz','stored_energy_j','wall_loss_w','q0','geometry_factor_ohm','r_over_q_accelerator_ohm','r_over_q_circuit_ohm'):
                    self.assertAlmostEqual(actual[key]/expected[key],1.,delta=1e-8,msg=key)
                self.assertAlmostEqual(actual['electric_energy_j'],.5,delta=1e-9)
                self.assertAlmostEqual(actual['magnetic_energy_j'],.5,delta=1e-9)
                self.assertEqual(actual['wall_h2_integral_a2_by_segment'][-1],0.)

    def test_regular_polynomials_phase_and_clipped_complex_axis_integral(self):
        for order in (1,2):
            _,case=rectangular_case(order);solution=solve_axis_hphi(replace(case,modes=1,
                acceleration=AxisAccelerationPath(.011,.137,.63,.019)))
            r,z=solution.space.dof_points.T
            values=1+2*r+3*z if order==1 else 1+r*z+2*z*z
            polynomial=replace(solution,coefficients=values[:,None])
            points=np.array([[0.,0.],[0.,.073],[.039,.072],[.1,.18]])
            r,z=points.T;u=1+2*r+3*z if order==1 else 1+r*z+2*z*z
            ur=2*np.ones_like(r) if order==1 else z;uz=3*np.ones_like(r) if order==1 else r+4*z
            fields=polynomial.fields_at(points);omega=TAU*solution.frequencies_hz[0]
            np.testing.assert_allclose(fields['Hphi_real_A_per_m'],r*u,rtol=1e-13,atol=1e-14)
            np.testing.assert_allclose(fields['Er_quadrature_V_per_m'],r*uz/(omega*EPS0),rtol=1e-13,atol=1e-12)
            np.testing.assert_allclose(fields['Ez_quadrature_V_per_m'],-(2*u+r*ur)/(omega*EPS0),rtol=1e-13)
            x,w=np.polynomial.legendre.leggauss(96);a,b=.011,.137;z=a+(x+1)*(b-a)/2
            u=1+3*z if order==1 else 1+2*z*z
            expected=-2j/(omega*EPS0)*(b-a)/2*np.dot(w,u*np.exp(1j*omega*(z-.019)/(.63*299792458.)))
            result=axis_hphi_quantities(polynomial);v=result['vacc_v']
            self.assertLess(abs(complex(v['real'],v['imag'])/expected-1),1e-12)
            self.assertAlmostEqual(result['r_over_q_accelerator_ohm'],2*result['r_over_q_circuit_ohm'])

    def test_holes_reject_probes_and_require_explicit_acceleration(self):
        mesh=AxisConnectedMesh(**geometry_tests.AxisConnectedMeshTests().data(2))
        for order in (1,2):
            case=AxisHphiCase(mesh,element_order=order,modes=2);solution=solve_axis_hphi(case)
            result=axis_hphi_quantities(solution)
            for key in ('vacc_v','eacc_v_per_m','r_over_q_accelerator_ohm','r_over_q_circuit_ohm'):
                self.assertIsNone(result[key])
            for hole in mesh.holes_rz_m:
                with self.assertRaises(ValueError):solution.fields_at([np.mean(hole,axis=0)])
            for invalid in ([[True,0]],[[0.,'0.1']],[[-1e-12,0.]],[[0.,float('nan')]]):
                with self.assertRaises(ValueError):solution.fields_at(invalid)
            self.assertEqual(len(result['wall_h2_integral_a2_by_component']),3)
            self.assertTrue(all(value>0 for value in result['wall_h2_integral_a2_by_component']))

    def test_strict_physics_path_and_schema(self):
        _,case=rectangular_case();doc=case.to_dict()
        self.assertEqual(AxisHphiCase.from_dict(doc).to_dict(),doc)
        for key,value in (('extra',1),('schema_version',True),('format','superfish_ng_hphi_mesh_case')):
            with self.assertRaises(ValueError):AxisHphiCase.from_dict(dict(doc,**{key:value}))
        for args in ((0.,.18,True,0.),(0.,.18,1.1,0.),(.18,0.,1.,0.),(0.,.18,1.,float('nan'))):
            with self.assertRaises(ValueError):AxisAccelerationPath(*args)
        with self.assertRaises(ValueError):replace(case,acceleration=AxisAccelerationPath(-.01,.18,1.,0.))
        with self.assertRaises(ValueError):replace(case,acceleration={})
        with self.assertRaises(ValueError):replace(case,element_order=True)
        bad=dict(doc);bad['fem']=dict(doc['fem'],quadrature_order=8)
        with self.assertRaises(ValueError):AxisHphiCase.from_dict(bad)


if __name__=='__main__':unittest.main()
