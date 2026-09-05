# SPDX-License-Identifier: Apache-2.0
"""Run the seminar pillbox, length sweep, field plots and optional Wine check."""
import argparse
from dataclasses import replace
import hashlib
import html
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
import numpy as np
import scipy
from scipy.integrate import simpson
from scipy.special import j1
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from superfish_ng import Case, solve
from superfish_ng.analytic import pillbox_tm_mode
from superfish_ng.constants import C0, EPS0, MU0, TAU
from superfish_ng.io import save_run
from superfish_ng.visualize import plot_mode
from compare_superfish import parse_sfo, read_sf7_line, write_deck, write_json, SIGMA

KEYS = ['frequency_hz', 'q0', 'geometry_factor_ohm', 'r_over_q_accelerator_ohm', 'wall_loss_w', 'transit_time_factor_abs']


def identify_pillbox_mode(case, solution, p):
    """Match the actual 2D eigenfield to J1(alpha*r)/r*cos(p*pi*z/L)."""
    a = pillbox_tm_mode(case.profile[0][1], case.length, p=p)
    r, z = solution.mesh.points.T
    alpha = a['radial_wave_number_per_m']
    template = np.full(len(r), alpha/2)
    np.divide(j1(alpha*r), r, out=template, where=r != 0)
    template *= np.cos(p*np.pi*z/case.length)
    mt = solution.mass @ template
    scores = np.abs(mt @ solution.u)/np.sqrt((template @ mt)*np.sum(solution.u*(solution.mass @ solution.u), axis=0))
    index = int(np.argmax(scores))
    if scores[index] < .99:
        raise ValueError(f'TM01{p} not found by field overlap: maximum {scores[index]:.5f}')
    return index, float(scores[index])


def signed_axis_metrics(sf, ng_axis, reference_energy):
    axis = np.asarray(sf['axis'])
    q = sf['quantities']
    if not np.isfinite(axis).all() or np.any(np.diff(axis[:, 0]) <= 0) or min(reference_energy, q['stored_energy_j']) <= 0:
        raise ValueError('signed axis must be ordered and finite, and normalization energy positive')
    omega = TAU*q['frequency_hz']
    voltage = abs(simpson(axis[:, 1]*np.exp(1j*omega*axis[:, 0]/C0), x=axis[:, 0]))
    absolute = simpson(np.abs(axis[:, 1]), x=axis[:, 0])
    rq = voltage**2/(omega*q['stored_energy_j'])
    native_energy = q['stored_energy_j']
    # Keep all amplitude-dependent output quantities at the same stated energy.
    q = {k: q[k] for k in ['frequency_hz', 'q0', 'geometry_factor_ohm', 'surface_resistance_ohm',
                           'conductivity_s_per_m', 'active_length_m', 'wall_loss_w']}
    q.update(vacc_v=float(voltage*np.sqrt(reference_energy/native_energy)),
             native_vacc_v=float(voltage), native_stored_energy_j=native_energy, stored_energy_j=reference_energy,
             r_over_q_accelerator_ohm=float(rq), r_over_q_circuit_ohm=float(rq/2),
             transit_time_factor_abs=float(voltage/absolute), wall_loss_w=q['wall_loss_w']*reference_energy/native_energy)
    z = np.linspace(axis[0, 0], axis[-1, 0], 4001)
    ea = np.interp(z, axis[:, 0], axis[:, 1])*np.sqrt(reference_energy/sf['quantities']['stored_energy_j'])
    eb = np.interp(z, ng_axis[:, 0], ng_axis[:, 1])
    eb *= 1 if np.dot(ea, eb) > 0 else -1
    error = float(np.sqrt(simpson((ea-eb)**2, x=z)/simpson(ea**2, x=z)))
    return q, error


