# SPDX-License-Identifier: Apache-2.0
"""Verified continuous piecewise affine maps between planar polygon disks.

The paired comparison triangulations define a globally non-affine map. They
are independent of the two FEM meshes. This geometry API neither solves nor
tracks a mode; smooth nonlinear maps and curved boundaries are unsupported.
"""
from dataclasses import dataclass, field
from fractions import Fraction
import numpy as np
from .config import integer, keys
from .planar_mesh import PlanarMesh
from .planar_tracking_affine_remesh import _boundary_cycle
from .planar_tracking_exact_affine import _corners, exact_affine_polygon_overlay
from .planar_tracking_overlap import PlanarTrackingOverlay, _cross
from .planar_tracking_remesh import _rational_points


def _exact_partition(mesh, budget):
    if not isinstance(mesh, PlanarMesh):
        raise ValueError('piecewise mapping requires two PlanarMesh partitions')
    if len(mesh.triangles) > budget:
        raise ValueError('comparison partition exceeds max_partition_triangles')
    mesh = PlanarMesh.create(mesh.polygon_xy_m, mesh.points_xy_m, mesh.triangles)
    polygon = _rational_points(mesh.polygon_xy_m)
    boundary = _rational_points(_boundary_cycle(mesh))
    if _corners(boundary) != _corners(polygon):
        raise ValueError('comparison boundary must cover the declared polygon exactly')
    points = _rational_points(mesh.points_xy_m)
    # The mesh contract checks edges, manifold links, disk topology and a
    # single boundary cycle. Exact area supplements those checks, not replaces
    # them: an equal-area displaced or overlapping region must still fail.
    area2 = sum((a[0]*b[1]-a[1]*b[0] for a, b in
                 zip(polygon, polygon[1:]+polygon[:1])), Fraction(0))
    if sum((_cross(*(points[int(i)] for i in cell))
            for cell in mesh.triangles), Fraction(0)) != area2:
        raise ValueError('comparison triangles must exactly cover the polygon')
    return mesh


def _binary64(values, label, *, positive=False):
    try:
        result = np.asarray(values, dtype=float)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f'{label} is unresolved in binary64') from exc
    if (not np.isfinite(result).all()
            or any(v != 0 and f == 0 for v, f in zip(np.asarray(values, dtype=object).flat, result.flat))
            or (positive and np.any(result <= 0))):
        raise ValueError(f'{label} is unresolved in binary64')
    result.setflags(write=False)
    return result


def _cell_linear(previous, current):
    """Compute Q*P^-1 exactly, with edge columns in P and Q."""
    a, b, c = previous
    p, q, r = current
    ux, uy = b[0]-a[0], b[1]-a[1]
    vx, vy = c[0]-a[0], c[1]-a[1]
    sx, sy = q[0]-p[0], q[1]-p[1]
    tx, ty = r[0]-p[0], r[1]-p[1]
    det = ux*vy-vx*uy
    return (((sx*vy-tx*uy)/det, (-sx*vx+tx*ux)/det),
            ((sy*vy-ty*uy)/det, (-sy*vx+ty*ux)/det))


