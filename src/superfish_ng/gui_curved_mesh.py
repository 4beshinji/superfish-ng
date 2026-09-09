# SPDX-License-Identifier: Apache-2.0
"""Bounded native mesh data for graphical selection before another history step."""
from dataclasses import replace
from .config import integer
from .mesh import make_mesh
from .curved_space import case_curved_space


def curved_mesh_document(project, *, maximum_cells=5000):
    integer(maximum_cells,'maximum_cells')
    case=project.case
    if case.geometry_order!=2:
        raise ValueError('graphical curved selection requires geometry_order=2')
    controls=case.contour_mesh
    if controls is None:
        raise ValueError('graphical selection requires native contour_mesh controls')
    # Lower only the failure budget: any completed mesh follows the identical
    # geometry/history path. Never coarsen or renumber a mesh for display.
    bounded=replace(case,contour_mesh=replace(controls,max_triangles=min(controls.max_triangles,maximum_cells)))
    try:
        from .mesh_input import mesh_from_dict
        mesh=make_mesh(bounded) if project.mesh_data is None else mesh_from_dict(bounded,project.mesh_data)
        space=case_curved_space(bounded,mesh)
    except ValueError as exc:
        raise ValueError(f'graphical mesh selection (maximum {maximum_cells} cells): {exc}') from exc
    if len(space.geometry.cell_nodes)>maximum_cells:
        raise ValueError(f'graphical mesh selection exceeds maximum {maximum_cells} cells')
    return dict(case=case.to_dict(),points_rz_m=space.geometry.points_rz_m.tolist(),
                cell_nodes=space.geometry.cell_nodes.tolist(),cell_index_origin=0,
                scope='original domain after its complete current history, before a new refinement step; no eigensolve')
