# SPDX-License-Identifier: Apache-2.0
"""Numerical acceptance fixtures for the general project/study interfaces.

Fixture names appear only in this verifier, never in the product dispatch.
No Wine executable or legacy result is used by this script.
"""

import argparse
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import subprocess
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from superfish_ng.project import Project
from superfish_ng.jobs import execute_project, _write_json, _implementation_hashes
from superfish_ng.studies import Study, execute_study
from superfish_ng.saved import (
    read_solution,
    compare_pillbox,
    analyze_band,
    export_radial_probe,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    source = _implementation_hashes()
    started = time.monotonic()
    records = []

    def record(name, passed, **evidence):
        records.append({"id": name, "passed": bool(passed), **evidence})
        _write_json(out / "progress.json", {"checks": records, "complete": False})
        print(f"{name}: {'PASS' if passed else 'FAIL'}", flush=True)

    # Length sweep requests enough modes to include TM011 at every length.
    project = Project.load(ROOT / "examples/seminar_pillbox.json")
    project = Project(replace(project.case, modes=4, nr=96, nz=105))
    study = Study(
        project, "sweep", "/case/geometry/points_zr_m/1/0", [0.04, 0.08, 0.12]
    )
    execute_study(study, out / "pillbox-lengths")
    for i, length in enumerate(study.values):
        directory = out / "pillbox-lengths" / f"point-{i + 1:03d}" / "solution"
        comparison = compare_pillbox(directory)
        _write_json(directory.parent / "analytical.json", comparison)
        targets = [m for m in comparison["modes"] if m["label"] in ("TM010", "TM011")]
        record(
            f"A1-L{length}",
            len(targets) == 2 and all(m["status"] == "PASS" for m in targets),
            modes=targets,
        )
        export_radial_probe(directory, directory.parent / "radial.csv", length / 4)
    for filename in ("seminar_pillbox_half_electric", "seminar_pillbox_half_magnetic"):
        base = Project.load(ROOT / "examples" / f"{filename}.json")
        for end in ("left", "right"):
            case = (
                base.case
                if end == "left"
                else replace(base.case, z_min=base.case.z_max, z_max=base.case.z_min)
            )
            project = Project(case, reflect_full=True)
            directory = out / f"{filename}-{end}"
            execute_project(project, directory)
            comparison = compare_pillbox(directory / "solution")
            _write_json(directory / "analytical.json", comparison)
            saved = read_solution(directory / "solution")
            record(
                f"A2-{filename}-{end}",
                all(m["status"] == "PASS" for m in comparison["modes"])
                and saved.case.normalization_j == 2 * case.normalization_j,
                modes=comparison["modes"],
            )
    # Fixed physical geometry, independently refined FEM. No tolerances are relaxed.
    for filename in (
        "seminar_4cell_flat",
        "seminar_4cell_rounded",
        "seminar_7cell_rounded",
        "seminar_4cell_flat_full_ends",
        "seminar_4cell_rounded_full_ends",
    ):
        base = Project.load(ROOT / "examples" / f"{filename}.json")
        case = replace(base.case, triangulation="crossed")
        if case.geometry_type == "arc_profile":
            case = replace(case, arc_chord_tolerance_m=7.5e-7)
        values = [1, 2, 4, 6] if filename == "seminar_4cell_flat" else [1, 2, 4]
        directory = out / filename
        print(f"Starting {filename}: factors {values}", flush=True)
        report = execute_study(
            Study(Project(case), "mesh_convergence", "mesh_scale", values), directory
        )
        record(
            f"A3-A4-{filename}",
            report["numerical_status"] == "PASS",
            final_comparison=report["comparisons"][-1],
            directory=str(directory),
        )
        finest = directory / report["points"][-1]["directory"] / "solution"
        try:
            band = analyze_band(finest, np.linspace(0, case.length, case.modes))
            _write_json(directory / "band.json", band)
            record(
                f"band-{filename}",
                "full_ends" not in filename,
                labels=[m["label"] for m in band["modes"]],
            )
        except ValueError as exc:
            record(f"band-{filename}", "full_ends" in filename, rejected=str(exc))
    for filename in ("seminar_4cell_rounded", "seminar_7cell_rounded"):
        case = replace(
            Project.load(ROOT / "examples" / f"{filename}.json").case,
            nr=128,
            nz=336 if "4cell" in filename else 672,
            triangulation="crossed",
        )
        directory = out / (filename + "-geometry")
        report = execute_study(
            Study(
                Project(case),
                "geometry_convergence",
                "/case/geometry/chord_tolerance_m",
                [3e-6, 7.5e-7, 1.875e-7],
            ),
            directory,
        )
        record(
            f"A3-geometry-{filename}",
            report["numerical_status"] == "PASS",
            final_comparison=report["comparisons"][-1],
        )
    # Independent synthetic shapes: scale invariance of vacuum Maxwell fields.
    template = Project.load(ROOT / "examples/pillbox.json").case
    template = replace(
        template, nr=24, nz=60, modes=3, name="Synthetic repeated cavity"
    )
    polygon = {
        "type": "profile",
        "points_zr_m": [[0, 0.04], [0.015, 0.06], [0.03, 0.04]],
    }
    arc = {
        "type": "arc_profile",
        "points_zr_m": [[0, 0.04], [0.01, 0.05], [0.02, 0.04]],
        "arcs": [
            {"end_index": 1, "radius_m": 0.01, "direction": "cw"},
            {"end_index": 2, "radius_m": 0.01, "direction": "cw"},
        ],
        "chord_tolerance_m": 1e-5,
    }
    for kind, geometry in [("polygon", polygon), ("arc", arc)]:
        for count in (3, 5):
            project = Project.from_sections(
                template, [{"geometry": geometry, "count": count}]
            )
            directory = out / f"synthetic-{kind}-{count}"
            execute_project(project, directory)
            scaled = deepcopy(geometry)
            scaled["points_zr_m"] = [[2 * z, 2 * r] for z, r in geometry["points_zr_m"]]
            if kind == "arc":
                scaled["arcs"] = [
                    dict(a, radius_m=2 * a["radius_m"]) for a in geometry["arcs"]
                ]
                scaled["chord_tolerance_m"] *= 2
            scaled_project = Project.from_sections(
                template, [{"geometry": scaled, "count": count}]
            )
            execute_project(scaled_project, out / f"synthetic-{kind}-{count}-scaled")
            first = read_solution(directory / "solution").results["modes"]
            second = read_solution(
                out / f"synthetic-{kind}-{count}-scaled" / "solution"
            ).results["modes"]
            checks = []
            for a, b in zip(first, second):
                checks.append(
                    {
                        "frequency_scale_error": abs(
                            b["frequency_hz"] * 2 / a["frequency_hz"] - 1
                        ),
                        "rq_scale_error": abs(
                            b["r_over_q_accelerator_ohm"]
                            / a["r_over_q_accelerator_ohm"]
                            - 1
                        ),
                        "g_scale_error": abs(
                            b["geometry_factor_ohm"] / a["geometry_factor_ohm"] - 1
                        ),
                        "q_scale_error": abs(b["q0"] / a["q0"] / np.sqrt(2) - 1),
                    }
                )
            record(
                f"A5-scale-{kind}-{count}",
                all(v < 1e-9 for c in checks for v in c.values()),
                errors=checks,
            )
            # Refinement and name independence are separate from scaling.
            refinement = execute_study(
                Study(
                    project,
                    "mesh_convergence",
                    "mesh_scale",
                    [1, 2, 4, 8] if kind == "polygon" else [1, 2, 4],
                ),
                out / f"synthetic-{kind}-{count}-refinement",
            )
            record(
                f"A5-refinement-{kind}-{count}",
                refinement["numerical_status"] == "PASS",
                final_comparison=refinement["comparisons"][-1],
            )
            renamed = Project(replace(project.case, name=""), sections=project.sections)
            renamed_directory = out / f"synthetic-{kind}-{count}-unnamed"
            execute_project(renamed, renamed_directory)
            unnamed = read_solution(renamed_directory / "solution").results["modes"]
            name_errors = [
                abs(b[key] / a[key] - 1)
                for a, b in zip(first, unnamed)
                for key in ("frequency_hz", "q0", "r_over_q_accelerator_ohm")
            ]
            record(
                f"A5-name-independent-{kind}-{count}",
                max(name_errors) < 1e-12,
                maximum_relative_difference=max(name_errors),
            )
    # Existing CLI and new project API must produce the same inputs and physics.
    case = Project.load(ROOT / "examples/pillbox.json")
    execute_project(case, out / "python-parity")
    command = [
        sys.executable,
        "-m",
        "superfish_ng",
        "run-project",
        str(ROOT / "examples/pillbox.json"),
        "--out",
        str(out / "cli-parity"),
    ]
    run = subprocess.run(command, capture_output=True, text=True)
    if run.returncode:
        raise RuntimeError(run.stderr)
    a = read_solution(out / "python-parity/solution")
    b = read_solution(out / "cli-parity/solution")
    record(
        "A7-cli-python",
        a.case.to_dict() == b.case.to_dict()
        and np.allclose(a.frequencies_hz, b.frequencies_hz, rtol=1e-12, atol=0),
        command=command,
    )
    report = {
        "passed": all(c["passed"] for c in records),
        "checks": records,
        "elapsed_seconds": time.monotonic() - started,
        "source_changed_during_run": source != _implementation_hashes(),
        "implementation_sha256": source,
        "not_performed": [
            "new Wine comparison",
            "measured cavity validation",
            "human usability evaluation",
        ],
    }
    report["passed"] &= not report["source_changed_during_run"]
    _write_json(out / "report.json", report)
    print(f"Overall {'PASS' if report['passed'] else 'FAIL'}: {out}", flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
