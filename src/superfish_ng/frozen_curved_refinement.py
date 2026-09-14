# SPDX-License-Identifier: Apache-2.0
"""Capture existing marked split choices before a declared shape transformation."""
from dataclasses import replace
from .project import Project
from .mesh import make_mesh
from .mesh_input import mesh_from_dict,mesh_to_dict
from .curved_space import case_curved_space
from .curved_refinement import refine_curved_space
from .curved_marked_refinement import refine_marked_curved_space


def freeze_curved_refinement(project):
    """Return an explicit-source Project with every marked step's choices fixed.

    The source geometry is unchanged. This records choices made on that source,
    not an automatic correspondence to arbitrary independently generated meshes.
    All later reconstruction still validates geometry, quality and budgets.
    """
    if not isinstance(project,Project):raise ValueError('freezing curved refinement requires a Project')
    project=Project.from_dict(project.to_dict());case=project.case
    if case.geometry_order!=2 or project.sections is not None:
        raise ValueError('freezing requires an unassembled native quadratic Project')
    if not any(step.kind=='marked' for step in case.curved_refinement_steps):
        raise ValueError('freezing requires at least one marked curved refinement step')
    mesh=make_mesh(case) if project.mesh_data is None else mesh_from_dict(case,project.mesh_data)
    space=case_curved_space(replace(case,curved_refinement_steps=()),mesh)
    limit=case.contour_mesh.max_triangles if case.contour_mesh is not None else 250000
    steps=[]
    for index,step in enumerate(case.curved_refinement_steps,1):
        try:
            if step.kind=='uniform':
                if 4*len(space.geometry.cell_nodes)>limit:raise ValueError(f'uniform refinement exceeds max_triangles={limit}')
                space=refine_curved_space(space).space;steps.append(step)
            else:
                refined=refine_marked_curved_space(space,list(step.marked_cells),max_triangles=limit,
                    minimum_corner_angle_deg=step.minimum_corner_angle_deg,split_pattern=step.split_pattern)
                space=refined.space;steps.append(replace(step,split_pattern=refined.split_pattern))
        except ValueError as exc:raise ValueError(f'freezing curved step {index}: {exc}') from exc
    return replace(project,case=replace(case,curved_refinement_steps=tuple(steps)),mesh_data=mesh_to_dict(mesh))