def gallery(out, cases, passed):
    options, panels = [], []
    for i, case in enumerate(cases):
        for p in (0, 1):
            key = f'{i}-{p}'
            mode = case['levels'][-1]['modes'][p]
            q = mode['quantities']
            label = f'L={case["length_m"]*1000:g} mm / TM01{p}'
            options.append(f'<option value="{key}">{label}</option>')
            rows = ''.join(f'<tr><td>{html.escape(k)}</td><td>{q[k]:.8g}</td></tr>' for k in KEYS)
            panels.append(f'<section id="{key}" class="mode" {"" if i==0 and p==0 else "hidden"}>'
                          f'<h2>{label}</h2><img src="{case["name"]}/TM01{p}.png" alt="{label}の電磁場、電界矢印、軸上・半径方向分布">'
                          f'<p>固有場の一致度：{mode["overlap"]:.8f}。周波数順位：{mode["mode_index"]}。</p>'
                          f'<table>{rows}</table><p><a href="{case["name"]}/radial_TM01{p}.csv">半径方向CSV</a> · '
                          f'<a href="{case["name"]}/n96/ng/axis_{mode["mode_index"]:03d}.csv">軸上CSV</a> · '
                          f'<a href="{case["name"]}/n96/ng/results.json">計算結果JSON</a></p></section>')
    document = ('<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                '<title>Superfish-NG · Pillbox演習</title><style>body{font:16px system-ui;max-width:1150px;margin:32px auto;padding:0 20px;color:#203044;background:#f7f9fc}'
                'h1{font-size:28px}img{max-width:100%;background:white;border-radius:10px}select{font:inherit;padding:10px;min-width:260px}'
                'td{padding:5px 16px;border-bottom:1px solid #dce3eb}a{color:#1263a0}section{margin:24px 0}code{background:#e9eef4;padding:3px}table{background:white}</style>'
                '<h1>教育加速器セミナー · Pillbox演習</h1>'
                f'<p>検証結果：{"PASS" if passed else "FAIL — comparison.jsonを確認"}。半径75 mm、真空、全外壁PEC、β=1、蓄積エネルギー1 J。</p>'
                '<p>モードは固有場と解析解の重なりで同定しています。EとHは90度位相が異なるピーク振幅です。矢印はEの向きを示します。</p>'
                '<label for="mode">空洞長とモード </label><select id="mode">'+''.join(options)+'</select>'+''.join(panels)+
                '<h2>長さと共振周波数</h2><img src="length_sweep.png" alt="空洞長変更に対するTM010とTM011の周波数変化">'
                '<p><a href="comparison.json">全比較結果・解析誤差・実行環境</a> · <a href="length_sweep.csv">長さ掃引CSV</a></p>'
                '<p>別の長さはJSON入力のlength_mを編集して<code>superfish-ng solve case.json --out out/new-run</code>で再計算できます。</p>'
                '<script>document.getElementById("mode").addEventListener("change",e=>{document.querySelectorAll(".mode").forEach(p=>p.hidden=p.id!==e.target.value)})</script></html>')
    (out/'index.html').write_text(document, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--run-legacy', action='store_true')
    parser.add_argument('--reference-run', type=Path, help='reuse verified AF/SFO/SF7 from a previous seminar run')
    args = parser.parse_args()
    out = args.out.resolve()
    if args.run_legacy and args.reference_run:
        parser.error('choose --run-legacy or --reference-run, not both')
    compare_legacy = args.run_legacy or args.reference_run is not None
    if compare_legacy and (not out.is_relative_to(ROOT/'out') or out == ROOT/'out'):
        parser.error('Wine reference output must be under a new project out/ subdirectory')
    out.mkdir(parents=True, exist_ok=False)
    base = Case.load(ROOT/'examples/seminar_pillbox.json')
    report = {'environment': {'python': platform.python_version(), 'numpy': np.__version__, 'scipy': scipy.__version__},
              'scope': 'full closed pillboxes; TM010/TM011; radius .075 m; beta=1; U=1 J',
              'wine_compared': compare_legacy, 'cases': [],
              'limits': {'frequency_relative': .001, 'rf_relative': .01, 'axis_l2': .01},
              'related_exercises': 'scripts/seminar_symmetry.py verifies half-domain electric/magnetic symmetry',
              'not_completed': ['whole-milestone numerical/reference acceptance', 'full-end-cell comparison', 'all-exercise integrated workflow']}
    if args.run_legacy:
        report['environment']['wine'] = subprocess.check_output(['wine', '--version'], text=True).strip()
    elif args.reference_run:
        source = json.loads((args.reference_run/'comparison.json').read_text())
        if not source.get('wine_compared') or not source.get('passed'):
            parser.error('reference run must be a passing Wine comparison')
        report['environment']['wine'] = source['environment']['wine']
        report['reference_run'] = str(args.reference_run.resolve())
    for length in [.04, .08, .12]:
        name = f'L{round(length*1000):03d}mm'
        case_record = {'name': name, 'length_m': length, 'levels': []}
        case_dir = out/name
        for n in [24, 48, 96]:
            case = replace(base, profile=((0., .075), (length, .075)), nr=n,
                           nz=max(12, round(n*length/.075)), modes=4, conductivity_s_per_m=SIGMA,
                           name=f'Seminar pillbox R75mm L{length*1000:g}mm')
            sol = solve(case)
            run = save_run(case, sol, case_dir/f'n{n}'/'ng')
            modes = []
            for p in (0, 1):
                index, score = identify_pillbox_mode(case, sol, p)
                q = run['modes'][index]
                exact = pillbox_tm_mode(.075, length, p=p, conductivity_s_per_m=SIGMA)
                errors = {k: abs(q[k]/exact[k]-1) for k in KEYS}
                modes.append({'label': f'TM01{p}', 'mode_index': index+1, 'overlap': score,
                              'quantities': q, 'analytic': exact, 'relative_errors': errors})
            case_record['levels'].append({'nr': n, 'nz': case.nz, 'nodes': len(sol.mesh.points), 'modes': modes})
        for p in (0, 1):
            finest = case_record['levels'][-1]['modes'][p]
            plot = plot_mode(case_dir/'n96/ng', case_dir/f'TM01{p}.png', finest['mode_index'])
            fields = plot['radial_fields']
            radial = np.column_stack((plot['radial_points_rz_m'], fields['Er_quadrature_V_per_m'], fields['Ez_quadrature_V_per_m'], fields['Hphi_A_per_m']))
            np.savetxt(case_dir/f'radial_TM01{p}.csv', radial, delimiter=',', header='r_m,z_m,Er_quadrature_V_per_m,Ez_quadrature_V_per_m,Hphi_A_per_m', comments='')
            errors = finest['relative_errors']
            finest['analytic_passed'] = all(errors[k] < (.001 if k == 'frequency_hz' else .01) for k in KEYS)
            previous = case_record['levels'][-2]['modes'][p]['quantities']
            finest['refinement_errors'] = {k: abs(finest['quantities'][k]/previous[k]-1) for k in KEYS}
            finest['refinement_passed'] = all(finest['refinement_errors'][k] < (.001 if k=='frequency_hz' else .01) for k in KEYS)
        report['cases'].append(case_record)
        print(f'{name}: '+', '.join(f'{m["label"]}={m["quantities"]["frequency_hz"]/1e6:.6f} MHz (mode {m["mode_index"]})' for m in case_record['levels'][-1]['modes']), flush=True)
    if compare_legacy:
        canonical = report['cases'][1]
        legacy = []
        for p in (0, 1):
            rows = []
            mode = canonical['levels'][-1]['modes'][p]
            for dx in [.2, .1, .05]:
                folder = out/'wine'/f'TM01{p}'/f'dx{dx:g}'
                folder.mkdir(parents=True)
                write_deck(base, folder, dx, 1500 if p == 0 else 2420)
                if args.reference_run:
                    original = source['legacy'][p]['runs'][len(rows)]
                    reference_root = Path(source.get('reference_run', args.reference_run))
                    source_folder = Path(original.get('source_directory', reference_root/'wine'/f'TM01{p}'/f'dx{dx:g}'))
                    for filename in ['cavity.af', 'cavity.seg']:
                        if (folder/filename).read_bytes() != (source_folder/filename).read_bytes():
                            raise ValueError(f'reference input differs: {source_folder/filename}')
                    for filename, hash_key in [('CAVITY.SFO', 'sfo_sha256'), ('OUTSF7.TXT', 'sf7_sha256')]:
                        if hashlib.sha256((source_folder/filename).read_bytes()).hexdigest() != original[hash_key]:
                            raise ValueError(f'reference output hash differs: {source_folder/filename}')
                    folder = source_folder
                else:
                    run_wine_mode(folder)
                sf = parse_sfo(folder/'CAVITY.SFO')
                signed = read_sf7_line(folder/'OUTSF7.TXT')
                if np.max(np.abs(signed[:, 1])) > 1e-12 or abs(signed[-1, 0]-.08) > 1e-10:
                    raise ValueError('SF7 probe is not the complete 80 mm axis')
                sf['axis'] = signed[:, [0, 2]].tolist()
                axis = np.loadtxt(out/'L080mm/n96/ng'/f'axis_{mode["mode_index"]:03d}.csv', delimiter=',', skiprows=1)
                q, field_error = signed_axis_metrics(sf, axis, 1.)
                differences = {k: abs(mode['quantities'][k]/q[k]-1) for k in KEYS}
                rows.append({'dx_cm': dx, 'quantities': q, 'relative_differences': differences,
                             'axis_relative_l2': field_error, 'sfo_version': sf['version'], 'sfo_sha256': sf['sfo_sha256'],
                             'source_directory': str(folder.resolve()),
                             'voltage_source': 'signed SF7 Ez; independent Simpson integration',
                             'sf7_sha256': hashlib.sha256((folder/'OUTSF7.TXT').read_bytes()).hexdigest()})
                print(f'Wine TM01{p} dx={dx}: f={q["frequency_hz"]/1e6:.6f} MHz, R/Q={q["r_over_q_accelerator_ohm"]:.6f} ohm, field L2={field_error:.3%}', flush=True)
            last = rows[-1]
            gates = {k: last['relative_differences'][k] < (.001 if k=='frequency_hz' else .01) for k in KEYS}
            gates['axis_l2'] = last['axis_relative_l2'] < .01
            gates['sf_refinement'] = all(abs(rows[-1]['quantities'][k]/rows[-2]['quantities'][k]-1) < (.001 if k=='frequency_hz' else .01) for k in KEYS)
            legacy.append({'label': f'TM01{p}', 'runs': rows, 'gates': gates, 'passed': all(gates.values())})
        report['legacy'] = legacy
    report['passed'] = all(m['analytic_passed'] and m['refinement_passed'] for c in report['cases'] for m in c['levels'][-1]['modes'])
    if compare_legacy:
        report['passed'] = report['passed'] and all(m['passed'] for m in report['legacy'])
    fig, ax = plt.subplots(figsize=(8, 5), layout='constrained')
    sweep = []
    for p in (0, 1):
        lengths = [c['length_m'] for c in report['cases']]
        f = [c['levels'][-1]['modes'][p]['quantities']['frequency_hz']/1e6 for c in report['cases']]
        ax.plot(np.array(lengths)*1000, f, 'o', label=f'FEM TM01{p}')
        ls = np.linspace(min(lengths), max(lengths), 200)
        ax.plot(ls*1000, [pillbox_tm_mode(.075, l, p=p)['frequency_hz']/1e6 for l in ls], label=f'Analytic TM01{p}')
        sweep.extend([length, p, frequency*1e6] for length, frequency in zip(lengths, f))
    ax.set(xlabel='Cavity length [mm]', ylabel='Frequency [MHz]', title='Pillbox radius 75 mm: length dependence')
    ax.grid(alpha=.3)
    ax.legend()
    fig.savefig(out/'length_sweep.png', dpi=160)
    plt.close(fig)
    np.savetxt(out/'length_sweep.csv', sweep, delimiter=',', header='length_m,axial_index_p,frequency_hz', comments='')
    report['source_sha256'] = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                              for path in sorted((ROOT/'src/superfish_ng').glob('*.py'))}
    report['script_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    write_json(out/'comparison.json', report)
    gallery(out, report['cases'], report['passed'])
    print(f'Seminar pillbox {"PASS" if report["passed"] else "FAIL"}: {out}/index.html', flush=True)
    return 0 if report['passed'] else 1


def run_wine_mode(folder, length_m=.08, timeout_s=120):
    if not np.isfinite(length_m) or length_m <= 0:
        raise ValueError('SF7 axis length must be finite and positive')
    if not np.isfinite(timeout_s) or timeout_s <= 0:
        raise ValueError('Wine timeout must be finite and positive')
    with (folder/'wine.log').open('w') as log:
        proc = subprocess.run([str(ROOT/'run-superfish.sh'), str(folder/'cavity.af')],
                              stdout=log, stderr=subprocess.STDOUT, timeout=timeout_s)
    if proc.returncode:
        raise RuntimeError(f'Wine failed in {folder}')
    (folder/'cavity.in7').write_text(f'line plotfiles\n0 0 {length_m*100:.12g} 0\n800\nend\n')
    with (folder/'sf7.log').open('w') as log:
        proc = subprocess.run(['wine', 'C:\\LANL\\SF7.EXE', 'CAVITY.T35'], cwd=folder,
                              env=dict(os.environ, WINEPREFIX=str(ROOT/'.wine-superfish'), WINEDEBUG='-all'),
                              stdout=log, stderr=subprocess.STDOUT, timeout=timeout_s)
    if proc.returncode:
        raise RuntimeError(f'SF7 failed in {folder}')


if __name__ == '__main__':
    raise SystemExit(main())
