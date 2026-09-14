# SPDX-License-Identifier: Apache-2.0
"""Version 10 fillets from all finite noncircular conic-offset source pairs."""
from fractions import Fraction as F

from .conics import EllipseArc, HyperbolaArc, curve_from_dict
from .certified_arcs import _number, _multiply, _parameter_fraction_enclosure, transcendental_interval, DEFAULT_ENDPOINT_WIDTH
from .conic_offset_intersections import classify_conic_offset_intersections
from .equal_distance_conic_branches import classify_equal_distance_conic_branches
from .reparameterized_conic_offsets import classify_reparameterized_conic_offsets
from .same_conic_offset_intersections import _same_endpoint_as_contact
from .quadratic_radicals import _sqrt_rational
from .normal_offsets import add, scale, normal_offset_bounds
from .circle_conic_fillet import _tangent_box
from .conic_fillet import _fillet_setup, _fillets_from_search


def _parameters(curve):
    return ((F(curve.start_rad), F(curve.sweep_rad)) if isinstance(curve, EllipseArc) else
            (F(curve.start_parameter), F(curve.end_parameter)-F(curve.start_parameter)))


def _contacts_coincide(curves, boxes, parallel, distances):
    if abs(distances[0]) != abs(distances[1]) or not parallel:
        return False
    first, second = [_tangent_box(curve, box) for curve, box in zip(curves, boxes)]
    dot = add(_multiply(first[0], second[0]), _multiply(first[1], second[1]))
    if dot[0] > 0:
        return distances[0] == distances[1]
    if dot[1] < 0:
        return distances[0] == -distances[1]
    raise ValueError('parallel original tangent directions remain unresolved')


def _shared_support_pairs(curves, distances, classified, *, endpoint_width, max_series_terms):
    """Expand equal-point endpoints and every directed reflected contact pair."""
    first, second = curves; evidence = classified['evidence']; mapping = evidence['support_map']
    diagonal = evidence['diagonal']; endpoints = diagonal['shared_endpoints']
    rows, unresolved = [], []
    controls = dict(endpoint_width=endpoint_width, max_terms=max_series_terms)
    for index, parameter in enumerate(endpoints):
        # An exact shared endpoint has zero symbolic pi shift; the hyperbola's
        # original parameter can also be reflected by the principal-frame map.
        parameters = parameter, mapping['parameter_orientation']*parameter
        fractions = tuple((t-start)/span for curve, t in zip(curves, parameters) for start, span in (_parameters(curve),))
        try:
            center = normal_offset_bounds(first, fractions[0], fractions[0], distance_m=distances[0],
                endpoint_width=endpoint_width, max_series_terms=max_series_terms)['center_box_zr_m']
            rows.append(dict(center_box_zr_m=center, exact_parameter_box=tuple((f, f) for f in fractions),
                source_parameter_identity=('shared_endpoint', index), center_identity=('shared_endpoint', index),
                contact_kind='SHARED_SUPPORT_ENDPOINT', source_contacts_coincide=True,
                certificate=dict(kind='NONCIRCULAR_SHARED_SUPPORT_ENDPOINT', first_original_parameter=parameter)))
        except ValueError as error:
            unresolved.append(dict(stage='shared_endpoint', endpoint_index=index, reason=str(error)))
    a, b = map(F, first.semiaxes_m); n = mapping['first_rotation_square']; ellipse = isinstance(first, EllipseArc)
    curvature = a*b*n*(1 if ellipse else -first.branch)
    oriented_distance = evidence['oriented_distances'][0]
    for index, contact in enumerate(evidence['self_contacts']):
        q = contact['parameter_square']
        speed_squared = n*(a*a*q+b*b*(1-q if ellipse else 1+q))
        curvature_product = oriented_distance*curvature
        difference = speed_squared**3-curvature_product**2
        speed_sign = 1 if curvature_product <= 0 else (difference > 0)-(difference < 0)
        parallel = ellipse and q in (0, 1)
        kind = 'CUSP' if speed_sign == 0 else 'REGULAR_TANGENCY' if parallel else 'TRANSVERSE'
        coordinate = scale(_sqrt_rational(contact['coordinate_square'], F(endpoint_width)/256/max(F(1), contact['coordinate_square'])),
                           contact['coordinate_factor'])
        c, s = mapping['first_rotation']; direction = (c, s) if contact['axis'] == 0 else (-s, c)
        center = tuple(tuple(F(origin)+x for x in scale(coordinate, coefficient)) for origin, coefficient in zip(first.center_zr_m, direction))
        duplicates = contact.get('duplicates_shared_endpoint', [])
        center_key = ('shared_endpoint', duplicates.index(True)) if True in duplicates else ('self_contact', index)
        for left, right in contact['included_parameter_pairs']:
            boxes = (contact['contacts_in_original_frames'][0][left], contact['contacts_in_original_frames'][1][right])
            source_key = ('self_contact', index, left)
            for endpoint_index, parameter in enumerate(endpoints):
                try:
                    same = _same_endpoint_as_contact(first, parameter, (boxes[0],), controls)
                    if same:
                        source_key = ('shared_endpoint', endpoint_index)
                    elif same is None:
                        raise ValueError('shared endpoint and reflected first source identity remain unresolved')
                except ValueError as error:
                    unresolved.append(dict(stage='source_identity', contact_index=index, first_point_index=left, reason=str(error)))
            rows.append(dict(source_local_box=boxes[0], target_local_box=boxes[1], center_box_zr_m=center,
                source_parameter_identity=source_key, center_identity=center_key, source_contacts_coincide=False,
                contact_kind=kind, tangent_parallel=parallel,
                certificate=dict(kind='NONCIRCULAR_REFLECTED_SOURCE_PAIR', contact_index=index,
                                 directed_point_indices=(left, right), offset_speed_factor_sign=speed_sign)))
    return rows, unresolved


