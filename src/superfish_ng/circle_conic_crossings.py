# SPDX-License-Identifier: Apache-2.0
"""Complete circular/noncircular offset intersections from rational charts.

Circle radius and rotation norm stay algebraic. Squared distance generates
candidates only; the original positive-root equation removes extraneous roots.
Finite source membership, cusp type and distinct centers are separate proofs.
"""
from fractions import Fraction as F
from .conics import EllipseArc, HyperbolaArc, rotation_cos_sin
from .rational_bounds import polynomial, add, multiply
from .algebraic_root_signs import RootSystem, AlgebraicRoot, scale, subtract
from .polynomial_roots import isolate_real_roots
from .quadratic_radicals import _sqrt_rational
from .certified_arcs import _arc_membership
from .contact_enclosures import _interval_add, _interval_divide
from .line_noncircular_crossings import _boxes, _same_center


def _dot(a, b):
    return add(multiply(a[0], b[0]), multiply(a[1], b[1]))


def _chart(curve, side, circle, distance, circle_distance):
    a, b = map(F, curve.semiaxes_m)
    c, s = map(F, rotation_cos_sin(curve.rotation_rad)); n = c*c+s*s
    ellipse = isinstance(curve, EllipseArc)
    H = polynomial((1, 0, 1 if ellipse else -1))
    X = polynomial((side, 0, -side if ellipse else side)); Y = polynomial((0, 2))
    local = scale(X, a), scale(Y, b)
    tangent = scale(Y, -a if ellipse else side*a), scale(X, b if ellipse else side*b)
    def rotate(v):
        return subtract(scale(v[0], c), scale(v[1], s)), add(scale(v[0], s), scale(v[1], c))
    U, V = rotate(local), rotate(tangent); JV = scale(V[1], -1), V[0]
    S = scale(_dot(tangent, tangent), n)
    W = tuple(add(u, scale(H, F(x)-F(y))) for u, x, y in zip(U, curve.center_zr_m, circle.center_zr_m))
    cc, cs = map(F, rotation_cos_sin(circle.rotation_rad)); k = cc*cc+cs*cs
    radius = F(circle.semiaxes_m[0]); HH = multiply(H, H)
    A = add(_dot(W, W), scale(HH, distance**2-radius**2*k-circle_distance**2))
    B = scale(multiply(H, _dot(W, JV)), 2*distance)
    K = scale(HH, 2*radius*circle_distance)
    E = subtract(multiply(add(multiply(A, A), scale(multiply(K, K), k)), S), multiply(B, B))
    G = scale(multiply(multiply(A, K), S), 2)
    circle_norm = _sqrt_rational(k, F(1, 2))
    if circle_distance == 0 or circle_norm[0] == circle_norm[1]:
        original = add(A, scale(K, circle_norm[0]))
        equation = subtract(multiply(multiply(original, original), S), multiply(B, B))
    else:
        equation = subtract(multiply(E, E), scale(multiply(G, G), k))
    return dict(side=side, H=H, source_local=(X, Y), local=local, tangent_local=tangent,
                U=U, V=V, JV=JV, S=S, W=W, A=A, B=B, K=K, E=E, G=G,
                circle_rotation=(cc, cs), circle_rotation_squared=k, rotation_squared=n,
                equation=equation, source_radial_derivative=_dot(W, V))


def _circle_local_box(root, chart, circle, distance, circle_distance, width):
    """Invert the signed circular radial map, preserving exact axis contacts."""
    c, s = chart['circle_rotation']; k = chart['circle_rotation_squared']
    radius = F(circle.semiaxes_m[0])
    rho_sign = root.radical_sign((-circle_distance,), (radius,), (k,))
    if rho_sign == 0:
        return None
    axes = ((c, s), (-s, c))
    numerators = []
    signs = []
    for axis in axes:
        a = add(scale(chart['W'][0], axis[0]), scale(chart['W'][1], axis[1]))
        b = scale(multiply(chart['H'], add(scale(chart['JV'][0], axis[0]), scale(chart['JV'][1], axis[1]))), distance)
        signs.append(root.radical_sign(b, a, chart['S'])*rho_sign)
        numerators.append((a, b))
    # Incidence proves the local point is on the unit circle. A zero component
    # therefore fixes the other component to exactly its certified sign.
    if 0 in signs:
        return tuple((F(sign), F(sign)) for sign in signs)
    norm = _sqrt_rational(k, width)
    denominator = tuple(radius*k-circle_distance*x for x in norm)
    denominator = min(denominator), max(denominator)
    if denominator[0] <= 0 <= denominator[1]:
        raise ValueError('signed circular radius enclosure is not separated')
    H = root.bounds(chart['H']); S = root.bounds(chart['S'])
    speed = _sqrt_rational(S[0], width)[0], _sqrt_rational(S[1], width)[1]
    result = []
    for a, b in numerators:
        numerator = _interval_add(root.bounds(a), _interval_divide(root.bounds(b), speed))
        result.append(_interval_divide(_interval_divide(numerator, H), denominator))
    return tuple(result)


