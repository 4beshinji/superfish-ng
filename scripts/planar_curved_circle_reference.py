# SPDX-License-Identifier: Apache-2.0
"""Streaming circular analytical comparison, with complete original fields.

Same Bessel roots, peak-phasor fields and sidewall G as the P05/P07 reference.
No whole-domain sampled field arrays are retained; two passes integrate direct
vector differences after ONE common scalar group rotation.
"""
import numpy as np
from scipy.special import jv, jvp, jn_zeros, jnp_zeros
from superfish_ng.constants import C0, TAU, EPS0, MU0, Z0
from superfish_ng.planar_curved_solver import planar_curved_quantities
from planar_curved_vector_reference import original_vectors
from validate_planar_curved_convergence import _rule
from validate_planar_curved_rf import groups


class CircularReference:
    def __init__(self, radius, polarization, normalization=1.):
        if polarization not in ('te', 'tm') or isinstance(radius, bool) or not np.isfinite(radius) or radius <= 0:
            raise ValueError('circle reference requires a positive radius and TE or TM')
        if isinstance(normalization, bool) or not np.isfinite(normalization) or normalization <= 0:
            raise ValueError('circle reference requires positive peak-phasor energy per length')
        self.radius, self.polarization = radius, polarization
        self.definition = groups(polarization)
        self.parameters, frequencies, geometry_factors = [], [], []
        material = MU0 if polarization == 'te' else EPS0
        for n, s, multiplicity, _ in self.definition:
            alpha = float((jnp_zeros if polarization == 'te' else jn_zeros)(n, s)[-1])
            omega = C0*alpha/radius
            integral = (2*np.pi if n == 0 else np.pi)*radius**2/2*(jvp(n, alpha)**2+(1-n*n/alpha**2)*jv(n, alpha)**2)
            amplitude = np.sqrt(2*normalization/(material*integral))
            self.parameters.append((n, alpha, multiplicity, omega, amplitude))
            frequencies.extend([omega/TAU]*multiplicity)
            geometry_factors.extend([Z0*alpha/2*(1-n*n/alpha**2 if polarization == 'te' else 1)]*multiplicity)
        self.frequencies_hz = np.array(frequencies)
        self.geometry_factors_ohm = np.array(geometry_factors)

    def fields(self, points):
        points = np.asarray(points, dtype=float)
        if points.ndim != 2 or points.shape[1] != 2 or not np.isfinite(points).all():
            raise ValueError('circle reference requires finite xy points')
        r, theta = np.linalg.norm(points, axis=1), np.arctan2(points[:, 1], points[:, 0])
        scalars, gradients = [], []
        for n, alpha, multiplicity, _, amplitude in self.parameters:
            radial_argument = alpha*r/self.radius
            bessel, derivative = jv(n, radial_argument), jvp(n, radial_argument)
            for sine in range(multiplicity):
                angular = np.sin(n*theta) if sine else np.cos(n*theta)
                angular_derivative = n*np.cos(n*theta) if sine else -n*np.sin(n*theta)
                scalars.append(amplitude*bessel*angular)
                radial = amplitude*alpha/self.radius*derivative*angular
                azimuthal = np.divide(amplitude*bessel*angular_derivative, r,
                    out=np.zeros_like(r), where=r != 0)
                gradient = np.column_stack((radial*np.cos(theta)-azimuthal*np.sin(theta),
                    radial*np.sin(theta)+azimuthal*np.cos(theta)))
                if np.any(r == 0):
                    gradient[r == 0] = ([0., amplitude*alpha/(2*self.radius)] if n == 1 and sine else
                        [amplitude*alpha/(2*self.radius), 0.] if n == 1 else [0., 0.])
                gradients.append(gradient)
        scalar = np.column_stack(scalars)
        gradient = np.stack(gradients, axis=1)
        omega = TAU*self.frequencies_hz
        electric = np.zeros((len(points), 3, len(omega)), dtype=complex)
        magnetic = np.zeros_like(electric)
        if self.polarization == 'te':
            magnetic[:, 2] = scalar
            electric[:, 0] = -1j*gradient[..., 1]/(omega*EPS0)
            electric[:, 1] = 1j*gradient[..., 0]/(omega*EPS0)
        else:
            electric[:, 2] = scalar
            magnetic[:, 0] = 1j*gradient[..., 1]/(omega*MU0)
            magnetic[:, 1] = -1j*gradient[..., 0]/(omega*MU0)
        return scalar, electric, magnetic


