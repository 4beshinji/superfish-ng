# SPDX-License-Identifier: Apache-2.0
"""Value-based initial meshes with an independent original shape correspondence."""
from bisect import bisect_right
import math
from .config import keys
from .curved_project_remesh import remesh_curved_project,validate_remesh_plan
from .curved_harmonic_study import geometry_at_value,project_at_value
from .curved_harmonic_deformation import deform_curved_project
from .curved_same_domain_tracking import compare_quadratic_space_boundaries
from .curved_space import case_curved_space
from .mesh_input import mesh_from_dict


def validate_mesh_schedule(schedule):
    fields=('schema_version','breakpoints','plans')
    keys(schedule,fields,fields,'curved Study mesh_schedule')
    if type(schedule['schema_version']) is not int or schedule['schema_version']!=1:
        raise ValueError('mesh_schedule schema_version must be 1')
    cuts=schedule['breakpoints']
    try:
        finite=(type(cuts) is list and all(type(x) in (int,float) and math.isfinite(x) for x in cuts))
    except OverflowError:finite=False
    if not finite or any(b<=a for a,b in zip(cuts,cuts[1:])):
        raise ValueError('mesh_schedule breakpoints must be a strictly increasing array of finite parameter values')
    plans=schedule['plans']
    if type(plans) is not list or len(plans)!=len(cuts)+1:
        raise ValueError('mesh_schedule requires one more plan than breakpoints')
    replaced=False
    for entry in plans:
        keys(entry,('kind','plan'),('kind',),'mesh_schedule entry')
        if entry['kind']=='original':keys(entry,('kind',),('kind',),'original mesh entry')
        elif entry['kind']=='replace':
            keys(entry,('kind','plan'),('kind','plan'),'replacement mesh entry')
            validate_remesh_plan(entry['plan']);replaced=True
        else:raise ValueError('mesh_schedule entry kind must be original or replace')
    if not replaced:raise ValueError('curved_remesh_sweep requires at least one replacement plan')


def projects_at_values(study):
    """Preflight every declared plan, then derive each point from its own base.

    Intervals are left-closed at their finite breakpoints (equality chooses the
    right plan). The same rule applies to descending sweeps and inserted values.
    New marked choices are frozen on the original geometry before deformation;
    the comparison geometry always retains the original Project's numbering.
    """
    schedule=study.mesh_schedule
    validate_mesh_schedule(schedule)
    bases=[study.project if entry['kind']=='original' else remesh_curved_project(study.project,entry['plan'])
           for entry in schedule['plans']]
    result=[]
    for value in study.values:
        original=project_at_value(study,value)
        base=bases[bisect_right(schedule['breakpoints'],value)]
        if base is study.project:result.append(original);continue
        candidate=deform_curved_project(base,geometry_at_value(study,value),rf_coordinates=study.rf_coordinates,
                                        minimum_corner_angle_deg=study.minimum_corner_angle_deg)
        def space(project):return case_curved_space(project.case,mesh_from_dict(project.case,project.mesh_data))
        compare_quadratic_space_boundaries(original.case,space(original),candidate.case,space(candidate))
        result.append(candidate)
    return result
