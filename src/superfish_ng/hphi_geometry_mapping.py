# SPDX-License-Identifier: Apache-2.0
"""Declared straight (r,z) geometry maps for explicit meridional Hphi domains.

This is the H08 mapping contract. It covers non-similar coaxial inner/outer
radius and length changes and an explicitly declared affine correspondence
that keeps the axis and every PEC hole. Coordinates denote their exact binary64
values; the declaration's invertibility, orientation and axis policy are
checked over exact rational numbers. The declared map is applied to the
previous mesh in binary64 and then compared to the current mesh with the
existing exact same-domain overlay, so boundary and hole coverage is checked
without a CAD tolerance. No automatic boundary, hole or mode correspondence is
inferred; a declaration that does not map the previous contours onto the
current ones exactly is rejected.
"""
from dataclasses import dataclass
from fractions import Fraction
import numpy as np
from .axis_connected_mesh import AxisConnectedMesh
from .axis_hphi import AxisAccelerationPath
from .config import integer, keys
from .meridional_mesh import MeridionalMesh
from .meridional_overlap import meridional_overlay


def _finite(value, name):
    if type(value) not in (int, float) or not np.isfinite(value):
        raise ValueError(name + ' must be finite')
    return float(value)


@dataclass(frozen=True)
class HphiGeometryMapping:
    """An invertible orientation-preserving affine map in the (r,z) plane.

    With ``inverse`` false the declaration is ``current = A*previous + t``.
    With ``inverse`` true it is read as ``previous = A*current + t`` and the
    operative previous-to-current map is the exact inverse. Only orientation
    preserving maps are accepted; a reflection or a collapsed element is
    rejected rather than silently renumbered.
    """
    linear_rz: object
    translation_rz_m: tuple = (0., 0.)
    inverse: bool = False
    max_candidate_tests: int = 2000000

    def __post_init__(self):
        linear = self.linear_rz
        if type(linear) not in (list, tuple) or len(linear) != 2:
            raise ValueError('linear_rz must be a 2x2 matrix')
        rows = []
        for row in linear:
            if type(row) not in (list, tuple) or len(row) != 2:
                raise ValueError('linear_rz must be a 2x2 matrix')
            rows.append(tuple(_finite(value, 'linear_rz entry') for value in row))
        object.__setattr__(self, 'linear_rz', tuple(rows))
        if type(self.translation_rz_m) not in (list, tuple) or len(self.translation_rz_m) != 2:
            raise ValueError('translation_rz_m requires two finite SI coordinates')
        object.__setattr__(self, 'translation_rz_m',
                           tuple(_finite(value, 'translation_rz_m') for value in self.translation_rz_m))
        if type(self.inverse) is not bool:
            raise ValueError('inverse must be boolean')
        integer(self.max_candidate_tests, 'max_candidate_tests')
        determinant = self._declared_determinant()
        if determinant == 0:
            raise ValueError('linear_rz must be invertible')
        if determinant < 0:
            raise ValueError('Hphi geometry mapping must preserve orientation; inversion is unsupported')

    def _declared_determinant(self):
        (a, b), (c, d) = [[Fraction(value) for value in row] for row in self.linear_rz]
        return a*d-b*c

    @property
    def matrix(self):
        return np.asarray(self.linear_rz, dtype=float)

    @property
    def orientation_preserving(self):
        return self._declared_determinant() > 0

    @property
    def signed_determinant(self):
        return float(np.linalg.det(self.matrix))

    def effective_exact(self):
        """Exact previous-to-current coefficients (a,b,c,d,tr,tz) as Fractions."""
        (a, b), (c, d) = [[Fraction(value) for value in row] for row in self.linear_rz]
        tr, tz = (Fraction(value) for value in self.translation_rz_m)
        determinant = a*d-b*c
        if self.inverse:
            a, b, c, d = d/determinant, -b/determinant, -c/determinant, a/determinant
            tr, tz = -(a*tr+b*tz), -(c*tr+d*tz)
        return a, b, c, d, tr, tz

    def transform_points(self, points):
        """Evaluate the previous-to-current map in floating arithmetic."""
        a, b, c, d, tr, tz = (float(value) for value in self.effective_exact())
        values = np.asarray(points, dtype=float)
        r, z = values[:, 0], values[:, 1]
        return np.column_stack((a*r+b*z+tr, c*r+d*z+tz))

    def to_dict(self):
        return dict(name='hphi_affine_rz', linear_rz=[list(row) for row in self.linear_rz],
                    translation_rz_m=list(self.translation_rz_m), inverse=self.inverse,
                    max_candidate_tests=self.max_candidate_tests)

    @classmethod
    def from_dict(cls, data):
        names = ['name', 'linear_rz', 'translation_rz_m', 'inverse', 'max_candidate_tests']
        keys(data, names, names, 'Hphi geometry mapping')
        if data['name'] != 'hphi_affine_rz':
            raise ValueError('expected hphi_affine_rz mapping')
        if type(data['linear_rz']) is not list or any(type(row) is not list for row in data['linear_rz']):
            raise ValueError('linear_rz must be a JSON list of two lists')
        if type(data['translation_rz_m']) is not list:
            raise ValueError('translation_rz_m must be a JSON list')
        return cls(data['linear_rz'], data['translation_rz_m'], data['inverse'], data['max_candidate_tests'])


