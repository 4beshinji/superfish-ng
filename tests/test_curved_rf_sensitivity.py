# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import unittest
import numpy as np
from superfish_ng import solve
from superfish_ng.constants import C0,EPS0,TAU
from superfish_ng.curved_rf import accelerating_voltage_curved,quantities_curved
from test_curved_reflection import half_case


class CurvedRFSensitivityTests(unittest.TestCase):
    def solution(self,tag='electric_symmetry'):
        case=replace(half_case('z_min',tag),beta=.37,voltage_interval_m=(.013,.078),phase_origin_m=.019)
        return solve(case)

    def test_constant_axis_voltage_and_linear_superposition(self):
        from superfish_ng.curved_rf_sensitivity import voltage_covector
        s=self.solution();c=voltage_covector(s);omega=TAU*s.frequencies_hz[0];k=omega/(s.case.beta*C0)
        _,(a,b),origin=s.case.acceleration_parameters
        exact=2/(omega*EPS0)*np.exp(1j*k*(a-origin))*np.expm1(1j*k*(b-a))/(1j*k)
        self.assertLess(abs(c.sum()-exact)/abs(exact),2e-13)
        rng=np.random.default_rng(932)
        u=rng.normal(size=s.u.shape);v=rng.normal(size=s.u.shape)
        mixed=replace(s,u=2*u-3*v)
        self.assertLess(abs(c@mixed.u[:,0]-accelerating_voltage_curved(mixed)[0]),1e-12)
        outside=np.setdiff1d(np.arange(len(c)),s.space.axis_dofs)
        self.assertTrue(np.all(c[outside]==0))
        self.assertFalse(c.flags.writeable)

    def test_fixed_frequency_gradient_matches_independent_finite_differences(self):
        from superfish_ng.curved_rf_sensitivity import r_over_q_gradient
        s=self.solution('magnetic_symmetry');rng=np.random.default_rng(41)
        delta=rng.normal(size=s.u.shape);delta[s.space.constrained_dofs]=0
        delta*=np.linalg.norm(s.u)/np.linalg.norm(delta)
        # Test off the eigenvector as well: electric and magnetic energies must
        # both remain in the denominator rather than imposing equipartition.
        s=replace(s,u=s.u+.03*delta);g=r_over_q_gradient(s)
        direction=rng.normal(size=s.u.shape);direction[s.space.constrained_dofs]=0
        direction*=np.linalg.norm(s.u)/np.linalg.norm(direction)
        h=1e-6
        plus=quantities_curved(replace(s,u=s.u+h*direction),include_surface_peaks=False)
        minus=quantities_curved(replace(s,u=s.u-h*direction),include_surface_peaks=False)
        for key,gradient in [('r_over_q_accelerator_ohm',g.accelerator_gradient),('r_over_q_circuit_ohm',g.circuit_gradient)]:
            numerical=(plus[key]-minus[key])/(2*h);actual=gradient@direction[:,0]
            self.assertLess(abs(actual-numerical)/max(abs(actual),abs(numerical)),2e-7)
        self.assertTrue(np.all(g.accelerator_gradient[s.space.constrained_dofs]==0))
        self.assertLess(abs(g.accelerator_gradient@s.u[:,0]),1e-11)
        np.testing.assert_array_equal(g.circuit_gradient,g.accelerator_gradient/2)

    def test_phase_origin_and_amplitude_invariants_and_strict_mode(self):
        from superfish_ng.curved_rf_sensitivity import r_over_q_gradient,voltage_covector
        s=self.solution();g=r_over_q_gradient(s)
        phase=r_over_q_gradient(replace(s,case=replace(s.case,phase_origin_m=.057)))
        scaled=r_over_q_gradient(replace(s,u=-3*s.u))
        np.testing.assert_allclose(phase.accelerator_gradient,g.accelerator_gradient,rtol=2e-12,atol=1e-15)
        np.testing.assert_allclose(scaled.accelerator_gradient,g.accelerator_gradient/(-3),rtol=2e-12,atol=1e-15)
        for mode in (True,-1,1):
            with self.assertRaises(ValueError):voltage_covector(s,mode)

    def test_maxwell_length_scaling_of_covector_and_gradient(self):
        from superfish_ng import Case
        from superfish_ng.curved_rf_sensitivity import voltage_covector,r_over_q_gradient
        a=self.solution();raw=a.case.to_dict()
        for curve in raw['geometry']['curves']:
            for key in ('start_zr_m','end_zr_m','center_zr_m','semiaxes_m'):
                if key in curve:curve[key]=[2*x for x in curve[key]]
        for key in ('chord_tolerance_m','join_tolerance_m','minimum_gap_m'):
            if key in raw['geometry']:raw['geometry'][key]*=2
        raw['mesh']['contour_mesh']['max_edge_m']*=2
        raw['rf']['normalization_j']*=4
        raw['rf']['voltage_interval_m']=[2*x for x in raw['rf']['voltage_interval_m']]
        raw['rf']['phase_origin_m']*=2
        b=solve(Case.from_dict(raw))
        np.testing.assert_array_equal(a.space.geometry.cell_nodes,b.space.geometry.cell_nodes)
        np.testing.assert_allclose(voltage_covector(b),4*voltage_covector(a),rtol=2e-11,atol=1e-14)
        ga,gb=r_over_q_gradient(a),r_over_q_gradient(b)
        np.testing.assert_allclose(gb.accelerator_gradient,2**1.5*ga.accelerator_gradient,rtol=2e-10,atol=1e-14)
