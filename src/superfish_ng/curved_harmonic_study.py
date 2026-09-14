# SPDX-License-Identifier: Apache-2.0
"""Finite laws for native curve coordinates, evaluated from the original Project."""
import math
import re
from .curved_harmonic_deformation import deform_curved_project


_CURVE_PATH=re.compile(r'/curves/(0|[1-9][0-9]*)/(?:((?:start|end|center)_zr_m|semiaxes_m)/(0|1)|(rotation_rad|start_rad|sweep_rad|start_parameter|end_parameter))\Z')


def curve_numeric_leaf(geometry,path):
    """Resolve only existing continuous primitive leaves, never topology/settings."""
    match=_CURVE_PATH.fullmatch(path) if type(path) is str else None
    if match is None:raise ValueError(f'geometry law path {path!r} must name an existing continuous numeric /curves/index/... field')
    try:
        parent=geometry['curves'][int(match[1])]
        key=match[4]
        if key is None:parent=parent[match[2]];key=int(match[3])
        if type(parent[key]) not in (int,float):raise KeyError(key)
    except (KeyError,IndexError,TypeError,ValueError) as exc:
        raise ValueError(f'geometry law path {path!r} does not name an existing numeric primitive field') from exc
    return parent,key


def geometry_at_value(study,value):
    """Set numeric primitive leaves simultaneously, in their native SI units.

    Paths cannot change curve count/type/order, a discrete hyperbola branch,
    boundary tags, chord/quality budgets, solver settings or refinement choices.
    """
    geometry=study.project.case.to_dict()['geometry']
    laws=study.geometry_coefficients
    if type(laws) is not dict or not laws:
        raise ValueError('geometry_coefficients requires a nonempty object of curve paths and ascending-power arrays')
    active=False
    for path,coefficients in laws.items():
        parent,key=curve_numeric_leaf(geometry,path)
        if type(coefficients) is not list or not coefficients:
            raise ValueError(f'geometry law {path}: coefficients must be a nonempty array in ascending power order')
        for coefficient in coefficients:
            try:finite=type(coefficient) in (int,float) and math.isfinite(coefficient)
            except OverflowError:finite=False
            if not finite:raise ValueError(f'geometry law {path}: coefficients must be finite numbers')
        active=active or any(c!=0 for c in coefficients[1:])
        try:
            mapped=coefficients[-1]
            for coefficient in reversed(coefficients[:-1]):mapped=mapped*value+coefficient
            finite=math.isfinite(mapped)
        except OverflowError:finite=False
        if not finite:raise ValueError(f'geometry law {path} exceeds finite range at the requested value')
        parent[key]=mapped
    if not active:raise ValueError('at least one geometry coefficient law must be nonconstant')
    return geometry


def validate_harmonic_study(study):
    from .te import is_te
    project=study.project;case=project.case
    if case.curved_contour is None or case.geometry_order!=2 or project.sections is not None:
        raise ValueError('curved harmonic Study requires unassembled native P2 geometry')
    if is_te(case):
        from .curved_same_domain_tracking import _te_end_conditions
        _te_end_conditions([case,case])
    elif project.reflect_full or any(t not in ('axis','pec') for t in case.curved_contour.edge_tags):
        raise ValueError('curved harmonic Study requires direct, unassembled native P2 closed PEC/axis geometry')
    if any(step.kind=='marked' and step.split_pattern is None for step in case.curved_refinement_steps):
        raise ValueError('curved harmonic Study requires frozen marked choices; run freeze-curved-refinement first')
    if not study.parameter.strip() or study.parameter_unit not in ('m','1'):
        raise ValueError('curved harmonic Study requires a nonempty parameter name and parameter_unit m or 1')
    if is_te(case) and study.rf_coordinates!='fixed':
        raise ValueError('TE curved geometry requires fixed RF metadata; accelerating coordinates are not applicable')
    if study.rf_coordinates not in ('fixed','axis_fraction'):
        raise ValueError('curved harmonic Study rf_coordinates must explicitly be fixed or axis_fraction')
    floor=study.minimum_corner_angle_deg
    try:valid=type(floor) in (int,float) and math.isfinite(floor) and 0<floor<60
    except OverflowError:valid=False
    if not valid:raise ValueError('minimum_corner_angle_deg must be finite and strictly between 0 and 60')
    for value in study.values:geometry_at_value(study,value)


def project_at_value(study,value):
    return deform_curved_project(study.project,geometry_at_value(study,value),
        rf_coordinates=study.rf_coordinates,minimum_corner_angle_deg=study.minimum_corner_angle_deg)
