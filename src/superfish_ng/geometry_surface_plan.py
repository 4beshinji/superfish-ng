# SPDX-License-Identifier: Apache-2.0
"""Strict input and provenance plans for separated geometry/surface validation.

This module does not solve, assess FEM convergence, or import a physical
reference from an NG result. Historical accepted reports are diagnostic evidence
only. The analytical sphere is regenerated without numerical FEM input.
"""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

from scipy.integrate import quad

from .analytic_sphere import SphereTM
from .config import Case, keys, positive
from .project import parse_json
from .saved_mode_tracking import _canonical
from .surface_convergence import LIMITS, _geometry_assessment


TRACKING = dict(mapping='curved_same_domain', sample_order=10, minimum_overlap=.98,
                minimum_assignment_margin=.05, relative_cluster_gap=1e-6,
                minimum_relative_singular_value=1e-8)
FIELD_GATES = dict(native_axis_relative_l2=.01, legacy_pair_overlap=.98,
                   legacy_pair_margin=.02, relative_cluster_gap=1e-6,
                   sphere_independent_volume_electric_magnetic_relative_l2=.01,
                   modern_reference_volume_electric_magnetic_relative_l2=.005)
CATALOG_FIELDS = ('schema_version', 'document_type', 'scope', 'quantity_change_limits',
                  'field_gates', 'native_tracking_controls', 'fixed_geometry_fem_requirement',
                  'geometry_requirement', 'quadrature', 'records', 'reference_reports',
                  'independent_reference_route', 'baseline_preservation')
RECORD_FIELDS = ('id', 'synthetic', 'base_case', 'geometry_chord_tolerances_m',
                 'fem_uniform_levels', 'matrix_size', 'target_mode_id', 'initial_ids',
                 'geometry_parameters', 'independent_meridian_area_m2',
                 'independent_rotational_volume_m3', 'expected_geometry_status',
                 'physical_reference', 'finite_peak_required', 'physical_peak_reference')
RF_REFERENCE_KEYS = ('frequency_hz', 'r_over_q_accelerator_ohm',
                     'r_over_q_circuit_ohm', 'geometry_factor_ohm')


def _text(value, name):
    if type(value) is not str or not value.strip():
        raise ValueError(f'{name} requires nonempty text')
    return value


def _equal(actual, expected, name):
    if _canonical(actual) != _canonical(expected):
        raise ValueError(f'{name} differs from the fixed N01 contract')


def _sha(value):
    if type(value) is not str or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('sha256 requires 64 lowercase hexadecimal characters')
    return value


def _path(value, root):
    path = Path(_text(value, 'source path'))
    path = path if path.is_absolute() else root/path
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError(f'source requires regular files without symlinks: {path}')
    return path.resolve()


def _bytes(path):
    if not path.is_file() or path.is_symlink():
        raise ValueError(f'source requires a regular file: {path}')
    return path.read_bytes()


def _source_hashes():
    root = Path(__file__).resolve().parent
    return {str(p): hashlib.sha256(_bytes(p)).hexdigest() for p in sorted(root.glob('*.py'))}


def _line(length):
    return dict(type='line', start_zr_m=[0., 0.], end_zr_m=[length, 0.])


def _arc(z, r, a, b, start, sweep):
    return dict(type='ellipse_arc', center_zr_m=[z, r], semiaxes_m=[a, b],
                start_rad=start, sweep_rad=sweep, rotation_rad=0.)


