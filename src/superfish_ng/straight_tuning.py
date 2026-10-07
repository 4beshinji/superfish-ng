# SPDX-License-Identifier: Apache-2.0
"""Owned straight polygon laws and derived comparison maps for scalar TM tune."""
from copy import deepcopy
from .config import integer,keys
from .project import Project
from .mesh_input import mesh_from_dict
from .scalar_expressions import validate_scalar_expression,evaluate_scalar_expression
from .saved_mode_tracking import validate_tracking_controls
from .studies import Study


def _law(request,project):
    case=project.case
    from .te import is_te
    if (is_te(case) or case.geometry_order!=1 or case.geometry_type not in ('profile','stepped_profile','contour')
            or case.z_min!='pec' or case.z_max!='pec' or project.sections is not None
            or project.reflect_full or project.mesh_data is not None):
        raise ValueError('straight tune version 9 requires an unassembled closed-PEC vacuum TM profile, stepped_profile or contour without an explicit solver mesh; TE integration is pending')
    law=request['shape_law']
    names=('format','version','reference_comparison_mesh','case_boundary_vertices','bindings')
    keys(law,names,names,'straight shape law')
    if law['format']!='straight_piecewise_shape_law' or type(law['version']) is not int or law['version']!=1:
        raise ValueError('straight shape law requires format straight_piecewise_shape_law and version 1')
    data=law['reference_comparison_mesh']
    mesh=mesh_from_dict(case,data)
    geometry=case.to_dict()['geometry'];field='vertices_zr_m' if case.geometry_type=='contour' else 'points_zr_m'
    vertices=geometry[field];owners=law['case_boundary_vertices']
    if type(owners) is not list or len(owners)!=len(vertices):
        raise ValueError('straight shape law must own every original Case boundary vertex exactly once')
    seen=set();references=set();boundary=set(mesh.boundary_edges.ravel().tolist())
    for owner in owners:
        keys(owner,('case_vertex','reference_vertex'),('case_vertex','reference_vertex'),'straight boundary owner')
        i=integer(owner['case_vertex'],'straight Case vertex',0);j=integer(owner['reference_vertex'],'straight reference vertex',0)
        if i>=len(vertices) or j>=len(mesh.points) or i in seen or j in references or j not in boundary:
            raise ValueError('straight boundary owners must be distinct valid original Case and comparison boundary vertices')
        if list(reversed(data['points'][j]))!=vertices[i]:
            raise ValueError('straight boundary owner does not match its original physical Case vertex')
        seen.add(i);references.add(j)
    bindings=law['bindings'];seen=set();active=False
    if type(bindings) is not list or not bindings:raise ValueError('straight bindings must be a nonempty list')
    for binding in bindings:
        keys(binding,('vertex','coordinate','expression'),('vertex','coordinate','expression'),'straight coordinate binding')
        i=integer(binding['vertex'],'straight binding vertex',0);coordinate=binding['coordinate']
        if i>=len(mesh.points) or coordinate not in ('r','z') or type(coordinate) is not str or (i,coordinate) in seen:
            raise ValueError('straight binding requires a distinct valid original reference vertex and coordinate r or z')
        seen.add((i,coordinate))
        metadata=validate_scalar_expression(binding['expression'],{request['parameter']:request['parameter_unit']},expected_unit='m')
        active=active or bool(metadata['variables'])
    if not active:raise ValueError('at least one straight binding must reference the parameter')
    return law,field


def _trial_geometry(request,project,value):
    law,field=_law(request,project)
    data=deepcopy(law['reference_comparison_mesh']);raw=project.to_dict()
    for binding in law['bindings']:
        coordinate=0 if binding['coordinate']=='r' else 1
        try:
            data['points'][binding['vertex']][coordinate]=evaluate_scalar_expression(binding['expression'],
                {request['parameter']:value},{request['parameter']:request['parameter_unit']},expected_unit='m')
        except ValueError as exc:
            raise ValueError(f'straight binding {binding["vertex"]}/{binding["coordinate"]} at {request["parameter"]}={value}: {exc}') from exc
    vertices=raw['case']['geometry'][field]
    for owner in law['case_boundary_vertices']:
        vertices[owner['case_vertex']]=list(reversed(data['points'][owner['reference_vertex']]))
    if project.case.geometry_type=='stepped_profile':
        for i,(left,right) in enumerate(zip(project.case.profile,project.case.profile[1:])):
            if (left[0]==right[0])!=(vertices[i][0]==vertices[i+1][0]):
                raise ValueError('straight step law must preserve the common z coordinate of both original step corners')
    trial=Project.from_dict(raw)
    if trial.case.to_dict()['geometry']!=raw['case']['geometry']:
        raise ValueError('straight law must preserve original boundary indexing, axis origin and tags')
    mesh_from_dict(trial.case,data)
    return trial,data


def validate_request(request,project):
    law,_=_law(request,project)
    controls=request['controls']
    if type(controls) is not dict or controls.get('mapping')!='piecewise_remesh' or 'comparison_meshes' in controls:
        raise ValueError('straight tune requires piecewise_remesh controls without input comparison_meshes; maps are derived from original trials')
    reference=law['reference_comparison_mesh']
    validate_tracking_controls(dict(controls,comparison_meshes=[reference,reference]))


def trial_project(request,project,value,phase):
    if phase not in ('search','refinement'):raise ValueError('straight tune phase must be search or refinement')
    trial,_=_trial_geometry(request,project,value)
    return (Study(trial,'mesh_convergence','mesh_scale',[1,request['refinement_scale']]).projects()[1]
            if phase=='refinement' else trial)


def pair_controls(request,previous_value,current_value,previous_project,current_project):
    """Reconstruct both original comparison domains and bind every Case attribute."""
    source=Project.from_dict(request['project']);meshes=[]
    for value,project in ((previous_value,previous_project),(current_value,current_project)):
        trial,data=_trial_geometry(request,source,value)
        fine=Study(trial,'mesh_convergence','mesh_scale',[1,request['refinement_scale']]).projects()[1]
        if project.to_dict() not in (trial.to_dict(),fine.to_dict()):
            raise ValueError('straight comparison Project differs from its original parameter law or declared final refinement')
        mesh_from_dict(project.case,data);meshes.append(data)
    controls=deepcopy(request['controls']);controls['comparison_meshes']=meshes
    validate_tracking_controls(controls)
    return controls
