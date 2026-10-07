# SPDX-License-Identifier: Apache-2.0
"""Source-bound native P2 field comparisons for geometry/surface validators.

The legacy centroid/axis comparison is retained as a separate diagnostic.
Sample coverage and absolute field differences are explicit. Fixed quadratic
domains also require the stronger N01 native tracking controls. These comparisons
do not assess peaks, FEM error, quadrature convergence or independent physics.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

from .completion import required_files
from .config import Case, keys
from .curved_solution import CurvedSolution
from .curved_same_domain_tracking import compare_quadratic_boundaries, track_curved_same_domain_modes
from .geometry_surface_plan import TRACKING, FIELD_GATES, _path, _bytes, _equal, _source_hashes
from .project import parse_json
from .sampling import FieldSampler
from .saved import read_solution
from .saved_mode_tracking import _canonical
from .studies import RF_KEYS, _physical_spec


FIELDS = ('Hphi_A_per_m', 'Er_quadrature_V_per_m', 'Ez_quadrature_V_per_m')


def _nullable(values):
    array = np.asarray(values)
    if array.ndim > 1:
        return [_nullable(row) for row in array]
    return [float(v) if np.isfinite(v) else None for v in array]


def _relative_l2(previous, current, weights):
    scale = float(np.max(np.abs(previous), initial=0.))
    if not scale > 0 or not np.isfinite(scale):
        return None
    a, b = previous/scale, current/scale
    with np.errstate(over='ignore', invalid='ignore'):
        denominator = np.sum(weights*a*a)
        numerator = np.sum(weights*(b-a)**2)
        value = np.sqrt(numerator/denominator) if denominator > 0 else np.nan
    return float(value) if np.isfinite(value) else None


def _validate_pair(previous, current, ids, mapping):
    if mapping not in ('analytic_geometry_approximations', 'curved_same_domain'):
        raise ValueError('mapping must be analytic_geometry_approximations or curved_same_domain')
    if any(not isinstance(s, CurvedSolution) for s in (previous, current)):
        raise ValueError('geometry surface field comparison requires native CurvedSolution fields')
    if _physical_spec(previous.case) != _physical_spec(current.case):
        raise ValueError('geometry surface field comparison requires identical whole physical Cases')
    for solution in (previous, current):
        case = solution.case
        if case.model is None:
            raise ValueError('geometry surface field comparison requires explicit vacuum m=0 TM physics')
        model = case.model.to_dict()
        if ((model['physics'], model['coordinates'], model['polarization'], model['azimuthal_index']) !=
                ('rf_eigenmode', 'axisymmetric', 'tm', 0) or case.geometry_order != 2 or case.element_order != 2
                or case.z_min != 'pec' or case.z_max != 'pec' or solution.reflection_source_case is not None
                or model['materials'] != [dict(id='vacuum', type='vacuum')]
                or model['regions'] != [dict(id='cavity', material='vacuum', domain='interior')]
                or any(tag not in ('axis', 'pec') for tag in solution.space.boundary_tags)):
            raise ValueError('geometry surface field comparison supports closed vacuum axis-connected m=0 TM P2 only')
        f = solution.frequencies_hz
        if (f.shape != (case.modes,) or solution.u.shape != (len(solution.space.geometry.points_rz_m), case.modes)
                or not np.isfinite(solution.u).all() or not np.isfinite(f).all()
                or np.any(f <= 0) or np.any(np.diff(f) < 0)):
            raise ValueError('native field dimensions and frequency ranks must be finite and ordered')
    if (type(ids) is not list or len(ids) != previous.case.modes or
            any(type(i) is not str or not i.strip() for i in ids) or len(set(ids)) != len(ids)):
        raise ValueError('previous_ids must name every previous frequency rank exactly once')
    if mapping == 'curved_same_domain':
        return compare_quadratic_boundaries(previous, current)
    return None


def _samples(previous, current):
    maps = previous.space.geometry.local_maps
    indices = np.linspace(0, len(maps)-1, min(4096, len(maps)), dtype=int)
    mapped = [maps[i].evaluate([[1/3, 1/3]]) for i in indices]
    positions = np.concatenate([s['points_rz_m'] for s in mapped])
    weights = np.concatenate([s['determinant_m2'] for s in mapped])*positions[:, 0]
    if not np.isfinite(weights).all() or np.any(weights <= 0):
        raise ValueError('geometry surface samples require positive finite Jacobian-radius weights')
    sampled = []
    for solution in (previous, current):
        sampler = FieldSampler.from_solution(solution)
        columns = [sampler.evaluate(positions, i, outside='nan') for i in range(solution.case.modes)]
        sampled.append({name: np.column_stack([c[name] for c in columns]) for name in FIELDS})
    hcommon = np.isfinite(sampled[0][FIELDS[0]]).all(axis=1) & np.isfinite(sampled[1][FIELDS[0]]).all(axis=1)
    common = hcommon.copy()
    for side in sampled:
        for values in side.values():
            common &= np.isfinite(values).all(axis=1)
    record = dict(reference_cell_indices=indices.tolist(), points_rz_m=positions.tolist(),
                  jacobian_radius_weights_m3=weights.tolist(), hphi_common_mask=hcommon.tolist(),
                  all_fields_common_mask=common.tolist(), selected_samples=len(positions),
                  available_reference_cells=len(maps), common_hphi_samples=int(hcommon.sum()),
                  common_all_fields_samples=int(common.sum()), missing_all_fields_samples=int((~common).sum()),
                  missing_indices=np.flatnonzero(~common).tolist(),
                  missing_weight_fraction=float(np.sum(weights[~common])/np.sum(weights)),
                  previous_fields={n: _nullable(v) for n, v in sampled[0].items()},
                  current_fields={n: _nullable(v) for n, v in sampled[1].items()},
                  criterion='first native mesh centroids and determinant*r weights, capped at 4096 cells; missing points retained; no full-domain quadrature or coverage proof',
                  whole_domain_coverage_proven=False)
    return sampled, weights, hcommon, common, record


def _axis_comparison(previous, current, i, j, sign):
    knots = np.union1d(*[s.space.geometry.points_rz_m[s.space.axis_dofs, 1] for s in (previous, current)])
    q, w = np.polynomial.legendre.leggauss(3)
    lo, hi = knots[:-1], knots[1:]
    z = ((lo+hi)[:, None]/2+(hi-lo)[:, None]*q/2).ravel()
    weights = ((hi-lo)[:, None]*w/2).ravel()
    points = np.column_stack((np.zeros_like(z), z))
    a = FieldSampler.from_solution(previous).evaluate(points, int(i))['Ez_quadrature_V_per_m']
    b = FieldSampler.from_solution(current).evaluate(points, int(j))['Ez_quadrature_V_per_m']*sign
    # Keep the original Study dot-product criterion. No independent per-field
    # phase or amplitude fitting is allowed after aligning the Hphi sign.
    norm = float(np.dot(weights, a*a))
    error = float(np.sqrt(np.dot(weights, (b-a)**2)/norm)) if norm > 0 else None
    if error is not None and not np.isfinite(error):
        error = None
    return error, dict(points_rz_m=points.tolist(), weights_m=weights.tolist(),
                       previous_ez_v_per_m=_nullable(a), sign_aligned_current_ez_v_per_m=_nullable(b),
                       rule='three Gauss points per union axis knot interval; one sign from Hphi; no amplitude adjustment')


def _legacy_mode(previous, current, i, j, overlap, identified, axis_error):
    qa = getattr(previous, 'results', {}).get('modes', [])
    qb = getattr(current, 'results', {}).get('modes', [])
    if len(qa) != previous.case.modes or len(qb) != current.case.modes:
        return None
    qa, qb = qa[i], qb[j]
    changes = {k: abs(qb[k]/qa[k]-1) if qa[k] else None for k in ('frequency_hz', *RF_KEYS)}
    gates = dict(frequency=changes['frequency_hz'] < .001,
                 axis_field=axis_error is not None and axis_error < .01,
                 rf=all(changes[k] is not None and changes[k] < .01 for k in RF_KEYS))
    verified = identified and axis_error is not None and all(v is not None for v in changes.values())
    return dict(first_mode_index=int(i+1), second_mode_index=int(j+1), field_overlap=overlap,
                pair_identified=identified, relative_changes=changes, axis_relative_l2=axis_error,
                rq_absolute_change_ohm=abs(qb['r_over_q_accelerator_ohm']-qa['r_over_q_accelerator_ohm']),
                gates=gates, status=('PASS' if all(gates.values()) else 'FAIL') if verified else 'UNVERIFIED')


def validate_native_resources(resources,*,maximum_budget=8388608):
    """Explicit computational resources; original field gates remain fixed."""
    if type(maximum_budget) is not int or maximum_budget not in (8388608,16777216):
        raise ValueError('native resource budget limit must be 8388608 or 16777216')
    keys(resources, ('sample_budget', 'sampling'), ('sample_budget', 'sampling'), 'native tracking resources')
    budget=resources['sample_budget']
    if type(budget) is not int or not 1<=budget<=maximum_budget:
        raise ValueError(f'native tracking sample_budget must be an integer from 1 to {maximum_budget}')
    if resources['sampling']!='uniform_parent_p2':
        raise ValueError('native tracking resources require sampling=uniform_parent_p2; original inverse sampling remains the default')
    return deepcopy(resources)


def compare_geometry_surface_fields(previous, current, previous_ids, *, mapping, native_resources=None,
                                    native_resource_budget_limit=8388608):
    """Compare provided native fields; saved wrapper additionally verifies FEM/RF.

    Polynomial fixtures can exercise this in-memory diagnostic, but are not
    eigenpairs. Only the saved wrapper provides the native eigenpair provenance.
    """
    if type(native_resource_budget_limit) is not int or native_resource_budget_limit not in (8388608,16777216):
        raise ValueError('native resource budget limit must be 8388608 or 16777216')
    if native_resources is None and native_resource_budget_limit!=8388608:
        raise ValueError('extended native resource budget limit requires explicit native resources')
    if native_resources is not None:
        native_resources=validate_native_resources(native_resources,maximum_budget=native_resource_budget_limit)
        if mapping!='curved_same_domain':
            raise ValueError('native tracking resources apply only to fixed quadratic domain comparisons')
    boundary = _validate_pair(previous, current, previous_ids, mapping)
    sampled, weights, hcommon, common, sampling = _samples(previous, current)
    modes, legacy_modes, current_ids = [], [], [None]*current.case.modes
    if hcommon.sum() >= 10:
        a, b = [side[FIELDS[0]][hcommon]*np.sqrt(weights[hcommon, None]) for side in sampled]
        with np.errstate(divide='ignore', invalid='ignore', over='ignore'):
            signed = a.T@b/np.outer(np.linalg.norm(a, axis=0), np.linalg.norm(b, axis=0))
        scores = np.abs(signed)
        rows, columns = linear_sum_assignment(np.where(np.isfinite(scores), 1-scores, 1e6))
        for i, j in zip(rows, columns):
            score = float(scores[i, j])
            if not np.isfinite(score):
                modes.append(dict(previous_mode_index=int(i+1), current_mode_index=int(j+1),
                                  previous_id=previous_ids[i], status='UNVERIFIED', reason='unresolved Hphi norm'))
                continue
            alternatives = np.concatenate((np.delete(scores[i], j), np.delete(scores[:, j], i)))
            competing = float(np.max(alternatives[np.isfinite(alternatives)], initial=0.))
            gap = any(np.any(np.delete(abs(s.frequencies_hz/s.frequencies_hz[k]-1), k) < 1e-6)
                      for s, k in ((previous, i), (current, j)))
            identified = bool(score >= FIELD_GATES['legacy_pair_overlap'] and
                              score-competing >= FIELD_GATES['legacy_pair_margin'] and not gap)
            sign = -1 if signed[i, j] < 0 else 1
            axis_error, axis = _axis_comparison(previous, current, i, j, sign)
            herror = eerror = None
            if common.any():
                herror = _relative_l2(sampled[0][FIELDS[0]][common, i],
                                      sign*sampled[1][FIELDS[0]][common, j], weights[common])
                electric = [np.column_stack([side[name][common, rank] for name in FIELDS[1:]])
                            for side, rank in ((sampled[0], i), (sampled[1], j))]
                eerror = _relative_l2(electric[0], sign*electric[1], weights[common, None])
            gates = dict(pair_identified=identified, axis_field=axis_error is not None and axis_error < FIELD_GATES['native_axis_relative_l2'],
                         sample_availability=bool(common.all()), finite_electric_magnetic_diagnostics=herror is not None and eerror is not None)
            status = 'UNVERIFIED' if not identified or axis_error is None or not gates['sample_availability'] or not gates['finite_electric_magnetic_diagnostics'] else 'PASS' if gates['axis_field'] else 'FAIL'
            modes.append(dict(previous_mode_index=int(i+1), current_mode_index=int(j+1), previous_id=previous_ids[i],
                              field_overlap=score, signed_hphi_overlap=float(signed[i, j]), competing_overlap=competing,
                              assignment_margin=score-competing, near_degenerate=bool(gap), pair_identified=identified,
                              single_hphi_sign=sign, hphi_sample_relative_l2=herror,
                              electric_meridian_sample_relative_l2=eerror, axis_relative_l2=axis_error,
                              axis_sampling=axis, gates=gates, status=status))
            if identified:
                current_ids[j] = previous_ids[i]
            legacy = _legacy_mode(previous, current, i, j, score, identified, axis_error)
            if legacy is not None:
                legacy_modes.append(legacy)
    native = None
    if mapping == 'curved_same_domain':
        count = sum(len(s.space.geometry.cell_nodes) for s in (previous, current))*TRACKING['sample_order']**2
        budget=262144 if native_resources is None else native_resources['sample_budget']
        if count > budget:
            reason=('N01 sample_order=10 exceeds native 262144 sample budget' if native_resources is None else
                    f'N01 sample_order=10 requires {count} samples, exceeding declared budget {budget}')
            native = dict(status='UNVERIFIED', reason=reason,
                          planned_samples=count, sample_budget=budget, current_mode_ids=[None]*current.case.modes,
                          individual_ids_complete=False)
        else:
            extras={} if native_resources is None else dict(sample_budget=budget,uniform_parent_sampling=True)
            if native_resource_budget_limit!=8388608:extras['sample_budget_limit']=native_resource_budget_limit
            native = track_curved_same_domain_modes(previous, current, previous_ids, **TRACKING, **extras)
    statuses = [m['status'] for m in modes]
    resolved = len(modes) == previous.case.modes and all(s != 'UNVERIFIED' for s in statuses)
    native_identified = native is None or (native['status'] == 'PASS' and native['individual_ids_complete'])
    status = 'UNVERIFIED' if not resolved or not native_identified else 'FAIL' if 'FAIL' in statuses else 'PASS'
    legacy_statuses = [m['status'] for m in legacy_modes]
    legacy_status = 'UNVERIFIED' if len(legacy_modes) != previous.case.modes or 'UNVERIFIED' in legacy_statuses else 'PASS' if all(s == 'PASS' for s in legacy_statuses) else 'FAIL'
    legacy_report = dict(status=legacy_status, pairing='same geometry; sampled magnetic-field overlap', samples=int(hcommon.sum()),
                         sampling='first mesh reference centroids mapped to physical points; Jacobian times radius weights; common domain only',
                         limits=dict(frequency=.001, rf=.01, axis_field=.01, pair_overlap=.98, pair_margin=.02), modes=legacy_modes,
                         surface_field='physical surface-peak convergence not assessed by this Study')
    if native is not None:
        current_ids = native['current_mode_ids'] if native_identified else [None]*current.case.modes
    native_controls=deepcopy(TRACKING) if native is not None else None
    if native_resources is not None and native_controls is not None:
        native_controls['resource_limits']=native_resources
        if native_resource_budget_limit!=8388608:
            native_controls['maximum_sample_budget']=native_resource_budget_limit
    return dict(status=status, mapping=mapping, previous_ids=deepcopy(previous_ids), current_ids=current_ids,
                modes=modes, sampling=sampling, legacy_comparison=legacy_report,
                native_fixed_geometry_tracking=native, quadratic_boundary_coincidence=boundary,
                native_controls=native_controls,
                field_gates=deepcopy(FIELD_GATES), physical_error_bound=None,
                continuous_field_accuracy='UNVERIFIED',
                scope='Hphi correspondence plus absolute axis Ez gate; centroid electric/magnetic relative L2 diagnostics with explicit missing samples; no full-domain field error bound, FEM/geometry/peak/quadrature acceptance or independent reference')


def _native_snapshot(directory):
    # Bind every completion-owned byte, including display/axis exports. This
    # rejects late changes even after the native reader finished checking them.
    case = Case.load(directory/'case.json')
    results = parse_json(_bytes(directory/'results.json').decode('utf-8'))
    manifest = parse_json(_bytes(directory/'save_complete.json').decode('utf-8'))
    keys(manifest, ('completion_version', 'files'), ('completion_version', 'files'), 'native completion')
    _equal(manifest['completion_version'], 1, 'native completion version')
    names = required_files(case, results)
    if type(manifest['files']) is not dict or set(manifest['files']) != names:
        raise ValueError('native completion requires exactly all declared output files')
    actual = {name: hashlib.sha256(_bytes(directory/name)).hexdigest() for name in sorted(names)}
    if actual != manifest['files']:
        raise ValueError('native source bytes disagree with completion manifest')
    actual['save_complete.json'] = hashlib.sha256(_bytes(directory/'save_complete.json')).hexdigest()
    return dict(directory=str(directory), sha256=actual)


def build_saved_geometry_surface_fields(request, *, base_directory=None):
    fields = ('schema_version', 'document_type', 'previous_run', 'current_run', 'previous_ids', 'mapping')
    keys(request, fields, fields, 'geometry surface field request')
    _equal(request['schema_version'], 1, 'geometry surface field version')
    _equal(request['document_type'], 'geometry_surface_field_request', 'geometry surface field document type')
    if request['mapping'] not in ('curved_same_domain', 'analytic_geometry_approximations'):
        raise ValueError('mapping requires curved_same_domain or analytic_geometry_approximations')
    root = Path.cwd() if base_directory is None else Path(base_directory).resolve()
    paths = [_path(request[name], root) for name in ('previous_run', 'current_run')]
    before = [_native_snapshot(p) for p in paths]; source = _source_hashes()
    solutions = [read_solution(p) for p in paths]
    report = compare_geometry_surface_fields(*solutions, request['previous_ids'], mapping=request['mapping'])
    if before != [_native_snapshot(p) for p in paths] or source != _source_hashes():
        raise ValueError('geometry surface field sources changed during comparison')
    normalized = deepcopy(request)
    normalized.update(previous_run=str(paths[0]), current_run=str(paths[1]))
    return dict(schema_version=1, document_type='saved_geometry_surface_fields', request=normalized,
                sources=before, implementation_sha256=source, status=report['status'], comparison=report,
                new_fem_solves=0, native_eigenpairs_revalidated=True, physical_error_bound=None,
                scope='verified saved native FEM/RF fields and completion-owned bytes; no new eigensolve; field-pair diagnostic only')


def save_geometry_surface_fields(request, path, *, base_directory=None):
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    result = build_saved_geometry_surface_fields(request, base_directory=base_directory)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False)+'\n')
    return result


def read_geometry_surface_fields(path):
    document = parse_json(_bytes(Path(path)).decode('utf-8'))
    if not isinstance(document, dict) or 'request' not in document:
        raise ValueError('saved geometry surface fields require a request')
    expected = build_saved_geometry_surface_fields(document['request'])
    if _canonical(document) != _canonical(expected):
        raise ValueError('geometry surface field replay differs from saved data or sources')
    return expected
