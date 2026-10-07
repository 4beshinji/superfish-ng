# SPDX-License-Identifier: Apache-2.0
"""Source-bound 3x3 geometry/FEM assessments with separate numerical gates.

Version 1 uses the complete N01 Case plan and strong individual mode tracking.
Version 2 replays one SHA-pinned historical single-mode ellipse without changing
its original acceptance policy or promoting it to a new three-mode result.
Neither version solves a new eigenproblem or accepts an NG physical reference.
"""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path

from .config import keys
from .curved_same_domain_tracking import compare_quadratic_boundaries
from .geometry_surface_fields import compare_geometry_surface_fields, _native_snapshot
from .geometry_surface_plan import build_geometry_surface_plan, _path, _bytes, _equal, _sha, _source_hashes
from .geometry_surface_numerics import (quantity_intervals, quantity_changes, boundary_error,
                                       mapped_moments, quadrature_check, ellipsoid_moments)
from .project import parse_json
from .saved import read_solution
from .saved_mode_tracking import _canonical
from .studies import _physical_spec
from .surface_convergence import LIMITS, _geometry_assessment


HISTORICAL_ELLIPSE_SHA = 'a025a9b0974bce2deec421032957fdd317733330b4fa7fdba1ce496eda48f0e2'


def _conjunction(values):
    if any(v is None for v in values):
        return None
    if any(type(v) is not bool for v in values):
        raise ValueError('numerical gates require boolean or explicit unresolved null evidence')
    return all(values)


def _status(gates):
    return 'UNVERIFIED' if any(v is None for v in gates.values()) else 'PASS' if all(gates.values()) else 'FAIL'


def assess_matrix_evidence(groups, geometry_fields, *, finite_peak_required):
    """Aggregate internally extracted evidence; this is not a native reader.

    Missing observations stay unresolved. Only the source-bound saved wrapper
    constructs authoritative evidence from native FEM files.
    """
    if type(finite_peak_required) is not bool:
        raise ValueError('finite_peak_required must be boolean')
    if len(groups) != 3 or any(len(g['rows']) != 3 or len(g['field_comparisons']) != 2 for g in groups) or len(geometry_fields) != 2:
        raise ValueError('separated surface assessment requires a complete 3x3 plan and two geometry links')
    required = tuple(LIMITS) if finite_peak_required else tuple(LIMITS)[:3]
    fixed = []
    for group in groups:
        changes = [quantity_changes(a['intervals'], b['intervals'], finite_peak_required=finite_peak_required)
                   for a, b in zip(group['rows'], group['rows'][1:])]
        quantity_gate = _conjunction([None if c['status'] == 'UNVERIFIED' else c['status'] == 'TARGETS_MET' for c in changes])
        field_gate = _conjunction([None if f['status'] == 'UNVERIFIED' else f['status'] == 'PASS' for f in group['field_comparisons']])
        quad_gate = _conjunction([None if r['quadrature']['status'] == 'UNVERIFIED' else r['quadrature']['status'] == 'PASS' for r in group['rows']])
        gates = dict(two_fem_intervals=quantity_gate, paired_target_fields=field_gate,
                     fixed_moments=group['fixed_moments'], quadratic_boundary_coincidence=group['boundary_coincidence'],
                     parent_child_ritz=group['ritz'], quadrature=quad_gate)
        fixed.append(dict(status=_status(gates), gates=gates, changes=changes,
                          required_quantities=list(required)))
    geometry_changes = [quantity_changes(a['rows'][-1]['intervals'], b['rows'][-1]['intervals'],
                                        finite_peak_required=finite_peak_required) for a, b in zip(groups, groups[1:])]
    error_keys = ('boundary_error_bound_m', 'relative_area_error', 'relative_volume_error')
    errors_resolved = all(g.get(n) is not None for g in groups for n in error_keys)
    decreasing = all(b[n] < a[n] for a, b in zip(groups, groups[1:]) for n in error_keys) if errors_resolved else None
    final_moments = all(groups[-1][n] < 1e-5 for n in error_keys[1:]) if errors_resolved else None
    expected = 'SMOOTH_WITHIN_TOLERANCE' if finite_peak_required else 'SINGULAR_GEOMETRY'
    geometry_statuses = [g['geometry_diagnostic']['status'] for g in groups]
    native_geometry = None if 'UNVERIFIED_GEOMETRY' in geometry_statuses else all(s == expected for s in geometry_statuses)
    gates = dict(each_fixed_geometry=_conjunction([None if f['status'] == 'UNVERIFIED' else f['status'] == 'PASS' for f in fixed]),
                 two_geometry_intervals=_conjunction([None if c['status'] == 'UNVERIFIED' else c['status'] == 'TARGETS_MET' for c in geometry_changes]),
                 geometry_target_fields=_conjunction([None if f['status'] == 'UNVERIFIED' else f['status'] == 'PASS' for f in geometry_fields]),
                 geometric_errors_decrease=decreasing, final_moments=final_moments, native_geometry=native_geometry)
    numerical_status = _status(gates)
    status = 'SINGULAR_GEOMETRY' if not finite_peak_required and all(s == expected for s in geometry_statuses) else numerical_status
    return dict(status=status, numerical_status=numerical_status, gates=gates,
                fixed_geometry_assessments=fixed, geometry_changes=geometry_changes,
                limits=deepcopy(LIMITS), final_relative_area_and_volume_limit=1e-5,
                physical_error_bound=None, physical_acceptance_status='UNVERIFIED',
                scope='both consecutive FEM changes at all three quadratic geometries and both finest-FEM geometry changes; separate field, moments, Ritz, quadrature and uncertain peak gates; empirical convergence only')


