# SPDX-License-Identifier: Apache-2.0
"""Actual curved Cartesian TE/TM FEM, original phasor fields and sidewall RF.

Only generic Cartesian spectral/algebraic checks are shared with planar.py.
Area assembly, mapped fields, point membership and curved ds remain dedicated.
"""
from dataclasses import dataclass
import numpy as np
from .config import integer
from .constants import C0, TAU, EPS0, MU0
from .planar import _eigenpairs, _restore
from .planar_curved import PlanarCurvedCase
from .planar_curved_fem import planar_curved_matrices
from .planar_curved_geometry import strict_array, immutable_array


def _reference_inputs(solution, cell_indices, reference_points):
    try:
        indices = np.asarray(cell_indices, dtype=object)
    except (TypeError, ValueError) as exc:
        raise ValueError('curved planar field cell indices require a vector') from exc
    if indices.ndim != 1:
        raise ValueError('curved planar field cell indices require a vector')
    cells = strict_array([[i] for i in indices], 1, 'curved planar cell indices', indices=True)[:, 0]
    ref = strict_array(reference_points, 2, 'curved planar field reference points')
    if len(cells) != len(ref) or np.any(cells >= len(solution.space.cell_nodes)) or np.any(ref < 0) or np.any(ref.sum(axis=1) > 1):
        raise ValueError('curved planar fields require valid cells and points in the closed reference triangle')
    return cells, ref


def _components(scalar, derivative, omega, polarization):
    fields = {f'{field}{axis}_{phase}_{unit}': np.zeros_like(scalar)
              for field, unit in (('E', 'V_per_m'), ('H', 'A_per_m'))
              for axis in 'xyz' for phase in ('real', 'quadrature')}
    if polarization == 'tm':
        fields.update(Ez_real_V_per_m=scalar, Hx_quadrature_A_per_m=derivative[..., 1]/(omega*MU0),
                      Hy_quadrature_A_per_m=-derivative[..., 0]/(omega*MU0))
    else:
        fields.update(Hz_real_A_per_m=scalar, Ex_quadrature_V_per_m=-derivative[..., 1]/(omega*EPS0),
                      Ey_quadrature_V_per_m=derivative[..., 0]/(omega*EPS0))
    return fields


@dataclass(frozen=True)
class PlanarCurvedSolution:
    case: PlanarCurvedCase
    space: object
    stiffness: object
    mass: object
    free_dofs: np.ndarray
    eigenvalues: np.ndarray
    frequencies_hz: np.ndarray
    coefficients: np.ndarray
    residuals: np.ndarray
    orthogonality_error: float

    def scalar_at_reference(self, cell_indices, reference_points, mode=0):
        integer(mode, 'mode', 0)
        if mode >= self.case.modes:
            raise ValueError('curved planar mode index is out of range')
        cells, ref = _reference_inputs(self, cell_indices, reference_points)
        scalar, derivative, points = np.empty(len(cells)), np.empty((len(cells), 2)), np.empty_like(ref)
        for cell in np.unique(cells):
            selected = np.flatnonzero(cells == cell)
            mapped = self.case.domain.elements[cell].evaluate(ref[selected])
            coefficient = self.coefficients[self.space.cell_nodes[cell], mode]
            scalar[selected] = mapped['basis_values']@coefficient
            derivative[selected] = np.einsum('qia,i->qa', mapped['basis_gradients'], coefficient)
            points[selected] = mapped['points_xy_m']
        if not np.isfinite(scalar).all() or not np.isfinite(derivative).all():
            raise ValueError('curved planar field arithmetic exceeds finite SI range')
        return dict(scalar=scalar, gradient_xy=derivative, points_xy_m=points)

    def fields_at_reference(self, cell_indices, reference_points, mode=0):
        mapped = self.scalar_at_reference(cell_indices, reference_points, mode)
        scalar, derivative = mapped['scalar'], mapped['gradient_xy']
        return _components(scalar, derivative, TAU*self.frequencies_hz[mode], self.case.polarization)

    def all_fields_at_reference(self, cell_indices, reference_points):
        """All original positive modes, shape (points,modes) per component."""
        cells, ref = _reference_inputs(self, cell_indices, reference_points)
        scalar = np.empty((len(cells), self.case.modes))
        derivative = np.empty((len(cells), self.case.modes, 2))
        for cell in np.unique(cells):
            selected = np.flatnonzero(cells == cell)
            mapped = self.case.domain.elements[cell].evaluate(ref[selected])
            coefficient = self.coefficients[self.space.cell_nodes[cell]]
            scalar[selected] = mapped['basis_values']@coefficient
            derivative[selected] = np.einsum('qia,im->qma', mapped['basis_gradients'], coefficient)
        if not np.isfinite(scalar).all() or not np.isfinite(derivative).all():
            raise ValueError('curved planar field arithmetic exceeds finite SI range')
        return _components(scalar, derivative, TAU*self.frequencies_hz, self.case.polarization)

    def fields_in_cells(self, cell_indices, barycentric, mode=0):
        bary = strict_array(barycentric, 3, 'curved planar barycentric points')
        if np.any(bary < 0) or not np.allclose(bary.sum(axis=1), 1, rtol=0, atol=4*np.finfo(float).eps):
            raise ValueError('curved planar barycentric coordinates must lie in the closed unit triangle')
        return self.fields_at_reference(cell_indices, bary[:, 1:], mode)


