# SPDX-License-Identifier: Apache-2.0
"""All line/noncircular offset intersections via rational charts and Sturm roots.

Squaring only generates candidates. Exact algebraic signs recover the original
positive square roots before finite membership or center counting. Distinct
source points at one center are grouped by the same-conic reflection theorem.
"""
from fractions import Fraction as F
from .conics import EllipseArc, HyperbolaArc, LineSegment, rotation_cos_sin
from .rational_bounds import polynomial, add, multiply
from .polynomial_roots import isolate_real_roots
from .algebraic_root_signs import RootSystem, AlgebraicRoot, scale, subtract
from .certified_arcs import _arc_membership, _multiply
from .contact_enclosures import _interval_add, _interval_divide
from .quadratic_radicals import _sqrt_rational


def _dot(vector, polynomials):
    result = (F(0),)
    for a, b in zip(vector, polynomials):
        result = add(result, scale(b, a))
    return result


def _chart(curve, side, line, distance, line_distance):
    a, b = map(F, curve.semiaxes_m)
    c, s = map(F, rotation_cos_sin(curve.rotation_rad))
    n = c*c+s*s
    ellipse = isinstance(curve, EllipseArc)
    H = polynomial((1, 0, 1 if ellipse else -1))
    X = polynomial((side, 0, -side if ellipse else side))
    Y = polynomial((0, 2))
    local = (scale(X, a), scale(Y, b))
    tangent_local = (scale(Y, -a if ellipse else side*a),
                     scale(X, b if ellipse else side*b))
    def rotate(vector):
        return subtract(scale(vector[0], c), scale(vector[1], s)), add(scale(vector[0], s), scale(vector[1], c))
    U, V = rotate(local), rotate(tangent_local)
    S = scale(add(multiply(tangent_local[0], tangent_local[0]), multiply(tangent_local[1], tangent_local[1])), n)
    JV = scale(V[1], -1), V[0]
    D = tuple(F(y)-F(x) for x, y in zip(line.start_zr_m, line.end_zr_m))
    N = -D[1], D[0]
    k = sum(x*x for x in D)
    delta = tuple(F(x)-F(y) for x, y in zip(curve.center_zr_m, line.start_zr_m))
    A = add(scale(H, sum(x*y for x, y in zip(N, delta))), _dot(N, U))
    B = scale(multiply(_dot(N, JV), H), distance)
    line_root = _sqrt_rational(k, F(1, 2))
    E = subtract(multiply(add(multiply(A, A), scale(multiply(H, H), line_distance**2*k)), S), multiply(B, B))
    G = scale(multiply(multiply(A, H), S), -2*line_distance)
    if line_distance == 0 or line_root[0] == line_root[1]:
        original_rational = subtract(A, scale(H, line_distance*line_root[0]))
        equation = subtract(multiply(multiply(original_rational, original_rational), S), multiply(B, B))
    else:
        equation = subtract(multiply(E, E), scale(multiply(G, G), k))
    return dict(side=side, H=H, source_local=(X, Y), local=local, tangent_local=tangent_local,
                U=U, V=V, JV=JV, S=S, A=A, B=B, E=E, G=G, equation=equation,
                k=k, D=D, N=N, delta=delta, rotation_squared=n)


def _boxes(root, chart, curve, distance, width):
    while True:
        H, S = root.bounds(chart['H']), root.bounds(chart['S'])
        if H[0] > 0 and S[0] > 0:
            break
        root.refine()
    speed = (_sqrt_rational(S[0], width)[0], _sqrt_rational(S[1], width)[1])
    local = tuple(_interval_divide(root.bounds(p), H) for p in chart['source_local'])
    point = []
    for center, u, v in zip(curve.center_zr_m, chart['U'], chart['JV']):
        displacement = _interval_add(_interval_divide(root.bounds(u), H),
                                     _interval_divide(root.bounds(scale(v, distance)), speed))
        point.append((F(center)+displacement[0], F(center)+displacement[1]))
    return local, tuple(point)


