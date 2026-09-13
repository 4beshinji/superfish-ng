# SPDX-License-Identifier: Apache-2.0
"""All offset/source-conic intersections when one signed distance is zero."""
from fractions import Fraction as F
from .conics import EllipseArc, HyperbolaArc, rotation_cos_sin
from .rational_bounds import polynomial, add, multiply
from .algebraic_root_signs import AlgebraicRoot, RootSystem, scale, subtract
from .polynomial_roots import isolate_real_roots
from .certified_arcs import _arc_membership
from .contact_enclosures import _interval_add, _interval_divide
from .quadratic_radicals import _sqrt_rational
from .line_noncircular_crossings import _boxes, _same_center


def _dot(axis, vector):
    return add(scale(vector[0], axis[0]), scale(vector[1], axis[1]))


def _chart(curve, side, target, distance):
    a, b = map(F, curve.semiaxes_m); c, s = map(F, rotation_cos_sin(curve.rotation_rad))
    ellipse = isinstance(curve, EllipseArc); n = c*c+s*s
    H = polynomial((1, 0, 1 if ellipse else -1))
    X = polynomial((side, 0, -side if ellipse else side)); Y = polynomial((0, 2))
    local = scale(X, a), scale(Y, b)
    tangent = scale(Y, -a if ellipse else side*a), scale(X, b if ellipse else side*b)
    def rotate(v):
        return subtract(scale(v[0], c), scale(v[1], s)), add(scale(v[0], s), scale(v[1], c))
    U, V = rotate(local), rotate(tangent); JV = scale(V[1], -1), V[0]
    S = scale(add(multiply(tangent[0], tangent[0]), multiply(tangent[1], tangent[1])), n)
    W = tuple(add(u, scale(H, F(x)-F(y))) for u, x, y in zip(U, curve.center_zr_m, target.center_zr_m))
    ta, tb = map(F, target.semiaxes_m); tc, ts = map(F, rotation_cos_sin(target.rotation_rad))
    k = tc*tc+ts*ts; epsilon = 1 if isinstance(target, EllipseArc) else -1
    axes = (tc, ts), (-ts, tc)
    def bilinear(v, w):
        return add(scale(multiply(_dot(axes[0], v), _dot(axes[0], w)), tb*tb),
                   scale(multiply(_dot(axes[1], v), _dot(axes[1], w)), epsilon*ta*ta))
    HH = multiply(H, H)
    source_equation = subtract(bilinear(W, W), scale(HH, ta*ta*tb*tb*k*k))
    A = add(multiply(source_equation, S), scale(multiply(bilinear(JV, JV), HH), distance*distance))
    B = scale(multiply(bilinear(W, JV), H), 2*distance)
    equation = source_equation if distance == 0 else subtract(multiply(A, A), multiply(multiply(B, B), S))
    return dict(side=side, H=H, source_local=(X, Y), local=local, tangent_local=tangent, U=U, V=V, JV=JV,
                S=S, W=W, A=A, B=B, equation=equation, rotation_squared=n,
                target_axes=axes, target_denominators=(k*ta, k*tb),
                gradient_dot_rational=scale(multiply(H, bilinear(V, JV)), distance),
                gradient_dot_radical=bilinear(V, W))


def _target_local_box(root, chart, target, distance, width):
    projections = [(_dot(axis, chart['W']), scale(_dot(axis, chart['JV']), distance)) for axis in chart['target_axes']]
    signs = [root.radical_sign(multiply(chart['H'], b), a, chart['S']) for a, b in projections]
    # The original incidence is already proved. Exact axis coordinates give
    # exact conic vertices, avoiding a numerical near-endpoint decision.
    if isinstance(target, EllipseArc) and 0 in signs or isinstance(target, HyperbolaArc) and signs[1] == 0:
        return tuple((F(sign), F(sign)) for sign in signs)
    H, S = root.bounds(chart['H']), root.bounds(chart['S'])
    speed = _sqrt_rational(S[0], width)[0], _sqrt_rational(S[1], width)[1]
    result = []
    for (a, b), denominator in zip(projections, chart['target_denominators']):
        value = _interval_add(_interval_divide(root.bounds(a), H), _interval_divide(root.bounds(b), speed))
        result.append(tuple(x/denominator for x in value))
    return tuple(result)


