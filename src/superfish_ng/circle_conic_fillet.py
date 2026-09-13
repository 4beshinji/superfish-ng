# SPDX-License-Identifier: Apache-2.0
"""Version 8 fillets from all circular/noncircular algebraic source pairs."""
from fractions import Fraction as F
from .conics import EllipseArc, HyperbolaArc, curve_from_dict, rotation_cos_sin
from .certified_arcs import _number, _multiply, _parameter_fraction_enclosure, transcendental_interval, DEFAULT_ENDPOINT_WIDTH
from .circle_conic_crossings import classify_circle_conic_crossings
from .conic_fillet import _fillet_setup, _fillets_from_search
from .normal_offsets import add, scale


def _tangent_box(curve, local):
    x, y = local; a, b = map(F, curve.semiaxes_m)
    if isinstance(curve, EllipseArc):
        tangent = scale(y, -a), scale(x, b)
        direction = 1 if curve.sweep_rad > 0 else -1
    else:
        tangent = scale(y, curve.branch*a), scale(x, curve.branch*b)
        direction = 1 if curve.end_parameter > curve.start_parameter else -1
    c, s = map(F, rotation_cos_sin(curve.rotation_rad))
    return (scale(add(scale(tangent[0], c), scale(tangent[1], -s)), direction),
            scale(add(scale(tangent[0], s), scale(tangent[1], c)), direction))


def _coincident_contacts(curves, boxes, row, distances):
    if distances[0] != distances[1]:
        return None
    if distances[0] == 0:
        return True
    if row['source_radial_derivative_sign'] != 0:
        return False
    # At a regular source tangency, equal signed normal distances imply equal
    # contacts iff the original directed tangents agree. Offset speed reversal
    # and negative circular radius do not change this source-tangent criterion.
    first, second = [_tangent_box(c, box) for c, box in zip(curves, boxes)]
    dot = add(_multiply(first[0], second[0]), _multiply(first[1], second[1]))
    return True if dot[0] > 0 else False if dot[1] < 0 else None


def intersect_algebraic_circle_conic_offsets(first, second, *, first_distance_m, second_distance_m,
                                             first_interval=(0., 1.), second_interval=(0., 1.),
                                             fraction_width=F(1, 2**40), max_root_boxes=10000,
                                             max_refinements=512, max_fraction_steps=128,
                                             endpoint_width=DEFAULT_ENDPOINT_WIDTH, max_series_terms=96):
    curves = first, second
    circles = [isinstance(c, EllipseArc) and c.semiaxes_m[0] == c.semiaxes_m[1] for c in curves]
    if sum(circles) != 1 or not all(isinstance(c, (EllipseArc, HyperbolaArc)) for c in curves):
        raise ValueError('circle/conic fillet requires one circle and one noncircular ellipse or hyperbola arc')
    circle_index = circles.index(True)
    distances = tuple(_number(x, 'distance_m') for x in (first_distance_m, second_distance_m))
    width = _number(fraction_width, 'fraction_width')
    if not 0 < width < 1:
        raise ValueError('fraction_width must be between zero and one')
    for name, value in (('max_root_boxes', max_root_boxes), ('max_refinements', max_refinements), ('max_fraction_steps', max_fraction_steps)):
        if type(value) is not int or value < 1:
            raise ValueError(f'{name} must be a positive integer')
    transcendental_interval('sin', 0, endpoint_width=endpoint_width, max_terms=max_series_terms)
    domains = []
    for interval in (first_interval, second_interval):
        if not isinstance(interval, (tuple, list)) or len(interval) != 2:
            raise ValueError('fraction interval requires a pair')
        low, high = (_number(t, 'fraction interval') for t in interval)
        if not 0 <= low < high <= 1:
            raise ValueError('circle/conic fraction interval must increase within [0,1]')
        domains.append((low, high))
    controls = dict(first_distance_m=distances[0], second_distance_m=distances[1], fraction_width=width,
                    max_root_boxes=max_root_boxes, max_refinements=max_refinements, max_fraction_steps=max_fraction_steps,
                    endpoint_width=F(endpoint_width), max_series_terms=max_series_terms)
    classified = classify_circle_conic_crossings(curves, distances, domains, endpoint_width=endpoint_width,
        max_series_terms=max_series_terms, max_root_boxes=max_root_boxes, max_refinements=max_refinements)
    report = dict(status='UNVERIFIED', roots=[], unresolved=list(classified['evidence']['unresolved']),
                  domain_box=tuple(domains), controls=controls, algebraic_intersections=classified,
                  method='circular/noncircular algebraic intersections with certified source-fraction order',
                  scope='complete finite source pairs and lexicographic traversal order when PASS; no output geometry or FEM accuracy assertion')
    if classified['evidence']['circle_collapsed']:
        if classified['complete'] and classified['centers'] == 0:
            report['status'] = 'PASS'
        else:
            report['unresolved'].append(dict(stage='collapsed_circle', reason='collapsed circle has infinitely many source parameters or unresolved finite incidence; no finite candidate-index list'))
        return report
    group_of = {i: group for group, indices in enumerate(classified['evidence']['same_center_groups']) for i in indices}
    for index, row in enumerate(classified['evidence']['intersections']):
        boxes = [None, None]; boxes[circle_index], boxes[1-circle_index] = row['circle_source_local_box'], row['source_local_box']
        try:
            fractions = [_parameter_fraction_enclosure(curve, box, fraction_width=width, max_fraction_steps=max_fraction_steps,
                endpoint_width=endpoint_width, max_series_terms=max_series_terms) for curve, box in zip(curves, boxes)]
            if any(f['status'] != 'PASS' for f in fractions):
                report['unresolved'].append(dict(stage='source_fraction', source_root_index=index, evidence=fractions))
                continue
            coincident = _coincident_contacts(curves, boxes, row, distances)
            if distances[0] == distances[1] and coincident is None:
                raise ValueError('parallel source tangent orientation remains unresolved')
            report['roots'].append(dict(parameter_box=tuple(f['interval'] for f in fractions), center_box_zr_m=row['center_box_zr_m'],
                center_group=group_of[index], source_root_index=index, source_contact_kind=row['contact_kind'], source_contacts_coincide=coincident,
                certificate=dict(kind='ALGEBRAIC_CIRCLE_CONIC_SOURCE_PAIR', source_root_index=index, source_fractions=fractions)))
        except ValueError as error:
            report['unresolved'].append(dict(stage='source_fraction', source_root_index=index, reason=str(error)))
    # A noncollapsed circle is injective on the allowed finite arc. Shared
    # centers therefore share its one source fraction, while the conic may
    # contribute several distinct source points.
    for group in set(r['center_group'] for r in report['roots']):
        rows = [r for r in report['roots'] if r['center_group'] == group]
        interval = max(r['parameter_box'][circle_index][0] for r in rows), min(r['parameter_box'][circle_index][1] for r in rows)
        if interval[0] > interval[1]:
            raise RuntimeError('certified same-center circular fractions have disjoint enclosures')
        for row in rows:
            box = list(row['parameter_box']); box[circle_index] = interval; row['parameter_box'] = tuple(box)
    report['roots'].sort(key=lambda r: tuple(sum(t)/2 for t in r['parameter_box']))
    for left, right in zip(report['roots'], report['roots'][1:]):
        coordinate = 1 if circle_index == 0 and left['center_group'] == right['center_group'] else 0
        if left['parameter_box'][coordinate][1] >= right['parameter_box'][coordinate][0]:
            report['unresolved'].append(dict(stage='candidate_order', source_root_indices=(left['source_root_index'], right['source_root_index']),
                reason='lexicographic candidate order is not separated at the requested fraction precision'))
    if classified['complete'] and not report['unresolved']:
        report['status'] = 'PASS'
    return report


