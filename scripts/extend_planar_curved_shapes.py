#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Extend terminal failed noncircular evidence without repeating its FEM solves.

All original artifacts stay read-only. Reused fields are physically restored
against their complete regenerated native domains. Newly required A/B levels
are actual independent FEM solves with the unchanged P05 gates.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import time
import numpy as np
from superfish_ng.jobs import _implementation_hashes
from superfish_ng.planar_curved import PlanarCurvedCase
from superfish_ng.planar_curved_solver import solve_planar_curved
from superfish_ng.project import parse_json
from planar_curved_mesh_reference import restriction_chain, compare_meshes
from planar_curved_shape_reference import ellipse_domain, corner_domain
from planar_curved_vector_reference import vectorized_validation_view
from validate_planar_curved_shapes import mode_groups, band_checks, targets_passed
from validate_planar_curved_independent import independent_integrals, save_solution
from validate_planar_curved_convergence import restore_evidence, compare_pair


def artifact_hashes(folder):
    result = {}
    for path in sorted(folder.rglob('*')):
        if path.is_symlink():
            raise ValueError('previous shape evidence must not contain symbolic links')
        if path.is_file():
            result[str(path.relative_to(folder))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def previous_specification(folder):
    report = parse_json((folder/'report.json').read_text())
    if report.get('passed') is not False or report.get('scope') != 'one synthetic noncircle, fixed original P2 domain; finite A/B and last-two f/E/H/full RF':
        raise ValueError('extension requires terminal failed fixed-domain noncircular evidence')
    before = _implementation_hashes()
    for name in ('implementation-before.json', 'implementation-after.json'):
        if parse_json((folder/name).read_text()) != before:
            raise ValueError('previous shape evidence requires unchanged production hashes')
    code = parse_json((folder/'validator-hashes.json').read_text())
    required = {Path(__file__).resolve().with_name(name) for name in
        ('validate_planar_curved_shapes.py', 'planar_curved_mesh_reference.py',
         'planar_curved_shape_reference.py', 'planar_curved_vector_reference.py',
         'validate_planar_curved_independent.py', 'validate_planar_curved_convergence.py',
         'validate_planar_curved_fem.py', 'validate_planar_curved_rf.py')}
    if len(code) != len(required) or {Path(name).resolve() for name in code} != required:
        raise ValueError('previous shape evidence requires complete validator hashes')
    for name, expected in code.items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != expected:
            raise ValueError(f'previous shape validator changed: {name}')
    shape, polarization, scale = report['shape'], report['polarization'], report['scale']
    if shape not in ('ellipse', 'corner') or polarization not in ('te', 'tm') or type(scale) is not int or scale not in (1, 2):
        raise ValueError('previous shape specification must retain the exact supported input')
    rows = report['records']
    if not rows or len({r['label'] for r in rows}) != len(rows):
        raise ValueError('previous shape evidence requires unique complete trial labels')
    if report['new_FEM_solves'] != len(rows) or parse_json((folder/'progress.json').read_text()) != rows:
        raise ValueError('previous terminal report must match the complete trial progress')
    for row in rows:
        match = re.fullmatch(r'([AB])-L([1-5])', row['label'])
        if match is None:
            raise ValueError('previous shape trial label must be a local A/B level')
        kind, level = match[1], int(match[2])
        expected = ['uniform']*level if kind == 'A' else ['bisection']+['uniform']*(level-1)
        if row['patterns'] != expected:
            raise ValueError('previous shape patterns disagree with the level and series')
        for name in ('case.json', 'fem-fields.npz', 'patterns.json', 'regenerated-parent-charts.npz'):
            if not (folder/row['label']/name).is_file():
                raise ValueError(f'previous shape evidence missing {row["label"]}/{name}')
    if report['accepted_B'] is not None:
        raise ValueError('failed shape evidence must not claim an accepted B series')
    a_levels = [len(r['patterns']) for r in rows if r['label'].startswith('A-')]
    b_levels = [len(r['patterns']) for r in rows if r['label'].startswith('B-')]
    if not a_levels or a_levels != list(range(1, max(a_levels)+1)):
        raise ValueError('previous A levels must be the complete consecutive prefix')
    if b_levels:
        if report['accepted_A'] != f'A-L{max(a_levels)}' or b_levels != list(range(max(a_levels)-1, max(b_levels)+1)):
            raise ValueError('previous B levels must follow the actual accepted A prefix')
        if any(r.get('passed') for r in rows if r['label'].startswith('B-')):
            raise ValueError('terminal failed B prefix must not contain a successful B trial')
    if shape == 'ellipse':
        count = report['initial_angular_segments']
        if type(count) is not int or count not in (16, 32, 64):
            raise ValueError('previous ellipse must retain its initial angular segments')
        original = ellipse_domain(count, scale=scale)
    else:
        original = corner_domain(.01*scale)
    return report, original, artifact_hashes(folder)


def restore_state(folder, row, original):
    charts = restriction_chain(original, tuple(row['patterns']))
    solution = restore_evidence(folder/row['label'])
    if solution.case.domain != charts.domain:
        raise ValueError('previous native geometry differs from full regenerated original restrictions')
    if parse_json((folder/row['label']/'patterns.json').read_text()) != row['patterns']:
        raise ValueError('previous saved patterns disagree with the trial')
    # The saved NPZ is evidence only: regenerate all charts first, then compare.
    with np.load(folder/row['label']/'regenerated-parent-charts.npz', allow_pickle=False) as raw:
        for name, expected in (('parent_cells', charts.parents), ('parent_reference_vertices', charts.vertices),
            ('coordinate_error_bounds_m', charts.coordinate_bounds_m)):
            if not np.array_equal(raw[name], expected):
                raise ValueError(f'previous saved chart artifact differs: {name}')
    return vectorized_validation_view(solution), charts, row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-evidence', required=True, type=Path)
    parser.add_argument('--max-level', type=int, default=5)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    if args.max_level != 5:
        parser.error('this bounded extension permits level 5 only')
    report, original, original_hashes = previous_specification(args.from_evidence)
    args.out.mkdir(parents=True, exist_ok=False)
    started, before = time.monotonic(), _implementation_hashes()
    (args.out/'implementation-before.json').write_text(json.dumps(before, indent=2)+'\n')
    (args.out/'reused-artifact-hashes.json').write_text(json.dumps(original_hashes, indent=2)+'\n')
    (args.out/'previous-report.json').write_text(json.dumps(report, indent=2)+'\n')
    modules = [Path(__file__), *(Path(__file__).with_name(name) for name in
        ('planar_curved_mesh_reference.py', 'planar_curved_shape_reference.py',
         'planar_curved_vector_reference.py', 'validate_planar_curved_shapes.py',
         'validate_planar_curved_independent.py', 'validate_planar_curved_convergence.py',
         'validate_planar_curved_fem.py', 'validate_planar_curved_rf.py'))]
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in modules}
    (args.out/'validator-hashes.json').write_text(json.dumps(hashes, indent=2)+'\n')
    shape, polarization, scale = report['shape'], report['polarization'], report['scale']
    definition = mode_groups(shape, polarization)
    rows = {r['label']: r for r in report['records']}
    new_rows, restored_labels = [], []
    accepted_a, accepted_b = None, None

    def restore(label):
        print(f'physically restoring {label}', flush=True)
        state = restore_state(args.from_evidence, rows[label], original)
        if state[0].case.modes != sum(definition):
            raise ValueError('previous shape fields must retain the complete band')
        restored_labels.append(label)
        return state

    def run(patterns, label):
        print(f'solving additional {label}', flush=True)
        charts = restriction_chain(original, tuple(patterns))
        case = PlanarCurvedCase(charts.domain, polarization, modes=sum(definition), max_geometry_boxes=100000000)
        solution = solve_planar_curved(case)
        save_solution(args.out/label, solution, charts)
        view = vectorized_validation_view(solution)
        row = dict(label=label, patterns=list(patterns), cells=len(case.domain.cell_nodes), dofs=len(solution.coefficients),
            band=band_checks(solution, shape, scale), independent_integrals=independent_integrals(view),
            final_original_map_relative_bound=charts.maximum_relative_coordinate_bound)
        new_rows.append(row)
        return view, charts, row

    def checkpoint():
        (args.out/'progress.json').write_text(json.dumps(new_rows, indent=2)+'\n')

    try:
        if report['accepted_A'] is not None:
            label = report['accepted_A']
            if label not in rows or not rows[label].get('passed'):
                raise ValueError('previous accepted A must refer to an actual passed trial')
            accepted_a = restore(label)
            level = len(accepted_a[1].patterns)
            coarse = restore(f'A-L{level-1}')
            replay = compare_pair(coarse[0], accepted_a[0], definition)
            band = band_checks(accepted_a[0], shape, scale)
            integral = independent_integrals(accepted_a[0])
            if not targets_passed(replay) or not band['passed'] or not integral['passed']:
                raise ValueError('previous accepted A does not pass independent physical replay')
            (args.out/'replayed-accepted-A.json').write_text(json.dumps(dict(comparison=replay, band=band, independent_integrals=integral), indent=2)+'\n')
        else:
            last = max((r for r in rows.values() if r['label'].startswith('A-')), key=lambda r: len(r['patterns']))
            prior = restore(last['label'])
            level = len(prior[1].patterns)+1
            if level > args.max_level:
                raise ValueError('no additional A level remains within the declared budget')
            current = run(('uniform',)*level, f'A-L{level}')
            current[2]['last_two'] = compare_pair(prior[0], current[0], definition)
            current[2]['passed'] = targets_passed(current[2]['last_two']) and current[2]['band']['passed'] and current[2]['independent_integrals']['passed']
            checkpoint()
            if current[2]['passed']:
                accepted_a = current
        if accepted_a is not None:
            old_b = [r for r in rows.values() if r['label'].startswith('B-')]
            if old_b:
                last = max(old_b, key=lambda r: len(r['patterns']))
                prior = restore(last['label'])
                start = len(prior[1].patterns)+1
            else:
                prior = None
                start = len(accepted_a[1].patterns)-1
            for level in range(start, args.max_level+1):
                current = run(('bisection',)+('uniform',)*(level-1), f'B-L{level}')
                if prior is not None:
                    current[2]['last_two'] = compare_meshes(prior[0], current[0], prior[1], current[1], definition)
                    current[2]['A_vs_B'] = compare_meshes(accepted_a[0], current[0], accepted_a[1], current[1], definition)
                    current[2]['passed'] = (targets_passed(current[2]['last_two']) and targets_passed(current[2]['A_vs_B'])
                        and current[2]['band']['passed'] and current[2]['independent_integrals']['passed'])
                else:
                    current[2]['passed'] = False
                checkpoint()
                print(f'{current[2]["label"]}: all final gates={current[2]["passed"]}', flush=True)
                if current[2]['passed']:
                    accepted_b = current
                    break
                prior = current
        after = _implementation_hashes()
        if before != after or artifact_hashes(args.from_evidence) != original_hashes:
            raise ValueError('product or original failed artifacts changed during extension')
        if any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != digest for p, digest in hashes.items()):
            raise ValueError('extension validator changed during fixed-source validation')
        result = dict(passed=accepted_a is not None and accepted_b is not None, shape=shape, polarization=polarization, scale=scale,
            previous_evidence=str(args.from_evidence), previous_FEM_solutions=len(rows),
            physically_restored_previous_solutions=restored_labels, new_FEM_solves=len(new_rows), records=new_rows,
            accepted_A=None if accepted_a is None else accepted_a[2]['label'], accepted_B=None if accepted_b is None else accepted_b[2]['label'],
            elapsed_s=time.monotonic()-started, product_files_unchanged=len(after), original_artifacts_unchanged=len(original_hashes),
            scope='bounded extension of failed noncircular fixed-P2 A/B evidence; original raw remains unchanged')
        (args.out/'implementation-after.json').write_text(json.dumps(after, indent=2)+'\n')
        (args.out/'report.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps({k: v for k, v in result.items() if k != 'records'}, indent=2), flush=True)
        if not result['passed']:
            raise AssertionError('extended fixed-domain gates unmet; retain failures without relaxed tolerance')
    except Exception as exc:
        checkpoint()
        (args.out/'failed-evidence.json').write_text(json.dumps(dict(error=repr(exc), elapsed_s=time.monotonic()-started), indent=2)+'\n')
        raise


if __name__ == '__main__':
    main()