def check_circle_streaming(solution, radius, *, quadrature_order=10):
    case = solution.case
    reference = CircularReference(radius, case.polarization, case.normalization_j_per_m)
    if case.modes != len(reference.frequencies_hz):
        raise ValueError('circular check requires the complete analytical target and guard band')
    refs, weights = _rule(quadrature_order)
    cross = np.zeros((case.modes, case.modes))
    energies = np.zeros((2, case.modes))
    scalar_field = 1 if case.polarization == 'te' else 0
    material = MU0 if case.polarization == 'te' else EPS0

    def sample(cell):
        mapped = case.domain.elements[cell].evaluate(refs)
        measure = weights*mapped['determinant_m2']
        a = original_vectors(solution, cell, refs)
        scalar, electric, magnetic = reference.fields(mapped['points_xy_m'])
        return measure, a, scalar, (electric, magnetic)

    for cell in range(len(case.domain.cell_nodes)):
        measure, numerical, scalar, _ = sample(cell)
        cross += (numerical[scalar_field][:, 2].real*measure[:, None]).T@scalar
        for field, vectors in enumerate(numerical):
            energies[field] += np.einsum('p,pcm,pcm->m', measure, vectors.conj(), vectors).real
    cross *= material/(2*case.normalization_j_per_m)
    energies *= np.array([EPS0, MU0])[:, None]/4
    selections, rotations, singulars = [], [], []
    offset = 0
    for _, _, count, _ in reference.definition:
        selected = slice(offset, offset+count)
        u, singular, vt = np.linalg.svd(cross[selected, selected])
        selections.append(selected)
        rotations.append(u@vt)
        singulars.append(singular.tolist())
        offset += count
    numerator = np.zeros((len(selections), 2))
    denominator = np.zeros_like(numerator)
    for cell in range(len(case.domain.cell_nodes)):
        measure, numerical, _, analytical = sample(cell)
        for group, (selected, rotation) in enumerate(zip(selections, rotations)):
            for field in range(2):
                target = analytical[field][:, :, selected]
                difference = numerical[field][:, :, selected]@rotation-target
                numerator[group, field] += np.einsum('p,pcm,pcm->', measure, difference.conj(), difference).real
                denominator[group, field] += np.einsum('p,pcm,pcm->', measure, target.conj(), target).real
    if not np.isfinite(numerator).all() or not np.isfinite(denominator).all() or np.any(denominator <= 0):
        raise ValueError('circular comparison requires finite positive complete E/H norms')
    errors = np.sqrt(numerator/denominator)
    rf = [planar_curved_quantities(solution, i) for i in range(case.modes)]
    energy_error = max(max(abs(energies[0, i]/row['electric_energy_j_per_m']-1),
        abs(energies[1, i]/row['magnetic_energy_j_per_m']-1)) for i, row in enumerate(rf))
    records = []
    for group, (selected, (n, s, count, target)) in enumerate(zip(selections, reference.definition)):
        f_error = float(np.max(abs(solution.frequencies_hz[selected]/reference.frequencies_hz[selected]-1)))
        g_error = float(np.max(abs(np.array([row['geometry_factor_ohm'] for row in rf])[selected]/reference.geometry_factors_ohm[selected]-1)))
        gates = dict(frequency=f_error <= 1e-4, electric=bool(errors[group, 0] <= .01),
            magnetic=bool(errors[group, 1] <= .01), geometry_factor=g_error <= .005)
        records.append(dict(analytic_group=dict(angular_order=n, positive_root_index=s, multiplicity=count),
            numerical_ranks_zero_based=list(range(selected.start, selected.stop)), target=target,
            frequency_relative_error=f_error, electric_relative_L2_error=float(errors[group, 0]),
            magnetic_relative_L2_error=float(errors[group, 1]), geometry_factor_relative_error=g_error,
            scalar_alignment_singular_values=singulars[group], common_scalar_rotation=rotations[group].tolist(),
            gates=gates, passed=all(gates.values())))
    target_count = 5 if case.polarization == 'te' else 3
    guard = bool(solution.frequencies_hz[target_count] > solution.frequencies_hz[target_count-1])
    return dict(target_groups_passed=all(row['passed'] for row in records if row['target']),
        full_analytic_guard_groups_present=guard, groups=records, RF=rf,
        independent_field_energy_relative_error=float(energy_error), independent_energy_passed=bool(energy_error <= 1e-8),
        algebraic_residual_max=float(np.max(solution.residuals)), orthogonality_error=solution.orthogonality_error,
        reference_quadrature_order=quadrature_order, sampling_storage='one original element; direct two-pass vector differences')
