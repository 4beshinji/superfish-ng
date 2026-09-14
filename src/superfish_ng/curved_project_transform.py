# SPDX-License-Identifier: Apache-2.0
"""Transport native curves and their source mesh through a declared affine map."""
from dataclasses import replace
import numpy as np
from .affine_conics import transform_curve
from .affine_remesh_tracking import validate_affine_map
from .mesh import make_mesh
from .mesh_input import mesh_from_dict, mesh_to_dict
from .project import Project


def relative_affine_map(previous, current):
    """Return current @ inverse(previous) for maps from the same base cavity."""
    a0, b0, c0 = validate_affine_map(previous)
    a1, b1, c1 = validate_affine_map(current)
    result = dict(radial_scale=a1/a0, axial_scale=c1/c0,
                  axial_shear=(b1-(c1/c0)*b0)/a0)
    validate_affine_map(result)
    return result


def _points(points, a, b, c):
    points = np.asarray(points, dtype=float)
    with np.errstate(over='ignore', invalid='ignore'):
        mapped = np.column_stack((a*points[:, 0], b*points[:, 0]+c*points[:, 1]))
    if not np.isfinite(mapped).all():
        raise ValueError('affine project mesh coordinates exceed finite range')
    return mapped


def _check_spaces(source, target, a, b, c):
    x, y = source.geometry, target.geometry
    for name in ('cell_nodes', 'boundary_nodes', 'boundary_curve_indices'):
        if not np.array_equal(getattr(x, name), getattr(y, name)):
            raise ValueError('affine project UNVERIFIED: refinement changes connectivity; '
                             'use a base or uniform history, or a map preserving each local split')
    expected = _points(x.points_rz_m, a, b, c)
    tolerance = 512*np.finfo(float).eps*float(np.max(np.ptp(expected, axis=0)))
    if (expected.shape != y.points_rz_m.shape
            or np.max(np.abs(expected-y.points_rz_m)) > tolerance
            or not np.allclose(x.boundary_parameters, y.boundary_parameters,
                               rtol=0., atol=512*np.finfo(float).eps)):
        raise ValueError('affine project UNVERIFIED: reconstructed quadratic geometry differs from transported maps')


def transform_curved_project(project, affine_map, *, rf_coordinates):
    """Return a new explicit-mesh Project with preserved native correspondence.

    rf_coordinates is required: 'fixed' retains all effective RF lengths;
    'axial' multiplies them by axial_scale. Physical gap/radius constraints,
    normalization/material data and generator/quality controls stay fixed.
    Chord and join approximation budgets scale by the map's spectral norm.
    Every reconstructed refinement stage must retain connectivity and maps.
    This performs geometry validation, not a solve or a convergence test.
    """
    if not isinstance(project, Project):
        raise ValueError('affine project requires a Project')
    if rf_coordinates not in ('fixed', 'axial'):
        raise ValueError('rf_coordinates must explicitly be fixed or axial')
    # Revalidate mutable nested dictionaries and all portable Project options.
    project = Project.from_dict(project.to_dict())
    case = project.case
    from .te import is_te,validate_te_case
    te=is_te(case)
    if te:
        validate_te_case(case)
        if rf_coordinates!='fixed':raise ValueError('TE affine geometry requires fixed RF metadata')
        if (case.geometry_order!=2 or project.reflect_full or case.curved_contour is None
                or any(t not in ('axis','pec') for t in case.curved_contour.edge_tags)):
            raise ValueError('TE affine geometry requires direct native P2 closed PEC/axis geometry')
    if case.curved_contour is None or project.sections is not None:
        raise ValueError('affine curved project requires native curved_contour without assembled sections')
    a, b, c = validate_affine_map(affine_map)
    matrix = np.array([[a, 0.], [b, c]])
    stretch = float(np.linalg.norm(matrix, ord=2))
    source_mesh = make_mesh(case) if project.mesh_data is None else mesh_from_dict(case, project.mesh_data)
    approximation = case.curved_contour.linearize(case.curve_chord_tolerance_m,
        max_segments=case.curve_chord_max_segments, segments_per_curve=case.curve_segments_per_curve)
    counts = tuple(np.bincount(approximation.segment_curve_indices,
                              minlength=len(case.curved_contour.curves)).tolist())
    contour = replace(case.curved_contour,
        curves=tuple(transform_curve(curve, affine_map) for curve in case.curved_contour.curves),
        join_tolerance_m=case.curved_contour.join_tolerance_m*stretch)
    rf={}
    if not te:
        active, interval, origin = case.acceleration_parameters
        factor = c if rf_coordinates == 'axial' else 1.
        rf=dict(active_length_m=active*factor,voltage_interval_m=tuple(v*factor for v in interval),
            phase_origin_m=None if case.phase_origin_m is None else origin*factor)
    target = replace(case, curved_contour=contour, contour=None,
        curve_chord_tolerance_m=case.curve_chord_tolerance_m*stretch,
        curve_segments_per_curve=counts, **rf)
    data = mesh_to_dict(source_mesh)
    data['points'] = _points(source_mesh.points, a, b, c).tolist()
    result = Project.from_dict(dict(project.to_dict(), case=target.to_dict(),
                                    project_version=2, mesh_data=data))
    if case.geometry_order == 2:
        from .curved_space import case_curved_space
        target_mesh = mesh_from_dict(target, result.mesh_data)
        # Prefix checks prevent a later marked-cell number from referring to a
        # different physical cell even if the final boundary still coincides.
        prefixes = range(len(case.curved_refinement_steps)+1)
        for end in prefixes:
            old_case = replace(case, curved_refinement_steps=case.curved_refinement_steps[:end])
            new_case = replace(target, curved_refinement_steps=target.curved_refinement_steps[:end])
            _check_spaces(case_curved_space(old_case, source_mesh),
                          case_curved_space(new_case, target_mesh), a, b, c)
    return result
