# SPDX-License-Identifier: Apache-2.0
"""Exact line contacts of noncircular conic offsets and regular-domain bounds.

All source points with a tangent parallel to the line are enumerated. Global
completeness additionally requires a proved constant offset-speed sign; other
cases retain finite contact witnesses without discarding crossings or cusps.
"""
from fractions import Fraction as F

from .certified_arcs import _arc_membership
from .conics import EllipseArc, HyperbolaArc, LineSegment, rotation_cos_sin
from .quadratic_radicals import RadicalTower


def _global_regularity(curve, distance, rotation_squared):
    a, b = map(F, curve.semiaxes_m)
    if isinstance(curve, EllipseArc):
        minimum = min(a,b)**4*rotation_squared/max(a,b)**2
        maximum = max(a,b)**4*rotation_squared/min(a,b)**2
        kind = ('FORWARD' if distance <= 0 or distance*distance < minimum else
                'REVERSED' if distance*distance > maximum else 'UNVERIFIED')
    else:
        minimum, maximum = b**4*rotation_squared/a**2, None
        kind = 'FORWARD' if distance >= 0 or distance*distance < minimum else 'UNVERIFIED'
    return dict(kind=kind, adjusted_distance_m=distance,
                minimum_curvature_radius_squared_m2=minimum,
                maximum_curvature_radius_squared_m2=maximum)


def _line_membership(tower, point, line, squared, domain, roots):
    fraction = tower.number(0)
    for coordinate, origin, direction in zip(point, line.start_zr_m,
                                            (F(b)-F(a) for a,b in zip(line.start_zr_m,line.end_zr_m))):
        fraction = tower.add(fraction, tower.scale(tower.subtract(coordinate,tower.number(origin)), direction/squared))
    signs = [tower.sign(tower.subtract(fraction,tower.number(x))) for x in domain]
    status = ('EXTERIOR' if signs[0] < 0 or signs[1] > 0 else
              'START' if signs[0] == 0 else 'END' if signs[1] == 0 else 'INTERIOR')
    return dict(status=status, fraction_coefficients=fraction,
                fraction_bounds=tower.bounds(fraction,roots), endpoint_difference_signs=signs)


