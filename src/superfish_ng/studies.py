# SPDX-License-Identifier: Apache-2.0
"""Explicit parameter studies and same-geometry refinement diagnostics."""

from copy import deepcopy
from dataclasses import dataclass, replace
import json
import math
from pathlib import Path
import sys
import traceback
import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.integrate import trapezoid
from .config import keys
from .project import Project, assemble_geometry
from .jobs import execute_project, _state, _write_json, _digest, _implementation_hashes
from .saved import read_solution
from .sampling import FieldSampler
from .mesh import element_geometry
from .constants import EPS0, TAU

RF_KEYS = [
    "q0",
    "geometry_factor_ohm",
    "r_over_q_accelerator_ohm",
    "r_over_q_circuit_ohm",
    "wall_loss_w",
    "transit_time_factor_abs",
]


@dataclass
class Study:
    project: Project
    kind: str
    parameter: str
    values: list

    def __post_init__(self):
        if self.kind not in ("sweep", "mesh_convergence", "geometry_convergence"):
            raise ValueError(
                "study kind must be sweep, mesh_convergence or geometry_convergence"
            )
        if (
            not isinstance(self.values, list)
            or len(self.values) < 2
            or any(
                type(v) not in (int, float) or not math.isfinite(v) for v in self.values
            )
        ):
            raise ValueError("study values must contain at least two finite numbers")
        if not isinstance(self.parameter, str):
            raise ValueError("study parameter must be a string")
        if self.kind == "mesh_convergence":
            if (
                self.parameter != "mesh_scale"
                or any(type(v) is not int or v < 1 for v in self.values)
                or any(b <= a for a, b in zip(self.values, self.values[1:]))
            ):
                raise ValueError(
                    "mesh convergence requires increasing positive integer mesh_scale values"
                )
        elif self.kind == "geometry_convergence":
            if (
                self.parameter != "/case/geometry/chord_tolerance_m"
                or self.project.case.geometry_type != "arc_profile"
                or any(v <= 0 for v in self.values)
                or any(b >= a for a, b in zip(self.values, self.values[1:]))
            ):
                raise ValueError(
                    "geometry convergence requires decreasing positive arc chord tolerances"
                )
        elif not self.parameter.startswith(("/case/", "/sections/")):
            raise ValueError(
                "sweep parameter must be an existing /case/ or /sections/ numeric path"
            )

    def to_dict(self):
        return {
            "study_version": 1,
            "project": self.project.to_dict(),
            "kind": self.kind,
            "parameter": self.parameter,
            "values": self.values,
        }

    @classmethod
    def from_dict(cls, data):
        keys(
            data,
            ["study_version", "project", "kind", "parameter", "values"],
            ["study_version", "project", "kind", "parameter", "values"],
            "study",
        )
        if type(data["study_version"]) is not int or data["study_version"] != 1:
            raise ValueError("only study_version 1 is supported")
        return cls(
            Project.from_dict(data["project"]),
            data["kind"],
            data["parameter"],
            data["values"],
        )

    def save(self, path):
        with Path(path).open("x", encoding="utf-8") as stream:
            json.dump(
                self.to_dict(), stream, ensure_ascii=False, indent=2, allow_nan=False
            )

    def projects(self):
        self.__post_init__()
        projects = []
        for value in self.values:
            raw = deepcopy(self.project.to_dict())
            if self.parameter == "mesh_scale":
                raw["case"]["mesh"]["nr"] *= value
                raw["case"]["mesh"]["nz"] *= value
                for key in ("boundary_max_edge_m", "corner_max_edge_m"):
                    if key in raw["case"]["mesh"]:
                        raw["case"]["mesh"][key] /= value
            else:
                parts = self.parameter.strip("/").split("/")
                parent = raw
                try:
                    for part in parts[:-1]:
                        parent = (
                            parent[int(part)]
                            if isinstance(parent, list)
                            else parent[part]
                        )
                    key = int(parts[-1]) if isinstance(parent, list) else parts[-1]
                    old = parent[key]
                    if type(old) not in (int, float):
                        raise ValueError("study target must be a numeric field")
                    parent[key] = value
                except (KeyError, IndexError, TypeError) as exc:
                    raise ValueError(
                        "study parameter does not exist in the saved project"
                    ) from exc
                if parts[0] == "sections":
                    raw["case"]["schema_version"] = max(raw["case"]["schema_version"], 2)
                    raw["case"]["geometry"] = assemble_geometry(raw["sections"])
                elif "sections" in raw and parts[:2] == ["case", "geometry"]:
                    # Direct geometry edits intentionally detach its editing recipe.
                    del raw["sections"]
            projects.append(Project.from_dict(raw))
        return projects


