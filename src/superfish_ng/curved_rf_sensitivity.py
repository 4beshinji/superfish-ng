# SPDX-License-Identifier: Apache-2.0
"""Fixed-frequency coefficient derivatives, not eigenmode or shape sensitivities."""
from dataclasses import dataclass
import math
import numpy as np
from .constants import C0,EPS0,MU0,TAU
from .curved_rf import _check
from .quadratic_rf import quadratic_voltage


def _omega(solution,mode):
    _check(solution,mode)
    omega=float(TAU*solution.frequencies_hz[mode])
    if not math.isfinite(omega) or omega<=0:
        raise ValueError('RF sensitivity requires a positive finite frequency')
    return omega


def voltage_covector(solution,mode=0):
    """Return c with V=c.T@u at fixed frequency, geometry and RF overrides.

    Coefficients u are real Hphi/r in A/m². Entries outside the axis are zero.
    The complex covector is not conjugated in its product with real u.
    """
    omega=_omega(solution,mode)
    geometry=solution.space.geometry
    nodes=geometry.boundary_nodes[solution.space.boundary_tags=='axis']
    points=geometry.points_rz_m[nodes]
    if not np.all(points[:,:,0]==0) or not np.array_equal(points[:,2,1],points[:,:2,1].mean(axis=1)):
        raise ValueError('RF sensitivity requires an exactly straight, affinely parameterized axis')
    ends=points[:,:2,1];_,interval,origin=solution.case.acceleration_parameters
    wave_number=omega/(solution.case.beta*C0)
    # Reuse the production integrator's full-axis topology and interval checks.
    quadratic_voltage(ends,np.zeros((len(ends),3)),wave_number,interval=interval,phase_origin=origin)
    result=np.zeros(len(solution.u),dtype=complex)
    basis=np.eye(3)
    for edge,indices in zip(ends,nodes):
        clipped=(max(interval[0],float(min(edge))),min(interval[1],float(max(edge))))
        if clipped[0]>=clipped[1]:continue
        for local,index in enumerate(indices):
            value,_=quadratic_voltage(edge[None,:],basis[local][None,:],wave_number,
                                      interval=clipped,phase_origin=origin)
            result[index]+=value
    result*=2/(omega*EPS0)
    if not np.isfinite(result).all():raise ValueError('voltage covector is not finite')
    result.setflags(write=False)
    return result


@dataclass(frozen=True)
class FixedFrequencyRQGradient:
    frequency_hz: float
    voltage_v: complex
    r_over_q_accelerator_ohm: float
    r_over_q_circuit_ohm: float
    accelerator_gradient: np.ndarray
    circuit_gradient: np.ndarray
    scope: str = ('derivatives with respect to real u=Hphi/r [A/m²] at fixed frequency, geometry, '
                  'beta and RF interval/phase conventions; homogeneous constrained entries are zero; '
                  'not a mesh-error estimator, shape derivative or total eigenmode derivative')


def r_over_q_gradient(solution,mode=0):
    """Differentiate both named R/Q definitions on the constrained real space.

    Both electric and magnetic energies are retained away from an eigenvector.
    No renormalization or equipartition assumption is made in the derivative.
    """
    omega=_omega(solution,mode);u=solution.u[:,mode]
    if not np.isfinite(u).all():raise ValueError('RF sensitivity requires finite coefficients')
    c=voltage_covector(solution,mode);voltage=complex(c@u)
    energy_action=(MU0*TAU/4)*(solution.mass@u)+(TAU/(4*omega**2*EPS0))*(solution.stiffness@u)
    energy=float(u@energy_action)
    if not math.isfinite(energy) or energy<=0:raise ValueError('RF sensitivity requires positive finite electromagnetic energy')
    rq=abs(voltage)**2/(omega*energy)
    gradient=2*np.real(np.conj(voltage)*c)/(omega*energy)-2*rq*energy_action/energy
    gradient[solution.space.constrained_dofs]=0.
    if not math.isfinite(rq) or not np.isfinite(gradient).all():raise ValueError('R/Q sensitivity is not finite')
    circuit=gradient/2
    gradient.setflags(write=False);circuit.setflags(write=False)
    return FixedFrequencyRQGradient(float(solution.frequencies_hz[mode]),voltage,rq,rq/2,gradient,circuit)
