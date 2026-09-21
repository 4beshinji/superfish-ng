# SPDX-License-Identifier: Apache-2.0
"""Explicit nonuniform straight-vacuum shape laws for Hphi tuning version 2."""
from dataclasses import replace
import numpy as np
from .axis_hphi import AxisHphiCase, AxisAccelerationPath
from .coaxial import CoaxialCase, _numeric_coordinates
from .config import keys, positive
from .hphi_mesh import HphiMeshCase
from .hphi_geometry_mapping import HphiGeometryMapping, coaxial_dimension_mapping


DIMENSIONS = ('inner_radius_m', 'outer_radius_m', 'length_m')


def tune_scope(request):
    return 'vacuum_uniform_scale' if request['schema_version'] == 1 else request['mapping']['kind']


def tune_parameter_unit(request):
    return 'm' if tune_scope(request) == 'coaxial_dimensions' else 'dimensionless'


def validate_shape_law(request, project):
    law = request['mapping']
    if not isinstance(law, dict):
        raise ValueError('Hphi tune v2 mapping must be an explicit shape-law object')
    if law.get('kind') == 'coaxial_dimensions':
        keys(law, ['kind'], ['kind'], 'Hphi coaxial shape law')
        if type(project.case) is not CoaxialCase or request['parameter'] not in DIMENSIONS:
            raise ValueError('coaxial_dimensions requires CoaxialCase and inner_radius_m, outer_radius_m or length_m')
    elif law.get('kind') == 'general_piecewise_affine':
        names = ['kind', 'reference_value', 'displacements_rz_m', 'acceleration_policy']
        keys(law, names, names, 'Hphi piecewise affine shape law')
        if type(project.case) not in (HphiMeshCase, AxisHphiCase) or request['parameter'] != 'deformation':
            raise ValueError('general_piecewise_affine requires an explicit straight mesh and dimensionless deformation parameter')
        positive(law['reference_value'], 'Hphi shape reference_value')
        displacement = _numeric_coordinates(law['displacements_rz_m'], 2, 'Hphi shape displacements_rz_m')
        if displacement.shape != project.case.mesh.points_rz_m.shape:
            raise ValueError('Hphi shape law requires one explicit displacement per original mesh vertex')
        if law['acceleration_policy'] != 'transport_on_axis':
            raise ValueError('Hphi shape acceleration_policy must explicitly be transport_on_axis; no inferred or fixed path')
        if type(project.case) is AxisHphiCase and np.any(displacement[project.case.mesh.axis_nodes, 0] != 0):
            raise ValueError('Hphi shape law cannot move an axis vertex radially')
    else:
        raise ValueError('Hphi tune v2 supports coaxial_dimensions or general_piecewise_affine only')


def _boundary_cycles(mesh):
    """Retain every original boundary node as an explicit control corner.

    This allows a declared displacement to bend a previously straight boundary
    at any original boundary node. No snapping or inferred interpolation occurs.
    """
    cycles = []
    lookup = {tuple(point): i for i, point in enumerate(mesh.points_rz_m)}
    for component, contour in enumerate((mesh.outer_rz_m, *mesh.holes_rz_m)):
        successors = dict(mesh.boundary_edges[mesh.boundary_components == component].tolist())
        start = lookup[tuple(contour[0])]
        cycle = [start]
        current = successors[start]
        while current != start:
            cycle.append(current)
            current = successors[current]
        cycles.append(cycle)
    return cycles


def shape_project(project, request, value):
    """Generate unrefined geometry from the original Project and explicit law."""
    law = request['mapping']
    if law['kind'] == 'coaxial_dimensions':
        return replace(project, case=replace(project.case, **{request['parameter']: value}))
    case = project.case
    mesh = case.mesh
    cycles = _boundary_cycles(mesh)
    points = mesh.points_rz_m + (value-law['reference_value'])*np.asarray(law['displacements_rz_m'])
    old = type(mesh)(mesh.points_rz_m[cycles[0]], [mesh.points_rz_m[c] for c in cycles[1:]],
                     mesh.points_rz_m, mesh.triangles)
    new = type(mesh)(points[cycles[0]], [points[c] for c in cycles[1:]], points, mesh.triangles)
    mapping = HphiGeometryMapping(old, new)
    changes = dict(mesh=new)
    if type(case) is AxisHphiCase and case.acceleration is not None:
        path = case.acceleration
        start, end, origin = mapping.transport_axis_coordinates([path.z_start_m, path.z_end_m, path.phase_origin_m])
        changes['acceleration'] = AxisAccelerationPath(float(start), float(end), path.beta, float(origin))
    return replace(project, case=replace(case, **changes))


def shape_comparison_mapping(request, previous_project, current_project):
    """The caller supplies unrefined trials, even for a final refined solution."""
    if request['mapping']['kind'] == 'coaxial_dimensions':
        return coaxial_dimension_mapping(previous_project.case, current_project.case)
    return HphiGeometryMapping(previous_project.case.mesh, current_project.case.mesh)
