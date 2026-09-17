# SPDX-License-Identifier: Apache-2.0
"""Strict vacuum Hphi uniform-scale tuning requests and independent trials."""
from copy import deepcopy
from dataclasses import dataclass, replace
import math
from pathlib import Path

import numpy as np

from .axis_hphi import AxisHphiCase
from .coaxial import CoaxialCase
from .config import integer, keys, positive
from .hphi_mesh import HphiMeshCase
from .hphi_project import HphiProject
from .hphi_study import HphiStudy
from .hphi_tracking import HphiTrackingControls
from .project import parse_json
from .hphi_field_overlap import _declared_mesh, _verified_solution
from .hphi_geometry_mapping import (
    HphiGeometryMapping,
    coaxial_dimension_mapping,
    map_axis_acceleration,
    map_mesh,
)
from .hphi_native import solve_hphi
from .hphi_tracking import HphiTrackingRequest, _track_hphi_modes
from .mode_tracking import tracked_frequency_hz
from .tuning import _decision


MAPPING_KINDS = ('uniform_scale', 'coaxial_dimensions', 'general_piecewise_affine')
COAXIAL_COORDINATES = ('inner_radius_m', 'outer_radius_m', 'length_m')
AFFINE_AXES = ('radial', 'axial')
SCOPE_BY_KIND = {'uniform_scale': 'vacuum_uniform_scale', 'coaxial_dimensions': 'vacuum_coaxial_dimensions',
                 'general_piecewise_affine': 'vacuum_general_piecewise_affine'}


def tune_scope(request):
    """Declared checkpoint scope for a validated Hphi tuning mapping."""
    return SCOPE_BY_KIND[request['mapping']['kind']]


def _coaxial_dimensions(case):
    return case.inner_radius_m, case.outer_radius_m, case.length_m


def _axis_mapping(axis, scale):
    """Single-axis dimensionless scaling map used by the affine tuning family."""
    if axis == 'radial':
        return HphiGeometryMapping(((scale, 0.), (0., 1.)))
    if axis == 'axial':
        return HphiGeometryMapping(((1., 0.), (0., scale)))
    raise ValueError('Hphi affine tuning axis must be radial or axial')


def _affine_case(case, axis, scale):
    """Apply one declared axis scale to a straight vacuum Case without inference."""
    mapping = _axis_mapping(axis, scale)
    if type(case) is CoaxialCase:
        if axis == 'axial':
            return replace(case, length_m=float(case.length_m)*scale)
        return replace(case, inner_radius_m=float(case.inner_radius_m)*scale,
                       outer_radius_m=float(case.outer_radius_m)*scale)
    if type(case) is HphiMeshCase:
        return replace(case, mesh=map_mesh(case.mesh, mapping))
    if type(case) is AxisHphiCase:
        acceleration = None if case.acceleration is None else map_axis_acceleration(mapping, case.acceleration)
        return replace(case, mesh=map_mesh(case.mesh, mapping), acceleration=acceleration)
    raise ValueError('general_piecewise_affine tuning requires a straight vacuum Hphi Project')


def _json_types(value):
    """Reject non-JSON scalar types before existing readers can coerce them."""
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise ValueError('Hphi tune object keys must be strings')
            _json_types(item)
    elif type(value) is list:
        for item in value:
            _json_types(item)
    elif type(value) not in (str, int, float, bool, type(None)):
        raise ValueError('Hphi tune requires JSON types, not NumPy or other scalar types')
    elif type(value) is float and not math.isfinite(value):
        raise ValueError('Hphi tune numbers must be finite')


def _mesh_counts(case):
    """Count all nodal coefficients, including constrained/zero-mode nodes."""
    if type(case) is CoaxialCase:
        return ((case.nr+1)*(case.nz+1),
                3*case.nr*case.nz+case.nr+case.nz, 2*case.nr*case.nz)
    cells = case.mesh.triangles
    edges = np.unique(np.sort(cells[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2), axis=1), axis=0)
    return len(case.mesh.points_rz_m), len(edges), len(cells)


def _budget(request, case):
    vertices, edges, triangles = _mesh_counts(case)
    controls = HphiTrackingControls.from_dict(request['controls'])
    for level in range(request['refinement_levels']+2):
        comparison = level == request['refinement_levels']+1
        dofs = vertices + (edges if comparison or case.element_order == 2 else 0)
        triangle_limit = min(250000, controls.max_overlay_triangles if comparison else request['max_triangles'])
        dof_limit = controls.max_dofs if comparison else request['max_dofs']
        if triangles > triangle_limit:
            raise ValueError('Hphi tune final/comparison mesh exceeds max_triangles or max_overlay_triangles')
        if dofs > dof_limit:
            raise ValueError('Hphi tune final/comparison mesh exceeds max_dofs')
        vertices, edges, triangles = vertices+edges, 2*edges+3*triangles, 4*triangles


