# SPDX-License-Identifier: Apache-2.0
"""TE display samples in the original FEM cells, never RF peak estimates."""
import numpy as np


def display_te_fields(solution, mode=0):
    """Return display points/triangles, nodal Ephi, and exact centre fields.

    Quadratic cells use four display triangles. Curved cell centres are
    mapped from reference coordinates, rather than sampled on the chords.
    """
    if solution.element_order == 1:
        points, cells = solution.mesh.points, solution.mesh.triangles
        split = np.array([[0, 1, 2]])
        reference = np.eye(3)
    else:
        if solution.case.geometry_order == 2:
            points = solution.space.geometry.points_rz_m
            cells = solution.space.geometry.cell_nodes
        else:
            points, cells = solution.space.dof_points, solution.space.cell_dofs
        split = np.array([[0, 3, 5], [3, 1, 4], [5, 4, 2], [3, 4, 5]])
        reference = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1],
                              [.5, .5, 0], [0, .5, .5], [.5, 0, .5]])
    centres = reference[split].mean(axis=1)
    fields = solution.fields_in_cells(np.repeat(np.arange(len(cells)), len(split)),
                                      np.tile(centres, (len(cells), 1)), mode)
    return (points, cells[:, split].reshape(-1, 3),
            points[:, 0]*solution.coefficients_v_per_m2[:, mode], fields)