def _descriptor(request, root):
    version = request.get('schema_version') if isinstance(request, dict) else None
    if type(version) is not int or version not in (1, 2):
        raise ValueError('geometry surface matrix request requires schema_version 1 or 2')
    if version == 1:
        fields = ('schema_version', 'document_type', 'plan_request', 'runs')
        keys(request, fields, fields, 'geometry surface matrix request')
        _equal(request['document_type'], 'geometry_surface_matrix_request', 'matrix document type')
        plan = build_geometry_surface_plan(request['plan_request'], base_directory=root)
        if len(plan['cases']) != 1:
            raise ValueError('matrix plan_request must select exactly one complete catalog case')
        case = plan['cases'][0]
        data = dict(case_id=case['id'], expected_cases=[[r['case'] for r in group] for group in case['matrix']],
                    initial_ids=case['initial_ids'], target_id=case['target_mode_id'],
                    finite_peak_required=case['finite_peak_required'], reference=case['physical_reference'],
                    moments=(case['independent_geometry']['meridian_area_m2'], case['independent_geometry']['rotational_volume_m3']),
                    geometry_diagnostic=case['geometry_diagnostic'], plan=plan,
                    historical=None, historical_source=None, native_policy='N01_strong_individual_ids')
        runs = request['runs']
    else:
        fields = ('schema_version', 'document_type', 'archive_report')
        keys(request, fields, fields, 'historical ellipse matrix request')
        _equal(request['document_type'], 'historical_ellipse_surface_matrix_request', 'historical matrix document type')
        keys(request['archive_report'], ('path', 'sha256'), ('path', 'sha256'), 'historical ellipse report')
        reference = request['archive_report']; _equal(_sha(reference['sha256']), HISTORICAL_ELLIPSE_SHA, 'historical ellipse source SHA')
        path = _path(reference['path'], root); raw = _bytes(path)
        if hashlib.sha256(raw).hexdigest() != HISTORICAL_ELLIPSE_SHA:
            raise ValueError('historical ellipse report sha256 mismatch')
        historical = parse_json(raw.decode('utf-8'))
        if historical.get('status') != 'PASS' or len(historical.get('geometry_groups', [])) != 3:
            raise ValueError('historical ellipse source requires its original PASS and three geometry groups')
        runs = [[r['run'] for r in g['rows']] for g in historical['geometry_groups']]
        data = dict(case_id='historical-single-mode-ellipse', expected_cases=None,
                    initial_ids=['historical-target'], target_id='historical-target', finite_peak_required=True,
                    reference=dict(status='UNVERIFIED', rf_values=None, field_source=None,
                                   reason='original NG ellipse is a historical diagnostic, never an independent Maxwell or physical-peak reference'),
                    moments=ellipsoid_moments(.1, .08), geometry_diagnostic=None, plan=None,
                    historical=historical, historical_source=dict(path=str(path), sha256=HISTORICAL_ELLIPSE_SHA),
                    native_policy='original_single_mode_Study_fields_with_explicit_quadratic_boundary_checks')
    if type(runs) is not list or len(runs) != 3 or any(type(g) is not list or len(g) != 3 for g in runs):
        raise ValueError('runs must contain three geometry rows, each with three uniform FEM entries')
    paths = [[None if p is None else _path(p, root) for p in group] for group in runs]
    supplied = [p for g in paths for p in g if p is not None]
    if len(set(supplied)) != len(supplied):
        raise ValueError('matrix runs must identify distinct original native solutions; do not repeat one result')
    return data, paths


