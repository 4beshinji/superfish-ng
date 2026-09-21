# SPDX-License-Identifier: Apache-2.0
"""Explicit straight Hphi geometry maps; no field transport or mode matching."""
from dataclasses import dataclass
import numpy as np
from .axis_connected_mesh import AxisConnectedMesh
from .coaxial import CoaxialCase, _numeric_coordinates
from .meridional_mesh import MeridionalMesh


@dataclass(frozen=True)
class HphiGeometryMapping:
    """Paired control triangulations, sharing explicit vertex/cell numbering.

    These are geometry partitions, not necessarily either solution's FEM mesh.
    Boundary component and segment numbers declare the correspondence.
    """
    previous: object
    current: object

    def __post_init__(self):
        allowed = (MeridionalMesh, AxisConnectedMesh)
        if type(self.previous) not in allowed or type(self.current) is not type(self.previous):
            raise ValueError('mapping requires two meshes of the same straight vacuum/axis type')
        meshes = [type(m).from_dict(m.to_dict()) for m in (self.previous, self.current)]
        a, b = meshes
        for name in ('triangles', 'boundary_edges', 'boundary_components', 'boundary_segments'):
            if not np.array_equal(getattr(a, name), getattr(b, name)):
                raise ValueError(f'explicit geometry correspondence must preserve {name}; no automatic matching')
        if len(a.points_rz_m) != len(b.points_rz_m) or len(a.holes_rz_m) != len(b.holes_rz_m):
            raise ValueError('geometry correspondence must preserve vertices and all PEC holes')
        if isinstance(a, AxisConnectedMesh) and not np.array_equal(a.axis_nodes, b.axis_nodes):
            raise ValueError('geometry correspondence must preserve every axis vertex and its order')
        object.__setattr__(self, 'previous', a)
        object.__setattr__(self, 'current', b)
        # Mesh validation proves coverage and orientation on each side. Also
        # reject numerically unresolved derivatives of their composition.
        jac = self.jacobians
        det = np.linalg.det(jac)
        if not np.isfinite(jac).all() or not np.isfinite(det).all() or np.any(det <= 0):
            raise ValueError('geometry mapping requires finite resolved positive Jacobians')

    @property
    def jacobians(self):
        edges = []
        for mesh in (self.previous, self.current):
            vertices = mesh.points_rz_m[mesh.triangles]
            edges.append(np.stack((vertices[:, 1]-vertices[:, 0], vertices[:, 2]-vertices[:, 0]), axis=-1))
        return np.linalg.solve(edges[0].transpose(0, 2, 1), edges[1].transpose(0, 2, 1)).transpose(0, 2, 1)

    def inverse(self):
        return HphiGeometryMapping(self.current, self.previous)

    def map_in_cells(self, cells, barycentric):
        """Map declared parent-cell barycentric points, without point-location guesses."""
        raw = np.asarray(cells, dtype=object)
        if raw.ndim != 1 or any(type(v) is bool or not isinstance(v, (int, np.integer)) for v in raw):
            raise ValueError('mapping cells must be integer indices')
        if any(v < 0 or v >= len(self.previous.triangles) for v in raw):
            raise ValueError('mapping cell index out of range')
        bary = _numeric_coordinates(barycentric, 3, 'mapping barycentric coordinates')
        if len(bary) != len(raw) or np.any(bary < 0) or np.any(bary > 1) or not np.allclose(bary.sum(axis=1), 1., rtol=0, atol=8*np.finfo(float).eps):
            raise ValueError('mapping requires one unit-sum nonnegative barycentric triple per cell')
        return np.einsum('ti,tij->tj', bary, self.current.points_rz_m[self.current.triangles[raw.astype(int)]])

    def transport_axis_coordinates(self, coordinates_m):
        """Transport explicit acceleration endpoints/origin on the vacuum axis.

        No extrapolation, inferred path, beta change or RF evaluation is made.
        Callers must explicitly choose this policy for all acceleration coordinates.
        """
        if not isinstance(self.previous, AxisConnectedMesh):
            raise ValueError('acceleration coordinate transport requires an axis-connected map')
        values = _numeric_coordinates([[v] for v in coordinates_m], 1, 'axis coordinates')[:, 0]
        a = self.previous.points_rz_m[self.previous.axis_nodes, 1]
        b = self.current.points_rz_m[self.current.axis_nodes, 1]
        if np.any(values < a[0]) or np.any(values > a[-1]):
            raise ValueError('acceleration coordinates must lie in the declared vacuum axis interval; extrapolation is unsupported')
        return np.interp(values, a, b)


def coaxial_dimension_mapping(previous, current):
    """Map inner/outer radii and length separately on a two-triangle partition.

    r' = a' + (r-a)(b'-a')/(b-a), z' = z L'/L.
    The control partition is independent of the FEM discretization settings.
    """
    meshes = []
    for case in (previous, current):
        if type(case) is not CoaxialCase:
            raise ValueError('coaxial dimension mapping requires CoaxialCase inputs')
        case = CoaxialCase.from_dict(case.to_dict())
        a, b, length = case.inner_radius_m, case.outer_radius_m, case.length_m
        points = [[a, 0.], [b, 0.], [b, length], [a, length]]
        meshes.append(MeridionalMesh(points, [], points, [[0, 1, 2], [0, 2, 3]]))
    return HphiGeometryMapping(*meshes)
