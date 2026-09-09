# SPDX-License-Identifier: Apache-2.0
"""Declared polygon homothety and nested original-element integration maps.

This module supplies geometry only. It does not certify mode correspondence.
The homothety is about the global origin, without translation or rotation.
"""
from dataclasses import dataclass
import numpy as np
from .config import integer, keys
from .planar_mesh import PlanarMesh
from .planar_refinement import refine_planar_mesh, REFERENCE, SPLIT
from .planar_tracking_overlap import PlanarTrackingOverlay


@dataclass(frozen=True)
class PolygonScaleMapping:
    scale: float
    previous_refinements: int = 0
    current_refinements: int = 0

    def __post_init__(self):
        if type(self.scale) not in (int, float) or not np.isfinite(self.scale) or self.scale <= 0:
            raise ValueError('polygon mapping scale must be a finite positive number')
        for name in ('previous_refinements', 'current_refinements'):
            integer(getattr(self, name), name, 0)
            if getattr(self, name) > 8:
                raise ValueError('polygon mapping supports at most eight declared refinements')
        if self.previous_refinements and self.current_refinements:
            raise ValueError('one polygon mesh must be the declared coarse mesh; only one refinement count may be nonzero')

    def to_dict(self):
        return dict(name='polygon_uniform_scale', scale=self.scale,
                    previous_refinements=self.previous_refinements,
                    current_refinements=self.current_refinements)

    @classmethod
    def from_dict(cls, data):
        names = ['name', 'scale', 'previous_refinements', 'current_refinements']
        keys(data, names, names, 'polygon scale mapping')
        if data['name'] != 'polygon_uniform_scale':
            raise ValueError('expected polygon_uniform_scale mapping')
        return cls(data['scale'], data['previous_refinements'], data['current_refinements'])


def _scaled(mesh, scale):
    with np.errstate(over='ignore', invalid='ignore'):
        points, polygon = mesh.points_xy_m*scale, mesh.polygon_xy_m*scale
    if not np.isfinite(points).all() or not np.isfinite(polygon).all():
        raise ValueError('polygon mapping scale overflows coordinates')
    return PlanarMesh.create(polygon, points, mesh.triangles)


def _same_declared_mesh(expected, actual):
    if not np.array_equal(expected.triangles, actual.triangles):
        raise ValueError('polygon mapping requires the declared triangle numbering and refinement connectivity')
    edges = np.unique(np.sort(expected.triangles[:, [[0,1],[1,2],[2,0]]].reshape(-1,2), axis=1), axis=0)
    lengths = np.linalg.norm(expected.points_xy_m[edges[:,1]]-expected.points_xy_m[edges[:,0]], axis=1)
    local_lengths = np.full(len(expected.points_xy_m), np.inf)
    np.minimum.at(local_lengths, edges[:,0], lengths)
    np.minimum.at(local_lengths, edges[:,1], lengths)
    boundary_lengths = np.linalg.norm(np.roll(expected.polygon_xy_m,-1,axis=0)-expected.polygon_xy_m, axis=1)
    boundary_local = np.minimum(boundary_lengths, np.roll(boundary_lengths,1))
    for name, local in (('polygon_xy_m', boundary_local), ('points_xy_m', local_lengths)):
        a, b = getattr(expected, name), getattr(actual, name)
        if a.shape != b.shape:
            raise ValueError('polygon mapping coordinate count differs from the declared refinement')
        # Arithmetic allowance must also be small relative to the local mesh.
        # Otherwise a large origin offset could hide a different physical domain.
        tolerance = 16*np.finfo(float).eps*np.minimum(np.maximum(np.abs(a), np.abs(b)), local[:,None])
        if not np.all(np.abs(a-b) <= tolerance):
            raise ValueError('polygon mapping coordinates do not match the declared origin scale and uniform refinement at local mesh precision')


def _exact_mesh(a, b):
    return all(np.array_equal(getattr(a, name), getattr(b, name))
               for name in ('polygon_xy_m', 'points_xy_m', 'triangles'))


def _refined(mesh, levels, budget):
    for _ in range(levels):
        mesh = refine_planar_mesh(mesh, max_triangles=budget)
    return mesh


