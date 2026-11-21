# SPDX-License-Identifier: Apache-2.0
"""Fresh uniform native solves for N06; convergence is separate from physics.

This worker uses the original FEM, saved-field tracking and discrete peak APIs.
It does not run the adaptive selector or substitute reference formulas for FEM.
"""
from contextlib import nullcontext
from copy import deepcopy
from dataclasses import replace
import json
import math
from pathlib import Path

from .adaptive_refinement import _request, _limits
from .adaptive_surface_stopping import surface_intervals, QUANTITIES as PEAKS
from .config import integer
from .contour_mesh import contour_mesh_quality
from .io import save_run
from .jobs import _implementation_hashes
from .marked_refinement import refine_marked_cells
from .mesh import make_mesh
from .mesh_input import mesh_from_dict, mesh_to_dict
from .project import parse_json
from .saved import read_solution
from .saved_mode_tracking import _snapshot, build_saved_mode_tracking
from .solver import solve
from .surface_convergence import _interval_change


RF = ('frequency_hz', 'r_over_q_accelerator_ohm', 'r_over_q_circuit_ohm', 'geometry_factor_ohm')


def _confirmation(levels, request):
    changes = []
    for previous, current in zip(levels[-3:], levels[-2:]) if len(levels) >= 3 else []:
        row = {}
        for name in RF:
            a, b = previous['quantities'][name], current['quantities'][name]
            key = 'r_over_q_accelerator_ohm' if name == 'r_over_q_circuit_ohm' else name
            limit = request['relative_tolerances'][key]
            value = abs(b/a-1) if all(type(v) in (int, float) and math.isfinite(v) and v > 0 for v in (a, b)) else None
            row[name] = dict(relative_change=value, limit=limit, passed=value is not None and value <= limit)
        for name in PEAKS:
            value = _interval_change(previous['surface']['intervals'][name], current['surface']['intervals'][name])
            limit = request['surface_relative_tolerances'][name]
            row[name] = dict(relative_change_upper_bound=value, limit=limit, passed=value is not None and value <= limit)
        changes.append(row)
    return dict(changes=changes, passed=len(changes) == 2 and all(v['passed'] for row in changes for v in row.values()))


