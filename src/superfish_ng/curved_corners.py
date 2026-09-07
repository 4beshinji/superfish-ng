# SPDX-License-Identifier: Apache-2.0
"""Geometric join diagnostics on analytic primitives, not on mesh subdivisions."""
import math
import numpy as np
from .curved_contour import CurvedContour


def classify_curve_joins(contour, *, angle_tolerance_rad=1e-8):
    """Classify PEC turns away from the axis; do not certify physical regularity.

    Native contours have positive orientation in (z,r), so an off-axis
    vacuum interior angle is pi minus the signed incoming/outgoing turn.
    Axis and mixed boundary joins require separate physical analysis.
    """
    if not isinstance(contour, CurvedContour):
        raise ValueError('corner diagnostics require a native CurvedContour')
    if (type(angle_tolerance_rad) not in (int, float) or not math.isfinite(angle_tolerance_rad)
            or not 0 < angle_tolerance_rad < math.pi/2):
        raise ValueError('angle_tolerance_rad must be finite and between 0 and pi/2')
    joins = []
    categories = ('axis_join', 'mixed_boundary_join', 'non_pec_join', 'tangent_within_tolerance',
                  'convex_pec_corner', 'reentrant_pec_corner', 'reversal_or_unresolved')
    counts = dict.fromkeys(categories, 0)
    for i, first in enumerate(contour.curves):
        j = (i+1) % len(contour.curves)
        a, b = first.evaluate(1.), contour.curves[j].evaluate(0.)
        u, v = a['tangent_zr'], b['tangent_zr']
        turn = math.atan2(float(u[0]*v[1]-u[1]*v[0]), float(u@v))
        tags = (contour.edge_tags[i], contour.edge_tags[j])
        interior = None
        if 'axis' in tags:
            category = 'axis_join'
        elif tags[0] != tags[1]:
            category = 'mixed_boundary_join'
        elif tags != ('pec', 'pec'):
            category = 'non_pec_join'
        else:
            interior = math.pi-turn
            if math.pi-abs(turn) <= angle_tolerance_rad:
                category = 'reversal_or_unresolved'
            elif abs(turn) <= angle_tolerance_rad:
                category = 'tangent_within_tolerance'
            else:
                category = 'convex_pec_corner' if turn > 0 else 'reentrant_pec_corner'
        counts[category] += 1
        joins.append(dict(incoming_curve_index=i, outgoing_curve_index=j, edge_tags=list(tags),
                          incoming_endpoint_zr_m=a['points_zr_m'].tolist(),
                          outgoing_endpoint_zr_m=b['points_zr_m'].tolist(),
                          endpoint_gap_m=float(np.linalg.norm(a['points_zr_m']-b['points_zr_m'])),
                          signed_turn_rad=turn, vacuum_interior_angle_rad=interior, classification=category))
    return dict(version=1, angle_tolerance_rad=angle_tolerance_rad, counts=counts, joins=joins,
                source='native analytic primitive joins; mesh-only joins excluded',
                physical_peak_status='UNVERIFIED',
                interpretation='reentrant PEC corners require dedicated peak convergence analysis; axis and mixed joins are not classified by a planar wedge criterion; near-tangent is tolerance-based, not exact smoothness certification')
