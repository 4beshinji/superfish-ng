# SPDX-License-Identifier: Apache-2.0
"""Verify/plot half-domain pillboxes against full FEM, theory and signed Wine SF7."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
import numpy as np
from scipy.integrate import simpson
from superfish_ng import Case, solve
from superfish_ng.analytic import pillbox_tm_mode
from superfish_ng.io import save_run
from superfish_ng.symmetry import reflect_solution
from superfish_ng.visualize import plot_mode
from seminar_pillbox import KEYS, identify_pillbox_mode, signed_axis_metrics
from compare_superfish import parse_sfo, read_sf7_line, write_deck, write_json


def gate(errors):
    return all(value < (.001 if key == 'frequency_hz' else .01) for key, value in errors.items())


def axis_error(first, second):
    z = np.linspace(0., .08, 4001)
    a, b = (np.interp(z, axis[:, 0], axis[:, 1]) for axis in (first, second))
    b *= 1 if np.dot(a, b) >= 0 else -1
    return float(np.sqrt(simpson((a-b)**2, x=z)/simpson(a*a, x=z)))


def load_reference(path, base, out):
    """Read raw signed outputs only after input/output provenance verification."""
    source = json.loads((path/'comparison.json').read_text())
    if not source.get('wine_compared') or not source.get('passed'):
        raise ValueError('reference must be a passing full-pillbox Wine comparison')
    references = []
    for p in (0, 1):
        records = source['legacy'][p]
        if records['label'] != f'TM01{p}':
            raise ValueError('unexpected reference mode label')
        row = records['runs'][-1]
        folder = Path(row['source_directory'])
        with tempfile.TemporaryDirectory(prefix='reference-input-', dir=out) as temp:
            write_deck(base, Path(temp), row['dx_cm'], 1500 if p == 0 else 2420)
            for name in ('cavity.af', 'cavity.seg'):
                if (Path(temp)/name).read_bytes() != (folder/name).read_bytes():
                    raise ValueError(f'reference input differs: {folder/name}')
        for name, key in [('CAVITY.SFO', 'sfo_sha256'), ('OUTSF7.TXT', 'sf7_sha256')]:
            if hashlib.sha256((folder/name).read_bytes()).hexdigest() != row[key]:
                raise ValueError(f'reference output hash differs: {folder/name}')
        sf = parse_sfo(folder/'CAVITY.SFO')
        fields = read_sf7_line(folder/'OUTSF7.TXT')
        if np.max(np.abs(fields[:, 1])) > 1e-12 or abs(fields[0, 0]) > 1e-12 or abs(fields[-1, 0]-.08) > 1e-10:
            raise ValueError('reference probe must cover the full 80 mm axis')
        sf['axis'] = fields[:, [0, 2]].tolist()
        references.append((sf, row))
    return references


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--reference-run', type=Path, help='verified full-pillbox Wine run; no Wine execution here')
    args = parser.parse_args(argv)
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    base = Case.load(ROOT/'examples/seminar_pillbox.json')
    refs = load_reference(args.reference_run.resolve(), base, out) if args.reference_run else None
    report = {'scope': 'R75mm L80mm pillbox: half domain L40mm, both symmetry types and both ends',
              'normalization': 'half U=0.5 J; reflected full U=1 J; physical amplitudes unchanged',
              'wine_compared': refs is not None, 'wine_scope': 'reflected NG fields compared to raw full-domain Wine SF7; Wine half decks not run',
              'limits': {'frequency_relative': .001, 'rf_relative': .01, 'axis_l2': .01}, 'cases': []}
    full_runs = {}
    for n in (24, 48, 96):
        nz_half = round(n*.04/.075)
        case = replace(base, nr=n, nz=2*nz_half, modes=2)
        sol = solve(case)
        run = save_run(case, sol, out/'full'/f'n{n}')
        full_runs[n] = (case, sol, run)
    panels = []
    for side in ('z_min', 'z_max'):
        for p, boundary in enumerate(('electric_symmetry', 'magnetic_symmetry')):
            name = f'TM01{p}-{side}'
            record = {'name': name, 'boundary': boundary, 'side': side, 'levels': []}
            for n in (24, 48, 96):
                folder = out/name/f'n{n}'
                half = replace(base, profile=((0., .075), (.04, .075)), nr=n,
                               nz=round(n*.04/.075), modes=1, normalization_j=.5,
                               name=f'TM01{p}: {boundary} at {side}', **{side: boundary})
                sol = solve(half)
                half_run = save_run(half, sol, folder/'half')
                full, reflected = reflect_solution(half, sol)
                full_run = save_run(full, reflected, folder/'reflected')
                index, overlap = identify_pillbox_mode(full, reflected, p)
                if index != 0:
                    raise ValueError('unexpected reflected mode index')
                q = full_run['modes'][0]
                exact = pillbox_tm_mode(.075, .08, p=p, conductivity_s_per_m=base.conductivity_s_per_m)
                direct_case, direct_sol, direct_run = full_runs[n]
                direct_index, _ = identify_pillbox_mode(direct_case, direct_sol, p)
                direct = direct_run['modes'][direct_index]
                axis = np.loadtxt(folder/'reflected/axis_001.csv', delimiter=',', skiprows=1)
                direct_axis = np.loadtxt(out/'full'/f'n{n}'/f'axis_{direct_index+1:03d}.csv', delimiter=',', skiprows=1)
                row = {'nr': n, 'nz_half': half.nz, 'half': half_run['modes'][0], 'reflected': q,
                       'overlap': overlap,
                       'analytic_relative_errors': {k: abs(q[k]/exact[k]-1) for k in KEYS},
                       'full_fem_relative_differences': {k: abs(q[k]/direct[k]-1) for k in KEYS},
                       'full_fem_axis_l2': axis_error(direct_axis, axis)}
                record['levels'].append(row)
            last, previous = record['levels'][-1], record['levels'][-2]
            last['refinement_errors'] = {k: abs(last['reflected'][k]/previous['reflected'][k]-1) for k in KEYS}
            gates = {'analytic': gate(last['analytic_relative_errors']), 'full_fem': gate(last['full_fem_relative_differences']),
                     'full_fem_axis': last['full_fem_axis_l2'] < .01, 'refinement': gate(last['refinement_errors'])}
            if refs:
                sf, provenance = refs[p]
                qsf, field_error = signed_axis_metrics(sf, axis, 1.)
                differences = {k: abs(last['reflected'][k]/qsf[k]-1) for k in KEYS}
                record['wine'] = {'quantities': qsf, 'relative_differences': differences, 'axis_l2': field_error,
                                  'source_directory': provenance['source_directory'], 'sfo_sha256': provenance['sfo_sha256'],
                                  'sf7_sha256': provenance['sf7_sha256'], 'sfo_version': sf['version']}
                gates.update(wine_rf=gate(differences), wine_axis=field_error < .01)
            record.update(gates=gates, passed=all(gates.values()))
            report['cases'].append(record)
            for kind in ('half', 'reflected'):
                plot_mode(out/name/'n96'/kind, out/name/f'{kind}.png')
            panels.append(f'<section><h2>{name}: {boundary}</h2><p>half U=0.5 J / reflected full U=1 J</p>'
                          f'<img src="{name}/half.png" alt="{name} half-domain fields">'
                          f'<img src="{name}/reflected.png" alt="{name} reflected full fields">'
                          f'<p><a href="{name}/n96/half/results.json">Half RF</a> · '
                          f'<a href="{name}/n96/reflected/results.json">Full RF</a> · '
                          f'<a href="{name}/n96/reflected/axis_001.csv">Full axis CSV</a></p></section>')
            print(f'{name}: {"PASS" if record["passed"] else "FAIL"}, f={last["reflected"]["frequency_hz"]/1e6:.6f} MHz, full FEM axis error={last["full_fem_axis_l2"]:.3%}', flush=True)
    report['passed'] = all(row['passed'] for row in report['cases'])
    report['environment'] = full_runs[96][2]['environment']
    paths = sorted((ROOT/'src').rglob('*.py'))+[Path(__file__).resolve(), ROOT/'scripts/seminar_pillbox.py', ROOT/'scripts/compare_superfish.py']
    report['source_sha256'] = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    write_json(out/'comparison.json', report)
    (out/'index.html').write_text('<!doctype html><html lang="ja"><meta charset="utf-8"><title>Superfish-NG symmetry</title>'
                                '<style>body{font:16px system-ui;max-width:1150px;margin:30px auto}img{width:100%}section{margin:40px 0}</style>'
                                '<h1>Pillbox半領域・対称境界</h1>'
                                f'<p>{"PASS" if report["passed"] else "FAIL"} · <a href="comparison.json">検証結果</a></p>'
                                '<p>対称面の壁損失は除外。半領域のR/Qは全空洞のR/Qではありません。全空洞の値は場の鏡映後に積分しています。</p>'
                                +''.join(panels)+'</html>', encoding='utf-8')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
