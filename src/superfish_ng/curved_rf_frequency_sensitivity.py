# SPDX-License-Identifier: Apache-2.0
"""Angular-frequency partial derivatives at fixed real coefficients and geometry."""
from dataclasses import dataclass
import math
import numpy as np
from scipy.special import spherical_jn
from .constants import C0,EPS0,MU0,TAU
from .curved_rf_sensitivity import _omega,r_over_q_gradient


def _axis_phase_moment(solution,mode,omega):
    """Integrate (z-origin) u(z) exp(i*k*(z-origin)) using cubic moments.

    The caller first validates the straight affine axis through the existing
    voltage covector. Only the phase-weighted moment is new here.
    """
    geometry=solution.space.geometry
    nodes=geometry.boundary_nodes[solution.space.boundary_tags=='axis']
    ends=geometry.points_rz_m[nodes[:,:2],1]
    values=solution.u[nodes,mode]
    _,(a,b),origin=solution.case.acceleration_parameters
    k=omega/(solution.case.beta*C0);total=0j
    for (left,right),(fleft,fright,fmid) in zip(ends,values):
        if left>right:left,right,fleft,fright=right,left,fright,fleft
        lo,hi=max(a,left),min(b,right)
        if lo>=hi:continue
        center,half=(left+right)/2,(right-left)/2
        nc,nh=(lo+hi)/2,(hi-lo)/2
        shift,scale=(nc-center)/half,nh/half
        A,B,C=fmid,(fright-fleft)/2,(fleft+fright)/2-fmid
        coeff=np.array([A+B*shift+C*shift**2,scale*(B+2*C*shift),C*scale**2])
        weighted=np.convolve(coeff,[nc-origin,nh])
        j0,j1,j2,j3=spherical_jn(np.arange(4),k*nh)
        # x^3=(3 P1 + 2 P3)/5; integral Pn exp(i*t*x)=2 i^n jn(t).
        moments=np.array([2*j0,2j*j1,2*(j0-2*j2)/3,2j*(3*j1-2*j3)/5])
        total+=nh*np.exp(1j*k*(nc-origin))*np.dot(weighted,moments)
    return complex(total)


@dataclass(frozen=True)
class RQFrequencyDerivative:
    angular_frequency_rad_s: float
    voltage_derivative_v_per_rad_s: complex
    accelerator_derivative_ohm_per_rad_s: float
    circuit_derivative_ohm_per_rad_s: float
    scope: str = ('partial derivative with respect to angular frequency omega at fixed real u, '
                  'K, M, geometry, beta, interval and phase origin; not a total shape derivative')


def r_over_q_frequency_derivative(solution,mode=0):
    """Include voltage phase, 1/omega electric field, and both stored energies.

    To obtain a derivative per Hz, multiply by 2*pi. The eigenvalue and field
    coefficients are held fixed here; no eigenpair is recomputed.
    """
    omega=_omega(solution,mode);g=r_over_q_gradient(solution,mode)
    moment=_axis_phase_moment(solution,mode,omega)
    derivative=-g.voltage_v/omega+2j*moment/(omega*EPS0*solution.case.beta*C0)
    u=solution.u[:,mode]
    magnetic=float(MU0*TAU/4*(u@(solution.mass@u)))
    electric=float(TAU/(4*omega**2*EPS0)*(u@(solution.stiffness@u)))
    energy=magnetic+electric;q=g.r_over_q_accelerator_ohm
    dq=float(2*np.real(np.conj(g.voltage_v)*derivative)/(omega*energy)-q/omega+2*q*electric/(omega*energy))
    if not np.isfinite(derivative) or not math.isfinite(dq):raise ValueError('RF frequency derivative is not finite')
    return RQFrequencyDerivative(omega,derivative,dq,dq/2)
