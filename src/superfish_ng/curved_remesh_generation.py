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


def validate_generation_settings(data):
    """Return an independent copy of strict version 1 or 2 metadata.

    Version 2 declares final-native chord sizes and bounded P2 restrictions.
    This does not establish geometry, pattern ownership or mesh feasibility;
    the generation entry point must implement and check those separately.
    """
    required=('schema_version','max_chord_edge_m','max_chord_triangle_area_m2',
              'minimum_corner_angle_deg','max_triangles','max_rounds')
    history=('curved_refinement_levels','curved_refinement_steps')
    boundary=('boundary_policy','max_boundary_edges','max_seed_rounds')
    label='curved remesh generation settings'
    keys(data,required+history+boundary,('schema_version',),label)
    version=data['schema_version']
    if type(version) is not int or version not in (1,2):
        raise ValueError(f'{label} schema_version must be 1 or 2')
    if version==1:
        legacy=data
    else:
        keys(data,required+history+boundary,required+boundary,label)
        if data['boundary_policy']!='restrict_native_p2':
            raise ValueError('boundary_policy must be restrict_native_p2')
        for name in ('max_boundary_edges','max_seed_rounds'):
            integer(data[name],name)
        # The portable plan still uses its original schema and history grammar.
        legacy={key:value for key,value in data.items() if key not in boundary}
        legacy['schema_version']=1
    try:
        _settings(legacy)
    except OverflowError as exc:
        raise ValueError(f'{label}: numeric history value is not representable as finite float') from exc
    return deepcopy(data)


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

    Version 2 instead bounds the final native chords and permits subdivision
    of the original P2 boundary through a frozen restriction history.
    """
    if isinstance(settings,dict) and type(settings.get('schema_version')) is int and settings['schema_version']==2:
        return _generate_boundary_remesh_plan(project,validate_generation_settings(settings))
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


def _native_chord_mesh(space):
    from types import SimpleNamespace
    return SimpleNamespace(points=space.geometry.points_rz_m,triangles=space.geometry.cell_nodes[:,:3])


def _native_size_marks(working,space,edge_limit):
    """Measure final-native endpoint chords, retaining the original corners."""
    areas,edges,cell_edges,ends,delta,lengths=_measure(_native_chord_mesh(space))
    if not np.isfinite(areas).all() or not np.isfinite(lengths).all() or np.any(areas<=0) or np.any(lengths<=0):
        raise ValueError('boundary remesh requires finite positive native chord areas and edge lengths')
    marked=lengths>edge_limit*(1+1e-12)
    boundary=np.bincount(cell_edges.ravel(),minlength=len(edges))==1
    if working.boundary_max_edge_m is not None:
        marked |= boundary & ~np.all(ends[:,:,0]==0,axis=1) & (lengths>working.boundary_max_edge_m*(1+1e-12))
    if working.corner_max_edge_m is not None:
        vertices=np.asarray(working.contour.vertices_zr_m)[:,::-1]
        incoming=vertices-np.roll(vertices,1,axis=0);outgoing=np.roll(vertices,-1,axis=0)-vertices
        turn=np.abs(incoming[:,0]*outgoing[:,1]-incoming[:,1]*outgoing[:,0])
        corners=vertices[turn>1e-12*np.linalg.norm(incoming,axis=1)*np.linalg.norm(outgoing,axis=1)]
        for corner in corners:
            fraction=np.clip(np.sum((corner-ends[:,0])*delta,axis=1)/lengths**2,0,1)
            distance=np.linalg.norm(ends[:,0]+fraction[:,None]*delta-corner,axis=1)
            marked |= (distance<=working.corner_radius_m*(1+1e-12)) & (lengths>working.corner_max_edge_m*(1+1e-12))
    return areas,edges,cell_edges,marked


def _restriction_counts(space,step):
    """Predict exact child counts without allocating the refined geometry.

    The edge closure mirrors the unchanged marked restriction kernel. Actual
    counts are checked after construction so a future kernel change cannot
    silently bypass the generation budgets.
    """
    g=space.geometry;cells=len(g.cell_nodes);boundary=len(g.boundary_nodes)
    if step.kind=='uniform':return 4*cells,2*boundary
    requested=np.asarray(step.marked_cells)
    if any(i>=cells for i in step.marked_cells):
        raise ValueError('marked_cells refers outside the current new generation prefix')
    vertices=g.cell_nodes[:,:3]
    edges,inverse=np.unique(np.sort(vertices[:,[[0,1],[1,2],[2,0]]].reshape(-1,2),axis=1),axis=0,return_inverse=True)
    cell_edges=inverse.reshape(-1,3);marked=np.zeros(len(edges),dtype=bool)
    if step.split_pattern is None:
        marked[cell_edges[requested]]=True
        scale=float(np.max(np.ptp(g.points_rz_m,axis=0)))
        lengths=np.linalg.norm((g.points_rz_m[edges[:,1]]-g.points_rz_m[edges[:,0]])/scale,axis=1)
        longest=cell_edges[np.arange(cells),np.argmax(lengths[cell_edges],axis=1)]
        while True:
            required=longest[marked[cell_edges].any(axis=1)]
            if marked[required].all():break
            marked[required]=True
    else:
        from .curved_split_pattern import curved_topology_digest
        if step.split_pattern.parent_topology_sha256!=curved_topology_digest(space):
            raise ValueError('split pattern parent topology differs from the new generation prefix')
        lookup={tuple(map(int,edge)):i for i,edge in enumerate(edges)}
        if any(edge not in lookup for edge in step.split_pattern.split_edges):
            raise ValueError('split pattern names an absent parent edge')
        marked[[lookup[edge] for edge in step.split_pattern.split_edges]]=True
    boundary_edges=np.bincount(cell_edges.ravel(),minlength=len(edges))==1
    return cells+int(marked[cell_edges].sum()),boundary+int(np.count_nonzero(marked & boundary_edges))


def _generation_budget(counts,settings):
    for count,name in zip(counts,('max_triangles','max_boundary_edges')):
        if count>settings[name]:
            raise ValueError(f'boundary remesh needs {count} {name.removeprefix("max_")}, exceeding {name}={settings[name]}')


def _check_generation_space(space,settings,angle):
    from .curved_marked_refinement import _minimum_corner_angle
    _generation_budget((len(space.geometry.cell_nodes),len(space.geometry.boundary_nodes)),settings)
    actual=_minimum_corner_angle(space.geometry.local_maps)
    if actual<angle:
        raise ValueError(f'boundary remesh minimum corner angle {actual:.9g} is below required {angle:.9g}')


def _apply_generation_step(space,step,settings,angle):
    from dataclasses import replace
    from .curved_refinement import refine_curved_space
    from .curved_marked_refinement import refine_marked_curved_space
    counts=_restriction_counts(space,step)
    _generation_budget(counts,settings)
    if step.kind=='uniform':
        result=refine_curved_space(space)
    else:
        result=refine_marked_curved_space(space,list(step.marked_cells),max_triangles=settings['max_triangles'],
                minimum_corner_angle_deg=max(angle,step.minimum_corner_angle_deg),split_pattern=step.split_pattern)
        step=replace(step,split_pattern=result.split_pattern)
    actual=(len(result.space.geometry.cell_nodes),len(result.space.geometry.boundary_nodes))
    if actual!=counts:raise ValueError('boundary remesh restriction counts differ from the budget prediction')
    _check_generation_space(result.space,settings,angle)
    return result.space,step


def _generate_boundary_remesh_plan(project,settings):
    """Regenerate a seed and restrict its P2 maps to satisfy final sizes."""
    from dataclasses import replace
    from .mesh_controls import ContourMeshControls
    from .curved_space import case_curved_space
    from .curved_refinement_steps import CurvedRefinementStep,steps_from_dict
    from .te import is_te
    if not isinstance(project,Project):raise ValueError('curved remesh generation requires a Project')
    project=Project.from_dict(project.to_dict());case=project.case
    if case.curved_contour is None or case.geometry_order!=2 or project.sections is not None:
        raise ValueError('curved remesh generation requires unassembled native P2 geometry')
    if is_te(case):
        from .curved_same_domain_tracking import _te_end_conditions
        _te_end_conditions([case,case])
    elif project.reflect_full or any(tag not in ('axis','pec') for tag in case.curved_contour.edge_tags):
        raise ValueError('TM curved remesh generation requires direct closed PEC/axis geometry')
    case_limit=case.contour_mesh.max_triangles if case.contour_mesh is not None else 250000
    if settings['max_triangles']>case_limit:
        raise ValueError(f'curved remesh generation max_triangles exceeds original Case limit {case_limit}')
    original=make_mesh(case) if project.mesh_data is None else mesh_from_dict(case,project.mesh_data)
    working=_boundary_case(case,original)
    root_edges=len(working.contour.vertices_zr_m)
    if root_edges>settings['max_boundary_edges']:
        raise ValueError(f'max_boundary_edges={settings["max_boundary_edges"]} is below the {root_edges} original P2 intervals; root interval coalescing is unsupported')
    _generation_budget((root_edges-2,root_edges),settings)
    bounds=np.ptp(np.asarray(working.contour.vertices_zr_m),axis=0)
    diameter=2*math.hypot(*bounds);seed_area=diameter*diameter
    if not math.isfinite(diameter) or not math.isfinite(seed_area) or diameter<=0 or seed_area<=0:
        raise ValueError('boundary remesh seed dimensions must be finite and positive')
    angle=max(settings['minimum_corner_angle_deg'],case.contour_mesh.min_angle_deg) if case.contour_mesh else settings['minimum_corner_angle_deg']
    # These relaxed sizes exist only in the temporary seed-generation Case.
    # The original Case controls are restored and enforced on the final mesh.
    seed_controls=replace(case.contour_mesh,max_edge_m=diameter) if case.contour_mesh else ContourMeshControls(diameter,min_angle_deg=angle)
    # An implicit source must be materialized before relaxing working sizes;
    # regenerating it under those sizes would change its original intervals.
    seed_project=replace(project,mesh_data=mesh_to_dict(original) if project.mesh_data is None else project.mesh_data,
                        case=replace(case,contour_mesh=seed_controls,
                        boundary_max_edge_m=None,corner_max_edge_m=None,corner_radius_m=None))
    seed_settings=dict(schema_version=1,max_chord_edge_m=diameter,max_chord_triangle_area_m2=seed_area,
        minimum_corner_angle_deg=angle,max_triangles=settings['max_triangles'],max_rounds=settings['max_seed_rounds'],curved_refinement_levels=0)
    try:
        plan=generate_curved_remesh_plan(seed_project,seed_settings)
    except ValueError as exc:
        raise ValueError(f'boundary remesh seed failed within max_seed_rounds={settings["max_seed_rounds"]}: {exc}') from exc
    seed=remesh_curved_project(project,plan)
    current=case_curved_space(seed.case,mesh_from_dict(seed.case,seed.mesh_data))
    _check_generation_space(current,settings,angle)
    steps=[]
    if 'curved_refinement_steps' in settings:
        declared=steps_from_dict(settings['curved_refinement_steps'])
    else:
        declared=(CurvedRefinementStep('uniform') for _ in range(settings['curved_refinement_levels']))
    for index,step in enumerate(declared,1):
        try:current,frozen=_apply_generation_step(current,step,settings,angle)
        except ValueError as exc:raise ValueError(f'boundary remesh declared history step {index}: {exc}') from exc
        steps.append(frozen)
    edge_limit=min(settings['max_chord_edge_m'],case.contour_mesh.max_edge_m) if case.contour_mesh else settings['max_chord_edge_m']
    area_limit=settings['max_chord_triangle_area_m2']
    for iteration in range(settings['max_rounds']+1):
        areas,edges,cell_edges,marked=_native_size_marks(working,current,edge_limit)
        selected=np.flatnonzero(marked[cell_edges].any(axis=1) | (areas>area_limit*(1+1e-12)))
        if not len(selected):break
        if iteration==settings['max_rounds']:
            lengths=np.linalg.norm(current.geometry.points_rz_m[edges[:,1]]-current.geometry.points_rz_m[edges[:,0]],axis=1)
            raise ValueError(f'boundary remesh unmet after max_rounds={settings["max_rounds"]}: {len(selected)} cells violate edge/area/Case local sizes; maximum chord edge={lengths.max():.9g} m, area={areas.max():.9g} m2')
        step=CurvedRefinementStep('marked',tuple(map(int,selected)),angle)
        current,frozen=_apply_generation_step(current,step,settings,angle)
        steps.append(frozen)
    quality=contour_mesh_quality(_native_chord_mesh(current))
    if quality['min_angle_deg']<angle:
        raise ValueError(f'boundary remesh chord minimum angle {quality["min_angle_deg"]:.9g} is below required {angle:.9g}')
    if steps:
        del plan['curved_refinement_levels']
        plan['curved_refinement_steps']=[step.to_dict() for step in steps]
    # Existing remesh replays every prefix, including its geometry, constraints
    # and whole-interval boundary equality against the original full history.
    candidate=remesh_curved_project(project,plan)
    replay=case_curved_space(candidate.case,mesh_from_dict(candidate.case,candidate.mesh_data))
    _check_generation_space(replay,settings,angle)
    for name in ('points_rz_m','cell_nodes','boundary_nodes','boundary_curve_indices','boundary_parameters'):
        if not np.array_equal(getattr(current.geometry,name),getattr(replay.geometry,name)):
            raise ValueError('boundary remesh frozen history does not reproduce the generated geometry')
    areas,_,cell_edges,marked=_native_size_marks(working,replay,edge_limit)
    if marked.any() or np.any(areas>area_limit*(1+1e-12)):
        raise ValueError('boundary remesh replay violates final chord sizes')
    return plan


_GENERATION_DOCUMENT_FIELDS=('schema_version','document_type','source_project','settings','plan',
                             'validation','physical_error_bound')
_GENERATION_VALIDATION_FIELDS=('status','boundary_comparison','seed_triangle_count','prefix_triangle_counts',
    'prefix_boundary_edge_counts','final_max_chord_edge_m','final_max_chord_triangle_area_m2',
    'final_minimum_chord_angle_deg','final_minimum_corner_angle_deg')


def _generation_validation(project,settings,plan):
    """Reconstruct every declared prefix and measure the final native geometry.

    Version 1 retains its initial-chord size semantics. Its final measurements
    are observations, not a new application of version 2 acceptance gates.
    """
    from .curved_space import curved_space,case_curved_space
    from .curved_refinement import refine_curved_space
    from .curved_marked_refinement import refine_marked_curved_space,_minimum_corner_angle
    from .curved_same_domain_tracking import compare_quadratic_space_boundaries
    candidate=remesh_curved_project(project,plan)
    mesh=mesh_from_dict(candidate.case,candidate.mesh_data)
    current=curved_space(candidate.case,mesh)
    triangles=[len(current.geometry.cell_nodes)];boundaries=[len(current.geometry.boundary_nodes)]
    def steps():
        for _ in range(candidate.case.curved_refinement_levels):yield None
        yield from candidate.case.curved_refinement_steps
    for step in steps():
        if step is None or step.kind=='uniform':
            if 4*len(current.geometry.cell_nodes)>settings['max_triangles']:
                raise ValueError('generation validation uniform prefix exceeds max_triangles')
            current=refine_curved_space(current).space
        else:
            current=refine_marked_curved_space(current,list(step.marked_cells),max_triangles=settings['max_triangles'],
                    minimum_corner_angle_deg=step.minimum_corner_angle_deg,split_pattern=step.split_pattern).space
        triangles.append(len(current.geometry.cell_nodes));boundaries.append(len(current.geometry.boundary_nodes))
    original_mesh=make_mesh(project.case) if project.mesh_data is None else mesh_from_dict(project.case,project.mesh_data)
    original=case_curved_space(project.case,original_mesh)
    comparison=compare_quadratic_space_boundaries(project.case,original,candidate.case,current)
    areas,_,_,_,_,lengths=_measure(_native_chord_mesh(current))
    p=current.geometry.points_rz_m[current.geometry.cell_nodes[:,:3]]
    # Endpoint triangle angles are unsigned geometric measurements. The native
    # P2 maps carry their own positive-Jacobian and whole-boundary validation.
    angles=[np.arctan2(2*np.abs(areas),np.sum((p[:,(i+1)%3]-p[:,i])*(p[:,(i+2)%3]-p[:,i]),axis=1)) for i in range(3)]
    return dict(status='GEOMETRY_VERIFIED',boundary_comparison=comparison,seed_triangle_count=triangles[0],
        prefix_triangle_counts=triangles,prefix_boundary_edge_counts=boundaries,
        final_max_chord_edge_m=float(lengths.max()),final_max_chord_triangle_area_m2=float(np.abs(areas).max()),
        final_minimum_chord_angle_deg=float(np.rad2deg(np.min(angles))),
        final_minimum_corner_angle_deg=_minimum_corner_angle(current.geometry.local_maps))


def build_curved_remesh_generation(project,settings):
    """Build a self-contained, reproducible generation document without FEM."""
    if not isinstance(project,Project):raise ValueError('curved remesh generation requires a Project')
    project=Project.from_dict(project.to_dict())
    settings=validate_generation_settings(settings)
    plan=generate_curved_remesh_plan(project,settings)
    return dict(schema_version=1,document_type='curved_remesh_generation',source_project=project.to_dict(),
                settings=settings,plan=plan,validation=_generation_validation(project,settings,plan),physical_error_bound=None)


def _same_generation_values(actual,expected):
    """Allow JSON real-number spelling changes; integer IDs/bools stay strict."""
    if type(expected) is dict:
        return type(actual) is dict and actual.keys()==expected.keys() and all(_same_generation_values(actual[k],v) for k,v in expected.items())
    if type(expected) is list:
        return type(actual) is list and len(actual)==len(expected) and all(_same_generation_values(a,b) for a,b in zip(actual,expected))
    if isinstance(expected,float):
        return (isinstance(actual,float) or type(actual) is int) and actual==expected
    return type(actual) is type(expected) and actual==expected


def replay_curved_remesh_generation(document):
    """Regenerate from all saved inputs and compare the complete document.

    There is no budget override or partial replay. This verifies consistency,
    not the external authenticity of a coherently replaced set of inputs.
    """
    keys(document,_GENERATION_DOCUMENT_FIELDS,_GENERATION_DOCUMENT_FIELDS,'curved remesh generation document')
    if (type(document['schema_version']) is not int or document['schema_version']!=1
            or type(document['document_type']) is not str or document['document_type']!='curved_remesh_generation'):
        raise ValueError('curved remesh generation document requires schema_version=1 and its document_type')
    if document['physical_error_bound'] is not None:
        raise ValueError('curved remesh generation physical_error_bound must be null')
    keys(document['validation'],_GENERATION_VALIDATION_FIELDS,_GENERATION_VALIDATION_FIELDS,'curved remesh generation validation')
    expected=build_curved_remesh_generation(Project.from_dict(document['source_project']),document['settings'])
    if not _same_generation_values(document,expected):
        raise ValueError('curved remesh generation document differs from full reconstruction')
    return expected


def _write_generation_json(path,data):
    """Publish a complete JSON file atomically without replacing any path."""
    import json
    import os
    from pathlib import Path
    from tempfile import TemporaryDirectory
    path=Path(path)
    text=json.dumps(data,indent=2,allow_nan=False)+'\n'
    with TemporaryDirectory(prefix='.curved-remesh-',dir=path.parent) as directory:
        staged=Path(directory)/'document.json'
        staged.write_text(text,encoding='utf-8')
        os.link(staged,path)