def _refine_mesh(mesh):
    """Split every straight triangle into four, retaining every PEC contour."""
    points, cells = mesh.points_rz_m, mesh.triangles
    edges, inverse = np.unique(np.sort(cells[:, [[0, 1], [1, 2], [2, 0]]].reshape(-1, 2), axis=1),
                               axis=0, return_inverse=True)
    local = np.column_stack((cells, len(points)+inverse.reshape(-1, 3)))
    split = np.array([[0, 3, 5], [3, 1, 4], [5, 4, 2], [3, 4, 5]])
    return type(mesh)(mesh.outer_rz_m, mesh.holes_rz_m,
                      np.vstack((points, points[edges].mean(axis=1))), local[:, split].reshape(-1, 3))


def _trial(project, value, phase, request):
    kind = request['mapping']['kind']
    if kind == 'uniform_scale':
        project = HphiStudy(project, 'uniform_scale', [value, value]).projects()[0]
    elif kind == 'coaxial_dimensions':
        project = HphiStudy(project, '/case/geometry/' + request['mapping']['coordinate'], [value, value]).projects()[0]
    elif kind == 'general_piecewise_affine':
        project = HphiProject(_affine_case(project.case, request['mapping']['axis'], value), project.display_length_unit)
    else:
        raise ValueError('unsupported Hphi tune mapping.kind')
    case = project.case
    for _ in range(request['refinement_levels'] if phase == 'refinement' else 0):
        case = (replace(case, nr=2*case.nr, nz=2*case.nz) if type(case) is CoaxialCase
                else replace(case, mesh=_refine_mesh(case.mesh)))
    return replace(project, case=case)


def validate_hphi_tune(request):
    """Validate all inputs and final/comparison budgets before any output or FEM."""
    _json_types(request)
    names = ('format', 'schema_version', 'project', 'parameter', 'mapping', 'bounds',
             'target_hz', 'frequency_tolerance_hz', 'parameter_tolerance', 'max_trials',
             'initial_ids', 'mode_id', 'controls', 'refinement_levels', 'max_triangles',
             'max_dofs', 'mesh_frequency_tolerance_hz')
    keys(request, names, names, 'Hphi tune')
    if request['format'] != 'superfish_ng_hphi_tune' or type(request['schema_version']) is not int or request['schema_version'] != 1:
        raise ValueError('expected superfish_ng_hphi_tune schema_version 1')
    project = HphiProject.from_dict(request['project'])
    if type(project.case) not in (CoaxialCase, HphiMeshCase, AxisHphiCase):
        raise ValueError('Hphi tune requires straight vacuum coaxial, positive-radius or regular-axis physics')
    mapping = request['mapping']
    if type(mapping) is not dict or type(mapping.get('kind')) is not str or mapping['kind'] not in MAPPING_KINDS:
        raise ValueError('Hphi tune mapping.kind must be uniform_scale, coaxial_dimensions or general_piecewise_affine')
    kind = mapping['kind']
    if kind == 'uniform_scale':
        keys(mapping, ['kind'], ['kind'], 'Hphi tune mapping')
        if request['parameter'] != 'uniform_scale':
            raise ValueError('Hphi tune parameter must be uniform_scale for the uniform_scale mapping; energy/conductivity are not shape variables')
    elif kind == 'coaxial_dimensions':
        keys(mapping, ['kind', 'coordinate'], ['kind', 'coordinate'], 'Hphi tune mapping')
        if mapping['coordinate'] not in COAXIAL_COORDINATES:
            raise ValueError('Hphi tune coaxial coordinate must be inner_radius_m, outer_radius_m or length_m')
        if request['parameter'] != 'coaxial_dimensions':
            raise ValueError('Hphi tune parameter must be coaxial_dimensions for the coaxial_dimensions mapping')
        if type(project.case) is not CoaxialCase:
            raise ValueError('coaxial_dimensions tuning requires a closed coaxial Project; explicit meshes need general_piecewise_affine')
    else:
        keys(mapping, ['kind', 'axis'], ['kind', 'axis'], 'Hphi tune mapping')
        if mapping['axis'] not in AFFINE_AXES:
            raise ValueError('Hphi tune affine axis must be radial or axial')
        if request['parameter'] != 'general_piecewise_affine':
            raise ValueError('Hphi tune parameter must be general_piecewise_affine for the general_piecewise_affine mapping')
    bounds = request['bounds']
    if type(bounds) is not list or len(bounds) != 2:
        raise ValueError('Hphi tune bounds require two increasing positive values')
    for value in bounds:
        positive(value, 'Hphi tune bound')
    if not bounds[0] < bounds[1]:
        raise ValueError('Hphi tune bounds must increase')
    for name in ('target_hz', 'frequency_tolerance_hz', 'parameter_tolerance', 'mesh_frequency_tolerance_hz'):
        positive(request[name], name)
    if request['parameter_tolerance'] > bounds[1]-bounds[0]:
        raise ValueError('parameter_tolerance must not exceed the bounds width')
    integer(request['max_trials'], 'max_trials', 2)
    for name in ('refinement_levels', 'max_triangles', 'max_dofs'):
        integer(request[name], name)
    if request['refinement_levels'] > 8:
        raise ValueError('Hphi tune refinement_levels must be from 1 to 8')
    ids = request['initial_ids']
    if (type(ids) is not list or not ids or len(ids) >= project.case.modes or
            any(type(i) is not str or not i.strip() for i in ids) or len(set(ids)) != len(ids)):
        raise ValueError('initial_ids require a distinct positive prefix and a computed upper guard mode')
    if type(request['mode_id']) is not str or request['mode_id'] not in ids:
        raise ValueError('mode_id must occur in initial_ids')
    controls = HphiTrackingControls.from_dict(request['controls'])
    if project.case.modes > controls.max_gram_modes:
        raise ValueError('Hphi tune spectrum exceeds max_gram_modes')
    _budget(request, project.case)
    for value in bounds:
        _trial(project, value, 'search', request)
    return project


