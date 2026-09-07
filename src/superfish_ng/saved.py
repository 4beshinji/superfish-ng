# SPDX-License-Identifier: Apache-2.0
"""Validate and read portable saved fields without rerunning the FEM solve."""

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
from .config import Case
from .constants import EPS0, TAU
from .mesh import element_geometry
from .modes import identify_cell_band, fit_dispersion
from .geometry import linearize_profile


def read_solution(directory):
    directory = Path(directory)
    results = json.loads((directory / "results.json").read_text(encoding="utf-8"))
    if type(results.get("schema_version")) is not int or results["schema_version"] != 1:
        raise ValueError("only saved result schema_version 1 is supported")
    case = Case.load(directory / "case.json")
    if Case.from_dict(results["case"]) != case:
        raise ValueError("saved case and result case differ")
    canonical = json.dumps(
        case.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    if hashlib.sha256(canonical.encode()).hexdigest() != results["case_sha256"]:
        raise ValueError("saved case hash differs")
    with np.load(directory / "fields.npz", allow_pickle=False) as data:
        arrays = {
            key: data[key]
            for key in (
                "points_rz_m",
                "triangles",
                "u_a_per_m2",
                "frequencies_hz",
                "boundary_edges",
                "boundary_tags",
                "boundary_cells",
                "axis_nodes",
            )
        }
    p, t, u, f = (
        arrays[k] for k in ("points_rz_m", "triangles", "u_a_per_m2", "frequencies_hz")
    )
    if (
        p.ndim != 2
        or p.shape[1] != 2
        or t.ndim != 2
        or t.shape[1] != 3
        or not np.issubdtype(t.dtype, np.integer)
        or not len(t)
        or t.min() < 0
        or t.max() >= len(p)
        or u.shape != (len(p), case.modes)
        or f.shape != (case.modes,)
        or len(results["modes"]) != case.modes
        or not all(np.isfinite(a).all() for a in (p, u, f))
        or np.any(f <= 0)
        or np.any(np.diff(f) < 0)
    ):
        raise ValueError("invalid saved field dimensions, topology, or frequencies")
    mesh = SimpleNamespace(points=p, triangles=t)
    element_geometry(mesh)
    if 'input_sha256' in results['mesh']:
        from .mesh_input import mesh_digest, mesh_from_dict
        from .project import parse_json
        mesh_data = parse_json((directory/'mesh.json').read_text(encoding='utf-8'))
        if mesh_digest(mesh_data) != results['mesh']['input_sha256']:
            raise ValueError('saved external mesh hash differs')
        imported = mesh_from_dict(case, mesh_data)
        for name, actual in (('points', p), ('triangles', t),
                             ('boundary_edges', arrays['boundary_edges']),
                             ('boundary_tags', arrays['boundary_tags']),
                             ('boundary_cells', arrays['boundary_cells']),
                             ('axis_nodes', arrays['axis_nodes'])):
            if not np.array_equal(getattr(imported, name), actual):
                raise ValueError(f'saved external mesh {name} differs from fields')
    axis = arrays["axis_nodes"]
    if (
        axis.ndim != 1
        or len(axis) < 2
        or not np.issubdtype(axis.dtype, np.integer)
        or axis.min() < 0
        or axis.max() >= len(p)
        or np.any(p[axis, 0] != 0)
        or np.any(np.diff(p[axis, 1]) <= 0)
    ):
        raise ValueError("invalid saved axis nodes")
    edges = arrays["boundary_edges"]
    tags = arrays["boundary_tags"]
    cells = arrays["boundary_cells"]
    if (
        edges.ndim != 2
        or edges.shape[1] != 2
        or not len(edges)
        or not np.issubdtype(edges.dtype, np.integer)
        or edges.min() < 0
        or edges.max() >= len(p)
        or tags.shape != (len(edges),)
        or cells.shape != (len(edges),)
        or not np.issubdtype(cells.dtype, np.integer)
        or cells.min() < 0
        or cells.max() >= len(t)
        or not np.isin(
            tags, ["axis", "pec", "electric_symmetry", "magnetic_symmetry"]
        ).all()
    ):
        raise ValueError("invalid saved boundary arrays")
    for i, q in enumerate(results["modes"]):
        axis_csv = np.loadtxt(
            directory / f"axis_{i + 1:03d}.csv", delimiter=",", skiprows=1
        )
        expected = np.column_stack((p[axis, 1], 2 * u[axis, i] / (TAU * EPS0 * f[i])))
        if (
            q["mode_index"] != i + 1
            or q["frequency_hz"] != f[i]
            or axis_csv.shape != expected.shape
            or not np.isfinite(axis_csv).all()
            or not np.allclose(axis_csv, expected, rtol=1e-12, atol=1e-8)
        ):
            raise ValueError("saved axis CSV, modes, and fields disagree")
    return SimpleNamespace(
        case=case, results=results, mesh=mesh, u=u, frequencies_hz=f, arrays=arrays
    )


def analyze_band(directory, cell_centers_z_m):
    """Explicit half-end cosine-band analysis with geometry and field checks.

    A user-supplied cell count alone never licenses physical phase labels.
    Centers must span both PEC end planes with equal spacing, and each
    center-to-center interval must have the same radial profile.
    """
    saved = read_solution(directory)
    case = saved.case
    centers = np.asarray(cell_centers_z_m, dtype=float)
    if (
        centers.ndim != 1
        or len(centers) < 2
        or not np.isfinite(centers).all()
        or np.any(np.diff(centers) <= 0)
        or case.z_min != "pec"
        or case.z_max != "pec"
        or not np.isclose(centers[0], 0, rtol=0, atol=1e-12)
        or not np.isclose(centers[-1], case.length, rtol=0, atol=1e-12)
        or not np.allclose(np.diff(centers), np.diff(centers)[0], rtol=1e-9, atol=1e-12)
    ):
        raise ValueError(
            "half-end band requires equally spaced cell centers on both PEC end planes; full-end or nonperiodic labels are unsupported"
        )
    # Compare original vertices and arc metadata, not a sampling grid that
    # could miss a narrow nonperiodic notch between sample coordinates.
    wall = np.asarray(case.profile)
    linear = np.asarray(linearize_profile(case))
    signatures = []
    for a, b in zip(centers, centers[1:]):
        inner = wall[(wall[:, 0] > a + 1e-12) & (wall[:, 0] < b - 1e-12)].copy()
        inner[:, 0] -= a
        polygon = np.vstack(
            (
                [0, np.interp(a, linear[:, 0], linear[:, 1])],
                inner,
                [b - a, np.interp(b, linear[:, 0], linear[:, 1])],
            )
        )
        arcs = []
        for index, radius, direction in case.arcs:
            start, end = wall[index - 1, 0], wall[index, 0]
            if end <= a + 1e-12 or start >= b - 1e-12:
                continue
            if start < a - 1e-12 or end > b + 1e-12:
                raise ValueError(
                    "band geometry check cannot split a circular arc at a cell center"
                )
            arcs.append([start - a, end - a, radius, 1 if direction == "ccw" else -1])
        signatures.append((polygon, np.asarray(arcs).reshape(-1, 4)))
    for signature in signatures[1:]:
        if any(
            x.shape != y.shape or not np.allclose(x, y, rtol=1e-8, atol=1e-12)
            for x, y in zip(signature, signatures[0])
        ):
            raise ValueError(
                "nonperiodic geometry does not satisfy the half-end band model"
            )
    axis = saved.arrays["axis_nodes"]
    z = saved.mesh.points[axis, 1]
    field = 2 * saved.u[axis] / (TAU * EPS0 * saved.frequencies_hz)
    modes = identify_cell_band(z, field, centers)
    dispersion = fit_dispersion(
        [m["phase_rad"] for m in modes],
        [saved.frequencies_hz[m["mode_index"] - 1] for m in modes],
    )
    return {
        "model": "half_end_cosine",
        "cell_centers_z_m": centers.tolist(),
        "modes": modes,
        "dispersion": dispersion,
        "scope": "field-based labels for this geometry only; not mode tracking across shape changes",
    }


def export_radial_probe(directory, out, z_m, mode=1):
    """Export unsmoothed saved fields on a radial line, in SI peak phasors."""
    from .sampling import FieldSampler, radial_extent
    from .constants import MU0

    saved = read_solution(directory)
    if type(mode) is not int or not 1 <= mode <= saved.case.modes:
        raise ValueError("probe mode must be a valid one-based integer")
    if (
        type(z_m) not in (int, float)
        or not np.isfinite(z_m)
        or not 0 <= z_m <= saved.case.length
    ):
        raise ValueError("probe z must lie inside the saved input domain in metres")
    radius = radial_extent(saved.mesh.points, saved.arrays["boundary_edges"], z_m)
    positions = np.column_stack((np.linspace(0, radius, 401), np.full(401, z_m)))
    sampler = FieldSampler(
        saved.mesh.points, saved.mesh.triangles, saved.u, saved.frequencies_hz
    )
    fields = sampler.evaluate(positions, mode - 1)
    columns = np.column_stack(
        (
            positions,
            fields["Er_quadrature_V_per_m"],
            fields["Ez_quadrature_V_per_m"],
            fields["Hphi_A_per_m"],
            MU0 * fields["Hphi_A_per_m"],
        )
    )
    out = Path(out)
    metadata_path = out.with_suffix(out.suffix + ".json")
    if out.exists() or metadata_path.exists():
        raise FileExistsError(f"probe output already exists: {out}")
    metadata = {
        "mode_index": mode,
        "frequency_hz": float(saved.frequencies_hz[mode - 1]),
        "z_m": z_m,
        "samples": len(positions),
        "case_sha256": saved.results["case_sha256"],
        "stored_energy_j": saved.results["modes"][mode - 1]["stored_energy_j"],
        "phasor": saved.results["conventions"]["phasor"],
    }
    with out.open("x", encoding="utf-8") as stream:
        np.savetxt(
            stream,
            columns,
            delimiter=",",
            header="r_m,z_m,Er_quadrature_V_per_m,Ez_quadrature_V_per_m,Hphi_A_per_m,Bphi_T",
            comments="",
        )
    with metadata_path.open("x", encoding="utf-8") as stream:
        json.dump(metadata, stream, indent=2, allow_nan=False)
    return metadata


def compare_pillbox(directory):
    """Independent analytical reference; associate labels using actual H fields."""
    from scipy.special import j1, jn_zeros
    from scipy.optimize import linear_sum_assignment
    from scipy.integrate import trapezoid
    from .analytic import pillbox_spectrum, pillbox_tm_mode
    from .sampling import FieldSampler

    saved = read_solution(directory)
    case = saved.case
    if (
        case.arcs
        or case.z_min != "pec"
        or case.z_max != "pec"
        or any(r != case.profile[0][1] for _, r in case.profile)
    ):
        raise ValueError(
            "analytical pillbox comparison requires a constant-radius full PEC cylinder; reflect a symmetry subdomain first"
        )
    radius = case.profile[0][1]
    candidates = pillbox_spectrum(radius, case.length, case.modes + 4)
    vertices, det, _ = element_geometry(saved.mesh)
    indices = np.linspace(0, len(vertices) - 1, min(4096, len(vertices)), dtype=int)
    points = vertices[indices].mean(axis=1)
    weights = det[indices] * points[:, 0]
    sampler = FieldSampler(
        saved.mesh.points, saved.mesh.triangles, saved.u, saved.frequencies_hz
    )
    actual = np.column_stack(
        [sampler.evaluate(points, i)["Hphi_A_per_m"] for i in range(case.modes)]
    )
    references = [
        pillbox_tm_mode(
            radius,
            case.length,
            n,
            p,
            case.beta,
            case.conductivity_s_per_m,
            case.normalization_j,
        )
        for _, _, n, p in candidates
    ]
    expected = np.column_stack(
        [
            q["h0_a_per_m"]
            * j1(jn_zeros(0, n)[-1] * points[:, 0] / radius)
            * np.cos(p * np.pi * points[:, 1] / case.length)
            for (_, _, n, p), q in zip(candidates, references)
        ]
    )
    a, b = actual * np.sqrt(weights[:, None]), expected * np.sqrt(weights[:, None])
    signed = a.T @ b / np.outer(np.linalg.norm(a, axis=0), np.linalg.norm(b, axis=0))
    score = np.abs(signed)
    rows, columns = linear_sum_assignment(1 - score)
    result = []
    axis = saved.arrays["axis_nodes"]
    z = saved.mesh.points[axis, 1]
    for i, j in zip(rows, columns):
        ref = references[j]
        f, label, n, p = candidates[j]
        margin = score[i, j] - np.max(np.delete(score[i], j), initial=0)
        unique = (
            score[i, j] >= 0.98
            and margin >= 0.02
            and not any(
                k != j and abs(candidate[0] / f - 1) < 1e-6
                for k, candidate in enumerate(candidates)
            )
        )
        q = saved.results["modes"][i]
        compare_keys = [
            "frequency_hz",
            "q0",
            "geometry_factor_ohm",
            "wall_loss_w",
            "r_over_q_accelerator_ohm",
            "r_over_q_circuit_ohm",
            "transit_time_factor_abs",
        ]
        errors = {
            key: abs(q[key] / ref[key] - 1) if ref[key] else None
            for key in compare_keys
        }
        numerical = 2 * saved.u[axis, i] / (TAU * EPS0 * saved.frequencies_hz[i])
        reference = ref["e0_v_per_m"] * np.cos(p * np.pi * z / case.length)
        if signed[i, j] < 0:
            numerical = -numerical
        error = float(
            np.sqrt(
                trapezoid((numerical - reference) ** 2, z) / trapezoid(reference**2, z)
            )
        )
        gates = {
            "frequency": errors["frequency_hz"] < 0.001,
            "axis_field": error < 0.01,
            "rf": all(
                errors[k] is not None and errors[k] < 0.01
                for k in compare_keys
                if k != "frequency_hz"
            ),
        }
        result.append(
            {
                "mode_index": int(i + 1),
                "label": label if unique else None,
                "n": n if unique else None,
                "p": p if unique else None,
                "field_overlap": float(score[i, j]),
                "axis_relative_l2": error,
                "reference": ref,
                "relative_errors": errors,
                "gates": gates,
                "status": ("PASS" if all(gates.values()) else "FAIL")
                if unique
                else "UNVERIFIED",
            }
        )
    return {
        "reference": "independent full PEC pillbox TM0np analysis; no solver correction",
        "case_sha256": saved.results["case_sha256"],
        "modes": result,
        "surface_field": "not included in the frequency/field/RF gates; P1 estimates remain separate",
    }
