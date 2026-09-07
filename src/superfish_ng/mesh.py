# SPDX-License-Identifier: Apache-2.0
"""Straight P1 triangles in (r,z); profile corners are mesh vertices."""
from dataclasses import dataclass, replace
import numpy as np
from .config import Case


@dataclass
class Mesh:
    points: np.ndarray
    triangles: np.ndarray
    boundary_edges: np.ndarray
    boundary_tags: np.ndarray  # axis / pec / electric_symmetry / magnetic_symmetry
    boundary_cells: np.ndarray
    axis_nodes: np.ndarray


def make_mesh(case: Case) -> Mesh:
    if case.contour is not None:
        raise ValueError("general contour mesh generation requires G02; profile mesher cannot process reentrant boundaries")
    mesh = make_base_mesh(case)
    if case.boundary_max_edge_m is not None or case.corner_max_edge_m is not None:
        mesh = refine_physical_edges(case, mesh)
    return mesh


def make_base_mesh(case: Case) -> Mesh:
    if case.geometry_type == 'arc_profile':
        from .geometry import linearize_profile
        polygon = replace(case, profile=linearize_profile(case), geometry_type='stepped_profile',
                          arcs=(), arc_chord_tolerance_m=1e-5)
        return make_stepped_mesh(polygon)
    if case.geometry_type == "stepped_profile":
        return make_stepped_mesh(case)
    zs = []
    for (za, _), (zb, _) in zip(case.profile, case.profile[1:]):
        count = max(1, int(np.ceil(case.nz * (zb - za) / case.length - 1e-12)))
        zs.extend(np.linspace(za, zb, count + 1)[:-1])
    zs.append(case.length)
    radius = np.interp(zs, *np.array(case.profile).T)
    stride = case.nr + 1
    points = [(s*r, z) for z, r in zip(zs, radius)
              for s in np.linspace(0, 1, stride)]
    axis_nodes = np.arange(0, len(points), stride)
    triangles = []
    for j in range(len(zs)-1):
        for i in range(case.nr):
            a = j*stride+i
            b = a+stride
            append_quad(points, triangles, (a, a+1, b+1, b), case.triangulation)
    triangles = np.array(triangles, dtype=np.int64)
    return finish_mesh(case, np.asarray(points), triangles, axis_nodes)


def append_quad(points, triangles, vertices, triangulation):
    """Split a counterclockwise trapezoid without changing its boundary."""
    a, b, c, d = vertices
    if triangulation == 'diagonal':
        triangles.extend(((a, b, c), (a, c, d)))
    else:
        center = len(points)
        points.append(tuple(sum(points[v][k] for v in vertices)/4 for k in (0, 1)))
        triangles.extend(((a, b, center), (b, c, center),
                          (c, d, center), (d, a, center)))


def finish_mesh(case, points, triangles, axis_nodes):
    """Extract boundary incidence without assuming a structured node stride."""
    incidence = {}
    for cell, t in enumerate(triangles):
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            edge = tuple(sorted((a, b)))
            incidence.setdefault(edge, []).append(cell)
    if any(len(cells) > 2 for cells in incidence.values()):
        raise ValueError("nonmanifold triangle edge")
    boundary = [(e, c[0]) for e, c in incidence.items() if len(c) == 1]
    edges = np.array([e for e, _ in boundary], dtype=np.int64)
    tags = np.full(len(edges), "pec", dtype="U20")
    tags[np.all(points[edges, 0] == 0, axis=1)] = "axis"
    tags[np.all(points[edges, 1] == 0, axis=1)] = case.z_min
    tags[np.all(points[edges, 1] == case.length, axis=1)] = case.z_max
    result = Mesh(points, triangles, edges, tags,
                  np.array([c for _, c in boundary]), axis_nodes)
    element_geometry(result)  # reject degenerate geometry before assembly
    return result


