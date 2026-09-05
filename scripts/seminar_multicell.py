# SPDX-License-Identifier: Apache-2.0
"""Multicell seminar: field identity, refinement, Wine comparison and plots."""
import argparse
from copy import deepcopy
from dataclasses import replace
import hashlib
import html
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
import numpy as np
import scipy
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from superfish_ng import Case, solve
from superfish_ng.constants import EPS0, TAU
from superfish_ng.io import save_run
from superfish_ng.modes import identify_cell_band, fit_dispersion
from superfish_ng.visualize import plot_mode
from compare_superfish import parse_sfo, read_sf7_line, write_deck, write_json
from seminar_pillbox import KEYS, signed_axis_metrics, run_wine_mode

EXERCISES = {
    'flat4': ('seminar_4cell_flat.json', [2836, 2843.5, 2858.5, 2866]),
    'rounded4': ('seminar_4cell_rounded.json', [2837, 2843, 2855, 2864]),
    'rounded7': ('seminar_7cell_rounded.json', [2837, 2839, 2844, 2850, 2857, 2862, 2864]),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_native(path, expected):
    """Read an explicitly supplied saved solve, checking input and field exports.

    This is evidence reuse, not a fresh solve; file hashes and that distinction
    are retained in the report. Default operation always performs a new solve.
    """
    run = json.loads((path/'results.json').read_text())
    if Case.from_dict(run['case']) != expected or Case.load(path/'case.json') != expected:
        raise ValueError(f'saved native input differs: {path}')
    canonical = json.dumps(expected.to_dict(), sort_keys=True, separators=(',', ':'), allow_nan=False)
    if run['case_sha256'] != hashlib.sha256(canonical.encode()).hexdigest():
        raise ValueError(f'saved native case hash is inconsistent: {path}')
    if len(run['modes']) != expected.modes or 'reflection_source_case' in run:
        raise ValueError('native reference must be a complete direct spectrum')
    axes = [np.loadtxt(path/f'axis_{i+1:03d}.csv', delimiter=',', skiprows=1) for i in range(expected.modes)]
    with np.load(path/'fields.npz', allow_pickle=False) as data:
        z = data['points_rz_m'][data['axis_nodes'], 1]
        ez = 2*data['u_a_per_m2'][data['axis_nodes']]/(TAU*EPS0*data['frequencies_hz'])
        for i, (axis, q) in enumerate(zip(axes, run['modes'])):
            if (q['frequency_hz'] != data['frequencies_hz'][i] or q['relative_eigen_residual'] > 1e-7
                    or not np.isfinite(axis).all() or not np.allclose(axis[:, 0], z, rtol=0, atol=1e-14)
                    or not np.allclose(axis[:, 1], ez[:, i], rtol=1e-12, atol=1e-8)):
                raise ValueError(f'saved native field exports are inconsistent: {path}')
    return run, axes


def relative(first, second):
    return {key: abs(first[key]/second[key]-1) for key in KEYS}


def gates(errors):
    return {key: value < (.001 if key == 'frequency_hz' else .01) for key, value in errors.items()}


def finer_dx(value, previous):
    dx = float(value)
    if not np.isfinite(dx) or not 0 < dx < previous:
        raise ValueError('supplemental Wine dx must be positive and strictly finer than this mode\'s previous dx')
    return dx


def replacement_identity(case, phase_rows, phase_index, candidate):
    """Re-identify the complete band after one independently refined mode changes.

    These are separate eigenproblems at per-mode mesh sizes, not one uniform
    finer mesh. Raw fields are unchanged; only a temporary identification grid
    is interpolated. Wrong/duplicate modes must fail the complete assignment.
    """
    rows = list(phase_rows)
    rows[phase_index] = (candidate, None)
    z = np.asarray(rows[0][0]['axis'])[:, 0]
    fields = np.column_stack([np.interp(z, np.asarray(sf['axis'])[:, 0], np.asarray(sf['axis'])[:, 1]) for sf, _ in rows])
    identity = identify_cell_band(z, fields, np.linspace(0., case.length, case.modes))
    if any(m['mode_index'] != i+1 for i, m in enumerate(identity)):
        raise ValueError('supplemental reference does not replace the requested physical phase')
    return identity[phase_index]


def mode_comparison(case, mode, sf, directory, native_q, native_axis, dx):
    q, error = signed_axis_metrics(sf, native_axis, case.normalization_j)
    difference = relative(native_q, q)
    return dict(mode, dx_cm=dx, quantities=q, relative_differences=difference,
                axis_relative_l2=error, gates=dict(gates(difference), axis_l2=error < .01),
                source_directory=str(directory),
                file_sha256={name: digest(directory/name) for name in
                             ['cavity.af', 'cavity.seg', 'CAVITY.SFO', 'OUTSF7.TXT']+
                             (['SF.INI'] if (directory/'SF.INI').is_file() else [])},
                sfo_version=sf['version'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--case', choices=list(EXERCISES), default='flat4')
    parser.add_argument('--levels', type=int, nargs='+')
    parser.add_argument('--triangulation', choices=['diagonal', 'crossed'], help='explicit P1 quad subdivision; default preserves the input')
    parser.add_argument('--chord-tolerance-m', type=float, help='arc sagitta bound, independent of FEM mesh counts')
    parser.add_argument('--native-runs', type=Path, nargs='+', help='reuse matching saved native runs, in level order; explicitly recorded')
    parser.add_argument('--run-legacy', action='store_true')
    parser.add_argument('--reference-dirs', type=Path, nargs='+', help='raw Wine roots with dxVALUE/modeN (or modeN) directories; exact input checked')
    parser.add_argument('--wine-dx', type=float, nargs='+', default=[.05, .025, .0125])
    parser.add_argument('--wine-timeout-s', type=float, default=600.)
    parser.add_argument('--extra-wine-reference', action='append', nargs=3, default=[],
                        metavar=('PHASE_INDEX', 'DX_CM', 'DIRECTORY'),
                        help='saved supplemental refinement for one physical phase (0-based), independently re-identified; repeat for further levels')
    args = parser.parse_args(argv)
    if args.levels is None:
        args.levels = [128, 256, 512] if args.case == 'flat4' else [32, 64, 128]
    if (len(args.levels) < 3 or any(n < 2 for n in args.levels)
            or any(b <= a for a, b in zip(args.levels, args.levels[1:]))):
        parser.error('at least three strictly increasing native mesh levels are required')
    if args.native_runs and len(args.native_runs) != len(args.levels):
        parser.error('supply one saved native run per level')
    if args.run_legacy and args.reference_dirs:
        parser.error('choose live Wine or saved reference directories')
    if (len(args.wine_dx) < 3 or any(not np.isfinite(dx) or dx <= 0 for dx in args.wine_dx)
            or any(b >= a for a, b in zip(args.wine_dx, args.wine_dx[1:]))):
        parser.error('at least three strictly decreasing positive Wine mesh sizes are required')
    out = args.out.resolve()
    compare = args.run_legacy or args.reference_dirs is not None
    if args.extra_wine_reference and not compare:
        parser.error('supplemental Wine references require a full-band Wine comparison')
    if compare and (not out.is_relative_to(ROOT/'out') or out == ROOT/'out'):
        parser.error('reference data must remain under a new project out/ directory')
    out.mkdir(parents=True, exist_ok=False)
    source_paths = sorted((ROOT/'src').rglob('*.py'))+[Path(__file__).resolve(), ROOT/'scripts/compare_superfish.py', ROOT/'scripts/seminar_pillbox.py']
    source_at_start = {str(p.relative_to(ROOT)): digest(p) for p in source_paths}
    filename, starts = EXERCISES[args.case]
    base = Case.load(ROOT/'examples'/filename)
    if args.triangulation is not None:
        base = replace(base, triangulation=args.triangulation)
    if args.chord_tolerance_m is not None:
        if base.geometry_type != 'arc_profile':
            parser.error('chord tolerance is only meaningful for arc_profile exercises')
        base = replace(base, arc_chord_tolerance_m=args.chord_tolerance_m)
    count = base.modes
    centers = np.linspace(0., base.length, count)
    report = {'case': base.to_dict(), 'exercise': args.case, 'scope': f'{base.name}; beta=1; U=1 J',
              'wine_compared': compare, 'native_computation': 'imported saved solves' if args.native_runs else 'fresh solves',
              'cell_centers_m': centers.tolist(), 'levels': [], 'legacy': [],
              'limits': {'frequency_relative': .001, 'rf_relative': .01, 'axis_l2': .01, 'cell_overlap_minimum': .98},
              'not_completed': ['other exercise families are separate runs', 'full-end-cell comparison', 'all-exercise integrated workflow']}
    for number, n in enumerate(args.levels):
        case = replace(base, nr=n, nz=round(n*base.nz/base.nr))
        path = args.native_runs[number].resolve() if args.native_runs else out/'native'/f'n{n}'
        if not args.native_runs:
            save_run(case, solve(case), path)
        run, axes = read_native(path, case)
        identity = identify_cell_band(axes[0][:, 0], np.column_stack([a[:, 1] for a in axes]), centers)
        modes = [dict(mode, quantities=run['modes'][mode['mode_index']-1]) for mode in identity]
        paths = [path/'case.json', path/'results.json', path/'fields.npz']+[path/f'axis_{i+1:03d}.csv' for i in range(count)]
        row = {'nr': n, 'nz': case.nz, 'mesh': run['mesh'], 'directory': str(path),
               'file_sha256': {p.name: digest(p) for p in paths}, 'modes': modes}
        report['levels'].append(row)
        print(f'NG n={n}: '+', '.join(f"{m['label']} {m['quantities']['frequency_hz']/1e6:.6f} MHz" for m in modes), flush=True)
    finest, previous = report['levels'][-1], report['levels'][-2]
    native_gates = []
    for last, prev in zip(finest['modes'], previous['modes']):
        last['refinement_errors'] = relative(last['quantities'], prev['quantities'])
        last['refinement_gates'] = gates(last['refinement_errors'])
        native_gates.extend(last['refinement_gates'].values())
    if compare:
        for dx in args.wine_dx:
            sf_rows, sf_axes = [], []
            for i, start in enumerate(starts):
                directory = out/'wine'/f'dx{dx:g}'/f'mode{i+1}'
                directory.mkdir(parents=True)
                write_deck(base, directory, dx, start)
                if args.reference_dirs:
                    matches = []
                    for root in args.reference_dirs:
                        for candidate in (root/f'dx{dx:g}'/f'mode{i+1}', root/f'mode{i+1}'):
                            if all((candidate/name).exists() and (candidate/name).read_bytes() == (directory/name).read_bytes()
                                   for name in ('cavity.af', 'cavity.seg')) and (candidate/'OUTSF7.TXT').exists():
                                matches.append(candidate.resolve())
                    if not matches:
                        raise ValueError(f'no matching complete Wine reference for dx={dx}, launch {i+1}')
                    directory = matches[0]
                else:
                    run_wine_mode(directory, base.length, args.wine_timeout_s)
                sf = parse_sfo(directory/'CAVITY.SFO')
                data = read_sf7_line(directory/'OUTSF7.TXT')
                if np.max(np.abs(data[:, 1])) > 1e-12 or abs(data[0, 0]) > 1e-12 or abs(data[-1, 0]-base.length) > 1e-10:
                    raise ValueError('Wine signed axis does not cover the full input domain')
                sf['axis'] = data[:, [0, 2]].tolist()
                sf_rows.append((sf, directory))
                sf_axes.append(data[:, [0, 2]])
            z = sf_axes[0][:, 0]
            fields = np.column_stack([np.interp(z, axis[:, 0], axis[:, 1]) for axis in sf_axes])
            identity = identify_cell_band(z, fields, centers)
            modes = []
            for p, mode in enumerate(identity):
                sf, directory = sf_rows[mode['mode_index']-1]
                index = finest['modes'][p]['mode_index']-1
                modes.append(mode_comparison(base, mode, sf, directory, finest['modes'][p]['quantities'], axes[index], dx))
            report['legacy'].append({'dx_cm': dx, 'modes': modes})
            print(f'Wine dx={dx}: '+', '.join(f"{m['label']} R/Q={m['quantities']['r_over_q_accelerator_ohm']:.6f}" for m in modes), flush=True)
        for last, prev in zip(report['legacy'][-1]['modes'], report['legacy'][-2]['modes']):
            last['refinement_errors'] = relative(last['quantities'], prev['quantities'])
            last['refinement_gates'] = gates(last['refinement_errors'])
        final_modes = deepcopy(report['legacy'][-1]['modes'])
        final_rows = [sf_rows[m['mode_index']-1] for m in final_modes]
        report['supplemental_legacy'] = []
        for phase_text, dx_text, directory_text in args.extra_wine_reference:
            p = int(phase_text)
            if not 0 <= p < count:
                raise ValueError('supplemental phase index is outside this band')
            previous = final_modes[p]
            dx = finer_dx(dx_text, previous['dx_cm'])
            directory = Path(directory_text).resolve()
            expected = out/'wine'/'supplemental'/f'phase{p}-dx{dx:g}'
            expected.mkdir(parents=True)
            write_deck(base, expected, dx, starts[previous['mode_index']-1])
            if any(not (directory/name).exists() or (directory/name).read_bytes() != (expected/name).read_bytes()
                   for name in ('cavity.af', 'cavity.seg')):
                raise ValueError('supplemental AF/SEG does not match the requested geometry, launch and dx')
            sf = parse_sfo(directory/'CAVITY.SFO')
            data = read_sf7_line(directory/'OUTSF7.TXT')
            if (np.max(np.abs(data[:, 1])) > 1e-12 or abs(data[0, 0]) > 1e-12
                    or abs(data[-1, 0]-base.length) > 1e-10):
                raise ValueError('supplemental Wine axis does not cover the full input domain')
            sf['axis'] = data[:, [0, 2]].tolist()
            identity = replacement_identity(base, final_rows, p, sf)
            # Preserve the original launch index; the temporary identification
            # columns are phase-ordered and are not new global mode ranks.
            identity['mode_index'] = previous['mode_index']
            index = finest['modes'][p]['mode_index']-1
            last = mode_comparison(base, identity, sf, directory, finest['modes'][p]['quantities'], axes[index], dx)
            last['refinement_errors'] = relative(last['quantities'], previous['quantities'])
            last['refinement_gates'] = gates(last['refinement_errors'])
            report['supplemental_legacy'].append({'phase_index': p, 'previous_dx_cm': previous['dx_cm'], 'mode': last})
            final_modes[p], final_rows[p] = last, (sf, directory)
            print(f"Wine supplemental phase={p}, dx={dx}: R/Q={last['quantities']['r_over_q_accelerator_ohm']:.9f}", flush=True)
        report['final_legacy_modes'] = final_modes
        fig, axs = plt.subplots((count+1)//2, 2, figsize=(11, 3.3*((count+1)//2)), layout='constrained')
        for p, ax in enumerate(axs.ravel()):
            if p >= count:
                ax.set_axis_off()
                continue
            native_index = finest['modes'][p]['mode_index']-1
            sf, _ = final_rows[p]
            reference = np.asarray(sf['axis']).copy()
            reference[:, 1] *= np.sqrt(base.normalization_j/sf['quantities']['stored_energy_j'])
            native = axes[native_index].copy()
            if np.dot(np.interp(reference[:, 0], native[:, 0], native[:, 1]), reference[:, 1]) < 0:
                native[:, 1] *= -1
            ax.plot(native[:, 0]*1000, native[:, 1]/1e6, label='NG')
            ax.plot(reference[:, 0]*1000, reference[:, 1]/1e6, '--', label='Wine SF7')
            ax.set(xlabel='z [mm]', ylabel='Ez [MV/m]', title=finest['modes'][p]['label'])
            ax.grid(alpha=.25)
            ax.legend()
        fig.suptitle('Signed axis comparison; U=1 J; global sign aligned')
        fig.savefig(out/'axis_comparison.png', dpi=160)
        plt.close(fig)
    frequencies = [m['quantities']['frequency_hz'] for m in finest['modes']]
    phase = [m['phase_rad'] for m in finest['modes']]
    fit = fit_dispersion(phase, frequencies)
    report['dispersion'] = fit
    fig, axs = plt.subplots(2, 1, figsize=(8, 7), layout='constrained')
    axs[0].plot(np.array(phase)/np.pi, np.array(frequencies)/1e6, 'o', label='NG')
    if compare:
        axs[0].plot(np.array(phase)/np.pi, [m['quantities']['frequency_hz']/1e6 for m in final_modes], 'x', label='Wine (final per-mode mesh)')
    theta = np.linspace(0., np.pi, 200)
    axs[0].plot(theta/np.pi, (fit['m1_hz']+fit['m2_hz']*np.cos(theta))/1e6, label='NG cosine fit')
    axs[0].set(ylabel='Frequency [MHz]', title=f'{base.name}: field-identified dispersion')
    axs[0].legend()
    axs[1].plot(np.array(phase)/np.pi, np.array(fit['residual_hz'])/1000, 'o-')
    axs[1].set(xlabel='Phase advance / pi', ylabel='NG - cosine fit [kHz]')
    for ax in axs: ax.grid(alpha=.25)
    fig.savefig(out/'dispersion.png', dpi=160)
    plt.close(fig)
    np.savetxt(out/'dispersion.csv', np.column_stack((phase, frequencies, fit['fitted_hz'], fit['residual_hz'])),
               delimiter=',', header='phase_rad,frequency_hz,fitted_hz,residual_hz', comments='')
    panels, options = [], []
    for p, mode in enumerate(finest['modes']):
        figure = plot_mode(Path(finest['directory']), out/f'mode{p}.png', mode['mode_index'], mode_label=mode['label'])
        radial = figure['radial_fields']
        np.savetxt(out/f'radial{p}.csv', np.column_stack((figure['radial_points_rz_m'], radial['Er_quadrature_V_per_m'],
                                                       radial['Ez_quadrature_V_per_m'], radial['Hphi_A_per_m'])),
                   delimiter=',', header='r_m,z_m,Er_quadrature_V_per_m,Ez_quadrature_V_per_m,Hphi_A_per_m', comments='')
        np.savetxt(out/f'axis{p}.csv', axes[mode['mode_index']-1], delimiter=',', header='z_m,Ez_quadrature_V_per_m', comments='')
        options.append(f'<option value="mode{p}">{html.escape(mode["label"])}</option>')
        panels.append(f'<section id="mode{p}" class="mode" {"hidden" if p else ""}><h2>{mode["label"]}</h2>'
                      f'<img src="mode{p}.png" alt="Mode {mode["label"]}: electric/magnetic fields and probes">'
                      f'<p>零交差={mode["zero_crossings"]}、セル場一致度={mode["cell_overlap"]:.8f}</p>'
                      +(f'<p>Wine最終DX={final_modes[p]["dx_cm"]:g} cm（モード別に細分履歴を保持）</p>' if compare else '')+
                      f'<a href="axis{p}.csv">軸上CSV</a> · <a href="radial{p}.csv">半径方向CSV</a></section>')
    report['native_refinement_passed'] = all(native_gates)
    report['passed'] = report['native_refinement_passed'] and (not compare or all(all(m['gates'].values()) and all(m['refinement_gates'].values()) for m in final_modes))
    report['report_source_sha256'] = source_at_start
    report['source_changed_during_run'] = source_at_start != {str(p.relative_to(ROOT)): digest(p) for p in source_paths}
    report['passed'] = report['passed'] and not report['source_changed_during_run']
    report['native_environment'] = run['environment']
    report['environment'] = {'python': platform.python_version(), 'numpy': np.__version__, 'scipy': scipy.__version__,
                             'matplotlib': matplotlib.__version__, 'platform': platform.platform()}
    write_json(out/'comparison.json', report)
    (out/'index.html').write_text('<!doctype html><html lang="ja"><meta charset="utf-8"><title>Superfish-NG multicell</title>'
                                '<style>body{font:16px system-ui;max-width:1150px;margin:32px auto;padding:0 20px}img{width:100%}select{font:inherit;padding:8px}</style>'
                                f'<h1>{html.escape(base.name)}</h1>'
                                f'<p>{"PASS" if report["passed"] else "FAIL — 未達ゲートをcomparison.jsonで確認"} · Wine照合={compare}</p>'
                                '<p>真空、全外壁PEC、端部half-cell、β=1、U=1 J。mode番号ではなく場の符号・零交差・セル中心値で同定。</p>'
                                '<label for="selector">モード </label><select id="selector">'+''.join(options)+'</select>'+''.join(panels)+
                                '<h2>分散曲線とフィット残差</h2><img src="dispersion.png" alt="Dispersion curve and cosine-fit residual">'
                                +('<h2>Wineとの符号付き軸場比較</h2><img src="axis_comparison.png" alt="NG and Wine signed on-axis fields">' if compare else '')+
                                '<p><a href="dispersion.csv">分散CSV</a> · <a href="comparison.json">入力・参照hash・全検証結果</a></p>'
                                '<script>document.getElementById("selector").addEventListener("change",e=>document.querySelectorAll(".mode").forEach(s=>s.hidden=s.id!==e.target.value))</script></html>', encoding='utf-8')
    print(f'{"PASS" if report["passed"] else "FAIL"}: {out}/index.html', flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
