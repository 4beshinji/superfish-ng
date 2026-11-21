# SPDX-License-Identifier: Apache-2.0
"""Original-element comparisons for fully regenerated planar shape trials."""
import numpy as np
from .config import integer
from .planar_mesh import PlanarMesh
from .planar_refinement import refine_planar_mesh, REFERENCE, SPLIT
from .planar_tracking_overlap import PlanarTrackingOverlay


def reference_shape_overlay(previous, current, mapping, *, max_overlay_triangles=250000, label):
    """A shared dyadic reference partition, retained separately in both domains.

    The public mapping caller validates the original Project, law and values.
    Each native geometry is independently revalidated and regenerated here.
    Floating midpoint rounding is retained; no global affine image is fitted.
    """
    integer(max_overlay_triangles, 'max_overlay_triangles')
    if any(not isinstance(mesh, PlanarMesh) for mesh in (previous, current)):
        raise ValueError(label + ' comparison requires two PlanarMesh objects')
    levels = (mapping.previous_refinements, mapping.current_refinements)
    maximum = max(levels)
    count = len(mapping.original_project.case.mesh.triangles)*4**maximum
    if count > max_overlay_triangles:
        raise ValueError(label + ' common partition exceeds max_overlay_triangles')
    parents, barycentrics, vertices = [], [], []
    for actual, value, level in zip((previous, current),
                                   (mapping.previous_value, mapping.current_value), levels):
        expected = mapping.shape_law.project(mapping.original_project, value).case.mesh
        for _ in range(level):
            expected = refine_planar_mesh(expected, max_triangles=max_overlay_triangles)
        if any(not np.array_equal(getattr(expected, name), getattr(actual, name))
               for name in ('polygon_xy_m', 'points_xy_m', 'triangles')):
            raise ValueError(label + ' native mesh differs from its original Project, law or refinement')
        # Diagnose altered regeneration first, then validate the actual geometry
        # independently before it contributes to a comparison partition.
        actual = PlanarMesh.create(actual.polygon_xy_m, actual.points_xy_m, actual.triangles)
        indices = np.arange(len(actual.triangles))
        bary = np.tile(np.eye(3), (len(indices), 1, 1))
        for _ in range(maximum-level):
            bary = np.einsum('cij,njk->ncik', REFERENCE[SPLIT], bary).reshape(-1, 3, 3)
            indices = np.repeat(indices, 4)
        parents.append(indices); barycentrics.append(bary)
        vertices.append(np.einsum('nij,njk->nik', bary, actual.points_xy_m[actual.triangles[indices]]))
    # Columns of each J map the common local triangle to an actual physical cell.
    jacobians = [np.swapaxes(v[:, 1:]-v[:, :1], 1, 2) for v in vertices]
    determinants = [j[:, 0, 0]*j[:, 1, 1]-j[:, 0, 1]*j[:, 1, 0] for j in jacobians]
    if any(not np.isfinite(j).all() for j in jacobians) or any(
            not np.isfinite(d).all() or np.any(d <= 0) for d in determinants):
        raise ValueError(label + ' physical comparison triangles are unresolved')
    # adj(J_current * inv(J_previous)) transports transverse cutoff E into
    # the previous frame, consistent with the existing affine-map convention.
    effective = jacobians[1] @ np.linalg.inv(jacobians[0])
    transport = np.empty_like(effective)
    transport[:, 0, 0] = effective[:, 1, 1]; transport[:, 1, 1] = effective[:, 0, 0]
    transport[:, 0, 1] = -effective[:, 0, 1]; transport[:, 1, 0] = -effective[:, 1, 0]
    if not np.isfinite(transport).all() or np.any(np.linalg.det(transport) <= 0):
        raise ValueError(label + ' field transport is unresolved')
    arrays = (*parents, *barycentrics, vertices[0], determinants[0])
    for array in (*arrays, transport):
        array.setflags(write=False)
    return PlanarTrackingOverlay(*arrays), transport
