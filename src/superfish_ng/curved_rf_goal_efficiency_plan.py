# SPDX-License-Identifier: Apache-2.0
"""Strict inputs for the fixed 36-run RF-goal comparison, without any solves.

The reviewed plan pins its four original sources and six explicit source meshes.
Every call rechecks those bytes, validates the public requests and returns fresh
objects. Reference preparation, native execution and physical acceptance belong
to later stages; the original N05 plan and public adaptive engines are unchanged.
"""
from copy import deepcopy
import hashlib
import math
import os
from pathlib import Path, PurePosixPath
import stat

from .curved_adaptive_refinement import validate_request as validate_v4
from .curved_rf_adaptive_refinement import validate_request as validate_v5
from .project import parse_json


FIXED_PLAN_PATH = 'examples/curved_rf_goal_efficiency/plan.json'
FIXED_PLAN_SHA256 = 'bd7413897cc677db774371310ad5e11b21de385e434f0b89de40474d71fd4d8d'
FIXED_PLAN_BYTES = 11490
_UNSUPPLIED = object()


def _read_bound(root, binding):
    """Read only a regular bound file, traversing directories without symlinks.

    Directory descriptors also prevent a changed parent symlink from directing
    the read outside the declared tree. Nonblocking open rejects FIFOs without
    waiting. The benchmark's measured process supervisor likewise targets POSIX.
    """
    relative = binding['path']
    if (type(relative) is not str or not relative or '\\' in relative or
            PurePosixPath(relative).is_absolute() or '..' in PurePosixPath(relative).parts or
            PurePosixPath(relative).as_posix() != relative):
        raise ValueError('fixed RF goal input requires a repository-relative path without traversal')
    path = root / relative
    descriptor = None
    file_descriptor = None
    try:
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        descriptor = os.open(root.anchor, directory_flags)
        for part in (*root.parts[1:], *PurePosixPath(relative).parts[:-1]):
            next_descriptor = os.open(part, directory_flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_descriptor
        file_descriptor = os.open(PurePosixPath(relative).name,
                                  os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                                  dir_fd=descriptor)
        info = os.fstat(file_descriptor)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError(f'fixed RF goal input requires a regular file without symlinks: {path}')
        if info.st_size != binding['bytes']:
            raise ValueError(f'fixed RF goal plan/input bytes differ: {path}; restore the reviewed input')
        with os.fdopen(file_descriptor, 'rb') as stream:
            file_descriptor = None
            data = stream.read(binding['bytes'] + 1)
    except (OSError, AttributeError, NotImplementedError) as exc:
        raise ValueError(f'fixed RF goal input requires readable regular files and directories '
                         f'without symlinks, on a platform supporting no-follow directory reads: {path}') from exc
    finally:
        if file_descriptor is not None:
            os.close(file_descriptor)
        if descriptor is not None:
            os.close(descriptor)
    if len(data) != binding['bytes'] or hashlib.sha256(data).hexdigest() != binding['sha256']:
        raise ValueError(f'fixed RF goal plan/input sha256 differs: {path}; restore the reviewed input '
                         'or use a separately reviewed comparison plan')
    return data


def _parse(text):
    if type(text) is not str:
        raise ValueError('RF goal efficiency plan JSON must be text')
    try:
        return parse_json(text)
    except (ValueError, RecursionError) as exc:
        raise ValueError(f'RF goal efficiency plan JSON is invalid: {exc}') from exc


def _same(value, expected, location):
    """Compare JSON types as well as values; True never equals integer 1."""
    if type(value) is not type(expected):
        raise ValueError(f'{location} requires the fixed {type(expected).__name__} type')
    if type(expected) is dict:
        if any(type(k) is not str for k in value) or value.keys() != expected.keys():
            raise ValueError(f'{location} has unknown or missing keys; restore the complete fixed object')
        for key in expected:
            _same(value[key], expected[key], f'{location}.{key}')
    elif type(expected) is list:
        if len(value) != len(expected):
            raise ValueError(f'{location} requires the complete fixed list of {len(expected)} entries')
        for i, (actual, original) in enumerate(zip(value, expected)):
            _same(actual, original, f'{location}[{i}]')
    elif (type(value) is float and not math.isfinite(value)) or value != expected:
        raise ValueError(f'{location} differs from the reviewed fixed value; restore it or use a separately reviewed plan')


def _original_requests(sources, requests):
    sphere, prolate, rounded_case, rounded_mesh = map(deepcopy, sources)
    sphere['max_triangles'] = 250000  # Explicit N05 budget, not the example's 20000.
    rounded = dict(schema_version=5, case=rounded_case, initial_mesh=rounded_mesh,
                   initial_ids=['target', 'guard-2', 'guard-3'], mode_id='target',
                   controls=dict(mapping='nested_curved', minimum_overlap=.98,
                                 minimum_assignment_margin=.05, relative_cluster_gap=1e-6,
                                 minimum_relative_singular_value=1e-8),
                   bulk_fraction=.5, max_levels=8, max_triangles=250000,
                   minimum_corner_angle_deg=5., confirmation='uniform_two_steps',
                   relative_tolerances=dict(frequency_hz=1e-4, r_over_q_accelerator_ohm=.005,
                                            geometry_factor_ohm=.005),
                   surface_relative_tolerances=dict(epk_over_eacc=.01, bpk_over_eacc_mt_per_mv_per_m=.01),
                   quadrature_check_order=24, quadrature_relative_tolerance=1e-6)
    originals = dict(sphere=sphere, prolate=prolate, **{'rounded-two-lobe': rounded})
    for family, request in originals.items():
        request['schema_version'] = 5
        request['surface_refinement_policy'] = 'rf_goal'
        if request['initial_mesh'] is None:
            # The specification bound these formerly implicit meshes once.
            # A plan read must not regenerate them using a later mesher.
            request['initial_mesh'] = deepcopy(requests[f'{family}-scale-1']['initial_mesh'])
    return originals


def _scaled_request(original, scale):
    request = deepcopy(original)
    geometry = request['case']['geometry']
    for curve in geometry['curves']:
        for key in ('start_zr_m', 'end_zr_m', 'center_zr_m', 'semiaxes_m'):
            if key in curve:
                curve[key] = [scale * v for v in curve[key]]
    for key in ('chord_tolerance_m', 'join_tolerance_m', 'minimum_gap_m'):
        geometry[key] *= scale
    request['case']['mesh']['contour_mesh']['max_edge_m'] *= scale
    request['case']['rf']['normalization_j'] = float(scale**2)
    request['initial_mesh']['points'] = [[scale*v for v in point] for point in original['initial_mesh']['points']]
    return request


def _verified_inputs(*, base_directory, supplied_plan=_UNSUPPLIED, execution=_UNSUPPLIED):
    try:
        root = (Path(__file__).resolve().parents[2] if base_directory is None else Path(base_directory)).absolute()
    except (TypeError, ValueError) as exc:
        raise ValueError('RF goal efficiency base_directory must be a filesystem directory') from exc
    plan_binding = dict(path=FIXED_PLAN_PATH, sha256=FIXED_PLAN_SHA256, bytes=FIXED_PLAN_BYTES)
    plan = _parse(_read_bound(root, plan_binding).decode('utf-8'))
    if supplied_plan is not _UNSUPPLIED:
        _same(supplied_plan, plan, 'plan')
    selected = None
    if execution is not _UNSUPPLIED:
        if type(execution) is not dict or type(execution.get('id')) is not str:
            raise ValueError('RF goal efficiency execution requires a complete fixed row with its string id')
        selected = next((row for row in plan['executions'] if row['id'] == execution['id']), None)
        if selected is None:
            raise ValueError('RF goal efficiency execution id is not in the fixed 36 rows')
        _same(execution, selected, 'execution')
    bindings = [plan_binding, *plan['input_sources'], *(case['request'] for case in plan['cases'])]
    # Read all sources before public validation. No untrusted path from a supplied
    # plan or row is ever followed, even if its SHA was recomputed by the caller.
    data = [_parse(_read_bound(root, binding).decode('utf-8')) for binding in bindings[1:]]
    requests = {case['id']: value for case, value in zip(plan['cases'], data[4:])}
    originals = _original_requests(data[:4], requests)
    for case in plan['cases']:
        request = requests[case['id']]
        expected = _scaled_request(originals[case['family']], case['scale'])
        _same(request, expected, f"request[{case['id']}]")
        validate_v5(request)  # Includes the complete strict Case and explicit mesh.
        _same(request, expected, f"validated request[{case['id']}]")
    selected_request = None
    if selected is not None:
        selected_request = deepcopy(requests[selected['case_id']])
        if selected['method'] == 'uniform':
            selected_request.pop('surface_refinement_policy')
            selected_request['schema_version'] = 4
            validator = validate_v4
        else:
            selected_request['surface_refinement_policy'] = selected['method']
            validator = validate_v5
        expected = deepcopy(selected_request)
        validator(selected_request)
        _same(selected_request, expected, 'validated execution request')
    # Reopen through the same no-follow path checks; do not trust stat metadata,
    # a prior cache or even an unchanged caller-supplied manifest.
    for binding in bindings:
        _read_bound(root, binding)
    return deepcopy(plan), deepcopy(selected_request)


def build_curved_rf_goal_efficiency_plan(*, base_directory=None):
    """Return the fixed, source-verified 36-row plan; no FEM or reference reads."""
    return _verified_inputs(base_directory=base_directory)[0]


def validate_curved_rf_goal_efficiency_plan(plan, *, base_directory=None):
    """Require the full fixed plan with exact JSON types and unchanged inputs."""
    return _verified_inputs(base_directory=base_directory, supplied_plan=plan)[0]


def parse_curved_rf_goal_efficiency_plan(text, *, base_directory=None):
    """Parse raw JSON with duplicate-key rejection, then verify the whole plan."""
    return validate_curved_rf_goal_efficiency_plan(_parse(text), base_directory=base_directory)


def request_for_curved_rf_goal_efficiency_execution(execution, *, base_directory=None):
    """Return an independent v4 uniform or explicit-policy v5 request for one row.

    The entire fixed plan and all ten source files are checked, including changes
    during validation. This resolves inputs only; it neither runs a worker nor
    supplies an independent reference or an accuracy/efficiency certificate.
    """
    return _verified_inputs(base_directory=base_directory, execution=execution)[1]
