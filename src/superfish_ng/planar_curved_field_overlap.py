# SPDX-License-Identifier: Apache-2.0
"""Separate original Cartesian E/H inner products on full quadratic maps."""
from dataclasses import dataclass, replace
import numpy as np
from scipy.sparse import issparse
from .config import integer
from .constants import EPS0, MU0, TAU
from .fem import triangle_quadrature
from .planar_curved import PlanarCurvedCase
from .planar_curved_solver import PlanarCurvedSolution, restore_planar_curved_solution
from .planar_curved_saved import _mesh_arrays, _same_array
from .planar_curved_geometry import immutable_array
from .planar_curved_comparison import (build_planar_curved_comparison,
    PlanarCurvedComparisonBudgetExceeded)

_SAMPLE_MODE_BATCH = 262144
_COMPONENTS = tuple(tuple(f'{field}{axis}_{phase}_{unit}' for axis in 'xyz'
    for phase in ('real', 'quadrature')) for field, unit in (('E', 'V_per_m'), ('H', 'A_per_m')))


@dataclass(frozen=True)
class PlanarCurvedFieldGrams:
    # Each tuple: previous self, previous/current cross, current self.
    electric: tuple
    magnetic: tuple
    diagnostic: dict


def verified_planar_curved_solution(solution):
    """Rebuild the actual lowest positive band; keep original arrays unchanged."""
    if type(solution) is not PlanarCurvedSolution or type(solution.case) is not PlanarCurvedCase:
        raise ValueError('curved planar field comparison requires original PlanarCurvedSolution objects')
    for name in ('coefficients', 'frequencies_hz'):
        value = getattr(solution, name)
        if type(value) is not np.ndarray or value.dtype != np.dtype(float):
            raise ValueError('curved planar field comparison requires original float64 arrays without conversion')
    case = PlanarCurvedCase.from_dict(solution.case.to_dict())
    restored = restore_planar_curved_solution(case, solution.coefficients, solution.frequencies_hz,
                                              verify_spectrum=True)
    expected, actual = _mesh_arrays(restored.space), _mesh_arrays(solution.space)
    if actual.keys() != expected.keys() or any(not _same_array(value, actual[name]) for name, value in expected.items()):
        raise ValueError('curved planar comparison mesh differs from the original declared quadratic FEM')
    for name in ('coefficients', 'frequencies_hz', 'free_dofs', 'eigenvalues'):
        value = getattr(solution, name)
        if type(value) is not np.ndarray or not _same_array(value, getattr(restored, name)):
            raise ValueError(f'curved planar comparison {name} differs from the original FEM reconstruction')
    # Diagnostics are derived, not native input fields. BLAS accumulation can
    # change its last bits when a strided input is copied into immutable storage.
    # The original solver's physical gates apply to the claimed diagnostics;
    # only the freshly rebuilt diagnostics/spectrum drive this comparison.
    residuals = solution.residuals
    if (type(residuals) is not np.ndarray or residuals.shape != restored.residuals.shape
            or not np.isfinite(residuals).all() or np.any(residuals < 0) or np.max(residuals) > 1e-7
            or not np.isfinite(solution.orthogonality_error)
            or not 0 <= solution.orthogonality_error <= 1e-8):
        raise ValueError('curved planar comparison diagnostics violate the original FEM gates')
    for name in ('stiffness', 'mass'):
        value, rebuilt = getattr(solution, name), getattr(restored, name)
        if (not issparse(value) or value.shape != rebuilt.shape or value.dtype != rebuilt.dtype
                or not np.isfinite(value.data).all() or (value-rebuilt).nnz):
            raise ValueError('curved planar comparison matrices differ from the original Cartesian area FEM')
    return restored


def _source_grams(solution):
    c, omega = solution.coefficients, TAU*solution.frequencies_hz
    scalar = c.T@(solution.mass@c)
    gradient = (c.T@(solution.stiffness@c))/omega[:, None]/omega[None, :]
    return (gradient/EPS0**2, scalar) if solution.case.polarization == 'te' else (scalar, gradient/MU0**2)