def read_hphi_tune_request(path):
    request = parse_json(Path(path).read_text(encoding='utf-8'))
    validate_hphi_tune(request)
    return deepcopy(request)


def trial_hphi_project(request, value, phase):
    """Derive a candidate from the original Project, never the latest trial."""
    project = validate_hphi_tune(request)
    _json_types(value)
    positive(value, 'Hphi tune trial value')
    if not request['bounds'][0] <= value <= request['bounds'][1]:
        raise ValueError('Hphi tune trial value is outside bounds')
    if phase not in ('search', 'refinement'):
        raise ValueError('Hphi tune phase must be search or refinement')
    return _trial(project, value, phase, request)


@dataclass(frozen=True)
class HphiTuneRun:
    """In-memory execution evidence; owned native/checkpoint I/O is separate."""
    report: dict
    projects: tuple
    solutions: tuple


def _tune_decision(request, trials):
    # Keep dedicated budget stops outside the shared bisection vocabulary.
    if trials and trials[-1]['status'] == 'MESH_LIMIT':
        return dict(status='MESH_LIMIT', next_trial=None, reason=trials[-1]['tracking']['verification_reasons'][0])
    decision = _decision(request, trials)
    if decision['status'] == 'PAUSED' and trials and decision['next_trial']['phase'] == 'search':
        # Every mapping family has one fixed shape reference (the initial
        # trial). Comparing a candidate to any other intermediate trial would
        # require a composed ratio that can introduce avoidable contour
        # roundoff. Keep bracket selection shared; declare the actual
        # comparison parent, whose declared mapping covers the candidate.
        decision['next_trial']['parent_index'] = 0
    return decision


def _assess_trial(request, trials, solutions, solution):
    decision = _tune_decision(request, trials)
    if decision['status'] != 'PAUSED':
        raise ValueError('Hphi tune contains trials after a terminal decision')
    trial = decision['next_trial']
    expected = trial_hphi_project(request, trial['value'], trial['phase'])
    if not hasattr(solution, 'case') or solution.case.to_dict() != expected.case.to_dict():
        raise ValueError('Hphi tune solution differs from the declared trial Project')
    solution = _verified_solution(solution)
    index = len(trials)
    parent = trial['parent_index']
    previous = solution if index == 0 else solutions[parent]
    ids = request['initial_ids'] if index == 0 else trials[parent]['current_mode_ids']
    kind = request['mapping']['kind']
    scale = None
    mapping = None
    if index != 0:
        if kind == 'uniform_scale':
            scale = trial['value']/trials[parent]['value']
        elif kind == 'coaxial_dimensions' or type(previous.case) is CoaxialCase:
            mapping = coaxial_dimension_mapping(*_coaxial_dimensions(previous.case), *_coaxial_dimensions(solution.case))
        else:
            mapping = _axis_mapping(request['mapping']['axis'], trial['value']/trials[parent]['value'])
    controls = HphiTrackingControls.from_dict(request['controls'])
    try:
        comparison = HphiTrackingRequest(_refine_mesh(_declared_mesh(previous)),
            _refine_mesh(_declared_mesh(solution)), previous_mode_count=len(ids),
            current_mode_count=len(ids), previous_mode_ids=ids, controls=controls)
        tracking = _track_hphi_modes(previous, solution, comparison, previous_scale=scale, previous_mapping=mapping)
        passed = tracking['status'] == 'PASS' and tracking['individual_ids_complete']
        status = ('INITIAL' if index == 0 else 'PASS') if passed else 'UNVERIFIED'
        frequency = tracked_frequency_hz(tracking, request['mode_id']) if passed else None
    except ValueError as exc:
        # Comparison refusal is evidence of no identity, never a frequency match.
        reason = str(exc)
        mesh_limit = reason in ('input meshes exceed max_overlay_triangles',
            'meridional intersections exceed max_overlay_triangles', 'Hphi mass coupling exceeds max_dofs')
        status = 'MESH_LIMIT' if mesh_limit else 'UNVERIFIED'
        frequency = None
        if scale is not None:
            declared = dict(kind='uniform_scale', previous_scale=scale)
        elif mapping is not None:
            declared = dict(kind='declared_affine', **mapping.to_dict())
        else:
            declared = dict(kind='same_geometry')
        tracking = dict(status=status, individual_ids_complete=False,
            current_mode_ids=[None]*len(ids), verification_reasons=[reason], mapping=declared)
    return dict(index=index, **trial, status=status, current_mode_ids=tracking['current_mode_ids'],
        frequency_hz=frequency, target_error_hz=None if frequency is None else frequency-request['target_hz'],
        tracking=tracking), expected


