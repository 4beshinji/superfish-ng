# SPDX-License-Identifier: Apache-2.0
"""Reproduce N01 frequency-only acceptance; no high-order RF claim."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
import numpy as np
from superfish_ng import Case, solve
from superfish_ng.analytic import pillbox_spectrum
from superfish_ng.high_order import solve_p2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    out = parser.parse_args().out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    exact = np.array([row[0] for row in pillbox_spectrum(.1, .2, 3)])
    rows = []
    for n in [4, 8, 16, 32]:
        case = Case(((0., .1), (.2, .1)), nr=n, nz=2*n, modes=3)
        for order, solver in [(1, solve), (2, solve_p2)]:
            start = time.perf_counter()
            sol = solver(case)
            rows.append(dict(nr=n, nz=2*n, element_order=order, dofs=len(sol.u),
                             seconds=time.perf_counter()-start,
                             frequencies_hz=sol.frequencies_hz.tolist(),
                             relative_errors=abs(sol.frequencies_hz/exact-1).tolist(),
                             residuals=sol.residuals.tolist()))
    p2 = [row for row in rows if row['element_order'] == 2]
    checks = {
        'n16_frequency_error_below_1e_5': bool(np.all(np.array(p2[2]['relative_errors']) < 1e-5)),
        'n8_to_n16_error_ratio_below_0_2': bool(np.all(np.array(p2[2]['relative_errors']) / p2[1]['relative_errors'] < .2)),
        'p2_better_than_p1_each_base_mesh': all(np.all(np.array(rows[i+1]['relative_errors']) < rows[i]['relative_errors']) for i in range(0, len(rows), 2)),
        'all_free_equation_residuals_below_1e_7': all(max(row['residuals']) < 1e-7 for row in rows),
    }
    fingerprints = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for folder in ['src', 'tests', 'scripts'] for p in sorted((ROOT/folder).rglob('*.py'))}
    report = dict(status='PASS' if all(checks.values()) else 'FAIL', scope='N01 frequencies only; RF is N02',
                  analytic_hz=exact.tolist(), rows=rows, checks=checks, source_sha256=fingerprints)
    (out/'quadratic.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(f"N01 {report['status']}: {out/'quadratic.json'}")
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
