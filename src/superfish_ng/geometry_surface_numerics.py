# SPDX-License-Identifier: Apache-2.0
"""Independent geometry diagnostics and same-field quadrature/interval gates.

The Decimal reference reuses this project's published validators' AGM/Taylor
arithmetic and interpolation remainder. It never generates a FEM eigenpair.
See docs/N01_GEOMETRY_SURFACE_CASES.md and the original validation scripts.
"""
from dataclasses import replace
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import math
import numpy as np

from .config import keys
from .conics import LineSegment, EllipseArc
from .constants import MU0
from .curved_fem import assemble_curved
from .curved_rf import quantities_curved
from .fem import triangle_quadrature
from .surface_convergence import LIMITS, _interval_change, _outward_float, _ratio_interval


def _decimal(value):
    value = F(value)
    return D(value.numerator)/D(value.denominator)


def _pi():
    # Identical reference arithmetic to validate_coincident_circle_arcs.py.
    a, b, t, p = D(1), D(1)/D(2).sqrt(), D(1)/4, D(1)
    for _ in range(9):
        following = (a+b)/2; b = (a*b).sqrt()
        t -= p*(a-following)**2; a = following; p *= 2
    return (a+b)**2/(4*t)


def ellipsoid_moments(axial_semiaxis_m, radial_semiaxis_m):
    with localcontext() as context:
        context.prec = 140
        a, b, pi = _decimal(axial_semiaxis_m), _decimal(radial_semiaxis_m), _pi()
        return float(pi*a*b/2), float(4*pi*a*b*b/3)


def _sine_cosine(angle):
    # Identical reference series to validate_general_coincident_circle_arcs.py.
    sine, cosine, st, ct = angle, D(1), angle, D(1)
    for index in range(1, 180):
        st *= -angle*angle/D(2*index*(2*index+1))
        ct *= -angle*angle/D((2*index-1)*2*index)
        sine += st; cosine += ct
        if max(abs(st), abs(ct)) < D('1e-130'):
            return sine, cosine
    raise ValueError('independent boundary trigonometric reference did not converge')


def _point(curve, fraction):
    f = _decimal(fraction)
    if isinstance(curve, LineSegment):
        a, b = [tuple(map(_decimal, p)) for p in (curve.start_zr_m, curve.end_zr_m)]
        return tuple(x+f*(y-x) for x, y in zip(a, b))
    if not isinstance(curve, EllipseArc) or curve.rotation_rad != 0.:
        raise ValueError('independent surface boundary reference supports lines and unrotated ellipse/circle arcs only')
    t = _decimal(curve.start_rad)+_decimal(curve.sweep_rad)*f
    sine, cosine = _sine_cosine(t)
    a, b = map(_decimal, curve.semiaxes_m); z, r = map(_decimal, curve.center_zr_m)
    return z+a*cosine, r+b*sine


