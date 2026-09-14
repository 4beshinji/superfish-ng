# SPDX-License-Identifier: Apache-2.0
"""Move a numbered curved mesh using declared boundary parameter correspondence.

The original chord mesh carries a planar P1 Laplace extension of the boundary
*displacement*. This is a mesh construction, not an electromagnetic solve or a
claim that the chosen correspondence identifies physical mode branches.
"""
from copy import deepcopy
from dataclasses import replace
import math
import warnings
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve, MatrixRankWarning
from .config import Case
from .project import Project
from .mesh import make_mesh, element_geometry
from .mesh_input import mesh_from_dict, mesh_to_dict
from .curved_space import curved_space, case_curved_space
from .curved_marked_refinement import _minimum_corner_angle


def _harmonic_displacement(mesh, boundary_nodes, boundary_positions):
    """Minimize integral |grad d|^2 on the original chord mesh, with fixed d_B.

    Affine displacement is exactly in this P1 space and has zero weak interior
    Laplacian. Extending the new positions with graph averaging would not have
    that patch property on an arbitrary source triangulation.
    """
    scale=float(np.max(np.ptp(mesh.points,axis=0)))
    normalized=replace(mesh,points=(mesh.points-mesh.points[0])/scale)
    _,det,grad=element_geometry(normalized)
    local=.5*det[:,None,None]*np.einsum('tik,tjk->tij',grad,grad)
    rows=np.repeat(mesh.triangles,3,axis=1).ravel()
    cols=np.tile(mesh.triangles,(1,3)).ravel()
    stiffness=coo_matrix((local.ravel(),(rows,cols)),shape=(len(mesh.points),)*2).tocsr()
    interior=np.setdiff1d(np.arange(len(mesh.points)),boundary_nodes)
    displacement=np.zeros_like(mesh.points)
    displacement[boundary_nodes]=(boundary_positions-mesh.points[boundary_nodes])/scale
    if len(interior):
        block=stiffness[interior][:,interior]
        rhs=-stiffness[interior][:,boundary_nodes]@displacement[boundary_nodes]
        with warnings.catch_warnings():
            warnings.simplefilter('error',MatrixRankWarning)
            try:displacement[interior]=spsolve(block,rhs)
            except (MatrixRankWarning,RuntimeError) as exc:
                raise ValueError('harmonic mesh displacement could not be solved on the original mesh') from exc
        residual=block@displacement[interior]-rhs
        bound=abs(block)@abs(displacement[interior])+abs(rhs)
        if np.max(abs(residual))>1e-11*max(float(np.max(bound)),np.finfo(float).tiny):
            raise ValueError('harmonic mesh displacement algebraic residual is unresolved')
    points=mesh.points+scale*displacement
    points[boundary_nodes]=boundary_positions
    if not np.isfinite(points).all():raise ValueError('harmonic mesh displacement exceeds finite coordinates')
    return points


def _boundary_positions(mesh, geometry, approximation):
    # Original mesh vertices may lie inside a chord, rather than on the analytic
    # primitive. Map their primitive fractions onto the corresponding *target
    # chord*. Native P2 lifting then reconstructs the analytic boundary nodes.
    vertices=np.asarray(approximation.contour.vertices_zr_m)[:,::-1]
    ends=np.roll(vertices,-1,axis=0)
    owners=np.asarray(approximation.segment_curve_indices)
    intervals=np.asarray(approximation.segment_parameter_intervals)
    tolerance=512*np.finfo(float).eps*float(np.max(np.ptp(vertices,axis=0)))
    assigned={}
    for edge,owner,parameters in zip(mesh.boundary_edges,geometry.boundary_curve_indices,geometry.boundary_parameters):
        segments=np.flatnonzero(owners==owner)
        for node,parameter in zip(edge,parameters):
            index=min(int(np.searchsorted(intervals[segments,1],parameter,side='left')),len(segments)-1)
            segment=segments[index];low,high=intervals[segment]
            fraction=float(np.clip((parameter-low)/(high-low),0.,1.))
            position=(1-fraction)*vertices[segment]+fraction*ends[segment]
            if int(node) in assigned and np.linalg.norm(assigned[int(node)]-position)>tolerance:
                raise ValueError('declared curve correspondence disagrees at a shared boundary vertex')
            assigned.setdefault(int(node),position)
    nodes=np.array(sorted(assigned),dtype=int)
    return nodes,np.array([assigned[int(node)] for node in nodes])


def _prefixes(case):
    for level in range(case.curved_refinement_levels+1):
        yield replace(case,curved_refinement_levels=level,curved_refinement_steps=())
    for end in range(1,len(case.curved_refinement_steps)+1):
        yield replace(case,curved_refinement_steps=case.curved_refinement_steps[:end])


