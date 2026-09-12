# SPDX-License-Identifier: Apache-2.0
"""Independent invariants for the positive-radius q=r Hphi formulation."""
from dataclasses import replace
import unittest
import numpy as np
from superfish_ng.constants import C0, MU0, EPS0, TAU
from superfish_ng.coaxial import CoaxialCase, coaxial_matrices, solve_coaxial, coaxial_quantities


class CoaxialTests(unittest.TestCase):
    def test_constant_nullspace_and_polynomial_weighted_forms(self):
        for order in (1, 2):
            case = CoaxialCase(.025, .1, .18, nr=4, nz=5, element_order=order)
            space, k, m, diagnostic = coaxial_matrices(case)
            r, z = space.dof_points.T
            functions = [(np.ones(len(r)), lambda r,z: (np.ones_like(r),0*r,0*r)),
                         (r, lambda r,z: (r,np.ones_like(r),0*r)),
                         (z, lambda r,z: (z,0*r,np.ones_like(r)))]
            if order == 2:
                functions += [(r*r, lambda r,z: (r*r,2*r,0*r)),
                              (r*z, lambda r,z: (r*z,z,r)),
                              (z*z, lambda r,z: (z*z,0*r,2*z))]
            x,w=np.polynomial.legendre.leggauss(64)
            rr,zz=np.meshgrid(.025+(x+1)*.075/2,(x+1)*.18/2)
            weights=np.outer(w,w)*.075*.18/4/rr
            c=np.column_stack([f[0] for f in functions])
            evaluated=[f[1](rr,zz) for f in functions]
            expected_m=np.array([[np.sum(weights*a[0]*b[0]) for b in evaluated] for a in evaluated])
            expected_k=np.array([[np.sum(weights*(a[1]*b[1]+a[2]*b[2])) for b in evaluated] for a in evaluated])
            np.testing.assert_allclose(c.T@(m@c),expected_m,rtol=1e-10,atol=1e-15)
            np.testing.assert_allclose(c.T@(k@c),expected_k,rtol=1e-10,atol=2e-12)
            self.assertLess(np.linalg.norm(k@np.ones(len(r)))/np.linalg.norm(k.data),1e-13)
            self.assertAlmostEqual(np.ones(len(r))@(m@np.ones(len(r))),.18*np.log(4),places=12)

    def test_strict_schema_and_unresolved_radial_integration(self):
        case=CoaxialCase(.025,.1,.18)
        self.assertEqual(CoaxialCase.from_dict(case.to_dict()),case)
        for data in [dict(case.to_dict(),extra=1),dict(case.to_dict(),schema_version=True)]:
            with self.assertRaises(ValueError):CoaxialCase.from_dict(data)
        for args in [(0,.1,.2),(.1,.1,.2),(.2,.1,.2),(.01,.1,True)]:
            with self.assertRaises(ValueError):CoaxialCase(*args)
        for kwargs in [dict(nr=True),dict(element_order=3),dict(quadrature_order=2),dict(nr=100000,nz=100000)]:
            with self.assertRaises(ValueError):CoaxialCase(.025,.1,.18,**kwargs)
        with self.assertRaisesRegex(ValueError,'quadrature.*refine'):
            coaxial_matrices(CoaxialCase(1e-5,.1,.18,nr=2,nz=2,quadrature_order=4))

    def test_polynomial_fields_obey_cylindrical_ampere_sign_and_probe_limits(self):
        for order in (1,2):
            solution=solve_coaxial(CoaxialCase(.025,.1,.18,nr=4,nz=5,element_order=order,modes=1))
            r,z=solution.space.dof_points.T
            q=r+2*z if order==1 else r*z
            polynomial=replace(solution,coefficients=q[:,None])
            points=np.array([[.025,0],[.041,.073],[.1,.18]])
            field=polynomial.fields_at(points);r,z=points.T;omega=TAU*solution.frequencies_hz[0]
            value=r+2*z if order==1 else r*z
            dr=np.ones_like(r) if order==1 else z
            dz=2*np.ones_like(r) if order==1 else r
            np.testing.assert_allclose(field['Hphi_real_A_per_m'],value/r,rtol=1e-13)
            np.testing.assert_allclose(field['Er_quadrature_V_per_m'],dz/(omega*EPS0*r),rtol=1e-13)
            np.testing.assert_allclose(field['Ez_quadrature_V_per_m'],-dr/(omega*EPS0*r),rtol=1e-13,atol=1e-12)
            for invalid in ([[0.,0.]],[[True,0.]],[[.03,float('nan')]],[[.03,'0.1']],[[10**1000,0.]]):
                with self.assertRaises(ValueError):polynomial.fields_at(invalid)
            for mode in (True,-1,1):
                with self.assertRaises(ValueError):polynomial.fields_at(points,mode)
            for invalid in ([[True,0.,0.]],[[.5,.5,-.1]],[[float('inf'),0.,0.]],[[1.,'0',0.]]):
                with self.assertRaises(ValueError):polynomial.fields_in_cells([0],invalid)

    def test_tem_modes_fields_end_walls_and_scaling(self):
        case=CoaxialCase(.025,.05,.18,nr=6,nz=24,element_order=2,modes=2)
        solution=solve_coaxial(case)
        np.testing.assert_allclose(solution.frequencies_hz,C0/(2*.18)*np.arange(1,3),rtol=5e-5)
        r,z=np.meshgrid(np.linspace(.026,.049,13),np.linspace(.003,.177,19))
        for mode in range(2):
            p=mode+1;omega=TAU*C0*p/(2*.18)
            amplitude=np.sqrt(2/(MU0*np.pi*.18*np.log(2)))
            h=amplitude*np.cos(p*np.pi*z/.18)/r
            e=-amplitude*np.sqrt(MU0/EPS0)*np.sin(p*np.pi*z/.18)/r
            field=solution.fields_at(np.column_stack((r.ravel(),z.ravel())),mode)
            sign=np.sign(np.dot(field['Hphi_real_A_per_m'],h.ravel()))
            for name,expected in [('Hphi_real_A_per_m',h),('Er_quadrature_V_per_m',e)]:
                self.assertLess(np.linalg.norm(sign*field[name]-expected.ravel())/np.linalg.norm(expected),.003)
            self.assertLess(np.linalg.norm(field['Ez_quadrature_V_per_m'])/np.linalg.norm(e),.003)
            q=coaxial_quantities(solution,mode)
            walls=amplitude**2*np.pi*np.array([.18/.025,.18/.05,2*np.log(2),2*np.log(2)])
            np.testing.assert_allclose(list(q['wall_h2_integral_a2_by_surface'].values()),walls,rtol=.003)
            self.assertLess(abs(q['geometry_factor_ohm']/(2*omega/walls.sum())-1),.003)
            self.assertIsNone(q['r_over_q_accelerator_ohm']);self.assertIsNone(q['r_over_q_circuit_ohm'])
            self.assertAlmostEqual(q['stored_energy_j'],1.,places=8)
            self.assertAlmostEqual(q['electric_energy_j'],q['magnetic_energy_j'],places=8)
        scaled=solve_coaxial(replace(case,inner_radius_m=.05,outer_radius_m=.1,length_m=.36,normalization_j=4))
        np.testing.assert_allclose(scaled.frequencies_hz,solution.frequencies_hz/2,rtol=1e-10)
        a,b=coaxial_quantities(solution),coaxial_quantities(scaled)
        self.assertAlmostEqual(b['geometry_factor_ohm']/a['geometry_factor_ohm'],1.,places=9)
        self.assertAlmostEqual(b['q0']/a['q0'],np.sqrt(2),places=9)
        self.assertAlmostEqual(b['wall_loss_w']/a['wall_loss_w'],np.sqrt(2),places=9)


if __name__=='__main__':unittest.main()
