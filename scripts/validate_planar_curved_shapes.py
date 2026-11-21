#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""P07 fixed-domain noncircular field/RF mesh checks, one case per output.

Synthetic smooth ellipse or graded reentrant L. Finite mesh differences do
not provide absolute eigenvalue error bounds or finite corner peaks. Geometry
series FEM and transformed-field scale checks remain distinct acceptance gates.
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
from planar_curved_mesh_reference import restriction_chain, compare_meshes
from planar_curved_shape_reference import ellipse_domain, ellipse_geometry, corner_domain, corner_harmonic_integrals
from planar_curved_vector_reference import vectorized_validation_view
from validate_planar_curved_independent import independent_integrals, save_solution


def mode_groups(shape, polarization):
    # The L has the complete Neumann cos(pi x/a), cos(pi y/a) eigenspace.
    # Their ordered pair is checked against that invariant, not labelled as
    # individual IDs. Other groups are separated simple ranks in this band.
    return [1, 1, 2, 1, 1] if shape == 'corner' and polarization == 'te' else [1]*6


def band_checks(solution, shape, scale):
    groups = mode_groups(shape, solution.case.polarization)
    ends = np.cumsum(groups)[:-1]
    gaps = [float(solution.frequencies_hz[i]/solution.frequencies_hz[i-1]-1) for i in ends]
    result = dict(group_boundary_relative_gaps=gaps, complete_band_separated=min(gaps) > 1e-3)
    if shape == 'corner' and solution.case.polarization == 'te':
        from superfish_ng.constants import C0
        expected = C0/(2*.01*scale)
        result['smooth_Neumann_pair_frequency_relative_error'] = float(np.max(abs(solution.frequencies_hz[2:4]/expected-1)))
        result['complete_declared_pair_verified'] = result['smooth_Neumann_pair_frequency_relative_error'] <= 1e-4
    result['passed'] = result['complete_band_separated'] and result.get('complete_declared_pair_verified', True)
    return result


