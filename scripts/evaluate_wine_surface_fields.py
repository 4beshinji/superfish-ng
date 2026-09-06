# SPDX-License-Identifier: Apache-2.0
"""Opt-in Wine black-box surface probes for the NG corner diagnostic.

Only input decks, configuration and numerical outputs are read. The caller
provides a Wine executable/wrapper configured for a separate installation.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
import numpy as np
from superfish_ng import Case
from compare_superfish import NUMBER, parse_sfo, write_deck
from evaluate_surface_fields import sharp_probes, write_json

HEADER = r'^\s*\(cm\)\s+\(cm\)\s+\(MV/m\)\s+\(MV/m\)\s+\(MV/m\)\s+\(A/m\)\s*$'


def parse_sf7_tables(path):
    """Keep each requested line separate; accept only explicit signed SI tables."""
    text = path.read_text(encoding='latin-1')
    headers = list(re.finditer(HEADER, text, re.M))
    tables = []
    for header in headers:
        rows = []
        for line in text[header.end():].splitlines():
            fields = line.split()
            if not fields and not rows:
                continue
            if len(fields) != 6 or any(re.fullmatch(NUMBER, v) is None for v in fields):
                break
            rows.append([float(v.replace('D', 'E')) for v in fields])
        table = np.asarray(rows)
        if len(table) < 3 or not np.isfinite(table).all():
            raise ValueError('incomplete SF7 line table')
        table[:, :2] /= 100
        table[:, 2:5] *= 1e6
        if not np.allclose(np.hypot(table[:, 2], table[:, 3]), table[:, 4], rtol=3e-5, atol=1e-3):
            raise ValueError('SF7 component magnitudes disagree')
        tables.append(table)
    if not tables:
        raise ValueError('missing signed SF7 tables')
    return tables


def inset_probes(base, inset_m):
    """Same fixed wall distances, displaced by a stated inward normal offset."""
    if not np.isfinite(inset_m) or inset_m <= 0:
        raise ValueError('inward offset must be positive and finite')
    vertices = np.asarray(base.profile)
    probes = []
    for p in sharp_probes(base):
        i = p['corner_index']
        delta = vertices[i]-vertices[i-1] if p['side'] == 'before' else vertices[i+1]-vertices[i]
        tangent = delta/np.linalg.norm(delta)
        normal_rz = np.array([-tangent[0], tangent[1]])
        probes.append(dict(p, surface_point_rz_m=p['point_rz_m'], inset_m=inset_m,
                           point_rz_m=(np.array(p['point_rz_m'])+inset_m*normal_rz).tolist()))
    return probes


def probe_input(base, insets=(1e-7, 1e-6)):
    probes = [p for inset in insets for p in inset_probes(base, inset)]
    groups = [probes[i:i+5] for i in range(0, len(probes), 5)]
    lines = []
    for group in groups:
        start, end = [np.array(p['point_rz_m'])[::-1]*100 for p in [group[0], group[-1]]]
        lines.append('line plotfiles\n'+' '.join(f'{v:.12g}' for v in [*start, *end])+'\n15\n')
    return ''.join(lines)+'end\n', groups


def run(wine, executable, argument, folder, logfile, timeout):
    command = [str(wine), executable, argument]
    with (folder/logfile).open('w') as stream:
        result = subprocess.run(command, cwd=folder, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'{executable} failed with exit={result.returncode}; see {folder/logfile}')
    return {'command': command, 'exit_code': result.returncode}


def write_surface_deck(case, folder, dx):
    """Export tangent control arcs using documented NT=4 ccw / NT=5 cw."""
    polygon_vertices = replace(case, geometry_type='profile', arcs=(), arc_chord_tolerance_m=1e-5)
    write_deck(polygon_vertices, folder, dx, 1270.)
    arcs = {index+1: (radius, direction) for index, radius, direction in case.arcs}
    lines, po_index = [], 0
    for line in (folder/'cavity.af').read_text().splitlines(keepends=True):
        if line.startswith('$po '):
            if po_index in arcs:
                radius, direction = arcs[po_index]
                nt = 4 if direction == 'ccw' else 5
                line = line.replace(' $', f', nt={nt}, radius={radius*100:.12g} $')
            po_index += 1
        lines.append(line)
    (folder/'cavity.af').write_text(''.join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wine', type=Path, required=True)
    parser.add_argument('--ng-report', type=Path, required=True)
    parser.add_argument('--ng-inset-report', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--dx-cm', type=float, nargs='+', default=[.2, .1, .05, .025])
    parser.add_argument('--timeout-s', type=float, default=600)
    parser.add_argument('--reuse-sharp', type=Path, help='reuse fully checked sharp rows from an earlier report; rerun rounded')
    args = parser.parse_args()
    if (len(args.dx_cm) < 3 or not np.isfinite(args.dx_cm).all() or min(args.dx_cm) <= 0
            or sorted(set(args.dx_cm), reverse=True) != args.dx_cm):
        parser.error('DX must contain at least three strictly decreasing positive values')
    out = args.out.resolve()
    if not out.is_relative_to(ROOT/'out') or out == ROOT/'out':
        parser.error('raw Wine results must remain under project out/')
    out.mkdir(parents=True, exist_ok=False)
    base = replace(Case.load(ROOT/'examples/shaped_cell.json'), modes=1, conductivity_s_per_m=1/1.7241e-8)
    in7, groups = probe_input(base)
    native = json.loads(args.ng_report.read_text())
    inset_native = json.loads(args.ng_inset_report.read_text())
    report = {'status': 'RUNNING', 'wine': str(args.wine.resolve()),
              'ng_report_sha256': hashlib.sha256(args.ng_report.read_bytes()).hexdigest(),
              'ng_inset_report_sha256': hashlib.sha256(args.ng_inset_report.read_bytes()).hexdigest(),
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'raw_output_redistribution': False, 'sharp': [], 'rounded': [],
              'normalization': 'SF7 field magnitude rescaled from SFO energy to 1 J; peak phasors'}
    arc = Case.load(args.ng_report.parent/'fillets-2.5e-07.json')
    report['rounded_reference_geometry'] = 'Tangent radius 3 mm arcs (NT4/NT5); NG uses chord tolerance 0.25 um, independently checked at 1 um.'
    if args.reuse_sharp:
        old = json.loads(args.reuse_sharp.read_text())
        if ([r['dx_cm'] for r in old['sharp']] != args.dx_cm or
                any(old[k] != report[k] for k in ['ng_report_sha256', 'ng_inset_report_sha256'])):
            raise ValueError('sharp reference meshes or NG input hashes differ')
        for row in old['sharp']:
            folder = Path(row.get('source_directory', args.reuse_sharp.parent/f'sharp-dx{row["dx_cm"]:g}')).resolve()
            for filename, expected in row['sha256'].items():
                if hashlib.sha256((folder/filename).read_bytes()).hexdigest() != expected:
                    raise ValueError(f'sharp reference changed: {folder/filename}')
            with tempfile.TemporaryDirectory() as temporary:
                write_surface_deck(base, Path(temporary), row['dx_cm'])
                if any((Path(temporary)/filename).read_bytes() != (folder/filename).read_bytes() for filename in ['cavity.af', 'cavity.seg']):
                    raise ValueError('sharp reference geometry differs')
            if (folder/'cavity.in7').read_text() != in7:
                raise ValueError('sharp reference probe coordinates differ')
            row['source_directory'] = str(folder)
            row['reused'] = True
            report['sharp'].append(row)
        report['sharp_reference_report_sha256'] = hashlib.sha256(args.reuse_sharp.read_bytes()).hexdigest()
    for name, case in [('sharp', base), ('rounded', arc)]:
        if name == 'sharp' and args.reuse_sharp:
            continue
        for dx in args.dx_cm:
            folder = out/f'{name}-dx{dx:g}'
            folder.mkdir()
            write_surface_deck(case, folder, dx)
            # Output precision affects printing only; disable coefficient tables.
            (folder/'SF.INI').write_text('[Global]\nTAPE40=C\nStoreTempDataInRAM=No\n[SF7]\nDecimalPlaces=10\nExpandedTable=No\n')
            start = time.perf_counter()
            commands = [run(args.wine.resolve(), r'C:\LANL\AUTOFISH.EXE', 'cavity.af', folder, 'wine.log', args.timeout_s)]
            sf = parse_sfo(folder/'CAVITY.SFO')
            row = {'dx_cm': dx, 'sf': sf, 'commands': commands, 'probes': [], 'source_directory': str(folder)}
            if name == 'sharp':
                (folder/'cavity.in7').write_text(in7)
                commands.append(run(args.wine.resolve(), r'C:\LANL\SF7.EXE', 'CAVITY.T35', folder, 'sf7.log', args.timeout_s))
                tables = parse_sf7_tables(folder/'OUTSF7.TXT')
                if len(tables) != len(groups):
                    raise ValueError('SF7 did not return all requested corner-side lines')
                for group, table in zip(groups, tables):
                    if len(table) != 16:
                        raise ValueError('SF7 line must contain 16 points')
                    for probe in group:
                        target = np.array(probe['point_rz_m'])[::-1]
                        # SF7 coordinates use six significant digits, independent
                        # of field DecimalPlaces; derive each rounding allowance.
                        tolerance = 5.1*10.**(np.floor(np.log10(np.maximum(np.abs(target), 1e-30)))-6)
                        indices = np.flatnonzero(np.all(np.abs(table[:, :2]-target) <= tolerance, axis=1))
                        if len(indices) != 1:
                            raise ValueError('SF7 table does not contain the requested physical coordinate')
                        field = table[indices[0]]
                        e = float(field[4]/np.sqrt(sf['quantities']['stored_energy_j']))
                        if e <= 0:
                            raise ValueError('zero SF7 inset field: inspect boundary classification before comparison')
                        comparisons = {}
                        for series in ['sharp_diagonal', 'sharp_crossed']:
                            ng = next(p for p in inset_native['runs'][series][-1]['probes']
                                      if all(p[k] == probe[k] for k in ['corner_index', 'side', 'distance_m', 'inset_m']))
                            comparisons[series] = {'ng_e_v_per_m': ng['e_v_per_m'],
                                                   'relative_difference': abs(ng['e_v_per_m']/e-1)}
                        row['probes'].append(dict(probe, e_v_per_m=e, ng_comparisons=comparisons,
                                                 printed_coordinate_error_m=float(np.linalg.norm(field[:2]-target))))
            row['seconds'] = time.perf_counter()-start
            row['sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()
                             if p.suffix.lower() in ['.af', '.seg', '.in7', '.ini', '.sfo', '.txt']}
            report[name].append(row)
            write_json(folder/'result.json', row)
            write_json(out/'report.json', report)
            print(f'{name} DX={dx:g} cm: Epk/Eacc={sf["quantities"]["epk_over_eacc_estimate"]:.8f}', flush=True)
    report['status'] = 'COMPUTED_NO_AUTOMATIC_ACCURACY_RANKING'
    write_json(out/'report.json', report)


if __name__ == '__main__':
    main()
