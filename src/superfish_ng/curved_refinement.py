# SPDX-License-Identifier: Apache-2.0
"""Uniform subdivision of validated quadratic geometry without curve reprojection."""
from dataclasses import dataclass
from types import MappingProxyType
import numpy as np
from scipy.sparse import coo_matrix
from .quadratic_geometry import QuadraticTriangle
from .quadratic_boundary import check_quadratic_boundary
from .curved_space import CurvedSpace, check_curved_edges

_REFERENCE = np.array([[0., 0.], [1., 0.], [0., 1.], [.5, 0.], [.5, .5], [0., .5]])
_CHILDREN = np.array([[0, 3, 5], [3, 1, 4], [5, 4, 2], [3, 4, 5]])


@dataclass(frozen=True)
class RestrictedGeometry:
    points_rz_m: np.ndarray
    cell_nodes: np.ndarray
    boundary_nodes: np.ndarray
    boundary_curve_indices: np.ndarray
    boundary_parameters: np.ndarray
    local_maps: tuple
    boundary_check: object


@dataclass(frozen=True)
class CurvedRefinement:
    space: CurvedSpace
    prolongation: object
    parent_cells: np.ndarray
    parent_reference_vertices: np.ndarray


def refine_curved_space(parent):
    """Split every reference triangle into four, retaining the same physical map.

    The sparse prolongation maps parent u coefficients to the identical field
    in the refined P2 space. Shared nodes are keyed by topology, never rounded
    physical coordinates. Boundary curve intervals record ancestry only: new
    points lie on the parent's quadratic edge, not on its analytic primitive.
    This space-level API does not yet participate in native solve/save/Study.
    """
    if not isinstance(parent, CurvedSpace):
        raise ValueError('curved refinement requires a validated CurvedSpace')
    geometry = parent.geometry
    points = list(geometry.points_rz_m.copy())
    coefficients = [{i: 1.} for i in range(len(points))]
    midpoints = {}
    cells, owners, reference_vertices = [], [], []
    scale = float(np.max(np.ptp(geometry.points_rz_m, axis=0)))
    tolerance = 512*np.finfo(float).eps*scale
    for cell, (nodes, mapping) in enumerate(zip(geometry.cell_nodes, geometry.local_maps)):
        for child in _CHILDREN:
            vertices = nodes[child]
            mids = []
            for a, b in ((0, 1), (1, 2), (2, 0)):
                key = tuple(sorted((int(vertices[a]), int(vertices[b]))))
                reference = (_REFERENCE[child[a]]+_REFERENCE[child[b]])/2
                evaluated = mapping.evaluate([reference])
                proposal = evaluated['points_rz_m'][0]
                row = {int(n): float(v) for n, v in zip(nodes, evaluated['basis_values'][0]) if v != 0}
                if key in midpoints:
                    index = midpoints[key]
                    if (np.linalg.norm(points[index]-proposal) > tolerance
                            or coefficients[index] != row):
                        raise ValueError('inconsistent shared refinement geometry or prolongation')
                else:
                    index = len(points)
                    midpoints[key] = index
                    points.append(proposal)
                    coefficients.append(row)
                mids.append(index)
            cells.append([*vertices, *mids])
            owners.append(cell)
            reference_vertices.append(_REFERENCE[child])
    boundary, parameters = [], []
    for (a, b, mid), (lo, hi) in zip(geometry.boundary_nodes, geometry.boundary_parameters):
        boundary.extend([[a, mid, midpoints[tuple(sorted((int(a), int(mid))))]],
                         [mid, b, midpoints[tuple(sorted((int(mid), int(b))))]]])
        centre = (lo+hi)/2
        parameters.extend([[lo, centre], [centre, hi]])
    points, cells, boundary = np.asarray(points), np.asarray(cells), np.asarray(boundary)
    maps = tuple(QuadraticTriangle(points[nodes]) for nodes in cells)
    boundary_check = MappingProxyType(check_quadratic_boundary(points, boundary))
    edge_check = MappingProxyType(check_curved_edges(points, cells, boundary))
    tags = np.repeat(parent.boundary_tags, 2)
    curve_indices = np.repeat(geometry.boundary_curve_indices, 2)
    parameters = np.asarray(parameters)
    axis = np.unique(boundary[tags == 'axis'])
    axis = axis[np.argsort(points[axis, 1])]
    constrained = np.unique(boundary[tags == 'magnetic_symmetry'])
    owners, reference_vertices = np.asarray(owners), np.asarray(reference_vertices)
    for array in (points, cells, boundary, tags, curve_indices, parameters, axis,
                  constrained, owners, reference_vertices):
        array.setflags(write=False)
    restricted = RestrictedGeometry(points, cells, boundary, curve_indices, parameters, maps, boundary_check)
    space = CurvedSpace(restricted, tags, axis, constrained, edge_check)
    rows, columns, values = [], [], []
    for i, row in enumerate(coefficients):
        for j, value in row.items():
            rows.append(i); columns.append(j); values.append(value)
    prolongation = coo_matrix((values, (rows, columns)),
                             shape=(len(points), len(geometry.points_rz_m))).tocsr()
    return CurvedRefinement(space, prolongation, owners, reference_vertices)