def coaxial_dimension_mapping(inner_radius_m, outer_radius_m, length_m,
                              target_inner_radius_m, target_outer_radius_m, target_length_m,
                              *, max_candidate_tests=2000000):
    """Diagonal map changing coaxial inner/outer radius and length independently.

    The previous annulus ``[inner, outer] x [0, length]`` maps onto the target
    rectangle. Radii stay strictly positive and ordered, so an inner conductor
    that closes on itself or passes the outer wall is rejected here rather than
    producing a degenerate domain.
    """
    values = dict(inner_radius_m=inner_radius_m, outer_radius_m=outer_radius_m, length_m=length_m,
                  target_inner_radius_m=target_inner_radius_m, target_outer_radius_m=target_outer_radius_m,
                  target_length_m=target_length_m)
    for name, value in values.items():
        _finite(value, name)
    if not 0 < inner_radius_m < outer_radius_m:
        raise ValueError('coaxial mapping requires 0 < inner_radius_m < outer_radius_m')
    if not 0 < target_inner_radius_m < target_outer_radius_m:
        raise ValueError('coaxial mapping requires 0 < target inner radius < target outer radius; hole disappearance is unsupported')
    if not 0 < length_m or not 0 < target_length_m or not np.isfinite(target_length_m/length_m):
        raise ValueError('coaxial mapping requires positive finite lengths')
    radial = (target_outer_radius_m-target_inner_radius_m)/(outer_radius_m-inner_radius_m)
    axial = target_length_m/length_m
    translation = (target_inner_radius_m-radial*inner_radius_m, 0.)
    return HphiGeometryMapping(((radial, 0.), (0., axial)), translation, max_candidate_tests=max_candidate_tests)


def map_mesh(mesh, mapping):
    """Return the declared affine image of an explicit meridional mesh."""
    if not isinstance(mapping, HphiGeometryMapping):
        raise ValueError('expected HphiGeometryMapping')
    mapping = HphiGeometryMapping.from_dict(mapping.to_dict())
    if type(mesh) not in (MeridionalMesh, AxisConnectedMesh):
        raise ValueError('Hphi geometry mapping requires an explicit meridional or axis-connected mesh')
    if type(mesh) is AxisConnectedMesh:
        _check_axis_map(mapping)
    data = {**mesh.to_dict()}
    data['outer_rz_m'] = mapping.transform_points(mesh.outer_rz_m).tolist()
    data['points_rz_m'] = mapping.transform_points(mesh.points_rz_m).tolist()
    data['holes_rz_m'] = [mapping.transform_points(hole).tolist() for hole in mesh.holes_rz_m]
    return type(mesh).from_dict(data)


