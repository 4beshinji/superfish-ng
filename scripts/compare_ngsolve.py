# SPDX-License-Identifier: Apache-2.0
"""Optional independent Hphi FEM reference; never a production solve backend."""
import argparse
from dataclasses import replace
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import eigsh

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from superfish_ng import Case, solve
from superfish_ng.analytic import pillbox_tm010
from superfish_ng.rf import quantities
from superfish_ng.sampling import FieldSampler

# Independent constants and postprocessing, with the same documented SI values.
C = 299792458.0
MU = 1.25663706127e-6
EPS = 1 / (MU * C**2)
LIMITS = {"frequency_hz": 1e-4, "r_over_q_accelerator_ohm": .005,
          "geometry_factor_ohm": .005}


def probe_points(case):
    z = np.repeat(np.array([.17, .39, .61, .83])*case.length, 3)
    radius = np.interp(z, *np.asarray(case.profile).T)
    return np.column_stack((radius*np.tile([.2, .5, .8], 4), z))


def reference(case, maxh, order=3, probes=None):
    """Solve r[(h_r+h/r)(v_r+v/r)+h_z*v_z] = k²*r*h*v.

    h=Hphi vanishes on the axis; PEC is natural. Netgen meshes the polygon
    independently. Axis Ez uses the regular limit 2*dHphi/dr/(omega*epsilon).
    Volume and wall integrals use NGSolve; voltage uses independent Gauss
    quadrature on its axis edges, evaluating the volume gradient trace.
    """
    if (case.geometry_type not in ("profile", "contour") or case.z_min != "pec"
            or case.z_max != "pec" or case.modes != 1):
        raise ValueError("reference requires a profile/contour, two PEC ends and modes=1")
    if case.contour is not None and any(tag not in ('axis','pec') for tag in case.contour.edge_tags):
        raise ValueError('reference requires full PEC contour walls')
    if probes is None:
        if case.contour is not None:
            raise ValueError('contour reference requires explicit interior probes')
        probes = probe_points(case)
    probes = np.asarray(probes,dtype=float)
    if probes.ndim != 2 or probes.shape[1] != 2 or not len(probes) or not np.all(np.isfinite(probes)) or np.any(probes[:,0] <= 0):
        raise ValueError('reference probes require finite positive-radius [r,z] pairs')
    if not np.isfinite(maxh) or maxh <= 0 or type(order) is not int or order < 2:
        raise ValueError("maxh must be positive and order an integer >= 2")
    import ngsolve as ng
    from netgen.geom2d import SplineGeometry

    start = time.perf_counter()
    geo = SplineGeometry()
    if case.contour is None:
        coords = [(0., 0.)] + [(r, z) for z, r in case.profile] + [(0., case.length)]
        tags = ['pec']*(len(coords)-1)+['axis']
    else:
        # Canonical contour is CCW in (z,r), so reverse it for Netgen (r,z).
        indices = list(range(len(case.contour.vertices_zr_m)-1,-1,-1))
        coords = [case.contour.vertices_zr_m[i][::-1] for i in indices]
        tags = [case.contour.edge_tags[(i-1)%len(indices)] for i in indices]
    vertices = [geo.AppendPoint(*point) for point in coords]
    for i in range(len(vertices)):
        geo.Append(["line", vertices[i], vertices[(i+1) % len(vertices)]],
                   bc=tags[i])
    mesh = ng.Mesh(geo.GenerateMesh(maxh=maxh))
    space = ng.H1(mesh, order=order, dirichlet="axis")
    h, v = space.TnT()
    r = ng.x
    a, b = ng.BilinearForm(space, symmetric=True), ng.BilinearForm(space, symmetric=True)
    a += r*((ng.grad(h)[0]+h/r)*(ng.grad(v)[0]+v/r)
            + ng.grad(h)[1]*ng.grad(v)[1])*ng.dx(bonus_intorder=6)
    b += r*h*v*ng.dx(bonus_intorder=6)
    a.Assemble()
    b.Assemble()
    free = np.flatnonzero(list(space.FreeDofs()))

    def sparse(mat):
        rows, cols, values = mat.COO()
        return coo_matrix((values, (rows, cols)), shape=(space.ndof, space.ndof)).tocsr()[free][:, free]

    stiffness, mass = sparse(a.mat), sparse(b.mat)
    values, vectors = eigsh(stiffness, M=mass, k=1, sigma=0, which="LM", tol=1e-11,
                            v0=np.random.default_rng(731).normal(size=len(free)))
    lam, vector = float(values[0]), vectors[:, 0]
    if not np.isfinite(lam) or lam <= 0:
        raise RuntimeError("nonpositive/nonfinite reference eigenvalue")
    kv, mv = stiffness @ vector, mass @ vector
    residual = float(np.linalg.norm(kv-lam*mv)/(np.linalg.norm(kv)+lam*np.linalg.norm(mv)))
    if not np.isfinite(residual) or residual > 1e-7:
        raise RuntimeError("reference eigenpair residual failed")
    field = ng.GridFunction(space)
    field.vec.FV().NumPy()[:] = 0
    field.vec.FV().NumPy()[free] = vector
    omega = C*np.sqrt(lam)
    magnetic = MU*np.pi/2*ng.Integrate(r*field**2, mesh, order=12)
    curl2 = (ng.grad(field)[0]+field/r)**2 + ng.grad(field)[1]**2
    electric = np.pi/(2*omega**2*EPS)*ng.Integrate(r*curl2, mesh, order=12)
    energy = float(electric+magnetic)
    field.vec.data *= np.sqrt(case.normalization_j/energy)
    scale2 = case.normalization_j/energy
    energy *= scale2
    wall_h2 = 2*np.pi*ng.Integrate(r*field**2, mesh, definedon=mesh.Boundaries("pec"), order=12)
    axis_ez = 2*ng.grad(field)[0]/(omega*EPS)
    kb = omega/(case.beta*C)
    # Boundary grad is tangential in NGSolve and would erase the radial
    # derivative on the axis. Evaluate the adjacent volume element instead.
    nodes, weights = np.polynomial.legendre.leggauss(12)
    voltage = 0j
    axis_length = 0.
    for edge in mesh.ngmesh.Elements1D():
        p, q = [mesh.ngmesh[index].p for index in edge.vertices]
        if p[0] != 0 or q[0] != 0:
            continue
        left, right = sorted((p[1], q[1]))
        z = (left+right)/2 + nodes*(right-left)/2
        ez = np.array([axis_ez(mesh(0., float(zi))) for zi in z])
        voltage += (right-left)/2*np.dot(weights, ez*np.exp(1j*kb*z))
        axis_length += right-left
    if not np.isclose(axis_length, case.length, rtol=1e-12, atol=0):
        raise RuntimeError("reference axis edges do not cover the full length")
    real, imag = voltage.real, voltage.imag
    rq = (real**2+imag**2)/(omega*energy)
    result = {"frequency_hz": float(omega/(2*np.pi)),
              "r_over_q_accelerator_ohm": float(rq), "r_over_q_circuit_ohm": float(rq/2),
              "geometry_factor_ohm": float(2*omega*energy/wall_h2),
              "stored_energy_j": energy,
              "energy_balance_relative": float(abs(electric-magnetic)/(electric+magnetic)),
              "relative_eigen_residual": residual,
              "maxh_m": maxh, "order": order, "dofs": space.ndof,
              "elements": mesh.ne, "seconds": time.perf_counter()-start}
    if not all(np.isfinite(value) for value in result.values()):
        raise RuntimeError("nonfinite reference result")
    if result["energy_balance_relative"] > 1e-7:
        raise RuntimeError("independent electric/magnetic energy check failed")
    result["hphi_probes_a_per_m"] = [float(field(mesh(*point))) for point in probes]
    ez = (ng.grad(field)[0]+field/r)/(omega*EPS)
    er = -ng.grad(field)[1]/(omega*EPS)
    result['electric_probes_v_per_m'] = [[float(er(mesh(*point))),float(ez(mesh(*point)))] for point in probes]
    return result