def circle_conic_fillet_candidates(first, second, *, radius_m, turn_direction, max_sweep_rad,
                                   position_tolerance_m, angle_tolerance_rad, fraction_width=F(1, 2**40),
                                   max_root_boxes=10000, max_refinements=512, max_fraction_steps=128,
                                   endpoint_width=DEFAULT_ENDPOINT_WIDTH, max_series_terms=96):
    common = dict(radius_m=radius_m, turn_direction=turn_direction, max_sweep_rad=max_sweep_rad,
                  position_tolerance_m=position_tolerance_m, angle_tolerance_rad=angle_tolerance_rad,
                  allow_extension=False, endpoint_width=endpoint_width, max_series_terms=max_series_terms)
    distance, _ = _fillet_setup(first, second, **common)
    search = intersect_algebraic_circle_conic_offsets(first, second, first_distance_m=distance, second_distance_m=distance,
        fraction_width=fraction_width, max_root_boxes=max_root_boxes, max_refinements=max_refinements,
        max_fraction_steps=max_fraction_steps, endpoint_width=endpoint_width, max_series_terms=max_series_terms)
    report = _fillets_from_search(first, second, search, retain_whole_at_endpoint=True, **common)
    report['arc_filter_status'] = 'ALGEBRAIC_CIRCLE_CONIC_FILLET_CONTACTS'
    report['scope'] = 'all finite circular/noncircular source pairs with certified order; nonempty retained endpoints; bounded output contact errors; explicit radius/turn/sweep; floating G1; closed contour checked separately'
    return report


def connect_circle_conic_fillet(first, second, *, candidate_index, **controls):
    if type(candidate_index) is not int or candidate_index < 0:
        raise ValueError('candidate_index must be an explicit nonnegative integer')
    report = circle_conic_fillet_candidates(first, second, **controls)
    if report['status'] != 'PASS':
        raise ValueError('circle/conic source-pair enumeration or order is UNVERIFIED; inspect unresolved evidence')
    if candidate_index >= len(report['candidates']):
        raise ValueError('candidate_index is outside the circle/conic fillet list')
    selected = report['candidates'][candidate_index]
    if selected['connection_direction'] != 'FORWARD':
        raise ValueError(selected.get('construction_reason', 'fillet is not usable'))
    return dict(curves=tuple(curve_from_dict(row) for row in selected['trimmed_curves']),
                selected_candidate=selected, joins=selected['joins'], enumeration=report)