def restore_planar_curved_solution(case, coefficients, frequencies_hz, *, verify_spectrum=True):
    """Rebuild the actual geometry/matrices and validate the full positive band."""
    space, k, m, free = planar_curved_matrices(case)
    restored = _restore(case, space, k, m, free, coefficients, frequencies_hz, verify_spectrum=verify_spectrum)
    return _curved_solution(restored)


def _curved_solution(restored):
    return PlanarCurvedSolution(restored.case, restored.space, restored.stiffness, restored.mass,
        restored.free_dofs, immutable_array(restored.eigenvalues, float), immutable_array(restored.frequencies_hz, float),
        immutable_array(restored.coefficients, float), immutable_array(restored.residuals, float), restored.orthogonality_error)


def solve_planar_curved(case):
    if not isinstance(case, PlanarCurvedCase):
        raise ValueError('curved planar solve requires an explicit PlanarCurvedCase')
    space, k, m, free = planar_curved_matrices(case)
    values, vectors = _eigenpairs(case, k, m, free)
    material = EPS0 if case.polarization == 'tm' else MU0
    coefficients = np.zeros((k.shape[0], case.modes))
    coefficients[free] = vectors*np.sqrt(2*case.normalization_j_per_m/material)
    for mode in range(case.modes):
        if coefficients[np.argmax(abs(coefficients[:, mode])), mode] < 0:
            coefficients[:, mode] *= -1
    restored = _restore(case, space, k, m, free, coefficients, C0/TAU*np.sqrt(values), verify_spectrum=False)
    return _curved_solution(restored)


class PlanarCurvedFieldSampler:
    def __init__(self, solution):
        if not isinstance(solution, PlanarCurvedSolution):
            raise ValueError('curved planar sampler requires a PlanarCurvedSolution')
        from .planar_curved_location import PlanarCurvedLocator
        self.solution = solution
        self.locator = PlanarCurvedLocator(solution.case.domain)

    def evaluate(self, points_xy_m, mode=0):
        cells, refs = self.locator.locate(points_xy_m)
        return self.solution.fields_at_reference(cells, refs, mode)


def planar_curved_quantities(solution, mode=0):
    if not isinstance(solution, PlanarCurvedSolution):
        raise ValueError('curved planar RF requires a PlanarCurvedSolution')
    integer(mode, 'mode', 0)
    case = solution.case
    if mode >= case.modes:
        raise ValueError('curved planar RF mode index is out of range')
    coefficient = solution.coefficients[:, mode]
    scalar = float(coefficient@(solution.mass@coefficient))
    gradient = float(coefficient@(solution.stiffness@coefficient))
    frequency = float(solution.frequencies_hz[mode])
    omega = TAU*frequency
    if case.polarization == 'tm':
        ue, um = EPS0*scalar/4, gradient/(4*omega**2*MU0)
    else:
        ue, um = gradient/(4*omega**2*EPS0), MU0*scalar/4
    nodes, weights = np.polynomial.legendre.leggauss(case.wall_quadrature_order)
    nodes, weights = (nodes+1)/2, weights/2
    domain = case.domain
    wall = 0.
    for edge, (cell, local) in enumerate(zip(domain.boundary_cells, domain.boundary_local_edges)):
        ref = (np.column_stack((nodes, 0*nodes)) if local == 0 else
               np.column_stack((1-nodes, nodes)) if local == 1 else np.column_stack((0*nodes, 1-nodes)))
        boundary = domain.boundary_evaluate(edge, nodes)
        fields = solution.fields_at_reference(np.full(len(nodes), cell), ref, mode)
        if case.polarization == 'te':
            tangent_h = fields['Hz_real_A_per_m']
        else:
            tangent_h = fields['Hx_quadrature_A_per_m']*boundary['tangent_xy'][:, 0]+fields['Hy_quadrature_A_per_m']*boundary['tangent_xy'][:, 1]
        wall += float(weights@(boundary['speed_m']*tangent_h**2))
    rs = float(np.sqrt(np.pi*frequency*MU0/case.conductivity_s_per_m))
    loss, energy = rs*wall/2, ue+um
    if not np.isfinite([ue, um, wall, loss]).all() or min(ue, um, wall, loss) <= 0:
        raise ValueError('curved planar RF requires finite positive energy and actual PEC sidewall loss')
    return dict(frequency_hz=frequency, stored_energy_j_per_m=energy, electric_energy_j_per_m=ue,
        magnetic_energy_j_per_m=um, wall_loss_w_per_m=loss, surface_resistance_ohm=rs,
        q0=omega*energy/loss, geometry_factor_ohm=2*omega*energy/wall,
        r_over_q_accelerator_ohm=None, r_over_q_circuit_ohm=None, vacc_v=None, eacc_v_per_m=None,
        accelerating_quantities_reason='cutoff cross-section per unit longitudinal length; no finite accelerating path is declared',
        wall_magnetic_integral_a2_per_m=wall, wall_quadrature_order=case.wall_quadrature_order,
        area_quadrature_order=case.quadrature_order, boundary_length_m=domain.boundary_length_m(quadrature_order=case.wall_quadrature_order),
        domain_area_m2=domain.area_m2, phasor_convention='peak exp(+i omega t)', longitudinal_units='J/m and W/m')
