# SPDX-License-Identifier: Apache-2.0
"""Exact projection polynomial for intersections of two normal conic offsets.

The discriminant of a conic/circle pencil is a necessary contact condition.
Substitution of the first offset and a radical norm yields every possible
source parameter, including extra roots. This module does not certify target
source points, finite target membership, or complete intersections.
"""
from fractions import Fraction as F

from .conics import EllipseArc, HyperbolaArc, rotation_cos_sin
from .certified_arcs import _number, _arc_membership, DEFAULT_ENDPOINT_WIDTH, transcendental_interval
from .conic_implicit_offset import _chart
from .rational_bounds import add, multiply
from .algebraic_root_signs import scale, subtract
from .polynomial_roots import _divide
from .primitive_polynomial_roots import (primitive_polynomial, isolate_primitive_real_roots,
                                         PrimitiveRootSystem, PrimitiveAlgebraicRoot)
from .line_noncircular_crossings import _boxes


def _discriminant_numerator(first, second, constant, cubic, denominator, radicand):
    """D^4 disc(c0 + (E1/D)t + (E2/D)t² + c3 t³), in Q[q,sqrt(S)]."""
    def product(left, right):
        a, b = left; c, d = right
        return (add(multiply(a, c), multiply(radicand, multiply(b, d))),
                add(multiply(a, d), multiply(b, c)))

    def times(element, rational, coefficient):
        return tuple(scale(multiply(p, rational), coefficient) for p in element)

    first_square, second_square = product(first, first), product(second, second)
    dd = multiply(denominator, denominator)
    terms = (product(first_square, second_square),
             times(product(second_square, second), denominator, -4*constant),
             times(product(first_square, first), denominator, -4*cubic),
             (scale(multiply(dd, dd), -27*constant**2*cubic**2), (F(0),)),
             times(product(first, second), dd, 18*constant*cubic))
    rational = radical = (F(0),)
    for a, b in terms:
        rational, radical = add(rational, a), add(radical, b)
    return rational, radical


def conic_offset_projection(first, second, *, first_distance_m, second_distance_m, side):
    """Build one exact source-chart projection for two nonzero signed offsets.

    Distances follow each original curve's traversal. ``side`` selects one of
    the ellipse's two half-angle charts, or the hyperbola's declared branch.
    The valid chart interior has H>0 and S>0. Its endpoints need separate chart
    duplicate/infinity handling when roots are used. An identically zero
    equation is left explicit, never interpreted as a finite root list.
    """
    if not all(isinstance(c, (EllipseArc, HyperbolaArc)) for c in (first, second)):
        raise ValueError('conic offset projection requires two ellipse or hyperbola arcs')
    if type(side) is not int or side not in ((-1, 1) if isinstance(first, EllipseArc) else (first.branch,)):
        raise ValueError('source chart side must be ±1 for an ellipse or the declared hyperbola branch')
    d, e = (_number(value, name) for value, name in
            ((first_distance_m, 'first_distance_m'), (second_distance_m, 'second_distance_m')))
    if d == 0 or e == 0:
        raise ValueError('this projection requires two nonzero offset distances; use the source-conic incidence path for zero distance')
    span = F(first.sweep_rad) if isinstance(first, EllipseArc) else F(first.end_parameter)-F(first.start_parameter)
    oriented_distance = d*(1 if span > 0 else -1)
    chart = _chart(first, side, second, oriented_distance)
    h, s, w, normal = (chart[key] for key in ('H', 'S', 'W', 'JV'))
    hh = multiply(h, h); denominator = multiply(hh, s)
    a, b = map(F, second.semiaxes_m)
    cosine, sine = map(F, rotation_cos_sin(second.rotation_rad)); norm = cosine*cosine+sine*sine
    epsilon = 1 if isinstance(second, EllipseArc) else -1
    axis_sum = b*b+epsilon*a*a
    distance_rational = multiply(s, add(add(multiply(w[0], w[0]), multiply(w[1], w[1])),
                                       scale(hh, oriented_distance**2)))
    distance_radical = scale(multiply(h, add(multiply(w[0], normal[0]), multiply(w[1], normal[1]))),
                              2*oriented_distance)
    # With w=P-C_target, the pencil determinant multiplied by a²b² is
    # c0 + c1*t + c2*t² + c3*t³, where c1,c2 contain only quadratic forms.
    constant = F(-epsilon)
    cubic = -norm*norm*e*e*a*a*b*b
    first_coefficient = (subtract(scale(distance_rational, epsilon),
                                  scale(denominator, epsilon*e*e+norm*axis_sum)),
                         scale(distance_radical, epsilon))
    second_coefficient = (subtract(chart['A'], scale(denominator, norm*e*e*axis_sum)), chart['B'])
    rational, radical = _discriminant_numerator(first_coefficient, second_coefficient, constant, cubic,
                                               denominator, s)
    removed = []
    if rational != (0,) or radical != (0,):
        # Only exact common factors known positive in the real chart interior
        # are removed. A factor at a possible real source root is never dropped.
        for name, factor in (('H', h), ('S', s)):
            count = 0
            while True:
                left, left_remainder = _divide(rational, factor)
                right, right_remainder = _divide(radical, factor)
                if left_remainder != (0,) or right_remainder != (0,):
                    break
                rational, radical = left, right; count += 1
            if count:
                removed.append(dict(name=name, polynomial=factor, power=count))
    equation = primitive_polynomial(subtract(multiply(rational, rational), multiply(s, multiply(radical, radical))))
    return dict(source_chart=chart, source_oriented_distance=oriented_distance, target_signed_distance=e,
                pencil_constant=constant, pencil_cubic=cubic, pencil_linear_numerator=first_coefficient,
                pencil_quadratic_numerator=second_coefficient, positive_denominator=denominator,
                discriminant_rational=rational, discriminant_radical=radical, removed_positive_factors=removed,
                equation=equation, identically_zero=equation == (0,), degree=None if equation == (0,) else len(equation)-1,
                scope='necessary source projection only; radical conjugates, target sign, real target sources and finite target membership remain to be checked')


