# SPDX-License-Identifier: Apache-2.0
"""Apply dimension-checked expressions atomically to native trial geometry."""
import re
from .config import keys
from .project import Project
from .scalar_expressions import validate_scalar_expression, evaluate_scalar_expression
from .curved_harmonic_study import curve_numeric_leaf
from .curved_harmonic_deformation import deform_curved_project
from .curved_tuning import refine_project
from .studies import Study


def geometry_at_value(request, project, value):
    geometry=project.case.to_dict()['geometry']
    bindings=request['bindings'];seen=set();active=False
    if type(bindings) is not list or not bindings:
        raise ValueError('expression bindings must be a nonempty list')
    units={request['parameter']:request['parameter_unit']}
    values={request['parameter']:value}
    for binding in bindings:
        keys(binding,('path','expression'),('path','expression'),'expression binding')
        path=binding['path']
        if type(path) is not str:raise ValueError('expression binding path must be a string')
        if path in seen:raise ValueError('duplicate expression binding target')
        seen.add(path)
        if request['geometry_kind']=='profile':
            match=re.fullmatch(r'/case/geometry/points_zr_m/(0|[1-9][0-9]*)/([01])',path)
            if match is None:raise ValueError('expression binding path must name a canonical profile vertex coordinate')
            index,key=map(int,match.groups())
            if index>=len(geometry['points_zr_m']):raise ValueError('expression binding vertex does not exist')
            parent=geometry['points_zr_m'][index];unit='m'
        elif request['geometry_kind']=='curved_harmonic':
            if not path.startswith('/case/geometry/'):
                raise ValueError('curve expression path must start with /case/geometry/')
            leaf=path[len('/case/geometry'):]
            parent,key=curve_numeric_leaf(geometry,leaf)
            unit='m' if leaf.split('/')[3].endswith('_m') else '1'
        else:raise ValueError('expression geometry_kind must be profile or curved_harmonic')
        try:
            metadata=validate_scalar_expression(binding['expression'],units,expected_unit=unit)
            active=active or bool(metadata['variables'])
            parent[key]=evaluate_scalar_expression(binding['expression'],values,units,expected_unit=unit)
        except ValueError as exc:
            raise ValueError(f'expression binding {path} at {request["parameter"]}={value}: {exc}') from exc
    if not active:raise ValueError('at least one expression binding must reference the parameter')
    return geometry


def validate_request(request, project):
    kind=request['geometry_kind']
    if kind not in ('profile','curved_harmonic'):
        raise ValueError('expression geometry_kind must be profile or curved_harmonic')
    if kind=='curved_harmonic':
        scale=request['refinement_scale']
        if scale & (scale-1):raise ValueError('curved expression tune refinement_scale must be a power of two')
        controls=request['controls']
        if not isinstance(controls,dict) or controls.get('mapping')!='piecewise_remesh' or 'comparison_meshes' in controls:
            raise ValueError('curved expression tune requires piecewise_remesh controls without comparison_meshes')
        from .curved_harmonic_tuning import pair_controls
        first=trial_project(request,project,request['bounds'][0],'search')
        pair_controls(request,first,first)


def trial_project(request, project, value, phase):
    geometry=geometry_at_value(request,project,value)
    if request['geometry_kind']=='curved_harmonic':
        project=deform_curved_project(project,geometry,rf_coordinates=request['rf_coordinates'],
            minimum_corner_angle_deg=request['minimum_corner_angle_deg'])
        return refine_project(request,project) if phase=='refinement' else project
    raw=project.to_dict();raw['case']['geometry']=geometry
    project=Project.from_dict(raw)
    return Study(project,'mesh_convergence','mesh_scale',[1,request['refinement_scale']]).projects()[1] if phase=='refinement' else project
