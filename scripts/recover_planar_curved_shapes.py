#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Physically replay a terminal interrupted shape prefix, then continue B.

The termination audit records an observed terminal tool handle, not an elapsed
time inference. No completed FEM solve is repeated. Original raw stays intact.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from superfish_ng.jobs import _implementation_hashes
from superfish_ng.planar_curved import PlanarCurvedCase
from superfish_ng.planar_curved_solver import solve_planar_curved
from superfish_ng.project import parse_json
from planar_curved_mesh_reference import restriction_chain, compare_meshes
from planar_curved_shape_reference import ellipse_domain, corner_domain
from validate_planar_curved_shapes import mode_groups, band_checks, targets_passed
from planar_curved_vector_reference import vectorized_validation_view
from validate_planar_curved_independent import independent_integrals, save_solution
from validate_planar_curved_convergence import compare_pair
from extend_planar_curved_shapes import restore_state, artifact_hashes


def prefix_preflight(folder, termination_audit):
    audit = parse_json(termination_audit.read_text())
    if audit.get('terminal') is not True or type(audit.get('observed_exit_code')) is not int or audit['observed_exit_code'] == 0:
        raise ValueError('recovery requires an observed terminal nonzero handle; elapsed time is insufficient')
    if Path(audit['original_evidence']).resolve() != folder.resolve():
        raise ValueError('terminal observation must refer to this exact evidence directory')
    if (folder/'report.json').exists():
        raise ValueError('completed reports must use the terminal-failure extension, not interrupted-prefix recovery')
    if parse_json((folder/'implementation-before.json').read_text()) != _implementation_hashes():
        raise ValueError('interrupted prefix requires exact unchanged production hashes')
    names = ('validate_planar_curved_shapes.py', 'planar_curved_mesh_reference.py',
        'planar_curved_shape_reference.py', 'planar_curved_vector_reference.py',
        'validate_planar_curved_independent.py', 'validate_planar_curved_convergence.py',
        'validate_planar_curved_fem.py', 'validate_planar_curved_rf.py')
    expected = {Path(__file__).resolve().with_name(n) for n in names}
    code = parse_json((folder/'validator-hashes.json').read_text())
    if len(code) != len(expected) or {Path(p).resolve() for p in code} != expected:
        raise ValueError('interrupted prefix requires complete original validator hashes')
    for p, digest in code.items():
        if hashlib.sha256(Path(p).read_bytes()).hexdigest() != digest:
            raise ValueError('interrupted prefix validator changed')
    rows = parse_json((folder/'progress.json').read_text())
    if not rows or len({r['label'] for r in rows}) != len(rows):
        raise ValueError('interrupted prefix must contain unique recorded states')
    for row in rows:
        label, patterns = row['label'], row['patterns']
        level = len(patterns)
        if not 1 <= level <= 5 or label not in (f'A-L{level}', f'B-L{level}'):
            raise ValueError('interrupted trial must be a local A/B label with bounded level')
        correct = ['uniform']*level if label.startswith('A-') else ['bisection']+['uniform']*(level-1)
        if patterns != correct:
            raise ValueError('interrupted trial pattern disagrees with its level')
        for name in ('case.json', 'fem-fields.npz', 'patterns.json', 'regenerated-parent-charts.npz'):
            if not (folder/label/name).is_file():
                raise ValueError(f'interrupted prefix missing complete recorded artifact {label}/{name}')
    a_levels = [len(r['patterns']) for r in rows if r['label'].startswith('A-')]
    b_levels = [len(r['patterns']) for r in rows if r['label'].startswith('B-')]
    if not a_levels or a_levels != list(range(1, max(a_levels)+1)):
        raise ValueError('interrupted A must be a complete consecutive prefix')
    if b_levels and b_levels != list(range(max(a_levels)-1, max(b_levels)+1)):
        raise ValueError('interrupted B must be a consecutive prefix after A')
    expected_labels = [f'A-L{level}' for level in a_levels] + [f'B-L{level}' for level in b_levels]
    if [row['label'] for row in rows] != expected_labels:
        raise ValueError('interrupted progress must preserve chronological A then B order')
    return rows, artifact_hashes(folder), audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-evidence', required=True, type=Path)
    parser.add_argument('--terminal-audit', required=True, type=Path)
    parser.add_argument('--shape', choices=('ellipse', 'corner'), required=True)
    parser.add_argument('--polarization', choices=('te', 'tm'), required=True)
    parser.add_argument('--scale', type=int, choices=(1, 2), required=True)
    parser.add_argument('--angular-segments', type=int, choices=(16, 32, 64), default=16)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    previous, original_hashes, audit = prefix_preflight(args.from_evidence, args.terminal_audit)
    original = ellipse_domain(args.angular_segments, scale=args.scale) if args.shape == 'ellipse' else corner_domain(.01*args.scale)
    groups = mode_groups(args.shape, args.polarization)
    args.out.mkdir(parents=True, exist_ok=False)
    before, started = _implementation_hashes(), time.monotonic()
    (args.out/'implementation-before.json').write_text(json.dumps(before, indent=2)+'\n')
    (args.out/'reused-artifact-hashes.json').write_text(json.dumps(original_hashes, indent=2)+'\n')
    (args.out/'termination-audit.json').write_text(json.dumps(audit, indent=2)+'\n')
    modules = [Path(__file__), *(Path(__file__).with_name(n) for n in
        ('extend_planar_curved_shapes.py', 'planar_curved_mesh_reference.py',
         'planar_curved_shape_reference.py', 'planar_curved_vector_reference.py',
         'validate_planar_curved_shapes.py', 'validate_planar_curved_independent.py',
         'validate_planar_curved_convergence.py', 'validate_planar_curved_fem.py',
         'validate_planar_curved_rf.py'))]
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in modules}
    (args.out/'validator-hashes.json').write_text(json.dumps(hashes, indent=2)+'\n')
    records, accepted_a, accepted_b, prior_a, prior_b = [], None, None, None, None
    new_solves = 0

    def evaluate(view, charts, label, patterns, origin):
        return dict(label=label, patterns=list(patterns), origin=origin,
            band=band_checks(view, args.shape, args.scale), independent_integrals=independent_integrals(view),
            cells=len(view.case.domain.cell_nodes), dofs=len(view.coefficients),
            final_original_map_relative_bound=charts.maximum_relative_coordinate_bound)

    def decide(state):
        nonlocal accepted_a, accepted_b, prior_a, prior_b
        view, charts, row = state
        if row['label'].startswith('A-'):
            if prior_a is not None:
                row['last_two'] = compare_pair(prior_a[0], view, groups)
            row['passed'] = ('last_two' in row and targets_passed(row['last_two'])
                and row['band']['passed'] and row['independent_integrals']['passed'])
            if row['passed']:
                accepted_a = state
            prior_a = state
        else:
            if accepted_a is None:
                raise ValueError('B prefix requires a physically reverified accepted A')
            if prior_b is not None:
                row['last_two'] = compare_meshes(prior_b[0], view, prior_b[1], charts, groups)
                row['A_vs_B'] = compare_meshes(accepted_a[0], view, accepted_a[1], charts, groups)
            row['passed'] = ('last_two' in row and targets_passed(row['last_two'])
                and targets_passed(row['A_vs_B']) and row['band']['passed'] and row['independent_integrals']['passed'])
            if row['passed']:
                accepted_b = state
            prior_b = state
        records.append(row)
        (args.out/'progress.json').write_text(json.dumps(records, indent=2)+'\n')

    try:
        for old in previous:
            print(f'replaying original {old["label"]}', flush=True)
            view, charts, _ = restore_state(args.from_evidence, old, original)
            if view.case.polarization != args.polarization or view.case.modes != sum(groups):
                raise ValueError('interrupted native case disagrees with the explicit physical specification')
            row = evaluate(view, charts, old['label'], old['patterns'], 'physically_replayed_previous')
            decide((view, charts, row))
        if accepted_a is None:
            raise ValueError('this bounded recovery requires the previous A prefix to pass actual replay')
        if accepted_b is None:
            start = len(prior_b[1].patterns)+1 if prior_b is not None else len(accepted_a[1].patterns)-1
            for level in range(start, 6):
                label, patterns = f'B-L{level}', ('bisection',)+('uniform',)*(level-1)
                if (args.from_evidence/label).exists():
                    raise ValueError('unrecorded original trial exists; audit its completeness before solving again')
                print(f'solving missing continuation {label}', flush=True)
                charts = restriction_chain(original, patterns)
                solution = solve_planar_curved(PlanarCurvedCase(charts.domain, args.polarization,
                    modes=sum(groups), max_geometry_boxes=100000000))
                new_solves += 1
                save_solution(args.out/label, solution, charts)
                view = vectorized_validation_view(solution)
                row = evaluate(view, charts, label, patterns, 'new_actual_FEM')
                decide((view, charts, row))
                if accepted_b is not None:
                    break
        after = _implementation_hashes()
        if after != before or artifact_hashes(args.from_evidence) != original_hashes:
            raise ValueError('product or interrupted raw changed during physical recovery')
        if any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != digest for p, digest in hashes.items()):
            raise ValueError('recovery validator changed during validation')
        result = dict(passed=accepted_a is not None and accepted_b is not None, shape=args.shape,
            polarization=args.polarization, scale=args.scale, previous_evidence=str(args.from_evidence),
            physically_replayed_previous_FEM_solutions=len(previous), new_FEM_solves=new_solves,
            accepted_A=None if accepted_a is None else accepted_a[2]['label'],
            accepted_B=None if accepted_b is None else accepted_b[2]['label'], records=records,
            product_files_unchanged=len(after), original_artifacts_unchanged=len(original_hashes),
            elapsed_s=time.monotonic()-started, scope='physical replay of a terminal interrupted prefix and actual missing B continuation')
        (args.out/'implementation-after.json').write_text(json.dumps(after, indent=2)+'\n')
        (args.out/'report.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps({k: v for k, v in result.items() if k != 'records'}, indent=2), flush=True)
        if not result['passed']:
            raise AssertionError('recovered mesh gates remain unmet without relaxed tolerance')
    except Exception as exc:
        (args.out/'failed-evidence.json').write_text(json.dumps(dict(error=repr(exc), elapsed_s=time.monotonic()-started), indent=2)+'\n')
        raise


if __name__ == '__main__':
    main()
