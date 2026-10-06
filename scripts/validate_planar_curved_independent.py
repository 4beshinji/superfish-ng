#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""P07 independent A/B meshes and quadrature on preserved quadratic circles.

Geometry-series, ellipse and corner gates remain separate. Original A results
are accepted only with complete raw hashes and unchanged product hashes.
All new actual FEM results, including failed coarse B levels, are preserved.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from numpy.polynomial.legendre import leggauss
from superfish_ng.constants import EPS0, MU0
from superfish_ng.jobs import _implementation_hashes
from superfish_ng.planar_curved import PlanarCurvedCase
from superfish_ng.planar_curved_solver import solve_planar_curved, planar_curved_quantities
from planar_curved_mesh_reference import restriction_chain, compare_meshes
from validate_planar_curved_convergence import verify_source, restore_evidence, _rule, _vectors, RF_VALUES
from validate_planar_curved_fem import circle_domain
from validate_planar_curved_rf import groups, check_solution


def independent_integrals(solution, order=20):
    """Independent area rule and full-vector normal subtraction at the wall."""
    refs, weights = _rule(order)
    energy = np.zeros((2, solution.case.modes))
    for cell, element in enumerate(solution.case.domain.elements):
        mapped = element.evaluate(refs)
        measure = weights*mapped['determinant_m2']
        for field, vectors in enumerate(_vectors(solution, cell, refs)):
            energy[field] += np.einsum('p,pcm,pcm->m', measure, vectors.conj(), vectors).real
    energy *= np.array([EPS0, MU0])[:, None]/4
    t, w = leggauss(order)
    t, w = (t+1)/2, w/2
    wall = np.zeros(solution.case.modes)
    for cell, local in zip(solution.case.domain.boundary_cells, solution.case.domain.boundary_local_edges):
        if local == 0:
            ref, direction = np.column_stack((t, 0*t)), np.array([1., 0.])
        elif local == 1:
            ref, direction = np.column_stack((1-t, t)), np.array([-1., 1.])
        else:
            ref, direction = np.column_stack((0*t, 1-t)), np.array([0., -1.])
        mapped = solution.case.domain.elements[cell].evaluate(ref)
        derivative = mapped['jacobian']@direction
        speed = np.linalg.norm(derivative, axis=1)
        normal = np.column_stack((derivative[:, 1], -derivative[:, 0], 0*t))/speed[:, None]
        magnetic = _vectors(solution, int(cell), ref)[1]
        normal_h = np.einsum('pc,pcm->pm', normal, magnetic)
        tangent = magnetic-normal[:, :, None]*normal_h[:, None, :]
        wall += np.einsum('p,pcm,pcm->m', w*speed, tangent.conj(), tangent).real
    rf = [planar_curved_quantities(solution, i) for i in range(solution.case.modes)]
    differences = dict(electric_energy=max(abs(energy[0, i]/row['electric_energy_j_per_m']-1) for i, row in enumerate(rf)),
        magnetic_energy=max(abs(energy[1, i]/row['magnetic_energy_j_per_m']-1) for i, row in enumerate(rf)),
        wall_magnetic_integral=max(abs(wall[i]/row['wall_magnetic_integral_a2_per_m']-1) for i, row in enumerate(rf)))
    return dict(order=order, differences={k: float(v) for k, v in differences.items()},
        passed=all(v <= 1e-8 for v in differences.values()))


def save_solution(folder, solution, charts):
    folder.mkdir()
    (folder/'case.json').write_text(json.dumps(solution.case.to_dict(), indent=2)+'\n')
    np.savez_compressed(folder/'fem-fields.npz', coefficients=solution.coefficients,
        frequencies_hz=solution.frequencies_hz)
    np.savez_compressed(folder/'regenerated-parent-charts.npz', parent_cells=charts.parents,
        parent_reference_vertices=charts.vertices, coordinate_error_bounds_m=charts.coordinate_bounds_m)
    (folder/'patterns.json').write_text(json.dumps(charts.patterns)+'\n')