def boundary_error(space, contour):
    """Whole-edge interpolation remainder plus high-precision node error.

    Fixed FEM subdivisions inherit quadratic curves: evaluate the ancestral
    coarse space, not fine points that were never projected to analytic curves.
    """
    rows = []
    with localcontext() as context:
        context.prec = 140
        for nodes, owner, (low, high) in zip(space.geometry.boundary_nodes,
                space.geometry.boundary_curve_indices, space.geometry.boundary_parameters):
            curve = contour.curves[int(owner)]; lo, hi = _decimal(float(low)), _decimal(float(high))
            exact = [_point(curve, F(f))[::-1] for f in (lo, hi, (lo+hi)/2)]
            stored = [tuple(map(_decimal, space.geometry.points_rz_m[n])) for n in nodes]
            node_error = max(sum((x-y)**2 for x, y in zip(a, b)).sqrt() for a, b in zip(exact, stored))
            interpolation = (max(map(_decimal, curve.semiaxes_m))*abs(_decimal(curve.sweep_rad)*(hi-lo))**3/(72*D(3).sqrt())
                             if isinstance(curve, EllipseArc) else D(0))
            bound = interpolation+D(5)/4*node_error; sampled = D(0)
            for x in (D('.25'), D('.75')):
                weights = (2*x-1)*(x-1), x*(2*x-1), 4*x*(1-x)
                point = [sum(w*p[k] for w, p in zip(weights, stored)) for k in (0, 1)]
                exact = _point(curve, F(lo+x*(hi-lo)))[::-1]
                error = sum((p-q)**2 for p, q in zip(point, exact)).sqrt()
                sampled = max(sampled, error)
                if error > bound+D('1e-120'):
                    raise ValueError('independent sampled boundary error exceeds interpolation remainder')
            upper = _outward_float(F(bound), upper=True)
            if upper is None:
                raise ValueError('independent boundary upper bound is not representable')
            rows.append(dict(curve_index=int(owner), source_fractions=[float(low), float(high)],
                             node_error_m=float(node_error), interpolation_bound_m=float(interpolation),
                             boundary_error_bound_m=upper, sampled_error_m=float(sampled)))
    if not rows:
        raise ValueError('boundary reference requires every native boundary edge')
    return dict(maximum_boundary_error_bound_m=max(r['boundary_error_bound_m'] for r in rows),
                maximum_sampled_error_m=max(r['sampled_error_m'] for r in rows), edges=rows,
                scope='analytic quadratic interpolation remainder plus 140-digit node-rounding reference; no electromagnetic error bound')


def mapped_moments(space):
    # Same independent mapped polynomial integration as the geometry validator.
    rule = list(triangle_quadrature(order=6))
    coordinates = [b[1:] for b, _ in rule]; weights = np.array([w for _, w in rule])
    areas, volumes = [], []
    for mapping in space.geometry.local_maps:
        data = mapping.evaluate(coordinates); measure = weights*data['determinant_m2']
        areas.append(float(measure.sum()))
        volumes.append(float(2*math.pi*(measure*data['points_rz_m'][:, 0]).sum()))
    return math.fsum(areas), math.fsum(volumes)


def quantity_intervals(q):
    """Never promote estimates, zero Eacc or unknown discrete peaks to intervals."""
    result = {n: [q[n], q[n]] for n in ('frequency_hz', 'r_over_q_accelerator_ohm', 'geometry_factor_ohm')}
    result.update(epk_over_eacc=None, bpk_over_eacc_mt_per_mv_per_m=None)
    names = ('epk_discrete_lower_bound_v_per_m', 'epk_discrete_upper_bound_v_per_m',
             'hpk_discrete_lower_bound_a_per_m', 'hpk_discrete_upper_bound_a_per_m')
    if (all(n in q for n in names) and q.get('epk_over_eacc_estimate') is not None
            and q.get('bpk_over_eacc_estimate_mt_per_mv_per_m') is not None and q['eacc_v_per_m'] > 0):
        result['epk_over_eacc'] = _ratio_interval(q[names[0]], q[names[1]], q['eacc_v_per_m'])
        result['bpk_over_eacc_mt_per_mv_per_m'] = _ratio_interval(q[names[2]], q[names[3]],
                                                               q['eacc_v_per_m'], factor=F(MU0)*10**9)
    return result


def _valid_interval(value):
    return (type(value) is list and len(value) == 2 and
            all(type(v) in (int, float) and math.isfinite(v) and v > 0 for v in value) and value[0] <= value[1])


def quantity_changes(previous, current, *, finite_peak_required=True):
    keys(previous, tuple(LIMITS), tuple(LIMITS), 'previous quantity intervals')
    keys(current, tuple(LIMITS), tuple(LIMITS), 'current quantity intervals')
    if type(finite_peak_required) is not bool:
        raise ValueError('finite_peak_required must be boolean')
    required = tuple(LIMITS) if finite_peak_required else tuple(LIMITS)[:3]
    changes = {n: _interval_change(previous[n], current[n]) if _valid_interval(previous[n]) and _valid_interval(current[n]) else None for n in required}
    gates = {n: v is not None and v <= LIMITS[n] for n, v in changes.items()}
    status = 'UNVERIFIED' if any(v is None for v in changes.values()) else 'TARGETS_MET' if all(gates.values()) else 'NOT_CONVERGED'
    return dict(status=status, relative_changes=changes, gates=gates,
                finite_peak_required=finite_peak_required,
                excluded_quantities=[] if finite_peak_required else list(LIMITS)[3:])


