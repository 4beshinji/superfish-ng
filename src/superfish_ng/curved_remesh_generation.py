# SPDX-License-Identifier: Apache-2.0
"""Regenerate an interior triangulation while retaining the native P2 boundary."""
from copy import deepcopy
import math
import numpy as np
from .config import Case,keys,integer
from .project import Project
from .contour import Contour
from .mesh import make_mesh
from .mesh_input import mesh_from_dict,mesh_to_dict
from .contour_mesh import (triangulate_contour,contour_mesh_quality,improve_contour_angles,
                           smooth_contour_interior,_split_marked_edges)
from .curved_project_remesh import validate_remesh_plan,remesh_curved_project


def _settings(data):
    required=('schema_version','max_chord_edge_m','max_chord_triangle_area_m2',
              'minimum_corner_angle_deg','max_triangles','max_rounds')
    history=('curved_refinement_levels','curved_refinement_steps')
    keys(data,required+history,required,'curved remesh generation settings')
    plan={k:deepcopy(v) for k,v in data.items() if k in ('schema_version','minimum_corner_angle_deg')+history}
    plan['source_mesh']={}
    validate_remesh_plan(plan)
    for name in ('max_chord_edge_m','max_chord_triangle_area_m2'):
        value=data[name]
        try:valid=type(value) in (int,float) and math.isfinite(value) and value>0
        except OverflowError:valid=False
        if not valid:raise ValueError(f'{name} must be finite and positive')
    for name in ('max_triangles','max_rounds'):integer(data[name],name)
    return plan


def _boundary_case(case,mesh):
    """Canonicalize only the boundary; old interior coordinates/IDs are unused."""
    graph={};tags={}
    for edge,tag in zip(mesh.boundary_edges,mesh.boundary_tags):
        a,b=map(int,edge);graph.setdefault(a,[]).append(b);graph.setdefault(b,[]).append(a)
        tags[tuple(sorted((a,b)))]=str(tag)
    start=next(i for i in graph if np.array_equal(mesh.points[i],[0.,0.]))
    current=start;previous=None;cycle=[];ordered_tags=[]
    while True:
        cycle.append(current)
        choices=[i for i in graph[current] if i!=previous]
        following=min(choices,key=lambda i:tuple(mesh.points[i]))
        ordered_tags.append(tags[tuple(sorted((current,following)))])
        previous,current=current,following
        if current==start:break
    contour=Contour(tuple(tuple(map(float,mesh.points[i,::-1])) for i in cycle),tuple(ordered_tags))
    return Case((),contour=contour,contour_mesh=case.contour_mesh,
                boundary_max_edge_m=case.boundary_max_edge_m,corner_max_edge_m=case.corner_max_edge_m,
                corner_radius_m=case.corner_radius_m)


def _measure(mesh):
    p=mesh.points[mesh.triangles];u,v=p[:,1]-p[:,0],p[:,2]-p[:,0]
    areas=(u[:,0]*v[:,1]-u[:,1]*v[:,0])/2
    edges,inverse=np.unique(np.sort(mesh.triangles[:,[[0,1],[1,2],[2,0]]].reshape(-1,2),axis=1),axis=0,return_inverse=True)
    ends=mesh.points[edges];delta=ends[:,1]-ends[:,0];lengths=np.linalg.norm(delta,axis=1)
    return areas,edges,inverse.reshape(-1,3),ends,delta,lengths


def _size_marks(case,mesh,edge_limit):
    areas,edges,cell_edges,ends,delta,lengths=_measure(mesh)
    marked=lengths>edge_limit*(1+1e-12)
    boundary=np.bincount(cell_edges.ravel(),minlength=len(edges))==1
    if case.boundary_max_edge_m is not None:
        marked |= boundary & ~np.all(ends[:,:,0]==0,axis=1) & (lengths>case.boundary_max_edge_m*(1+1e-12))
    if case.corner_max_edge_m is not None:
        vertices=np.asarray(case.contour.vertices_zr_m)[:,::-1]
        incoming=vertices-np.roll(vertices,1,axis=0);outgoing=np.roll(vertices,-1,axis=0)-vertices
        turn=np.abs(incoming[:,0]*outgoing[:,1]-incoming[:,1]*outgoing[:,0])
        corners=vertices[turn>1e-12*np.linalg.norm(incoming,axis=1)*np.linalg.norm(outgoing,axis=1)]
        for corner in corners:
            fraction=np.clip(np.sum((corner-ends[:,0])*delta,axis=1)/lengths**2,0,1)
            distance=np.linalg.norm(ends[:,0]+fraction[:,None]*delta-corner,axis=1)
            marked |= (distance<=case.corner_radius_m*(1+1e-12)) & (lengths>case.corner_max_edge_m*(1+1e-12))
    if np.any(marked & boundary):
        raise ValueError('fixed quadratic boundary conflicts with requested chord edge/Case boundary or corner size; increase the requested size or prepare another original boundary explicitly')
    return areas,edges,cell_edges,marked


def _insert_centroids(case,mesh,selected,limit):
    if len(mesh.triangles)+2*len(selected)>limit:
        raise ValueError(f'curved remesh generation exceeds max_triangles={limit}')
    chosen=set(map(int,selected));points=mesh.points.tolist();triangles=[]
    for cell,tri in enumerate(mesh.triangles):
        if cell not in chosen:triangles.append(tri.tolist());continue
        a,b,c=map(int,tri);node=len(points);points.append(mesh.points[tri].mean(axis=0).tolist())
        triangles.extend(((a,b,node),(b,c,node),(c,a,node)))
    data=mesh_to_dict(mesh);data.update(points=points,triangles=[list(t) for t in triangles])
    return mesh_from_dict(case,data)


