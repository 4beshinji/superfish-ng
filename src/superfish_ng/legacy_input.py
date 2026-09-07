# SPDX-License-Identifier: Apache-2.0
"""Strict, limited AF interface import; never executes a legacy solver."""
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re

from .config import Case, positive
from .model import Model

NUMBER = re.compile(r'[+-]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eEdD][+-]?[0-9]+)?')
IDENTIFIER = re.compile(r'[A-Za-z][A-Za-z0-9_]*')
REG_KEYS = {'kprob', 'icylin', 'nbslo', 'nbsup', 'nbslf', 'nbsrt', 'beta',
            'kmethod', 'zctr', 'mat', 'conv', 'dx', 'dy', 'freq', 'epsik', 'xdri', 'ydri'}
PO_KEYS = {'x', 'y', 'nt', 'radius'}
INTEGER_KEYS = {'kprob', 'icylin', 'nbslo', 'nbsup', 'nbslf', 'nbsrt', 'kmethod', 'mat', 'nt'}


class AFInputError(ValueError):
    def __init__(self, text, offset, message):
        self.line = text.count('\n', 0, offset) + 1
        self.column = offset - text.rfind('\n', 0, offset)
        super().__init__(f'AF line {self.line}, column {self.column}: {message}')


@dataclass(frozen=True)
class Entry:
    value: float | int
    offset: int
    literal: str


def _blocks(text):
    # Mask comments without moving any source position, including CRLF lines.
    clean = re.sub(r'[!;][^\r\n]*', lambda m: ' ' * len(m[0]), text)
    first = re.search(r'^[ \t]*([$&])', clean, re.M)
    if first is None:
        raise AFInputError(text, 0, 'expected one REG namelist followed by PO points')
    title = clean[:first.start(1)].strip()
    index = first.start(1)
    blocks = []

    def whitespace(i):
        while i < len(clean) and clean[i].isspace():
            i += 1
        return i

    while (index := whitespace(index)) < len(clean):
        start = index
        marker = clean[index]
        if marker not in '$&':
            raise AFInputError(text, index, 'expected REG/PO namelist; trailing directives are unsupported')
        name_match = IDENTIFIER.match(clean, index + 1)
        if name_match is None or name_match[0].lower() not in ('reg', 'po'):
            raise AFInputError(text, index, 'only REG and PO namelists are supported')
        name = name_match[0].lower()
        if (not blocks and name != 'reg') or (blocks and name != 'po'):
            raise AFInputError(text, index, 'requires exactly one REG first, followed only by PO points')
        index = name_match.end()
        entries = {}
        while True:
            index = whitespace(index)
            if index == len(clean):
                raise AFInputError(text, index, f'unterminated {name.upper()} namelist')
            if clean[index] in '$&':
                if clean[index] != marker:
                    raise AFInputError(text, index, 'namelist start/end markers must match')
                index += 1
                end = re.match(r'end\b', clean[index:], re.I)
                if end:
                    index += end.end()
                break
            key_match = IDENTIFIER.match(clean, index)
            if key_match is None:
                raise AFInputError(text, index, 'expected a scalar variable assignment')
            offset, key = index, key_match[0].lower()
            if key not in (REG_KEYS if name == 'reg' else PO_KEYS):
                raise AFInputError(text, offset, f'unsupported {name.upper()} variable {key}')
            if key in entries:
                raise AFInputError(text, offset, f'duplicate variable {key}')
            index = whitespace(key_match.end())
            if index == len(clean) or clean[index] != '=':
                raise AFInputError(text, index, f'expected = after {key}; arrays are unsupported')
            index = whitespace(index + 1)
            number = NUMBER.match(clean, index)
            if number is None:
                raise AFInputError(text, index, f'{key} requires a finite numeric literal, not an expression')
            literal = number[0]
            if key in INTEGER_KEYS:
                if re.fullmatch(r'[+-]?[0-9]+', literal) is None:
                    raise AFInputError(text, index, f'{key} requires an integer literal')
                value = int(literal)
            else:
                value = float(literal.replace('d', 'e').replace('D', 'e'))
                if not math.isfinite(value):
                    raise AFInputError(text, index, f'{key} must be finite')
            entries[key] = Entry(value, offset, literal)
            index = number.end()
            if index < len(clean) and not (clean[index].isspace() or clean[index] in ',$&'):
                raise AFInputError(text, index, f'unexpected text after {key}; expressions are unsupported')
            index = whitespace(index)
            if index < len(clean) and clean[index] == ',':
                index += 1
        blocks.append((name, start, entries))
    return title, blocks


