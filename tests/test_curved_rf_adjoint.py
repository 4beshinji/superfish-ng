# SPDX-License-Identifier: Apache-2.0
from dataclasses import replace
import unittest
import numpy as np
from scipy.linalg import eigh
from superfish_ng import solve
from superfish_ng.curved_rf import quantities_curved
from superfish_ng.curved_rf_sensitivity import r_over_q_gradient
from test_curved_reflection import half_case


class CurvedRFAdjointTests(unittest.TestCase):
    def solution(self):
        return solve(replace(half_case('z_min','magnetic_symmetry'),modes=3,beta=.37,
                             voltage_interval_m=(.013,.078),phase_origin_m=.019))

    def test_independent_complete_spectral_expansion(self):
        from superfish_ng.curved_rf_adjoint import r_over_q_adjoint
        s=self.solution();result=r_over_q_adjoint(s)
        free=np.setdiff1d(np.arange(len(s.u)),s.space.constrained_dofs)
        k=s.stiffness[free][:,free].toarray();m=s.mass[free][:,free].toarray()
        values,vectors=eigh(k,m)
        for mode in range(3):
            result=r_over_q_adjoint(s,mode)
            g=r_over_q_gradient(s,mode).accelerator_gradient[free]
            keep=np.arange(len(values))!=mode
            expected=vectors[:,keep]@((vectors[:,keep].T@g)/(values[keep]-values[mode]))
            np.testing.assert_allclose(result.accelerator_adjoint[free],expected,rtol=2e-8,atol=1e-10)
        self.assertLess(result.relative_residual,1e-10)
        self.assertLess(result.relative_gauge_error,1e-12)
        self.assertTrue(np.all(result.accelerator_adjoint[s.space.constrained_dofs]==0))
        np.testing.assert_array_equal(result.circuit_adjoint,result.accelerator_adjoint/2)
        self.assertFalse(result.accelerator_adjoint.flags.writeable)

    def test_matrix_perturbation_mode_response_at_fixed_rf_frequency(self):
        from superfish_ng.curved_rf_adjoint import r_over_q_adjoint
        s=self.solution();result=r_over_q_adjoint(s)
        free=np.setdiff1d(np.arange(len(s.u)),s.space.constrained_dofs)
        k=s.stiffness[free][:,free].toarray();m=s.mass[free][:,free].toarray()
        rng=np.random.default_rng(104);p=rng.normal(size=len(free));p/=np.linalg.norm(p)
        perturbation=np.outer(p,p)*np.linalg.norm(k,2)
        amplitude=np.sqrt(s.u[free,0]@m@s.u[free,0]);h=1e-7;qs=[]
        for sign in (1,-1):
            _,v=eigh(k+sign*h*perturbation,m,subset_by_index=(0,0))
            u=s.u.copy();u[free,0]=v[:,0]*amplitude
            # Change the mode coefficients only; RF omega and physical energy
            # matrices remain fixed, as required by this adjoint's scope.
            qs.append(quantities_curved(replace(s,u=u),include_surface_peaks=False)['r_over_q_accelerator_ohm'])
        numerical=(qs[0]-qs[1])/(2*h)
        predicted=-result.accelerator_adjoint[free]@perturbation@s.u[free,0]
        self.assertLess(abs(numerical-predicted)/max(abs(numerical),abs(predicted)),2e-6)

    def test_amplitude_rule_and_invalid_eigenpair_rejection(self):
        from superfish_ng.curved_rf_adjoint import r_over_q_adjoint
        s=self.solution();a=r_over_q_adjoint(s);b=r_over_q_adjoint(replace(s,u=-3*s.u))
        np.testing.assert_allclose(b.accelerator_adjoint,a.accelerator_adjoint/(-3),rtol=2e-9,atol=1e-10)
        bad=s.u.copy();bad[:,0]+=np.random.default_rng(91).normal(size=len(bad))
        with self.assertRaisesRegex(ValueError,'eigenpair|constraint'):r_over_q_adjoint(replace(s,u=bad))
        values=s.eigenvalues.copy();values[1]=values[0]*(1+1e-9)
        with self.assertRaisesRegex(ValueError,'separation'):r_over_q_adjoint(replace(s,eigenvalues=values))
        for mode in (True,-1,3):
            with self.assertRaises(ValueError):r_over_q_adjoint(s,mode)
