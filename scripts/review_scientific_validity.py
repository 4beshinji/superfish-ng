# SPDX-License-Identifier: Apache-2.0
"""Reproduce the bounded 2026-10-13 scientific review, without changing a solver.

Run with the existing uv environment, OPENBLAS_NUM_THREADS=1, and a new --out.
The report separates successful checks from deliberately reproduced API defects.
This is neither the full validator nor an external-solver/measurement validation.
"""
import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import numpy as np
import scipy
from scipy.special import j0, j1, jn_zeros, jnp_zeros
from superfish_ng import Case, solve
from superfish_ng.rf import quantities
from superfish_ng.sampling import FieldSampler

MODULES = [
    'test_physics', 'test_quadratic_elements', 'test_quadratic_rf',
    'test_curved_fem', 'test_curved_solution', 'test_curved_rf', 'test_te',
    'test_coaxial', 'test_material_hphi', 'test_planar_curved_solver',
    'test_electrostatic', 'test_axis_magnetostatic', 'test_bh_curve',
    'test_planar_bh', 'test_mode_tracking',
]


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def snapshot():
    paths = [p for folder in ('src', 'tests', 'scripts', 'examples')
             for p in (ROOT / folder).rglob('*')
             if p.is_file() and p.suffix in ('.py', '.json', '.js', '.html', '.css', '.mjs')
             and '__pycache__' not in p.parts]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths)}


def analytic_reference(radius=.1, length=.2):
    # Independent review formulas, not superfish_ng.analytic. SI central values
    # and the SciPy special-function implementation are shared dependencies.
    c = 299792458.
    mu = 1.25663706127e-6
    eps = 1 / (mu * c * c)
    root = jn_zeros(0, 1)[0]
    omega = c * root / radius
    t = abs(np.sin(omega * length / (2 * c)) / (omega * length / (2 * c)))
    h0 = np.sqrt(2 / (mu * np.pi * radius**2 * length * j1(root)**2))
    g = omega * mu * radius * length / (2 * (radius + length))
    rs = np.sqrt(omega * mu / (2 * 5.8e7))
    return dict(frequency_hz=omega/(2*np.pi), geometry_factor_ohm=g, q0=g/rs,
                r_over_q_accelerator_ohm=2*length*t*t/(omega*eps*np.pi*radius**2*j1(root)**2),
                transit_time_factor_abs=t, epk_over_eacc_estimate=1/t,
                bpk_over_eacc_estimate_mt_per_mv_per_m=j1(jnp_zeros(1, 1)[0])/(c*t)*1e9,
                h_amplitude_a_per_m=h0, e_amplitude_v_per_m=np.sqrt(mu/eps)*h0,
                radial_wave_number_per_m=root/radius)


def field_errors(solution, exact):
    # Independent 8-by-8 product Gauss integration, in the actual mesh volume.
    # Public field evaluator is the object under test; assembly/analytic helpers
    # are not used as the expected field or integration weights.
    vertices = solution.mesh.points[solution.mesh.triangles]
    a = vertices[:, 1] - vertices[:, 0]
    b = vertices[:, 2] - vertices[:, 0]
    det = abs(a[:, 0]*b[:, 1] - a[:, 1]*b[:, 0])
    g, w = np.polynomial.legendre.leggauss(8)
    g, w = (g+1)/2, w/2
    sampler = FieldSampler.from_solution(solution)
    hh = ee = hn = en = cross = 0.
    saved = []
    for x, wx in zip(g, w):
        for y, wy in zip(g, w):
            bary = np.array([1-x-(1-x)*y, x, (1-x)*y])
            points = np.einsum('i,tij->tj', bary, vertices)
            field = sampler.evaluate(points)
            r = points[:, 0]
            ha = exact['h_amplitude_a_per_m']*j1(exact['radial_wave_number_per_m']*r)
            ea = exact['e_amplitude_v_per_m']*j0(exact['radial_wave_number_per_m']*r)
            measure = 2*np.pi*r*det*wx*wy*(1-x)
            cross += float(measure @ (ha*field['Hphi_A_per_m']))
            saved.append((measure, field, ha, ea))
    sign = 1 if cross >= 0 else -1
    for measure, field, ha, ea in saved:
        hh += float(measure @ (sign*field['Hphi_A_per_m']-ha)**2)
        ee += float(measure @ ((sign*field['Ez_quadrature_V_per_m']-ea)**2
                              + field['Er_quadrature_V_per_m']**2))
        hn += float(measure @ ha**2)
        en += float(measure @ ea**2)
    return dict(h_relative_l2=np.sqrt(hh/hn), e_relative_l2=np.sqrt(ee/en), common_sign=sign)