def classify_line_noncircular_contacts(curves, distances, domains, *, endpoint_width, max_series_terms):
    """The public classifier validates inputs before entering this extension."""
    if sum(isinstance(curve,LineSegment) for curve in curves) != 1:
        return None
    index = 0 if isinstance(curves[0],LineSegment) else 1
    line, curve = curves[index], curves[1-index]
    if not isinstance(curve,(EllipseArc,HyperbolaArc)):
        return None
    a,b = map(F,curve.semiaxes_m)
    if isinstance(curve,EllipseArc) and a == b:
        return None
    epsilon = 1 if isinstance(curve,EllipseArc) else -1
    branch = 1 if epsilon == 1 else curve.branch
    span = F(curve.sweep_rad) if epsilon == 1 else F(curve.end_parameter)-F(curve.start_parameter)
    distance = F(distances[1-index])*(1 if span > 0 else -1)*branch
    line_distance = F(distances[index])
    line_domain, arc_domain = [tuple(map(F,domains[i])) for i in (index,1-index)]
    delta = tuple(F(y)-F(x) for x,y in zip(line.start_zr_m,line.end_zr_m))
    normal = (-delta[1],delta[0]); squared = sum(x*x for x in delta)
    c,s = map(F,rotation_cos_sin(curve.rotation_rad)); rotation_squared = c*c+s*s
    local_normal = (c*normal[0]+s*normal[1],-s*normal[0]+c*normal[1])
    u,v = local_normal
    support_square = a*a*u*u+epsilon*b*b*v*v
    regularity = _global_regularity(curve,distance,rotation_squared)
    evidence = dict(identity='all source-conic tangents parallel to the offset line',
                    line_index=index, normal=normal, line_length_squared=squared,
                    local_normal=local_normal, support_square=support_square,
                    global_regularity=regularity, source_tangent_contacts=[])
    tower = RadicalTower()

    def report(classification, *, complete=False, count=None, infinite=None, reason):
        evidence['radicands'] = tuple(tower.radicands)
        return dict(classification=classification,complete=complete,centers=count,infinite=infinite,
                    evidence=evidence,reason=reason)

    if support_square <= 0:
        return report('UNVERIFIED',reason='no finite parallel source tangent; general crossings and cusps are not excluded')
    line_length = tower.square_root(tower.number(squared))
    support = tower.square_root(tower.number(support_square))
    roots = tower.root_bounds(F(endpoint_width)/256)
    center_projection = sum(normal[i]*(F(curve.center_zr_m[i])-F(line.start_zr_m[i])) for i in range(2))
    records = []
    for side in (-1,1):
        local = (tower.scale(support,side*a*u/support_square),
                 tower.scale(support,side*epsilon*b*v/support_square))
        if epsilon == -1 and tower.sign(local[0]) != branch:
            continue
        source = tuple(tower.add(tower.number(center),tower.add(tower.scale(local[0],x),tower.scale(local[1],y)))
                       for center,(x,y) in zip(curve.center_zr_m,((c*a,-s*b),(s*a,c*b))))
        point = tuple(tower.subtract(x,tower.scale(line_length,side*distance*n/squared)) for x,n in zip(source,normal))
        incidence = tower.subtract(tower.add(tower.number(center_projection),tower.scale(support,side)),
                                   tower.scale(line_length,line_distance+side*distance))
        # Positive denominator is n^2 a^2 b^2 |N|^3. The hyperbolic
        # signed curvature has the opposite sign to the adjusted distance.
        factor_numerator = tower.subtract(tower.scale(line_length,rotation_squared**2*a*a*b*b*squared),
                                          tower.scale(support,epsilon*distance*support_square))
        factor_sign = tower.sign(factor_numerator)
        row = dict(side=side,source_local_coefficients=local,center_coefficients=point,
                   center_box_zr_m=tuple(tower.bounds(x,roots) for x in point),
                   incidence=incidence,incidence_sign=tower.sign(incidence),
                   offset_speed_factor_numerator=factor_numerator,offset_speed_factor_sign=factor_sign,
                   contact_kind='CUSP_AT_SOURCE_TANGENCY' if factor_sign == 0 else 'REGULAR_TANGENCY',
                   parameter_pair_in_domain=False)
        if row['incidence_sign'] == 0:
            start = F(curve.start_rad) if epsilon == 1 else F(curve.start_parameter)
            try:
                box = tuple(tower.ratio_bounds(x,tower.number(1),roots) for x in local)
                arc_membership = _arc_membership(curve,box,parameter_endpoints=tuple(start+span*t for t in arc_domain),
                                                endpoint_width=endpoint_width,max_series_terms=max_series_terms)
            except ValueError as error:
                arc_membership = dict(status='UNVERIFIED',reason=str(error))
            line_membership = _line_membership(tower,point,line,squared,line_domain,roots)
            membership = [None,None]; membership[index] = line_membership; membership[1-index] = arc_membership
            statuses = [item['status'] for item in membership]
            row.update(membership=membership,parameter_pair_in_domain=(False if 'EXTERIOR' in statuses else
                       None if 'UNVERIFIED' in statuses else True))
        records.append(row)
    evidence.update(source_tangent_contacts=records,root_bounds=roots)
    if regularity['kind'] != 'UNVERIFIED':
        if epsilon == 1:
            minimum,maximum = records if regularity['kind'] == 'FORWARD' else records[::-1]
            outside = minimum['incidence_sign'] > 0 or maximum['incidence_sign'] < 0
        else:
            row = records[0]
            outside = row['side']*row['incidence_sign'] > 0
        if outside:
            evidence['supporting_parameter_intersection_count'] = 0
            return report('DISJOINT',complete=True,count=0,infinite=False,reason='global projection extremum excludes every supporting intersection')
        contacts = [row for row in records if row['incidence_sign'] == 0]
        if contacts:
            assert len(contacts) == 1, 'strict global regularity requires a unique supporting extremum contact'
            evidence['supporting_parameter_intersection_count'] = 1
            exists = contacts[0]['parameter_pair_in_domain']
            if exists is not None:
                return report('SINGLE_TANGENCY' if exists else 'DISJOINT',complete=True,count=int(exists),infinite=False,
                              reason='unique global supporting contact and finite memberships classified')
        else:
            evidence['supporting_parameter_intersection_count'] = 2
    groups = []
    for contact_index,row in enumerate(records):
        if row['parameter_pair_in_domain'] is not True:
            continue
        for group in groups:
            representative = records[group[0]]
            if all(tower.sign(tower.subtract(a,b)) == 0 for a,b in zip(row['center_coefficients'],representative['center_coefficients'])):
                group.append(contact_index); break
        else:
            groups.append([contact_index])
    evidence.update(tangency_witness_center_count=len(groups),same_center_contact_groups=groups)
    return report('TANGENCY_WITNESSES' if groups else 'UNVERIFIED',
                  reason='certified finite tangent witnesses; other crossings or cusps remain unclassified' if groups
                  else 'source tangent possibilities checked; finite membership or general crossings remain unresolved')
