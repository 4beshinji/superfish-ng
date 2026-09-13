# SPDX-License-Identifier: Apache-2.0
"""Replayable offset diagnostics bound to an existing fillet construction."""
from copy import deepcopy
from fractions import Fraction
from .config import keys
from .conics import curve_from_dict
from .tangent_construction import _canonical, _json_value, replay_construction
from .offset_degeneracies import classify_offset_degeneracies, _classify_offset_degeneracies, _classify_offset_degeneracies_v2, _classify_offset_degeneracies_v3, _classify_offset_degeneracies_v4, _classify_offset_degeneracies_v5, _classify_offset_degeneracies_v6


def _from_replayed_construction(construction, *, schema_version=7):
    """Internal: construction must be freshly built or successfully replayed."""
    if type(schema_version) is not int or schema_version not in (1,2,3,4,5,6,7):
        raise ValueError('construction offset diagnosis requires schema version 1, 2, 3, 4, 5, 6 or 7')
    if construction['schema_version'] not in (5,6):return None
    request=construction['request'];index=request['pair_start']
    curves=[curve_from_dict(row) for row in request['case_template']['geometry']['curves'][index:index+2]]
    search=construction['enumeration']['certificate']
    def rational(value):
        return Fraction(int(value['rational_numerator']),int(value['rational_denominator']))
    domain=[tuple(rational(x) for x in interval) for interval in search['domain_box']]
    controls=search['controls']
    classifier = {1:_classify_offset_degeneracies,2:_classify_offset_degeneracies_v2,3:_classify_offset_degeneracies_v3,4:_classify_offset_degeneracies_v4,5:_classify_offset_degeneracies_v5,6:_classify_offset_degeneracies_v6,7:classify_offset_degeneracies}[schema_version]
    diagnosis=classifier(*curves,
        first_distance_m=rational(controls['first_distance_m']),second_distance_m=rational(controls['second_distance_m']),
        first_interval=domain[0],second_interval=domain[1],endpoint_width=rational(controls['endpoint_width']),
        max_series_terms=controls['max_series_terms'])
    return dict(schema_version=schema_version,document_type='construction_offset_diagnosis',
                construction=deepcopy(construction),parameter_domain_box=deepcopy(search['domain_box']),diagnosis=_json_value(diagnosis))


def diagnose_construction(document):
    result=_from_replayed_construction(replay_construction(document))
    if result is None:raise ValueError('offset diagnosis requires a saved version 5 or 6 fillet construction')
    return result


def replay_construction_diagnosis(document):
    fields=('schema_version','document_type','construction','parameter_domain_box','diagnosis')
    keys(document,fields,fields,'saved construction offset diagnosis')
    expected=_from_replayed_construction(replay_construction(document['construction']),schema_version=document['schema_version'])
    if expected is None:raise ValueError('offset diagnosis requires a saved version 5 or 6 fillet construction')
    if _canonical(document)!=_canonical(expected):
        raise ValueError('construction offset diagnosis replay differs from saved data; regenerate from the construction')
    return expected