def _check_axis_map(mapping):
    a, b, c, d, tr, tz = mapping.effective_exact()
    if b != 0 or tr != 0 or tz != 0:
        raise ValueError('axis-connected domains require the axis to stay fixed; radial shear, radial translation and axial shift are unsupported')
    if a <= 0 or d <= 0:
        raise ValueError('axis-connected domains require positive radial and axial scaling')


def map_axis_interval(mapping, interval):
    """Map a declared vacuum axis interval, rejecting an off-axis movement."""
    if not isinstance(mapping, HphiGeometryMapping):
        raise ValueError('expected HphiGeometryMapping')
    if type(interval) not in (tuple, list) or len(interval) != 2:
        raise ValueError('axis interval requires two SI coordinates')
    a, b, c, d, tr, tz = mapping.effective_exact()
    if b != 0 or tr != 0 or tz != 0:
        raise ValueError('axis interval mapping requires the axis to stay fixed with no radial shear or translation')
    start, end = (Fraction(_finite(value, 'axis interval')) for value in interval)
    mapped = (d*start, d*end)
    if not mapped[0] < mapped[1]:
        raise ValueError('axis interval must map to an increasing interval')
    return (float(mapped[0]), float(mapped[1]))


def map_axis_acceleration(mapping, path):
    """Map an axis acceleration path consistently with the declared (r,z) map.

    ``beta`` is a velocity ratio and stays unchanged. The start, end and phase
    origin follow the axial image ``z' = d*z`` on the fixed axis, so the
    declared coordinates remain inside the mapped vacuum.
    """
    if not isinstance(mapping, HphiGeometryMapping):
        raise ValueError('expected HphiGeometryMapping')
    if not isinstance(path, AxisAccelerationPath):
        raise ValueError('axis acceleration mapping requires an AxisAccelerationPath')
    a, b, c, d, tr, tz = mapping.effective_exact()
    if b != 0 or tr != 0 or tz != 0:
        raise ValueError('axis acceleration mapping requires the axis to stay fixed')
    z_start = float(d*Fraction(path.z_start_m))
    z_end = float(d*Fraction(path.z_end_m))
    origin = float(d*Fraction(path.phase_origin_m))
    return AxisAccelerationPath(z_start, z_end, path.beta, origin)


def hphi_geometry_overlay(previous, current, mapping, *, max_candidate_tests=2000000,
                          max_overlay_triangles=250000):
    """Partition previous and current under a declared affine map.

    The previous mesh is mapped by the declaration and then compared to the
    current mesh with the exact same-domain overlay: both must cover exactly
    the same outer contour and every PEC hole, with independent interior
    connectivity and boundary subdivisions. A rounded or nearest-point match
    is rejected, and no boundary or hole correspondence is inferred. The exact
    determinant and axis checks are applied before the float map, so a
    reflection, collapsed element or moved axis is refused even when the
    rounded contours would happen to agree.
    """
    if not isinstance(mapping, HphiGeometryMapping):
        raise ValueError('expected HphiGeometryMapping')
    mapping = HphiGeometryMapping.from_dict(mapping.to_dict())
    integer(max_candidate_tests, 'max_candidate_tests')
    integer(max_overlay_triangles, 'max_overlay_triangles')
    if type(previous) not in (MeridionalMesh, AxisConnectedMesh) or type(previous) is not type(current):
        raise ValueError('Hphi geometry overlay requires two explicit meshes with the same unknown')
    if type(previous) is AxisConnectedMesh:
        _check_axis_map(mapping)
    return meridional_overlay(map_mesh(previous, mapping), current,
                              max_candidate_tests=max_candidate_tests,
                              max_overlay_triangles=max_overlay_triangles)
