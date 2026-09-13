# SPDX-License-Identifier: Apache-2.0
"""Complete line/conic source-parameter pairs for explicit fillet construction.

Every source pair remains a separate root, including pairs sharing a center.
Candidate order is certified lexicographically in original traversal fractions.
"""
from fractions import Fraction as F
from .conics import EllipseArc, HyperbolaArc, LineSegment, rotation_cos_sin
from .certified_arcs import _number, _parameter_fraction_enclosure, transcendental_interval, DEFAULT_ENDPOINT_WIDTH
from .line_noncircular_crossings import classify_line_noncircular_crossings
from .normal_offsets import add, scale
from .offset_degeneracies import _classify_offset_degeneracies_v6


def _coincident_source_contacts(arc, line, row, distances):
    if distances[0] != distances[1]:
        return None
    if distances[0] == 0:
        return True
    if row['source_projection_derivative_sign'] != 0:
        return False
    # Equal signed offsets and equally directed parallel tangents give equal
    # original contacts. Opposite tangents give contacts separated by 2|d|.
    x, y = row['source_local_box']; a, b = map(F, arc.semiaxes_m)
    if isinstance(arc, EllipseArc):
        tangent = scale(y, -a), scale(x, b)
        direction = 1 if arc.sweep_rad > 0 else -1
    else:
        tangent = scale(y, arc.branch*a), scale(x, arc.branch*b)
        direction = 1 if arc.end_parameter > arc.start_parameter else -1
    c, s = map(F, rotation_cos_sin(arc.rotation_rad))
    rotated = add(scale(tangent[0], c), scale(tangent[1], -s)), add(scale(tangent[0], s), scale(tangent[1], c))
    dot = (F(0), F(0))
    for box, start, end in zip(rotated, line.start_zr_m, line.end_zr_m):
        dot = add(dot, scale(box, direction*(F(end)-F(start))))
    return True if dot[0] > 0 else False if dot[1] < 0 else None