def differences(actual, expected):
    return {key: abs(actual[key]/expected[key]-1) for key in LIMITS}


def acceptance(native, external, analytic=None):
    """Agreement alone cannot pass: each independent mesh sequence must converge."""
    if len(native) < 3 or len(external) < 3:
        raise ValueError("at least three levels per solver are required")
    checks = {"ng_last_refinement": differences(native[-1], native[-2]),
              "reference_last_refinement": differences(external[-1], external[-2]),
              "cross_solver": differences(native[-1], external[-1])}
    if analytic is not None:
        checks["ng_analytic"] = differences(native[-1], analytic)
        checks["reference_analytic"] = differences(external[-1], analytic)
    passed = all(np.isfinite(value) and value <= LIMITS[key]
                 for row in checks.values() for key, value in row.items())
    a, b = (np.asarray(rows[-1]["hphi_probes_a_per_m"]) for rows in (native, external))
    field_error = float(min(np.linalg.norm(a-b), np.linalg.norm(a+b))/np.linalg.norm(b))
    passed = passed and np.isfinite(field_error) and field_error <= .005
    return {"passed": bool(passed), "relative_differences": checks,
            "hphi_probe_relative_l2": field_error, "hphi_probe_limit": .005}


def fingerprints():
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for folder in ("src", "scripts", "tests", "examples")
            for path in sorted((ROOT/folder).rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--levels", nargs="+", type=int, default=[32, 64, 128])
    parser.add_argument("--reference-sizes", nargs="+", type=float, default=[.012, .006, .003])
    args = parser.parse_args()
    if (len(args.levels) < 3 or any(n < 2 for n in args.levels)
            or any(a >= b for a, b in zip(args.levels, args.levels[1:]))
            or len(args.reference_sizes) < 3
            or any(not np.isfinite(h) or h <= 0 for h in args.reference_sizes)
            or any(a <= b for a, b in zip(args.reference_sizes, args.reference_sizes[1:]))):
        parser.error("use >=3 strictly increasing NG levels and decreasing positive reference sizes")
    try:
        import ngsolve
    except ImportError as exc:
        parser.error(f"optional NGSolve environment required (docs/INDEPENDENT_COMPARISON.md): {exc}")
    args.out.mkdir(parents=True, exist_ok=False)
    before = fingerprints()
    report = {"passed": False, "scope": "two synthetic vacuum closed PEC fundamental m=0 TM modes",
              "limits_relative": LIMITS, "source_sha256": before,
              "environment": {"python": platform.python_version(), "platform": platform.platform(),
                              **{name: importlib.metadata.version(name) for name in
                                 ("ngsolve", "netgen-mesher", "numpy", "scipy")}},
              "conventions": "SI; peak phasors; exp(+i omega t); U=1 J; R/Q=|V|^2/(omega U)",
              "not_verified": ["surface peaks", "measured structures", "legacy input compatibility",
                               "higher modes", "fully independent linear algebra"], "cases": {}}
    cases = {"pillbox": Case(((0., .08), (.12, .08)), modes=1),
             "frustum": Case(((0., .08), (.12, .10)), modes=1)}
    try:
        for name, base in cases.items():
            entry = {"input": base.to_dict(), "probe_points_rz_m": probe_points(base).tolist(),
                     "ng": [], "ngsolve": []}
            report["cases"][name] = entry
            for n in args.levels:
                case = replace(base, nr=n, nz=2*n)
                start = time.perf_counter()
                solution = solve(case)
                row = quantities(case, solution)
                row.update(nr=n, nz=2*n, dofs=len(solution.mesh.points), seconds=time.perf_counter()-start)
                sampler = FieldSampler(solution.mesh.points, solution.mesh.triangles,
                                       solution.u, solution.frequencies_hz)
                row["hphi_probes_a_per_m"] = sampler.evaluate(probe_points(case))["Hphi_A_per_m"].tolist()
                entry["ng"].append(row)
                print(f"{name} NG {n}: f={row['frequency_hz']:.9g} R/Q={row['r_over_q_accelerator_ohm']:.9g}", flush=True)
            for size in args.reference_sizes:
                row = reference(base, size)
                entry["ngsolve"].append(row)
                print(f"{name} NGSolve {size}: f={row['frequency_hz']:.9g} R/Q={row['r_over_q_accelerator_ohm']:.9g}", flush=True)
            analytic = pillbox_tm010(.08, .12) if name == "pillbox" else None
            entry["acceptance"] = acceptance(entry["ng"], entry["ngsolve"], analytic)
            if analytic is not None:
                entry["analytic"] = analytic
        report["source_changed_during_run"] = fingerprints() != before
        report["passed"] = (not report["source_changed_during_run"]
                            and all(row["acceptance"]["passed"] for row in report["cases"].values()))
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        (args.out/"comparison.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    print(f"{'PASS' if report['passed'] else 'FAIL'}: {args.out}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
