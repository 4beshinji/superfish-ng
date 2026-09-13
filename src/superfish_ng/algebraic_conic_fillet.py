# SPDX-License-Identifier: Apache-2.0
"""Version 7 line/conic fillets from all algebraically isolated source pairs."""
from fractions import Fraction as F
from .conics import curve_from_dict
from .certified_arcs import DEFAULT_ENDPOINT_WIDTH
from .conic_fillet import _fillet_setup, _fillets_from_search
from .algebraic_offset_parameters import intersect_algebraic_line_offsets


def algebraic_conic_fillet_candidates(first, second, *, radius_m, turn_direction, max_sweep_rad,
                                      position_tolerance_m, angle_tolerance_rad, allow_extension=False,
                                      fraction_width=F(1, 2**40), max_root_boxes=10000, max_refinements=512,
                                      max_fraction_steps=128, endpoint_width=DEFAULT_ENDPOINT_WIDTH, max_series_terms=96):
    common = dict(radius_m=radius_m, turn_direction=turn_direction, max_sweep_rad=max_sweep_rad,
                  position_tolerance_m=position_tolerance_m, angle_tolerance_rad=angle_tolerance_rad,
                  allow_extension=allow_extension, endpoint_width=endpoint_width, max_series_terms=max_series_terms)
    distance, domains = _fillet_setup(first, second, **common)
    search = intersect_algebraic_line_offsets(first, second, first_distance_m=distance, second_distance_m=distance,
        fraction_width=fraction_width, max_root_boxes=max_root_boxes, max_refinements=max_refinements,
        max_fraction_steps=max_fraction_steps, endpoint_width=endpoint_width, max_series_terms=max_series_terms, **domains)
    report = _fillets_from_search(first, second, search, retain_whole_at_endpoint=True, **common)
    report['arc_filter_status'] = 'ALGEBRAIC_LINE_CONIC_FILLET_CONTACTS'
    report['scope'] = 'all finite algebraic source pairs with certified candidate order; bounded output contact errors and nonempty retained endpoints; explicit radius/turn/sweep/extension; floating G1; closed contour checked separately'
    return report


def connect_algebraic_conic_fillet(first, second, *, candidate_index, **controls):
    if type(candidate_index) is not int or candidate_index < 0:
        raise ValueError('candidate_index must be an explicit nonnegative integer')
    report = algebraic_conic_fillet_candidates(first, second, **controls)
    if report['status'] != 'PASS':
        raise ValueError('algebraic fillet source-pair enumeration or ordering is UNVERIFIED; inspect unresolved evidence')
    if candidate_index >= len(report['candidates']):
        raise ValueError('candidate_index is outside the algebraic conic fillet list')
    selected = report['candidates'][candidate_index]
    if selected['connection_direction'] != 'FORWARD':
        raise ValueError(selected.get('construction_reason', 'fillet is not usable'))
    return dict(curves=tuple(curve_from_dict(row) for row in selected['trimmed_curves']),
                selected_candidate=selected, joins=selected['joins'], enumeration=report)
