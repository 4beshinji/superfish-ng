# SPDX-License-Identifier: Apache-2.0
"""Version-four scalar affine tuning of native quadratic curved projects."""
import math
from copy import deepcopy
from .config import keys
from .curved_project_transform import transform_curved_project,relative_affine_map
from .affine_remesh_tracking import validate_affine_map
from .saved_mode_tracking import validate_tracking_controls
from .studies import Study


IDENTITY=dict(radial_scale=1.,axial_scale=1.,axial_shear=0.)


def trial_map(request,value):
    laws=request['affine_coefficients'];names=tuple(IDENTITY)
    keys(laws,names,names,'affine_coefficients')
    result={};active=False
    for name in names:
        coefficients=laws[name]
        if type(coefficients) is not list or not coefficients:
            raise ValueError('affine coefficients must be nonempty arrays in ascending power order')
        for coefficient in coefficients:
            try:finite=type(coefficient) in (int,float) and math.isfinite(coefficient)
            except OverflowError:finite=False
            if not finite:raise ValueError('affine coefficients must be finite numbers')
        active=active or any(c!=0 for c in coefficients[1:])
        mapped=coefficients[-1]
        for coefficient in reversed(coefficients[:-1]):mapped=mapped*value+coefficient
        result[name]=mapped
    if not active:raise ValueError('at least one affine coefficient law must be nonconstant')
    validate_affine_map(result)
    return result


def validate_request(request,project):
    if project.case.curved_contour is None or project.case.geometry_order!=2:
        raise ValueError('curved tune requires native curved_contour with geometry_order=2')
    if project.sections is not None:
        raise ValueError('curved tune requires an unassembled native curved project')
    if request['rf_coordinates'] not in ('fixed','axial'):
        raise ValueError('curved tune rf_coordinates must be fixed or axial')
    scale=request['refinement_scale']
    if scale & (scale-1):
        raise ValueError('curved tune refinement_scale must be a power of two for uniform quadratic restriction')
    controls=request['controls']
    if not isinstance(controls,dict) or controls.get('mapping')!='affine_remesh' or 'affine_map' in controls:
        raise ValueError('curved tune requires affine_remesh controls without affine_map; each trial map is derived')
    validate_tracking_controls(dict(controls,affine_map=IDENTITY))


def trial_project(request,project,value,phase):
    project=transform_curved_project(project,trial_map(request,value),rf_coordinates=request['rf_coordinates'])
    return refine_project(request,project) if phase=='refinement' else project


def refine_project(request,project):
    """Restrict the accepted quadratic domain without repeating shape motion."""
    levels=request['refinement_scale'].bit_length()-1
    if project.case.curved_refinement_steps:
        parameter='additional_uniform_refinements';values=[0,levels]
    else:
        parameter='/case/mesh/curved_refinement_levels'
        first=project.case.curved_refinement_levels;values=[first,first+levels]
    return Study(project,'fixed_geometry_convergence',parameter,values).projects()[1]


def pair_controls(request,previous_value,current_value):
    return dict(deepcopy(request['controls']),affine_map=relative_affine_map(
        trial_map(request,previous_value),trial_map(request,current_value)))
