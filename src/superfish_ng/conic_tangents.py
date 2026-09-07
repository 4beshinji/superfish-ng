# SPDX-License-Identifier: Apache-2.0
"""Common tangent candidates of supporting conics; finite arcs are not filtered."""
from fractions import Fraction as F
import math
from .conics import EllipseArc, HyperbolaArc, rotation_cos_sin
from .rational_bounds import polynomial, add, multiply, _sqrt_bound
from .polynomial_roots import isolate_real_roots, _value


def _central(curve):
    if not isinstance(curve, (EllipseArc, HyperbolaArc)):
        raise ValueError('supporting conic tangents require ellipse or hyperbola primitives')
    c, s = map(F, rotation_cos_sin(curve.rotation_rad))
    a, b = (F(x)**2 for x in curve.semiaxes_m)
    if isinstance(curve, HyperbolaArc):
        b = -b
    return tuple(map(F, curve.center_zr_m)), ((a*c*c+b*s*s, (a-b)*c*s), ((a-b)*c*s, a*s*s+b*c*c))


def _quadratic(q, chart):
    return polynomial((q[0][0], 2*q[0][1], q[1][1]) if chart == 0 else (q[1][1], 2*q[0][1], q[0][0]))


def _range(p, a, b):
    lo = hi = F(0)
    for coefficient in reversed(p):
        products = (lo*a, lo*b, hi*a, hi*b)
        lo, hi = min(products)+coefficient, max(products)+coefficient
    return lo, hi


def _subtract(a, b):
    return add(a, tuple(-x for x in b))


def _contacts(centres, matrices, n, w, returned_normal):
    points = []
    residual = F(0)
    for c, q, offset in zip(centres, matrices, w):
        if offset == 0:
            raise ValueError('infinite or unresolved contact')
        v = tuple(sum(q[i][j]*n[j] for j in range(2)) for i in range(2))
        point = tuple(float(c[i]+v[i]/offset) for i in range(2))
        if not all(math.isfinite(x) for x in point):
            raise ValueError('contact exceeds floating-point range')
        # Recheck the actual returned float coordinates, including loss under translation.
        delta = tuple(F(point[i])-c[i] for i in range(2))
        determinant = q[0][0]*q[1][1]-q[0][1]**2
        implicit = (q[1][1]*delta[0]**2-2*q[0][1]*delta[0]*delta[1]+q[0][0]*delta[1]**2)/determinant
        incidence = abs(sum(n[i]*delta[i] for i in range(2))/offset-1)
        gradient = (q[1][1]*delta[0]-q[0][1]*delta[1], q[0][0]*delta[1]-q[0][1]*delta[0])
        denominator = sum(x*x for x in gradient)*sum(x*x for x in returned_normal)
        if denominator == 0:
            raise ValueError('returned contact has unresolved normal')
        cross = gradient[0]*returned_normal[1]-gradient[1]*returned_normal[0]
        angle = F(_sqrt_bound(cross*cross/denominator, upper=True))
        residual = max(residual, abs(implicit-1), incidence, angle)
        points.append(point)
    return points, float(residual)