def classify_circle_conic_crossings(curves, distances, domains, *, endpoint_width,
                                    max_series_terms, max_root_boxes=10000, max_refinements=512):
    """Private extension; validated public inputs use fixed recorded budgets."""
    circles = [isinstance(c, EllipseArc) and c.semiaxes_m[0] == c.semiaxes_m[1] for c in curves]
    if sum(circles) != 1 or not all(isinstance(c, (EllipseArc, HyperbolaArc)) for c in curves):
        return None
    if type(max_root_boxes) is not int or max_root_boxes < 1 or type(max_refinements) is not int or max_refinements < 1:
        raise ValueError('positive integer root and refinement budgets required')
    index = circles.index(True); circle, curve = curves[index], curves[1-index]
    ellipse = isinstance(curve, EllipseArc)
    start = F(curve.start_rad) if ellipse else F(curve.start_parameter)
    span = F(curve.sweep_rad) if ellipse else F(curve.end_parameter)-start
    distance = F(distances[1-index])*(1 if span > 0 else -1)
    circle_distance = F(distances[index])*(1 if circle.sweep_rad > 0 else -1)
    domains = [tuple(map(F, domain)) for domain in domains]
    width = F(endpoint_width)/256
    controls = dict(endpoint_width=endpoint_width, max_series_terms=max_series_terms)
    evidence = dict(identity='circle distance equation on rational conic charts with original positive-root signs',
                    circle_index=index, max_root_boxes=max_root_boxes, max_refinements=max_refinements,
                    charts=[], intersections=[], excluded=[], unresolved=[], same_center_groups=[])
    cc, cs = map(F, rotation_cos_sin(circle.rotation_rad))
    collapsed = circle_distance > 0 and circle_distance**2 == F(circle.semiaxes_m[0])**2*(cc*cc+cs*cs)
    included = []
    for side in ((1, -1) if ellipse else (curve.branch,)):
        chart = _chart(curve, side, circle, distance, circle_distance)
        record = dict(side=side, polynomial=chart['equation']); evidence['charts'].append(record)
        if chart['equation'] == (0,):
            evidence['unresolved'].append(dict(side=side, reason='identically zero elimination polynomial'))
            continue
        search = isolate_real_roots(chart['equation'], -1, 1, absolute_width=F(1, 2**24), max_boxes=max_root_boxes)
        record['isolation'] = search
        evidence['unresolved'].extend(dict(side=side, parameter_interval=(lo, hi), distinct_count=count,
            reason='Sturm isolation budget exhausted') for lo, hi, count in search['unresolved'])
        if not search['roots']:
            continue
        system = RootSystem(chart['equation'])
        for interval in search['roots']:
            row = dict(side=side, rational_parameter_interval=interval)
            root = AlgebraicRoot(system, interval, max_refinements=max_refinements)
            try:
                if interval in ((F(-1), F(-1)), (F(1), F(1))) and (not ellipse or side == -1):
                    evidence['excluded'].append(dict(row, reason='hyperbola infinity' if not ellipse else 'duplicate source at chart boundary'))
                    continue
                k = chart['circle_rotation_squared']
                squared_sign = root.radical_sign(chart['E'], chart['G'], (k,))
                first_sign = root.radical_sign(chart['A'], chart['K'], (k,)); second_sign = root.sign(chart['B'])
                row.update(squared_incidence_sign=squared_sign, original_side_signs=(first_sign, second_sign))
                if squared_sign != 0 or first_sign != -second_sign:
                    evidence['excluded'].append(dict(row, reason='extraneous root excluded by original positive-root incidence'))
                    continue
                a, b = map(F, curve.semiaxes_m)
                curvature = a*b*chart['rotation_squared']*(1 if ellipse else -curve.branch)
                numerator = scale(multiply(multiply(chart['H'], chart['H']), chart['H']), -distance*curvature)
                speed_sign = root.radical_sign(numerator, chart['S'], chart['S'])
                tangent_sign = root.sign(chart['source_radial_derivative'])
                root.narrow(width)
                local, center = _boxes(root, chart, curve, distance, width)
                circle_local = _circle_local_box(root, chart, circle, distance, circle_distance, width)
                is_collapsed = circle_local is None
                row.update(offset_speed_factor_sign=speed_sign, source_radial_derivative_sign=tangent_sign,
                    contact_kind='COLLAPSED_CIRCLE' if is_collapsed else 'CUSP' if speed_sign == 0 else
                    'REGULAR_TANGENCY' if tangent_sign == 0 else 'TRANSVERSE')
                memberships = [None, None]
                for i, c, box, endpoints in (
                    (1-index, curve, local, tuple(start+span*t for t in domains[1-index])),
                    (index, circle, circle_local, tuple(F(circle.start_rad)+F(circle.sweep_rad)*t for t in domains[index]))):
                    try:
                        memberships[i] = dict(status='COLLAPSED', fraction_interval=domains[i]) if box is None else _arc_membership(c, box, parameter_endpoints=endpoints, **controls)
                    except ValueError as error:
                        memberships[i] = dict(status='UNVERIFIED', reason=str(error))
                statuses = [m['status'] for m in memberships]
                present = False if 'EXTERIOR' in statuses else None if 'UNVERIFIED' in statuses else True
                row.update(source_local_box=local, circle_source_local_box=circle_local, center_box_zr_m=center,
                           membership=memberships, parameter_pair_in_domain=present)
                if present is None:
                    evidence['unresolved'].append(dict(row, reason='finite membership remains unresolved'))
                elif present:
                    included.append((root, chart, row)); evidence['intersections'].append(row)
                else:
                    evidence['excluded'].append(dict(row, reason='outside at least one finite domain'))
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
        evidence['unresolved'].append(dict(reason=str(error), stage='distinct center grouping'))
    complete = not evidence['unresolved']; count = len(groups)
    evidence.update(same_center_groups=groups, circle_collapsed=collapsed)
    return dict(classification=('INFINITE_PARAMETER_PAIRS' if collapsed and count else 'FINITE_CENTERS' if count else 'DISJOINT') if complete else 'UNVERIFIED',
                complete=complete, centers=count if complete else None,
                infinite=bool(collapsed and count) if complete else None, evidence=evidence,
                reason='all source roots, original incidence, finite memberships and distinct centers certified' if complete else
                'some chart roots, finite memberships or center identities remain unresolved')