def parse_af(text, *, nr, nz, modes, conductivity_s_per_m, normalization_j,
             arc_chord_tolerance_m=1e-5):
    """Return a v3 Case and diagnostics for the supported closed-vacuum subset."""
    if not isinstance(text, str):
        raise ValueError('AF input must be decoded text')
    title, blocks = _blocks(text)
    _, start, reg = blocks[0]

    def value(entries, key, fallback=None):
        return entries[key].value if key in entries else fallback

    def error(entries, key, message, fallback=start):
        raise AFInputError(text, entries[key].offset if key in entries else fallback, message)

    fixed = {'kprob': 1, 'icylin': 1, 'nbslo': 0, 'nbsup': 1, 'nbslf': 1,
             'nbsrt': 1, 'beta': 1, 'kmethod': 1}
    for key, expected in fixed.items():
        if value(reg, key) != expected:
            error(reg, key, f'explicit {key}={expected} required for closed vacuum axisymmetric TM import')
    if value(reg, 'mat', 1) != 1:
        error(reg, 'mat', 'only MAT=1 (vacuum) is supported')
    for key in ('conv', 'dx', 'dy', 'freq', 'epsik'):
        if key in reg and reg[key].value <= 0:
            error(reg, key, f'{key} must be positive')
    if ('xdri' in reg) != ('ydri' in reg):
        error(reg, 'xdri' if 'xdri' in reg else 'ydri', 'XDRI and YDRI must be supplied together')
    scale = value(reg, 'conv', 1.) * .01
    if not math.isfinite(scale) or scale <= 0:
        error(reg, 'conv', 'CONV cannot be represented as a positive SI length scale')
    points, arcs = [], []
    point_blocks = blocks[1:]
    for i, (_, position, po) in enumerate(point_blocks):
        for key in ('x', 'y'):
            if key not in po:
                error(po, key, f'explicit PO {key} is required', position)
        point = (po['x'].value * scale, po['y'].value * scale)
        if not all(math.isfinite(v) for v in point):
            error(po, 'x', 'PO coordinates overflow SI conversion', position)
        points.append(point)
        nt = value(po, 'nt', 1)
        if nt not in (1, 4, 5):
            error(po, 'nt', 'only NT=1,4,5 are supported; other curves require G03', position)
        if nt == 1 and 'radius' in po:
            error(po, 'radius', 'RADIUS is supported only with NT=4/5', position)
        if nt in (4, 5):
            if not 2 <= i <= len(point_blocks)-3:
                error(po, 'nt', 'circular arcs are allowed only between wall points', position)
            radius = value(po, 'radius', 0.) * scale
            if not math.isfinite(radius) or radius <= 0:
                error(po, 'radius', 'NT=4/5 requires a positive RADIUS', position)
            arcs.append((i-1, radius, 'ccw' if nt == 4 else 'cw'))
    if len(points) < 5:
        raise AFInputError(text, start, 'expected closed axis-connected contour with at least five PO points')
    if points[0] != (0., 0.) or points[-1] != points[0]:
        raise AFInputError(text, point_blocks[-1][1], 'contour must start and finish at (0,0)')
    if points[1][0] != 0 or points[-2] != (points[-3][0], 0.):
        raise AFInputError(text, point_blocks[-2][1], 'expected flat endplates from axis to the first/last wall point')
    length = points[-3][0]
    if 'zctr' not in reg or not math.isclose(value(reg, 'zctr', 0.) * scale, length/2, rel_tol=1e-12, abs_tol=0.):
        error(reg, 'zctr', 'explicit ZCTR at the full cavity midpoint is required')
    profile = points[1:-2]
    kind = 'arc_profile' if arcs else ('stepped_profile' if any(a[0] == b[0] for a, b in zip(profile, profile[1:])) else 'profile')
    try:
        positive(arc_chord_tolerance_m, 'arc_chord_tolerance_m')
        settings = dict(nr=nr, nz=nz, modes=modes, conductivity_s_per_m=conductivity_s_per_m,
                        normalization_j=normalization_j)
        options = dict(arcs=tuple(arcs), arc_chord_tolerance_m=arc_chord_tolerance_m) if arcs else {}
        case = Case(tuple(profile), geometry_type=kind, name=title or 'imported AF cavity',
                    model=Model(), **settings, **options)
    except ValueError as exc:
        raise AFInputError(text, point_blocks[1][1], f'NG case or settings rejected: {exc}') from exc
    controls = {}
    for key, target, factor in [('dx', 'dx_m', scale), ('dy', 'dy_m', scale),
                                ('xdri', 'drive_z_m', scale), ('ydri', 'drive_r_m', scale),
                                ('freq', 'frequency_initial_hz', 1e6), ('epsik', 'epsik', 1.)]:
        if key in reg:
            converted = reg[key].value * factor
            if not math.isfinite(converted):
                error(reg, key, f'{key} overflows its converted units')
            controls[target] = converted
    declarations = []
    for name, position, entries in blocks:
        declarations.append({'namelist': name.upper(), 'line': text.count('\n', 0, position)+1,
                             'variables': {key: {'value': entry.value, 'literal': entry.literal,
                                'line': text.count('\n', 0, entry.offset)+1,
                                'column': entry.offset-text.rfind('\n', 0, entry.offset)}
                                for key, entry in entries.items()}})
    canonical = json.dumps(case.to_dict(), sort_keys=True, separators=(',', ':'), allow_nan=False)
    report = {'conversion_version': 1, 'scope': 'single vacuum region; axis-connected; closed PEC; m=0 TM; beta=1',
              'input_specification': 'R25 VI.1/2; limited subset documented in docs/LEGACY_INPUT.md',
              'legacy_execution_performed': False, 'legacy_compatibility_status': 'UNVERIFIED',
              'length_scale_m_per_input_unit': scale, 'declarations': declarations,
              'legacy_controls_si': controls, 'ng_settings': dict(settings, arc_chord_tolerance_m=arc_chord_tolerance_m),
              'case_sha256': hashlib.sha256(canonical.encode()).hexdigest(),
              'diagnostics': [
                  'NG uses the explicitly supplied nr/nz; legacy DX/DY mesh controls are recorded, not applied.',
                  'NG solves the lowest requested modes; legacy FREQ/EPSIK/drive controls are recorded, not applied. Mode correspondence is unverified.',
                  'NG uses the explicitly supplied wall conductivity and peak-phasor energy; legacy defaults are not inferred.',
                  'SEG is not imported. NG wall loss includes all real PEC surfaces; legacy selected-surface loss is not reproduced.',
              ]}
    return case, report


def import_af(source, directory, *, encoding='utf-8', **settings):
    """Preserve original bytes and a validated conversion in a new directory."""
    if encoding not in ('utf-8', 'latin-1'):
        raise ValueError('AF encoding must be explicitly utf-8 or latin-1')
    original = Path(source).read_bytes()
    try:
        text = original.decode(encoding)
    except UnicodeDecodeError as exc:
        raise ValueError('AF decoding failed; select the correct --encoding utf-8 or latin-1') from exc
    case, report = parse_af(text, **settings)
    report.update(source_sha256=hashlib.sha256(original).hexdigest(), source_encoding=encoding,
                  source_file='source.af', case_file='case.json')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    (directory/'source.af').write_bytes(original)
    (directory/'case.json').write_text(json.dumps(case.to_dict(), indent=2, allow_nan=False)+'\n', encoding='utf-8')
    (directory/'conversion.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    return case, report
