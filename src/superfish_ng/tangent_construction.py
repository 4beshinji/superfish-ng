# SPDX-License-Identifier: Apache-2.0
"""Replayable tangent construction documents and canonical Case validation."""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from . import __version__
from .arc_tangents import finite_arc_tangents, connect_finite_arcs
from .config import Case, keys
from .conics import EllipseArc, HyperbolaArc, curve_from_dict, curve_to_dict
from .project import parse_json


def _json_value(value):
    if isinstance(value, Fraction):
        return {'rational_numerator': str(value.numerator), 'rational_denominator': str(value.denominator)}
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _request(request):
    keys(request, ('schema_version', 'case_template', 'pair_start', 'controls'),
         ('schema_version', 'case_template', 'pair_start', 'controls'), 'tangent construction request')
    if type(request['schema_version']) is not int or request['schema_version'] != 1:
        raise ValueError('tangent construction request requires schema_version 1')
    _canonical(request)  # Reject nonfinite JSON values even in the unfinished template.
    template = request['case_template']
    keys(template, ('schema_version', 'name', 'geometry', 'mesh', 'solver', 'rf', 'model', 'boundaries'),
         ('schema_version', 'geometry', 'model'), 'construction case template')
    if type(template['schema_version']) is not int or template['schema_version'] != 3:
        raise ValueError('construction requires a v3 curved_contour case template')
    from .model import Model
    Model.from_dict(template['model'])
    geometry = template['geometry']
    keys(geometry, ('type', 'curves', 'edge_tags', 'join_tolerance_m', 'minimum_gap_m',
                    'chord_tolerance_m', 'chord_max_segments'),
         ('type', 'curves', 'edge_tags', 'join_tolerance_m', 'chord_tolerance_m'), 'construction geometry')
    if geometry['type'] != 'curved_contour' or not isinstance(geometry['curves'], list):
        raise ValueError('construction requires curved_contour with a curves array')
    curves = [curve_from_dict(row) for row in geometry['curves']]
    tags = geometry['edge_tags']
    if (not isinstance(tags, list) or len(tags) != len(curves)
            or any(tag not in ('axis', 'pec', 'electric_symmetry', 'magnetic_symmetry') for tag in tags)):
        raise ValueError('construction requires one supported edge tag per curve')
    index = request['pair_start']
    if type(index) is not int or index < 0 or index+1 >= len(curves):
        raise ValueError('pair_start must identify two consecutive curves without wrapping')
    if any(not isinstance(curve, (EllipseArc, HyperbolaArc)) for curve in curves[index:index+2]):
        raise ValueError('tangent pair must contain two ellipse or hyperbola arcs')
    if tags[index:index+2] != ['pec', 'pec']:
        raise ValueError('tangent construction currently requires two PEC arcs')
    controls = request['controls']
    allowed = ('position_tolerance_m', 'angle_tolerance_rad', 'parameter_guard', 'normal_width',
               'max_boxes', 'residual_tolerance')
    keys(controls, allowed, allowed, 'tangent controls')
    return template, geometry, curves, index, controls


def construct_tangent_case(request, *, candidate_index=None):
    """Preview candidates or explicitly replace a consecutive pair by arc/line/arc.

    The input template is an unfinished editing document, not an accepted Case.
    Selection invokes the full existing Case/closed-contour validator, including
    all solver/RF settings. A preview never authorizes the template for solving.
    """
    template, geometry, curves, index, controls = _request(request)
    first, second = curves[index:index+2]
    if candidate_index is None:
        enumeration = finite_arc_tangents(first, second, **controls)
        case, joins = None, None
        status = 'CANDIDATES' if enumeration['status'] == 'PASS' else 'UNVERIFIED'
    else:
        construction = connect_finite_arcs(first, second, candidate_index=candidate_index, **controls)
        enumeration, joins = construction['enumeration'], construction['joins']
        selected = deepcopy(template)
        selected['geometry']['curves'] = [curve_to_dict(curve) for curve in
                                          curves[:index]+list(construction['curves'])+curves[index+2:]]
        selected['geometry']['edge_tags'] = geometry['edge_tags'][:index]+['pec']*3+geometry['edge_tags'][index+2:]
        case = Case.from_dict(selected).to_dict()
        status = 'CASE_VALIDATED'
    return _json_value(dict(schema_version=1, software_version=__version__, request=deepcopy(request),
                           request_sha256=hashlib.sha256(_canonical(request).encode()).hexdigest(),
                           candidate_index=candidate_index, enumeration=enumeration, joins=joins,
                           case=case, status=status,
                           scope='guarded numerical tangent construction; preview template is not a validated case; no FEM solve'))


def save_construction(request, path, *, candidate_index=None):
    """Save a fully computed single document with exclusive creation."""
    document = construct_tangent_case(request, candidate_index=candidate_index)
    text = json.dumps(document, indent=2, allow_nan=False)+'\n'
    with Path(path).open('x', encoding='utf-8') as stream:
        stream.write(text)
    return document


def read_construction(path):
    """Replay the source request and reject a stale or modified saved result.

    Exact JSON replay targets this implementation/environment. It is not an
    authenticity signature; a changed request can produce a new valid document.
    """
    return replay_construction(parse_json(Path(path).read_text(encoding='utf-8')))


def replay_construction(document):
    """Validate an in-memory saved document using the same replay as file import."""
    keys(document, ('schema_version', 'software_version', 'request', 'request_sha256', 'candidate_index',
                    'enumeration', 'joins', 'case', 'status', 'scope'),
         ('schema_version', 'software_version', 'request', 'request_sha256', 'candidate_index',
          'enumeration', 'joins', 'case', 'status', 'scope'), 'saved tangent construction')
    expected = construct_tangent_case(document['request'], candidate_index=document['candidate_index'])
    if _canonical(document) != _canonical(expected):
        raise ValueError('construction replay differs from saved data; regenerate from the source request')
    return document


def export_constructed_case(source, target):
    document = read_construction(source)
    if document['status'] != 'CASE_VALIDATED':
        raise ValueError('construction has no explicitly selected, validated case')
    text = json.dumps(document['case'], indent=2, allow_nan=False)+'\n'
    with Path(target).open('x', encoding='utf-8') as stream:
        stream.write(text)