def _physical_spec(case):
    from .model import Model
    raw = case.to_dict()
    # Schema migration and names of the single interior/vacuum material do not
    # alter physics. Retain the actual physics declaration in the comparison.
    raw['model'] = replace(case.model or Model(), material_id='vacuum', region_id='cavity').to_dict()
    raw.pop("mesh")
    raw["solver"].pop("element_order", None)
    raw.pop("name")
    raw.pop("schema_version")
    raw["geometry"].pop("chord_tolerance_m", None)
    return raw


def compare_refinement(first_dir, second_dir):
    """Pair only unchanged physical geometry; abstain on ambiguous overlap.

    This sampled field criterion is a pairing diagnostic, not a mathematical
    error bound or a tracker for different shapes. Degenerate modes abstain.
    """
    first, second = read_solution(first_dir), read_solution(second_dir)
    if _physical_spec(first.case) != _physical_spec(second.case):
        raise ValueError("refinement comparison requires identical physical cases")
    vertices, det, _ = element_geometry(first.mesh)
    indices = np.linspace(0, len(vertices) - 1, min(4096, len(vertices)), dtype=int)
    positions = vertices[indices].mean(axis=1)
    weights = det[indices] * positions[:, 0]
    sampled = []
    for solution in (first, second):
        sampler = FieldSampler.from_solution(solution)
        sampled.append(
            np.column_stack(
                [
                    sampler.evaluate(positions, i, outside="nan")["Hphi_A_per_m"]
                    for i in range(solution.case.modes)
                ]
            )
        )
    common = np.isfinite(sampled[0]).all(axis=1) & np.isfinite(sampled[1]).all(axis=1)
    if common.sum() < 10:
        raise ValueError("insufficient common field samples for refinement pairing")
    a, b = [v[common] * np.sqrt(weights[common, None]) for v in sampled]
    signed = a.T @ b / np.outer(np.linalg.norm(a, axis=0), np.linalg.norm(b, axis=0))
    scores = np.abs(signed)
    rows, columns = linear_sum_assignment(1 - scores)
    records = []
    for i, j in zip(rows, columns):
        competing = max(
            np.max(np.delete(scores[i], j), initial=0),
            np.max(np.delete(scores[:, j], i), initial=0),
        )
        degenerate = any(
            np.any(
                np.delete(np.abs(s.frequencies_hz / s.frequencies_hz[k] - 1), k) < 1e-6
            )
            for s, k in [(first, i), (second, j)]
        )
        identifiable = bool(
            scores[i, j] >= 0.98 and scores[i, j] - competing >= 0.02 and not degenerate
        )
        qa, qb = first.results["modes"][i], second.results["modes"][j]
        differences = {
            key: abs(qb[key] / qa[key] - 1) if qa[key] else None
            for key in ["frequency_hz", *RF_KEYS]
        }
        axis = []
        for solution, k in [(first, i), (second, j)]:
            nodes = solution.arrays["axis_nodes"]
            axis.append(
                (
                    solution.mesh.points[nodes, 1],
                    2
                    * solution.u[nodes, k]
                    / (TAU * EPS0 * solution.frequencies_hz[k]),
                )
            )
        z = np.union1d(axis[0][0], axis[1][0])
        ea = np.interp(z, *axis[0])
        eb = np.interp(z, *axis[1])
        integration_weights = None
        if first.element_order == 2 or second.element_order == 2:
            # Union of original axis element endpoints; three Gauss points
            # integrate the square of either P1/P2 difference exactly.
            knots = z
            qg, wg = np.polynomial.legendre.leggauss(3)
            lo, hi = knots[:-1], knots[1:]
            z = ((lo+hi)[:, None]/2+(hi-lo)[:, None]*qg/2).ravel()
            integration_weights = ((hi-lo)[:, None]*wg/2).ravel()
            positions_axis = np.column_stack((np.zeros_like(z), z))
            ea = FieldSampler.from_solution(first).evaluate(positions_axis, int(i))['Ez_quadrature_V_per_m']
            eb = FieldSampler.from_solution(second).evaluate(positions_axis, int(j))['Ez_quadrature_V_per_m']
        if signed[i, j] < 0:
            eb = -eb
        integral = trapezoid if integration_weights is None else lambda values, _: np.dot(integration_weights, values)
        norm = integral(ea**2, z)
        axis_error = (
            float(np.sqrt(integral((eb - ea) ** 2, z) / norm)) if norm > 0 else None
        )
        gates = {
            "frequency": differences["frequency_hz"] < 0.001,
            "axis_field": axis_error is not None and axis_error < 0.01,
            "rf": all(
                differences[k] is not None and differences[k] < 0.01 for k in RF_KEYS
            ),
        }
        verified = (
            identifiable
            and axis_error is not None
            and all(v is not None for v in differences.values())
        )
        records.append(
            {
                "first_mode_index": int(i + 1),
                "second_mode_index": int(j + 1),
                "field_overlap": float(scores[i, j]),
                "pair_identified": identifiable,
                "relative_changes": differences,
                "axis_relative_l2": axis_error,
                "rq_absolute_change_ohm": abs(
                    qb["r_over_q_accelerator_ohm"] - qa["r_over_q_accelerator_ohm"]
                ),
                "gates": gates,
                "status": ("PASS" if all(gates.values()) else "FAIL")
                if verified
                else "UNVERIFIED",
            }
        )
    statuses = [m["status"] for m in records]
    status = (
        "UNVERIFIED"
        if "UNVERIFIED" in statuses
        else "PASS"
        if all(s == "PASS" for s in statuses)
        else "FAIL"
    )
    return {
        "status": status,
        "pairing": "same geometry; sampled magnetic-field overlap",
        "samples": int(common.sum()),
        "limits": {
            "frequency": 0.001,
            "rf": 0.01,
            "axis_field": 0.01,
            "pair_overlap": 0.98,
            "pair_margin": 0.02,
        },
        "modes": records,
        "surface_field": "not certified; P1 peak estimates retained",
    }