def _normalized_difference(first, second):
    if not all(np.isfinite(matrix).all() for matrix in (*first, *second)):
        raise ValueError('UNVERIFIED: curved planar field integrals exceed finite SI range')
    left, right = np.sqrt(np.diag(second[0])), np.sqrt(np.diag(second[2]))
    if not np.isfinite(left).all() or not np.isfinite(right).all() or np.any(left <= 0) or np.any(right <= 0):
        raise ValueError('UNVERIFIED: curved planar field self norms are not finite positive')
    return max(float(np.max(abs(a-b)/x[:, None]/y[None, :]))
               for a, b, x, y in zip(first, second, (left, left, right), (left, right, right)))


def _samples(solution, rows):
    cells = np.concatenate([np.full(len(row['native_reference_points']), row['native_cell'], dtype=int) for row in rows])
    points = np.concatenate([row['native_reference_points'] for row in rows])
    fields = solution.all_fields_at_reference(cells, points)
    expected = set(name for family in _COMPONENTS for name in family)
    if (fields.keys() != expected or any(value.shape != (len(cells), solution.case.modes)
            or not np.isfinite(value).all() for value in fields.values())):
        raise ValueError('UNVERIFIED: original curved planar phasor components are unresolved')
    return [[fields[name] for name in family] for family in _COMPONENTS]


