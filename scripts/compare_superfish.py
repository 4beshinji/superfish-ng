# SPDX-License-Identifier: Apache-2.0
"""Opt-in black-box comparison with locally installed Wine SUPERFISH.

Run from the project root. Raw legacy outputs stay in ignored out/ and are not
redistributed. No legacy solver implementation is imported or inspected.
"""
import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import numpy as np
import scipy
from scipy.integrate import simpson
from superfish_ng import Case, solve
from superfish_ng.analytic import pillbox_tm010
from superfish_ng.io import save_run

NUMBER = r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[EeDd][-+]?\d+)?'
LIMITS = {'frequency_hz': .001, 'q0': .005, 'geometry_factor_ohm': .005,
          'r_over_q_accelerator_ohm': .01, 'transit_time_factor_abs': .005}
SIGMA = 1 / 1.7241e-8  # SFO room-temperature copper: 1.7241 microohm cm.


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def scalar(text, name):
    values = re.findall(r'^' + re.escape(name) + r'\s+(?:[AS]\s+)?(' + NUMBER + r')\s', text, re.M)
    if not values:
        raise ValueError(f'missing SFO variable {name}')
    value = float(values[-1].replace('D', 'E'))
    if not np.isfinite(value):
        raise ValueError(f'nonfinite SFO variable {name}')
    return value


