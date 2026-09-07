# SPDX-License-Identifier: Apache-2.0
"""Continuous bounds of discrete curved PEC fields; physical peaks need convergence."""
from fractions import Fraction
import numpy as np
from .constants import EPS0, TAU
from .curved_surface import CurvedSurfaceSampler
from .rational_bounds import add, multiply, polynomial, bound_rational_norm

_REFERENCE = ((0, 0), (1, 0), (0, 1))
_GRADIENTS = ((-1, -1), (1, 0), (0, 1))


def _negative(p):
    return tuple(-v for v in p)


def _combine(polynomials, values):
    result = (Fraction(0),)
    for p, value in zip(polynomials, values):
        result = add(result, multiply(p, (Fraction(float(value)),)))
    return result


def edge_field_polynomials(sampler, boundary_index, mode=0):
    """Exact polynomial coefficients from the stored binary geometry and u.

    E has two quartic numerators over omega*epsilon*det(J); H=r*u is quartic.
    Returned coefficients follow the stored boundary endpoint parameterization.
    """
    solution = sampler.solution
    if type(boundary_index) is not int or not 0 <= boundary_index < len(sampler.owners):
        raise ValueError('boundary_index must be a valid zero-based integer')
    if type(mode) is not int or not 0 <= mode < solution.case.modes:
        raise ValueError('mode must be a valid zero-based integer')
    cell, a, b, direction = sampler.owners[boundary_index]
    if direction == -1:
        a, b = b, a
    start, end = _REFERENCE[a], _REFERENCE[b]
    x, y = [polynomial([start[k], end[k]-start[k]]) for k in range(2)]
    barycentric = [add([1], _negative(add(x, y))), x, y]
    basis, gradients = [], []
    for i, value in enumerate(barycentric):
        basis.append(multiply(value, add(multiply([2], value), [-1])))
        gradients.append([multiply(add(multiply([4], value), [-1]), [g]) for g in _GRADIENTS[i]])
    for i, j in ((0, 1), (1, 2), (2, 0)):
        basis.append(multiply([4], multiply(barycentric[i], barycentric[j])))
        gradients.append([multiply([4], add(multiply([_GRADIENTS[i][k]], barycentric[j]),
                                               multiply([_GRADIENTS[j][k]], barycentric[i]))) for k in range(2)])
    nodes = solution.space.geometry.cell_nodes[cell]
    points = solution.space.geometry.points_rz_m[nodes]
    coefficients = solution.u[nodes, mode]
    gx, gy = [g[0] for g in gradients], [g[1] for g in gradients]
    r, u = _combine(basis, points[:, 0]), _combine(basis, coefficients)
    rx, ry = _combine(gx, points[:, 0]), _combine(gy, points[:, 0])
    zx, zy = _combine(gx, points[:, 1]), _combine(gy, points[:, 1])
    ux, uy = _combine(gx, coefficients), _combine(gy, coefficients)
    determinant = add(multiply(rx, zy), _negative(multiply(ry, zx)))
    er = multiply(r, add(multiply(ux, ry), _negative(multiply(uy, rx))))
    ez = add(multiply([2], multiply(u, determinant)),
             multiply(r, add(multiply(ux, zy), _negative(multiply(uy, zx)))))
    denominator = multiply(determinant, polynomial([float(TAU*solution.frequencies_hz[mode]*EPS0)]))
    return dict(electric=(er, ez), denominator=denominator, magnetic=multiply(r, u))


def bound_surface_peaks(solution, mode=0, *, relative_tolerance=1e-6, max_boxes_per_edge=10000):
    """Bound |E| and |Hphi| over every closed PEC edge, including one-sided corners.

    PASS means the represented discrete fields have bounded extrema. It does
    not certify physical surface peaks, corner regularity or mesh convergence.
    """
    sampler = CurvedSurfaceSampler(solution)
    indices = np.flatnonzero(solution.space.boundary_tags == 'pec')
    if not len(indices):
        raise ValueError('surface extrema require PEC edges')
    reports = {'electric_v_per_m': [], 'magnetic_a_per_m': []}
    for index in indices:
        edge = int(index)
        functions = edge_field_polynomials(sampler, edge, mode)
        for name, numerator, denominator in (
                ('electric_v_per_m', functions['electric'], functions['denominator']),
                ('magnetic_a_per_m', [functions['magnetic']], [1])):
            result = bound_rational_norm(numerator, denominator, relative_tolerance=relative_tolerance,
                                         max_boxes=max_boxes_per_edge)
            result['boundary_index'] = edge
            reports[name].append(result)
    maxima = {}
    for name, bounds in reports.items():
        best = max(bounds, key=lambda record: record['lower_bound'])
        maxima[name] = dict(lower_bound=best['lower_bound'], upper_bound=max(b['upper_bound'] for b in bounds),
                            boundary_index=best['boundary_index'], parameter=best['parameter'],
                            parameter_fraction=best['parameter_fraction'],
                            point_rz_m=sampler.evaluate(best['boundary_index'], [best['parameter']], mode)['points_rz_m'][0].tolist(),
                            boxes=sum(b['boxes'] for b in bounds))
    return dict(status='PASS', scope='continuous extrema of stored discrete fields; physical peaks not certified',
                corner_convention='all PEC edges closed; one-sided cell derivatives retained',
                relative_tolerance=relative_tolerance, pec_edges=len(indices), **maxima)
