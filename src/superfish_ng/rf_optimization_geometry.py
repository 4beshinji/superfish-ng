# SPDX-License-Identifier: Apache-2.0
"""Unit-declared multivariate curve dimensions for native RF design searches."""
import math
from .config import keys
from .rf_design import _number
from .curved_harmonic_study import curve_numeric_leaf
from .curved_harmonic_deformation import deform_curved_project


def geometry_at_values(request,project,values):
    variables=request['variables'];count=len(variables)
    if (type(values) is not list or len(values)!=count or
            any(not _number(x) or not v['lower']<=x<=v['upper'] for x,v in zip(values,variables))):
        raise ValueError('geometry values must provide one finite in-bounds value per declared variable')
    laws=request['geometry_terms']
    if type(laws) is not dict or not laws:raise ValueError('geometry_terms must map numeric curve paths to nonempty monomial lists')
    geometry=project.case.to_dict()['geometry'];active=set()
    for path,terms in laws.items():
        parent,key=curve_numeric_leaf(geometry,path)
        if type(terms) is not list or not terms:raise ValueError(f'geometry terms for {path} must be a nonempty list')
        seen=set();summands=[]
        for term in terms:
            keys(term,('coefficient','powers'),('coefficient','powers'),'geometry monomial')
            coefficient=term['coefficient'];powers=term['powers']
            if not _number(coefficient):raise ValueError('geometry monomial coefficient must be finite')
            if type(powers) is not list or len(powers)!=count or any(type(p) is not int or p<0 for p in powers):
                raise ValueError('monomial powers must give one nonnegative integer per variable, in declaration order')
            signature=tuple(powers)
            if signature in seen:raise ValueError(f'duplicate monomial powers for geometry path {path}')
            seen.add(signature)
            if coefficient!=0:active.update(i for i,p in enumerate(powers) if p)
            try:
                product=float(coefficient)
                for x,power in zip(values,powers):product*=float(x)**power
                finite=math.isfinite(product)
            except (OverflowError,ValueError):finite=False
            if not finite:raise ValueError(f'geometry monomial for {path} exceeds finite range at the trial values')
            summands.append(product)
        try:mapped=math.fsum(summands)
        except OverflowError:raise ValueError(f'geometry law for {path} exceeds finite range') from None
        if not math.isfinite(mapped):raise ValueError(f'geometry law for {path} exceeds finite range')
        parent[key]=mapped
    if active!=set(range(count)):raise ValueError('every design variable must occur in a nonzero nonconstant geometry term')
    return geometry


def validate_geometry_request(request,project):
    floor=request['minimum_corner_angle_deg']
    if not _number(floor) or not 0<floor<60:raise ValueError('minimum_corner_angle_deg must be finite and strictly between 0 and 60')
    if request['rf_coordinates'] not in ('fixed','axis_fraction'):
        raise ValueError('geometry RF optimization rf_coordinates must be fixed or axis_fraction')
    geometry_at_values(request,project,[v['initial'] for v in request['variables']])


def trial_project(request,project,values):
    return deform_curved_project(project,geometry_at_values(request,project,values),
        rf_coordinates=request['rf_coordinates'],minimum_corner_angle_deg=request['minimum_corner_angle_deg'])
