# SPDX-License-Identifier: Apache-2.0
"""Seminar p.28: iris-center full ends versus cavity-center half ends."""
import argparse
from dataclasses import replace
import html
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from superfish_ng import Case, solve
from superfish_ng.geometry import profile_area
from superfish_ng.io import save_run
from superfish_ng.modes import identify_cell_band
from superfish_ng.visualize import plot_mode
from seminar_multicell import relative, gates, digest, read_native
from compare_superfish import write_json


def zero_identification(z, fields, centers):
    """Describe full-end modes by actual zero count, without half-end phase labels."""
    result = []
    for i, field in enumerate(fields.T):
        nonzero = field[np.abs(field) > np.max(np.abs(field))*1e-3]
        count = int(np.count_nonzero(nonzero[:-1]*nonzero[1:] < 0))
        amplitude = np.interp(centers, z, field)
        amplitude /= np.max(np.abs(amplitude))
        if amplitude[0] < 0:
            amplitude *= -1
        result.append({'mode_index': i+1, 'zero_crossings': count,
                       'label': f'full ends: {count} axial zeros (no phase assignment)',
                       'cell_amplitudes_normalized': amplitude.tolist()})
    if sorted(m['zero_crossings'] for m in result) != list(range(4)):
        raise ValueError('full-end lowest band must have unique 0,1,2,3 axial zero counts')
    return sorted(result, key=lambda m: m['zero_crossings'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--families', choices=['flat', 'rounded'], nargs='+', default=['flat', 'rounded'])
    parser.add_argument('--levels', type=int, nargs='+', default=[64, 128, 256])
    parser.add_argument('--flat-half-extra-n', type=int, help='additional refinement for the cancellation-sensitive flat half-end 0 mode')
    parser.add_argument('--native-roots', type=Path, nargs='+', default=[], help='explicit reuse of matching saved native runs; unmatched levels are freshly solved')
    args = parser.parse_args(argv)
    if (len(args.levels) < 3 or any(n < 2 for n in args.levels)
            or any(b <= a for a, b in zip(args.levels, args.levels[1:]))
            or len(set(args.families)) != len(args.families)):
        parser.error('use unique families and at least three strictly increasing positive mesh levels')
    if args.flat_half_extra_n is not None and args.flat_half_extra_n <= args.levels[-1]:
        parser.error('flat-half extra level must exceed the last standard level')
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    sources = sorted((ROOT/'src').rglob('*.py'))+[Path(__file__).resolve(), ROOT/'scripts/seminar_multicell.py',
                                               ROOT/'scripts/compare_superfish.py']+sorted((ROOT/'examples').glob('seminar_4cell_*.json'))
    hashes = {str(p.relative_to(ROOT)): digest(p) for p in sources}
    report = {'scope': 'seminar p.28 boundary-cut comparison; not a tuning or phase-matched comparison',
              'native_computation': 'fresh solves with explicit saved-run reuse' if args.native_roots else 'fresh solves',
              'reference': 'user-provided seminar exercise 1-1 PDF p.28; full ends reconstructed from the illustrated iris-center cuts',
              'wine_compared': False, 'limits': {'frequency_relative': .001, 'rf_relative': .01},
              'families': [], 'source_sha256': hashes,
              'limitations': ['full-end physical phase labels are not assigned', 'corner surface peaks have no convergence guarantee',
                              'full-end variants have no Wine comparison in this report']}
    options, panels, checks = [], [], []
    period = .03499
    for family in args.families:
        family_row = {'family': family, 'ends': {}}
        finest_axes = {}
        for ends in ('half', 'full'):
            filename = f'seminar_4cell_{family}'+('_full_ends' if ends == 'full' else '')+'.json'
            source = ROOT/'examples'/filename
            base = replace(Case.load(source), triangulation='crossed')
            centers = (np.arange(4)+.5)*period if ends == 'full' else np.linspace(0., base.length, 4)
            row = {'case': base.to_dict(), 'input_sha256': digest(source), 'input_file': filename,
                   'cell_centers_m': centers.tolist(), 'levels': []}
            levels = args.levels+([args.flat_half_extra_n] if family == 'flat' and ends == 'half' and args.flat_half_extra_n else [])
            for n in levels:
                case = replace(base, nr=n, nz=round(n*base.nz/base.nr))
                folder = out/'native'/family/ends/f'n{n}'
                reused = False
                for root in args.native_roots:
                    for candidate in (root/'native'/family/ends/f'n{n}', root/family/ends/f'n{n}', root):
                        if (candidate/'case.json').exists() and Case.load(candidate/'case.json') == case:
                            folder = candidate.resolve(); reused = True; break
                    if reused: break
                if not reused:
                    save_run(case, solve(case), folder)
                run, axes = read_native(folder, case)
                z, fields = axes[0][:, 0], np.column_stack([a[:, 1] for a in axes])
                identity = (zero_identification(z, fields, centers) if ends == 'full'
                            else identify_cell_band(z, fields, centers))
                modes = [dict(m, quantities=run['modes'][m['mode_index']-1]) for m in identity]
                files = [folder/'case.json', folder/'results.json', folder/'fields.npz']+list(folder.glob('axis_*.csv'))
                row['levels'].append({'nr': n, 'nz': case.nz, 'directory': str(folder), 'mesh': run['mesh'], 'modes': modes,
                                      'computation': 'imported saved solve' if reused else 'fresh solve',
                                      'file_sha256': {p.name: digest(p) for p in files}, 'environment': run['environment']})
                print(f'{family}/{ends} n={n}: '+', '.join(f"{m['quantities']['frequency_hz']/1e6:.6f}" for m in modes)+' MHz', flush=True)
            for last, previous in zip(row['levels'][-1]['modes'], row['levels'][-2]['modes']):
                last['refinement_errors'] = relative(last['quantities'], previous['quantities'])
                last['refinement_gates'] = gates(last['refinement_errors'])
                checks.extend(last['refinement_gates'].values())
            finest_axes[ends] = axes
            family_row['ends'][ends] = row
        half, full = (Case.from_dict(family_row['ends'][e]['case']) for e in ('half', 'full'))
        family_row['full_to_half_area_ratio'] = profile_area(full)/profile_area(half)
        family_row['periodic_area_invariant_passed'] = abs(family_row['full_to_half_area_ratio']-4/3) < 1e-12
        checks.append(family_row['periodic_area_invariant_passed'])
        fig, axs = plt.subplots(4, 1, figsize=(10, 12), layout='constrained')
        for p in range(4):
            key = f'{family}{p}'
            images = []
            for ends in ('half', 'full'):
                row = family_row['ends'][ends]
                mode = row['levels'][-1]['modes'][p]
                index = mode['mode_index']
                axis = finest_axes[ends][index-1]
                y = axis[:, 1]/np.max(np.abs(axis[:, 1]))
                if np.interp(row['cell_centers_m'][0], axis[:, 0], y) < 0: y *= -1
                axs[p].plot(axis[:, 0]/axis[-1, 0], y, label=f'{ends} ends, {mode["quantities"]["frequency_hz"]/1e6:.4f} MHz')
                axs[p].set(xlabel='Normalized axial coordinate z/L (different physical lengths)',
                           ylabel='Signed Ez / max |Ez|', title=f'{p} axial zeros; not equal phase labels')
                axs[p].legend(fontsize=8); axs[p].grid(alpha=.25)
                target = f'{key}-{ends}.png'
                radial = plot_mode(Path(row['levels'][-1]['directory']), out/target, index,
                                   probe_z_m=row['cell_centers_m'][1], mode_label=mode['label'])
                csv = f'{key}-{ends}-axis.csv'
                np.savetxt(out/csv, axis, delimiter=',', header='z_m,Ez_quadrature_V_per_m', comments='')
                values = radial['radial_fields']
                radial_csv = f'{key}-{ends}-radial.csv'
                np.savetxt(out/radial_csv, np.column_stack((radial['radial_points_rz_m'], values['Er_quadrature_V_per_m'],
                                                          values['Ez_quadrature_V_per_m'], values['Hphi_A_per_m'])),
                           delimiter=',', header='r_m,z_m,Er_quadrature_V_per_m,Ez_quadrature_V_per_m,Hphi_A_per_m', comments='')
                images.append(f'<h3>{ends}-cell ends</h3><img src="{target}" alt="{family} {ends} ends: fields and probes">'
                              f'<p><a href="{csv}">軸上CSV</a> · <a href="{radial_csv}">半径方向CSV</a></p>')
            options.append(f'<option value="{key}">{family}: 軸上零交差{p}個</option>')
            panels.append(f'<section id="{key}" class="mode" {"hidden" if panels else ""}><h2>{family}: 零交差{p}個</h2>'+''.join(images)+'</section>')
        fig.suptitle(f'{family}: cavity-center half ends versus iris-center full ends')
        fig.savefig(out/f'{family}-comparison.png', dpi=150); plt.close(fig)
        report['families'].append(family_row)
    report['source_changed_during_run'] = hashes != {str(p.relative_to(ROOT)): digest(p) for p in sources}
    report['passed'] = all(checks) and not report['source_changed_during_run']
    write_json(out/'comparison.json', report)
    (out/'index.html').write_text('<!doctype html><html lang="ja"><meta charset="utf-8"><title>Superfish-NG end cells</title>'
        '<style>body{font:16px system-ui;max-width:1150px;margin:32px auto;padding:0 20px}img{width:100%}select{font:inherit;padding:8px}</style>'
        f'<h1>端部full-cell / half-cell比較</h1><p>{"PASS" if report["passed"] else "FAIL — 数値ゲート未達"} · NG細分検査。Wine照合なし。</p>'
        '<p>資料p.28の切断面から構成。全長half=104.97 mm、full=139.96 mm。真空・全外壁PEC・β=1・U=1 J。'
        '零交差数で並べており、同じ位相進みを比較したものではありません。ピーク場の収束保証なし。</p>'
        '<label for="selector">形状とモード </label><select id="selector">'+''.join(options)+'</select>'+''.join(panels)+
        ''.join(f'<h2>{html.escape(f)}：正規化軸場比較</h2><img src="{f}-comparison.png" alt="{f}: normalized signed axis comparison">' for f in args.families)+
        '<p><a href="comparison.json">入力・環境・場hash・収束検査</a></p>'
        '<script>document.getElementById("selector").addEventListener("change",e=>document.querySelectorAll(".mode").forEach(s=>s.hidden=s.id!==e.target.value))</script></html>', encoding='utf-8')
    print(f'{"PASS" if report["passed"] else "FAIL"}: {out}/index.html', flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
