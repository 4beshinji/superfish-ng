# SPDX-License-Identifier: Apache-2.0
"""Tracking controls derived from the actual compared Study point geometries."""
from copy import deepcopy
from .curved_affine_study import pair_controls as affine_pair_controls
from .curved_harmonic_study import project_at_value
from .saved_mode_tracking import validate_tracking_controls


def comparison_mesh(project):
    result=dict(schema_version=2,source_mesh=deepcopy(project.mesh_data))
    case=project.case
    if case.curved_refinement_steps:
        result['curved_refinement_steps']=[step.to_dict() for step in case.curved_refinement_steps]
    else:result['curved_refinement_levels']=case.curved_refinement_levels
    return result


def pair_controls(study,control,previous_value,current_value,*,projects=None):
    """Use each sampled geometry, including midpoints, with original thresholds.

    Internal callers may supply their already validated pair of Projects to avoid
    repeating mesh construction. These are the exact declared points from Study,
    not independent user-supplied comparison meshes.
    """
    if study.kind not in ('curved_harmonic_sweep','curved_remesh_sweep'):
        return affine_pair_controls(study,control,previous_value,current_value)
    result=deepcopy(control)
    if not isinstance(result,dict) or result.get('mapping')!='piecewise_remesh' or 'comparison_meshes' in result:
        raise ValueError('curved harmonic Study tracking requires piecewise_remesh controls without comparison_meshes; each pair is derived from its actual values')
    # Replacement FEM meshes have independent numbering and histories. Only the
    # original Project supplies the correspondence, evaluated at actual values.
    if projects is None or study.kind=='curved_remesh_sweep':projects=[project_at_value(study,x) for x in (previous_value,current_value)]
    result['comparison_meshes']=[comparison_mesh(project) for project in projects]
    validate_tracking_controls(result)
    return result
