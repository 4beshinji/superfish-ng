# SPDX-License-Identifier: Apache-2.0
"""Read-only deformation preparation for the local Project editor."""
import json
from .config import keys
from .project import Project, load_document, parse_json
from .curved_harmonic_deformation import deform_curved_project
from .curved_space import case_curved_space
from .mesh import make_mesh
from .mesh_input import mesh_from_dict


def _preview(project):
    from .gui import preview_document
    mesh=make_mesh(project.case) if project.mesh_data is None else mesh_from_dict(project.case,project.mesh_data)
    geometry=case_curved_space(project.case,mesh).geometry
    result=preview_document(project)
    active,interval,origin=project.case.acceleration_parameters
    result['rf_coordinates']=dict(active_length_m=active,voltage_interval_m=list(interval),
        phase_origin_m=origin,phase_origin_explicit=project.case.phase_origin_m is not None)
    # Edges are (start, end, midpoint), from the complete current P2 history.
    # The browser draws their exact quadratic Bezier curves, not their chords.
    result['native_boundary']=dict(edges_rz_m=geometry.points_rz_m[geometry.boundary_nodes].tolist(),
        cell_count=len(geometry.cell_nodes),node_count=len(geometry.points_rz_m),
        scope='complete native quadratic mesh boundary; no eigensolve')
    return result


def deformation_response(data):
    fields=['document','geometry_document','rf_coordinates','minimum_corner_angle_deg']
    keys(data,fields,fields,'curved deformation preview')
    project=load_document(data['document']) if isinstance(data['document'],str) else Project.from_dict(data['document'])
    geometry=parse_json(data['geometry_document']) if isinstance(data['geometry_document'],str) else data['geometry_document']
    target=deform_curved_project(project,geometry,rf_coordinates=data['rf_coordinates'],
        minimum_corner_angle_deg=data['minimum_corner_angle_deg'])
    return dict(source=_preview(project),target=_preview(target),
        serialized=json.dumps(target.to_dict(),indent=2,ensure_ascii=False,allow_nan=False)+'\n')
