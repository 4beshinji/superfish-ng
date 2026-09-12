# SPDX-License-Identifier: Apache-2.0
"""Saved declaration for exact affine maps with independent boundary meshes."""
from dataclasses import dataclass
from fractions import Fraction
import numpy as np
from .config import keys
from .planar_tracking_affine_remesh import PolygonAffineRemeshMapping
from .planar_tracking_exact_affine import exact_affine_polygon_overlay


@dataclass(frozen=True)
class PolygonExactAffineRemeshMapping:
    """Map x_current = A*x_previous+t, or its rationally evaluated inverse.

    Boundary and interior subdivisions are independent. Both actual mesh
    boundaries must be exact affine images of the declared polygons. This
    declaration does not generate rounded mesh coordinates.
    """
    linear_xy: object
    translation_xy_m: tuple = (0., 0.)
    inverse: bool = False
    max_candidate_tests: int = 2000000

    def __post_init__(self):
        validated = PolygonAffineRemeshMapping(self.linear_xy, self.translation_xy_m,
                                               self.inverse, self.max_candidate_tests)
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, getattr(validated, name))
        # The geometry can remain rational, but field integration must use a
        # finite, nonsingular binary64 transform. Reject unresolved conversion.
        self.current_to_previous_linear

    @property
    def exact_determinant(self):
        (a, b), (c, d) = self.linear_xy
        return Fraction(a)*Fraction(d)-Fraction(b)*Fraction(c)

    @property
    def orientation_preserving(self):
        return self.exact_determinant > 0

    @property
    def current_to_previous_linear(self):
        """adj(E), with effective E=A or A^-1; round only final entries."""
        (a, b), (c, d) = [[Fraction(v) for v in row] for row in self.linear_xy]
        det = a*d-b*c
        exact = [[a/det, b/det], [c/det, d/det]] if self.inverse else [[d, -b], [-c, a]]
        try:
            result = np.asarray(exact, dtype=float)
        except (OverflowError, ValueError) as exc:
            raise ValueError('exact affine field transport is unresolved in binary64') from exc
        if (not np.isfinite(result).all()
                or any(v != 0 and f == 0 for row, floats in zip(exact, result) for v, f in zip(row, floats))):
            raise ValueError('exact affine field transport is unresolved in binary64')
        (u, v), (w, z) = [[Fraction(float(f)) for f in row] for row in result]
        if u*z-v*w == 0:
            raise ValueError('exact affine field transport is singular after binary64 conversion')
        result.setflags(write=False)
        return result

    def to_dict(self):
        return dict(name='polygon_exact_affine_remesh', linear_xy=[list(row) for row in self.linear_xy],
                    translation_xy_m=list(self.translation_xy_m), inverse=self.inverse,
                    max_candidate_tests=self.max_candidate_tests)

    @classmethod
    def from_dict(cls, data):
        names = ['name', 'linear_xy', 'translation_xy_m', 'inverse', 'max_candidate_tests']
        keys(data, names, names, 'exact affine-remesh mapping')
        if data['name'] != 'polygon_exact_affine_remesh':
            raise ValueError('expected polygon_exact_affine_remesh mapping')
        # Reuse the established strict JSON shape checks, without inheriting
        # version 6's rounded-coordinate semantics or isinstance dispatch.
        value = PolygonAffineRemeshMapping.from_dict(dict(data, name='polygon_affine_remesh'))
        return cls(value.linear_xy, value.translation_xy_m, value.inverse, value.max_candidate_tests)


def polygon_exact_affine_remesh_overlay(previous, current, mapping, *, max_overlay_triangles=250000):
    """Integrate original element fields using the current physical xy area."""
    if not isinstance(mapping, PolygonExactAffineRemeshMapping):
        raise ValueError('expected PolygonExactAffineRemeshMapping')
    mapping = PolygonExactAffineRemeshMapping.from_dict(mapping.to_dict())
    return exact_affine_polygon_overlay(previous, current, linear_xy=mapping.linear_xy,
        translation_xy_m=mapping.translation_xy_m, inverse=mapping.inverse,
        max_candidate_tests=mapping.max_candidate_tests, max_overlay_triangles=max_overlay_triangles)