def _line_membership(root, chart, distance, domain):
    signs = []
    for endpoint in domain:
        projection = sum(x*y for x, y in zip(chart['D'], chart['delta']))-chart['k']*endpoint
        a = add(scale(chart['H'], projection), _dot(chart['D'], chart['U']))
        b = scale(multiply(_dot(chart['D'], chart['JV']), chart['H']), distance)
        signs.append(root.radical_sign(b, a, chart['S']))
    status = ('EXTERIOR' if signs[0] < 0 or signs[1] > 0 else
              'START' if signs[0] == 0 else 'END' if signs[1] == 0 else 'INTERIOR')
    return dict(status=status, endpoint_difference_signs=signs)


def _same_center(first, second, curve, distance):
    root, chart, row = first
    other, other_chart, other_row = second
    if any(a[1] < b[0] or b[1] < a[0] for a, b in zip(row['center_box_zr_m'], other_row['center_box_zr_m'])):
        return False
    if isinstance(curve, EllipseArc) and curve.semiaxes_m[0] == curve.semiaxes_m[1]:
        # A noncollapsed circular offset is an injective radial scaling. A
        # collapsed circle gives an identically zero polynomial when incident.
        return False
    # Exhaustive same-source-conic self-contact reflection alternatives. Chart
    # boundary duplicates have already been removed, so equal roots are absent.
    same_half = chart['side'] == other_chart['side']
    reflection = -1 if same_half else 1
    axis = 1 if same_half else 0
    if not root.equals_transformed(other, reflection):
        return False
    tangent = chart['tangent_local']
    normal = (scale(tangent[1], -1), tangent[0])
    constant = scale(multiply(normal[axis], chart['H']), distance)
    return root.radical_sign(constant, chart['local'][axis], chart['S']) == 0


