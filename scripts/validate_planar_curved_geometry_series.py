#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""P07 geometry approximation and separate fixed-P2 FEM gates, one domain.

Run independent N16/32/64 inputs; do not confuse more boundary segments with
FEM convergence on one original P2 domain. All failed coarse levels remain.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time
import numpy as np
from superfish_ng.jobs import _implementation_hashes
from superfish_ng.planar_curved import PlanarCurvedCase
from superfish_ng.planar_curved_solver import solve_planar_curved
from planar_curved_mesh_reference import restriction_chain
from planar_curved_shape_reference import ellipse_domain, ellipse_geometry
from planar_curved_vector_reference import vectorized_validation_view
from planar_curved_circle_reference import check_circle_streaming
from validate_planar_curved_fem import circle_domain
from validate_planar_curved_shapes import mode_groups, band_checks
from validate_planar_curved_rf import groups as circle_groups
from validate_planar_curved_independent import independent_integrals, save_solution
from validate_planar_curved_convergence import compare_pair


def circle_geometry(domain, radius, count):
    half_angle = np.pi/count
    area = count*radius**2*np.sin(half_angle)*(4-np.cos(half_angle))/3
    area_error = abs(domain.area_m2/area-1)
    if area_error > 1e-12:
        raise ValueError('circle P2 area disagrees with independent Green/circular formula')
    perimeter = domain.boundary_length_m(quadrature_order=20)
    metrics = dict(exact_P2_area_relative_error=area_error,
        true_area_relative_error=abs(domain.area_m2/(np.pi*radius**2)-1),
        true_perimeter_relative_error=abs(perimeter/(2*np.pi*radius)-1),
        true_boundary_distance_upper_bound_over_major_axis=1-math.sqrt(1-(1-math.cos(half_angle))**2/4))
    metrics['geometry_gates_passed'] = all(metrics[name] <= 1e-4 for name in
        ('true_area_relative_error', 'true_perimeter_relative_error', 'true_boundary_distance_upper_bound_over_major_axis'))
    return metrics


