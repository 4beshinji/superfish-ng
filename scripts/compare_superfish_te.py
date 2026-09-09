# SPDX-License-Identifier: Apache-2.0
"""Opt-in complementary TE black-box checks; never use SFO TM wall loss for TE.

Only existing executable invocation, input/configuration and numerical output are
used. Raw reference files must stay under ignored out/. This is a verification
script, not a legacy backend or a general AF input converter.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

import numpy as np
from scipy.integrate import simpson

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from superfish_ng import Case, solve
from superfish_ng.constants import EPS0, MU0, TAU
from superfish_ng.io import save_run
from superfish_ng.model import Model
from superfish_ng.te import TEFieldSampler, te_quantities
from compare_superfish import scalar
from evaluate_wine_surface_fields import parse_sf7_tables
from validate_te import analytic
from validate_curved_rf_adaptive import fingerprints

LIMITS = dict(frequency=1e-4, fields=.01, geometry_factor=.005)
DECLARATION = 'vacuum_axisymmetric_complementary_te'
IMPEDANCE = np.sqrt(MU0 / EPS0)


def complementary_fields(table, *, declaration):
    """SF7 SI (z,r,Ez,Er,|E|,Hphi) -> real Ephi and NG quadrature H.

    SF7's printed real electric coefficients already carry its quadrature
    convention. Both H quadrature components therefore have a positive factor
    here; applying an additional Maxwell duality minus sign would be incorrect.
    The phase relationship is checked against the analytic cylindrical field,
    without independently sign-aligning magnetic and electric components.
    """
    if declaration != DECLARATION:
        raise ValueError('an explicit vacuum axisymmetric complementary TE declaration is required')
    a = np.asarray(table, dtype=float)
    if a.ndim != 2 or a.shape[1] != 6 or len(a) < 3 or not np.isfinite(a).all():
        raise ValueError('expected a finite signed SF7 SI table with six columns')
    if np.any(a[:, :2] < 0) or not np.allclose(np.hypot(a[:, 2], a[:, 3]), a[:, 4], rtol=3e-5, atol=1e-3):
        raise ValueError('invalid coordinates or inconsistent SF7 electric magnitude')
    return dict(Ephi_V_per_m=a[:, 5] * IMPEDANCE,
                Hr_quadrature_A_per_m=a[:, 3] / IMPEDANCE,
                Hz_quadrature_A_per_m=a[:, 2] / IMPEDANCE)


def wall_integral(tables, radius, length, *, declaration):
    """Integral of peak |H_t|^2 dS on the two end disks and cylinder wall."""
    if len(tables) != 3 or not np.isfinite([radius, length]).all() or min(radius, length) <= 0:
        raise ValueError('three complete cylindrical PEC wall tables are required')
    total = 0.
    for i, table in enumerate(tables):
        fields = complementary_fields(table, declaration=declaration)
        z, r = table[:, :2].T
        coordinate = z if i == 1 else r
        fixed = r if i == 1 else z
        expected_fixed = radius if i == 1 else (0. if i == 0 else length)
        extent = length if i == 1 else radius
        tolerance = max(radius, length) * 1e-8
        if (not np.allclose(fixed, expected_fixed, rtol=0, atol=tolerance)
                or abs(coordinate[0]) > tolerance or abs(coordinate[-1] - extent) > tolerance
                or not np.all(np.diff(coordinate) > 0)):
            raise ValueError('wall tables must cover ordered full end disks / outer cylinder / end disk')
        h = fields['Hz_quadrature_A_per_m' if i == 1 else 'Hr_quadrature_A_per_m']
        total += TAU * simpson(r * h**2, x=coordinate)
    if not np.isfinite(total) or total <= 0:
        raise ValueError('TE wall integral must be positive and finite')
    return float(total)


def write_inputs(folder, radius, length, axial, dx, frequency):
    if axial not in (1, 2):
        raise ValueError('this acceptance driver supports only radial 1, axial 1/2')
    z, r = length * 100, radius * 100
    (folder / 'cavity.af').write_text(
        'Independent synthetic vacuum cylinder, explicitly complementary TE\n'
        f'$reg kprob=1, icylin=1, dx={dx:.12g}, freq={frequency/1e6:.12g},\n'
        f'xdri={z/(2*axial):.12g}, ydri={r/2:.12g}, kmethod=1, beta=1, zctr={z/2:.12g},\n'
        'nbslo=0, nbsup=0, nbslf=0, nbsrt=0, epsik=1e-10 $\n' +
        ''.join(f'$po x={x:.12g}, y={y:.12g} $\n' for x, y in [(0,0),(0,r),(z,r),(z,0),(0,0)]))
    lines = [(0,r/2,z,r/2),(z/(2*axial),0,z/(2*axial),r),(0,0,0,r),(0,r,z,r),(z,0,z,r)]
    (folder / 'cavity.in7').write_text(''.join('line plotfiles\n' + ' '.join(f'{v:.12g}' for v in line) + '\n200\n' for line in lines) + 'end\n')
    (folder / 'SF.INI').write_text('[Global]\nTAPE40=C\nStoreTempDataInRAM=No\n[SF7]\nDecimalPlaces=10\nExpandedTable=No\n')
    return lines


def run(wine, prefix, display, executable, argument, folder, timeout):
    command = [str(wine), executable, argument]
    log = folder / ('autofish.log' if 'AUTOFISH' in executable else 'sf7.log')
    with log.open('x') as stream:
        result = subprocess.run(command, cwd=folder, stdout=stream, stderr=subprocess.STDOUT,
            timeout=timeout, env=dict(os.environ, WINEPREFIX=str(prefix), DISPLAY=display, WINEDEBUG='-all'))
    if result.returncode:
        raise RuntimeError(f'{executable} exited {result.returncode}; see {log}')
    expected = 'CAVITY.SFO' if 'AUTOFISH' in executable else 'OUTSF7.TXT'
    if not (folder / expected).is_file():
        raise RuntimeError(f'{executable} exited zero but did not generate {expected}; see {log}')
    return dict(command=command, exit_code=result.returncode)


def field_errors(tables, expected):
    observed = [complementary_fields(t, declaration=DECLARATION) for t in tables]
    keys = tuple(observed[0])
    sign = 1 if sum(np.dot(a['Ephi_V_per_m'], b['Ephi_V_per_m']) for a,b in zip(observed,expected)) >= 0 else -1
    return {k: float(max(np.max(abs(sign*a[k]-b[k])) for a,b in zip(observed,expected)) /
                     max(np.max(abs(b[k])) for b in expected)) for k in keys}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--run-legacy', action='store_true')
    parser.add_argument('--wine', type=Path, required=True, help='existing Wine executable; no legacy binaries are copied')
    parser.add_argument('--prefix', type=Path, required=True)
    parser.add_argument('--display', required=True, help='dedicated existing X display')
    parser.add_argument('--timeout-s', type=float, default=120)
    args = parser.parse_args()
    out = args.out.resolve()
    if not args.run_legacy or not out.is_relative_to(ROOT/'out') or out == ROOT/'out':
        parser.error('--run-legacy and a fresh project out/ subdirectory are required')
    if not np.isfinite(args.timeout_s) or args.timeout_s <= 0:
        parser.error('timeout must be positive and finite')
    out.mkdir(parents=True, exist_ok=False)
    before = fingerprints(); records = []; start = time.perf_counter()
    report = dict(status='RUNNING', declaration=DECLARATION, limits=LIMITS,
        source_sha256=before, raw_output_redistribution=False, records=records,
        scope='synthetic closed vacuum cylinder radial 1 axial 1/2; two scales and three legacy mesh sizes; independent P2 FEM',
        conventions=dict(normalization='SFO stored energy, without amplitude fitting; one common global field sign',
            fields='SF7 SI: Ephi=Z0*Hphi; Hr_quadrature=Er/Z0; Hz_quadrature=Ez/Z0',
            geometry_factor='2*omega*U / integral(|H_t_peak|^2 dS); SFO POWER is not used'),
        wine_version=subprocess.check_output([str(args.wine.resolve()), '--version'], text=True).strip())
    def checkpoint():
        (out/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    checkpoint()
    for scale in (1., 2.):
        radius, length = .1*scale, .2*scale
        refs, evaluate = analytic(radius, length, 1., 2)
        case = Case(((0.,radius),(length,radius)), nr=32, nz=48, element_order=2, modes=2, model=Model(polarization='te'))
        solution = solve(case); save_run(case, solution, out/f'ng-scale-{int(scale)}')
        sampler = TEFieldSampler(solution)
        for mode, ref in enumerate(refs):
            for dx in (.4, .2, .1):
                folder = out/f'scale-{int(scale)}-axial-{ref[2]}-dx-{dx:g}'; folder.mkdir()
                lines = write_inputs(folder, radius, length, ref[2], dx*scale, ref[0]*.999)
                commands = [run(args.wine.resolve(), args.prefix.resolve(), args.display, r'C:\LANL\AUTOFISH.EXE', 'cavity.af', folder, args.timeout_s)]
                text = (folder/'CAVITY.SFO').read_text(encoding='latin-1')
                version = re.search(r'^Program SFO\s+(\d+\.\d+[^\n]*)', text, re.M)
                if not version or any(scalar(text,k) != v for k,v in dict(ICYLIN=1,NBSLO=0,NBSUP=0,NBSLF=0,NBSRT=0).items()):
                    raise ValueError('missing version or unexpected complementary cylindrical boundary configuration')
                f, u = scalar(text,'FREQ')*1e6, scalar(text,'ENERGY')
                if not np.isfinite([f,u]).all() or min(f,u) <= 0:
                    raise ValueError('invalid frequency or stored energy')
                commands.append(run(args.wine.resolve(), args.prefix.resolve(), args.display, r'C:\LANL\SF7.EXE', 'CAVITY.T35', folder, args.timeout_s))
                tables = parse_sf7_tables(folder/'OUTSF7.TXT')
                if len(tables) != 5:
                    raise ValueError('expected two interior lines and three full PEC wall lines')
                for table, line in zip(tables, lines):
                    expected = np.linspace(np.array(line[:2])/100, np.array(line[2:])/100, 201)
                    if table.shape != (201,6) or not np.allclose(table[:,:2], expected, rtol=0, atol=length*1e-8):
                        raise ValueError('SF7 coordinates or line resolution differ from the declared probes')
                analytic_fields = [evaluate(ref,t[:,[1,0]])[0] for t in tables[:2]]
                # Both comparisons use the same physical U; no fitted field magnitude.
                normalized = [t.copy() for t in tables]
                for t in normalized:t[:,2:] /= np.sqrt(u)
                errors = field_errors(normalized[:2], analytic_fields)
                ng_fields = [sampler.evaluate(t[:,[1,0]], mode) for t in tables[:2]]
                ng_errors = field_errors(normalized[:2], ng_fields)
                integral = wall_integral(tables[2:], radius, length, declaration=DECLARATION)
                g = 2*TAU*f*u/integral; exact_g = evaluate(ref, tables[0][:,[1,0]])[1]
                q = te_quantities(solution,mode)
                row = dict(scale=scale, axial_index=ref[2], dx_cm=dx*scale, version=version[1].strip(),
                    commands=commands, frequency_hz=f, stored_energy_j=u, geometry_factor_ohm=g,
                    sfo_power_not_used_w=scalar(text,'POWER'), frequency_relative_error=abs(f/ref[0]-1),
                    field_relative_errors=errors, geometry_factor_relative_error=abs(g/exact_g-1),
                    ng_comparison=dict(frequency_relative_difference=abs(f/q['frequency_hz']-1),
                        field_relative_differences=ng_errors, geometry_factor_relative_difference=abs(g/q['geometry_factor_ohm']-1)),
                    raw_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()
                        if p.suffix.lower() in ('.txt','.sfo','.af','.in7','.ini','.log')})
                records.append(row); checkpoint()
                print(scale, ref[2], dx, row['frequency_relative_error'], max(errors.values()), row['geometry_factor_relative_error'], flush=True)
                if dx == .1:
                    assert row['frequency_relative_error'] < LIMITS['frequency'] and max(errors.values()) < LIMITS['fields'] and row['geometry_factor_relative_error'] < LIMITS['geometry_factor'], row
                    assert row['ng_comparison']['frequency_relative_difference'] < LIMITS['frequency'] and max(ng_errors.values()) < LIMITS['fields'] and row['ng_comparison']['geometry_factor_relative_difference'] < LIMITS['geometry_factor'], row
    similarity=[]
    for a,b in zip(records[:6],records[6:]):
        assert a['axial_index']==b['axial_index'] and a['dx_cm']*2==b['dx_cm']
        similarity.extend([abs(b['frequency_hz']*2/a['frequency_hz']-1),abs(b['geometry_factor_ohm']/a['geometry_factor_ohm']-1)])
    assert max(similarity)<1e-6, similarity
    assert fingerprints()==before
    report.update(status='PASS',source_unchanged=True,max_similarity_error=max(similarity),seconds=time.perf_counter()-start)
    checkpoint()


if __name__ == '__main__':
    main()