def _integrate_fields(previous, current, comparison, order, max_sample_points):
    """Private test seam; public entry accepts only fully verified eigenfields."""
    rule = list(triangle_quadrature(order))
    q, w = np.array([p[1:] for p, _ in rule]), np.array([weight for _, weight in rule])
    if 2*len(rule)*len(comparison.triangles) > max_sample_points:
        raise PlanarCurvedComparisonBudgetExceeded('curved planar field integration exceeds max_sample_points')
    na, nb = previous.case.modes, current.case.modes
    grams = [[np.zeros((na, na)), np.zeros((na, nb)), np.zeros((nb, nb))] for _ in range(2)]
    batch = max(1, _SAMPLE_MODE_BATCH//(len(rule)*max(na, nb)))
    for start in range(0, len(comparison.triangles), batch):
        part = replace(comparison, triangles=comparison.triangles[start:start+batch])
        samples = []
        for side, solution in enumerate((previous, current)):
            rows = part.evaluate(side, q)
            measure = np.concatenate([row['determinant_m2']*w for row in rows])
            if not np.isfinite(measure).all() or np.any(measure <= 0):
                raise ValueError('UNVERIFIED: curved planar comparison requires finite positive Cartesian area')
            root = np.sqrt(measure)[:, None]
            samples.append([[root*values for values in family] for family in _samples(solution, rows)])
        for matrices, left, right in zip(grams, *samples):
            for a, b in zip(left, right):
                matrices[0] += a.T@a
                matrices[1] += a.T@b
                matrices[2] += b.T@b
    return grams


def planar_curved_field_grams(previous, current, domain, *, previous_cells=None, current_cells=None,
        quadrature_order=None, max_pair_tests=2000000, max_triangles=250000,
        max_gram_modes=256, max_sample_points=2000000):
    """Compare real Hermitian peak-phasor E/H products with actual native dx dy.

    Cross products retain fixed Cartesian components and sqrt(dA_old*dA_new).
    Source self Grams retain their actual original amplitudes, signs and energy.
    The full twelve named real/+i quadrature components are sampled. This is a
    unitary L2 correspondence, not a Maxwell transform, frequency law, field
    projection, discretization estimate, individual identity or mode tracking.
    """
    for name, value in (('max_pair_tests', max_pair_tests), ('max_triangles', max_triangles),
                       ('max_gram_modes', max_gram_modes), ('max_sample_points', max_sample_points)):
        integer(value, name)
    if quadrature_order is not None:
        integer(quadrature_order, 'quadrature_order', 4)
        if quadrature_order > 28:
            raise ValueError('curved planar comparison quadrature_order must be from 4 to 28; verification uses order+4 <=32')
    for solution in (previous, current):
        if type(solution) is not PlanarCurvedSolution or type(solution.case) is not PlanarCurvedCase:
            raise ValueError('curved planar field comparison requires original PlanarCurvedSolution objects')
        if solution.case.modes > max_gram_modes:
            raise PlanarCurvedComparisonBudgetExceeded('curved planar field comparison exceeds max_gram_modes')
    if previous.case.polarization != current.case.polarization:
        raise ValueError('curved planar field comparison cannot mix TE and TM polarizations')
    previous, current = map(verified_planar_curved_solution, (previous, current))
    comparison = build_planar_curved_comparison(previous.case.domain, current.case.domain, domain,
        previous_cells=previous_cells, current_cells=current_cells,
        max_pair_tests=max_pair_tests, max_triangles=max_triangles)
    order = min(28, max(16, previous.case.quadrature_order+4, current.case.quadrature_order+4)) if quadrature_order is None else quadrature_order
    orders = [order, order+4]
    count = 2*len(comparison.triangles)*sum(n*n for n in orders)
    if count > max_sample_points:
        raise PlanarCurvedComparisonBudgetExceeded('complete two-order two-side curved field comparison exceeds max_sample_points')
    low, high = (_integrate_fields(previous, current, comparison, n, max_sample_points) for n in orders)
    differences = [_normalized_difference(a, b) for a, b in zip(low, high)]
    if max(differences) > 1e-10:
        raise ValueError('UNVERIFIED: curved planar field quadrature; increase quadrature_order or refine the declared native partition')
    sources = [_source_grams(solution) for solution in (previous, current)]
    reproduction, minimum = [], []
    for family, matrices in enumerate(high):
        for matrix, expected in ((matrices[0], sources[0][family]), (matrices[2], sources[1][family])):
            norm = np.sqrt(np.diag(expected))
            reproduction.append(float(np.max(abs(matrix-expected)/norm[:, None]/norm[None, :])))
        aa, ab, bb = matrices
        joint = np.block([[aa, ab], [ab.T, bb]])
        norm = np.sqrt(np.diag(joint))
        normalized = joint/norm[:, None]/norm[None, :]
        values = np.linalg.eigvalsh((normalized+normalized.T)/2)
        if values[0] < -1e-10*max(1., values[-1]):
            raise ValueError('UNVERIFIED: curved planar joint field Gram is not positive semidefinite')
        minimum.append(float(values[0]))
    if not np.isfinite(reproduction).all() or max(reproduction) > 1e-8:
        raise ValueError('UNVERIFIED: curved planar comparison does not reproduce original FEM E/H energy Grams')
    high = [tuple(immutable_array(matrix, float) for matrix in matrices) for matrices in high]
    diagnostic = dict(measure='actual original native dx dy, per unit z length; no radial weight',
        electric_units='V^2', magnetic_units='A^2',
        phasor='peak exp(+i omega t); real part of conjugate vector product; all real/+i quadrature components',
        integration_orders=orders, integration_tolerance=1e-10,
        normalized_quadrature_differences=differences, sample_points=count, max_sample_points=max_sample_points,
        maximum_source_gram_difference=max(reproduction), source_gram_tolerance=1e-8,
        minimum_normalized_joint_gram_eigenvalues=minimum, geometry=comparison.report,
        polarization=previous.case.polarization,
        spectrum='each original lowest positive cutoff band reverified; TE constant nullspace excluded',
        normalization_j_per_m=[s.case.normalization_j_per_m for s in (previous, current)],
        transport='fixed Cartesian components and square-root actual native area density; unitary L2 comparison, not a Maxwell transform',
        mode_tracking='not_performed', scope='separate original area E/H inner products; no continuum error bound or mode identity')
    return PlanarCurvedFieldGrams(*high, diagnostic)