def execute_uniform_efficiency(request, directory, *, max_new_levels=None, recorder=None):
    """Save consecutive full refinements, actual IDs and quantity/peak intervals.

    Native convergence never implies independent reference accuracy. Partial
    runs retain PAUSED/NOT_RUN physics; this initial worker has no resume API.
    """
    request = deepcopy(request)
    if type(request) is not dict or request.get('schema_version') not in (3, 4):
        raise ValueError('uniform efficiency requires five-quantity affine v3 or curved v4 request')
    case = _request(request)
    model = None if case.model is None else case.model.to_dict()
    if (case.element_order != 2 or model is None or
            (model['physics'], model['coordinates'], model['polarization'], model['azimuthal_index']) !=
            ('rf_eigenmode', 'axisymmetric', 'tm', 0) or case.z_min != 'pec' or case.z_max != 'pec' or
            model['materials'] != [dict(id='vacuum', type='vacuum')] or
            model['regions'] != [dict(id='cavity', material='vacuum', domain='interior')] or
            case.curved_refinement_levels or case.curved_refinement_steps):
        raise ValueError('uniform efficiency supports direct closed vacuum axis-connected m=0 TM P2 with fresh initial geometry only')
    if max_new_levels is not None:
        integer(max_new_levels, 'max_new_levels')
    def phase(name):return nullcontext() if recorder is None else recorder.phase(name)
    directory = Path(directory).resolve()
    if directory.exists():
        raise FileExistsError(directory)
    with phase('initial_mesh_and_quality'):
        mesh = make_mesh(case) if request['initial_mesh'] is None else mesh_from_dict(case, request['initial_mesh'])
        source_mesh = mesh_to_dict(mesh)
        if case.geometry_order == 2:
            from .curved_adaptive_refinement import _maximum, _quality
            from .curved_space import case_curved_space
            maximum = _maximum(case, request)
            space = case_curved_space(case, mesh)
            _quality(space, request)
            triangles = len(space.geometry.cell_nodes)
        else:
            maximum, angle = _limits(case, request)
            triangles = len(mesh.triangles)
            if contour_mesh_quality(mesh)['min_angle_deg'] < angle:
                raise ValueError('uniform initial mesh fails minimum_angle_deg')
        if triangles > maximum:
            raise ValueError('uniform initial mesh exceeds max_triangles')
    directory.mkdir(parents=True, exist_ok=False)
    implementation = _implementation_hashes()
    runs, levels, sources = [], [], []
    status = 'PAUSED'
    confirmation = dict(changes=[], passed=False)
    current_case = case
    for index in range(min(request['max_levels'], max_new_levels or request['max_levels'])):
        run = directory / f'level-{index+1:03d}'
        marked = []
        try:
            if index:
                if 4*triangles > maximum:
                    status = 'REFINEMENT_LIMIT'
                    break
                with phase('uniform_refinement_and_quality'):
                    if case.geometry_order == 2:
                        from .curved_adaptive_refinement import _apply, _quality
                        from .curved_refinement_steps import CurvedRefinementStep
                        space = _apply(current.space, CurvedRefinementStep('uniform'), maximum)
                        _quality(space, request)
                        triangles = len(space.geometry.cell_nodes)
                        current_case = replace(case, curved_refinement_levels=index)
                    else:
                        marked = list(range(len(current.mesh.triangles)))
                        refined = refine_marked_cells(case, current.mesh, marked,
                                                     max_triangles=maximum, minimum_angle_deg=angle)
                        mesh = refined.mesh
                        triangles = len(mesh.triangles)
                count = len(space.geometry.points_rz_m) if case.geometry_order == 2 else len(mesh.points)
                if case.geometry_order == 1:
                    from .high_order import quadratic_space
                    count = len(quadratic_space(mesh).dof_points)
                if count*2*case.modes > 8388608:
                    status = 'TRACKING_BUDGET'
                    break
            with phase('native_solve_and_normalization'):
                solution = solve(current_case, mesh_data=source_mesh if case.geometry_order == 2 else mesh_to_dict(mesh))
            with phase('rf_and_native_save'):
                save_run(current_case, solution, run)
            with phase('native_reconstruction'):
                current = read_solution(run)
                source = _snapshot(run)
            ids = request['initial_ids']
            pair = None
            with phase('individual_mode_tracking'):
                if index:
                    controls = dict(request['controls'], marked_cells=marked) if case.geometry_order == 1 else request['controls']
                    pair = build_saved_mode_tracking(dict(schema_version=1, previous_run=runs[-1], current_run=str(run),
                                                         previous_ids=levels[-1]['current_mode_ids'], controls=controls))
                    ids = pair['tracking']['current_mode_ids']
                    if pair['status'] != 'PASS' or not pair['tracking']['individual_ids_complete']:
                        status = 'UNVERIFIED'
            mode = None if status == 'UNVERIFIED' else ids.index(request['mode_id'])
            q = None if mode is None else parse_json((run/'results.json').read_text())['modes'][mode]
            surface = quadrature = None
            if mode is not None:
                with phase('discrete_peak_intervals'):
                    if case.geometry_order == 2:
                        from .curved_adaptive_refinement import _surface
                        surface = _surface(current, mode, q)
                    else:
                        surface = surface_intervals(case, current, mode)
                if case.geometry_order == 2:
                    with phase('quadrature_indicator_and_form_check'):
                        from .curved_residual_indicator import curved_residual_indicator
                        from .curved_adaptive_refinement import _quadrature
                        low = curved_residual_indicator(current.case, current, mode=mode,
                                                        quadrature_order=current.case.quadrature_order)
                        quadrature = _quadrature(current, request, mode, low)
                        if not quadrature['passed']:
                            status = 'QUADRATURE_UNVERIFIED'
            row = dict(index=index, refinement_kind='initial' if not index else 'uniform_confirmation',
                       triangles=triangles, dofs=len(current.u), current_mode_ids=deepcopy(ids), mode_index=mode,
                       tracking=pair, quantities=q, surface=surface, quadrature_check=quadrature)
            runs.append(str(run)); levels.append(row); sources.append(source)
            with phase('uniform_quantity_confirmation'):
                if mode is not None and status == 'PAUSED':
                    confirmation = _confirmation(levels, request)
                    if confirmation['passed']:
                        status = 'TARGETS_MET'
            if implementation != _implementation_hashes() or sources != [_snapshot(Path(p)) for p in runs]:
                raise RuntimeError('uniform implementation or saved sources changed during execution')
            document = dict(schema_version=1, document_type='adaptive_efficiency_uniform_checkpoint',
                            request=request, status=status, level_runs=runs, levels=levels, sources=sources,
                            confirmation=confirmation, physical_acceptance_status='NOT_RUN', physical_error_bound=None,
                            scope='fresh uniform native FEM and original individual IDs; two consecutive quantity/peak interval changes; no independent reference acceptance or resume API')
            with phase('uniform_checkpoint_save'):
                with (directory/f'checkpoint-{index+1:03d}.json').open('x') as stream:
                    json.dump(document, stream, indent=2, allow_nan=False);stream.write('\n')
            if status != 'PAUSED':
                break
        except BaseException as error:
            with (directory/f'failure-{index+1:03d}.json').open('x') as stream:
                json.dump(dict(status='FAILED', level_index=index, run=str(run),
                               error_type=type(error).__name__, error=str(error), preceding_level_runs=runs), stream, indent=2)
            raise
    if status == 'PAUSED' and len(levels) == request['max_levels']:
        status = 'LEVEL_LIMIT'
    document['status'] = status
    with (directory/'result.json').open('x') as stream:
        json.dump(document, stream, indent=2, allow_nan=False);stream.write('\n')
    return document