def _exact_alternate_construction(previous, current, mapping, budget):
    """Recognize documented arithmetic orders without fitting coordinates."""
    if not mapping.previous_refinements:
        # Scale after subdivision, in addition to subdivision after scaling.
        expected = _scaled(_refined(previous, mapping.current_refinements, budget), mapping.scale)
        return _exact_mesh(expected, current)
    # Recover the coarse vertices preserved by our numbered four-way split.
    count = len(current.points_xy_m)
    base = PlanarMesh.create(previous.polygon_xy_m, previous.points_xy_m[:count], current.triangles)
    if _exact_mesh(_refined(base, mapping.previous_refinements, budget), previous):
        if _exact_mesh(_scaled(base, mapping.scale), current):
            return True
    # Reverse a scale-after-refinement construction without changing the input.
    expected = _scaled(_refined(current, mapping.previous_refinements, budget), 1/mapping.scale)
    return _exact_mesh(expected, previous)


def polygon_scale_overlay(previous, current, mapping, *, max_overlay_triangles=250000):
    """Map a verified nested pair into the previous mesh's physical xy area.

    previous_refinements means the previous mesh is finer than the current;
    current_refinements means the current mesh is finer than the previous.
    The common cells retain the finer input's numbering. Parent barycentric
    maps evaluate the original polynomials even when their element orders differ.
    """
    if not isinstance(previous, PlanarMesh) or not isinstance(current, PlanarMesh):
        raise ValueError('polygon scale mapping requires two declared PlanarMesh objects')
    if not isinstance(mapping, PolygonScaleMapping):
        raise ValueError('expected PolygonScaleMapping')
    mapping = PolygonScaleMapping.from_dict(mapping.to_dict())
    integer(max_overlay_triangles, 'max_overlay_triangles')
    reverse = bool(mapping.previous_refinements)
    coarse, fine = (current, previous) if reverse else (previous, current)
    levels = mapping.previous_refinements if reverse else mapping.current_refinements
    count = len(coarse.triangles)*4**levels
    if count > max_overlay_triangles:
        raise ValueError('polygon common refinement exceeds max_overlay_triangles')
    if count != len(fine.triangles):
        raise ValueError('polygon mapping triangle count differs from the declared refinement count')
    # Revalidate even caller-owned objects, before trusting geometry or topology.
    previous = PlanarMesh.create(previous.polygon_xy_m, previous.points_xy_m, previous.triangles)
    current = PlanarMesh.create(current.polygon_xy_m, current.points_xy_m, current.triangles)
    coarse, fine = (current, previous) if reverse else (previous, current)
    expected = _scaled(coarse, 1/mapping.scale if reverse else mapping.scale)
    parents = np.arange(len(coarse.triangles))
    bary = np.tile(np.eye(3), (len(parents), 1, 1))
    for _ in range(levels):
        expected = refine_planar_mesh(expected, max_triangles=max_overlay_triangles)
        bary = np.einsum('cij,njk->ncik', REFERENCE[SPLIT], bary).reshape(-1, 3, 3)
        parents = np.repeat(parents, 4)
    try:
        _same_declared_mesh(expected, fine)
    except ValueError:
        if not _exact_alternate_construction(previous, current, mapping, max_overlay_triangles):
            raise
    identity = np.tile(np.eye(3), (count, 1, 1))
    indices = np.arange(count)
    vertices = fine.points_xy_m[fine.triangles].copy()
    if not reverse:
        vertices /= mapping.scale
    a, b = vertices[:, 1]-vertices[:, 0], vertices[:, 2]-vertices[:, 0]
    determinants = a[:, 0]*b[:, 1]-a[:, 1]*b[:, 0]
    if not np.isfinite(vertices).all() or not np.isfinite(determinants).all() or np.any(determinants <= 0):
        raise ValueError('polygon reference integration area is not finite positive')
    arrays = ((indices, parents, identity, bary) if reverse else (parents, indices, bary, identity))
    arrays = (*arrays, vertices, determinants)
    for array in arrays:
        array.setflags(write=False)
    return PlanarTrackingOverlay(*arrays)
