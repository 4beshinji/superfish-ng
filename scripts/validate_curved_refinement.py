# SPDX-License-Identifier: Apache-2.0
"""Run separate geometry and FEM studies of the synthetic ellipsoid."""
import argparse
from dataclasses import replace
import json
from pathlib import Path

from superfish_ng import Case
from superfish_ng.project import Project
from superfish_ng.studies import Study, execute_study


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    parser.add_argument("--max-rounds", type=int, default=12)
    args = parser.parse_args()
    root = Path(args.out)
    root.mkdir(parents=True, exist_ok=False)
    case = Case.load(Path(__file__).resolve().parents[1] / "examples/curved_ellipse.json")
    case = replace(case, contour_mesh=replace(case.contour_mesh, max_rounds=args.max_rounds))
    geometry_case = replace(case, contour_mesh=replace(case.contour_mesh, max_edge_m=.005))
    fem_case = replace(case, contour=None, curve_chord_tolerance_m=.00003125)
    studies = {
        "geometry": Study(Project.from_dict(geometry_case.to_dict()), "geometry_convergence",
                          "/case/geometry/chord_tolerance_m", [.0005, .000125, .00003125]),
        "fem": Study(Project.from_dict(fem_case.to_dict()), "mesh_convergence",
                     "mesh_scale", [1, 2, 4]),
    }
    reports = {}
    for name, study in studies.items():
        print(f"Running {name} refinement", flush=True)
        try:
            report = execute_study(study, root / name)
        except (ValueError, RuntimeError) as exc:
            reports[name] = {"numerical_status": "UNVERIFIED", "execution_status": "FAIL", "error": str(exc)}
            print(f"{name}: execution FAIL: {exc}", flush=True)
            continue
        reports[name] = {
            "numerical_status": report["numerical_status"],
            "comparisons": report["comparisons"],
            "geometry_errors": [p["geometry_approximation"] for p in report["points"]],
        }
        print(f'{name}: {report["numerical_status"]}', flush=True)
    result = {
        "scope": "synthetic ellipsoid, fundamental mode, straight P2 elements",
        "reference": "successive discretizations; analytic area and revolution volume only",
        "surface_field": "not certified",
        "studies": reports,
    }
    (root / "summary.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(root / "summary.json", flush=True)
    return 0 if all(r["numerical_status"] == "PASS" for r in reports.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