@dataclass(frozen=True, eq=False)
class PlanarPiecewiseMapping:
    """F(x)=A_cell*x+t_cell using paired, identically numbered partitions.

    Shared vertices/edges define one continuous map. Both partitions must be
    valid polygon disks with positive cells. Consequently the map is a
    bijection, including the entire boundary. No coordinate fitting occurs.
    xy transport is adj(A_cell), matching the TE scalar-curl convention of
    the existing affine comparison. It is not an eigenfield deformation law.
    """
    previous_partition: PlanarMesh
    current_partition: PlanarMesh
    max_partition_triangles: int = 250000
    max_candidate_tests: int = 2000000
    linear_xy: np.ndarray = field(init=False, repr=False)
    jacobian_determinants: np.ndarray = field(init=False, repr=False)
    current_to_previous_linear: np.ndarray = field(init=False, repr=False)

    def __post_init__(self):
        integer(self.max_partition_triangles, 'max_partition_triangles')
        integer(self.max_candidate_tests, 'max_candidate_tests')
        previous, current = [_exact_partition(mesh, self.max_partition_triangles)
                             for mesh in (self.previous_partition, self.current_partition)]
        if (len(previous.points_xy_m) != len(current.points_xy_m)
                or not np.array_equal(previous.triangles, current.triangles)):
            raise ValueError('piecewise partitions require identical vertex numbering and triangle connectivity')
        matrices, determinants, transports = [], [], []
        points = [_rational_points(mesh.points_xy_m) for mesh in (previous, current)]
        for cell in previous.triangles:
            triangles = [[p[int(i)] for i in cell] for p in points]
            matrix = _cell_linear(*triangles)
            (a, b), (c, d) = matrix
            determinant = a*d-b*c
            if determinant <= 0:
                raise ValueError('piecewise mapping requires positive Jacobians')
            matrices.append(matrix)
            determinants.append(determinant)
            transports.append(((d, -b), (-c, a)))
        linear = _binary64(matrices, 'piecewise linear map')
        transport = _binary64(transports, 'piecewise xy transport')
        for matrices64 in (linear, transport):
            for matrix in matrices64:
                (a, b), (c, d) = [[Fraction(float(v)) for v in row] for row in matrix]
                if a*d-b*c <= 0:
                    raise ValueError('piecewise xy matrix is singular or reversed after binary64 conversion')
        for name, value in (('previous_partition', previous), ('current_partition', current),
                            ('linear_xy', linear), ('current_to_previous_linear', transport),
                            ('jacobian_determinants', _binary64(determinants, 'piecewise Jacobian', positive=True))):
            object.__setattr__(self, name, value)

    def reversed(self):
        """Swap the paired domains and recompute the exact inverse per cell."""
        return type(self)(self.current_partition, self.previous_partition,
                          self.max_partition_triangles, self.max_candidate_tests)

    def map_points(self, points_xy_m, partition_cells):
        """Evaluate declared cells exactly on binary64 points, then round once.

        A point must belong to the specified closed comparison triangle.
        Shared-edge points have the same image from either incident cell.
        This does not search or interpolate either FEM field.
        """
        try:
            raw = np.asarray(points_xy_m, dtype=object)
            indices = np.asarray(partition_cells, dtype=object)
            if raw.ndim != 2 or raw.shape[1] != 2 or indices.shape != (len(raw),):
                raise ValueError('map_points requires xy pairs and one partition cell per point')
            if any(isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, float, np.integer, np.floating)) for v in raw.flat):
                raise ValueError('map_points coordinates must be finite numbers')
            xy = raw.astype(float)
            if not np.isfinite(xy).all():
                raise ValueError('map_points coordinates must be finite numbers')
            if any(isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer))
                   or v < 0 or v >= len(self.linear_xy) for v in indices):
                raise ValueError('map_points partition cell index out of range or not integer')
        except (TypeError, OverflowError) as exc:
            raise ValueError('map_points requires finite xy pairs and integer cell indices') from exc
        old = _rational_points(self.previous_partition.points_xy_m)
        new = _rational_points(self.current_partition.points_xy_m)
        result = []
        for point, ci in zip(_rational_points(xy), indices):
            cell = self.previous_partition.triangles[int(ci)]
            a, b, c = [old[int(i)] for i in cell]
            det = _cross(a, b, c)
            bary = (_cross(point, b, c)/det, _cross(a, point, c)/det,
                    _cross(a, b, point)/det)
            if min(bary) < 0:
                raise ValueError('map_points point is outside its declared comparison cell')
            result.append([sum((v*new[int(i)][k] for v, i in zip(bary, cell)), Fraction(0))
                           for k in (0, 1)])
        return _binary64(result, 'mapped xy coordinates').reshape(-1, 2)

    def to_dict(self):
        return dict(name='planar_piecewise_affine', mapping_version=1,
                    previous_partition=self.previous_partition.to_dict(),
                    current_partition=self.current_partition.to_dict(),
                    max_partition_triangles=self.max_partition_triangles,
                    max_candidate_tests=self.max_candidate_tests)

    @classmethod
    def from_dict(cls, data):
        names = ['name', 'mapping_version', 'previous_partition', 'current_partition',
                 'max_partition_triangles', 'max_candidate_tests']
        keys(data, names, names, 'planar piecewise mapping')
        if (data['name'] != 'planar_piecewise_affine' or type(data['mapping_version']) is not int
                or data['mapping_version'] != 1):
            raise ValueError('expected planar_piecewise_affine mapping_version 1')
        integer(data['max_partition_triangles'], 'max_partition_triangles')
        integer(data['max_candidate_tests'], 'max_candidate_tests')
        for name in ('previous_partition', 'current_partition'):
            mesh = data[name]
            if not isinstance(mesh, dict) or not isinstance(mesh.get('triangles'), list):
                raise ValueError(f'{name} requires an explicit mesh declaration')
            if len(mesh['triangles']) > data['max_partition_triangles']:
                raise ValueError('comparison partition exceeds max_partition_triangles')
        return cls(*(PlanarMesh.from_dict(data[name]) for name in names[2:4]),
                   data['max_partition_triangles'], data['max_candidate_tests'])


@dataclass(frozen=True)
class PlanarPiecewiseDomainPartitions:
    """Separate comparison-to-native overlays, each in its own SI xy area."""
    previous: PlanarTrackingOverlay
    current: PlanarTrackingOverlay


def verify_planar_piecewise_domains(previous, current, mapping, *, max_overlay_triangles=250000):
    """Verify every original FEM cell and the full boundary in both domains.

    Overlay.previous_cells indexes the corresponding comparison partition;
    overlay.current_cells indexes the corresponding native FEM mesh. These
    two partitions are not yet a joint field comparison (development P04).
    """
    if not isinstance(mapping, PlanarPiecewiseMapping):
        raise ValueError('expected PlanarPiecewiseMapping')
    integer(max_overlay_triangles, 'max_overlay_triangles')
    mapping = PlanarPiecewiseMapping.from_dict(mapping.to_dict())
    overlays = [exact_affine_polygon_overlay(partition, mesh, linear_xy=((1., 0.), (0., 1.)),
                max_candidate_tests=mapping.max_candidate_tests,
                max_overlay_triangles=max_overlay_triangles)
                for partition, mesh in zip((mapping.previous_partition, mapping.current_partition),
                                           (previous, current))]
    return PlanarPiecewiseDomainPartitions(*overlays)
