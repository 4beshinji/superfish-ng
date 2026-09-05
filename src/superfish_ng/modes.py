# SPDX-License-Identifier: Apache-2.0
"""Field-based identification of the seminar half-end-cell band and dispersion."""
import numpy as np
from scipy.optimize import linear_sum_assignment


def identify_cell_band(z, axis_fields, cell_centers, minimum_overlap=.98):
    """Identify N modes by cosine-like cell amplitudes AND axial zero count.

    This is the half-end-cell seminar band, not a universal multicell labeler.
    Input columns can be in any order; returned modes are ordered by phase.
    No fields are changed, corrected or replaced by the idealized templates.
    """
    z, fields, centers = (np.asarray(value, dtype=float) for value in (z, axis_fields, cell_centers))
    if (z.ndim != 1 or fields.ndim != 2 or centers.ndim != 1 or len(z) < 3 or len(centers) < 2
            or fields.shape[0] != len(z) or fields.shape[1] < len(centers)
            or not all(np.isfinite(v).all() for v in (z, fields, centers))
            or np.any(np.diff(z) <= 0) or np.any(np.diff(centers) <= 0)
            or centers[0] < z[0] or centers[-1] > z[-1]
            or not 0 < minimum_overlap <= 1):
        raise ValueError('band identification requires finite ordered axis/centers and enough field columns')
    count = len(centers)
    cell_fields = np.column_stack([np.interp(centers, z, column) for column in fields.T])
    phase = np.linspace(0., np.pi, count)
    templates = np.cos(np.arange(count)[:, None]*phase)
    norms = np.linalg.norm(cell_fields, axis=0)
    if np.any(norms <= 0):
        raise ValueError('zero cell-center field cannot identify a mode')
    scores = np.abs(templates.T @ cell_fields)/np.outer(np.linalg.norm(templates, axis=0), norms)
    zeros = []
    for column in fields.T:
        # Ignore values near a zero, not lobes: require every sign transition
        # between amplitudes above 1e-3 of the global maximum to be accounted for.
        nonzero = column[np.abs(column) > np.max(np.abs(column))*1e-3]
        zeros.append(int(np.count_nonzero(nonzero[:-1]*nonzero[1:] < 0)))
    cost = 1-scores+10*(np.arange(count)[:, None] != np.array(zeros)[None, :])
    rows, columns = linear_sum_assignment(cost)
    result = []
    for p, index in zip(rows, columns):
        if zeros[index] != p or scores[p, index] < minimum_overlap:
            raise ValueError(f'phase {p}*pi/{count-1} not identified: zero count={zeros[index]}, cell overlap={scores[p,index]:.6f}')
        amplitude = cell_fields[:, index]/np.max(np.abs(cell_fields[:, index]))
        if amplitude @ templates[:, p] < 0:
            amplitude *= -1
        result.append({'phase_index': int(p), 'phase_rad': float(phase[p]),
                       'label': f'{p}*pi/{count-1}', 'mode_index': int(index+1),
                       'zero_crossings': zeros[index], 'cell_overlap': float(scores[p, index]),
                       'cell_amplitudes_normalized': amplitude.tolist()})
    return result


def fit_dispersion(phase_rad, frequencies_hz):
    """Least-squares f=m1+m2*cos(theta), retaining signed residuals in hertz."""
    theta, frequencies = (np.asarray(value, dtype=float) for value in (phase_rad, frequencies_hz))
    if (theta.ndim != 1 or frequencies.shape != theta.shape or len(theta) < 2
            or not np.isfinite(theta).all() or not np.isfinite(frequencies).all()
            or np.any(frequencies <= 0)):
        raise ValueError('dispersion requires matching finite phases and positive frequencies')
    matrix = np.column_stack((np.ones(len(theta)), np.cos(theta)))
    parameters, _, rank, _ = np.linalg.lstsq(matrix, frequencies, rcond=None)
    if rank != 2:
        raise ValueError('dispersion phases do not determine two coefficients')
    fitted = matrix @ parameters
    residual = frequencies-fitted
    return {'model': 'f_hz=m1_hz+m2_hz*cos(phase_rad)', 'm1_hz': float(parameters[0]),
            'm2_hz': float(parameters[1]), 'fitted_hz': fitted.tolist(), 'residual_hz': residual.tolist(),
            'rms_residual_hz': float(np.sqrt(np.mean(residual**2)))}