def target_passed(comparison, polarization):
    return all(row['passed'] for row, group in zip(comparison['groups'], groups(polarization)) if group[3])


def quadrature_series(root):
    reports = []
    for radius in (.01, .02):
        charts = restriction_chain(circle_domain(radius, 16))
        for polarization in ('te', 'tm'):
            definition = [g[2] for g in groups(polarization)]
            solutions, rows = [], []
            for area, wall in ((8, 12), (12, 16), (16, 20)):
                case = PlanarCurvedCase(charts.domain, polarization, modes=sum(definition),
                    quadrature_order=area, wall_quadrature_order=wall, max_geometry_boxes=100000000)
                solution = solve_planar_curved(case)
                label = f'quadrature-{polarization}-r{radius:g}-a{area}-w{wall}'
                save_solution(root/label, solution, charts)
                integrals = independent_integrals(solution)
                rows.append(dict(label=label, area_order=area, wall_order=wall, independent_integrals=integrals))
                solutions.append(solution)
                print(f'{label}: independent area/wall={integrals}', flush=True)
            differences = []
            for first, second in zip(solutions, solutions[1:]):
                pair = compare_meshes(first, second, charts, charts, definition)
                f = max(r['frequency_relative_difference'] for r in pair['groups'])
                rf = max(max(r['RF_relative_differences'].values()) for r in pair['groups'])
                k = np.linalg.norm((first.stiffness-second.stiffness).data)/np.linalg.norm(second.stiffness.data)
                m = np.linalg.norm((first.mass-second.mass).data)/np.linalg.norm(second.mass.data)
                differences.append(dict(comparison=pair, frequency_max=f, all_RF_max=rf,
                    stiffness_relative_norm=float(k), mass_relative_norm=float(m), passed=f <= 1e-8 and rf <= 1e-8))
            restored = restore_evidence(root/rows[-1]['label'])
            if not np.array_equal(restored.coefficients, solutions[-1].coefficients):
                raise ValueError('physical restore replaced original quadrature coefficients')
            report = dict(radius_m=radius, polarization=polarization, orders=rows, differences=differences,
                last_original_physically_restored=True, passed=differences[-1]['passed'] and all(r['independent_integrals']['passed'] for r in rows))
            reports.append(report)
            (root/'quadrature-progress.json').write_text(json.dumps(reports, indent=2)+'\n')
    return reports