def deform_curved_project(project, target_geometry, *, rf_coordinates, minimum_corner_angle_deg):
    """Return a portable Project with the same numbered mesh and split history.

    Target geometry is a native Case geometry object. Each curve index, edge tag
    and increasing primitive fraction declares the boundary correspondence. The
    original chord counts are mandatory; omitted counts are filled explicitly.
    All marked split patterns must already be frozen. New analytic curves are
    lifted only on the original mesh, then restricted through the old history.

    RF coordinates are explicitly fixed, or scaled with total axis length via
    'axis_fraction'. Other Case/Project controls are retained. A requested corner
    angle floor applies to every target stage, in addition to saved step limits.
    Every stage checks positive quadratic maps, all edges, boundary and budgets.
    Invalid motion is rejected; there is no smoothing, remeshing or field fitting.
    """
    if not isinstance(project,Project):raise ValueError('curved deformation requires a Project')
    project=Project.from_dict(project.to_dict());case=project.case
    from .te import is_te
    if (case.curved_contour is None or case.geometry_order!=2 or project.sections is not None
            or project.reflect_full or any(t not in ('axis','pec') for t in case.curved_contour.edge_tags)):
        raise ValueError('curved deformation requires direct, unassembled native P2 closed PEC/axis geometry')
    if is_te(case) and rf_coordinates!='fixed':
        raise ValueError('TE curved geometry requires fixed RF metadata; accelerating coordinates are not applicable')
    if rf_coordinates not in ('fixed','axis_fraction'):
        raise ValueError('curved deformation rf_coordinates must explicitly be fixed or axis_fraction')
    try:quality_valid=type(minimum_corner_angle_deg) in (int,float) and math.isfinite(minimum_corner_angle_deg) and 0<minimum_corner_angle_deg<60
    except OverflowError:quality_valid=False
    if not quality_valid:raise ValueError('minimum_corner_angle_deg must be finite and strictly between 0 and 60')
    if any(s.kind=='marked' and s.split_pattern is None for s in case.curved_refinement_steps):
        raise ValueError('curved deformation requires frozen marked split choices; run freeze-curved-refinement first')
    if not isinstance(target_geometry,dict) or target_geometry.get('type')!='curved_contour':
        raise ValueError('target_geometry must be a native curved_contour geometry object')
    old=case.curved_contour.linearize(case.curve_chord_tolerance_m,max_segments=case.curve_chord_max_segments,
                                    segments_per_curve=case.curve_segments_per_curve)
    counts=np.bincount(old.segment_curve_indices,minlength=len(case.curved_contour.curves)).tolist()
    geometry=deepcopy(target_geometry)
    supplied=geometry.get('segments_per_curve',counts)
    if not isinstance(supplied,list) or any(type(n) is not int for n in supplied) or supplied!=counts:
        raise ValueError('target geometry must preserve the original segments_per_curve; changing initial mesh partitions requires separate correspondence')
    geometry['segments_per_curve']=counts
    if not isinstance(geometry.get('curves'),list) or len(geometry['curves'])!=len(case.curved_contour.curves) or geometry.get('edge_tags')!=list(case.curved_contour.edge_tags):
        raise ValueError('target geometry must preserve curve count and ordered edge tags; index and parameter fraction declare correspondence')
    raw=case.to_dict();raw['geometry']=geometry
    # Obtain the new axis length without first imposing old explicit RF limits
    # on a shorter target. Final RF validation remains in Case.from_dict below.
    from .curved_contour import CurvedContour
    contour_keys=('curves','edge_tags','join_tolerance_m','minimum_gap_m','minimum_meridional_radius_m')
    target_contour=CurvedContour.from_dict({k:v for k,v in geometry.items() if k in contour_keys})
    length=max(max(c.start_zr_m[0],c.end_zr_m[0]) for c,t in zip(target_contour.curves,target_contour.edge_tags) if t=='axis')
    if not is_te(case):
        active,interval,origin=case.acceleration_parameters
        factor=length/case.length if rf_coordinates=='axis_fraction' else 1.
        raw['rf'].update(active_length_m=active*factor,voltage_interval_m=[v*factor for v in interval])
        if case.phase_origin_m is not None:raw['rf']['phase_origin_m']=origin*factor
    target=Case.from_dict(raw)
    source_mesh=make_mesh(case) if project.mesh_data is None else mesh_from_dict(case,project.mesh_data)
    limit=case.contour_mesh.max_triangles if case.contour_mesh is not None else 250000
    if len(source_mesh.triangles)>limit:raise ValueError(f'curved deformation source mesh exceeds max_triangles={limit}')
    source_base=curved_space(case,source_mesh)
    approximation=target.curved_contour.linearize(target.curve_chord_tolerance_m,max_segments=target.curve_chord_max_segments,
                                                  segments_per_curve=target.curve_segments_per_curve)
    nodes,positions=_boundary_positions(source_mesh,source_base.geometry,approximation)
    data=mesh_to_dict(source_mesh);data['points']=_harmonic_displacement(source_mesh,nodes,positions).tolist()
    result=Project.from_dict(dict(project.to_dict(),project_version=2,case=target.to_dict(),mesh_data=data))
    target_mesh=mesh_from_dict(target,result.mesh_data)
    for index,(old_case,new_case) in enumerate(zip(_prefixes(case),_prefixes(target))):
        previous=case_curved_space(old_case,source_mesh);current=case_curved_space(new_case,target_mesh)
        for key in ('cell_nodes','boundary_nodes','boundary_curve_indices'):
            if not np.array_equal(getattr(previous.geometry,key),getattr(current.geometry,key)):
                raise ValueError(f'curved deformation stage {index} changes numbered {key}')
        if not np.allclose(previous.geometry.boundary_parameters,current.geometry.boundary_parameters,rtol=0.,atol=512*np.finfo(float).eps):
            raise ValueError(f'curved deformation stage {index} changes declared boundary fractions')
        angle=_minimum_corner_angle(current.geometry.local_maps)
        if angle<minimum_corner_angle_deg:
            raise ValueError(f'curved deformation stage {index} minimum corner angle {angle:.9g} is below minimum_corner_angle_deg={minimum_corner_angle_deg}')
    return result