def _independent_geometry(parameters):
    """Explicit r(z) quadrature/closed forms, independent of native moments."""
    if 'axial_semiaxis_m' in parameters:
        names = ('axial_semiaxis_m', 'radial_semiaxis_m')
        keys(parameters, names, names, 'ellipsoid parameters')
        a, b = [positive(parameters[n], n) for n in names]
        return dict(kind='sphere' if a == b else 'ellipsoid',
                    curves=[_line(2*a), _arc(a, 0., a, b, 0., math.pi)],
                    moments=[math.pi*a*b/2, 4*math.pi*a*b*b/3],
                    status='SMOOTH_WITHIN_TOLERANCE', integration_error_estimates=None,
                    method='independent closed ellipsoid moments pi*a*b/2 and 4*pi*a*b^2/3')
    rounded = 'fillet_radius_m' in parameters
    names = ('lobe_radius_m', 'half_center_separation_m') + (
        ('fillet_radius_m', 'fillet_center_radius_m', 'throat_radius_m') if rounded else
        ('conductor_tip_angle_rad', 'vacuum_interior_angle_rad', 'throat_radius_m'))
    keys(parameters, names, names, 'two-lobe parameters')
    values = {n: positive(parameters[n], n) for n in names}
    radius, d = values['lobe_radius_m'], values['half_center_separation_m']
    if not d < radius:
        raise ValueError('two-lobe half_center_separation_m must be below lobe_radius_m')
    length = 2*(radius+d)
    if rounded:
        rho = values['fillet_radius_m']
        c = math.sqrt((radius+rho)**2-d*d)
        if c <= rho:
            raise ValueError('rounded two-lobe must have a positive axis-connected throat')
        for name, expected in (('fillet_center_radius_m', c), ('throat_radius_m', c-rho)):
            _equal(parameters[name], expected, name)
        alpha = math.atan2(c, d)
        curves = [_line(length), _arc(radius+2*d, 0., radius, radius, 0., math.pi-alpha),
                  _arc(radius+d, c, rho, rho, -alpha, -math.pi+2*alpha),
                  _arc(radius, 0., radius, radius, alpha, math.pi-alpha)]
        s = radius*d/(radius+rho)
        left, right = radius+s, radius+2*d-s
        segments = [(0., left, lambda z: math.sqrt(radius**2-(z-radius)**2)),
                    (left, right, lambda z: c-math.sqrt(rho**2-(z-radius-d)**2)),
                    (right, length, lambda z: math.sqrt(radius**2-(z-radius-2*d)**2))]
    else:
        alpha = math.acos(d/radius)
        for name, expected in (('conductor_tip_angle_rad', 2*alpha),
                               ('vacuum_interior_angle_rad', 2*math.pi-2*alpha),
                               ('throat_radius_m', math.sqrt(radius*radius-d*d))):
            _equal(parameters[name], expected, name)
        curves = [_line(length), _arc(radius+2*d, 0., radius, radius, 0., math.pi-alpha),
                  _arc(radius, 0., radius, radius, alpha, math.pi-alpha)]
        segments = [(0., radius+d, lambda z: math.sqrt(radius**2-(z-radius)**2)),
                    (radius+d, length, lambda z: math.sqrt(radius**2-(z-radius-2*d)**2))]
    moments, errors = [], []
    for power in (1, 2):
        integrals = [quad(lambda z: f(z)**power, lo, hi, epsabs=2e-15,
                          epsrel=2e-13, limit=200) for lo, hi, f in segments]
        factor = math.pi if power == 2 else 1.
        moments.append(factor*math.fsum(v for v, _ in integrals))
        errors.append(factor*math.fsum(e for _, e in integrals))
    return dict(kind='rounded_two_lobe' if rounded else 'sharp_two_lobe', curves=curves,
                moments=moments, integration_error_estimates=errors,
                status='SMOOTH_WITHIN_TOLERANCE' if rounded else 'SINGULAR_GEOMETRY',
                method='independent explicit piecewise r(z), area integral r dz, volume pi integral r^2 dz; SciPy error estimates are not certified bounds')


