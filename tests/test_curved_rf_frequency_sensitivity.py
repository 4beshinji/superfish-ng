# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import unittest
import numpy as np
from superfish_ng import solve
from superfish_ng.constants import C0,EPS0,TAU
from superfish_ng.curved_rf import quantities_curved
from test_curved_reflection import half_case


class CurvedRFFrequencySensitivityTests(unittest.TestCase):
    def solution(self):
        return solve(replace(half_case('z_min','electric_symmetry'),beta=.37,
                             voltage_interval_m=(.013,.078),phase_origin_m=.019))

    def test_constant_axis_closed_form_and_zero_voltage(self):
        from superfish_ng.curved_rf_frequency_sensitivity import r_over_q_frequency_derivative
        s=self.solution();s=replace(s,u=np.ones_like(s.u));r=r_over_q_frequency_derivative(s)
        w=TAU*s.frequencies_hz[0];speed=s.case.beta*C0
        _,(a,b),origin=s.case.acceleration_parameters
        ea,eb=np.exp(1j*w*np.array([a-origin,b-origin])/speed)
        difference=eb-ea;derivative=1j*((b-origin)*eb-(a-origin)*ea)/speed
        expected=2*speed/(1j*EPS0)*(derivative/w**2-2*difference/w**3)
        self.assertLess(abs(r.voltage_derivative_v_per_rad_s-expected)/abs(expected),2e-13)
        # A nonzero off-axis field has zero axial voltage and zero first R/Q derivative.
        u=s.u.copy();u[s.space.axis_dofs]=0
        zero=r_over_q_frequency_derivative(replace(s,u=u))
        self.assertEqual(zero.accelerator_derivative_ohm_per_rad_s,0.)

    def test_off_eigenvector_frequency_difference_and_phase_amplitude_invariance(self):
        from superfish_ng.curved_rf_frequency_sensitivity import r_over_q_frequency_derivative
        s=self.solution();rng=np.random.default_rng(522)
        u=s.u*(1+.04*rng.normal(size=s.u.shape));s=replace(s,u=u)
        r=r_over_q_frequency_derivative(s);w=TAU*s.frequencies_hz[0];h=1e-6
        plus=quantities_curved(replace(s,frequencies_hz=s.frequencies_hz*(1+h)),include_surface_peaks=False)
        minus=quantities_curved(replace(s,frequencies_hz=s.frequencies_hz*(1-h)),include_surface_peaks=False)
        for key,d in [('r_over_q_accelerator_ohm',r.accelerator_derivative_ohm_per_rad_s),('r_over_q_circuit_ohm',r.circuit_derivative_ohm_per_rad_s)]:
            numerical=(plus[key]-minus[key])/(2*h*w)
            self.assertLess(abs(d-numerical)/max(abs(d),abs(numerical)),2e-7)
        for altered in (replace(s,u=-3*s.u),replace(s,case=replace(s.case,phase_origin_m=.057))):
            other=r_over_q_frequency_derivative(altered)
            self.assertAlmostEqual(other.accelerator_derivative_ohm_per_rad_s/r.accelerator_derivative_ohm_per_rad_s,1.,places=11)
        self.assertEqual(r.circuit_derivative_ohm_per_rad_s,r.accelerator_derivative_ohm_per_rad_s/2)
        for mode in (True,-1,1):
            with self.assertRaises(ValueError):r_over_q_frequency_derivative(s,mode)

    def test_combined_adjoint_and_frequency_mode_perturbation(self):
        from scipy.linalg import eigh
        from superfish_ng.curved_rf_adjoint import r_over_q_adjoint
        from superfish_ng.curved_rf_frequency_sensitivity import r_over_q_frequency_derivative
        s=self.solution();z=r_over_q_adjoint(s).accelerator_adjoint
        dw=r_over_q_frequency_derivative(s).accelerator_derivative_ohm_per_rad_s
        free=np.setdiff1d(np.arange(len(s.u)),s.space.constrained_dofs)
        k=s.stiffness[free][:,free].toarray();m=s.mass[free][:,free].toarray();u=s.u[free,0]
        p=np.random.default_rng(194).normal(size=len(free));p/=np.linalg.norm(p)
        p=np.linalg.cholesky(m)@p
        perturbation=s.eigenvalues[0]*(m+np.outer(p,p))
        eigenvalue_derivative=(u@perturbation@u)/(u@m@u)
        frequency_part=dw*C0/(2*np.sqrt(s.eigenvalues[0]))*eigenvalue_derivative
        coefficient_part=-z[free]@perturbation@u
        predicted=coefficient_part+frequency_part
        amplitude=np.sqrt(u@m@u);h=1e-7;qs=[]
        for sign in (1,-1):
            values,v=eigh(k+sign*h*perturbation,m,subset_by_index=(0,0))
            changed=s.u.copy();changed[free,0]=amplitude*v[:,0]
            qs.append(quantities_curved(replace(s,u=changed,frequencies_hz=C0*np.sqrt(values)/TAU),
                                       include_surface_peaks=False)['r_over_q_accelerator_ohm'])
        numerical=(qs[0]-qs[1])/(2*h)
        self.assertLess(abs(numerical-predicted)/max(abs(numerical),abs(predicted)),2e-6)
        # This fixture must actually distinguish the combined derivative from
        # the earlier coefficient-only adjoint.
        self.assertGreater(abs(frequency_part)/max(abs(predicted),abs(coefficient_part)),.01)