def supporting_conic_tangents(first, second, *, normal_width=F(1, 2**44), max_boxes=10000, residual_tolerance=1e-10):
    """Enumerate finite tangent candidates of the whole central conics.

    PASS concerns the exact binary-coefficient normal polynomials and checked
    floating contact residuals, not finite-arc membership or a G1 connector.
    Both hyperbola branches participate. Unresolved roots/contacts remain visible.
    Chart 0 owns |nr/nz|<=1; chart 1 owns |nz/nr|<1, avoiding tolerance deduplication.
    """
    if type(residual_tolerance) not in (int, float) or not math.isfinite(residual_tolerance) or not 0 < residual_tolerance < 1:
        raise ValueError('residual_tolerance must be finite and between zero and one')
    # Validate root controls even when the elimination polynomial is identically zero.
    isolate_real_roots([1], -1, 1, absolute_width=normal_width, max_boxes=max_boxes)
    data = (_central(first), _central(second))
    centres, matrices = tuple(d[0] for d in data), tuple(d[1] for d in data)
    difference = tuple(centres[1][i]-centres[0][i] for i in range(2))
    candidates, unresolved, excluded, charts = [], [], [], []
    for chart in (0, 1):
        d = polynomial((difference[0], difference[1]) if chart == 0 else (difference[1], difference[0]))
        q1, q2 = (_quadratic(q, chart) for q in matrices)
        d2 = multiply(d, d)
        term = add(d2, _subtract(q1, q2))
        equation = _subtract(multiply(term, term), tuple(4*x for x in multiply(d2, q1)))
        if equation == (0,):
            unresolved.append(dict(chart=chart, reason='identically zero elimination polynomial; infinite or degenerate candidate family'))
            charts.append(dict(chart=chart, coefficients=equation, roots=None))
            continue
        roots = isolate_real_roots(equation, -1, 1, absolute_width=normal_width, max_boxes=max_boxes)
        charts.append(dict(chart=chart, coefficients=equation, roots=roots))
        for box in roots['unresolved']:
            unresolved.append(dict(chart=chart, interval=box[:2], root_count=box[2], reason='normal root isolation budget'))
        for lo, hi in roots['roots']:
            record = dict(chart=chart, normal_interval=(lo, hi))
            if chart == 1 and lo == hi and abs(lo) == 1:
                excluded.append(dict(**record, reason='boundary direction owned by chart 0'))
                continue
            t = (lo+hi)/2
            if len(d) == 2:
                zero = -d[0]/d[1]
                if (lo == hi == zero or lo < zero < hi) and _value(equation, zero) == 0:
                    t = zero
            exact = _value(equation, t) == 0
            record.update(normal_parameter=t, normal_parameter_is_exact_root=exact)
            n = (F(1), t) if chart == 0 else (t, F(1))
            D, a, b = (_value(p, t) for p in (d, q1, q2))
            if any(_range(q, lo, hi)[1] < 0 for q in (q1, q2)) or (exact and min(a,b) < 0):
                excluded.append(dict(**record, reason='no real contact on a supporting conic'))
                continue
            if exact and (a == 0 or b == 0):
                excluded.append(dict(**record, reason='contact at infinity; not a finite tangent segment'))
                continue
            if (not exact and any(_range(q,lo,hi)[0] <= 0 for q in (q1,q2))
                    or (D != 0 and _range(d,lo,hi)[0] <= 0 <= _range(d,lo,hi)[1])):
                unresolved.append(dict(**record, reason='normal interval does not separate a contact denominator from zero'))
                continue
            try:
                if D == 0:
                    root = F(_sqrt_bound(a, upper=False))
                    offsets = (root, -root)
                else:
                    offsets = ((D*D+a-b)/(2*D),)
                for w1 in offsets:
                    w2 = w1-D
                    norm = math.hypot(*map(float,n))
                    returned_normal = tuple(float(x)/norm for x in n)
                    returned_offset = float(w1/F(norm))
                    points, residual = _contacts(centres, matrices, n, (w1,w2), tuple(map(F,returned_normal)))
                    for point in points:
                        incidence = abs(sum(F(returned_normal[i])*(F(point[i])-centres[0][i]) for i in range(2))-F(returned_offset))/abs(w1/F(norm))
                        residual = max(residual, float(incidence))
                    if residual > residual_tolerance:
                        unresolved.append(dict(**record, reason='contact reconstruction residual', residual=residual))
                        continue
                    length = math.hypot(*(points[1][i]-points[0][i] for i in range(2)))
                    if not math.isfinite(length):
                        raise ValueError('contact distance exceeds floating-point range')
                    candidates.append(dict(**record, contacts_zr_m=points, normal_zr=returned_normal,
                                           origin_zr_m=tuple(map(float,centres[0])), offset_from_origin_m=returned_offset,
                                           contact_residual=residual, contact_distance_m=length,
                                           coincident_contacts_at_output_precision=points[0] == points[1]))
            except (ValueError, OverflowError) as error:
                unresolved.append(dict(**record, reason=str(error)))
    return dict(status='UNVERIFIED' if unresolved else 'PASS', candidates=candidates,
                unresolved=unresolved, excluded=excluded, charts=charts,
                arc_filter_status='NOT_APPLIED',
                scope='supporting conics with both hyperbola branches; binary-coefficient root isolation and floating contact residuals only')