def _physical_reference(record, case, geometry):
    reference = record['physical_reference']
    allowed = ('status', 'rf_values', 'field_source', 'source', 'prior_report', 'legacy_computed_modes')
    keys(reference, allowed, ('status', 'rf_values', 'field_source'), 'physical reference')
    if 'legacy_computed_modes' in reference:
        _equal(reference['legacy_computed_modes'], 1, 'historical mode count')
    status = reference['status']
    if status == 'ANALYTICAL_REFERENCE_AVAILABLE':
        if geometry['kind'] != 'sphere':
            raise ValueError('SphereTM independent reference requires an exact spherical meridian')
        _equal(reference.get('field_source'), 'superfish_ng.analytic_sphere.SphereTM', 'analytical field source')
        _equal(reference.get('source'), 'docs/SPHERE_REFERENCE.md', 'analytical provenance')
        a = record['geometry_parameters']['axial_semiaxis_m']
        analytical = SphereTM(a, beta=case.beta, conductivity_s_per_m=case.conductivity_s_per_m,
                              normalization_j=case.normalization_j).quantities()
        keys(reference['rf_values'], RF_REFERENCE_KEYS, RF_REFERENCE_KEYS, 'analytical RF values')
        for name in RF_REFERENCE_KEYS:
            value = positive(reference['rf_values'][name], name)
            if abs(value/analytical[name]-1) > 2e-12:
                raise ValueError(f'independent analytical reference {name} differs from SphereTM')
        _equal(record['physical_peak_reference'], 'SphereTM independent PEC boundary fields', 'sphere peak source')
        return dict(status='AVAILABLE', kind='analytical_sphere',
                    rf_values={n: analytical[n] for n in RF_REFERENCE_KEYS},
                    field_source=reference['field_source'], comparison_status='NOT_RUN',
                    independent_of_ng_eigensolve=True, physical_error_bound=None,
                    physical_peak_comparison_status='NOT_RUN')
    if status not in ('INDEPENDENT_MAXWELL_REFERENCE_UNVERIFIED', 'SINGULAR_PEAK_CONTROL'):
        raise ValueError('physical reference kind unsupported; NG reports cannot be independent references')
    if 'source' in reference or reference['rf_values'] is not None or reference['field_source'] is not None or record['physical_peak_reference'] is not None:
        raise ValueError('missing independent physical reference must retain null values/source/peaks; NG output is diagnostic only')
    expected = 'SINGULAR_PEAK_CONTROL' if geometry['kind'] == 'sharp_two_lobe' else 'INDEPENDENT_MAXWELL_REFERENCE_UNVERIFIED'
    _equal(status, expected, 'physical reference status')
    return dict(status='UNVERIFIED', kind='independent_maxwell_not_available', rf_values=None,
                field_source=None, comparison_status='UNVERIFIED', physical_error_bound=None,
                physical_peak_comparison_status='NOT_APPLICABLE_SINGULAR' if not record['finite_peak_required'] else 'UNVERIFIED',
                reason='no supported independent Maxwell/physical peak artifact; historical NG reports and the planned finest NG solve are not independent references')


def _historical_report(reference, root):
    fields = ('path', 'sha256', 'status', 'new_fem')
    keys(reference, fields, fields, 'historical diagnostic report')
    _equal(reference['status'], 'PREVIOUSLY_ACCEPTED', 'historical report status')
    _equal(reference['new_fem'], 0, 'historical report new_fem')
    expected = _sha(reference['sha256']); path = _path(reference['path'], root)
    result = dict(path=str(path), expected_sha256=expected, role='historical_diagnostic_only',
                  independent_maxwell_reference=False, new_fem=0)
    if not path.exists():
        return dict(result, status='UNVERIFIED', actual_sha256=None,
                    reason='historical diagnostic artifact is absent; not regenerated')
    data = _bytes(path); actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        raise ValueError(f'historical diagnostic sha256 mismatch: {path}')
    report = parse_json(data.decode('utf-8'))
    if not isinstance(report, dict) or not (report.get('status') == 'PASS' or report.get('passed') is True):
        raise ValueError(f'historical diagnostic report is not accepted: {path}')
    if report.get('status') in ('FAIL', 'UNVERIFIED') or report.get('passed') is False:
        raise ValueError(f'historical diagnostic report has conflicting acceptance: {path}')
    return dict(result, status='VERIFIED_HISTORY', actual_sha256=actual,
                prior_status=report.get('status'), prior_passed=report.get('passed'))


