# SPDX-License-Identifier: Apache-2.0
"""Version 9 fillets from all finite circular-offset source pairs."""
from fractions import Fraction as F

from .algebraic_circular_offsets import _models, _dot, classify_algebraic_circular_offsets
from .certified_arcs import _number, _parameter_fraction_enclosure, transcendental_interval, DEFAULT_ENDPOINT_WIDTH
from .conics import EllipseArc, curve_from_dict
from .conic_fillet import _fillet_setup, _fillets_from_search
from .general_coincident_circle_arcs import classify_general_coincident_arcs
from .normal_offsets import add, scale
from .certified_arcs import _multiply
from .quadratic_radicals import RadicalTower


def _same_contacts(tower, curves, models, point, distances):
    if distances[0] != distances[1]:
        return None
    if distances[0] == 0:
        return True
    # Equal signed distances: compare original directed unit radial vectors.
    # Cross multiplication preserves equality even when a support radius is negative.
    vectors = [tuple(tower.scale(tower.subtract(x, tower.number(c)), 1 if curve.sweep_rad > 0 else -1)
                     for x, c in zip(point, model['center'])) for curve, model in zip(curves, models)]
    return all(tower.sign(tower.subtract(tower.multiply(a, models[1]['rho']),
                                        tower.multiply(b, models[0]['rho']))) == 0
               for a, b in zip(*vectors))


def _local_box(tower, model, point, bounds):
    delta = tuple(tower.subtract(x, tower.number(c)) for x, c in zip(point, model['center']))
    c, s = model['rotation']
    return tuple(tower.ratio_bounds(_dot(tower, delta, axis), model['denominator'], bounds)
                 for axis in ((c, s), (-s, c)))


def _shared_endpoint(tower, curves, models, distances, overlap, bounds, controls):
    first_angle = overlap['overlap_start_bounds'][0]
    shift = overlap['shift_bounds']
    if shift[0] != shift[1]:
        raise ValueError('shared endpoint shift is not exact')
    angles = first_angle, first_angle-shift[0]
    fractions = tuple((theta-F(curve.start_rad))/F(curve.sweep_rad) for curve, theta in zip(curves, angles))
    centers = []
    for model, theta in zip(models, angles):
        cs, sn = [transcendental_interval(kind, theta, endpoint_width=controls['endpoint_width'],
                                         max_terms=controls['max_series_terms']) for kind in ('cos', 'sin')]
        c, s = model['rotation']
        length = tower.square_root(tower.number(c*c+s*s))
        factor = tower.ratio_bounds(model['rho'], length, bounds)
        radial = add(scale(cs, c), scale(sn, -s)), add(scale(cs, s), scale(sn, c))
        centers.append(tuple(add((x, x), _multiply(factor, v)) for x, v in zip(model['center'], radial)))
    center = tuple((max(a[0], b[0]), min(a[1], b[1])) for a, b in zip(*centers))
    if any(lo > hi for lo, hi in center):
        raise RuntimeError('proved shared endpoint has disjoint center enclosures')
    coincident = None
    if distances[0] == distances[1]:
        orientations = [(1 if c.sweep_rad > 0 else -1)*tower.sign(m['rho']) for c, m in zip(curves, models)]
        coincident = distances[0] == 0 or orientations[0] == orientations[1]
    return dict(parameter_box=tuple((x, x) for x in fractions), center_box_zr_m=center,
                source_contacts_coincide=coincident, source_contact_kind='SHARED_SUPPORT_ENDPOINT',
                certificate=dict(kind='CIRCULAR_SHARED_SUPPORT_ENDPOINT', periodic_intersection=overlap,
                                 source_fractions=tuple(dict(status='PASS', interval=(x, x), steps=0) for x in fractions)))