def project_conic_offset_candidates(first, second, *, first_distance_m, second_distance_m,
                                    first_interval=(0., 1.), endpoint_width=DEFAULT_ENDPOINT_WIDTH,
                                    max_series_terms=96, max_root_boxes=10000, max_refinements=512):
    """Enumerate every finite source candidate, without asserting target incidence.

    ``projection_complete`` refers to the pencil-discriminant projection after
    the original source radical sign and source finite membership are checked.
    The target distance sign, target real parameters and finite target arc are
    still unclassified.
    """
    return _project_conic_offset_candidates(first, second, first_distance_m=first_distance_m,
        second_distance_m=second_distance_m, first_interval=first_interval, endpoint_width=endpoint_width,
        max_series_terms=max_series_terms, max_root_boxes=max_root_boxes, max_refinements=max_refinements)


def _project_conic_offset_candidates(first, second, *, first_distance_m, second_distance_m,
                                     first_interval=(0., 1.), endpoint_width=DEFAULT_ENDPOINT_WIDTH,
                                     max_series_terms=96, max_root_boxes=10000, max_refinements=512,
                                     candidate_handler=None):
    """Reuse isolated roots for target recovery without rebuilding Sturm systems.

    A handler owns target failures; they must not erase proved source candidates.
    The public projection-only entry point installs no handler.
    """
    if not isinstance(first_interval, (tuple, list)) or len(first_interval) != 2:
        raise ValueError('source fraction interval requires a pair')
    domain = tuple(_number(x, 'source fraction interval') for x in first_interval)
    if not 0 <= domain[0] < domain[1] <= 1:
        raise ValueError('source fraction interval must increase within [0,1]')
    for value in (max_root_boxes, max_refinements):
        if type(value) is not int or value < 1:
            raise ValueError('positive integer root and refinement budgets required')
    width = _number(endpoint_width, 'endpoint_width')
    transcendental_interval('sin', 0, endpoint_width=width, max_terms=max_series_terms)
    # Validate the curve kinds and both signed distances before reading fields.
    side = 1 if isinstance(first, EllipseArc) else first.branch if isinstance(first, HyperbolaArc) else 1
    first_projection = conic_offset_projection(first, second, first_distance_m=first_distance_m,
                                               second_distance_m=second_distance_m, side=side)
    ellipse = isinstance(first, EllipseArc)
    start = F(first.start_rad) if ellipse else F(first.start_parameter)
    span = F(first.sweep_rad) if ellipse else F(first.end_parameter)-start
    endpoints = tuple(start+span*fraction for fraction in domain)
    result = dict(projection_complete=False, source_candidates=[], excluded=[], unresolved=[], charts=[],
                  source_interval=domain, target_incidence_certified=False,
                  controls=dict(endpoint_width=width, max_series_terms=max_series_terms,
                                max_root_boxes=max_root_boxes, max_refinements=max_refinements),
                  scope='all source projection candidates when complete; not a finite target intersection classification or fillet construction')
    for side in ((1, -1) if ellipse else (first.branch,)):
        projection = first_projection if side == (1 if ellipse else first.branch) else conic_offset_projection(
            first, second, first_distance_m=first_distance_m, second_distance_m=second_distance_m, side=side)
        result['charts'].append(projection)
        if projection['identically_zero']:
            result['unresolved'].append(dict(side=side, reason='identically zero projection; target recovery or shared-support classification required'))
            continue
        system = PrimitiveRootSystem(projection['equation']) if len(projection['equation']) > 1 else None
        search = (system.isolate(-1, 1, absolute_width=F(1, 2**24), max_boxes=max_root_boxes) if system is not None else
                  isolate_primitive_real_roots(projection['equation'], -1, 1, absolute_width=F(1, 2**24), max_boxes=max_root_boxes))
        projection['isolation'] = search
        result['unresolved'].extend(dict(side=side, parameter_interval=(lo, hi), distinct_count=count,
                                         reason='projection root isolation budget exhausted') for lo, hi, count in search['unresolved'])
        if not search['roots']:
            continue
        chart = projection['source_chart']
        for interval in search['roots']:
            row = dict(side=side, rational_parameter_interval=interval)
            root = PrimitiveAlgebraicRoot(system, interval, max_refinements=max_refinements)
            try:
                if interval in ((F(-1), F(-1)), (F(1), F(1))) and (not ellipse or side == -1):
                    result['excluded'].append(dict(row, reason='hyperbola infinity' if not ellipse else 'duplicate ellipse chart endpoint'))
                    continue
                sign = root.radical_sign(projection['discriminant_rational'], projection['discriminant_radical'], chart['S'])
                row['original_pencil_discriminant_sign'] = sign
                if sign != 0:
                    result['excluded'].append(dict(row, reason='opposite source radical fails original pencil discriminant'))
                    continue
                a, b = map(F, first.semiaxes_m)
                curvature = a*b*chart['rotation_squared']*(1 if ellipse else -first.branch)
                distance = projection['source_oriented_distance']
                speed = root.radical_sign(scale(multiply(multiply(chart['H'], chart['H']), chart['H']), -distance*curvature),
                                         chart['S'], chart['S'])
                root.narrow(width/256); local, center = _boxes(root, chart, first, distance, width/256)
                membership = _arc_membership(first, local, parameter_endpoints=endpoints,
                                              endpoint_width=width, max_series_terms=max_series_terms)
                row.update(source_local_box=local, center_box_zr_m=center, source_membership=membership,
                           source_offset_speed_factor_sign=speed, source_regularity='CUSP' if speed == 0 else 'REGULAR')
                if membership['status'] == 'UNVERIFIED':
                    result['unresolved'].append(dict(row, reason='finite source membership unresolved'))
                elif membership['status'] == 'EXTERIOR':
                    result['excluded'].append(dict(row, reason='outside finite source domain'))
                else:
                    if candidate_handler is not None:
                        candidate_handler(root, projection, row)
                    result['source_candidates'].append(row)
            except ValueError as error:
                result['unresolved'].append(dict(row, reason=str(error)))
            finally:
                row.update(rational_parameter_interval=root.interval, refinements=root.refinements)
    result['projection_complete'] = not result['unresolved']
    return result