def intersect_algebraic_line_offsets(first, second, *, first_distance_m, second_distance_m,
                                    first_interval=(0., 1.), second_interval=(0., 1.),
                                    fraction_width=F(1, 2**40), max_root_boxes=10000,
                                    max_refinements=512, max_fraction_steps=128,
                                    endpoint_width=DEFAULT_ENDPOINT_WIDTH, max_series_terms=96):
    curves = first, second
    if sum(isinstance(c, LineSegment) for c in curves) != 1 or sum(isinstance(c, (EllipseArc, HyperbolaArc)) for c in curves) != 1:
        raise ValueError('algebraic fillet requires one line and one ellipse or hyperbola arc')
    line_index = 0 if isinstance(first, LineSegment) else 1
    line, arc = curves[line_index], curves[1-line_index]
    distances = tuple(_number(x, 'distance_m') for x in (first_distance_m, second_distance_m))
    width = _number(fraction_width, 'fraction_width')
    if not 0 < width < 1:
        raise ValueError('fraction_width must be between zero and one')
    for name, value in (('max_root_boxes', max_root_boxes), ('max_refinements', max_refinements), ('max_fraction_steps', max_fraction_steps)):
        if type(value) is not int or value < 1:
            raise ValueError(f'{name} must be a positive integer')
    transcendental_interval('sin', 0, endpoint_width=endpoint_width, max_terms=max_series_terms)
    domain = []
    for curve, interval in zip(curves, (first_interval, second_interval)):
        if not isinstance(interval, (list, tuple)) or len(interval) != 2:
            raise ValueError('fraction interval requires a pair')
        lo, hi = (_number(x, 'fraction interval') for x in interval)
        if lo >= hi or not isinstance(curve, LineSegment) and not 0 <= lo < hi <= 1:
            raise ValueError('fraction interval must increase; conic fractions must be in [0,1]')
        domain.append((lo, hi))
    controls = dict(first_distance_m=distances[0], second_distance_m=distances[1], fraction_width=width,
                    max_root_boxes=max_root_boxes, max_refinements=max_refinements, max_fraction_steps=max_fraction_steps,
                    endpoint_width=F(endpoint_width), max_series_terms=max_series_terms)
    report = dict(status='UNVERIFIED', roots=[], unresolved=[], domain_box=tuple(domain), controls=controls,
                  method='rational conic charts and certified traversal fractions',
                  scope='complete source-parameter pair enumeration and certified lexicographic order when PASS; no output fillet or FEM accuracy assertion')
    if isinstance(arc, EllipseArc) and arc.semiaxes_m[0] == arc.semiaxes_m[1]:
        c, s = map(F, rotation_cos_sin(arc.rotation_rad))
        distance = distances[1-line_index]*(1 if arc.sweep_rad > 0 else -1)
        if distance > 0 and distance**2 == F(arc.semiaxes_m[0])**2*(c*c+s*s):
            diagnosis = _classify_offset_degeneracies_v6(*curves, first_distance_m=distances[0], second_distance_m=distances[1],
                first_interval=domain[0], second_interval=domain[1], endpoint_width=endpoint_width, max_series_terms=max_series_terms)
            report['collapsed_circle_diagnosis'] = diagnosis
            if diagnosis['finite_domain_complete'] and diagnosis['finite_center_count'] == 0:
                report['status'] = 'PASS'
            else:
                report['unresolved'].append(dict(stage='collapsed_circle', reason='collapsed circle offset has a continuum of source parameters or unresolved line membership; choose another radius or primitive'))
            return report
    classified = classify_line_noncircular_crossings(curves, distances, domain, endpoint_width=endpoint_width,
        max_series_terms=max_series_terms, max_root_boxes=max_root_boxes, max_refinements=max_refinements, include_circles=True)
    report['algebraic_intersections'] = classified
    report['unresolved'].extend(classified['evidence']['unresolved'])
    group_of = {i: group for group, indices in enumerate(classified['evidence']['same_center_groups']) for i in indices}
    delta = tuple(F(b)-F(a) for a, b in zip(line.start_zr_m, line.end_zr_m))
    squared = sum(x*x for x in delta)
    for index, row in enumerate(classified['evidence']['intersections']):
        try:
            fraction = _parameter_fraction_enclosure(arc, row['source_local_box'], fraction_width=width,
                max_fraction_steps=max_fraction_steps, endpoint_width=endpoint_width, max_series_terms=max_series_terms)
            if fraction['status'] != 'PASS':
                report['unresolved'].append(dict(stage='arc_fraction', source_root_index=index, evidence=fraction))
                continue
            projected = (F(0), F(0))
            for box, origin, direction in zip(row['center_box_zr_m'], line.start_zr_m, delta):
                projected = add(projected, scale((box[0]-F(origin), box[1]-F(origin)), direction/squared))
            status = row['membership'][line_index]['status']
            if status in ('START', 'END'):
                value = domain[line_index][0 if status == 'START' else 1]
                projected = value, value
            else:
                projected = max(projected[0], domain[line_index][0]), min(projected[1], domain[line_index][1])
            if projected[0] > projected[1] or projected[1]-projected[0] > width:
                raise ValueError('line fraction enclosure does not meet the requested width')
            coincident = _coincident_source_contacts(arc, line, row, distances)
            if distances[0] == distances[1] and coincident is None:
                raise ValueError('parallel source tangent orientation remains unresolved')
            box = [None, None]; box[line_index], box[1-line_index] = projected, fraction['interval']
            report['roots'].append(dict(parameter_box=tuple(box), center_box_zr_m=row['center_box_zr_m'],
                center_group=group_of.get(index), source_root_index=index, source_contact_kind=row['contact_kind'],
                source_contacts_coincide=coincident,
                certificate=dict(kind='ALGEBRAIC_SOURCE_PARAMETER_PAIR', source_root_index=index, arc_fraction=fraction)))
        except ValueError as error:
            report['unresolved'].append(dict(stage='parameter_fraction', source_root_index=index, reason=str(error)))
    # A shared center has one exact line fraction. Intersect its enclosures so
    # all corresponding source pairs use the same first-coordinate sort key.
    for group in set(r['center_group'] for r in report['roots'])-{None}:
        rows = [r for r in report['roots'] if r['center_group'] == group]
        interval = max(r['parameter_box'][line_index][0] for r in rows), min(r['parameter_box'][line_index][1] for r in rows)
        if interval[0] > interval[1]:
            raise RuntimeError('certified same-center line fractions have disjoint enclosures')
        for row in rows:
            box = list(row['parameter_box']); box[line_index] = interval; row['parameter_box'] = tuple(box)
    report['roots'].sort(key=lambda r: tuple(sum(t)/2 for t in r['parameter_box']))
    for left, right in zip(report['roots'], report['roots'][1:]):
        same_first = line_index == 0 and left['center_group'] is not None and left['center_group'] == right['center_group']
        coordinate = 1 if same_first else 0
        if left['parameter_box'][coordinate][1] >= right['parameter_box'][coordinate][0]:
            report['unresolved'].append(dict(stage='candidate_order', source_root_indices=(left['source_root_index'], right['source_root_index']),
                                             reason='lexicographic candidate order is not separated at the requested fraction precision'))
    if classified['complete'] and not report['unresolved']:
        report['status'] = 'PASS'
    return report