def _run_result(request, trials, projects, solutions):
    decision = _tune_decision(request, trials)
    kind = request['mapping']['kind']
    if kind == 'coaxial_dimensions':
        parameter, parameter_unit = request['mapping']['coordinate'] + ' [m]', 'm'
    elif kind == 'general_piecewise_affine':
        parameter, parameter_unit = request['mapping']['axis'] + ' length scale', 'dimensionless'
    else:
        parameter, parameter_unit = 'uniform_scale', 'dimensionless'
    report = dict(format='superfish_ng_hphi_tune_result', schema_version=1,
        request=deepcopy(request), trials=deepcopy(trials), decision=decision,
        status=decision['status'], can_resume=decision['status'] == 'PAUSED',
        scope=tune_scope(request), parameter=parameter, parameter_unit=parameter_unit, frequency_unit='Hz',
        interpretation='original Hphi FEM and individually confirmed E/H identities; separate target and two-mesh frequency gates; no RF convergence or continuum error certificate')
    return HphiTuneRun(report, tuple(projects), tuple(solutions))


def assess_hphi_tune(request, solutions):
    """Reconstruct decisions from ordered, verified original in-memory FEMs."""
    request = deepcopy(request)
    validate_hphi_tune(request)
    if type(solutions) not in (list, tuple) or len(solutions) > request['max_trials']+1:
        raise ValueError('Hphi tune requires solutions within search plus final trial budget')
    trials, projects, accepted = [], [], []
    for solution in solutions:
        trial, project = _assess_trial(request, trials, accepted, solution)
        trials.append(trial); projects.append(project); accepted.append(solution)
    return _run_result(request, trials, projects, accepted)


def run_hphi_tune(request, *, max_new_trials=None):
    """Run actual dedicated FEMs; pause only between complete trials.

    This API returns original solutions and a serializable decision report.
    Persistent checkpoints, replay/resume and process cancellation belong to
    the separate ownership/worker layers, not this in-memory runner.
    """
    request = deepcopy(request)
    validate_hphi_tune(request)
    if max_new_trials is not None:
        integer(max_new_trials, 'max_new_trials')
    trials, projects, solutions = [], [], []
    while _tune_decision(request, trials)['status'] == 'PAUSED':
        if max_new_trials is not None and len(trials) >= max_new_trials:
            break
        candidate = _tune_decision(request, trials)['next_trial']
        project = trial_hphi_project(request, candidate['value'], candidate['phase'])
        solution = solve_hphi(project.case)
        trial, project = _assess_trial(request, trials, solutions, solution)
        trials.append(trial); projects.append(project); solutions.append(solution)
    return _run_result(request, trials, projects, solutions)


def execute_hphi_tune(request, directory, *, max_new_trials=None, checkpoint=None):
    """Execute the owned persistent Hphi tuning workflow."""
    from .hphi_tuning_saved import execute_hphi_tune as _execute
    return _execute(request, directory, max_new_trials=max_new_trials, checkpoint=checkpoint)


def replay_hphi_tune(document, *, base_directory=None):
    """Replay an owned persistent Hphi tuning checkpoint."""
    from .hphi_tuning_saved import replay_hphi_tune as _replay
    return _replay(document, base_directory=base_directory)


def read_hphi_tune(path):
    """Read and replay an owned persistent Hphi tuning checkpoint."""
    from .hphi_tuning_saved import read_hphi_tune as _read
    return _read(path)
