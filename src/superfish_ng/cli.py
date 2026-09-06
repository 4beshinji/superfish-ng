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
    run.add_argument("--reflect-full", action="store_true", help="reflect a single symmetry end; export the full cavity at twice the input energy")
    check = sub.add_parser("converge", help="TM010 pillbox refinement benchmark, with exit-code gate")
    check.add_argument("--levels", nargs="+", type=int, default=[8, 16, 32, 64])
    check.add_argument("--out", required=True, type=Path)
    plot = sub.add_parser("plot", help="plot a saved mode and axial/radial probes (requires plot extra)")
    plot.add_argument("run", type=Path)
    plot.add_argument("--out", required=True, type=Path)
    plot.add_argument("--mode", type=int, default=1)
    plot.add_argument("--probe-z-m", type=float)
    plot.add_argument("--mesh", action="store_true")
    gui = sub.add_parser("gui", help="open the local cavity workspace (plot extra required)")
    gui.add_argument("--workspace", type=Path, default=Path("out/gui-workspace"))
    gui.add_argument("--port", type=int, default=0)
    gui.add_argument("--no-browser", action="store_true")
    project = sub.add_parser("run-project", help="solve a shared project or existing case")
    project.add_argument("project", type=Path)
    project.add_argument("--out", type=Path, required=True)
    study = sub.add_parser("study", help="run a saved parameter or refinement study")
    study.add_argument("study", type=Path)
    study.add_argument("--out", type=Path, required=True)
    band = sub.add_parser("band", help="analyze an explicitly declared half-end cell band")
    band.add_argument("run", type=Path)
    band.add_argument("--centers-m", nargs="+", type=float, required=True)
    band.add_argument("--out", type=Path, required=True)
    probe = sub.add_parser("probe", help="export a radial probe from saved fields")
    probe.add_argument("run", type=Path)
    probe.add_argument("--z-m", type=float, required=True)
    probe.add_argument("--mode", type=int, default=1)
    probe.add_argument("--out", type=Path, required=True)
    reference = sub.add_parser("compare-pillbox", help="compare saved cylindrical modes with independent analytical fields and RF")
    reference.add_argument("run", type=Path)
    reference.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "gui":
            from .gui import serve
            serve(args.workspace, args.port, not args.no_browser)
        elif args.command == "study":
            from .studies import Study, execute_study
            from .project import parse_json
            study = Study.from_dict(parse_json(args.study.read_text()))
            report = execute_study(study, args.out)
            print(f"study complete; numerical status: {report['numerical_status']}")
            return 1 if report['numerical_status'] == 'FAIL' else 0
        elif args.command == "compare-pillbox":
            from .saved import compare_pillbox
            if args.out.exists():raise ValueError(f"output already exists: {args.out}")
            report = compare_pillbox(args.run)
            with args.out.open('x') as stream:json.dump(report, stream, indent=2, allow_nan=False)
            return 0 if all(m['status']=='PASS' for m in report['modes']) else 1
        elif args.command == "probe":
            from .saved import export_radial_probe
            export_radial_probe(args.run, args.out, args.z_m, args.mode)
        elif args.command == "band":
            from .saved import analyze_band
            if args.out.exists():
                raise ValueError(f"output already exists: {args.out}")
            report = analyze_band(args.run, args.centers_m)
            with args.out.open('x') as stream:
                json.dump(report, stream, indent=2, allow_nan=False)
        elif args.command == "run-project":
            from .project import Project
            from .jobs import execute_project
            result = execute_project(Project.load(args.project), args.out)
            print(f"{result['status']}: {args.out}")
        elif args.command == "solve":
            if args.out.exists():
                raise ValueError(f"output already exists: {args.out}; choose a new directory")
            case = Case.load(args.case)
            solution = solve(case)
            if args.reflect_full:
                from .symmetry import reflect_solution
                case, solution = reflect_solution(case, solution)
            result = save_run(case, solution, args.out)
            for mode in result["modes"]:
                print(f"Mode {mode['mode_index']}: {mode['frequency_hz']/1e6:.6f} MHz, "
                      f"Q0={mode['q0']:.3f}, R/Q(acc)={mode['r_over_q_accelerator_ohm']:.6f} ohm")
        elif args.command == "plot":
            try:
                from .visualize import plot_mode
            except ImportError as exc:
                raise ValueError("plotting requires the optional dependencies: pip install -e '.[plot]'") from exc
            plot_mode(args.run, args.out, args.mode, args.probe_z_m, args.mesh)
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
