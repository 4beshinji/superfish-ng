# SPDX-License-Identifier: Apache-2.0
"""Replayable straight TM geometry candidates; no FEM or RF assessment.

Every trial is reconstructed from the complete original Project and owned
comparison mesh. Geometry verification does not establish a mode identity,
an RF constraint, discretization accuracy, or an optimization result.
"""
from copy import deepcopy
from .config import keys,integer
from .project import Project
from .rf_design import _number
from .scalar_expressions import validate_scalar_expression
from .saved_mode_tracking import validate_tracking_controls,_canonical
from .straight_tuning import _law,_trial_geometry
from .te import is_te


def validate_straight_candidate_request(request):
    fields=('schema_version','document_type','project','variables','shape_law','controls','max_candidates')
    keys(request,fields,fields,'straight RF candidate request')
    if (type(request['schema_version']) is not int or request['schema_version']!=1
            or request['document_type']!='straight_rf_candidate_request'):
        raise ValueError('straight RF candidates require schema_version 1 and document_type straight_rf_candidate_request')
    integer(request['max_candidates'],'max_candidates')
    variables=request['variables'];units={}
    if type(variables) is not list or not variables:raise ValueError('candidate variables must be a nonempty list')
    for variable in variables:
        names=('name','unit','lower','upper');keys(variable,names,names,'candidate variable')
        name=variable['name']
        if type(name) is not str or not name.strip() or name in units:
            raise ValueError('candidate variable names must be distinct nonempty strings')
        if variable['unit'] not in ('1','m'):raise ValueError('candidate variable units must be 1 or m in SI')
        if (not _number(variable['lower']) or not _number(variable['upper'])
                or not variable['lower']<variable['upper']):
            raise ValueError('candidate bounds must be finite and strictly increasing')
        units[name]=variable['unit']
    source=Project.from_dict(request['project'])
    if is_te(source.case):raise ValueError('straight RF candidate adapter supports TM only; TE belongs to D08/D10-TE')
    law,_=_law(request,source,variable_units=units)
    active=set()
    for binding in law['bindings']:
        active.update(validate_scalar_expression(binding['expression'],units,expected_unit='m')['variables'])
    if active!=set(units):raise ValueError('every declared candidate variable must occur in a coordinate expression')
    controls=request['controls']
    if type(controls) is not dict or controls.get('mapping')!='piecewise_remesh' or 'comparison_meshes' in controls:
        raise ValueError('straight candidates require piecewise_remesh controls without input comparison_meshes')
    reference=law['reference_comparison_mesh']
    validate_tracking_controls(dict(controls,comparison_meshes=[reference,reference]))
    _canonical(request)
    return source,units


def straight_candidate_project(request,values):
    """Build the actual unassembled Project and comparison mesh at named values."""
    source,units=validate_straight_candidate_request(request)
    variables=request['variables']
    if (type(values) is not list or len(values)!=len(variables)
            or any(not _number(x) or not v['lower']<=x<=v['upper'] for v,x in zip(variables,values))):
        raise ValueError('candidate values must provide one finite in-bounds value per declared variable')
    return _trial_geometry(request,source,None,variable_units=units,
        variable_values={v['name']:x for v,x in zip(variables,values)})


def _ledger(request,values):
    validate_straight_candidate_request(request)
    if type(values) is not list or len(values)>request['max_candidates']:
        raise ValueError('candidate values must be a list within max_candidates; failures also consume this budget')
    _canonical(values)
    candidates=[]
    for index,value in enumerate(values):
        try:
            project,mesh=straight_candidate_project(request,value)
            candidate=dict(status='GEOMETRY_VERIFIED',project=project.to_dict(),comparison_mesh=mesh,error=None)
        except ValueError as exc:
            candidate=dict(status='INVALID_GEOMETRY',project=None,comparison_mesh=None,error=str(exc))
        candidates.append(dict(index=index,values=deepcopy(value),**candidate,mode_id=None,assessment=None))
    return dict(schema_version=1,document_type='straight_rf_candidate_ledger',request=deepcopy(request),
        candidates=candidates,candidates_attempted=len(values),max_candidates=request['max_candidates'],
        fem_calls_attempted=0,rf_assessments=0,
        scope='original straight TM geometry candidates only; mode IDs and RF assessments are unverified; no FEM or optimization acceptance')


def replay_straight_rf_candidates(document):
    fields=('schema_version','document_type','request','candidates','candidates_attempted','max_candidates',
            'fem_calls_attempted','rf_assessments','scope')
    keys(document,fields,fields,'straight RF candidate ledger')
    if type(document['candidates']) is not list or any(type(c) is not dict or 'values' not in c for c in document['candidates']):
        raise ValueError('candidate ledger requires candidate records with original values')
    expected=_ledger(document['request'],[c['values'] for c in document['candidates']])
    if _canonical(expected)!=_canonical(document):raise ValueError('straight RF candidate replay differs from original laws, values or geometry')
    return expected


def prepare_straight_rf_candidates(request,values,*,checkpoint=None):
    """Append candidates to a verified immutable prefix, without a solve."""
    previous=[]
    if checkpoint is not None:
        verified=replay_straight_rf_candidates(checkpoint)
        if _canonical(verified['request'])!=_canonical(request):raise ValueError('candidate resume request differs from checkpoint')
        previous=[c['values'] for c in verified['candidates']]
    if type(values) is not list:raise ValueError('new candidate values must be a list')
    return _ledger(request,previous+values)