def quadrature_check(solution, mode):
    """12/16/24 and wall8/16 on unchanged coefficients/frequency; no eigsolve."""
    if solution.case.quadrature_order != 12:
        raise ValueError('separated surface quadrature requires the original order 12 native field')
    if type(mode) is not int or not 0 <= mode < len(solution.frequencies_hz):
        raise ValueError('quadrature target must be an identified zero-based mode')
    u = solution.u[:, mode].copy(); u /= np.max(np.abs(u))
    rows = []
    for order in (12, 16, 24):
        k, m = (solution.stiffness, solution.mass) if order == 12 else assemble_curved(solution.space, quadrature_order=order)
        stiffness, mass = float(u@(k@u)), float(u@(m@u))
        high = replace(solution, stiffness=k, mass=m, quadrature_order=order)
        rf = {str(w): quantities_curved(high, mode, wall_quadrature_order=w, include_surface_peaks=False) for w in (8, 16)}
        rows.append(dict(order=order, normalized_field_stiffness=stiffness, normalized_field_mass=mass,
                         rayleigh_frequency_hz=float(solution.frequencies_hz[mode])*math.sqrt((stiffness/mass)/(rows[0]['normalized_field_stiffness']/rows[0]['normalized_field_mass'])) if rows else float(solution.frequencies_hz[mode]),
                         rf_by_wall_order=rf))
    comparisons = []
    for a, b in zip(rows, rows[1:]):
        differences = dict(rayleigh_frequency=abs(math.sqrt((b['normalized_field_stiffness']/b['normalized_field_mass'])/(a['normalized_field_stiffness']/a['normalized_field_mass']))-1),
                           mass=abs(b['normalized_field_mass']/a['normalized_field_mass']-1),
                           stiffness=abs(b['normalized_field_stiffness']/a['normalized_field_stiffness']-1))
        for wall in ('8', '16'):
            for n in ('stored_energy_j', 'r_over_q_accelerator_ohm', 'geometry_factor_ohm'):
                x, y = a['rf_by_wall_order'][wall][n], b['rf_by_wall_order'][wall][n]
                differences[f'{n}_wall_{wall}'] = abs(y/x-1) if x > 0 else None
        comparisons.append(dict(previous_order=a['order'], current_order=b['order'], relative_differences=differences,
                                passed=all(v is not None and math.isfinite(v) and v < 1e-8 for v in differences.values())))
    walls = []
    for row in rows:
        a, b = row['rf_by_wall_order']['8'], row['rf_by_wall_order']['16']
        differences = {n: abs(b[n]/a[n]-1) for n in ('wall_loss_w', 'geometry_factor_ohm')}
        walls.append(dict(volume_order=row['order'], relative_differences=differences,
                          passed=all(math.isfinite(v) and v < 1e-8 for v in differences.values())))
    # Preserve the exact old three-metric criterion as its own diagnostic.
    old_differences = dict(rayleigh_frequency=comparisons[0]['relative_differences']['rayleigh_frequency'],
                           mass=comparisons[0]['relative_differences']['mass'],
                           geometry_factor_wall_integral=walls[0]['relative_differences']['geometry_factor_ohm'])
    old = dict(passed=max(old_differences.values()) < 1e-8, relative_differences=old_differences,
               base_order=12, high_order=16, tolerance=1e-8)
    resolved = all(v is not None for c in comparisons for v in c['relative_differences'].values())
    passed = all(c['passed'] for c in comparisons+walls)
    return dict(status='UNVERIFIED' if not resolved else 'PASS' if passed else 'FAIL',
                rows=rows, volume_comparisons=comparisons, wall_comparisons=walls,
                legacy_comparison=old, tolerance=1e-8, new_eigensolves=0,
                scope='same saved coefficients, frequency and represented geometry; no eigensolve, normalization rescaling or surface-peak/quadrature-error guarantee')