def _check_new_history_budget(project,plan,settings):
    """Apply the generation budget to new prefixes, allowing a larger old mesh."""
    from .curved_space import case_curved_space
    from .frozen_curved_refinement import freeze_curved_refinement
    raw=project.to_dict();raw.update(project_version=2,mesh_data=deepcopy(plan['source_mesh']))
    mesh_settings=raw['case']['mesh']
    for name in ('curved_refinement_levels','curved_refinement_steps'):
        mesh_settings.pop(name,None)
        if name in plan:mesh_settings[name]=deepcopy(plan[name])
    mesh_settings.setdefault('contour_mesh',dict(max_edge_m=settings['max_chord_edge_m']))['max_triangles']=settings['max_triangles']
    candidate=Project.from_dict(raw)
    if any(step.kind=='marked' for step in candidate.case.curved_refinement_steps):
        candidate=freeze_curved_refinement(candidate)
        plan['curved_refinement_steps']=[step.to_dict() for step in candidate.case.curved_refinement_steps]
    case_curved_space(candidate.case,mesh_from_dict(candidate.case,candidate.mesh_data))


def generate_curved_remesh_plan(project,settings):
    """Return a fully checked plan accepted by remesh-curved-project/Study v4.

    Start again from the original boundary polygon, discarding every old
    interior vertex and triangle. Bounded internal edge subdivision, centroid
    insertion, angle-improving flips and smoothing obey chord size/area limits.
    Boundary vertices/edges/tags never move or split. The final native P2 maps
    and every new history prefix must pass existing remesh checks; a failed
    heuristic is an error, never a quality/physics certificate or a partial plan.
    """
    plan=_settings(settings)
    if not isinstance(project,Project):raise ValueError('curved remesh generation requires a Project')
    project=Project.from_dict(project.to_dict());case=project.case
    from .te import is_te
    if case.curved_contour is None or case.geometry_order!=2 or project.sections is not None:
        raise ValueError('curved remesh generation requires unassembled native P2 geometry')
    if is_te(case):
        from .curved_same_domain_tracking import _te_end_conditions
        _te_end_conditions([case,case])
    elif project.reflect_full or any(tag not in ('axis','pec') for tag in case.curved_contour.edge_tags):
        raise ValueError('TM curved remesh generation requires direct closed PEC/axis geometry')
    original=make_mesh(case) if project.mesh_data is None else mesh_from_dict(case,project.mesh_data)
    case_limit=case.contour_mesh.max_triangles if case.contour_mesh is not None else 250000
    limit=settings['max_triangles']
    if limit>case_limit:raise ValueError(f'curved remesh generation max_triangles exceeds original Case limit {case_limit}')
    working=_boundary_case(case,original)
    if len(working.contour.vertices_zr_m)-2>limit:
        raise ValueError(f'curved remesh generation boundary triangulation exceeds max_triangles={limit}')
    mesh=triangulate_contour(working)
    edge_limit=min(settings['max_chord_edge_m'],case.contour_mesh.max_edge_m) if case.contour_mesh else settings['max_chord_edge_m']
    chord_floor=max(settings['minimum_corner_angle_deg'],case.contour_mesh.min_angle_deg) if case.contour_mesh else settings['minimum_corner_angle_deg']
    area_limit=settings['max_chord_triangle_area_m2'];last_reason='size/area limits'
    for round_index in range(settings['max_rounds']+1):
        areas,edges,cell_edges,marked=_size_marks(working,mesh,edge_limit)
        if not marked.any():
            mesh=improve_contour_angles(working,mesh,max_edge_m=edge_limit)
            mesh=smooth_contour_interior(working,mesh,edge_limit)
            areas,edges,cell_edges,marked=_size_marks(working,mesh,edge_limit)
        oversized=np.flatnonzero(areas>area_limit*(1+1e-12))
        if not marked.any() and not len(oversized):
            quality=contour_mesh_quality(mesh)
            if quality['min_angle_deg']>=chord_floor:
                plan['source_mesh']=mesh_to_dict(mesh)
                _check_new_history_budget(project,plan,settings)
                # No catch: invalid P2 maps/geometry/history must remain visible.
                candidate=remesh_curved_project(project,plan)
                if candidate.case.curved_refinement_steps:
                    plan['curved_refinement_steps']=[s.to_dict() for s in candidate.case.curved_refinement_steps]
                return plan
            last_reason=f'chord minimum angle {quality["min_angle_deg"]:.9g} < {chord_floor:.9g}'
            p=mesh.points[mesh.triangles];u,v=p[:,1]-p[:,0],p[:,2]-p[:,0]
            twice=u[:,0]*v[:,1]-u[:,1]*v[:,0]
            angles=np.min([np.arctan2(twice,np.sum((p[:,(i+1)%3]-p[:,i])*(p[:,(i+2)%3]-p[:,i]),axis=1)) for i in range(3)],axis=0)
            oversized=np.flatnonzero(np.rad2deg(angles)<chord_floor)
        if round_index==settings['max_rounds']:
            raise ValueError(f'curved remesh generation unmet after max_rounds={settings["max_rounds"]}: {last_reason}; revise limits or supply an explicit plan')
        if marked.any():mesh=_split_marked_edges(working,mesh,edges,cell_edges,marked,limit)
        elif len(oversized):mesh=_insert_centroids(working,mesh,oversized,limit)
    raise AssertionError('unreachable remesh generation state')
