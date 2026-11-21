# SPDX-License-Identifier: Apache-2.0
"""Bind N05's actual initial inputs and alternating twelve-run N06 schedule.

Only input parsing and tagged-mesh validation happen here. Requests for the
uniform and adaptive workers share the exact original Case/mesh; neither a
physical acceptance nor a completed native solve can be inferred from this plan.
"""
from copy import deepcopy
import hashlib
from pathlib import Path

from .adaptive_refinement import _request as validate_adaptive_request
from .config import Case
from .mesh_input import mesh_from_dict
from .project import parse_json


INPUTS = (
    ('pillbox', 'examples/adaptive_refinement/pillbox_confirmed.json',
     'e326796c7b036001eefb533362b09ae5907ec1c83d091aa9728ad5ef161226a0'),
    ('sphere', 'examples/adaptive_refinement/curved_sphere_confirmed.json',
     '48bb3d48e9d75061af7041bf8f482c1d9f9aa710a7b77ef576ea4db81f329f1b'),
    ('rounded_case', 'examples/adaptive_efficiency/rounded_two_lobe_case.json',
     '2b426b617de7f1c36a9f63f340817abf81322781b0a8882299372ccaa3d9ac90'),
    ('rounded_mesh', 'examples/adaptive_efficiency/rounded_two_lobe_mesh.json',
     '959c056225acbeb7dcc860a4260f1d0fbe00caabc9413331197e903b63319fe7'),
)


def build_adaptive_efficiency_plan(*, base_directory=None):
    """Return a new plan with source bytes pinned before any native work."""
    root = Path(base_directory) if base_directory is not None else Path(__file__).resolve().parents[2]
    data = {}
    sources = []
    for name, relative, expected in INPUTS:
        path = root / relative
        if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
            raise ValueError(f'N05 initial input requires a regular file without symlinks: {path}')
        value = path.read_bytes()
        if hashlib.sha256(value).hexdigest() != expected:
            raise ValueError(f'fixed N05 initial input sha256 differs: {path}; restore the fixed input '
                             'or specify a separately reviewed comparison plan')
        data[name] = parse_json(value.decode('utf-8'))
        sources.append(dict(path=relative, sha256=expected, bytes=len(value)))
    # Verify the old requests before changing only N05's explicit comparison
    # budgets and tolerances. Case, source mesh and historical controls survive.
    for name in ('pillbox', 'sphere'):
        validate_adaptive_request(data[name])
    rounded_case = Case.from_dict(data['rounded_case'])
    mesh_from_dict(rounded_case, data['rounded_mesh'])
    rounded = dict(schema_version=4, case=data['rounded_case'], initial_mesh=data['rounded_mesh'],
                   initial_ids=['target', 'guard-2', 'guard-3'], mode_id='target',
                   controls=dict(mapping='nested_curved', minimum_overlap=.98,
                                 minimum_assignment_margin=.05, relative_cluster_gap=1e-6,
                                 minimum_relative_singular_value=1e-8),
                   minimum_corner_angle_deg=5., quadrature_check_order=24,
                   quadrature_relative_tolerance=1e-6, confirmation='uniform_two_steps')
    requests = [('cylinder', deepcopy(data['pillbox'])),
                ('sphere', deepcopy(data['sphere'])), ('rounded-two-lobe', rounded)]
    cases = []
    executions = []
    for name, request in requests:
        case = Case.from_dict(request['case'])
        if case.element_order != 2 or (case.normalization_j, case.beta, case.conductivity_s_per_m) != (1., 1., 5.8e7):
            raise ValueError('N05 requires original P2, 1 J, beta=1 and sigma=5.8e7 S/m')
        request.update(max_levels=8, max_triangles=min(250000, case.contour_mesh.max_triangles if case.contour_mesh else 250000),
                       bulk_fraction=.5, confirmation='uniform_two_steps',
                       relative_tolerances=dict(frequency_hz=1e-4, r_over_q_accelerator_ohm=.005, geometry_factor_ohm=.005),
                       surface_relative_tolerances=dict(epk_over_eacc=.01, bpk_over_eacc_mt_per_mv_per_m=.01))
        if case.geometry_order == 1:
            request['schema_version'] = 3
            request['minimum_angle_deg'] = max(5., request['minimum_angle_deg'],
                                             case.contour_mesh.min_angle_deg if case.contour_mesh else 0.)
        else:
            request['minimum_corner_angle_deg'] = max(5., request['minimum_corner_angle_deg'],
                                                    case.contour_mesh.min_angle_deg)
            request.update(quadrature_check_order=24, quadrature_relative_tolerance=1e-6)
        validated_case = validate_adaptive_request(request)
        if validated_case != case:
            raise ValueError('N05 request adaptation changed the original Case')
        cases.append(dict(id=name, request=deepcopy(request), physical_error_bound=None,
                          reference_kind={'cylinder': 'Bessel_TM010', 'sphere': 'SphereTM',
                                          'rounded-two-lobe': 'N03_saved_independent_three_h_five_modes'}[name]))
        for repetition, methods in ((1, ('uniform', 'adaptive')), (2, ('adaptive', 'uniform'))):
            for method in methods:
                executions.append(dict(id=f'{name}-repetition-{repetition}-{method}', case_id=name,
                                       repetition=repetition, method=method, request=deepcopy(request),
                                       wall_limit_seconds=3600, memory_limit_bytes=32 * 1024**3,
                                       initial_solve='fresh native FEM; no reuse from other execution',
                                       status='NOT_RUN'))
    # The source binding is rechecked after all parsing and geometry validation.
    if any(hashlib.sha256((root/s['path']).read_bytes()).hexdigest() != s['sha256'] for s in sources):
        raise ValueError('N05 initial input changed during plan construction')
    return dict(schema_version=1, document_type='adaptive_efficiency_execution_plan',
                status='PLANNED', cases=cases, executions=executions, input_sources=sources,
                expected_native_executions=12, new_fem_solves=0, physical_acceptance_status='NOT_RUN',
                comparison_limits=dict(frequency_hz=1e-4, r_over_q_accelerator_ohm=.005,
                                       r_over_q_circuit_ohm=.005, geometry_factor_ohm=.005,
                                       epk_over_eacc=.01, bpk_over_eacc_mt_per_mv_per_m=.01,
                                       electric_relative_l2=.005, magnetic_relative_l2=.005,
                                       axis_ez_relative_l2=.01),
                scope='fixed N05 inputs and serial alternating independent repetitions; uniform/adaptive '
                      'fresh initial solves; no numerical/efficiency acceptance; two full uniform '
                      'confirmation intervals and separate shared reference costs required')
