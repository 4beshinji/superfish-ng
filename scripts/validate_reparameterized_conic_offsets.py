# SPDX-License-Identifier: Apache-2.0
"""Independent original-normal bisection and mapped-parameter comparison."""
import argparse
from dataclasses import replace
from decimal import Decimal as D, localcontext
from fractions import Fraction as F
import itertools
import json
import math
from pathlib import Path
import time

from validate_coincident_circle_arcs import fingerprints, reference_pi
from validate_general_coincident_circle_arcs import decimal_value as dec, sine_cosine
from validate_same_conic_offset_intersections import reference_contacts, parameter_range
from superfish_ng.conics import EllipseArc, HyperbolaArc, curve_to_dict, rotation_cos_sin
from superfish_ng.offset_degeneracies import classify_offset_degeneracies
from superfish_ng.tangent_construction import _json_value


def local_point(curve, parameter):
    if isinstance(curve, EllipseArc):
        s, c = sine_cosine(parameter)
        return c, s
    exp = parameter.exp()
    return curve.branch*(exp+1/exp)/2, (exp-1/exp)/2


def original_offset(curve, parameter, distance):
    a, b = map(dec, curve.semiaxes_m); x, y = local_point(curve, parameter)
    tangent = (-a*y, b*x) if isinstance(curve, EllipseArc) else (curve.branch*a*y, curve.branch*b*x)
    c, s = map(dec, rotation_cos_sin(curve.rotation_rad)); vx, vy = tangent
    tangent = c*vx-s*vy, s*vx+c*vy
    length = sum(t*t for t in tangent).sqrt()
    direction = 1 if (curve.sweep_rad if isinstance(curve, EllipseArc) else curve.end_parameter-curve.start_parameter) > 0 else -1
    d = direction*dec(distance)
    return (dec(curve.center_zr_m[0])+c*a*x-s*b*y-d*tangent[1]/length,
            dec(curve.center_zr_m[1])+s*a*x+c*b*y+d*tangent[0]/length)


def symbolic_angle(angle, pi):
    for numerator in range(-4, 9):
        coefficient = F(numerator, 2)
        if angle == dec(coefficient)*pi:
            return coefficient
    return None


def contains(interval, angle, periodic, pi):
    return any(dec(interval[0]) <= angle+2*period*pi <= dec(interval[1])
               for period in (range(-8, 9) if periodic else (0,)))


def oracle(curves, distances, domains, orientation, phase, pi):
    first, second = curves; ellipse = isinstance(first, EllipseArc)
    ranges = [parameter_range(c, domain) for c, domain in zip(curves, domains)]
    mapped = tuple(sorted(orientation*t for t in ranges[1])); positive = 0; endpoints = []
    for period in (range(-8, 9) if ellipse else (0,)):
        coefficient = phase+2*period
        if coefficient == 0:
            low, high = max(ranges[0][0], mapped[0]), min(ranges[0][1], mapped[1])
            if low == high: endpoints.append(low)
        else:
            shift = dec(coefficient)*pi
            low, high = max(dec(ranges[0][0]), dec(mapped[0])+shift), min(dec(ranges[0][1]), dec(mapped[1])+shift)
            assert abs(high-low) > D('1e-85'), 'reference endpoint ordering unresolved'
        positive += high > low
    scale = max(map(F, first.semiaxes_m)); a, b = (F(x)/scale for x in first.semiaxes_m)
    span = F(first.sweep_rad) if ellipse else F(first.end_parameter)-F(first.start_parameter)
    distance = (1 if span > 0 else -1)*F(distances[0])/scale
    rotation = tuple(map(F, rotation_cos_sin(first.rotation_rad)))
    pairs = reference_contacts('ellipse' if ellipse else 'hyperbola', 1 if ellipse else first.branch,
                               a, b, distance, sum(x*x for x in rotation))
    records = []; added = 0
    for pair in pairs:
        angles = tuple(point[0] for point in pair)
        second_angles = tuple(orientation*(angle-dec(phase)*pi) for angle in angles)
        memberships = ([contains(ranges[0], angle, ellipse, pi) for angle in angles],
                       [contains(ranges[1], angle, ellipse, pi) for angle in second_angles])
        directions = [memberships[0][left] and memberships[1][right] for left, right in ((0, 1), (1, 0))]
        duplicate = any(endpoint == 0 and symbolic_angle(angle, pi) == 0
                        for endpoint in endpoints for angle in angles)
        if any(directions) and not duplicate: added += 1
        points = (tuple(local_point(first, angle) for angle in angles),
                  tuple(local_point(second, angle) for angle in second_angles))
        center = original_offset(first, angles[0], distances[0])
        # Compare the original position plus oriented unit normal in both
        # frames, without calling the product support map or reflection roots.
        for curve, params, d in zip(curves, (angles, second_angles), distances):
            for angle in params:
                other = original_offset(curve, angle, d)
                assert max(abs(x-y)/dec(scale) for x, y in zip(center, other)) < D('1e-95')
        records.append(dict(points=points, directions=directions, duplicates=duplicate))
    if positive: expected = ('INFINITE_PARAMETER_PAIRS', None, True)
    elif added: expected = ('FINITE_CENTERS', added+len(endpoints), False)
    elif endpoints: expected = ('SHARED_PARAMETER_ENDPOINT', len(endpoints), False)
    else: expected = ('DISJOINT', 0, False)
    return expected, records, dict(positive_components=positive, shared_endpoints=len(endpoints), added_centers=added)