def _unresolved_field(reason):
    return dict(status='UNVERIFIED', reason=reason, comparison=None, previous_mode_index=None, current_mode_index=None)


def _field(previous, current, ids, target, mapping):
    if previous is None or current is None or ids is None or any(i is None for i in ids):
        return _unresolved_field('native source or all individual mode IDs are unavailable'), None
    try:
        report = compare_geometry_surface_fields(previous, current, ids, mapping=mapping)
    except ValueError as error:
        if 'UNVERIFIED' not in str(error):
            raise
        return _unresolved_field(str(error)), None
    next_ids = report['current_ids']
    complete = all(i is not None for i in next_ids)
    matches = [m for m in report['modes'] if m['previous_id'] == target]
    if not complete or len(matches) != 1 or not matches[0].get('pair_identified'):
        return dict(_unresolved_field('all individual correspondences must be identified before selecting the target'), comparison=report), None
    match = matches[0]
    return dict(status=match['status'], comparison=report,
                previous_mode_index=match['previous_mode_index'], current_mode_index=match['current_mode_index']), next_ids


def _row(solution, ids, target, run):
    blank = {n: None for n in LIMITS}
    if solution is None:
        return dict(run=None, status='UNVERIFIED', mode_index=None, intervals=blank,
                    triangles=None, degrees_of_freedom=None, moments=None,
                    quadrature=dict(status='UNVERIFIED', reason='native solve not supplied'), rf_values=None)
    index = ids.index(target) if ids is not None and target in ids and all(i is not None for i in ids) else None
    moments = mapped_moments(solution.space)
    q = solution.results['modes'][index] if index is not None else None
    return dict(run=str(run), status='IDENTIFIED' if q is not None else 'UNVERIFIED', mode_index=None if index is None else index+1,
                intervals=quantity_intervals(q) if q is not None else blank,
                triangles=len(solution.space.geometry.cell_nodes), degrees_of_freedom=len(solution.u),
                moments=list(moments), quadrature=quadrature_check(solution, index) if index is not None else dict(status='UNVERIFIED', reason='no verified individual target'),
                rf_values=deepcopy(q), refinement_level=solution.case.curved_refinement_levels)


def _historical_compatibility(groups, geometry_fields, descriptor):
    original = descriptor['historical']
    if original is None:
        return None
    failures = []
    for i, (new, old) in enumerate(zip(groups, original['geometry_groups'])):
        intervals = [r['intervals'] for r in new['rows']]
        changes = [quantity_changes(a, b) for a, b in zip(intervals, intervals[1:])]
        old_changes = [dict(passed=c['status'] == 'TARGETS_MET', relative_changes=c['relative_changes']) for c in changes]
        if _canonical(old_changes) != _canonical(old['fem_changes']): failures.append(f'geometry-{i}-quantity-changes')
        if _canonical(intervals) != _canonical([r['intervals'] for r in old['rows']]): failures.append(f'geometry-{i}-intervals')
        fields = [f['comparison']['legacy_comparison'] if f['comparison'] is not None else None for f in new['field_comparisons']]
        if _canonical(fields) != _canonical(old['field_comparisons']): failures.append(f'geometry-{i}-fields')
        quad = new['rows'][-1]['quadrature'].get('legacy_comparison')
        if _canonical(quad) != _canonical(old['quadrature']): failures.append(f'geometry-{i}-legacy-quadrature')
        gates = dict(two_fem_intervals=all(c['passed'] for c in old_changes),
                     paired_fields_and_rf=all(f is not None and f['status'] == 'PASS' for f in fields),
                     fixed_moments=new['fixed_moments'], parent_child_ritz=new['ritz'],
                     quadrature=quad is not None and quad['passed'])
        if _canonical(gates) != _canonical(old['gates']): failures.append(f'geometry-{i}-original-gates')
    changes = [quantity_changes(a['rows'][-1]['intervals'], b['rows'][-1]['intervals']) for a, b in zip(groups, groups[1:])]
    if _canonical([dict(passed=c['status'] == 'TARGETS_MET', relative_changes=c['relative_changes']) for c in changes]) != _canonical(original['geometry_changes']): failures.append('geometry-quantity-changes')
    fields = [f['comparison']['legacy_comparison'] if f['comparison'] is not None else None for f in geometry_fields]
    if _canonical(fields) != _canonical(original['geometry_field_comparisons']): failures.append('geometry-fields')
    decreasing = all(b[n] < a[n] for a, b in zip(groups, groups[1:]) for n in ('boundary_error_bound_m', 'relative_area_error', 'relative_volume_error'))
    gates = dict(each_fixed_geometry=all(g['fixed_moments'] and g['ritz'] and all(f['status'] == 'PASS' for f in g['field_comparisons']) and all(c['status'] == 'TARGETS_MET' for c in [quantity_changes(a['intervals'], b['intervals']) for a, b in zip(g['rows'], g['rows'][1:])]) and g['rows'][-1]['quadrature']['legacy_comparison']['passed'] for g in groups),
                 two_geometry_intervals=all(c['status'] == 'TARGETS_MET' for c in changes),
                 geometry_field_comparisons=all(f is not None and f['status'] == 'PASS' for f in fields),
                 geometric_errors_decrease=decreasing, archive_unchanged=True, source_unchanged=True)
    if _canonical(gates) != _canonical(original['gates']): failures.append('original-whole-gates')
    return dict(status='PASS' if not failures else 'FAIL', original_report_sha256=HISTORICAL_ELLIPSE_SHA,
                exact_original_quantities_fields_quadrature_and_gates=not failures, mismatches=failures,
                scope='original single-mode ellipse diagnostic acceptance only; new order24/all-row quadrature and new three-mode policy are reported separately')


