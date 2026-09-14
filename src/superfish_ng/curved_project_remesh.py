# SPDX-License-Identifier: Apache-2.0
"""Replace a curved Project's initial mesh and explicitly redeclare its history."""
from copy import deepcopy
from dataclasses import replace
import math
from .config import keys
from .project import Project
from .mesh import make_mesh
from .mesh_input import mesh_from_dict
from .curved_space import case_curved_space
from .curved_marked_refinement import _minimum_corner_angle
from .curved_same_domain_tracking import compare_quadratic_space_boundaries
from .frozen_curved_refinement import freeze_curved_refinement


def remesh_curved_project(project, plan):
    """Return a portable Project on the identical represented quadratic domain.

    A plan explicitly supplies a source chord mesh and either uniform levels or
    a complete new ordered history. Marked IDs refer solely to that new history;
    old selections are never reinterpreted. New marked choices are frozen on the
    declared replacement mesh for subsequent shape deformation. Whole quadratic
    boundaries, rather than just shared analytic primitives, must coincide.
    No eigenmode is solved and no physical correspondence is inferred.
    """
    if not isinstance(project,Project):raise ValueError('curved remeshing requires a Project')
    project=Project.from_dict(project.to_dict());case=project.case
    from .te import is_te
    if (case.curved_contour is None or case.geometry_order!=2 or project.sections is not None
            or project.reflect_full or is_te(case) or any(t not in ('axis','pec') for t in case.curved_contour.edge_tags)):
        raise ValueError('curved remeshing requires direct, unassembled native P2 closed PEC/axis TM geometry')
    fields=('schema_version','source_mesh','curved_refinement_levels','curved_refinement_steps','minimum_corner_angle_deg')
    keys(plan,fields,('schema_version','source_mesh','minimum_corner_angle_deg'),'curved remesh plan')
    if type(plan['schema_version']) is not int or plan['schema_version']!=1:
        raise ValueError('curved remesh plan schema_version must be 1')
    choices=[name for name in ('curved_refinement_levels','curved_refinement_steps') if name in plan]
    if len(choices)!=1:
        raise ValueError('curved remesh plan must explicitly declare either curved_refinement_levels or curved_refinement_steps; old cell selections are not inherited')
    angle=plan['minimum_corner_angle_deg']
    try:valid=type(angle) in (int,float) and math.isfinite(angle) and 0<angle<60
    except OverflowError:valid=False
    if not valid:raise ValueError('minimum_corner_angle_deg must be finite and strictly between 0 and 60')
    if not isinstance(plan['source_mesh'],dict):raise ValueError('curved remesh plan source_mesh must be a complete chord mesh object')
    original_mesh=make_mesh(case) if project.mesh_data is None else mesh_from_dict(case,project.mesh_data)
    limit=case.contour_mesh.max_triangles if case.contour_mesh is not None else 250000
    if len(original_mesh.triangles)>limit:
        raise ValueError(f'curved remeshing original mesh exceeds max_triangles={limit}')
    original_space=case_curved_space(case,original_mesh)
    raw=project.to_dict();raw.update(project_version=2,mesh_data=deepcopy(plan['source_mesh']))
    mesh_settings=raw['case']['mesh']
    for name in ('curved_refinement_levels','curved_refinement_steps'):mesh_settings.pop(name,None)
    mesh_settings[choices[0]]=deepcopy(plan[choices[0]])
    candidate=Project.from_dict(raw)
    mesh=mesh_from_dict(candidate.case,candidate.mesh_data)
    if len(mesh.triangles)>limit:
        raise ValueError(f'curved remeshing source mesh exceeds max_triangles={limit}')
    if any(step.kind=='marked' for step in candidate.case.curved_refinement_steps):
        candidate=freeze_curved_refinement(candidate)
    def stages():
        for level in range(candidate.case.curved_refinement_levels+1):
            yield replace(candidate.case,curved_refinement_levels=level,curved_refinement_steps=())
        for end in range(1,len(candidate.case.curved_refinement_steps)+1):
            yield replace(candidate.case,curved_refinement_steps=candidate.case.curved_refinement_steps[:end])
    for index,stage in enumerate(stages()):
        space=case_curved_space(stage,mesh)
        actual=_minimum_corner_angle(space.geometry.local_maps)
        if actual<angle:
            raise ValueError(f'curved remeshing stage {index} minimum corner angle {actual:.9g} is below minimum_corner_angle_deg={angle}')
        compare_quadratic_space_boundaries(case,original_space,stage,space)
    return candidate