def encloses(boxes, point):
    # High precision trig is a numerical cross-check; exact axis values are
    # restored only when the reference parameter is an exact pi multiple.
    return all(dec(lo)-D('1e-100') <= value <= dec(hi)+D('1e-100') for (lo, hi), value in zip(boxes, point))


def families():
    ellipse_arcs = ((.5, .5, 2., .5), (0., 1., -1.5, 1.), (-3., 6., -3., 6.), (0., .25, .25, .25), (3., .5, -3.1, .3))
    frames = ((0., F(1, 2)), (0., F(1)), (0., F(-1, 2)), (.3, F(1, 2)), (.3, F(1)))
    for axes, (rotation, phase), distance, arc in itertools.product(((2., 1.), (1., 2.)), frames,
            (-.75, 0., .5, .75, 1., 2., 2.5, 4.), ellipse_arcs):
        a = EllipseArc((0, 0), axes, arc[0], arc[1], rotation)
        b = EllipseArc((0, 0), axes if phase == 1 else axes[::-1], arc[2], arc[3], rotation+float(phase)*math.pi)
        yield (a, b), (distance, distance), 1, phase
    for branch, rotation, distance, arc in itertools.product((-1, 1), (0., .3),
            (-2., -.75, -.5, 0., .5, .75), ((.25, .75, .25, .75), (0., 1., 0., 1.), (0., 1., -1., 0.), (1., 2., 1., 2.))):
        a = HyperbolaArc((0, 0), (2, 1), arc[0], arc[1], rotation_rad=rotation, branch=branch)
        b = replace(a, start_parameter=arc[2], end_parameter=arc[3], rotation_rad=rotation+math.pi, branch=-branch)
        yield (a, b), (distance, -distance), -1, F(0)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, required=True); args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False); before = fingerprints(); start = time.monotonic(); records = []
    with localcontext() as context:
        context.prec = 140; pi = reference_pi()
        variants = ((1., False, False), (2.**-40, True, False), (2.**40, False, True), (1., True, True))
        for family, (base, base_distances, orientation, base_phase) in enumerate(families()):
            for variant, (scale, reverse, exchange) in enumerate(variants):
                curves = [replace(c, center_zr_m=(3*scale, 4*scale), semiaxes_m=tuple(x*scale for x in c.semiaxes_m)) for c in base]
                distances = [d*scale for d in base_distances]; phase = base_phase
                domains = [(0, 1), (0, 1)] if variant < 3 else [(F(1, 8), F(7, 8)), (F(1, 4), F(3, 4))]
                if reverse:
                    b = curves[1]
                    curves[1] = (replace(b, start_rad=b.start_rad+b.sweep_rad, sweep_rad=-b.sweep_rad) if isinstance(b, EllipseArc)
                                 else replace(b, start_parameter=b.end_parameter, end_parameter=b.start_parameter))
                    distances[1] = -distances[1]
                if exchange:
                    curves.reverse(); distances.reverse(); domains.reverse(); phase = -orientation*phase
                row = dict(family=family, variant=variant, curves=[curve_to_dict(c) for c in curves], distances=distances,
                           domains=[[str(x) for x in domain] for domain in domains], orientation=orientation, phase=str(phase))
                actual = None
                try:
                    expected, reference, counts = oracle(curves, distances, domains, orientation, phase, pi)
                    actual = classify_offset_degeneracies(*curves, first_distance_m=distances[0], second_distance_m=distances[1],
                                first_interval=domains[0], second_interval=domains[1])
                    observed = (actual['classification'], actual['finite_center_count'], actual['infinite_parameter_pairs'])
                    assert actual['finite_domain_complete'] and observed == expected, (observed, expected)
                    product = actual['evidence']['self_contacts']; assert len(product) == len(reference)
                    for result in product:
                        matches = []
                        for ref in reference:
                            for order in ((0, 1), (1, 0)):
                                if all(encloses(box, ref['points'][0][i]) for box, i in zip(result['contacts'], order)):
                                    matches.append((ref, order))
                        assert len(matches) == 1, 'reference contact pair is not uniquely matched'
                        ref, order = matches[0]
                        for boxes, points in zip(result['contacts_in_original_frames'], ref['points']):
                            assert all(encloses(box, points[i]) for box, i in zip(boxes, order))
                        directions = ref['directions'] if order == (0, 1) else ref['directions'][::-1]
                        assert result['parameter_pair_directions'] == directions
                    row.update(expected=expected, observed=observed, reference=counts,
                               reflected_source_pairs=sum(sum(ref['directions']) for ref in reference))
                    records.append(row)
                except Exception:
                    (args.out/'failure.json').write_text(json.dumps(dict(case=row, actual=_json_value(actual)), indent=2)+'\n')
                    raise
    assert fingerprints() == before
    report = dict(status='PASS', cases=len(records), seconds=time.monotonic()-start,
                  reflected_source_pairs=sum(row['reflected_source_pairs'] for row in records),
                  infinite_cases=sum(row['observed'][2] is True for row in records),
                  source_sha256=before, source_changed_during_run=False,
                  reference='140-digit original-normal-component bisection, original point/normal in both frames, fixed 17 ellipse translates',
                  scope='equal offsets on one noncircular support under exact principal reparameterization; no fillet or FEM accuracy claim', records=records)
    (args.out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    print({key: report[key] for key in ('status', 'cases', 'seconds', 'reflected_source_pairs', 'infinite_cases')})


if __name__ == '__main__':
    main()