def independent_meshes(root, previous, source_audit, max_extra_levels):
    _, raw = verify_source(previous, source_audit)
    (root/'reused-A-artifact-hashes.json').write_text(json.dumps(raw, indent=2)+'\n')
    previous_rows = json.loads((previous/'progress.json').read_text())
    records = []
    for row in previous_rows:
        radius, polarization = row['radius_m'], row['polarization']
        level = row['final_levels'][-1]
        print(f'regenerating/restoring A {polarization} radius={radius} L={level}', flush=True)
        a_charts = restriction_chain(circle_domain(radius, 16), ('uniform',)*level)
        a = restore_evidence(previous/f'{polarization}-r{radius:g}-L{level}')
        if a.case.domain != a_charts.domain:
            raise ValueError('preserved A does not match regenerated full parent restrictions')
        definition = [g[2] for g in groups(polarization)]
        runs, prior = [], None
        record = dict(radius_m=radius, polarization=polarization, A_level=level, B_runs=runs, passed=False)
        records.append(record)
        for b_level in range(level-1, level+max_extra_levels+1):
            patterns = ('bisection',)+('uniform',)*(b_level-1)
            print(f'generating B {polarization} radius={radius} patterns={patterns}', flush=True)
            b_charts = restriction_chain(a_charts.original, patterns)
            b = solve_planar_curved(replace(a.case, domain=b_charts.domain))
            label = f'mesh-B-{polarization}-r{radius:g}-L{b_level}'
            save_solution(root/label, b, b_charts)
            run = dict(label=label, patterns=list(patterns), cells=len(b.case.domain.cell_nodes),
                dofs=len(b.coefficients), analytic=check_solution(b, radius),
                independent_integrals=independent_integrals(b),
                final_original_map_relative_bound=b_charts.maximum_relative_coordinate_bound)
            runs.append(run)
            if prior is not None:
                run['B_last_two'] = compare_meshes(prior[0], b, prior[1], b_charts, definition)
                run['A_vs_B'] = compare_meshes(a, b, a_charts, b_charts, definition)
                record['passed'] = (target_passed(run['B_last_two'], polarization)
                    and target_passed(run['A_vs_B'], polarization) and run['analytic']['target_groups_passed']
                    and run['independent_integrals']['passed'])
            (root/label/'checks.json').write_text(json.dumps(run, indent=2)+'\n')
            (root/'mesh-progress.json').write_text(json.dumps(records, indent=2)+'\n')
            print(f'{label}: full final gates={record["passed"]}', flush=True)
            if record['passed']:
                break
            prior = b, b_charts
    # A inputs are read-only throughout, including all coarse and failed runs.
    if verify_source(previous, source_audit)[1] != raw:
        raise ValueError('preserved A changed during independent mesh validation')
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--from-evidence', type=Path)
    parser.add_argument('--source-audit', type=Path)
    parser.add_argument('--quadrature-only', action='store_true')
    parser.add_argument('--mesh-only', action='store_true')
    parser.add_argument('--max-extra-levels', type=int, default=1)
    args = parser.parse_args()
    if args.quadrature_only and args.mesh_only or not 0 <= args.max_extra_levels <= 2:
        parser.error('select one stage; extra refinement budget must be 0..2')
    if not args.quadrature_only and (args.from_evidence is None or args.source_audit is None):
        parser.error('mesh stage requires --from-evidence and --source-audit')
    args.out.mkdir(parents=True, exist_ok=False)
    before = _implementation_hashes()
    started = time.monotonic()
    (args.out/'implementation-before.json').write_text(json.dumps(before, indent=2)+'\n')
    code = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in
        (Path(__file__), Path(__file__).with_name('planar_curved_mesh_reference.py'),
         Path(__file__).with_name('validate_planar_curved_convergence.py'),
         Path(__file__).with_name('validate_planar_curved_rf.py'),
         Path(__file__).with_name('validate_planar_curved_fem.py'))}
    (args.out/'validator-hashes.json').write_text(json.dumps(code, indent=2)+'\n')
    try:
        quadrature = [] if args.mesh_only else quadrature_series(args.out)
        mesh = [] if args.quadrature_only else independent_meshes(args.out, args.from_evidence, args.source_audit, args.max_extra_levels)
        after = _implementation_hashes()
        if before != after:
            raise ValueError('production changed during validation')
        for name, digest in code.items():
            if hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() != digest:
                raise ValueError('validator changed during validation')
        report = dict(passed=all(r['passed'] for r in quadrature+mesh), quadrature=quadrature, independent_meshes=mesh,
            elapsed_s=time.monotonic()-started, product_files_unchanged=len(after),
            scope='P07 circular independent A/B meshes and/or quadrature; declared reference groups only',
            remaining_P07=['geometry series with sufficiently fine FEM', 'ellipse', 'reentrant corner'])
        (args.out/'implementation-after.json').write_text(json.dumps(after, indent=2)+'\n')
        (args.out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps({k: v for k, v in report.items() if k not in ('quadrature', 'independent_meshes')}, indent=2), flush=True)
        if not report['passed']:
            raise AssertionError('fixed gates unmet: preserve failures and add refinement without relaxing tolerances')
    except Exception as exc:
        (args.out/'failed-evidence.json').write_text(json.dumps(dict(error=repr(exc), elapsed_s=time.monotonic()-started), indent=2)+'\n')
        raise


if __name__ == '__main__':
    main()
