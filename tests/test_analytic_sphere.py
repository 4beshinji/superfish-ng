# SPDX-License-Identifier: Apache-2.0
import math
import unittest
import numpy as np
from superfish_ng.analytic_sphere import SphereTM
from superfish_ng.constants import EPS0,MU0,TAU


class SphereReferenceTests(unittest.TestCase):
    def test_boundary_center_and_independent_energy_integrals(self):
        s = SphereTM(.08)
        x = s.root
        self.assertLess(abs((x*x-1)*math.sin(x)+x*math.cos(x)),1e-13)
        theta = np.linspace(0,math.pi,51)
        fields = s.fields(np.column_stack((s.radius_m*np.sin(theta),s.radius_m*(1+np.cos(theta)))))
        tangent = fields['Er_quadrature_V_per_m']*np.cos(theta)-fields['Ez_quadrature_V_per_m']*np.sin(theta)
        self.assertLess(np.max(abs(tangent)),1e-7)
        q,w = np.polynomial.legendre.leggauss(32)
        radial = s.radius_m*(q+1)/2
        cosine = q
        r = radial[:,None]*np.sqrt(1-cosine**2)
        z = s.radius_m+radial[:,None]*cosine
        fields = s.fields(np.column_stack((r.ravel(),z.ravel())))
        weights = (2*math.pi*radial[:,None]**2*s.radius_m/2*w[:,None]*w).ravel()
        magnetic = MU0/4*np.dot(weights,fields['Hphi_A_per_m']**2)
        electric = EPS0/4*np.dot(weights,fields['Er_quadrature_V_per_m']**2+fields['Ez_quadrature_V_per_m']**2)
        self.assertAlmostEqual(magnetic,.5,places=12)
        self.assertAlmostEqual(electric,.5,places=12)
        center = s.fields([[0,s.radius_m]])
        self.assertEqual(center['Hphi_A_per_m'][0],0)
        self.assertTrue(np.isfinite(center['Ez_quadrature_V_per_m'][0]))

    def test_local_maxwell_curl_by_finite_differences(self):
        s = SphereTM(.08)
        points = np.array([[.01,.04],[.03,.08],[.04,.10],[.015,.12]])
        step = s.radius_m*1e-5
        derivatives = []
        for axis,key in ((1,'Er_quadrature_V_per_m'),(0,'Ez_quadrature_V_per_m')):
            shift = np.zeros_like(points)
            shift[:,axis] = step
            derivatives.append((s.fields(points+shift)[key]-s.fields(points-shift)[key])/(2*step))
        curl = derivatives[0]-derivatives[1]
        reference = TAU*s.frequency_hz*MU0*s.fields(points)['Hphi_A_per_m']
        np.testing.assert_allclose(curl,reference,rtol=1e-8)

    def test_scale_energy_and_transit_conventions(self):
        a,b = SphereTM(.08),SphereTM(.24,normalization_j=4)
        qa,qb = a.quantities(),b.quantities()
        self.assertAlmostEqual(qa['frequency_hz']/qb['frequency_hz'],3)
        for key in ('r_over_q_accelerator_ohm','geometry_factor_ohm','transit_time_factor_abs'):
            self.assertAlmostEqual(qa[key]/qb[key],1)
        self.assertEqual(qa['r_over_q_accelerator_ohm'],2*qa['r_over_q_circuit_ohm'])
        # Symmetric axis profile gives a voltage phase exp(i*k*R/beta), including its sign.
        for beta in (1.,.5,.1):
            s = SphereTM(.08,beta=beta)
            q = s.quantities()
            v = complex(q['voltage_real_v'],q['voltage_imag_v'])
            phase = s.root/beta
            centered = v*complex(math.cos(phase),-math.sin(phase))
            self.assertLess(abs(centered.imag),1e-8)

    def test_invalid_parameters_and_outside_points(self):
        for v in (True,0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):
                SphereTM(v)
        with self.assertRaises(ValueError):
            SphereTM(.08,beta=1.1)
        for points in ([[0,-.001]],[[-.01,.08]],[[.09,.08]],[[0,float('nan')]],[],[['0','.08']]):
            with self.assertRaises(ValueError):
                SphereTM(.08).fields(points)