def intersect_algebraic_noncircular_offsets(first, second, *, first_distance_m, second_distance_m,
                                             first_interval=(0., 1.), second_interval=(0., 1.),
                                             fraction_width=F(1, 2**40), max_root_boxes=10000,
                                             max_refinements=512, max_fraction_steps=128,
                                             endpoint_width=DEFAULT_ENDPOINT_WIDTH, max_series_terms=96):
    curves = first, second
    if not all(isinstance(c, (EllipseArc, HyperbolaArc)) and not (
            isinstance(c, EllipseArc) and c.semiaxes_m[0] == c.semiaxes_m[1]) for c in curves):
        raise ValueError('noncircular conic fillet requires two noncircular ellipse or hyperbola arcs')
    distances = tuple(_number(x, 'distance_m') for x in (first_distance_m, second_distance_m))
    if 0 in distances:
        raise ValueError('noncircular fillet source pairs require two nonzero normal distances; use conic implicit-offset diagnosis for zero distance')
    width = _number(fraction_width, 'fraction_width')
    if not 0 < width < 1:
        raise ValueError('fraction_width must be between zero and one')
    for name, value in (('max_root_boxes', max_root_boxes), ('max_refinements', max_refinements), ('max_fraction_steps', max_fraction_steps)):
        if type(value) is not int or value < 1:
            raise ValueError(f'{name} must be a positive integer')
    endpoint_width = _number(endpoint_width, 'endpoint_width')
    transcendental_interval('sin', 0, endpoint_width=endpoint_width, max_terms=max_series_terms)
    domains = []
    for interval in (first_interval, second_interval):
        if not isinstance(interval, (tuple, list)) or len(interval) != 2:
            raise ValueError('fraction interval requires a pair')
        low, high = (_number(x, 'fraction interval') for x in interval)
        if not 0 <= low < high <= 1:
            raise ValueError('noncircular conic fraction interval must increase within [0,1]')
        domains.append((low, high))
    common = dict(endpoint_width=endpoint_width, max_series_terms=max_series_terms)
    classified = classify_reparameterized_conic_offsets(curves, distances, domains, **common)
    shared = classified is not None
    if not shared:
        classified = classify_equal_distance_conic_branches(curves, distances, domains, **common)
    if classified is None:
        classified = classify_conic_offset_intersections(curves, distances, domains, max_root_boxes=max_root_boxes,
                                                         max_refinements=max_refinements, **common)
    report = dict(status='UNVERIFIED', roots=[], unresolved=list(classified['evidence']['unresolved']),
                  domain_box=tuple(domains), algebraic_intersections=classified,
                  controls=dict(first_distance_m=distances[0], second_distance_m=distances[1], fraction_width=width,
                                max_root_boxes=max_root_boxes, max_refinements=max_refinements, max_fraction_steps=max_fraction_steps, **common),
                  method='all finite noncircular source pairs with certified original traversal order',
                  scope='complete finite source pairs and lexicographic order when PASS; output geometry and FEM accuracy are separate')
    if classified['infinite']:
        report['unresolved'].append(dict(stage='infinite_source_pairs', reason='overlapping equal offsets have infinitely many source parameters; restrict the finite domains before choosing a candidate index'))
        return report
    if not classified['complete']:
        report['unresolved'].append(dict(stage='intersection_classification', reason=classified['reason']))
    if shared:
        pairs, unresolved = _shared_support_pairs(curves, distances, classified, **common)
        report['unresolved'].extend(unresolved)
    else:
        groups = {i: group for group, indices in enumerate(classified['evidence']['same_center_groups']) for i in indices}
        pairs = [dict(row, source_parameter_identity=('projection_source', row['source_candidate_index']) if 'source_candidate_index' in row else ('branch_source', index),
                      center_identity=('classified_center', groups.get(index)),
                      certificate=dict(kind='NONCIRCULAR_ALGEBRAIC_SOURCE_PAIR', intersection_index=index))
                 for index, row in enumerate(classified['evidence']['intersections'])]
    center_ids = {}
    for index, row in enumerate(pairs):
        try:
            if 'exact_parameter_box' in row:
                fractions = [dict(status='PASS', interval=box, steps=0) for box in row['exact_parameter_box']]
            else:
                boxes = row['source_local_box'], row['target_local_box']
                fractions = [_parameter_fraction_enclosure(curve, box, fraction_width=width,
                    max_fraction_steps=max_fraction_steps, **common) for curve, box in zip(curves, boxes)]
                if any(f['status'] != 'PASS' for f in fractions):
                    report['unresolved'].append(dict(stage='source_fraction', source_root_index=index, evidence=fractions))
                    continue
            coincident = row.get('source_contacts_coincide')
            if coincident is None:
                coincident = _contacts_coincide(curves, boxes, row['tangent_parallel'], distances)
            center_key = row['center_identity']
            if center_key not in center_ids:
                center_ids[center_key] = len(center_ids)
            report['roots'].append(dict(parameter_box=tuple(f['interval'] for f in fractions), center_box_zr_m=row['center_box_zr_m'],
                center_group=center_ids[center_key], source_root_index=index, source_parameter_identity=row['source_parameter_identity'],
                source_contact_kind=row['contact_kind'], source_contacts_coincide=coincident,
                certificate=dict(row['certificate'], source_fractions=fractions)))
        except ValueError as error:
            report['unresolved'].append(dict(stage='source_fraction', source_root_index=index, reason=str(error)))
    # Equal first source parameters can have two different target feet. Share
    # their proved first enclosure, then order by the second original fraction.
    for key in set(row['source_parameter_identity'] for row in report['roots']):
        rows = [row for row in report['roots'] if row['source_parameter_identity'] == key]
        interval = max(row['parameter_box'][0][0] for row in rows), min(row['parameter_box'][0][1] for row in rows)
        if interval[0] > interval[1]:
            raise RuntimeError('proved identical first source has disjoint fraction enclosures')
        for row in rows:
            row['parameter_box'] = interval, row['parameter_box'][1]
    report['roots'].sort(key=lambda row: tuple(sum(box)/2 for box in row['parameter_box']))
    for left, right in zip(report['roots'], report['roots'][1:]):
        coordinate = 1 if left['source_parameter_identity'] == right['source_parameter_identity'] else 0
        if left['parameter_box'][coordinate][1] >= right['parameter_box'][coordinate][0]:
            report['unresolved'].append(dict(stage='candidate_order', source_root_indices=(left['source_root_index'], right['source_root_index']),
                reason='lexicographic candidate order is not separated at the requested fraction precision'))
    if classified['complete'] and not report['unresolved']:
        report['status'] = 'PASS'
    return report