def parse_sfo(path):
    text = path.read_text(encoding='latin-1')
    if 'Treating the problem geometry as a single full cell:' not in text:
        raise ValueError('expected a full cell: explicitly set ZCTR to the cavity midpoint')
    f, energy, power = (scalar(text, k) for k in ['FREQ', 'ENERGY', 'POWER'])
    length, e0, t = scalar(text, 'ZLONG') / 100, scalar(text, 'EZERO'), scalar(text, 'T')
    if min(f, energy, power, length, e0) <= 0:
        raise ValueError('invalid positive SFO quantities')
    s_match = re.search(r'^\s+S\s+=\s*(' + NUMBER + ')', text, re.M)
    if not s_match:
        raise ValueError('missing sine transit-time integral')
    ttf = float(np.hypot(t, float(s_match[1])))
    omega = 2 * np.pi * f * 1e6
    vacc = e0 * length * ttf
    q0 = omega * energy / power
    resistivity = re.search(r'Normal-conductor resistivity\s*=\s*(' + NUMBER + r')\s+microOhm-cm', text)
    if not resistivity:
        raise ValueError('missing resistivity with explicit microOhm-cm units')
    axis_block = text.split('Z(cm)      Ez(V/m)', 1)[1]
    rows = []
    for line in axis_block.splitlines()[1:]:
        match = re.fullmatch(r'\s*(' + NUMBER + r')\s+(' + NUMBER + r')\s*', line)
        if not match:
            break
        rows.append([float(match[1]) / 100, float(match[2])])
    axis = np.asarray(rows)
    if len(axis) < 3 or np.any(np.diff(axis[:, 0]) <= 0):
        raise ValueError('invalid SFO on-axis field table')
    if abs(axis[0, 0]) > 1e-8 or abs(axis[-1, 0] - length) > 1e-7:
        raise ValueError('SFO axis table does not cover the complete cavity')
    version_match = re.search(r'^Program SFO\s+(\d+\.\d+[^\n]*)', text, re.M)
    if not version_match:
        raise ValueError('missing numerical SFO version')
    version = version_match[1].strip()
    values = {'frequency_hz': f * 1e6, 'stored_energy_j': energy, 'wall_loss_w': power,
              'surface_resistance_ohm': scalar(text, 'RS'), 'q0': q0,
              'geometry_factor_ohm': q0 * scalar(text, 'RS'), 'vacc_v': vacc,
              'r_over_q_accelerator_ohm': vacc**2 / (omega * energy),
              'r_over_q_circuit_ohm': vacc**2 / (2 * omega * energy),
              'transit_time_factor_abs': ttf, 'active_length_m': length,
              'conductivity_s_per_m': 1 / (float(resistivity[1]) * 1e-8),
              'epk_over_eacc_estimate': scalar(text, 'EMAX') / (vacc / length),
              'bpk_over_eacc_estimate_mt_per_mv_per_m': scalar(text, 'FMU0') * scalar(text, 'HMAX') / (vacc / length) * 1e9}
    # Independently integrate the printed field, without using the NG RF routine.
    v_axis = simpson(axis[:, 1] * np.exp(1j * omega * axis[:, 0] / 299792458), x=axis[:, 0])
    values['axis_voltage_vs_sfo_relative_difference'] = float(abs(abs(v_axis) / vacc - 1))
    return {'version': version, 'nodes': int(scalar(text, 'NPINP')), 'quantities': values,
            'axis': axis.tolist(), 'sfo_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def write_deck(case, folder, dx_cm, frequency_mhz):
    profile = [(z * 100, r * 100) for z, r in case.profile]
    header = (f'Independent closed vacuum cavity comparison: {case.name}\n'
              f'$reg kprob=1, icylin=1, dx={dx_cm}, freq={frequency_mhz},\n'
              f'xdri=0, ydri={profile[0][1]}, kmethod=1, beta=1, zctr={case.length*50},\n'
              'nbslo=0, nbsup=1, nbslf=1, nbsrt=1, epsik=1e-10 $\n')
    points = [(0, 0)] + profile + [(case.length * 100, 0), (0, 0)]
    (folder / 'cavity.af').write_text(header + ''.join(f'$po x={z:.12g}, y={r:.12g} $\n' for z, r in points))
    segments = ' '.join(str(n) for n in range(1, len(profile) + 2))
    (folder / 'cavity.seg').write_text(f'FieldSegments\n{segments}\nEndData\nEnd\n')


def relative(a, b):
    return {k: abs(a[k] / b[k] - 1) for k in LIMITS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='new directory inside project out/')
    parser.add_argument('--run-legacy', action='store_true', help='explicitly authorize local Wine execution')
    args = parser.parse_args()
    if not args.run_legacy:
        parser.error('--run-legacy is required')
    out = args.out.resolve()
    if not out.is_relative_to(ROOT / 'out') or out == ROOT / 'out':
        parser.error('raw reference output must be in a new subdirectory of project out/')
    out.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    cases = [
        ('short_pillbox', Case(((0., .075), (.08, .075)), modes=1, conductivity_s_per_m=SIGMA,
                               name='pillbox R75mm L80mm'), 1500.),
        ('seed_pillbox', replace(Case.load(ROOT / 'examples/pillbox.json'), modes=1, conductivity_s_per_m=SIGMA), 1140.),
        ('shaped_cell', replace(Case.load(ROOT / 'examples/shaped_cell.json'), modes=1, conductivity_s_per_m=SIGMA), 1270.),
    ]
    report = {'environment': {'python': platform.python_version(), 'numpy': np.__version__,
                             'scipy': scipy.__version__, 'wine': subprocess.check_output(['wine', '--version'], text=True).strip(),
                             'platform': platform.platform()},
              'scope': 'three closed vacuum axis-connected m=0 TM fundamental modes; beta=1; all PEC walls',
              'limits': LIMITS, 'axis_l2_limit': .01, 'raw_output_redistribution': False,
              'conventions': {'coordinates': 'NG (z,r) metres -> SUPERFISH (x,y)=(z,r) centimetres',
                              'voltage': '|E0 * full_length * (T+iS)|; ZCTR=full_length/2',
                              'rq_accelerator': '|Vacc|^2/(omega U)', 'rq_circuit': '|Vacc|^2/(2 omega U)',
                              'q0': 'omega U / P; all wall segments included',
                              'resistivity': 'SFO summary microOhm-cm -> ohm m with factor 1e-8',
                              'axis_field': 'peak phasor; U=1 J; global sign aligned'},
              'cases': []}
    for name, base, initial_frequency in cases:
        runs = []
        for level, dx in zip([24, 48, 96], [.4, .2, .1]):
            run_dir = out / name / f'level-{level}'
            legacy_dir = run_dir / 'superfish'
            legacy_dir.mkdir(parents=True)
            write_deck(base, legacy_dir, dx, initial_frequency)
            command = [str(ROOT / 'run-superfish.sh'), str(legacy_dir / 'cavity.af')]
            with (legacy_dir / 'wine.log').open('w') as log:
                proc = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=120,
                                      env=dict(os.environ, WINEDEBUG='-all'))
            if proc.returncode:
                raise RuntimeError(f'Wine failed: {legacy_dir}, exit={proc.returncode}')
            sf = parse_sfo(legacy_dir / 'CAVITY.SFO')
            if abs(sf['quantities']['conductivity_s_per_m'] / SIGMA - 1) > 1e-8:
                raise ValueError('SUPERFISH conductivity differs from the specified NG case')
            case = replace(base, nr=level, nz=round(level * base.length / max(r for _, r in base.profile)))
            sol = solve(case)
            ng = save_run(case, sol, run_dir / 'ng')
            q = ng['modes'][0]
            ng_axis = np.loadtxt(run_dir / 'ng/axis_001.csv', delimiter=',', skiprows=1)
            sf_axis = np.asarray(sf.pop('axis'))
            # Dense common grid for relative L2; interpolation is only for comparison.
            z = np.linspace(0, case.length, 4001)
            ea = np.interp(z, sf_axis[:, 0], sf_axis[:, 1]) / np.sqrt(sf['quantities']['stored_energy_j'])
            eb = np.interp(z, ng_axis[:, 0], ng_axis[:, 1])
            eb *= 1 if np.dot(ea, eb) >= 0 else -1
            axis_error = float(np.sqrt(simpson((ea-eb)**2, x=z) / simpson(ea**2, x=z)))
            row = {'ng_nr': case.nr, 'ng_nz': case.nz, 'sf_dx_cm': dx, 'sf': sf,
                   'ng': {'nodes': len(sol.mesh.points), 'quantities': q},
                   'relative_differences': relative(q, sf['quantities']), 'axis_relative_l2': axis_error,
                   'command': command, 'af_sha256': hashlib.sha256((legacy_dir / 'cavity.af').read_bytes()).hexdigest()}
            runs.append(row)
            write_json(run_dir / 'comparison.json', row)
            print(f'{name} n={level}: SF={sf["quantities"]["frequency_hz"]/1e6:.6f} NG={q["frequency_hz"]/1e6:.6f} MHz; '
                  f'R/Q diff={row["relative_differences"]["r_over_q_accelerator_ohm"]:.3%}; axis L2={axis_error:.3%}', flush=True)
        finest = runs[-1]
        refinements = {solver: relative(runs[-1][solver]['quantities'], runs[-2][solver]['quantities']) for solver in ['ng', 'sf']}
        gates = {k: finest['relative_differences'][k] < limit for k, limit in LIMITS.items()}
        gates['axis_l2'] = finest['axis_relative_l2'] < .01
        gates['sf_printed_axis_voltage'] = finest['sf']['quantities']['axis_voltage_vs_sfo_relative_difference'] < .001
        for solver, differences in refinements.items():
            gates[solver + '_refinement'] = all(differences[k] < limit for k, limit in LIMITS.items())
        item = {'name': name, 'case': base.to_dict(), 'runs': runs, 'finest_refinement': refinements, 'gates': gates,
                'passed': all(gates.values())}
        if name != 'shaped_cell':
            exact = pillbox_tm010(base.profile[0][1], base.length, conductivity_s_per_m=SIGMA)
            item['analytic'] = exact
            item['analytic_errors'] = {s: relative(finest[s]['quantities'], exact) for s in ['ng', 'sf']}
        report['cases'].append(item)
        write_json(out / 'comparison.json', report)
    report['passed'] = all(c['passed'] for c in report['cases'])
    report['seconds'] = time.perf_counter() - started
    report['source_sha256'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted((ROOT / 'src/superfish_ng').glob('*.py'))}
    report['script_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    write_json(out / 'comparison.json', report)
    print(f'Comparison {"PASS" if report["passed"] else "FAIL"}: {out}', flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
