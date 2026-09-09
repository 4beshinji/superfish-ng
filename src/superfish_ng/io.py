# SPDX-License-Identifier: Apache-2.0
"""Portable JSON, NPZ, CSV, legacy ASCII VTK; no viewer required to solve."""
import csv
import hashlib
import json
import platform
import os
import tempfile
from pathlib import Path
import numpy as np
import scipy
from . import __version__
from .constants import EPS0, TAU
from .rf import cell_fields, quantities


def write_vtk(path, solution, mode):
    """2D meridian embedded at x=r,y=z,z=0. Cylindrical components are scalars."""
    from .display import display_fields
    points, triangles, nodal_h, (er, ez, h) = display_fields(solution, mode)
    title = 'Superfish-NG meridian x=r y=z; peak phasors'
    if getattr(solution, 'element_order', 1) == 2:
        title += '; P2 sampled on four display triangles per element'
    with Path(path).open("w", encoding="ascii") as f:
        f.write(f"# vtk DataFile Version 3.0\n{title}\nASCII\nDATASET UNSTRUCTURED_GRID\n")
        f.write(f"POINTS {len(points)} double\n")
        np.savetxt(f, np.column_stack((points, np.zeros(len(points)))), fmt="%.16e")
        f.write(f"CELLS {len(triangles)} {len(triangles)*4}\n")
        np.savetxt(f, np.column_stack((np.full(len(triangles), 3), triangles)), fmt="%d")
        f.write(f"CELL_TYPES {len(triangles)}\n")
        np.savetxt(f, np.full(len(triangles), 5), fmt="%d")
        f.write(f"POINT_DATA {len(points)}\nSCALARS Hphi_A_per_m double 1\nLOOKUP_TABLE default\n")
        np.savetxt(f, nodal_h, fmt="%.16e")
        f.write(f"CELL_DATA {len(triangles)}\n")
        for name, values in (("Er_quadrature_V_per_m", er), ("Ez_quadrature_V_per_m", ez),
                             ("E_abs_V_per_m", np.hypot(er, ez)), ("Hphi_center_A_per_m", h)):
            f.write(f"SCALARS {name} double 1\nLOOKUP_TABLE default\n")
            np.savetxt(f, values, fmt="%.16e")


def save_run(case, solution, directory):
    """Publish readiness after writing all files; never replace an existing path."""
    from .curved_solution import CurvedSolution
    if isinstance(solution, CurvedSolution):
        from dataclasses import replace
        expected_case = (case if case.geometry_order == 2 else
                         replace(case, geometry_order=2, quadrature_order=solution.quadrature_order))
        if expected_case != solution.case:
            raise ValueError('case and curved solution disagree')
        case = solution.case
    elif case.geometry_order == 2:
        raise ValueError('geometry_order=2 requires a curved solution')
    if getattr(solution, 'element_order', 1) not in (1, 2):
        raise ValueError('unsupported field element order')
    if solution.element_order != case.element_order:
        if solution.element_order == 2 and case.element_order == 1:
            from dataclasses import replace
            case = replace(case, element_order=2)
        else:
            raise ValueError('case and solution element orders disagree')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    from .completion import digest, required_files
    with (directory/'save_protocol.json').open('x', encoding='utf-8') as stream:
        stream.write('{"version":1}\n')
    with tempfile.TemporaryDirectory(prefix='.save-staging-', dir=directory) as temporary:
        staging = Path(temporary)
        result = _write_run(case, solution, staging)
        for path in sorted(staging.iterdir()):
            os.link(path, directory/path.name)
        files = {name: digest(directory/name) for name in sorted(required_files(case, result))}
        marker = staging/'save_complete.json'
        marker.write_text(json.dumps({'completion_version': 1, 'files': files}, indent=2)+'\n', encoding='utf-8')
        os.link(marker, directory/marker.name)  # Atomic no-replace publication point.
    return result


def _write_run(case, solution, directory):
    from .curved_solution import CurvedSolution
    if isinstance(solution, CurvedSolution):
        from .curved_saved import write_curved_run
        return write_curved_run(case, solution, directory)
    canonical = json.dumps(case.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False)
    result = {"schema_version": 1, "save_protocol_version": 1, "software_version": __version__,
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
    if case.curved_contour is not None:
        approximation = case.curved_contour.linearize(case.curve_chord_tolerance_m,max_segments=case.curve_chord_max_segments,segments_per_curve=case.curve_segments_per_curve)
        result['geometry_approximation'] = dict(
            representation='straight chords of analytic primitives',geometry_order=1,
            tolerance_m=approximation.tolerance_m,
            primitive_chord_tolerance_m=approximation.primitive_chord_tolerance_m,
            endpoint_adjustments_m=list(approximation.endpoint_adjustments_m),
            segment_curve_indices=list(approximation.segment_curve_indices),
            segment_parameter_intervals=[list(p) for p in approximation.segment_parameter_intervals],
            analytic_area_m2=approximation.analytic_area_m2,
            analytic_volume_m3=case.curved_contour.volume_m3,
            chord_volume_m3=approximation.contour.volume_m3,
            volume_difference_m3=approximation.contour.volume_m3-case.curved_contour.volume_m3,
            chord_area_m2=approximation.contour.area_m2,
            area_difference_m2=approximation.area_difference_m2)
    if solution.element_order == 2:
        result['field_space'] = {'element_order': 2, 'basis': 'quadratic Lagrange u=Hphi/r',
                                 'geometry_order': 1, 'dofs': len(solution.u)}
    if solution.source_case is not None:
        result['reflection_source_case'] = solution.source_case
        if solution.element_order == 2:
            from dataclasses import replace
            from .config import Case
            source = Case.from_dict(solution.source_case)
            result['reflection_source_case'] = replace(source, element_order=2).to_dict()
    if case.has_acceleration_overrides:
        result['conventions'].update(
            voltage='integral over voltage_interval_m of Ez_quadrature(0,z) exp(+i omega (z-phase_origin_m)/(beta c)) dz; global -i omitted',
            domain='energy and wall loss cover the full input domain; accelerating voltage uses its specified interval; Eacc uses active_length_m; symmetry planes have no wall loss')
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
    extra = {}
    if solution.element_order == 2:
        extra = {name: getattr(solution.space, name) for name in
                 ('dof_points', 'cell_dofs', 'boundary_dofs', 'axis_dofs')}
    np.savez_compressed(directory/"fields.npz", points_rz_m=mesh.points, triangles=mesh.triangles,
                        boundary_edges=mesh.boundary_edges, boundary_tags=mesh.boundary_tags,
                        boundary_cells=mesh.boundary_cells, axis_nodes=mesh.axis_nodes,
                        u_a_per_m2=solution.u, frequencies_hz=solution.frequencies_hz, **extra)
    for i in range(case.modes):
        write_vtk(directory/f"mode_{i+1:03d}.vtk", solution, i)
        axis = mesh.axis_nodes if solution.element_order == 1 else solution.space.axis_dofs
        points = mesh.points if solution.element_order == 1 else solution.space.dof_points
        z = points[axis, 1]
        ez = 2*solution.u[axis, i]/(TAU*solution.frequencies_hz[i]*EPS0)
        np.savetxt(directory/f"axis_{i+1:03d}.csv", np.column_stack((z, ez)), delimiter=",",
                   header="z_m,Ez_quadrature_V_per_m", comments="")
    with (directory/"modes.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(result["modes"][0]))
        writer.writeheader()
        writer.writerows(result["modes"])
    return result