def intersect_algebraic_circular_offsets(first, second, *, first_distance_m, second_distance_m,
                                        first_interval=(0., 1.), second_interval=(0., 1.),
                                        fraction_width=F(1, 2**40), max_fraction_steps=128,
                                        max_radical_refinements=3, endpoint_width=DEFAULT_ENDPOINT_WIDTH,
                                        max_series_terms=96):
    curves = first, second
    if not all(isinstance(c, EllipseArc) and c.semiaxes_m[0] == c.semiaxes_m[1] for c in curves):
        raise ValueError('circular fillet requires two circular arcs with equal semiaxes')
    distances = tuple(_number(x, 'distance_m') for x in (first_distance_m, second_distance_m))
    width = _number(fraction_width, 'fraction_width')
    if not 0 < width < 1:
        raise ValueError('fraction_width must be between zero and one')
    for name, value in (('max_fraction_steps', max_fraction_steps), ('max_radical_refinements', max_radical_refinements)):
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
            raise ValueError('circular fraction interval must increase within [0,1]')
        domains.append((low, high))
    controls = dict(first_distance_m=distances[0], second_distance_m=distances[1], fraction_width=width,
                    max_fraction_steps=max_fraction_steps, max_radical_refinements=max_radical_refinements,
                    endpoint_width=endpoint_width, max_series_terms=max_series_terms)
    report = dict(status='UNVERIFIED', roots=[], unresolved=[], domain_box=tuple(domains), controls=controls,
                  method='exact circular supports and certified source-fraction order',
                  scope='complete finite source pairs and lexicographic traversal order when PASS; output geometry and FEM accuracy are separate')
    tower = RadicalTower(); models = _models(tower, curves, distances)
    classified = classify_algebraic_circular_offsets(curves, distances, domains,
        endpoint_width=endpoint_width, max_series_terms=max_series_terms)
    if classified is None:
        classified = classify_general_coincident_arcs(curves, distances, domains,
            endpoint_width=endpoint_width, max_series_terms=max_series_terms)
        if classified is None:
            # The algebraic classifier returns None only for concentric equal
            # supports; the noncollapsed case was handled immediately above.
            if not all(tower.sign(m['rho']) == 0 for m in models):
                raise RuntimeError('unclassified equal circular supports')
            classified = dict(classification='INFINITE_PARAMETER_PAIRS', complete=True, centers=1, infinite=True,
                              evidence=dict(center_zr_m=models[0]['center'], both_circles_collapsed=True))
        report['algebraic_intersections'] = classified
        if not classified.get('complete') or classified.get('infinite'):
            report['unresolved'].append(dict(stage='coincident_support', reason='infinitely many source parameter pairs; no finite candidate-index list'
                if classified.get('infinite') else classified.get('reason', 'finite membership is unresolved')))
            return report
        bounds = tower.root_bounds(endpoint_width/256)
        for overlap in classified['evidence'].get('periodic_intersections', []):
            if overlap['classification'] != 'SHARED_ENDPOINT':
                continue
            try:
                report['roots'].append(_shared_endpoint(tower, curves, models, distances, overlap, bounds, controls))
            except ValueError as error:
                report['unresolved'].append(dict(stage='shared_endpoint', reason=str(error)))
    else:
        report['algebraic_intersections'] = classified
        if not classified['complete']:
            report['unresolved'].append(dict(stage='finite_membership', reason=classified['reason']))
        if classified['infinite'] or any(tower.sign(m['rho']) == 0 for m in models):
            if classified['complete'] and classified['centers'] == 0:
                report['status'] = 'PASS'
            else:
                report['unresolved'].append(dict(stage='collapsed_circle', reason='collapsed circle incidence has infinitely many source parameters or is unresolved'))
            return report
        tower.radicands = list(classified['evidence']['radicands'])
        for index, row in enumerate(classified['evidence'].get('candidates', [])):
            if row['parameter_pair_in_domain'] is not True:
                continue
            point = row['center_coefficients']; fractions = None; reason = None
            for refinement in range(max_radical_refinements):
                bounds = tower.root_bounds(endpoint_width/2**(8+64*refinement))
                try:
                    fractions = [_parameter_fraction_enclosure(c, _local_box(tower, m, point, bounds), fraction_width=width,
                        max_fraction_steps=max_fraction_steps, endpoint_width=endpoint_width, max_series_terms=max_series_terms)
                        for c, m in zip(curves, models)]
                    if all(f['status'] == 'PASS' for f in fractions):
                        break
                except ValueError as error:
                    reason = str(error)
            else:
                report['unresolved'].append(dict(stage='source_fraction', source_root_index=index, evidence=fractions, reason=reason))
                continue
            report['roots'].append(dict(parameter_box=tuple(f['interval'] for f in fractions),
                center_box_zr_m=tuple(tower.bounds(x, bounds) for x in point),
                source_contacts_coincide=_same_contacts(tower, curves, models, point, distances),
                source_contact_kind='REGULAR_TANGENCY' if classified['evidence']['discriminant_sign'] == 0 else 'TRANSVERSE',
                certificate=dict(kind='ALGEBRAIC_CIRCULAR_SOURCE_PAIR', source_root_index=index,
                                 source_fractions=fractions, radical_refinement=refinement)))
    report['roots'].sort(key=lambda r: tuple(sum(t)/2 for t in r['parameter_box']))
    for left, right in zip(report['roots'], report['roots'][1:]):
        if left['parameter_box'][0][1] >= right['parameter_box'][0][0]:
            report['unresolved'].append(dict(stage='candidate_order', reason='first source fractions are not separated at the requested precision'))
    if not report['unresolved']:
        report['status'] = 'PASS'
    return report


