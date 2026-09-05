# SPDX-License-Identifier: Apache-2.0
import argparse
import json
import sys
from pathlib import Path
from dataclasses import replace
from . import __version__
from .analytic import pillbox_tm010
from .config import Case
from .io import save_run
from .rf import quantities
from .solver import solve


def main(argv=None):
    parser = argparse.ArgumentParser(description="Superfish-NG: axisymmetric TM research solver")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("solve", help="solve a JSON case and export RF quantities/fields")
    run.add_argument("case", type=Path)
    run.add_argument("--out", required=True, type=Path, help="new output directory; must not exist")
    check = sub.add_parser("converge", help="TM010 pillbox refinement benchmark, with exit-code gate")
    check.add_argument("--levels", nargs="+", type=int, default=[8, 16, 32, 64])
    check.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "solve":
            if args.out.exists():
                raise ValueError(f"output already exists: {args.out}; choose a new directory")
            case = Case.load(args.case)
            result = save_run(case, solve(case), args.out)
            for mode in result["modes"]:
                print(f"Mode {mode['mode_index']}: {mode['frequency_hz']/1e6:.6f} MHz, "
                      f"Q0={mode['q0']:.3f}, R/Q(acc)={mode['r_over_q_accelerator_ohm']:.6f} ohm")
        else:
            if args.out.exists():
                raise ValueError(f"output already exists: {args.out}")
            if len(args.levels) < 2 or any(n < 2 for n in args.levels) or any(b <= a for a, b in zip(args.levels, args.levels[1:])):
                raise ValueError("levels must be at least two strictly increasing integers >= 2")
            base = Case(((0., .1), (.2, .1)), modes=1)
            exact = pillbox_tm010(.1, .2)
            rows = []
            for n in args.levels:
                case = replace(base, nr=n, nz=n)
                solution = solve(case)
                q = quantities(case, solution)
                rows.append({"nr": n, "nz": n, "nodes": len(solution.mesh.points), "quantities": q,
                             "relative_errors": {k: abs(q[k]/v-1) for k, v in exact.items() if v is not None and v != 0}})
                print(f"n={n}: f={q['frequency_hz']/1e6:.9f} MHz, relative error={rows[-1]['relative_errors']['frequency_hz']:.3g}")
            freq = [r["relative_errors"]["frequency_hz"] for r in rows]
            gates = {"frequency_finest_below_1e-4": freq[-1] < 1e-4,
                     "frequency_error_decreases": all(b < a for a, b in zip(freq, freq[1:])),
                     "rq_finest_below_0_005": rows[-1]["relative_errors"]["r_over_q_accelerator_ohm"] < .005,
                     "q0_finest_below_0_005": rows[-1]["relative_errors"]["q0"] < .005}
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps({"benchmark": "pillbox TM010 R=.1 L=.2 beta=1 sigma=5.8e7", "analytic": exact,
                                           "rows": rows, "gates": gates, "passed": all(gates.values())}, indent=2, allow_nan=False)+"\n")
            return 0 if all(gates.values()) else 1
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
