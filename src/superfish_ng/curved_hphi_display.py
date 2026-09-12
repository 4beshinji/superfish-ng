# SPDX-License-Identifier: Apache-2.0
"""Original-cell samples and exact polynomial boundaries for curved Hphi views."""
import numpy as np
from .constants import MU0
from .curved_hphi import CurvedHphiSolution


def curved_hphi_display_fields(solution, mode=0):
    """Partition each reference triangle 64 ways, retaining its quadratic map.

    Colour is the original FEM field at the mapped reference centroid. The
    six mapped points of each subtriangle define its actual curved boundary;
    joining only the three vertices would change the vacuum geometry.
    """
    if type(solution) is not CurvedHphiSolution:
        raise ValueError('curved display requires the original CurvedHphiSolution')
    reference = np.eye(3)[None, :, :]
    for _ in range(3):
        a, b, c = reference.transpose(1, 0, 2)
        ab, bc, ca = (a+b)/2, (b+c)/2, (c+a)/2
        reference = np.stack((np.stack((a, ab, ca), axis=1),
                              np.stack((ab, b, bc), axis=1),
                              np.stack((ca, bc, c), axis=1),
                              np.stack((ab, bc, ca), axis=1)), axis=1).reshape(-1, 3, 3)
    count = len(solution.space.cell_dofs)
    if count * len(reference) > 250000:
        raise ValueError('curved field display exceeds 250000 samples; use SI probes for this mesh')
    cells = np.repeat(np.arange(count), len(reference))
    barycentric = np.tile(reference.mean(axis=1), (count, 1))
    fields = solution.fields_in_cells(cells, barycentric, mode)
    for axis in ('r', 'phi', 'z'):
        for phase in ('real', 'quadrature'):
            fields[f'B{axis}_{phase}_T'] = MU0 * fields[f'H{axis}_{phase}_A_per_m']
    vertices = np.tile(reference, (count, 1, 1))
    midpoints = (vertices + np.roll(vertices, -1, axis=1))/2
    node_barycentric = np.concatenate((vertices, midpoints), axis=1)
    points = solution.mapped_points(np.repeat(cells, 6), node_barycentric.reshape(-1, 3))[0].reshape(-1, 6, 2)
    return dict(points_rz_m=points[:, :3].reshape(-1, 2),
                triangles=np.arange(3*len(cells)).reshape(-1, 3),
                quadratic_points_rz_m=points, parent_cells=cells,
                barycentric=barycentric, fields=fields,
                geometry='exact quadratic polynomial subtriangle boundaries',
                reference_subtriangles_per_cell=64)


def _triangle_path(points, scale):
    from matplotlib.path import Path
    a, b, c, ab, bc, ca = points[:, [1, 0]] * scale
    vertices = [a, 2*ab-(a+b)/2, b, 2*bc-(b+c)/2, c,
                2*ca-(c+a)/2, a, a]
    return Path(vertices, [Path.MOVETO, Path.CURVE3, Path.CURVE3,
                           Path.CURVE3, Path.CURVE3, Path.CURVE3,
                           Path.CURVE3, Path.CLOSEPOLY])


def paint_curved_hphi_panel(axis, solution, samples, values, scale, maximum, mesh):
    """Colour quadratic patches; holes are omitted by the original cell partition."""
    from matplotlib.path import Path
    from matplotlib.patches import PathPatch
    from matplotlib.collections import PatchCollection
    patches = [PathPatch(_triangle_path(points, scale))
               for points in samples['quadratic_points_rz_m']]
    artist = PatchCollection(patches, cmap='RdBu_r', edgecolors='none', antialiased=False)
    artist.set_array(values)
    artist.set_clim(-maximum, maximum)
    axis.add_collection(artist)
    geometry = solution.case.geometry
    edges = geometry.edge_vertices if mesh else geometry.base_mesh.boundary_edges
    midpoints = {tuple(edge): point for edge, point in
                 zip(geometry.edge_vertices, geometry.edge_midpoints_rz_m)}
    boundaries = {tuple(sorted(edge)) for edge in geometry.base_mesh.boundary_edges}
    for edge in edges:
        a, b = geometry.base_mesh.points_rz_m[edge][:, [1, 0]] * scale
        middle = midpoints[tuple(sorted(edge))][[1, 0]] * scale
        boundary = tuple(sorted(edge)) in boundaries
        path = Path([a, 2*middle-(a+b)/2, b], [Path.MOVETO, Path.CURVE3, Path.CURVE3])
        axis.add_patch(PathPatch(path, fill=False, color='black' if boundary else '0.5',
                                 linewidth=.7 if boundary else .25))
    bounds = solution.case.bounds_rz_m
    axis.update_datalim(np.asarray(bounds).T[:, [1, 0]] * scale)
    axis.autoscale_view()
    return artist