def cylinder_series():
    exact = analytic_reference()
    rows = []
    for order in (1, 2):
        for n in (8, 16, 32):
            case = Case(((0., .1), (.2, .1)), nr=n, nz=n, modes=1, element_order=order)
            solution = solve(case)
            rf = quantities(case, solution)
            keys = [k for k in exact if k in rf]
            rows.append(dict(element_order=order, nr=n, nz=n, dofs=len(solution.u),
                             residual=float(solution.residuals[0]),
                             rf={k:rf[k] for k in keys},
                             relative_errors={k:abs(rf[k]/exact[k]-1) for k in keys},
                             fields=field_errors(solution, exact)))
    return dict(radius_m=.1, length_m=.2, beta=1., stored_energy_j=1.,
                conductivity_s_per_m=5.8e7, exact=exact, rows=rows)


def mismatched_case(out):
    from superfish_ng.io import save_run
    from superfish_ng.saved import read_solution
    rows = []
    for order in (1, 2):
        case = Case(((0., .1), (.2, .1)), nr=8, nz=8, modes=1, element_order=order)
        solution = solve(case)
        original = quantities(case, solution)
        variants = {'radius':replace(case, profile=((0., .2), (.2, .2))),
                    'length':replace(case, profile=((0., .1), (.4, .1))),
                    'normalization':replace(case, normalization_j=9.)}
        for name, other in variants.items():
            row = dict(element_order=order, mutation=name, input=other.to_dict())
            try:
                rf = quantities(other, solution)
                row.update(quantities_accepted=True, frequency_hz=rf['frequency_hz'],
                           stored_energy_j=rf['stored_energy_j'],
                           eacc_ratio_to_original=rf['eacc_v_per_m']/original['eacc_v_per_m'])
            except ValueError as exc:
                row.update(quantities_accepted=False, quantities_error=str(exc))
            path = out/f'mismatch-p{order}-{name}'
            try:
                save_run(other, solution, path)
                row['save_accepted'] = True
                row['completion_marker'] = (path/'save_complete.json').is_file()
                try:
                    restored = read_solution(path)
                    row.update(read_accepted=True, declared_length_m=restored.case.length,
                               actual_mesh_z_max_m=float(restored.mesh.points[:, 1].max()),
                               declared_radius_m=restored.case.profile[0][1],
                               actual_mesh_r_max_m=float(restored.mesh.points[:, 0].max()))
                except ValueError as exc:
                    row.update(read_accepted=False, read_error=str(exc))
            except ValueError as exc:
                row.update(save_accepted=False, save_error=str(exc))
            rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    before = snapshot()
    write(out/'source-before.json', before)
    command = [sys.executable, '-m', 'unittest', '-v', *MODULES]
    env = dict(os.environ, PYTHONPATH=os.pathsep.join((str(ROOT/'src'), str(ROOT/'tests'))))
    with (out/'unittest.log').open('w') as log:
        unit_start = time.perf_counter()
        run = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    unit_seconds = time.perf_counter()-unit_start
    print(f'Selected unittest exit={run.returncode}; {unit_seconds:.3f}s', flush=True)
    series = cylinder_series()
    print('P1/P2 cylinder series complete', flush=True)
    mismatches = mismatched_case(out)
    evidence_paths = [
        'out/independent-ngsolve-20260907-first/comparison.json',
        'out/n03-native-surface-series-20261007/n03-card-acceptance.json',
        'out/p07-planar-exact-reference-20261007/final-p07-acceptance.json',
        'out/validation-n03-milestone-localhost-20261007/validation.json',
        'benchmarks/cavsim2d/a01-20260914.json',
        'benchmarks/validation/validation.json',
    ]
    evidence = {}
    for name in evidence_paths:
        p = ROOT/name
        evidence[name] = dict(exists=p.is_file())
        if p.is_file():
            evidence[name].update(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    after = snapshot()
    write(out/'source-after.json', after)
    changed = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
    report = dict(scope='bounded scientific review; not full acceptance',
                  base_commit=subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
                  environment=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,
                                   platform=platform.platform(),executable=sys.executable,
                                   openblas_num_threads=os.environ.get('OPENBLAS_NUM_THREADS')),
                  unittest=dict(modules=MODULES,command=command,exit_code=run.returncode,seconds=unit_seconds,
                                log_tail=(out/'unittest.log').read_text().splitlines()[-5:]),
                  cylinder_series=series, mismatched_case=mismatches,
                  historical_evidence_presence=evidence, source_file_count=len(before),
                  source_changes=changed, seconds=time.perf_counter()-started,
                  not_performed=['full suite','full/seed validate.py','new external solver comparison',
                                 'legacy execution or inspection','measurement validation','GUI review'])
    write(out/'review.json', report)
    print(f'Review evidence: {out}/review.json; source changes={changed}', flush=True)
    return int(run.returncode != 0 or bool(changed))


if __name__ == '__main__':
    raise SystemExit(main())
