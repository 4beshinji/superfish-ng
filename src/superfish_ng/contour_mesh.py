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


def refine_contour(case, mesh, max_edge_m, *, max_triangles=250000, max_passes=30):
    """Conforming midpoint refinement with inherited boundary tags.

    All edges obey max_edge_m; existing Case boundary/corner controls can
    request smaller local sizes. Longest-edge closure avoids splitting only
    a short side. This does not repair poor angles in the initial mesh.
    """
    from .mesh_input import mesh_from_dict, mesh_to_dict

    if case.contour is None:
        raise ValueError('contour refinement requires a contour Case')
    if type(max_edge_m) not in (int, float) or not np.isfinite(max_edge_m) or max_edge_m <= 0:
        raise ValueError('max_edge_m must be finite and positive')
    if type(max_triangles) is not int or max_triangles < 1:
        raise ValueError('max_triangles must be a positive integer')
    if type(max_passes) is not int or max_passes < 1:
        raise ValueError('max_passes must be a positive integer')
    mesh = mesh_from_dict(case, mesh_to_dict(mesh))
    vertices = np.asarray(case.contour.vertices_zr_m)[:, ::-1]
    incoming, outgoing = vertices-np.roll(vertices, 1, axis=0), np.roll(vertices, -1, axis=0)-vertices
    turns = np.abs(incoming[:, 0]*outgoing[:, 1]-incoming[:, 1]*outgoing[:, 0])
    corners = vertices[turns > 1e-12*np.linalg.norm(incoming, axis=1)*np.linalg.norm(outgoing, axis=1)]
    for iteration in range(max_passes+1):
        if len(mesh.triangles) > max_triangles:
            raise ValueError('contour refinement exceeds max_triangles; increase requested edge sizes or the explicit limit')
        edges, inverse = np.unique(np.sort(mesh.triangles[:, [[0,1],[1,2],[2,0]]].reshape(-1,2), axis=1),
                                   axis=0, return_inverse=True)
        cell_edges = inverse.reshape(-1,3)
        ends = mesh.points[edges]
        delta = ends[:,1]-ends[:,0]
        lengths = np.linalg.norm(delta, axis=1)
        marked = lengths > max_edge_m*(1+1e-12)
        if case.boundary_max_edge_m is not None:
            boundary = (np.bincount(inverse, minlength=len(edges)) == 1) & ~np.all(ends[:,:,0] == 0, axis=1)
            marked |= boundary & (lengths > case.boundary_max_edge_m*(1+1e-12))
        if case.corner_max_edge_m is not None:
            for corner in corners:
                fraction = np.clip(np.sum((corner-ends[:,0])*delta, axis=1)/lengths**2, 0, 1)
                distance = np.linalg.norm(ends[:,0]+fraction[:,None]*delta-corner, axis=1)
                marked |= ((distance <= case.corner_radius_m*(1+1e-12))
                           & (lengths > case.corner_max_edge_m*(1+1e-12)))
        if not marked.any():
            return mesh
        if iteration == max_passes:
            raise ValueError('contour refinement exceeds max_passes; increase requested edge sizes or the explicit limit')
        longest = cell_edges[np.arange(len(cell_edges)), np.argmax(lengths[cell_edges], axis=1)]
        while True:
            required = longest[marked[cell_edges].any(axis=1)]
            if marked[required].all():
                break
            marked[required] = True
        predicted = len(mesh.triangles)+int(marked[cell_edges].sum())
        if predicted > max_triangles:
            raise ValueError('contour refinement exceeds max_triangles; increase requested edge sizes or the explicit limit')
        ids = np.flatnonzero(marked)
        midpoint = np.full(len(edges), -1, dtype=int)
        midpoint[ids] = np.arange(len(mesh.points), len(mesh.points)+len(ids))
        points = np.concatenate((mesh.points, ends[ids].mean(axis=1)))
        triangles = []
        for tri, es in zip(mesh.triangles, cell_edges):
            flags = marked[es]
            count = int(flags.sum())
            if count == 0:
                triangles.append(tuple(tri))
            elif count == 3:
                a,b,c = tri
                ab,bc,ca = midpoint[es]
                triangles.extend(((a,ab,ca),(ab,b,bc),(ca,bc,c),(ab,bc,ca)))
            elif count == 1:
                i = int(np.flatnonzero(flags)[0])
                a,b,c = np.roll(tri,-i)
                m = midpoint[es[i]]
                triangles.extend(((a,m,c),(m,b,c)))
            else:
                i = int(np.flatnonzero(~flags)[0])
                a,b,c = np.roll(tri,-i)
                _,bc,ca = midpoint[np.roll(es,-i)]
                triangles.append((ca,bc,c))
                if np.linalg.norm(points[a]-points[bc]) <= np.linalg.norm(points[b]-points[ca]):
                    triangles.extend(((a,b,bc),(a,bc,ca)))
                else:
                    triangles.extend(((a,b,ca),(b,bc,ca)))
        edge_lookup = {tuple(e): i for i,e in enumerate(edges)}
        boundary, tags = [], []
        for (a,b), tag in zip(mesh.boundary_edges, mesh.boundary_tags):
            m = midpoint[edge_lookup[tuple(sorted((a,b)))]]
            children = [(a,b)] if m < 0 else [(a,m),(m,b)]
            boundary.extend(children)
            tags.extend([str(tag)]*len(children))
        mesh = mesh_from_dict(case, dict(
            schema_version=1, length_unit='m', coordinate_order='rz', index_base=0,
            points=points.tolist(), triangles=np.asarray(triangles).tolist(),
            boundary_edges=np.asarray(boundary).tolist(), boundary_tags=tags))


def contour_mesh_quality(mesh):
    """Geometric measurements only; no implication of RF accuracy."""
    from .mesh import element_geometry
    element_geometry(mesh)
    p = mesh.points[mesh.triangles]
    sides = np.linalg.norm(np.roll(p,-1,axis=1)-p,axis=2)
    u,v = p[:,1]-p[:,0], p[:,2]-p[:,0]
    twice_area = u[:,0]*v[:,1]-u[:,1]*v[:,0]
    angles = []
    for i in range(3):
        a,b = p[:,(i+1)%3]-p[:,i], p[:,(i+2)%3]-p[:,i]
        angles.append(np.arctan2(twice_area,np.sum(a*b,axis=1)))
    quality = 2*np.sqrt(3)*twice_area/np.sum(sides**2,axis=1)
    return dict(triangles=len(p), points=len(mesh.points),
                min_angle_deg=float(np.rad2deg(np.min(angles))),
                min_quality=float(quality.min()), median_quality=float(np.median(quality)),
                max_edge_m=float(sides.max()))