def classify_line_noncircular_crossings(curves, distances, domains, *, endpoint_width,
                                        max_series_terms, max_root_boxes=10000, max_refinements=512,
                                        include_circles=False):
    """Private extension; the public diagnosis validates curves and controls.

    The fixed public algebraic budgets are recorded in evidence. Exhaustion or
    unresolved membership preserves every unfinished chart/root and no total.
    """
    if sum(isinstance(c, LineSegment) for c in curves) != 1:
        return None
    index = 0 if isinstance(curves[0], LineSegment) else 1
    line, curve = curves[index], curves[1-index]
    if not isinstance(curve, (EllipseArc, HyperbolaArc)):
        return None
    ellipse = isinstance(curve, EllipseArc)
    if type(include_circles) is not bool:
        raise ValueError('include_circles must be an explicit boolean')
    if ellipse and curve.semiaxes_m[0] == curve.semiaxes_m[1] and not include_circles:
        return None
    if type(max_root_boxes) is not int or max_root_boxes < 1 or type(max_refinements) is not int or max_refinements < 1:
        raise ValueError('positive integer root and refinement budgets required')
    start = F(curve.start_rad) if ellipse else F(curve.start_parameter)
    span = F(curve.sweep_rad) if ellipse else F(curve.end_parameter)-start
    distance = F(distances[1-index])*(1 if span > 0 else -1)
    line_distance = F(distances[index])
    line_domain, arc_domain = [tuple(map(F, domains[i])) for i in (index, 1-index)]
    width = F(endpoint_width)/256
    evidence = dict(identity='rational conic charts, exhaustive Sturm roots and unsquared offset incidence',
                    line_index=index, max_root_boxes=max_root_boxes, max_refinements=max_refinements,
                    charts=[], intersections=[], excluded=[], unresolved=[], same_center_groups=[])
    included = []
    for side in ((1, -1) if ellipse else (curve.branch,)):
        chart = _chart(curve, side, line, distance, line_distance)
        record = dict(side=side, polynomial=chart['equation'])
        evidence['charts'].append(record)
        if chart['equation'] == (0,):
            evidence['unresolved'].append(dict(side=side, reason='identically zero elimination polynomial'))
            continue
        search = isolate_real_roots(chart['equation'], -1, 1, absolute_width=F(1, 2**24), max_boxes=max_root_boxes)
        record['isolation'] = search
        evidence['unresolved'].extend(dict(side=side, parameter_interval=(lo, hi), distinct_count=n,
                                           reason='Sturm isolation budget exhausted') for lo, hi, n in search['unresolved'])
        if not search['roots']:
            continue
        system = RootSystem(chart['equation'])
        for interval in search['roots']:
            row = dict(side=side, rational_parameter_interval=interval)
            root = AlgebraicRoot(system, interval, max_refinements=max_refinements)
            try:
                if interval in ((F(-1), F(-1)), (F(1), F(1))) and (not ellipse or side == -1):
                    row['reason'] = 'hyperbola infinity' if not ellipse else 'duplicate source at chart boundary'
                    evidence['excluded'].append(row)
                    continue
                norm_sign = root.radical_sign(chart['E'], chart['G'], (chart['k'],))
                first_sign = root.radical_sign(chart['A'], scale(chart['H'], -line_distance), (chart['k'],))
                second_sign = root.sign(chart['B'])
                row.update(squared_incidence_sign=norm_sign, original_side_signs=(first_sign, second_sign))
                if norm_sign != 0 or first_sign != -second_sign:
                    row['reason'] = 'extraneous root excluded by original positive-root incidence'
                    evidence['excluded'].append(row)
                    continue
                a, b = map(F, curve.semiaxes_m)
                curvature = a*b*chart['rotation_squared']*(1 if ellipse else -curve.branch)
                numerator = scale(multiply(multiply(chart['H'], chart['H']), chart['H']), -distance*curvature)
                speed_sign = root.radical_sign(numerator, chart['S'], chart['S'])
                tangent_sign = root.sign(_dot(chart['N'], chart['V']))
                row.update(offset_speed_factor_sign=speed_sign, source_projection_derivative_sign=tangent_sign,
                           contact_kind='CUSP' if speed_sign == 0 else 'REGULAR_TANGENCY' if tangent_sign == 0 else 'TRANSVERSE')
                line_membership = _line_membership(root, chart, distance, line_domain)
                root.narrow(width)
                local, center = _boxes(root, chart, curve, distance, width)
                try:
                    arc_membership = _arc_membership(curve, local, endpoint_width=endpoint_width,
                        max_series_terms=max_series_terms, parameter_endpoints=tuple(start+span*t for t in arc_domain))
                except ValueError as error:
                    arc_membership = dict(status='UNVERIFIED', reason=str(error))
                memberships = [None, None]
                memberships[index], memberships[1-index] = line_membership, arc_membership
                statuses = [r['status'] for r in memberships]
                present = False if 'EXTERIOR' in statuses else None if 'UNVERIFIED' in statuses else True
                row.update(source_local_box=local, center_box_zr_m=center, membership=memberships,
                           parameter_pair_in_domain=present)
                if present is None:
                    evidence['unresolved'].append(dict(row, reason='finite membership remains unresolved'))
                elif present:
                    included.append((root, chart, row))
                    evidence['intersections'].append(row)
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
                    group.append(i)
                    break
            else:
                groups.append([i])
    except ValueError as error:
        evidence['unresolved'].append(dict(reason=str(error), stage='distinct center grouping'))
    evidence['same_center_groups'] = groups
    complete = not evidence['unresolved']
    return dict(classification=('FINITE_CENTERS' if groups else 'DISJOINT') if complete else 'UNVERIFIED',
                complete=complete, centers=len(groups) if complete else None, infinite=False if complete else None,
                evidence=evidence, reason='all chart roots, original incidence, finite membership and distinct centers certified' if complete
                else 'some chart roots, memberships or center identities remain unresolved')
