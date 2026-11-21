# SPDX-License-Identifier: Apache-2.0
"""Polynomial vertex displacements on a fixed original planar triangulation.

Cell orientation is certified on the full closed parameter interval. Global
boundary embedding and binary64 mesh validity are checked at each trial;
positive cell determinants alone are not a global geometry certificate.
"""
from dataclasses import dataclass, replace
from fractions import Fraction
import numpy as np
from .config import keys, integer
from .planar_affine_shape import _finite, _number, _evaluate
from .planar_mesh import PlanarMesh
from .planar_polygon import PlanarPolygonCase
from .planar_project import PlanarProject
from .planar_tracking_affine_remesh import _boundary_cycle
from .polynomial_roots import isolate_real_roots
from .rational_bounds import polynomial, add, multiply


def _coefficients(values):
    if type(values) not in (list, tuple) or not 1 <= len(values) <= 9:
        raise ValueError('piecewise displacement requires one to nine ascending coefficients')
    return polynomial([_finite(v, 'piecewise displacement coefficient') for v in values])


def _subtract(a, b):
    return add(a, tuple(-v for v in b))


@dataclass(frozen=True, eq=False)
class PlanarPiecewiseShapeLaw:
    original_mesh: PlanarMesh
    displacement_xy_m_coefficients: object
    bounds: object
    max_triangles: int = 250000

    def __post_init__(self):
        integer(self.max_triangles, 'piecewise shape max_triangles')
        if not isinstance(self.original_mesh, PlanarMesh):
            raise ValueError('piecewise shape requires an original PlanarMesh')
        if len(self.original_mesh.triangles) > self.max_triangles:
            raise ValueError('piecewise shape original mesh exceeds max_triangles')
        mesh = PlanarMesh.create(self.original_mesh.polygon_xy_m, self.original_mesh.points_xy_m,
                                 self.original_mesh.triangles)
        raw = self.displacement_xy_m_coefficients
        if (type(raw) not in (list, tuple) or len(raw) != len(mesh.points_xy_m)
                or any(type(row) not in (list, tuple) or len(row) != 2 for row in raw)):
            raise ValueError('piecewise shape requires two displacement polynomials per original vertex')
        coefficients = tuple(tuple(_coefficients(values) for values in row) for row in raw)
        if type(self.bounds) not in (list, tuple) or len(self.bounds) != 2:
            raise ValueError('piecewise shape requires two increasing bounds')
        bounds = tuple(_finite(v, 'piecewise shape bound') for v in self.bounds)
        if bounds[0] >= bounds[1]:
            raise ValueError('piecewise shape bounds must increase')
        positions = [tuple(add((Fraction(float(v)),), p) for v, p in zip(point, row))
                     for point, row in zip(mesh.points_xy_m, coefficients)]
        for index, cell in enumerate(mesh.triangles):
            a, b, c = [positions[int(i)] for i in cell]
            u = tuple(_subtract(y, x) for x, y in zip(a, b))
            v = tuple(_subtract(y, x) for x, y in zip(a, c))
            determinant = _subtract(multiply(u[0], v[1]), multiply(u[1], v[0]))
            if (_evaluate(determinant, bounds[0]) <= 0
                    or isolate_real_roots(determinant, *bounds, max_boxes=1)['distinct_count']):
                raise ValueError(f'piecewise shape cell {index} Jacobian is not positive throughout the closed interval')
        object.__setattr__(self, 'original_mesh', mesh)
        object.__setattr__(self, 'displacement_xy_m_coefficients', coefficients)
        object.__setattr__(self, 'bounds', bounds)

    def exact_points(self, value):
        value = _finite(value, 'piecewise shape parameter')
        if not self.bounds[0] <= value <= self.bounds[1]:
            raise ValueError('piecewise shape parameter is outside its certified interval')
        return tuple(tuple(Fraction(float(v))+_evaluate(p, value) for v, p in zip(point, row))
                     for point, row in zip(self.original_mesh.points_xy_m, self.displacement_xy_m_coefficients))

    def project(self, original, value):
        """Regenerate from the original mesh, preserving all boundary vertices."""
        if type(original) is not PlanarProject or type(original.case) is not PlanarPolygonCase:
            raise ValueError('piecewise shape requires an original explicit polygon Project')
        if any(not np.array_equal(getattr(original.case.mesh, name), getattr(self.original_mesh, name))
               for name in ('polygon_xy_m', 'points_xy_m', 'triangles')):
            raise ValueError('piecewise shape original Project mesh differs from the law declaration')
        exact = self.exact_points(value)
        try:
            points = np.asarray(exact, dtype=float)
        except (ValueError, OverflowError) as exc:
            raise ValueError('piecewise shape coordinates are unresolved in binary64') from exc
        if (not np.isfinite(points).all()
                or any(v != 0 and f == 0 for row, floats in zip(exact, points) for v, f in zip(row, floats))):
            raise ValueError('piecewise shape coordinates are unresolved in binary64')
        lookup = {tuple(point): i for i, point in enumerate(self.original_mesh.points_xy_m)}
        boundary = [lookup[tuple(point)] for point in _boundary_cycle(self.original_mesh)]
        # A formerly collinear boundary vertex may become a real corner. Keep
        # the entire cycle, rather than invent a chord through that vertex.
        mapped = PlanarMesh.create(points[boundary], points, self.original_mesh.triangles)
        return replace(original, case=replace(original.case, mesh=mapped))

    def to_dict(self):
        return dict(kind='polynomial_piecewise_xy', parameter_unit='dimensionless',
                    coefficient_order='ascending', displacement_coefficient_unit='m',
                    original_mesh=self.original_mesh.to_dict(),
                    displacement_xy_m_coefficients=[[list(map(_number, values)) for values in row]
                                                     for row in self.displacement_xy_m_coefficients],
                    bounds=list(map(_number, self.bounds)), max_triangles=self.max_triangles)

    @classmethod
    def from_dict(cls, data):
        names = ['kind', 'parameter_unit', 'coefficient_order', 'displacement_coefficient_unit',
                 'original_mesh', 'displacement_xy_m_coefficients', 'bounds', 'max_triangles']
        keys(data, names, names, 'planar piecewise shape law')
        for key, value in (('kind', 'polynomial_piecewise_xy'), ('parameter_unit', 'dimensionless'),
                           ('coefficient_order', 'ascending'), ('displacement_coefficient_unit', 'm')):
            if data[key] != value:
                raise ValueError('piecewise shape ' + key + ' must be ' + value)
        integer(data['max_triangles'], 'piecewise shape max_triangles')
        raw = data['displacement_xy_m_coefficients']
        if (type(raw) is not list or any(type(row) is not list or any(type(p) is not list for p in row) for row in raw)
                or type(data['bounds']) is not list):
            raise ValueError('piecewise shape JSON coefficients and bounds must be arrays')
        mesh = data['original_mesh']
        if not isinstance(mesh, dict) or type(mesh.get('triangles')) is not list:
            raise ValueError('piecewise shape original_mesh requires an explicit mesh declaration')
        if len(mesh['triangles']) > data['max_triangles']:
            raise ValueError('piecewise shape original mesh exceeds max_triangles')
        return cls(PlanarMesh.from_dict(mesh), raw, data['bounds'], data['max_triangles'])
