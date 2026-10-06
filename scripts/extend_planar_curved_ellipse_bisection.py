#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Continue ellipse TM B-L4 by bisection after terminal uniform-L5 map failure.

The cumulative original-map bound and all physical gates remain unchanged.
Completed A/B states are physically restored; only the mixed B is newly solved.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
from superfish_ng.jobs import _implementation_hashes
from superfish_ng.project import parse_json
from superfish_ng.planar_curved import PlanarCurvedCase
from superfish_ng.planar_curved_solver import solve_planar_curved
from extend_planar_curved_shapes import previous_specification, artifact_hashes, restore_state
from planar_curved_mesh_reference import restriction_chain, compare_meshes
from planar_curved_vector_reference import vectorized_validation_view
from validate_planar_curved_independent import independent_integrals, save_solution
from validate_planar_curved_shapes import mode_groups, band_checks, targets_passed


def previous_ellipse(folder, uniform_failure, terminal_audit):
    report, original, snapshot = previous_specification(folder)
    if (report['shape'], report['polarization'], report['initial_angular_segments']) != ('ellipse', 'tm', 16):
        raise ValueError('mixed B continuation requires the exact N16 ellipse TM specification')
    labels = [r['label'] for r in report['records']]
    if report['accepted_A'] != 'A-L4' or labels != [f'A-L{i}' for i in range(1, 5)]+['B-L3', 'B-L4']:
        raise ValueError('mixed B requires a complete accepted A-L4 and failed B-L3..B-L4 prefix')
    audit = parse_json(terminal_audit.read_text())
    if audit.get('terminal') is not True or type(audit.get('observed_exit_code')) is not int or audit['observed_exit_code'] == 0:
        raise ValueError('mixed B requires an observed terminal failed uniform extension')
    if Path(audit['original_evidence']).resolve() != uniform_failure.resolve():
        raise ValueError('terminal audit must identify the exact failed extension directory')
    failed = parse_json((uniform_failure/'failed-evidence.json').read_text())
    if 'cumulative original-map roundoff exceeds local resolution' not in failed.get('error', ''):
        raise ValueError('mixed B requires the recorded cumulative original-map roundoff failure')
    if parse_json((uniform_failure/'progress.json').read_text()) != [] or (uniform_failure/'report.json').exists():
        raise ValueError('failed uniform extension must have no completed new FEM trial')
    if parse_json((uniform_failure/'previous-report.json').read_text()) != report:
        raise ValueError('failed uniform extension must retain this exact original physical report')
    if parse_json((uniform_failure/'implementation-before.json').read_text()) != _implementation_hashes():
        raise ValueError('failed uniform extension product hashes changed')
    manifest = parse_json((uniform_failure/'validator-hashes.json').read_text())
    required = {Path(__file__).resolve().with_name(name) for name in
        ('extend_planar_curved_shapes.py', 'planar_curved_mesh_reference.py',
         'planar_curved_shape_reference.py', 'planar_curved_vector_reference.py',
         'validate_planar_curved_shapes.py', 'validate_planar_curved_independent.py',
         'validate_planar_curved_convergence.py', 'validate_planar_curved_fem.py', 'validate_planar_curved_rf.py')}
    if len(manifest) != len(required) or {Path(name).resolve() for name in manifest} != required:
        raise ValueError('failed uniform extension requires its complete original validator manifest')
    for name, digest in manifest.items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest:
            raise ValueError('failed uniform extension validator changed')
    return report, original, snapshot, artifact_hashes(uniform_failure), audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-evidence', required=True, type=Path)
    parser.add_argument('--uniform-failure', required=True, type=Path)
    parser.add_argument('--terminal-audit', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    report, original, old_hashes, failed_hashes, audit = previous_ellipse(args.from_evidence, args.uniform_failure, args.terminal_audit)
    args.out.mkdir(parents=True, exist_ok=False)
    started, before = time.monotonic(), _implementation_hashes()
    modules = [Path(__file__), *(Path(__file__).with_name(name) for name in
        ('extend_planar_curved_shapes.py', 'planar_curved_mesh_reference.py',
         'planar_curved_shape_reference.py', 'planar_curved_vector_reference.py',
         'validate_planar_curved_shapes.py', 'validate_planar_curved_independent.py',
         'validate_planar_curved_convergence.py', 'validate_planar_curved_fem.py', 'validate_planar_curved_rf.py'))]
    code = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in modules}
    for name, data in [('implementation-before', before), ('validator-hashes', code),
        ('reused-artifact-hashes', old_hashes), ('uniform-failure-artifact-hashes', failed_hashes),
        ('previous-report', report), ('termination-audit', audit)]:
        (args.out/f'{name}.json').write_text(json.dumps(data, indent=2)+'\n')
    rows, new_solves = [], 0
    groups = mode_groups('ellipse', 'tm')
    previous_rows = {r['label']: r for r in report['records']}
    try:
        restored = {}
        for label in ('A-L3', 'A-L4', 'B-L4'):
            print(f'physically restoring {label}', flush=True)
            restored[label] = restore_state(args.from_evidence, previous_rows[label], original)
            view = restored[label][0]
            if view.case.polarization != 'tm' or view.case.modes != sum(groups):
                raise ValueError('restored ellipse must retain TM and its complete band')
        a, prior = restored['A-L4'], restored['B-L4']
        replay = compare_meshes(restored['A-L3'][0], a[0], restored['A-L3'][1], a[1], groups)
        band, integrals = band_checks(a[0], 'ellipse', report['scale']), independent_integrals(a[0])
        if not targets_passed(replay) or not band['passed'] or not integrals['passed']:
            raise ValueError('previous accepted A must pass actual independent physical replay')
        (args.out/'replayed-accepted-A.json').write_text(json.dumps(dict(comparison=replay, band=band, independent_integrals=integrals), indent=2)+'\n')
        patterns = ('bisection', 'uniform', 'uniform', 'uniform', 'bisection')
        label = 'B-bisection-uniform3-bisection'
        print(f'solving {label}: patterns={patterns}', flush=True)
        charts = restriction_chain(original, patterns, max_geometry_boxes=100000000)
        case = PlanarCurvedCase(charts.domain, 'tm', modes=sum(groups), max_geometry_boxes=100000000)
        solution = solve_planar_curved(case)
        new_solves += 1
        save_solution(args.out/label, solution, charts)
        view = vectorized_validation_view(solution)
        row = dict(label=label, patterns=list(patterns), cells=len(charts.domain.cell_nodes), dofs=len(solution.coefficients),
            band=band_checks(view, 'ellipse', report['scale']), independent_integrals=independent_integrals(view),
            final_original_map_relative_bound=charts.maximum_relative_coordinate_bound,
            last_two=compare_meshes(prior[0], view, prior[1], charts, groups),
            A_vs_B=compare_meshes(a[0], view, a[1], charts, groups))
        if charts.domain == a[1].domain:
            raise ValueError('independent A/B must use genuinely different native meshes')
        row['passed'] = targets_passed(row['last_two']) and targets_passed(row['A_vs_B']) and row['band']['passed'] and row['independent_integrals']['passed']
        rows.append(row)
        (args.out/'progress.json').write_text(json.dumps(rows, indent=2)+'\n')
        after = _implementation_hashes()
        if after != before or artifact_hashes(args.from_evidence) != old_hashes or artifact_hashes(args.uniform_failure) != failed_hashes:
            raise ValueError('product or original preserved evidence changed during mixed B continuation')
        if any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != digest for p, digest in code.items()):
            raise ValueError('mixed B validator changed during fixed-source validation')
        result = dict(passed=row['passed'], shape='ellipse', polarization='tm', scale=report['scale'],
            previous_evidence=str(args.from_evidence), uniform_failure=str(args.uniform_failure),
            physically_restored_previous_solutions=list(restored), new_FEM_solves=new_solves,
            accepted_A='A-L4', accepted_B=label if row['passed'] else None, records=rows,
            product_files_unchanged=len(after), original_artifacts_unchanged=len(old_hashes),
            elapsed_s=time.monotonic()-started, scope='mixed B bisection after terminal original-map roundoff failure; original P2 and all gates fixed')
        (args.out/'implementation-after.json').write_text(json.dumps(after, indent=2)+'\n')
        (args.out/'report.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps({k:v for k,v in result.items() if k!='records'}, indent=2), flush=True)
        if not result['passed']:
            raise AssertionError('mixed ellipse B gates unmet; preserve failures without relaxed tolerances')
    except Exception as exc:
        (args.out/'progress.json').write_text(json.dumps(rows, indent=2)+'\n')
        (args.out/'failed-evidence.json').write_text(json.dumps(dict(error=repr(exc), new_FEM_solves=new_solves,
            elapsed_s=time.monotonic()-started), indent=2)+'\n')
        raise


if __name__ == '__main__':
    main()
