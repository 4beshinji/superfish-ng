# SPDX-License-Identifier: Apache-2.0
"""Strict tagged triangle interchange for the existing axis-connected TM domain."""
from dataclasses import replace
import hashlib
import json

import numpy as np

from .config import keys
from .mesh import Mesh, element_geometry, validate_profile_mesh


def mesh_to_dict(mesh):
    return {'schema_version': 1, 'length_unit': 'm', 'coordinate_order': 'rz',
            'index_base': 0, 'points': mesh.points.tolist(),
            'triangles': mesh.triangles.tolist(),
            'boundary_edges': mesh.boundary_edges.tolist(),
            'boundary_tags': mesh.boundary_tags.tolist()}


def mesh_digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def mesh_from_dict(case, data):
    """Validate geometry and topology before deriving incidence and ordered axis.

    Tags are mandatory, including all PEC edges. Only the Case's prescribed
    polygon is accepted; importing a mesh does not extend the physics scope.
    Positive, consistently oriented triangles form a connected topological disk
    with a single simple prescribed boundary. No reorientation or tag inference.
    """
    required = ('schema_version', 'length_unit', 'coordinate_order', 'index_base',
                'points', 'triangles', 'boundary_edges', 'boundary_tags')
    keys(data, required, required, 'mesh input')
    if type(data['schema_version']) is not int or data['schema_version'] != 1:
        raise ValueError('mesh schema_version must be 1')
    if data['length_unit'] != 'm' or data['coordinate_order'] != 'rz':
        raise ValueError('mesh requires length_unit=m and coordinate_order=rz; convert explicitly')
    if type(data['index_base']) is not int or data['index_base'] != 0:
        raise ValueError('mesh index_base must be integer 0')

    def array(name, width, indices=False):
        rows = data[name]
        if not isinstance(rows, list) or not rows:
            raise ValueError(f'mesh {name} must be a nonempty array')
        for row in rows:
            if not isinstance(row, list) or len(row) != width:
                raise ValueError(f'mesh {name} requires rows of length {width}')
            for value in row:
                if indices:
                    if type(value) is not int or not 0 <= value < len(data['points']):
                        raise ValueError(f'mesh {name} indices must be integers within points')
                elif type(value) not in (int, float) or not np.isfinite(value):
                    raise ValueError(f'mesh {name} coordinates must be finite numbers')
        return np.array(rows, dtype=np.int64 if indices else float)

    points = array('points', 2)
    if np.any(points[:, 0] < 0) or len(np.unique(points, axis=0)) != len(points):
        raise ValueError('mesh requires nonnegative radii and unique points')
    triangles, edges = array('triangles', 3, True), array('boundary_edges', 2, True)
    if len(np.unique(triangles)) != len(points):
        raise ValueError('mesh contains unused points')
    if len(np.unique(np.sort(triangles, axis=1), axis=0)) != len(triangles):
        raise ValueError('mesh contains duplicate triangles')
    tags = data['boundary_tags']
    if (not isinstance(tags, list) or len(tags) != len(edges)
            or any(type(tag) is not str or tag not in
                   ('axis', 'pec', 'electric_symmetry', 'magnetic_symmetry') for tag in tags)):
        raise ValueError('mesh boundary_tags must name every edge: axis/pec/electric_symmetry/magnetic_symmetry')
    mesh = Mesh(points, triangles, edges, np.array(tags, dtype='U20'), None, None)
    element_geometry(mesh)
    incidence = {}
    for cell, triangle in enumerate(triangles):
        for a, b in zip(triangle, np.roll(triangle, -1)):
            incidence.setdefault(tuple(sorted((a, b))), []).append((cell, a, b))
    for entries in incidence.values():
        if len(entries) > 2:
            raise ValueError('mesh has a nonmanifold edge')
        if len(entries) == 2 and entries[0][1:] != entries[1][1:][::-1]:
            raise ValueError('mesh triangles have inconsistent shared-edge orientation')
    expected = {edge: entries[0][0] for edge, entries in incidence.items() if len(entries) == 1}
    supplied = [tuple(sorted(edge)) for edge in edges]
    if len(set(supplied)) != len(supplied) or set(supplied) != set(expected):
        raise ValueError('mesh boundary_edges must cover every boundary exactly once and no interior edges')
    mesh.boundary_cells = np.array([expected[edge] for edge in supplied], dtype=np.int64)
    axis_edges = []
    for edge, tag in zip(edges, tags):
        ends = points[edge]
        if np.all(ends[:, 0] == 0):
            expected_tag = 'axis'
            axis_edges.append(edge)
        elif np.all(ends[:, 1] == 0):
            expected_tag = case.z_min
        elif np.all(ends[:, 1] == case.length):
            expected_tag = case.z_max
        else:
            expected_tag = 'pec'
        if tag != expected_tag:
            raise ValueError(f'mesh boundary tag {tag!r} conflicts with case/axis: expected {expected_tag!r}')
    if not axis_edges:
        raise ValueError('mesh requires an axis boundary; inner conductors are unsupported')
    axis = np.unique(axis_edges)
    axis = axis[np.argsort(points[axis, 1])]
    expected_axis = {tuple(sorted(pair)) for pair in zip(axis[:-1], axis[1:])}
    if (points[axis[0], 1] != 0 or points[axis[-1], 1] != case.length
            or set(map(tuple, np.sort(axis_edges, axis=1))) != expected_axis
            or set(axis) != set(np.flatnonzero(points[:, 0] == 0))):
        raise ValueError('mesh axis must be one connected chain covering z=0 to case.length')
    mesh.axis_nodes = axis
    polygon = case
    if case.geometry_type == 'arc_profile':
        from .geometry import linearize_profile
        polygon = replace(case, profile=linearize_profile(case), geometry_type='stepped_profile',
                          arcs=(), arc_chord_tolerance_m=1e-5)
    validate_profile_mesh(polygon, mesh)
    # A connected disk must also have one boundary cycle, not pinched vertices.
    # validate_profile_mesh checks vertex degree two, connectivity, Euler=1,
    # prescribed boundary coverage/perimeter and positive total area.
    return mesh
