# SPDX-License-Identifier: Apache-2.0
"""Declared affine Study geometry and maps between actual sampled values."""
from copy import deepcopy
from .curved_project_transform import relative_affine_map
from .saved_mode_tracking import validate_tracking_controls


def value_map(study,value):
    # Import lazily: the tuning refinement path also consumes ordinary Study.
    from .curved_tuning import trial_map
    return trial_map({'affine_coefficients':study.affine_coefficients},value)


def validate_affine_study(study):
    from .te import is_te
    case=study.project.case
    if case.curved_contour is None or case.geometry_order!=2 or study.project.sections is not None:
        raise ValueError('curved affine Study requires an unassembled native curved_contour with geometry_order=2')
    if is_te(case):
        raise ValueError('curved affine Study uses TM accelerating-coordinate conventions; TE shape sweeps require a separate coordinate contract')
    if not study.parameter.strip() or study.parameter_unit not in ('m','1'):
        raise ValueError('curved affine Study requires a nonempty parameter name and parameter_unit m or 1')
    if study.rf_coordinates not in ('fixed','axial'):
        raise ValueError('curved affine Study rf_coordinates must explicitly be fixed or axial')
    for value in study.values:value_map(study,value)


def pair_controls(study,control,previous_value,current_value):
    """Validate controls, deriving A(current) @ inverse(A(previous)) if declared.

    In adaptive execution the values may be inserted midpoints, so an original
    interval's map must never be reused for a smaller accepted or rejected pair.
    """
    result=deepcopy(control)
    if study.kind=='curved_affine_sweep':
        if not isinstance(result,dict) or result.get('mapping')!='affine_remesh' or 'affine_map' in result:
            raise ValueError('curved affine Study tracking requires affine_remesh controls without affine_map; each pair map is derived from its actual values')
        result['affine_map']=relative_affine_map(value_map(study,previous_value),value_map(study,current_value))
    validate_tracking_controls(result)
    return result