def noncircular_conic_fillet_candidates(first, second, *, radius_m, turn_direction, max_sweep_rad,
                                       position_tolerance_m, angle_tolerance_rad, fraction_width=F(1, 2**40),
                                       max_root_boxes=10000, max_refinements=512, max_fraction_steps=128,
                                       endpoint_width=DEFAULT_ENDPOINT_WIDTH, max_series_terms=96):
    common = dict(radius_m=radius_m, turn_direction=turn_direction, max_sweep_rad=max_sweep_rad,
                  position_tolerance_m=position_tolerance_m, angle_tolerance_rad=angle_tolerance_rad,
                  allow_extension=False, endpoint_width=endpoint_width, max_series_terms=max_series_terms)
    distance, _ = _fillet_setup(first, second, **common)
    search = intersect_algebraic_noncircular_offsets(first, second, first_distance_m=distance, second_distance_m=distance,
        fraction_width=fraction_width, max_root_boxes=max_root_boxes, max_refinements=max_refinements,
        max_fraction_steps=max_fraction_steps, endpoint_width=endpoint_width, max_series_terms=max_series_terms)
    report = _fillets_from_search(first, second, search, retain_whole_at_endpoint=True, **common)
    report['arc_filter_status'] = 'ALGEBRAIC_NONCIRCULAR_FILLET_CONTACTS'
    report['scope'] = 'all finite noncircular source pairs with certified order; nonempty retained endpoints and bounded output contact errors; explicit radius/turn/sweep; floating G1; closed contour checked separately'
    return report


def connect_noncircular_conic_fillet(first, second, *, candidate_index, **controls):
    if type(candidate_index) is not int or candidate_index < 0:
        raise ValueError('candidate_index must be an explicit nonnegative integer')
    report = noncircular_conic_fillet_candidates(first, second, **controls)
    if report['status'] != 'PASS':
        raise ValueError('noncircular conic source-pair enumeration or order is UNVERIFIED; inspect unresolved evidence')
    if candidate_index >= len(report['candidates']):
        raise ValueError('candidate_index is outside the noncircular conic fillet list')
    selected = report['candidates'][candidate_index]
    if selected['connection_direction'] != 'FORWARD':
        raise ValueError(selected.get('construction_reason', 'fillet is not usable'))
    return dict(curves=tuple(curve_from_dict(row) for row in selected['trimmed_curves']),
                selected_candidate=selected, joins=selected['joins'], enumeration=report)