def _record_plan(record, reports, root):
    keys(record, RECORD_FIELDS+('historical_ng_baseline',), RECORD_FIELDS, 'geometry surface case')
    _text(record['id'], 'case id'); _equal(record['synthetic'], True, 'synthetic shape')
    case = Case.from_dict(record['base_case'])
    if (case.geometry_type != 'curved_contour' or case.geometry_order != 2 or case.element_order != 2
            or case.quadrature_order != 12 or case.curved_refinement_levels != 0 or case.curved_refinement_steps
            or case.model is None):
        raise ValueError('geometry surface plan requires an unrefined native P2 curved TM Case at quadrature order 12')
    model = case.model.to_dict()
    if (model['physics'], model['coordinates'], model['polarization'], model['azimuthal_index']) != ('rf_eigenmode', 'axisymmetric', 'tm', 0):
        raise ValueError('geometry surface plan supports only vacuum closed PEC axis-connected m=0 TM')
    if (model['materials'] != [dict(id='vacuum', type='vacuum')] or
            model['regions'] != [dict(id='cavity', material='vacuum', domain='interior')]):
        raise ValueError('geometry surface plan supports only the canonical single vacuum cavity')
    _equal(case.beta, 1., 'beta'); _equal(case.normalization_j, 1., 'peak energy normalization')
    _equal(case.conductivity_s_per_m, 5.8e7, 'conductivity')
    _equal(case.z_min, 'pec', 'z_min'); _equal(case.z_max, 'pec', 'z_max')
    _equal(case.active_length_m, None, 'explicit active length')
    _equal(case.voltage_interval_m, None, 'explicit voltage interval')
    _equal(case.phase_origin_m, None, 'explicit phase origin')
    if case.modes < 3:
        raise ValueError('new geometry surface cases require the target and at least two guard modes')
    ids = record['initial_ids']
    if type(ids) is not list or len(ids) != case.modes or any(type(i) is not str or not i.strip() for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('initial_ids must name every computed mode exactly once')
    if record['target_mode_id'] not in ids:
        raise ValueError('target_mode_id must occur in initial_ids; ranks are not labels')
    _equal(record['fem_uniform_levels'], [0, 1, 2], 'three uniform FEM levels')
    _equal(record['matrix_size'], [3, 3], 'geometry/FEM matrix size')
    tolerances = record['geometry_chord_tolerances_m']
    if type(tolerances) is not list or len(tolerances) != 3:
        raise ValueError('geometry_chord_tolerances_m requires three decreasing positive levels')
    tolerances = [positive(v, 'chord tolerance') for v in tolerances]
    if not all(a > b for a, b in zip(tolerances, tolerances[1:])) or tolerances[0] != case.curve_chord_tolerance_m:
        raise ValueError('chord tolerances must decrease and start at the base Case value')
    geometry = _independent_geometry(record['geometry_parameters'])
    native = case.curved_contour.to_dict()
    _equal(native['curves'], geometry['curves'], 'whole independent meridian')
    _equal(native['edge_tags'], ['axis']+['pec']*(len(geometry['curves'])-1), 'whole boundary tags')
    diagnostic = _geometry_assessment(case.curved_contour)
    _equal(record['expected_geometry_status'], geometry['status'], 'expected geometry status')
    _equal(diagnostic['status'], geometry['status'], 'native geometry diagnostic')
    _equal(record['finite_peak_required'], geometry['status'] != 'SINGULAR_GEOMETRY', 'finite peak requirement')
    declared = [positive(record[n], n) for n in ('independent_meridian_area_m2', 'independent_rotational_volume_m3')]
    actual = [case.curved_contour.area_m2, case.curved_contour.volume_m3]
    for source, moments in (('declared', declared), ('native', actual)):
        if any(abs(v/ref-1) > 2e-12 for v, ref in zip(moments, geometry['moments'])):
            raise ValueError(f'independent {source} moment mismatch for {record["id"]}')
    if 'prior_report' in record['physical_reference'] and record['physical_reference']['prior_report'] not in reports:
        raise ValueError('case prior_report must exactly match a declared historical diagnostic report')
    baseline = record.get('historical_ng_baseline')
    if baseline is not None:
        fields = ('report', 'report_sha256', 'finest_geometry_fem_intervals', 'scope')
        keys(baseline, fields, fields, 'historical NG baseline')
        sources = [r for r in reports if r['path'] == baseline['report'] and r['sha256'] == baseline['report_sha256']]
        if len(sources) != 1:
            raise ValueError('historical NG baseline source must match a declared diagnostic report')
        _text(baseline['scope'], 'historical baseline scope')
        keys(baseline['finest_geometry_fem_intervals'], tuple(LIMITS), tuple(LIMITS), 'historical NG intervals')
        for name, interval in baseline['finest_geometry_fem_intervals'].items():
            if type(interval) is not list or len(interval) != 2 or not 0 < positive(interval[0], name) <= positive(interval[1], name):
                raise ValueError('historical NG intervals require positive ordered endpoints')
        path = _path(baseline['report'], root)
        if path.exists():
            report = parse_json(_bytes(path).decode('utf-8'))
            try:
                original = report['geometry_groups'][-1]['rows'][-1]['intervals']
            except (KeyError, IndexError, TypeError) as error:
                raise ValueError('historical NG baseline requires the original separated report intervals') from error
            _equal(baseline['finest_geometry_fem_intervals'], original, 'historical NG baseline intervals')
    matrix = []
    for g, tolerance in enumerate(tolerances):
        rows = []
        for level in record['fem_uniform_levels']:
            raw = deepcopy(record['base_case'])
            raw['geometry']['chord_tolerance_m'] = tolerance
            if level:
                raw['mesh']['curved_refinement_levels'] = level
            parsed = Case.from_dict(raw)
            if parsed.curved_contour.to_dict() != native:
                raise ValueError('geometry approximation must preserve the whole analytic meridian')
            rows.append(dict(geometry_index=g, fem_uniform_level=level, case=parsed.to_dict(),
                             solve_status='NOT_RUN', source_mesh_requirement='one fixed source mesh for all FEM levels in this geometry row'))
        matrix.append(rows)
    return dict(id=record['id'], synthetic=True, target_mode_id=record['target_mode_id'],
                initial_ids=deepcopy(ids), matrix=matrix, geometry_diagnostic=diagnostic,
                independent_geometry=dict(kind=geometry['kind'], meridian_area_m2=geometry['moments'][0],
                                          rotational_volume_m3=geometry['moments'][1],
                                          method=geometry['method'], integration_error_estimates=geometry['integration_error_estimates'],
                                          declared_relative_differences=[abs(v/ref-1) for v, ref in zip(declared, geometry['moments'])]),
                finite_peak_required=record['finite_peak_required'],
                physical_reference=_physical_reference(record, case, geometry),
                historical_ng_baseline=deepcopy(baseline),
                historical_ng_baseline_is_independent_reference=False,
                geometry_convergence='NOT_RUN', fem_convergence='NOT_RUN',
                quadrature_convergence='NOT_RUN', native_field_correspondence='NOT_RUN',
                discrete_peak_convergence='NOT_APPLICABLE_SINGULAR' if not record['finite_peak_required'] else 'NOT_RUN',
                physical_error_bound=None)


def build_geometry_surface_plan(request, *, base_directory=None):
    """Bind strict full Cases and independent geometry without constructing a mesh."""
    fields = ('schema_version', 'document_type', 'catalog', 'catalog_sha256', 'case_ids')
    keys(request, fields+('reference_directory',), fields, 'geometry surface plan request')
    _equal(request['schema_version'], 1, 'request schema_version')
    _equal(request['document_type'], 'geometry_surface_plan_request', 'request document_type')
    root = Path.cwd() if base_directory is None else Path(base_directory).resolve()
    root = _path(request.get('reference_directory', str(root)), root)
    if not root.is_dir():
        raise ValueError('reference_directory requires an existing historical artifact base directory')
    catalog_path = _path(request['catalog'], root)
    data = _bytes(catalog_path); sha = hashlib.sha256(data).hexdigest()
    if sha != _sha(request['catalog_sha256']):
        raise ValueError('catalog sha256 differs; explicitly identify the intended input before FEM')
    source_before = _source_hashes()
    catalog = parse_json(data.decode('utf-8'))
    keys(catalog, CATALOG_FIELDS, CATALOG_FIELDS, 'N01 catalog')
    _equal(catalog['schema_version'], 1, 'catalog schema_version')
    _equal(catalog['document_type'], 'N01_geometry_surface_case_catalog', 'catalog document_type')
    for name in ('scope', 'fixed_geometry_fem_requirement', 'geometry_requirement', 'baseline_preservation'):
        _text(catalog[name], name)
    _equal(catalog['quantity_change_limits'], LIMITS, 'five quantity limits')
    _equal(catalog['field_gates'], FIELD_GATES, 'field gates')
    _equal(catalog['native_tracking_controls'], TRACKING, 'native tracking controls')
    quadrature = catalog['quadrature']
    keys(quadrature, ('orders', 'relative_tolerance', 'role'), ('orders', 'relative_tolerance', 'role'), 'quadrature')
    _equal(quadrature['orders'], [12, 16, 24], 'quadrature orders')
    _equal(quadrature['relative_tolerance'], 1e-8, 'quadrature tolerance'); _text(quadrature['role'], 'quadrature role')
    route = catalog['independent_reference_route']
    route_fields = ('primary', 'pin', 'metadata', 'fallback', 'when_unavailable')
    keys(route, route_fields, route_fields, 'independent reference acquisition route')
    for name in route_fields:
        _text(route[name], name)
    _equal(route['pin'], '48741ff46ca44463281a5ab5945328615881b502', 'isolated A01 reference pin')
    _equal(route['metadata'], 'benchmarks/cavsim2d/a01-20260914.json', 'isolated A01 metadata')
    records, references = catalog['records'], catalog['reference_reports']
    if type(records) is not list or not records or type(references) is not list:
        raise ValueError('records require nonempty case records and reference_reports requires a list')
    historical = [_historical_report(r, root) for r in references]
    plans = [_record_plan(r, references, root) for r in records]
    ids = [p['id'] for p in plans]
    if len(set(ids)) != len(ids):
        raise ValueError('catalog case ids must be unique')
    selected = request['case_ids']
    if (type(selected) is not list or not selected or any(type(i) is not str for i in selected)
            or len(set(selected)) != len(selected) or any(i not in ids for i in selected)):
        raise ValueError('case_ids requires distinct known catalog ids in the requested order')
    normalized = deepcopy(request)
    normalized.update(catalog=str(catalog_path), reference_directory=str(root))
    if (_bytes(catalog_path) != data or historical != [_historical_report(r, root) for r in references]
            or source_before != _source_hashes()):
        raise ValueError('geometry surface plan sources changed during validation')
    return dict(schema_version=1, document_type='geometry_surface_plan', status='INPUTS_VERIFIED',
                request=normalized, catalog_sha256=sha, source_sha256=source_before,
                cases=[plans[ids.index(i)] for i in selected], historical_reports=historical,
                limits=deepcopy(LIMITS), field_gates=deepcopy(FIELD_GATES), native_tracking_controls=deepcopy(TRACKING),
                quadrature=deepcopy(quadrature), independent_reference_route=deepcopy(route),
                planned_fem_solves=9*len(selected), new_fem_solves=0,
                numerical_acceptance_status='NOT_RUN', physical_acceptance_status='UNVERIFIED',
                physical_error_bound=None,
                scope='strict inputs, independent geometry invariants and SHA-identified historical diagnostics only; no FEM, field pairing, quadrature or physical-peak acceptance')


def save_geometry_surface_plan(request, path, *, base_directory=None):
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    result = build_geometry_surface_plan(request, base_directory=base_directory)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(result, indent=2, allow_nan=False)+'\n')
    return result


def read_geometry_surface_plan(path):
    document = parse_json(_bytes(Path(path)).decode('utf-8'))
    if not isinstance(document, dict) or 'request' not in document:
        raise ValueError('geometry surface plan requires a saved request')
    expected = build_geometry_surface_plan(document['request'])
    if _canonical(document) != _canonical(expected):
        raise ValueError('geometry surface plan replay differs from saved data or sources')
    return expected
