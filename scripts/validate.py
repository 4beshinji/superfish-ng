# SPDX-License-Identifier: Apache-2.0
"""Reproduce tests, analytical comparisons, shaped case and provenance locally."""
import argparse
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
import numpy as np
import scipy
from superfish_ng import Case, solve
from superfish_ng.analytic import pillbox_spectrum
from superfish_ng.io import save_run
from superfish_ng.rf import quantities


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True, help='new output directory')
    parser.add_argument('--test-workers', type=int, default=min(8, os.cpu_count() or 1),
                        help='isolated unittest module processes (default: up to 8; 1 uses original serial discovery)')
    args = parser.parse_args()
    if args.test_workers < 1:
        parser.error('--test-workers must be a positive integer')
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, PYTHONPATH=str(ROOT/'src'))
    test_command = ([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v']
                    if args.test_workers == 1 else [sys.executable, str(ROOT/'scripts/run_tests.py'),
                        '--workers', str(args.test_workers), '--out', str(out/'test-run')])
    commands = [test_command,
                [sys.executable, '-m', 'superfish_ng', 'converge', '--out', str(out/'pillbox_convergence.json')]]
    runs = []
    for name, command in zip(['tests', 'convergence'], commands):
        start = time.perf_counter()
        parallel_tests = name == 'tests' and args.test_workers > 1
        if parallel_tests:
            run = subprocess.run(command, cwd=ROOT, env=env)
            if (out/'test-run/tests.log').exists():
                shutil.copyfile(out/'test-run/tests.log', out/'tests.log')
        else:
            run = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
            (out/f'{name}.log').write_text(run.stdout+run.stderr, encoding='utf-8')
        runs.append({'name': name, 'command': command[1:], 'exit_code': run.returncode, 'seconds': time.perf_counter()-start})
        if run.returncode:
            if not parallel_tests:
                print(run.stdout+run.stderr, file=sys.stderr)
            return run.returncode
    case = replace(Case.load(ROOT/'examples/pillbox.json'), modes=6, nr=40, nz=48)
    sol = solve(case)
    save_run(case, sol, out/'pillbox')
    exact = pillbox_spectrum(.1, .2, 6)
    modes = [{'label': item[1], 'analytic_hz': item[0], 'numerical_hz': float(f),
              'relative_error': abs(float(f)/item[0]-1)} for item,f in zip(exact, sol.frequencies_hz)]
    (out/'multimode.json').write_text(json.dumps(modes, indent=2)+'\n')
    shaped = Case.load(ROOT/'examples/shaped_cell.json')
    save_run(shaped, solve(shaped), out/'shaped_cell')
    profile_rows = []
    for nr, nz in [(16,32),(32,64),(64,128)]:
        c = replace(shaped, nr=nr,nz=nz,modes=1)
        s = solve(c)
        profile_rows.append({'nr':nr,'nz':nz,'nodes':len(s.mesh.points),'quantities':quantities(c,s)})
    (out/'shaped_refinement.json').write_text(json.dumps({'status':'self-convergence only; not external validation',
                                                       'rows':profile_rows},indent=2)+'\n')
    fingerprints = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for folder in ['src','tests','scripts','examples'] for p in sorted((ROOT/folder).rglob('*'))
                    if p.is_file() and '__pycache__' not in p.parts}
    report = {'passed': all(r['exit_code']==0 for r in runs) and max(m['relative_error'] for m in modes)<.003,
              'environment': {'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,
                              'platform':platform.platform(),'openblas_num_threads':os.environ.get('OPENBLAS_NUM_THREADS'),
                              'test_workers':args.test_workers},
              'commands':runs,'source_sha256':fingerprints,
              'not_performed':['external solver comparison','legacy SUPERFISH comparison','measured cavity validation','GUI/ParaView interactive check']}
    (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f"Validation {'PASS' if report['passed'] else 'FAIL'}: {out}")
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