def execute_study(study, directory, prepared=False):
    implementation = _implementation_hashes()
    directory = Path(directory)
    projects = study.projects()  # validate every point before starting
    if not prepared:
        directory.mkdir(parents=True, exist_ok=False)
        study.save(directory / "study.json")
        _state(directory, "queued", kind="study")
    try:
        points = []
        comparisons = []
        for i, project in enumerate(projects):
            _state(
                directory,
                "running",
                kind="study",
                stage=f"point {i + 1}/{len(projects)}",
                completed_points=i,
            )
            target = directory / f"point-{i + 1:03d}"
            execute_project(project, target)
            result = read_solution(target / "solution").results
            points.append(
                {
                    "value": study.values[i],
                    "directory": target.name,
                    "case_sha256": result["case_sha256"],
                    "modes": result["modes"],
                }
            )
            if i and study.kind != "sweep":
                comparisons.append(
                    compare_refinement(
                        directory / points[-2]["directory"] / "solution",
                        target / "solution",
                    )
                )
        report = {
            "study": study.to_dict(),
            "points": points,
            "comparisons": comparisons,
            "mode_tracking": "not performed; independent spectra",
            "numerical_status": comparisons[-1]["status"]
            if comparisons
            else "UNVERIFIED",
            "surface_field": "P1 estimates; not certified",
        }
        if implementation != _implementation_hashes():
            raise RuntimeError(
                "implementation changed during study; retry with stable source"
            )
        report["implementation_sha256"] = implementation
        _write_json(directory / "study-results.json", report)
        files = {
            p.relative_to(directory).as_posix(): _digest(p)
            for p in directory.rglob("*")
            if p.is_file() and p.name not in ("job.json", "log.txt")
        }
        _write_json(
            directory / "manifest.json",
            {"manifest_version": 1, "kind": "study", "files": files},
        )
        _state(
            directory,
            "complete",
            kind="study",
            numerical_validation=report["numerical_status"],
        )
        return report
    except Exception as exc:
        _state(directory, "failed", kind="study", error=str(exc))
        raise


if __name__ == "__main__":
    try:
        directory = Path(sys.argv[1])
        study = Study.from_dict(json.loads((directory / "study.json").read_text()))
        execute_study(study, directory, prepared=True)
    except Exception:
        traceback.print_exc()
        sys.exit(2)
