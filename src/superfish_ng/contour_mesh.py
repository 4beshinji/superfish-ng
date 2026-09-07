# SPDX-License-Identifier: Apache-2.0
"""Initial polygon triangulation; refinement is required before public solving."""
import numpy as np


def triangulate_contour(case):
    """Partition a validated contour without deleting tagged collinear vertices.

    Work in normalized (z,r), clip convex ears containing no other active
    vertex (including their boundary), then reverse orientation for (r,z).
    Prefer the ear with largest dimensionless area/edge-square quality.
    This preference is not a minimum-angle guarantee or a mesh-size control.
    """
    from .mesh_input import mesh_from_dict

    if case.contour is None:
        raise ValueError('initial contour triangulation requires a contour Case')
    contour = case.contour
    points = np.asarray(contour.vertices_zr_m)
    q = points / np.max(points)
    tolerance = 128 * np.finfo(float).eps
    active = list(range(len(points)))
    triangles = []

    def cross(a, b):
        return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]

    while len(active) > 3:
        best = None
        for slot, b in enumerate(active):
            a, c = active[slot - 1], active[(slot + 1) % len(active)]
            pa, pb, pc = q[[a, b, c]]
            twice_area = cross(pb - pa, pc - pa)
            if twice_area <= tolerance:
                continue
            others = q[[v for v in active if v not in (a, b, c)]]
            inside = ((cross(pb-pa, others-pa) >= -tolerance)
                      & (cross(pc-pb, others-pb) >= -tolerance)
                      & (cross(pa-pc, others-pc) >= -tolerance))
            if inside.any():
                continue
            quality = twice_area / (np.sum((pb-pa)**2)
                                    + np.sum((pc-pb)**2) + np.sum((pa-pc)**2))
            if best is None or quality > best[0]:
                best = (quality, slot, (a, c, b))
        if best is None:
            raise ValueError('contour triangulation cannot resolve a positive ear; '
                             'check small gaps/near-collinear features or supply a validated external mesh')
        _, slot, triangle = best
        triangles.append(list(triangle))
        del active[slot]
    a, b, c = active
    if cross(q[b]-q[a], q[c]-q[a]) <= tolerance:
        raise ValueError('contour triangulation leaves a numerically degenerate triangle; '
                         'check feature scales or supply a validated external mesh')
    triangles.append([a, c, b])
    return mesh_from_dict(case, dict(
        schema_version=1, length_unit='m', coordinate_order='rz', index_base=0,
        points=points[:, ::-1].tolist(), triangles=triangles,
        boundary_edges=[[i, (i+1) % len(points)] for i in range(len(points))],
        boundary_tags=list(contour.edge_tags)))
