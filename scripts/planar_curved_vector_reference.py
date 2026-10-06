# SPDX-License-Identifier: Apache-2.0
"""Vectorized independent P2 evaluation for large validator integrations.

Uses actual native geometry, coefficients and frequencies. No eigenpair or
scalar amplitude is changed. Kept outside production; compare with its public
12-component API before using this kernel in an acceptance driver.
"""
import numpy as np
from dataclasses import fields
from superfish_ng.constants import EPS0, MU0, TAU
from superfish_ng.planar_curved_geometry import strict_array, _closed_reference_mask
from superfish_ng.planar_curved_solver import PlanarCurvedSolution, _reference_inputs


def original_vectors(solution, cell, refs):
    if isinstance(cell, bool) or not isinstance(cell, (int, np.integer)) or not 0 <= cell < len(solution.space.cell_nodes):
        raise ValueError('vector reference requires an original cell index')
    refs = strict_array(refs, 2, 'vector reference points')
    if not np.all(_closed_reference_mask(refs)):
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


class _VectorizedValidationSolution(PlanarCurvedSolution):
    """Explicit validator adapter retaining all original solution arrays.

    RF still uses the production routine and original coefficients; only the
    all-mode field sampling used by comparison/independent area rules changes.
    """
    def all_fields_at_reference(self, cell_indices, reference_points):
        cells, refs = _reference_inputs(self, cell_indices, reference_points)
        electric = np.empty((len(refs), 3, self.case.modes), dtype=complex)
        magnetic = np.empty_like(electric)
        for cell in np.unique(cells):
            selected = np.flatnonzero(cells == cell)
            electric[selected], magnetic[selected] = original_vectors(self, int(cell), refs[selected])
        return {f'{name}{axis}_{phase}_{unit}': getattr(vector[:, i], part)
            for name, unit, vector in (('E', 'V_per_m', electric), ('H', 'A_per_m', magnetic))
            for i, axis in enumerate('xyz') for phase, part in (('real', 'real'), ('quadrature', 'imag'))}


def vectorized_validation_view(solution):
    if not isinstance(solution, PlanarCurvedSolution):
        raise ValueError('validation adapter requires an actual curved planar solution')
    return _VectorizedValidationSolution(**{field.name: getattr(solution, field.name)
        for field in fields(PlanarCurvedSolution)})