def targets_passed(comparison):
    return all(row['passed'] for row in comparison['groups'][:3])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shape', choices=('ellipse', 'corner'), required=True)
    parser.add_argument('--polarization', choices=('te', 'tm'), required=True)
    parser.add_argument('--scale', type=int, choices=(1, 2), required=True)
    parser.add_argument('--angular-segments', type=int, choices=(16, 32, 64), default=16)
    parser.add_argument('--max-level', type=int, default=4)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if not 2 <= args.max_level <= 5:
        parser.error('max-level must be 2..5')
    args.out.mkdir(parents=True, exist_ok=False)
    before = _implementation_hashes()
    started = time.monotonic()
    (args.out/'implementation-before.json').write_text(json.dumps(before, indent=2)+'\n')
    modules = (Path(__file__), *(Path(__file__).with_name(name) for name in
        ('planar_curved_mesh_reference.py', 'planar_curved_shape_reference.py',
         'planar_curved_vector_reference.py', 'validate_planar_curved_independent.py',
         'validate_planar_curved_convergence.py', 'validate_planar_curved_fem.py',
         'validate_planar_curved_rf.py')))
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in modules}
    (args.out/'validator-hashes.json').write_text(json.dumps(hashes, indent=2)+'\n')
    if args.shape == 'ellipse':
        original = ellipse_domain(args.angular_segments, scale=args.scale)
        geometry = ellipse_geometry(original, args.angular_segments, scale=args.scale)
    else:
        original = corner_domain(.01*args.scale)
        geometry = dict(area_relative_error=abs(original.area_m2/(3*(.01*args.scale)**2)-1),
            perimeter_relative_error=abs(original.boundary_length_m()/(8*.01*args.scale)-1),
            local_harmonic=corner_harmonic_integrals(.01*args.scale))
    groups = mode_groups(args.shape, args.polarization)
    records, accepted_a, accepted_b, prior = [], None, None, None

    def run(patterns, label):
        print(f'{label}: regenerating {patterns}', flush=True)
        charts = restriction_chain(original, patterns)
        case = PlanarCurvedCase(charts.domain, args.polarization, modes=sum(groups), max_geometry_boxes=100000000)
        solution = solve_planar_curved(case)
        save_solution(args.out/label, solution, charts)
        view = vectorized_validation_view(solution)
        record = dict(label=label, patterns=list(patterns), cells=len(charts.domain.cell_nodes),
            dofs=len(solution.coefficients), band=band_checks(solution, args.shape, args.scale),
            independent_integrals=independent_integrals(view),
            final_original_map_relative_bound=charts.maximum_relative_coordinate_bound)
        records.append(record)
        return view, charts, record

    def checkpoint():
        (args.out/'progress.json').write_text(json.dumps(records, indent=2)+'\n')

    try:
        for level in range(1, args.max_level+1):
            current = run(('uniform',)*level, f'A-L{level}')
            if prior is not None:
                current[2]['last_two'] = compare_meshes(prior[0], current[0], prior[1], current[1], groups)
                current[2]['passed'] = (targets_passed(current[2]['last_two'])
                    and current[2]['band']['passed'] and current[2]['independent_integrals']['passed'])
            else:
                current[2]['passed'] = False
            checkpoint()
            print(f'A-L{level}: all final gates={current[2]["passed"]}', flush=True)
            if current[2]['passed']:
                accepted_a = current
                break
            prior = current
        if accepted_a is not None:
            a_level = len(accepted_a[1].patterns)
            prior = None
            for level in range(a_level-1, min(args.max_level, a_level+1)+1):
                current = run(('bisection',)+('uniform',)*(level-1), f'B-L{level}')
                if prior is not None:
                    current[2]['last_two'] = compare_meshes(prior[0], current[0], prior[1], current[1], groups)
                    current[2]['A_vs_B'] = compare_meshes(accepted_a[0], current[0], accepted_a[1], current[1], groups)
                    current[2]['passed'] = (targets_passed(current[2]['last_two']) and targets_passed(current[2]['A_vs_B'])
                        and current[2]['band']['passed'] and current[2]['independent_integrals']['passed'])
                else:
                    current[2]['passed'] = False
                checkpoint()
                print(f'B-L{level}: all final gates={current[2]["passed"]}', flush=True)
                if current[2]['passed']:
                    accepted_b = current
                    break
                prior = current
        after = _implementation_hashes()
        if after != before or any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != digest for p, digest in hashes.items()):
            raise ValueError('product or validator changed during fixed-source validation')
        report = dict(passed=accepted_a is not None and accepted_b is not None,
            shape=args.shape, polarization=args.polarization, scale=args.scale, geometry=geometry,
            initial_angular_segments=args.angular_segments if args.shape == 'ellipse' else None,
            records=records, accepted_A=None if accepted_a is None else accepted_a[2]['label'],
            accepted_B=None if accepted_b is None else accepted_b[2]['label'],
            new_FEM_solves=len(records), product_files_unchanged=len(after), elapsed_s=time.monotonic()-started,
            scope='one synthetic noncircle, fixed original P2 domain; finite A/B and last-two f/E/H/full RF',
            remaining_P07=['other scales/polarizations', 'geometry series FEM', 'scale/rotation field checks', 'parent acceptance audit'])
        (args.out/'implementation-after.json').write_text(json.dumps(after, indent=2)+'\n')
        (args.out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps({k: v for k, v in report.items() if k not in ('geometry', 'records')}, indent=2), flush=True)
        if not report['passed']:
            raise AssertionError('mesh/band gates unmet; preserve coarse failures and refine without relaxed gates')
    except Exception as exc:
        checkpoint()
        (args.out/'failed-evidence.json').write_text(json.dumps(dict(error=repr(exc), elapsed_s=time.monotonic()-started), indent=2)+'\n')
        raise


if __name__ == '__main__':
    main()
