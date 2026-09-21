# SPDX-License-Identifier: Apache-2.0
"""Finite polynomial affine shape laws evaluated from an original xy Project.

The parameter and matrix coefficients are dimensionless; translation
coefficients are metres. Binary64 declarations denote exact rational numbers.
The determinant test covers the entire closed parameter interval, including
even-multiplicity roots. It is not a mesh quality or floating-point certificate.
"""
from dataclasses import dataclass, replace
from fractions import Fraction
import math

import numpy as np

from .config import keys
from .polynomial_roots import isolate_real_roots
from .rational_bounds import polynomial, add, multiply
from .planar_project import PlanarProject
from .planar_polygon import PlanarPolygonCase
from .planar_mesh import PlanarMesh


def _finite(value, name):
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(name + ' must be a finite JSON number')
    return Fraction(value)


def _number(value):
    return value.numerator if value.denominator == 1 else float(value)


def _coefficients(values):
    if type(values) not in (list, tuple) or not 1 <= len(values) <= 9:
        raise ValueError('affine shape coefficients require one to nine ascending powers')
    return polynomial([_finite(v, 'affine shape coefficient') for v in values])


def _evaluate(coefficients, value):
    result = Fraction(0)
    for coefficient in reversed(coefficients):
        result = result * value + coefficient
    return result


@dataclass(frozen=True)
class PlanarAffineShapeLaw:
    linear_xy_coefficients: object
    translation_xy_m_coefficients: object
    bounds: object

    def __post_init__(self):
        matrix = self.linear_xy_coefficients
        if (type(matrix) not in (list, tuple) or len(matrix) != 2 or
                any(type(row) not in (list, tuple) or len(row) != 2 for row in matrix)):
            raise ValueError('affine shape requires a 2x2 matrix of coefficient arrays')
        matrix = tuple(tuple(_coefficients(p) for p in row) for row in matrix)
        translation = self.translation_xy_m_coefficients
        if type(translation) not in (list, tuple) or len(translation) != 2:
            raise ValueError('affine shape requires two translation coefficient arrays')
        translation = tuple(_coefficients(p) for p in translation)
        if type(self.bounds) not in (list, tuple) or len(self.bounds) != 2:
            raise ValueError('affine shape requires two increasing bounds')
        bounds = tuple(_finite(v, 'affine shape bound') for v in self.bounds)
        if bounds[0] >= bounds[1]:
            raise ValueError('affine shape bounds must increase')
        (a, b), (c, d) = matrix
        determinant = add(multiply(a, d), tuple(-v for v in multiply(b, c)))
        if determinant == (0,):
            raise ValueError('affine shape determinant is identically zero')
        # Only the exact root count is needed; do not spend work isolating roots
        # of an already invalid declaration. Count includes endpoint/tangent roots.
        roots = isolate_real_roots(determinant, *bounds, max_boxes=1)
        if roots['distinct_count']:
            raise ValueError('affine shape determinant vanishes in the closed parameter interval')
        object.__setattr__(self, 'linear_xy_coefficients', matrix)
        object.__setattr__(self, 'translation_xy_m_coefficients', translation)
        object.__setattr__(self, 'bounds', bounds)

    def exact_transform(self, value):
        value = _finite(value, 'affine shape parameter')
        if not self.bounds[0] <= value <= self.bounds[1]:
            raise ValueError('affine shape parameter is outside its certified interval')
        return (tuple(tuple(_evaluate(p, value) for p in row)
                      for row in self.linear_xy_coefficients),
                tuple(_evaluate(p, value) for p in self.translation_xy_m_coefficients))

    def to_dict(self):
        return dict(kind='polynomial_affine_xy', parameter_unit='dimensionless',
                    coefficient_order='ascending', linear_coefficient_unit='dimensionless',
                    translation_coefficient_unit='m',
                    linear_xy_coefficients=[[list(map(_number, p)) for p in row]
                                            for row in self.linear_xy_coefficients],
                    translation_xy_m_coefficients=[list(map(_number, p)) for p in self.translation_xy_m_coefficients],
                    bounds=list(map(_number, self.bounds)))

    @classmethod
    def from_dict(cls, data):
        names = ('kind', 'parameter_unit', 'coefficient_order', 'linear_coefficient_unit',
                 'translation_coefficient_unit', 'linear_xy_coefficients',
                 'translation_xy_m_coefficients', 'bounds')
        keys(data, names, names, 'planar affine shape law')
        for key, value in [('kind', 'polynomial_affine_xy'), ('parameter_unit', 'dimensionless'),
                           ('coefficient_order', 'ascending'), ('linear_coefficient_unit', 'dimensionless'),
                           ('translation_coefficient_unit', 'm')]:
            if data[key] != value:
                raise ValueError('planar affine shape ' + key + ' must be ' + value)
        return cls(data['linear_xy_coefficients'], data['translation_xy_m_coefficients'], data['bounds'])

    def project(self, original, value):
        """Transform an explicit original polygon, rounding each final coordinate once.

        Case validation rejects invalid floating geometry. No coordinate fitting,
        cumulative deformation, field transport, or eigensolve occurs here.
        """
        if type(original) is not PlanarProject or type(original.case) is not PlanarPolygonCase:
            raise ValueError('affine shape requires an original explicit polygon PlanarProject')
        matrix, translation = self.exact_transform(value)
        (a, b), (c, d) = matrix
        determinant = a*d-b*c
        def transform(points):
            try:
                values = np.asarray([[float(a*Fraction(float(x))+b*Fraction(float(y))+translation[0]),
                                      float(c*Fraction(float(x))+d*Fraction(float(y))+translation[1])]
                                     for x, y in points])
            except (ValueError, OverflowError) as exc:
                raise ValueError('affine shape coordinates are not finite binary64') from exc
            if not np.isfinite(values).all():
                raise ValueError('affine shape coordinates are not finite binary64')
            return values
        mesh = original.case.mesh
        polygon = transform(mesh.polygon_xy_m)
        cells = mesh.triangles
        if determinant < 0:
            polygon = polygon[::-1]
            cells = cells[:, [0, 2, 1]]
        mapped = PlanarMesh.create(polygon, transform(mesh.points_xy_m), cells)
        return replace(original, case=replace(original.case, mesh=mapped))
