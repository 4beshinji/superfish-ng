# SPDX-License-Identifier: Apache-2.0
"""Declared value-dependent partitions of one analytic curved geometry.

Each replacement declares its own mesh and refinement history. Reference charts
establish correspondence even when the represented P2 boundaries differ.
"""
from bisect import bisect_right
from copy import deepcopy
from dataclasses import replace
import math
from .config import keys, integer
from .project import Project
from .curved_project_remesh import validate_remesh_plan
from .curved_harmonic_deformation import _prefixes
from .curved_marked_refinement import _minimum_corner_angle
from .curved_space import case_curved_space
from .mesh_input import mesh_from_dict
from .frozen_curved_refinement import freeze_curved_refinement
from .curved_reference_partition import build_curved_reference_partition
from .curved_piecewise_remesh_tracking import validate_curved_comparison_meshes

MAX_PARTITIONS = 32


def _finite(value, label):
    try:valid=type(value) in (int,float) and math.isfinite(value)
    except OverflowError:valid=False
    if not valid:raise ValueError(f'{label} must be a finite number')


def _validate(schedule):
    fields=('schema_version','breakpoints','partitions','max_pair_tests')
    keys(schedule,fields,fields,'curved partition schedule')
    if type(schedule['schema_version']) is not int or schedule['schema_version']!=1:
        raise ValueError('curved partition schedule requires schema_version 1')
    cuts=schedule['breakpoints']
    if type(cuts) is not list:raise ValueError('partition breakpoints must be an array')
    for value in cuts:_finite(value,'partition breakpoint')
    if any(a>=b for a,b in zip(cuts,cuts[1:])):
        raise ValueError('partition breakpoints must be strictly increasing')
    partitions=schedule['partitions']
    if type(partitions) is not list or not 1<=len(partitions)<=MAX_PARTITIONS or len(partitions)!=len(cuts)+1:
        raise ValueError(f'partitions requires one more entry than breakpoints, at most {MAX_PARTITIONS}')
    integer(schedule['max_pair_tests'],'max_pair_tests')
    return partitions


def partition_index(schedule,value):
    """Equality chooses the right interval, independently of trial order."""
    _validate(schedule);_finite(value,'partition selection value')
    return bisect_right(schedule['breakpoints'],value)


def partition_comparison_mesh(project, partition, max_pair_tests):
    """Describe the actual source mesh, explicit chart and selected history."""
    from .study_shape_tracking import comparison_mesh
    result=comparison_mesh(project)
    result.update(schema_version=5,reference_vertices=deepcopy(partition['reference_vertices']),
        boundary_pairing='declared_reference_polylines',max_pair_tests=max_pair_tests)
    return result


def build_partition_schedule(project,schedule):
    """Preflight all native partitions and their common reference coverage.

    The Case's analytic primitives, RF metadata and physics are inherited.
    Only source mesh, optional chord counts and explicitly new histories vary.
    Marked indices belong to that new history and are frozen there. Each P2
    stage checks geometry and angle quality. No electromagnetic solve is run.
    """
    partitions=_validate(schedule)
    if not isinstance(project,Project):raise ValueError('partition schedule requires a Project')
    project=Project.from_dict(project.to_dict());case=project.case
    from .te import is_te
    if case.curved_contour is None or case.geometry_order!=2 or project.sections is not None:
        raise ValueError('partition schedule requires unassembled native P2 geometry')
    if is_te(case):
        from .curved_same_domain_tracking import _te_end_conditions
        _te_end_conditions([case,case])
    elif project.reflect_full or any(t not in ('axis','pec') for t in case.curved_contour.edge_tags):
        raise ValueError('TM partition schedule requires direct closed PEC/axis geometry')
    limit=case.contour_mesh.max_triangles if case.contour_mesh is not None else 250000
    results=[];documents=[]
    for partition in partitions:
        fields=('source_mesh','segments_per_curve','reference_vertices','curved_refinement_levels',
                'curved_refinement_steps','minimum_corner_angle_deg')
        keys(partition,fields,('source_mesh','reference_vertices','minimum_corner_angle_deg'),'curved partition')
        plan={k:deepcopy(v) for k,v in partition.items() if k not in ('segments_per_curve','reference_vertices')}
        choice,angle=validate_remesh_plan(dict(plan,schema_version=1))
        raw=project.to_dict();raw.update(project_version=2,mesh_data=deepcopy(partition['source_mesh']))
        if 'segments_per_curve' in partition:
            raw['case']['geometry']['segments_per_curve']=deepcopy(partition['segments_per_curve'])
        settings=raw['case']['mesh']
        for key in ('curved_refinement_levels','curved_refinement_steps'):settings.pop(key,None)
        settings[choice]=deepcopy(partition[choice])
        candidate=Project.from_dict(raw)
        mesh=mesh_from_dict(candidate.case,candidate.mesh_data)
        if len(mesh.triangles)>limit:raise ValueError('partition source mesh exceeds max_triangles')
        if any(step.kind=='marked' for step in candidate.case.curved_refinement_steps):
            candidate=freeze_curved_refinement(candidate)
        for index,stage in enumerate(_prefixes(candidate.case)):
            space=case_curved_space(stage,mesh)
            if is_te(stage) and candidate.reflect_full:
                from .curved_reflection import reflect_curved_space
                parity=1 if 'magnetic_symmetry' in (stage.z_min,stage.z_max) else -1
                reflect_curved_space(stage,space,coefficient_parity=parity)
            if _minimum_corner_angle(space.geometry.local_maps)<angle:
                raise ValueError(f'partition stage {index} violates minimum_corner_angle_deg')
        document=partition_comparison_mesh(candidate,partition,schedule['max_pair_tests'])
        validate_curved_comparison_meshes([document,document])
        results.append(candidate);documents.append(document)
    for candidate,document in zip(results,documents):
        # Charts describe the original half-domain; full reflected geometry was
        # validated above. Field tracking evaluates both lobes independently.
        build_curved_reference_partition(replace(results[0],reflect_full=False),replace(candidate,reflect_full=False),
            reference_vertices=[documents[0]['reference_vertices'],document['reference_vertices']],
            max_pair_tests=schedule['max_pair_tests'],max_triangles=limit)
    return tuple(results)
