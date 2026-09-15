# SPDX-License-Identifier: Apache-2.0
"""H03--H05 evidence: actual vacuum FEMs, owned checkpoints and refusals."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

import numpy as np

from superfish_ng.coaxial import CoaxialCase
from superfish_ng.constants import C0
from superfish_ng.hphi_native import save_hphi_run, hphi_result
from superfish_ng.hphi_project import HphiProject
from superfish_ng.hphi_tracking import HphiTrackingControls
from superfish_ng.hphi_tuning import (
    execute_hphi_tune,
    read_hphi_tune,
    run_hphi_tune,
    assess_hphi_tune,
    validate_hphi_tune,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    request = dict(format='superfish_ng_hphi_tune', schema_version=1,
        project=HphiProject(CoaxialCase(.025, .05, .18, nr=3, nz=8, modes=3)).to_dict(),
        parameter='uniform_scale', mapping=dict(kind='uniform_scale'), bounds=[1., 2.],
        target_hz=C0/(2*.18*1.5), frequency_tolerance_hz=1e6, parameter_tolerance=1e-6,
        max_trials=20, initial_ids=['TEM-1'], mode_id='TEM-1', controls=HphiTrackingControls().to_dict(),
        refinement_levels=1, max_triangles=10000, max_dofs=10000, mesh_frequency_tolerance_hz=1e6)
    def write(name, value):
        with (args.out/name).open('x') as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write('\n')
    write('request.json', request)
    execution = run_hphi_tune(request)
    write('tune.json', execution.report)
    checks = dict(tuned=execution.report['status'] == 'TUNED',
        bisection=[t['value'] for t in execution.report['trials']] == [1., 2., 1.5, 1.5])
    errors = []
    for i, (project, solution) in enumerate(zip(execution.projects, execution.solutions)):
        project.save(args.out/f'project-{i:03d}.json')
        save_hphi_run(project.case, solution, args.out/f'native-{i:03d}')
        # Closed coaxial TEM longitudinal resonance, independent of the FEM.
        errors.append(abs(float(solution.frequencies_hz[0])/(C0/(2*project.case.length_m))-1))
    checks['analytic_tem_frequency'] = max(errors) < 2e-5
    a, b = execution.solutions[:2]
    qa, qb = (hphi_result(s)['modes'] for s in (a, b))
    factors = dict(frequency_hz=.5, stored_energy_j=1., volume_m3=8.,
        geometry_factor_ohm=1., q0=np.sqrt(2.), wall_loss_w=2**-1.5)
    rf_errors = {key: max(abs(y[key]/(factor*x[key])-1) for x, y in zip(qa, qb))
                 for key, factor in factors.items()}
    checks['rf_scale_laws'] = max(rf_errors.values()) < 1e-9
    points = a.space.mesh.points[a.space.mesh.triangles].mean(axis=1)
    fields_a, fields_b = a.fields_at(points), b.fields_at(2*points)
    phase = 1 if fields_a['Hphi_real_A_per_m']@fields_b['Hphi_real_A_per_m'] > 0 else -1
    field_errors = {}
    for family, names in [('electric', ['Er_quadrature_V_per_m', 'Ez_quadrature_V_per_m']),
                          ('magnetic', ['Hphi_real_A_per_m'])]:
        x = np.column_stack([fields_a[k] for k in names])*2**-1.5
        y = np.column_stack([fields_b[k] for k in names])*phase
        field_errors[family] = float(np.linalg.norm(y-x)/np.linalg.norm(x))
    checks['original_field_scale_laws'] = max(field_errors.values()) < 1e-9
    variants = [('mesh_gate', 'mesh_frequency_tolerance_hz', 1e-5, 4, 'REFINEMENT_FAILED'),
        ('unbracketed', 'target_hz', 3*request['target_hz'], 2, 'UNBRACKETED'),
        ('iteration_limit', 'max_trials', 2, 2, 'ITERATION_LIMIT'),
        ('parameter_limit', 'parameter_tolerance', 1., 2, 'PARAMETER_LIMIT')]
    for name, field, value, count, status in variants:
        q = deepcopy(request); q[field] = value
        result = assess_hphi_tune(q, execution.solutions[:count]).report
        write(name+'.json', result)
        checks[name] = result['status'] == status
    q = deepcopy(request); q['controls']['relative_cluster_gap'] = .9
    result = assess_hphi_tune(q, execution.solutions[:1]).report
    write('unverified.json', result)
    checks['unverified_frequency_null'] = result['status'] == 'UNVERIFIED' and result['trials'][0]['frequency_hz'] is None
    q = deepcopy(request); q['target_hz'] = float(execution.solutions[2].frequencies_hz[0]); q['frequency_tolerance_hz'] = 1e-3
    result = assess_hphi_tune(q, execution.solutions).report
    write('target_gate.json', result)
    checks['independent_target_gate'] = result['status'] == 'REFINEMENT_FAILED' and not result['decision']['refined_target_met'] and result['decision']['mesh_difference_met']
    q = deepcopy(request); q['max_triangles'] = 191
    try:
        validate_hphi_tune(q)
        checks['preflight_mesh_limit'] = False
    except ValueError as exc:
        checks['preflight_mesh_limit'] = 'exceeds' in str(exc)
        write('preflight_refusal.json', dict(request=q, reason=str(exc)))
    owned_first = execute_hphi_tune(request, args.out/'owned-first', max_new_trials=2)
    owned_pre_refinement = execute_hphi_tune(
        request, args.out/'owned-pre-refinement', checkpoint=owned_first, max_new_trials=1
    )
    owned_final = execute_hphi_tune(request, args.out/'owned-rest', checkpoint=owned_pre_refinement)
    unverified_request = deepcopy(request)
    unverified_request['controls']['relative_cluster_gap'] = .9
    owned_unverified = execute_hphi_tune(unverified_request, args.out/'owned-unverified')
    checks['owned_pause_replay'] = (
        owned_first['status'] == 'PAUSED'
        and read_hphi_tune(args.out/'owned-first/checkpoint-002.json') == owned_first
    )
    checks['owned_resume_replay'] = (
        owned_final['status'] == 'TUNED'
        and read_hphi_tune(args.out/'owned-rest/checkpoint-004.json') == owned_final
    )
    checks['owned_pre_refinement_replay'] = (
        owned_pre_refinement['status'] == 'PAUSED'
        and read_hphi_tune(args.out/'owned-pre-refinement/checkpoint-003.json') == owned_pre_refinement
    )
    checks['owned_unverified_replay'] = (
        owned_unverified['status'] == 'UNVERIFIED'
        and not owned_unverified['can_resume']
        and read_hphi_tune(args.out/'owned-unverified/checkpoint-001.json') == owned_unverified
    )
    moved = args.out/'owned-pre-refinement-moved'
    (args.out/'owned-pre-refinement').rename(moved)
    try:
        checks['owned_prefix_survives_source_move'] = read_hphi_tune(
            args.out/'owned-rest/checkpoint-004.json'
        ) == owned_final
    finally:
        moved.rename(args.out/'owned-pre-refinement')
    report = dict(status='PASS' if all(checks.values()) else 'FAIL', checks=checks,
        new_fem_solves=len(execution.solutions) + len(owned_final['trials']) + len(owned_unverified['trials']), analytic_frequency_relative_errors=errors,
        rf_scale_relative_errors=rf_errors, field_scale_relative_errors=field_errors,
        scope='H03/H04 in-memory and H05 owned checkpoint/CLI API; synthetic coaxial TEM; no legacy or measured structure comparison')
    write('report.json', report)
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
