# SPDX-License-Identifier: Apache-2.0
"""Scalar native curve laws with harmonic motion and derived comparison maps."""
from copy import deepcopy
from dataclasses import replace
from .studies import Study
from .curved_harmonic_study import project_at_value
from .curved_tuning import refine_project
from .study_shape_tracking import comparison_mesh
from .saved_mode_tracking import validate_tracking_controls
from .project import Project


def shape_study(request,project):
    return Study(project,'curved_harmonic_sweep',request['parameter'],request['bounds'],
        parameter_unit=request['parameter_unit'],geometry_coefficients=request['geometry_coefficients'],
        rf_coordinates=request['rf_coordinates'],minimum_corner_angle_deg=request['minimum_corner_angle_deg'])


def validate_request(request,project):
    study=shape_study(request,project)
    scale=request['refinement_scale']
    if scale & (scale-1):
        raise ValueError('curved harmonic tune refinement_scale must be a power of two for quadratic restriction')
    controls=request['controls']
    if not isinstance(controls,dict) or controls.get('mapping')!='piecewise_remesh' or 'comparison_meshes' in controls:
        raise ValueError('curved harmonic tune requires piecewise_remesh controls without comparison_meshes; each pair is derived')
    first=project_at_value(study,request['bounds'][0])
    pair_controls(request,first,first)


def trial_project(request,project,value,phase):
    project=project_at_value(shape_study(request,project),value)
    return refine_project(request,project) if phase=='refinement' else project


def pair_controls(request,previous,current):
    """Use actual trial chord meshes with the original fixed comparison history.

    Final refinement changes the solved space, not the quadratic domain or the
    comparison partition. Both native fields are sampled in their own spaces.
    The accepted parent can be an earlier endpoint, not the preceding trial.
    """
    original=Project.from_dict(request['project']).case
    result=deepcopy(request['controls'])
    result['comparison_meshes']=[comparison_mesh(replace(project,case=replace(project.case,
        curved_refinement_steps=original.curved_refinement_steps,
        curved_refinement_levels=original.curved_refinement_levels))) for project in (previous,current)]
    validate_tracking_controls(result)
    return result
