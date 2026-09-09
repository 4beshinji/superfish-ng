# SPDX-License-Identifier: Apache-2.0
"""Explicit mesh replacement and uniform subdivisions of fixed straight domains."""
from copy import deepcopy
import numpy as np
from .project import Project,parse_json
from .mesh import make_mesh
from .mesh_input import mesh_from_dict,mesh_to_dict


def replace_project_mesh(document,mesh_document):
    """Replace or detach a mesh atomically, without reinterpreting marked IDs.

    The old mesh may no longer fit edited geometry; it is deliberately replaced,
    not parsed as the new mesh. Other Project and Case fields remain strict.
    """
    raw=deepcopy(document.to_dict() if isinstance(document,Project) else
                 parse_json(document) if isinstance(document,str) else document)
    old=None
    if isinstance(raw,dict) and 'project_version' in raw:
        version=raw['project_version']
        if type(version) is not int or version not in (1,2):raise ValueError('project_version must be 1 or 2')
        if version==1 and 'mesh_data' in raw:raise ValueError('project version 1 cannot contain mesh_data')
        if version==2:
            if not isinstance(raw.get('mesh_data'),dict):raise ValueError('project version 2 requires a mesh_data object')
            old=raw.pop('mesh_data');raw['project_version']=1
    base=Project.from_dict(raw)
    data=parse_json(mesh_document) if isinstance(mesh_document,str) else deepcopy(mesh_document)
    if mesh_document is not None and not isinstance(data,dict):
        raise ValueError('mesh document must be a JSON object; use the detach operation to remove it')
    result=base.to_dict()
    if data is not None:result.update(project_version=2,mesh_data=data)
    candidate=Project.from_dict(result)
    if any(step.kind=='marked' for step in base.case.curved_refinement_steps):
        previous=make_mesh(base.case) if old is None else mesh_from_dict(base.case,old)
        following=make_mesh(base.case) if data is None else mesh_from_dict(base.case,data)
        if mesh_to_dict(previous)!=mesh_to_dict(following):
            raise ValueError('mesh replacement changes the base of marked-cell history; clear that history explicitly first')
    return candidate


def _straight_mesh_refinement_projects(project,values):
    """Dyadic subdivisions with common edge midpoints, preserving the polygon."""
    from .contour_mesh import _split_marked_edges
    mesh=mesh_from_dict(project.case,project.mesh_data)
    limit=project.case.contour_mesh.max_triangles if project.case.contour_mesh is not None else 250000
    capacity=limit//len(mesh.triangles)
    if max(values)>(capacity.bit_length()-1)//2:
        raise ValueError(f'uniform source-mesh refinement exceeds max_triangles={limit}')
    result=[]
    for level in range(max(values)+1):
        if level in values:
            raw=project.to_dict();raw['mesh_data']=mesh_to_dict(mesh);result.append(Project.from_dict(raw))
        if level<max(values):
            edges,inverse=np.unique(np.sort(mesh.triangles[:,[[0,1],[1,2],[2,0]]].reshape(-1,2),axis=1),axis=0,return_inverse=True)
            mesh=_split_marked_edges(project.case,mesh,edges,inverse.reshape(-1,3),np.ones(len(edges),dtype=bool),limit)
    return result