def circular_fillet_candidates(first, second, *, radius_m, turn_direction, max_sweep_rad,
                               position_tolerance_m, angle_tolerance_rad, fraction_width=F(1, 2**40),
                               max_fraction_steps=128, max_radical_refinements=3,
                               endpoint_width=DEFAULT_ENDPOINT_WIDTH, max_series_terms=96):
    common = dict(radius_m=radius_m, turn_direction=turn_direction, max_sweep_rad=max_sweep_rad,
                  position_tolerance_m=position_tolerance_m, angle_tolerance_rad=angle_tolerance_rad,
                  allow_extension=False, endpoint_width=endpoint_width, max_series_terms=max_series_terms)
    distance, _ = _fillet_setup(first, second, **common)
    search = intersect_algebraic_circular_offsets(first, second, first_distance_m=distance, second_distance_m=distance,
        fraction_width=fraction_width, max_fraction_steps=max_fraction_steps, max_radical_refinements=max_radical_refinements,
        endpoint_width=endpoint_width, max_series_terms=max_series_terms)
    result = _fillets_from_search(first, second, search, retain_whole_at_endpoint=True, **common)
    result['arc_filter_status'] = 'ALGEBRAIC_CIRCULAR_FILLET_CONTACTS'
    result['scope'] = 'all finite circular source pairs with certified order; nonempty retained endpoints; bounded output contact errors; explicit radius/turn/sweep; floating G1; closed contour checked separately'
    return result


def connect_circular_fillet(first, second, *, candidate_index, **controls):
    if type(candidate_index) is not int or candidate_index < 0:
        raise ValueError('candidate_index must be an explicit nonnegative integer')
    report = circular_fillet_candidates(first, second, **controls)
    if report['status'] != 'PASS':
        raise ValueError('circular source-pair enumeration or order is UNVERIFIED; inspect unresolved evidence')
    if candidate_index >= len(report['candidates']):
        raise ValueError('candidate_index is outside the circular fillet list')
    selected = report['candidates'][candidate_index]
    if selected['connection_direction'] != 'FORWARD':
        raise ValueError(selected.get('construction_reason', 'fillet is not usable'))
    return dict(curves=tuple(curve_from_dict(row) for row in selected['trimmed_curves']),
                selected_candidate=selected, joins=selected['joins'], enumeration=report)
