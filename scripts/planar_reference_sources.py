# SPDX-License-Identifier: Apache-2.0
"""Bind owned NG inputs to a reference table without changing their geometry."""
import hashlib
from pathlib import Path
import re

from superfish_ng.config import keys
from superfish_ng.planar_polygon import planar_case_from_dict
from superfish_ng.project import parse_json


def _owned_path(root, relative):
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise ValueError('source paths must be relative owned examples/ or out/ inputs')
    path = (root / relative).resolve()
    if not any(path.is_relative_to(root / name) for name in ('examples', 'out')):
        raise ValueError('source paths must stay inside owned examples/ or out/')
    if not path.is_file():
        raise ValueError(f'missing source evidence: {relative}')
    return path


def _checked_bytes(root, record):
    keys(record, ['path', 'sha256'], ['path', 'sha256'], 'reference source binding')
    if not isinstance(record['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', record['sha256']):
        raise ValueError('reference source binding requires a SHA-256 digest')
    path = _owned_path(root, record['path'])
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != record['sha256']:
        raise ValueError(f'source evidence changed: {record["path"]}')
    return raw


def load_source_catalog(path, project_root):
    """Validate every source before output creation; no FEM or field replay."""
    root = Path(project_root).resolve()
    try:
        raw = Path(path).read_bytes()
        data = parse_json(raw.decode('utf-8'))
    except (OSError, UnicodeDecodeError) as error:
        raise ValueError(f'cannot read UTF-8 planar source catalog: {path}: {error}') from error
    names = ['format', 'schema_version', 'cases']
    keys(data, names, names, 'planar reference source catalog')
    if (data['format'] != 'superfish_ng_planar_reference_sources'
            or type(data['schema_version']) is not int or data['schema_version'] != 1
            or not isinstance(data['cases'], list) or not data['cases']):
        raise ValueError('expected nonempty superfish_ng_planar_reference_sources version 1')
    output, ids = [], set()
    for row in data['cases']:
        names = ['id', 'feature_ids', 'conditions', 'case', 'evidence']
        keys(row, names, names, 'planar reference source case')
        identity = row['id']
        if (not isinstance(identity, str) or not re.fullmatch('[a-z][a-z0-9_-]*', identity)
                or identity in ids):
            raise ValueError('source case IDs must be unique safe lowercase names')
        ids.add(identity)
        for name in ('feature_ids', 'conditions'):
            if (not isinstance(row[name], list) or not row[name]
                    or any(not isinstance(v, str) or not v.strip() for v in row[name])):
                raise ValueError(f'source {name} requires a nonempty list of strings')
        if not isinstance(row['evidence'], list) or not row['evidence']:
            raise ValueError('source case requires historical evidence bindings')
        case_bytes = _checked_bytes(root, row['case'])
        case = planar_case_from_dict(parse_json(case_bytes.decode('utf-8')))
        for evidence in row['evidence']:
            _checked_bytes(root, evidence)
        output.append((row, case_bytes, case))
    if Path(path).read_bytes() != raw:
        raise ValueError('source catalog changed during validation')
    return output, {'sha256': hashlib.sha256(raw).hexdigest(), 'schema_version': 1}


def append_source_cases(report, out, catalog, project_root):
    """Copy exact native input bytes; leave reference metrics and geometry unknown."""
    root = Path(project_root).resolve()
    rows, binding = catalog
    report['schema_version'] = 2
    report['scope'] += '; bound polygon/whole quadratic NG sources; no legacy geometry substitution'
    report['source_catalog'] = binding
    report['historical_source_cases'] = len(rows)
    for row, raw, case in rows:
        # Sources and receipts are checked again at publication, including earlier rows.
        if _checked_bytes(root, row['case']) != raw:
            raise ValueError(f'source case changed: {row["id"]}')
        for evidence in row['evidence']:
            _checked_bytes(root, evidence)
        folder = out / ('source-' + row['id'])
        folder.mkdir()
        with (folder / 'ng-case.json').open('xb') as stream:
            stream.write(raw)
        relative = folder.relative_to(out).as_posix()
        project_relative = folder.relative_to(root).as_posix()
        reason = ('7.17 exact whole quadratic boundary export not specified; do not replace mids by chords or analytic conics'
                  if case.to_dict()['schema_version'] == 3 else
                  '7.17 arbitrary polygon PEC boundary/IBOUND interpretation and signed Cartesian units not verified')
        report['cases'].append({
            'id': 'source-' + row['id'], 'feature_ids': row['feature_ids'], 'conditions': row['conditions'],
            'synthetic': True, 'polarization': case.polarization,
            'ng_schema_version': case.to_dict()['schema_version'],
            'original_input': row['case'], 'historical_evidence': row['evidence'],
            'evidence_role': 'historical NG source; not a new solve, replay or legacy comparison',
            'geometry_equivalence': {'status': 'UNVERIFIED', 'reason': reason},
            'legacy_deck': {'status': 'UNVERIFIED', 'path': None, 'reason': reason},
            'mode_correspondence': {'status': 'UNVERIFIED', 'ng_mode_index': None, 'reference_mode': None},
            'gates': {q: {'status': 'UNVERIFIED', 'reason': reason}
                      for q in ('frequency', 'fields', 'rf_integrals', 'surface_fields')},
            'acceptance_axes': {q: {'status': 'UNVERIFIED', 'reason': reason} for q in 'FIONW'},
            'both_sides_refinement': {'status': 'UNVERIFIED', 'reason': 'historical NG input only; reference mesh levels absent'},
            'levels': [{'path': relative, 'ng_run': {
                'status': 'NOT_RUN', 'exit_code': None, 'working_directory': str(root),
                'expected_command': ['uv', 'run', '--no-sync', 'python', '-m', 'superfish_ng',
                                     'solve-planar', f'{project_relative}/ng-case.json', '--out',
                                     f'{project_relative}/ng-result']},
                'reference_run': {'status': 'NOT_RUN', 'exit_code': None,
                                  'command': None, 'timeout_seconds': 120, 'reason': reason}}]})
    for row, raw, case in rows:
        if _checked_bytes(root, row['case']) != raw:
            raise ValueError(f'source case changed during preparation: {row["id"]}')
        for evidence in row['evidence']:
            _checked_bytes(root, evidence)
