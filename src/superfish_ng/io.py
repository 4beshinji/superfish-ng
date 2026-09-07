# SPDX-License-Identifier: Apache-2.0
"""Portable JSON, NPZ, CSV, legacy ASCII VTK; no viewer required to solve."""
import csv
import hashlib
import json
import platform
from pathlib import Path
import numpy as np
import scipy
from . import __version__
from .constants import EPS0, TAU
from .rf import cell_fields, quantities


def write_vtk(path, solution, mode):
    """2D meridian embedded at x=r,y=z,z=0. Cylindrical components are scalars."""
    mesh = solution.mesh
    er, ez, h = cell_fields(solution, mode)
    with Path(path).open("w", encoding="ascii") as f:
        f.write("# vtk DataFile Version 3.0\nSuperfish-NG meridian x=r y=z; peak phasors\nASCII\nDATASET UNSTRUCTURED_GRID\n")
        f.write(f"POINTS {len(mesh.points)} double\n")
        np.savetxt(f, np.column_stack((mesh.points, np.zeros(len(mesh.points)))), fmt="%.16e")
        f.write(f"CELLS {len(mesh.triangles)} {len(mesh.triangles)*4}\n")
        np.savetxt(f, np.column_stack((np.full(len(mesh.triangles), 3), mesh.triangles)), fmt="%d")
        f.write(f"CELL_TYPES {len(mesh.triangles)}\n")
        np.savetxt(f, np.full(len(mesh.triangles), 5), fmt="%d")
        f.write(f"POINT_DATA {len(mesh.points)}\nSCALARS Hphi_A_per_m double 1\nLOOKUP_TABLE default\n")
        np.savetxt(f, mesh.points[:, 0]*solution.u[:, mode], fmt="%.16e")
        f.write(f"CELL_DATA {len(mesh.triangles)}\n")
        for name, values in (("Er_quadrature_V_per_m", er), ("Ez_quadrature_V_per_m", ez),
                             ("E_abs_V_per_m", np.hypot(er, ez)), ("Hphi_center_A_per_m", h)):
            f.write(f"SCALARS {name} double 1\nLOOKUP_TABLE default\n")
            np.savetxt(f, values, fmt="%.16e")


def save_run(case, solution, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    canonical = json.dumps(case.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False)
    result = {"schema_version": 1, "software_version": __version__,
              "case_sha256": hashlib.sha256(canonical.encode()).hexdigest(), "case": case.to_dict(),
              "environment": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__, "platform": platform.platform()},
              "mesh": {"nodes": len(solution.mesh.points), "triangles": len(solution.mesh.triangles)},
              "mass_orthogonality_error": solution.orthogonality_error,
              "field_construction": solution.construction,
              "scope": "vacuum; closed PEC cavity or explicit symmetry subdomain; axis-connected; m=0 TM only; perturbative normal-conductor loss",
              "conventions": {"phasor": "exp(+i omega t); H real, E=-i*exported_quadrature",
                              "energy": "U=1/4 integral(eps|E|^2+mu|H|^2)dV",
                              "domain": "all RF integrals cover the input domain only; symmetry planes have no wall loss; no automatic volume or voltage doubling",
                              "rq_accelerator": "|Vacc|^2/(omega U)", "rq_circuit": "|Vacc|^2/(2 omega U)",
                              "voltage": "integral Ez_quadrature(0,z) exp(+i omega z/(beta c)) dz; global -i omitted",
                              "vtk_coordinates": "x=r, y=z, z=0; scalar cylindrical components"},
              "modes": [quantities(case, solution, i) for i in range(case.modes)]}
    if solution.source_case is not None:
        result['reflection_source_case'] = solution.source_case
    if solution.mesh_input is not None:
        from .mesh_input import mesh_digest
        result['mesh'].update(source='external tagged mesh', input_file='mesh.json',
                              input_sha256=mesh_digest(solution.mesh_input),
                              generation_parameters_applied=False)
        (directory/'mesh.json').write_text(json.dumps(solution.mesh_input, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    if case.geometry_type == 'arc_profile':
        from .geometry import linearize_profile
        polygon = linearize_profile(case)
        result['geometry_approximation'] = {
            'method': 'straight chords of specified circular minor arcs; original vertices/radii remain in case',
            'maximum_arc_sagitta_m': case.arc_chord_tolerance_m,
            'linearized_wall_vertices': len(polygon),
            'near_duplicate_coordinate_tolerance_m': 32*np.finfo(float).eps*max(r for _, r in polygon)}
    (directory/"case.json").write_text(json.dumps(case.to_dict(), indent=2)+"\n", encoding="utf-8")
    (directory/"results.json").write_text(json.dumps(result, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    mesh = solution.mesh
    np.savez_compressed(directory/"fields.npz", points_rz_m=mesh.points, triangles=mesh.triangles,
                        boundary_edges=mesh.boundary_edges, boundary_tags=mesh.boundary_tags,
                        boundary_cells=mesh.boundary_cells, axis_nodes=mesh.axis_nodes,
                        u_a_per_m2=solution.u, frequencies_hz=solution.frequencies_hz)
    for i in range(case.modes):
        write_vtk(directory/f"mode_{i+1:03d}.vtk", solution, i)
        z = mesh.points[mesh.axis_nodes, 1]
        ez = 2*solution.u[mesh.axis_nodes, i]/(TAU*solution.frequencies_hz[i]*EPS0)
        np.savetxt(directory/f"axis_{i+1:03d}.csv", np.column_stack((z, ez)), delimiter=",",
                   header="z_m,Ez_quadrature_V_per_m", comments="")
    with (directory/"modes.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(result["modes"][0]))
        writer.writeheader()
        writer.writerows(result["modes"])
    return result
