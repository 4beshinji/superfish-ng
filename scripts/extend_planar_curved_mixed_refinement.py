#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Continue failed L-corner TM with a bounded mixed A refinement.

Uniform L5 exceeded the strict geometry budget before FEM. This continuation
instead bisects the complete A-L4 mesh, preserving its original P2 domain.
The general common-parent comparator is mandatory for this mixed refinement.
No physical tolerance or geometry budget is increased.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
from superfish_ng.jobs import _implementation_hashes
from superfish_ng.planar_curved import PlanarCurvedCase
from superfish_ng.planar_curved_solver import solve_planar_curved
from superfish_ng.project import parse_json
from extend_planar_curved_shapes import previous_specification, artifact_hashes, restore_state
from planar_curved_mesh_reference import restriction_chain, compare_meshes
from planar_curved_vector_reference import vectorized_validation_view
from validate_planar_curved_independent import independent_integrals, save_solution
from validate_planar_curved_shapes import mode_groups, band_checks, targets_passed


def mixed_specification(folder, budget_failure):
    report, original, snapshot = previous_specification(folder)
    if report['shape'] != 'corner' or report['polarization'] != 'tm' or report['accepted_A'] is not None:
        raise ValueError('mixed continuation requires failed corner TM A-L4 evidence')
    if [r['label'] for r in report['records']] != [f'A-L{level}' for level in range(1, 5)]:
        raise ValueError('mixed continuation requires exactly the complete uniform A-L1..A-L4 prefix')
    failure = parse_json((budget_failure/'failed-evidence.json').read_text())
    if 'max_geometry_boxes=100000000 exhausted' not in failure.get('error', ''):
        raise ValueError('mixed continuation requires recorded exhaustion of the strict geometry budget')
    if parse_json((budget_failure/'progress.json').read_text()) != [] or (budget_failure/'report.json').exists():
        raise ValueError('the budget failure must have no completed new FEM trial')
    previous = parse_json((budget_failure/'previous-report.json').read_text())
    if previous.get('shape') != 'corner' or previous.get('polarization') != 'tm':
        raise ValueError('recorded geometry budget exhaustion must concern corner TM')
    # The measured failure can be shared across scales; it is a cost observation,
    # not evidence that either scale meets a physical gate.
    return report, original, snapshot, artifact_hashes(budget_failure)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-evidence', required=True, type=Path)
    parser.add_argument('--budget-failure', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    report, original, previous_hashes, failure_hashes = mixed_specification(args.from_evidence, args.budget_failure)
    args.out.mkdir(parents=True, exist_ok=False)
    started, before = time.monotonic(), _implementation_hashes()
    modules = [Path(__file__), *(Path(__file__).with_name(name) for name in
        ('extend_planar_curved_shapes.py', 'planar_curved_mesh_reference.py',
         'planar_curved_shape_reference.py', 'planar_curved_vector_reference.py',
         'validate_planar_curved_shapes.py', 'validate_planar_curved_independent.py',
         'validate_planar_curved_convergence.py', 'validate_planar_curved_fem.py', 'validate_planar_curved_rf.py'))]
    code = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in modules}
    for name, data in [('implementation-before', before), ('validator-hashes', code),
        ('reused-artifact-hashes', previous_hashes), ('geometry-failure-artifact-hashes', failure_hashes),
        ('previous-report', report)]:
        (args.out/f'{name}.json').write_text(json.dumps(data, indent=2)+'\n')
    groups, rows, new_solves = mode_groups('corner', 'tm'), [], 0

    def solve(patterns, label):
        nonlocal new_solves
        print(f'solving {label}: patterns={patterns}', flush=True)
        charts = restriction_chain(original, patterns, max_geometry_boxes=100000000)
        solution = solve_planar_curved(PlanarCurvedCase(charts.domain, 'tm', modes=sum(groups), max_geometry_boxes=100000000))
        new_solves += 1
        save_solution(args.out/label, solution, charts)
        view = vectorized_validation_view(solution)
        row = dict(label=label, patterns=list(patterns), cells=len(charts.domain.cell_nodes),
            dofs=len(solution.coefficients), band=band_checks(view, 'corner', report['scale']),
            independent_integrals=independent_integrals(view),
            final_original_map_relative_bound=charts.maximum_relative_coordinate_bound,
            geometry=dict(charts.domain.geometry_diagnostics))
        rows.append(row)
        return view, charts, row

    def checkpoint():
        (args.out/'progress.json').write_text(json.dumps(rows, indent=2)+'\n')

    def passed(row, independent=False):
        return (targets_passed(row['last_two']) and row['band']['passed']
            and row['independent_integrals']['passed'] and (not independent or targets_passed(row['A_vs_B'])))

    try:
        print('physically restoring uniform A-L4', flush=True)
        coarse = restore_state(args.from_evidence, report['records'][-1], original)
        if coarse[0].case.polarization != 'tm' or coarse[0].case.modes != sum(groups):
            raise ValueError('restored A must retain TM and the complete band')
        mixed = solve(('uniform',)*4+('bisection',), 'A-uniform4-bisection')
        mixed[2]['last_two'] = compare_meshes(coarse[0], mixed[0], coarse[1], mixed[1], groups)
        mixed[2]['passed'] = passed(mixed[2])
        checkpoint()
        accepted_b = None
        if mixed[2]['passed']:
            prior = solve(('bisection',)+('uniform',)*3, 'B-bisection-uniform3')
            prior[2]['passed'] = False
            checkpoint()
            fine = solve(('bisection',)+('uniform',)*4, 'B-bisection-uniform4')
            if fine[1].domain == mixed[1].domain:
                raise ValueError('A/B must retain genuinely different native meshes')
            fine[2]['last_two'] = compare_meshes(prior[0], fine[0], prior[1], fine[1], groups)
            fine[2]['A_vs_B'] = compare_meshes(mixed[0], fine[0], mixed[1], fine[1], groups)
            fine[2]['passed'] = passed(fine[2], independent=True)
            checkpoint()
            if fine[2]['passed']:
                accepted_b = fine
        after = _implementation_hashes()
        if after != before or artifact_hashes(args.from_evidence) != previous_hashes or artifact_hashes(args.budget_failure) != failure_hashes:
            raise ValueError('product or original raw changed during mixed continuation')
        if any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != digest for p, digest in code.items()):
            raise ValueError('mixed continuation validator changed during fixed-source validation')
        result = dict(passed=mixed[2]['passed'] and accepted_b is not None, shape='corner', polarization='tm',
            scale=report['scale'], previous_evidence=str(args.from_evidence),
            geometry_budget_failure=str(args.budget_failure), geometry_budget=100000000,
            physically_restored_previous_solutions=['A-L4'], new_FEM_solves=new_solves, records=rows,
            accepted_A=mixed[2]['label'] if mixed[2]['passed'] else None,
            accepted_B=accepted_b[2]['label'] if accepted_b else None,
            product_files_unchanged=len(after), original_artifacts_unchanged=len(previous_hashes),
            elapsed_s=time.monotonic()-started, scope='mixed original-P2 corner TM refinement with unchanged physical gates and geometry budget')
        (args.out/'implementation-after.json').write_text(json.dumps(after, indent=2)+'\n')
        (args.out/'report.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps({k: v for k, v in result.items() if k != 'records'}, indent=2), flush=True)
        if not result['passed']:
            raise AssertionError('mixed refinement gates unmet; retain actual results without relaxed tolerances')
    except Exception as exc:
        checkpoint()
        (args.out/'failed-evidence.json').write_text(json.dumps(dict(error=repr(exc), new_FEM_solves=new_solves,
            elapsed_s=time.monotonic()-started), indent=2)+'\n')
        raise


if __name__ == '__main__':
    main()
