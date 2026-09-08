# SPDX-License-Identifier: Apache-2.0
"""Constrained eigenvector adjoints for fixed-frequency curved RF objectives."""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import bmat,csc_matrix,diags
from scipy.sparse.linalg import splu
from .constants import C0,TAU
from .curved_rf_sensitivity import r_over_q_gradient


@dataclass(frozen=True)
class FixedFrequencyRQAdjoint:
    accelerator_adjoint: np.ndarray
    circuit_adjoint: np.ndarray
    accelerator_lagrange_multiplier: float
    relative_residual: float
    relative_gauge_error: float
    eigenpair_relative_residual: float
    scope: str = ('(K-lambda M)z + M u eta = fixed-frequency RF coefficient gradient; '
                  'u.T M z = 0 on the homogeneous constrained space; '
                  'not a total frequency/shape derivative, error bound or simplicity certificate')


def r_over_q_adjoint(solution,mode=0):
    """Solve the bordered adjoint using sparse, mass-diagonally scaled matrices.

    The requested eigenpair must be resolved and separated from other supplied
    eigenvalues. Uncomputed eigenvalues are not certified to be separated.
    The circuit adjoint and multiplier are one half of the accelerator values.
    """
    gradient=r_over_q_gradient(solution,mode).accelerator_gradient
    u=solution.u[:,mode];value=float(solution.eigenvalues[mode])
    if not np.isfinite(value) or value<=0 or abs((TAU*solution.frequencies_hz[mode]/C0)**2/value-1)>1e-10:
        raise ValueError('adjoint requires a positive eigenvalue consistent with frequency')
    others=np.delete(solution.eigenvalues,mode)
    if not np.isfinite(others).all() or np.any(abs(others-value)/value<1e-7):
        raise ValueError('adjoint requires eigenvalue separation; use a subspace objective for a cluster')
    constrained=solution.space.constrained_dofs
    if np.any(u[constrained]!=0):raise ValueError('adjoint eigenpair violates homogeneous constraints')
    free=np.setdiff1d(np.arange(len(u)),constrained)
    k=solution.stiffness[free][:,free];m=solution.mass[free][:,free];v=u[free]
    ku,mu=k@v,m@v
    eigen_residual=float(np.linalg.norm(ku-value*mu)/(np.linalg.norm(ku)+value*np.linalg.norm(mu)))
    if not np.isfinite(eigen_residual) or eigen_residual>1e-7:
        raise ValueError('adjoint requires a resolved eigenpair (relative residual <= 1e-7)')
    diagonal=m.diagonal()
    if not np.isfinite(diagonal).all() or np.any(diagonal<=0):raise ValueError('adjoint requires a positive finite mass diagonal')
    d=1/np.sqrt(diagonal);scale=diags(d)
    gauge=d*mu;gauge_norm=float(np.linalg.norm(gauge));gauge/=gauge_norm
    operator=(k/value-m).tocsc();scaled=scale@operator@scale
    border=csc_matrix(gauge[:,None])
    matrix=bmat([[scaled,border],[border.T,None]],format='csc')
    rhs=np.r_[d*gradient[free]/value,0.]
    try:
        answer=splu(matrix).solve(rhs)
    except RuntimeError as exc:
        raise ValueError('adjoint bordered system is singular; check eigenvalue separation') from exc
    z=d*answer[:-1];eta=float(value*answer[-1]/gauge_norm)
    residual=operator@z+mu*(eta/value)-gradient[free]/value
    denominator=np.linalg.norm(operator@z)+np.linalg.norm(mu*(eta/value))+np.linalg.norm(gradient[free]/value)
    relative=float(np.linalg.norm(residual)/max(denominator,np.finfo(float).tiny))
    orthogonality=float(abs(mu@z)/max(np.linalg.norm(mu)*np.linalg.norm(z),np.finfo(float).tiny))
    if not np.isfinite(answer).all() or not np.isfinite([eta,relative,orthogonality]).all() or relative>1e-8 or orthogonality>1e-10:
        raise ValueError('adjoint residual or mass-orthogonality check failed')
    result=np.zeros(len(u));result[free]=z;circuit=result/2
    result.setflags(write=False);circuit.setflags(write=False)
    return FixedFrequencyRQAdjoint(result,circuit,eta,relative,orthogonality,eigen_residual)