def classify_conic_implicit_offset(curves, distances, domains, *, endpoint_width, max_series_terms,
                                   max_root_boxes=10000, max_refinements=512):
    """Private extension after public input validation; nonzero/nonzero returns None."""
    if not all(isinstance(c, (EllipseArc, HyperbolaArc)) and
               not (isinstance(c, EllipseArc) and c.semiaxes_m[0] == c.semiaxes_m[1]) for c in curves):
        return None
    if all(F(d) != 0 for d in distances):
        return None
    if type(max_root_boxes) is not int or max_root_boxes < 1 or type(max_refinements) is not int or max_refinements < 1:
        raise ValueError('positive integer root and refinement budgets required')
    target_index = 1 if F(distances[1]) == 0 else 0; source_index = 1-target_index
    target, curve = curves[target_index], curves[source_index]; ellipse = isinstance(curve, EllipseArc)
    start = F(curve.start_rad) if ellipse else F(curve.start_parameter)
    span = F(curve.sweep_rad) if ellipse else F(curve.end_parameter)-start
    distance = F(distances[source_index])*(1 if span > 0 else -1)
    domains = [tuple(map(F, d)) for d in domains]; width = F(endpoint_width)/256
    controls = dict(endpoint_width=endpoint_width, max_series_terms=max_series_terms)
    evidence = dict(identity='source conic quadratic form evaluated on a rational-chart normal offset',
                    source_index=source_index, target_index=target_index, max_root_boxes=max_root_boxes,
                    max_refinements=max_refinements, charts=[], intersections=[], excluded=[], unresolved=[], same_center_groups=[])
    included = []
    for side in ((1, -1) if ellipse else (curve.branch,)):
        chart = _chart(curve, side, target, distance); record = dict(side=side, polynomial=chart['equation'])
        evidence['charts'].append(record)
        if chart['equation'] == (0,):
            evidence['unresolved'].append(dict(side=side, reason='identically zero conic incidence polynomial; shared support needs finite-parameter classification'))
            continue
        search = isolate_real_roots(chart['equation'], -1, 1, absolute_width=F(1, 2**24), max_boxes=max_root_boxes)
        record['isolation'] = search
        evidence['unresolved'].extend(dict(side=side, parameter_interval=(lo, hi), distinct_count=count,
            reason='Sturm isolation budget exhausted') for lo, hi, count in search['unresolved'])
        if not search['roots']:
            continue
        system = RootSystem(chart['equation'])
        for interval in search['roots']:
            row = dict(side=side, rational_parameter_interval=interval); root = AlgebraicRoot(system, interval, max_refinements=max_refinements)
            try:
                if interval in ((F(-1), F(-1)), (F(1), F(1))) and (not ellipse or side == -1):
                    evidence['excluded'].append(dict(row, reason='hyperbola infinity' if not ellipse else 'duplicate source at chart boundary'))
                    continue
                incidence = root.radical_sign(chart['A'], chart['B'], chart['S'])
                row['original_incidence_sign'] = incidence
                if incidence != 0:
                    evidence['excluded'].append(dict(row, reason='extraneous squared root fails original positive-root incidence'))
                    continue
                a, b = map(F, curve.semiaxes_m)
                curvature = a*b*chart['rotation_squared']*(1 if ellipse else -curve.branch)
                numerator = scale(multiply(multiply(chart['H'], chart['H']), chart['H']), -distance*curvature)
                speed_sign = root.radical_sign(numerator, chart['S'], chart['S'])
                tangent_sign = root.radical_sign(chart['gradient_dot_rational'], chart['gradient_dot_radical'], chart['S'])
                row.update(offset_speed_factor_sign=speed_sign, source_gradient_dot_sign=tangent_sign,
                           contact_kind='CUSP' if speed_sign == 0 else 'REGULAR_TANGENCY' if tangent_sign == 0 else 'TRANSVERSE')
                root.narrow(width); local, center = _boxes(root, chart, curve, distance, width)
                target_local = _target_local_box(root, chart, target, distance, width)
                boxes = [None, None]; boxes[source_index], boxes[target_index] = local, target_local
                memberships = []
                for c, box, domain in zip(curves, boxes, domains):
                    begin = F(c.start_rad) if isinstance(c, EllipseArc) else F(c.start_parameter)
                    extent = F(c.sweep_rad) if isinstance(c, EllipseArc) else F(c.end_parameter)-begin
                    try:
                        memberships.append(_arc_membership(c, box, parameter_endpoints=tuple(begin+extent*t for t in domain), **controls))
                    except ValueError as error:
                        memberships.append(dict(status='UNVERIFIED', reason=str(error)))
                statuses = [m['status'] for m in memberships]
                present = False if 'EXTERIOR' in statuses else None if 'UNVERIFIED' in statuses else True
                row.update(source_local_box=local, target_source_local_box=target_local, center_box_zr_m=center,
                           membership=memberships, parameter_pair_in_domain=present)
                if present is None:
                    evidence['unresolved'].append(dict(row, reason='finite source/target membership remains unresolved'))
                elif present:
                    included.append((root, chart, row)); evidence['intersections'].append(row)
                else:
                    evidence['excluded'].append(dict(row, reason='outside at least one finite domain or target branch'))
            except ValueError as error:
                evidence['unresolved'].append(dict(row, reason=str(error)))
            finally:
                row.update(rational_parameter_interval=root.interval, refinements=root.refinements)
    groups = []
    try:
        for i, item in enumerate(included):
            for group in groups:
                if _same_center(item, included[group[0]], curve, distance):
                    group.append(i); break
            else:
                groups.append([i])
    except ValueError as error:
        evidence['unresolved'].append(dict(stage='distinct center grouping', reason=str(error)))
    evidence['same_center_groups'] = groups; complete = not evidence['unresolved']
    return dict(classification=('FINITE_CENTERS' if groups else 'DISJOINT') if complete else 'UNVERIFIED',
                complete=complete, centers=len(groups) if complete else None, infinite=False if complete else None, evidence=evidence,
                reason='all conic incidence roots, original signs, finite source pairs and distinct centers certified' if complete else
                'some incidence roots, finite memberships or center identities remain unresolved')