def build_geometry_surface_matrix(request, *, base_directory=None):
    root = Path.cwd() if base_directory is None else Path(base_directory).resolve()
    source = _source_hashes(); descriptor, paths = _descriptor(request, root)
    flat = [p for g in paths for p in g if p is not None]; before = [_native_snapshot(p) for p in flat]
    solutions = [[None if p is None else read_solution(p) for p in group] for group in paths]
    expected = descriptor['expected_cases']; physical = None
    for g, group in enumerate(solutions):
        base = None; mesh = None
        for level, solution in enumerate(group):
            if solution is None: continue
            case = solution.case
            if expected is not None:
                _equal(case.to_dict(), expected[g][level], 'complete native matrix Case')
            else:
                if case.modes != 1 or case.geometry_order != 2 or case.element_order != 2 or case.quadrature_order != 12:
                    raise ValueError('historical ellipse requires its original single-mode P2 order12 native Cases')
                from .geometry_surface_plan import _independent_geometry
                curve = _independent_geometry(dict(axial_semiaxis_m=.1, radial_semiaxis_m=.08))
                _equal(case.curved_contour.to_dict()['curves'], curve['curves'], 'original ellipse whole meridian')
            if case.curved_refinement_steps or case.curved_refinement_levels != level:
                raise ValueError('matrix requires uniform FEM levels 0/1/2, without changed local history')
            raw = replace(case, curved_refinement_levels=0).to_dict()
            if base is None: base, mesh = raw, solution.source_mesh_data
            if raw != base or solution.source_mesh_data != mesh:
                raise ValueError('fixed geometry row must retain exactly one base Case and source mesh')
            spec = _physical_spec(case)
            if physical is None: physical = spec
            if spec != physical:
                raise ValueError('all geometry/FEM points require identical whole physical Cases')
    groups, coarse_links, ids_grid = [], [], []
    ids = descriptor['initial_ids']; target = descriptor['target_id']; historical = descriptor['historical'] is not None
    for g, group in enumerate(solutions):
        if g:
            link, ids = _field(solutions[g-1][0], group[0], ids_grid[g-1][0], target, 'analytic_geometry_approximations')
            coarse_links.append(link)
        row_ids = [ids]; fields = []; boundaries = []
        for level in (1, 2):
            a, b = group[level-1], group[level]
            if a is None or b is None: boundaries.append(None)
            else:
                compare_quadratic_boundaries(a, b); boundaries.append(True)
            field, ids = _field(a, b, row_ids[-1], target, 'analytic_geometry_approximations' if historical else 'curved_same_domain')
            fields.append(field); row_ids.append(ids)
        ids_grid.append(row_ids)
        rows = [_row(s, identity, target, p) for s, identity, p in zip(group, row_ids, paths[g])]
        moments = [r['moments'] for r in rows]
        fixed = all(abs(value[k]/moments[0][k]-1) < 2e-12 for value in moments for k in (0, 1)) if all(m is not None for m in moments) else None
        ritz = all(all(v <= u*(1+1e-10) for u, v in zip(a.frequencies_hz, b.frequencies_hz)) for a, b in zip(group, group[1:])) if all(s is not None for s in group) else None
        first = group[0]
        boundary = boundary_error(first.space, first.case.curved_contour) if first is not None else None
        geometry = _geometry_assessment(first.case.curved_contour) if first is not None else descriptor['geometry_diagnostic'] or dict(status='UNVERIFIED_GEOMETRY')
        groups.append(dict(rows=rows, field_comparisons=fields, fixed_moments=fixed, ritz=ritz,
                           boundary_coincidence=_conjunction(boundaries), geometry_diagnostic=geometry,
                           analytic_boundary=boundary,
                           boundary_error_bound_m=boundary['maximum_boundary_error_bound_m'] if boundary is not None else None,
                           relative_area_error=abs(moments[0][0]/descriptor['moments'][0]-1) if moments[0] is not None else None,
                           relative_volume_error=abs(moments[0][1]/descriptor['moments'][1]-1) if moments[0] is not None else None))
    geometry_fields = []
    for g in (0, 1):
        field, current_ids = _field(solutions[g][-1], solutions[g+1][-1], ids_grid[g][-1], target, 'analytic_geometry_approximations')
        if current_ids is not None and current_ids != ids_grid[g+1][-1]:
            field = dict(field, status='UNVERIFIED', reason='coarse geometry/refinement route and finest geometry route disagree on individual IDs')
        geometry_fields.append(field)
    assessment = assess_matrix_evidence(groups, geometry_fields, finite_peak_required=descriptor['finite_peak_required'])
    compatibility = _historical_compatibility(groups, geometry_fields, descriptor)
    if before != [_native_snapshot(p) for p in flat] or source != _source_hashes():
        raise ValueError('geometry surface matrix native/implementation sources changed during assessment')
    if descriptor['historical_source'] is not None:
        bound = descriptor['historical_source']
        if hashlib.sha256(_bytes(Path(bound['path']))).hexdigest() != bound['sha256']:
            raise ValueError('historical ellipse report changed during assessment')
    if descriptor['plan'] is not None:
        if _canonical(build_geometry_surface_plan(descriptor['plan']['request'])) != _canonical(descriptor['plan']):
            raise ValueError('geometry surface matrix catalog/reference plan changed during assessment')
    normalized = deepcopy(request)
    if historical: normalized['archive_report'] = descriptor['historical_source']
    else:
        normalized['plan_request'] = descriptor['plan']['request']
        normalized['runs'] = [[None if p is None else str(p) for p in group] for group in paths]
    return dict(schema_version=request['schema_version'], document_type='geometry_surface_matrix', request=normalized,
                status=assessment['status'], case_id=descriptor['case_id'], target_mode_id=target,
                native_policy=descriptor['native_policy'], sources=before, implementation_sha256=source,
                plan=descriptor['plan'], historical_source=descriptor['historical_source'],
                independent_reference=descriptor['reference'], geometry_groups=groups,
                coarse_geometry_identity_links=coarse_links, geometry_field_comparisons=geometry_fields,
                mode_ids_by_node=ids_grid, assessment=assessment, historical_compatibility=compatibility,
                planned_native_points=9, supplied_native_points=len(flat), new_fem_solves=0,
                physical_acceptance_status='UNVERIFIED', physical_error_bound=None,
                scope='source-identified native 3x3 matrix, target-only convergence with all individual IDs required, separate geometry/FEM/quadrature/field/discrete peak gates; no independent physical-peak guarantee')


def save_geometry_surface_matrix(request, path, *, base_directory=None):
    path = Path(path)
    if path.exists() or path.is_symlink(): raise FileExistsError(path)
    report = build_geometry_surface_matrix(request, base_directory=base_directory)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(report, indent=2, allow_nan=False)+'\n')
    return report


def read_geometry_surface_matrix(path):
    document = parse_json(_bytes(Path(path)).decode('utf-8'))
    if not isinstance(document, dict) or 'request' not in document:
        raise ValueError('saved matrix requires its source request')
    expected = build_geometry_surface_matrix(document['request'])
    if _canonical(document) != _canonical(expected):
        raise ValueError('geometry surface matrix replay differs from saved data or sources')
    return expected