def fixed_domain_passed(comparison, shape, polarization):
    if shape not in ('circle', 'ellipse') or polarization not in ('te', 'tm'):
        raise ValueError('geometry-series acceptance requires circle/ellipse and TE/TM')
    expected = len(circle_groups(polarization)) if shape == 'circle' else 6
    if len(comparison['groups']) != expected:
        raise ValueError('geometry-series acceptance requires the complete target and guard band')
    count = 3  # ellipse: three complete simple modes
    if shape == 'circle':
        selected = [r for r, g in zip(comparison['groups'], circle_groups(polarization)) if g[3]]
    else:
        selected = comparison['groups'][:count]
    return all(r['passed'] for r in selected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shape', choices=('circle', 'ellipse'), required=True)
    parser.add_argument('--polarization', choices=('te', 'tm'), required=True)
    parser.add_argument('--scale', type=int, choices=(1, 2), required=True)
    parser.add_argument('--angular-segments', type=int, choices=(16, 32, 64), required=True)
    parser.add_argument('--max-level', type=int, default=4)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if not 2 <= args.max_level <= 5:
        parser.error('max-level must be 2..5')
    args.out.mkdir(parents=True, exist_ok=False)
    before, started = _implementation_hashes(), time.monotonic()
    (args.out/'implementation-before.json').write_text(json.dumps(before, indent=2)+'\n')
    modules = [Path(__file__), *(Path(__file__).with_name(name) for name in
        ('planar_curved_circle_reference.py', 'planar_curved_mesh_reference.py',
         'planar_curved_shape_reference.py', 'planar_curved_vector_reference.py',
         'validate_planar_curved_fem.py', 'validate_planar_curved_rf.py',
         'validate_planar_curved_shapes.py', 'validate_planar_curved_independent.py',
         'validate_planar_curved_convergence.py'))]
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in modules}
    (args.out/'validator-hashes.json').write_text(json.dumps(hashes, indent=2)+'\n')
    radius = .01*args.scale
    if args.shape == 'circle':
        original = circle_domain(radius, args.angular_segments)
        geometry = circle_geometry(original, radius, args.angular_segments)
        definition = [g[2] for g in circle_groups(args.polarization)]
    else:
        original = ellipse_domain(args.angular_segments, scale=args.scale)
        geometry = ellipse_geometry(original, args.angular_segments, scale=args.scale)
        definition = mode_groups('ellipse', args.polarization)
    (args.out/'original-domain.json').write_text(json.dumps(original.to_dict(), indent=2)+'\n')
    records, prior, accepted = [], None, None
    try:
        for level in range(args.max_level+1):
            print(f'{args.shape} N={args.angular_segments} {args.polarization} s={args.scale} L={level}: regenerating', flush=True)
            charts = restriction_chain(original, ('uniform',)*level)
            case = PlanarCurvedCase(charts.domain, args.polarization, modes=sum(definition), max_geometry_boxes=100000000)
            solution = solve_planar_curved(case)
            view = vectorized_validation_view(solution)
            label = f'L{level}'
            save_solution(args.out/label, solution, charts)
            record = dict(label=label, level=level, cells=len(case.domain.cell_nodes), dofs=len(solution.coefficients),
                independent_integrals=independent_integrals(view),
                final_original_map_relative_bound=charts.maximum_relative_coordinate_bound)
            records.append(record)
            if args.shape == 'circle':
                record['analytic'] = check_circle_streaming(view, radius)
                band_passed = record['analytic']['full_analytic_guard_groups_present'] and record['analytic']['independent_energy_passed']
                absolute_passed = record['analytic']['target_groups_passed']
            else:
                record['band'] = band_checks(solution, 'ellipse', args.scale)
                band_passed, absolute_passed = record['band']['passed'], True
            if prior is not None:
                record['last_two'] = compare_pair(prior, view, definition)
                record['fixed_FEM_passed'] = fixed_domain_passed(record['last_two'], args.shape, args.polarization)
            else:
                record['fixed_FEM_passed'] = False
            record['passed'] = (level >= 2 and geometry['geometry_gates_passed'] and band_passed
                and absolute_passed and record['fixed_FEM_passed'] and record['independent_integrals']['passed'])
            (args.out/label/'checks.json').write_text(json.dumps(record, indent=2)+'\n')
            (args.out/'progress.json').write_text(json.dumps(records, indent=2)+'\n')
            print(f'{label}: geometry={geometry["geometry_gates_passed"]}, fixed FEM={record["fixed_FEM_passed"]}, analytic={absolute_passed}, complete={record["passed"]}', flush=True)
            if record['passed']:
                accepted = record
                break
            prior = view
        after = _implementation_hashes()
        if after != before or any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != digest for p, digest in hashes.items()):
            raise ValueError('product or geometry-series validator changed during validation')
        result = dict(passed=accepted is not None, shape=args.shape, polarization=args.polarization, scale=args.scale,
            angular_segments=args.angular_segments, geometry=geometry, records=records,
            accepted_level=None if accepted is None else accepted['level'],
            new_FEM_solves=len(records), product_files_unchanged=len(after), elapsed_s=time.monotonic()-started,
            scope='one geometry-series domain; true geometry errors and fixed-domain FEM differences are separate',
            remaining_P07=['other geometry-series domains', 'independent-mesh conditions', 'parent audit'])
        (args.out/'implementation-after.json').write_text(json.dumps(after, indent=2)+'\n')
        (args.out/'report.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps({k: v for k, v in result.items() if k not in ('records', 'geometry')}, indent=2), flush=True)
        if not result['passed']:
            raise AssertionError('geometry/FEM/analytical gates unmet; preserve evidence and refine')
    except Exception as exc:
        (args.out/'failed-evidence.json').write_text(json.dumps(dict(error=repr(exc), elapsed_s=time.monotonic()-started), indent=2)+'\n')
        raise


if __name__ == '__main__':
    main()
