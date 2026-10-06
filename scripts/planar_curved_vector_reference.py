# SPDX-License-Identifier: Apache-2.0
"""Vectorized independent P2 evaluation for large validator integrations.

Uses actual native geometry, coefficients and frequencies. No eigenpair or
scalar amplitude is changed. Kept outside production; compare with its public
12-component API before using this kernel in an acceptance driver.
"""
import numpy as np
from superfish_ng.constants import EPS0, MU0, TAU
from superfish_ng.planar_curved_geometry import strict_array


def original_vectors(solution, cell, refs):
    if isinstance(cell, bool) or not isinstance(cell, (int, np.integer)) or not 0 <= cell < len(solution.space.cell_nodes):
        raise ValueError('vector reference requires an original cell index')
    refs = strict_array(refs, 2, 'vector reference points')
    if np.any(refs < 0) or np.any(refs.sum(axis=1) > 1):
        raise ValueError('vector reference points must be in the closed reference triangle')
    bary = np.column_stack((1-refs.sum(axis=1), refs))
    gradient = np.array([[-1., -1.], [1., 0.], [0., 1.]])
    values = np.empty((len(refs), 6))
    derivatives = np.empty((len(refs), 6, 2))
    values[:, :3] = bary*(2*bary-1)
    derivatives[:, :3] = (4*bary-1)[:, :, None]*gradient
    for k, (i, j) in enumerate(((0, 1), (1, 2), (2, 0)), 3):
        values[:, k] = 4*bary[:, i]*bary[:, j]
        derivatives[:, k] = 4*(bary[:, i, None]*gradient[j]+bary[:, j, None]*gradient[i])
    geometry = solution.case.domain.points_xy_m[solution.case.domain.cell_nodes[cell]]
    jacobian = np.einsum('ia,pib->pab', geometry-geometry[0], derivatives)
    determinant = np.linalg.det(jacobian)
    if not np.isfinite(jacobian).all() or np.any(determinant <= 0):
        raise ValueError('original vector reference requires resolved positive actual Jacobians')
    physical = np.einsum('pia,pab->pib', derivatives, np.linalg.inv(jacobian))
    coefficients = solution.coefficients[solution.space.cell_nodes[cell]]
    scalar = values@coefficients
    derivative = np.einsum('pia,im->pam', physical, coefficients)
    omega = TAU*solution.frequencies_hz
    electric = np.zeros((len(refs), 3, solution.case.modes), dtype=complex)
    magnetic = np.zeros_like(electric)
    if solution.case.polarization == 'te':
        magnetic[:, 2] = scalar
        electric[:, 0] = -1j*derivative[:, 1]/(omega*EPS0)
        electric[:, 1] = 1j*derivative[:, 0]/(omega*EPS0)
    elif solution.case.polarization == 'tm':
        electric[:, 2] = scalar
        magnetic[:, 0] = 1j*derivative[:, 1]/(omega*MU0)
        magnetic[:, 1] = -1j*derivative[:, 0]/(omega*MU0)
    else:
        raise ValueError('original vector reference requires vacuum TE or TM')
    if not np.isfinite(electric).all() or not np.isfinite(magnetic).all():
        raise ValueError('original vector reference exceeds finite SI arithmetic')
    return electric, magnetic
