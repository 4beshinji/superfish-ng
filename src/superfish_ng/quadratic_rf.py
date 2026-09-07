# SPDX-License-Identifier: Apache-2.0
"""P2 RF building blocks; full quantities/save integration remains N02 work."""
import numpy as np
from scipy.special import spherical_jn
from .constants import C0, EPS0, TAU


def quadratic_voltage(ends_z, values, wave_number, *, interval=None, phase_origin=0.):
    """Integrate quadratic edges times exp(i*k*(z-origin)) and absolute field.

    values columns are left endpoint, right endpoint, midpoint. Edges may be
    reversed; their physical orientation does not change the integral.
    Centered polynomial moments use x=P1(x), x²=(P0(x)+2P2(x))/3.
    """
    ends = np.asarray(ends_z, dtype=float)
    values = np.asarray(values, dtype=float)
    if ends.ndim != 2 or ends.shape[1] != 2 or values.shape != (len(ends), 3) or not len(ends):
        raise ValueError('quadratic voltage requires N by 2 endpoints and N by 3 field values')
    if not np.isfinite(ends).all() or not np.isfinite(values).all() or np.any(ends[:, 0] == ends[:, 1]):
        raise ValueError('quadratic voltage requires finite fields and nonzero edges')
    if not np.isfinite(wave_number) or not np.isfinite(phase_origin):
        raise ValueError('wave number and phase origin must be finite')
    ends, values = ends.copy(), values.copy()
    reverse = ends[:, 0] > ends[:, 1]
    ends[reverse] = ends[reverse, ::-1]
    values[reverse, :2] = values[reverse, 1::-1]
    order = np.argsort(ends[:, 0])
    ends, values = ends[order], values[order]
    if np.any(ends[1:, 0] != ends[:-1, 1]):
        raise ValueError('quadratic voltage edges must cover one continuous interval without overlap')
    a, b = (ends[0, 0], ends[-1, 1]) if interval is None else interval
    if not np.isfinite([a, b]).all() or not ends[0, 0] <= a < b <= ends[-1, 1]:
        raise ValueError('voltage interval must lie within the quadratic axis')
    voltage, absolute = 0j, 0.
    for (left, right), (fleft, fright, fmid) in zip(ends, values):
        lo, hi = max(a, left), min(b, right)
        if lo >= hi:
            continue
        center, half = (left+right)/2, (right-left)/2
        # f(x)=A+B*x+C*x² for x in [-1,1]. Recenter onto the clipped edge.
        A, B, C = fmid, (fright-fleft)/2, (fleft+fright)/2-fmid
        new_center, new_half = (lo+hi)/2, (hi-lo)/2
        shift, scale = (new_center-center)/half, new_half/half
        coeff = np.array([A+B*shift+C*shift**2, scale*(B+2*C*shift), C*scale**2])
        t = wave_number*new_half
        phase = wave_number*(new_center-phase_origin)
        if not np.isfinite(t) or not np.isfinite(phase):
            raise ValueError('voltage parameters produce an unrepresentable phase')
        j0, j1, j2 = spherical_jn(np.arange(3), abs(t))
        j1 *= np.sign(t)
        moments = np.array([2*j0, 2j*j1, 2*(j0-2*j2)/3])
        voltage += new_half*np.exp(1j*phase)*np.dot(coeff, moments)
        roots = np.polynomial.polynomial.polyroots(coeff)
        cuts = [-1.] + sorted(float(x.real) for x in roots if abs(x.imag) < 1e-12 and -1 < x.real < 1) + [1.]
        primitive = np.polynomial.polynomial.polyint(coeff)
        absolute += new_half*sum(abs(np.polynomial.polynomial.polyval(y, primitive)-np.polynomial.polynomial.polyval(x, primitive)) for x, y in zip(cuts[:-1], cuts[1:]))
    return complex(voltage), float(absolute)


def accelerating_voltage_p2(case, solution, mode=0):
    """Use original axis edges and all P2 coefficients under the R01 convention."""
    if solution.element_order != 2 or solution.space is None:
        raise ValueError('quadratic accelerating voltage requires a P2 solution')
    edges = solution.space.boundary_dofs[solution.mesh.boundary_tags == 'axis']
    z = solution.space.dof_points[edges[:, :2], 1]
    omega = TAU*solution.frequencies_hz[mode]
    field = 2*solution.u[edges, mode]/(omega*EPS0)
    _, interval, origin = case.acceleration_parameters
    return quadratic_voltage(z, field, omega/(case.beta*C0), interval=interval, phase_origin=origin)