def make_stepped_mesh(case):
    """Conforming axial slabs with shared absolute radial levels at every step.

    Each slab is a trapezoid. Unequal column heights are joined by triangles;
    neighboring slabs share all nodes below the smaller aperture. Vertical
    disk faces remain boundary edges, never short artificial sloping walls.
    """
    maximum = max(r for _, r in case.profile)
    levels = np.unique(np.concatenate((np.linspace(0., maximum, case.nr+1),
                                       np.array(case.profile)[:, 1])))
    points, triangles, lookup = [], [], {}
    epsilon = 32*np.finfo(float).eps*maximum
    distinct = [levels[0]]
    for value in levels[1:]:
        if value-distinct[-1] > epsilon:
            distinct.append(value)
    levels = np.array(distinct)

    def column(z, radius):
        # Merge only roundoff-scale duplicates, including translated arc samples.
        index = np.searchsorted(levels, radius)
        for near in levels[max(0, index-1):index+1]:
            if abs(radius-near) <= epsilon:
                radius = near
                break
        radii = np.append(levels[levels < radius-epsilon], radius)
        indices = []
        for r in radii:
            key = (float(r), float(z))
            if key not in lookup:
                lookup[key] = len(points)
                points.append(key)
            indices.append(lookup[key])
        return indices, radii

    for (za, ra), (zb, rb) in zip(case.profile, case.profile[1:]):
        if zb == za:
            continue
        count = max(1, int(np.ceil(case.nz*(zb-za)/case.length-1e-12)))
        zs = np.linspace(za, zb, count+1)
        radii = np.linspace(ra, rb, count+1)
        left, lr = column(zs[0], radii[0])
        for z, radius in zip(zs[1:], radii[1:]):
            right, rr = column(z, radius)
            i = j = 0
            while i < len(left)-1 or j < len(right)-1:
                if i == len(left)-1:
                    triangles.append((left[i], right[j+1], right[j]))
                    j += 1
                elif j == len(right)-1 or lr[i+1] < rr[j+1]:
                    triangles.append((left[i], left[i+1], right[j]))
                    i += 1
                elif lr[i+1] == rr[j+1]:
                    append_quad(points, triangles, (left[i], left[i+1], right[j+1], right[j]),
                                case.triangulation)
                    i += 1
                    j += 1
                else:
                    triangles.append((left[i], right[j+1], right[j]))
                    j += 1
            left, lr = right, rr
    points, triangles = np.asarray(points), np.asarray(triangles, dtype=np.int64)
    axis = np.flatnonzero(points[:, 0] == 0.)
    axis = axis[np.argsort(points[axis, 1])]
    mesh = finish_mesh(case, points, triangles, axis)
    validate_profile_mesh(case, mesh)
    return mesh


def validate_profile_mesh(case, mesh):
    """Reject missing/extra boundary, cracks and area errors in slab meshes."""
    _, counts = np.unique(mesh.boundary_edges, return_counts=True)
    if np.any(counts != 2):
        raise ValueError("mesh boundary has a crack or branch")
    all_edges = np.sort(np.concatenate((mesh.triangles[:, [0, 1]], mesh.triangles[:, [1, 2]],
                                        mesh.triangles[:, [2, 0]])), axis=1)
    edge_count = len(np.unique(all_edges, axis=0))
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    graph = coo_matrix((np.ones(len(all_edges)), all_edges.T), shape=(len(mesh.points), len(mesh.points))).tocsr()
    if (connected_components(graph, directed=False, return_labels=False) != 1
            or len(mesh.points)-edge_count+len(mesh.triangles) != 1):
        raise ValueError("mesh must be a connected disk without holes")
    if case.contour is None:
        boundary = [(0., 0.)]+list(case.profile)+[(case.length, 0.), (0., 0.)]
    else:
        boundary = list(case.contour.vertices_zr_m)+[case.contour.vertices_zr_m[0]]
    segments = np.array(list(zip(boundary, boundary[1:])))[:, :, ::-1]
    scale = float(np.max(np.abs(segments)))
    tolerance = 128*np.finfo(float).eps*scale
    covered = np.zeros(len(mesh.boundary_edges), dtype=bool)
    ends = mesh.points[mesh.boundary_edges]
    for segment_index, (a, b) in enumerate(segments):
        delta = b-a
        offsets = ends-a
        cross = offsets[:, :, 0]*delta[1]-offsets[:, :, 1]*delta[0]
        fraction = offsets @ delta/(delta @ delta)
        matches = np.all((np.abs(cross) <= tolerance*np.linalg.norm(delta)) &
                         (fraction >= -tolerance/np.linalg.norm(delta)) &
                         (fraction <= 1+tolerance/np.linalg.norm(delta)), axis=1)
        covered |= matches
        if case.contour is not None:
            if not np.any(matches) or np.any(mesh.boundary_tags[matches] != case.contour.edge_tags[segment_index]):
                raise ValueError(f'mesh contour segment {segment_index} is missing or has wrong tags')
            spans = np.sort(fraction[matches], axis=1)
            spans = spans[np.argsort(spans[:, 0])]
            eps = tolerance/np.linalg.norm(delta)
            if (abs(spans[0, 0]) > eps or abs(spans[-1, 1]-1) > eps
                    or np.any(np.abs(spans[1:, 0]-spans[:-1, 1]) > eps)):
                raise ValueError(f'mesh contour segment {segment_index} has gaps or overlapping coverage')
    expected_length = np.linalg.norm(segments[:, 1]-segments[:, 0], axis=1).sum()
    actual_length = np.linalg.norm(ends[:, 1]-ends[:, 0], axis=1).sum()
    expected_area = (case.contour.area_m2 if case.contour is not None else
                     sum((b[0]-a[0])*(a[1]+b[1])/2 for a, b in zip(case.profile, case.profile[1:])))
    _, det, _ = element_geometry(mesh)
    if (not covered.all() or abs(actual_length/expected_length-1) > 1e-10
            or abs(det.sum()/(2*expected_area)-1) > 1e-10):
        raise ValueError("mesh does not reproduce the prescribed profile boundary and area")


def element_geometry(mesh):
    p = mesh.points[mesh.triangles]
    jac = np.stack((p[:, 1]-p[:, 0], p[:, 2]-p[:, 0]), axis=2)
    det = np.linalg.det(jac)
    if np.any(det <= 0) or not np.all(np.isfinite(det)):
        raise ValueError("mesh has nonpositive or nonfinite triangle Jacobian")
    grad = np.einsum("ij,tjk->tik", np.array([[-1., -1.], [1., 0.], [0., 1.]]), np.linalg.inv(jac))
    return p, det, grad


def refine_physical_edges(case, mesh):
    """Conforming midpoint refinement by physical edge length, without moving walls.

    Mark boundary edges and edges intersecting balls around polygon turns.
    Longest-edge closure limits skinny transition triangles. Every shared edge
    has exactly one midpoint; two-edge transitions use their shorter diagonal.
    """
    corners = []
    for a, b, c in zip(case.profile, case.profile[1:], case.profile[2:]):
        left, right = np.subtract(b, a), np.subtract(c, b)
        if abs(np.linalg.det(np.array([left, right]))) > 1e-12*np.linalg.norm(left)*np.linalg.norm(right):
            corners.append(b[::-1])
    for iteration in range(30):
        triangles = mesh.triangles
        edges, inverse = np.unique(np.sort(triangles[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2), axis=1),
                                   axis=0, return_inverse=True)
        cell_edges = inverse.reshape(-1, 3)
        ends = mesh.points[edges]
        delta = ends[:, 1]-ends[:, 0]
        length = np.linalg.norm(delta, axis=1)
        marked = np.zeros(len(edges), dtype=bool)
        if case.boundary_max_edge_m is not None:
            counts = np.bincount(inverse, minlength=len(edges))
            # Axis is a coordinate boundary, not a physical wall.
            boundary = (counts == 1) & ~np.all(ends[:, :, 0] == 0, axis=1)
            marked |= boundary & (length > case.boundary_max_edge_m*(1+1e-12))
        if case.corner_max_edge_m is not None:
            for corner in corners:
                fraction = np.clip(np.sum((corner-ends[:, 0])*delta, axis=1)/length**2, 0, 1)
                distance = np.linalg.norm(ends[:, 0]+fraction[:, None]*delta-corner, axis=1)
                marked |= (distance <= case.corner_radius_m*(1+1e-12)) & (length > case.corner_max_edge_m*(1+1e-12))
        if not marked.any():
            polygon = case
            if case.geometry_type == 'arc_profile':
                from .geometry import linearize_profile
                polygon = replace(case, profile=linearize_profile(case), geometry_type='stepped_profile',
                                  arcs=(), arc_chord_tolerance_m=1e-5)
            validate_profile_mesh(polygon, mesh)
            return mesh
        # Splitting a short edge also splits a longest edge of its owner cells.
        longest = cell_edges[np.arange(len(triangles)), np.argmax(length[cell_edges], axis=1)]
        while True:
            required = longest[marked[cell_edges].any(axis=1)]
            if marked[required].all():
                break
            marked[required] = True
        ids = np.flatnonzero(marked)
        midpoints = np.full(len(edges), -1, dtype=int)
        midpoints[ids] = np.arange(len(mesh.points), len(mesh.points)+len(ids))
        points = np.concatenate((mesh.points, ends[ids].mean(axis=1)))
        result = []
        for tri, es in zip(triangles, cell_edges):
            flags = marked[es]
            count = int(flags.sum())
            if count == 0:
                result.append(tuple(tri))
            elif count == 3:
                a, b, c = tri
                ab, bc, ca = midpoints[es]
                result.extend(((a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)))
            elif count == 1:
                i = int(np.flatnonzero(flags)[0])
                a, b, c = np.roll(tri, -i)
                m = midpoints[es[i]]
                result.extend(((a, m, c), (m, b, c)))
            else:
                # Rotate so the unsplit edge is a--b.
                i = int(np.flatnonzero(~flags)[0])
                a, b, c = np.roll(tri, -i)
                _, bc, ca = midpoints[np.roll(es, -i)]
                result.append((ca, bc, c))
                if np.linalg.norm(points[a]-points[bc]) <= np.linalg.norm(points[b]-points[ca]):
                    result.extend(((a, b, bc), (a, bc, ca)))
                else:
                    result.extend(((a, b, ca), (b, bc, ca)))
        axis = np.flatnonzero(points[:, 0] == 0)
        axis = axis[np.argsort(points[axis, 1])]
        mesh = finish_mesh(case, points, np.asarray(result, dtype=np.int64), axis)
    raise ValueError('physical mesh refinement exceeded 30 passes; increase edge size or reduce base mesh size')
