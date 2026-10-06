#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind accepted noncircle raw to the strict/cache/grouping implementation.

Regenerate complete original parent charts/native matrices and lowest band.
Preserve coefficients/frequencies bitwise and all RF metadata exactly. The
only allowed RF numerical difference is canonical wall floating roundoff.
No new FEM solve, fitted correction or relaxed physical gate is introduced.
"""
import argparse
from dataclasses import fields
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from superfish_ng.jobs import _implementation_hashes
from superfish_ng.project import parse_json
from superfish_ng.planar_curved_solver import PlanarCurvedSolution, planar_curved_quantities
from superfish_ng.planar_curved_geometry import _canonical_boundary_parameters
from extend_planar_curved_shapes import artifact_hashes, restore_state
from planar_curved_shape_reference import corner_domain, ellipse_domain
from planar_curved_vector_reference import original_vectors
from validate_planar_curved_shapes import mode_groups, band_checks, targets_passed
from validate_planar_curved_independent import independent_integrals


def verify_RF(actual, expected):
    """Complete original RF schema/metadata plus <=1e-12 floating roundoff."""
    if not actual or len(actual) != len(expected):
        raise ValueError('source bridge requires the complete original RF band')
    differences = {}
    for a, b in zip(actual, expected):
        if set(a) != set(b):
            raise ValueError('source bridge requires identical complete RF schemas')
        for name, value in b.items():
            if type(value) is float:
                if type(a[name]) is not float or not np.isfinite(value) or not np.isfinite(a[name]):
                    raise ValueError('source bridge requires finite original RF numerical values')
                difference = abs(a[name]/value-1) if value else abs(a[name]-value)
                if difference > 1e-12:
                    raise ValueError('canonical wall roundoff exceeds source bridge limit 1e-12')
                differences[name] = max(differences.get(name, 0.), difference)
            elif a[name] != value or type(a[name]) is not type(value):
                raise ValueError('source bridge RF metadata, units, orders, nulls and reasons must be exactly identical')
    return differences


def sampled_original_fields(solution):
    """Signed public E/H versus independent literal P2/Maxwell evaluation."""
    cells = np.unique(np.linspace(0, len(solution.space.cell_nodes)-1, 48, dtype=int))
    refs = np.array([[.2, .3], [.1, .6], [.4, .1]])
    errors = [0., 0.]
    for cell in cells:
        public = solution.all_fields_at_reference(np.full(len(refs), cell), refs)
        literal = original_vectors(solution, int(cell), refs)
        for index, (name, unit) in enumerate((('E', 'V_per_m'), ('H', 'A_per_m'))):
            actual = np.stack([public[f'{name}{axis}_real_{unit}']+1j*public[f'{name}{axis}_quadrature_{unit}'] for axis in 'xyz'], axis=1)
            denominator = np.linalg.norm(literal[index])
            difference = np.linalg.norm(actual-literal[index])
            error = float(difference/denominator) if denominator else float(difference)
            if not np.isfinite(error) or error > 1e-12:
                raise ValueError('signed public original E/H differs from independent literal field')
            errors[index] = max(errors[index], error)
    if solution.case.polarization == 'tm':
        t, _ = np.polynomial.legendre.leggauss(32)
        t = _canonical_boundary_parameters((t+1)/2)
        for owner, local in zip(solution.case.domain.boundary_cells, solution.case.domain.boundary_local_edges):
            wall = np.column_stack((t, 0*t)) if local == 0 else np.column_stack((1-t, t)) if local == 1 else np.column_stack((0*t, 1-t))
            actual = solution.all_fields_at_reference(np.full(len(t), owner), wall)['Ez_real_V_per_m']
            if np.any(actual != 0.):
                raise ValueError('original TM essential PEC scalar must be exactly zero on the canonical wall')
    return dict(sampled_cells=len(cells), reference_points_per_cell=len(refs),
        electric_relative_difference=errors[0], magnetic_relative_difference=errors[1],
        independent_signed_field_limit=1e-12,
        exact_TM_PEC_wall_checked=solution.case.polarization == 'tm',
        exact_TM_PEC_wall_modes=solution.case.modes if solution.case.polarization == 'tm' else 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('accepted-evidence', 'accepted-artifact-hashes', 'saved-solution', 'original-source', 'accepted-implementation', 'out'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    started, before = time.monotonic(), _implementation_hashes()
    original_source = parse_json(args.original_source.read_text())
    approved = parse_json((args.accepted_implementation/'implementation-after.json').read_text())
    changed = ['planar_curved_geometry.py', 'planar_curved_location.py', 'planar_curved_refinement.py', 'planar_curved_solver.py']
    if before != approved or set(before) != set(original_source) or [k for k in before if before[k] != original_source[k]] != changed:
        raise ValueError('source bridge requires the physically accepted strict/cache/grouping source and exactly four declared product changes')
    accepted_hashes = parse_json(args.accepted_artifact_hashes.read_text())
    if args.accepted_evidence.name in accepted_hashes:
        accepted_hashes = accepted_hashes[args.accepted_evidence.name]
    if 'artifacts_sha256' in accepted_hashes:
        accepted_hashes = accepted_hashes['artifacts_sha256']
    if artifact_hashes(args.accepted_evidence) != accepted_hashes:
        raise ValueError('complete accepted report/raw differs from its preserved terminal snapshot')
    if args.saved_solution.parent.resolve() != args.accepted_evidence.resolve():
        # The recovered corner TE B5 remains in its original interrupted folder.
        # Bind those external original bytes to a snapshot IN the accepted report.
        saved_hashes = artifact_hashes(args.saved_solution.parent)
        if not any(parse_json(p.read_text()) == saved_hashes for p in args.accepted_evidence.glob('*artifact-hashes.json')):
            raise ValueError('external saved original raw is not bound to the accepted recovery snapshot')
    report = parse_json((args.accepted_evidence/'report.json').read_text())
    if not report['passed'] or report['shape'] not in ('corner', 'ellipse') or report['polarization'] not in ('te', 'tm') or type(report['scale']) is not int or report['scale'] not in (1, 2):
        raise ValueError('source bridge requires an actually accepted noncircle, polarization and independent scale')
    label = report['accepted_B']
    if not label or args.saved_solution.name != label:
        raise ValueError('source bridge saved solution must be the exact accepted B')
    row = report if 'last_two' in report else next(r for r in report['records'] if r['label'] == label)
    if not targets_passed(row['last_two']) or not targets_passed(row['A_vs_B']) or not row['band']['passed'] or not row['independent_integrals']['passed']:
        raise ValueError('complete original last-two, A/B, guard and independent physical acceptance is mandatory')
    old_before = parse_json((args.accepted_evidence/'implementation-before.json').read_text())
    if parse_json((args.accepted_evidence/'implementation-after.json').read_text()) != old_before or set(old_before) != set(original_source):
        raise ValueError('accepted evidence requires unchanged complete original source provenance')
    old_changes = [k for k in old_before if old_before[k] != original_source[k]]
    if old_changes not in ([], ['planar_curved_geometry.py'], ['planar_curved_geometry.py', 'planar_curved_refinement.py']):
        raise ValueError('only explicitly accepted old geometry/boundary source variants may be bridged')
    for name, digest in parse_json((args.accepted_evidence/'validator-hashes.json').read_text()).items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest:
            raise ValueError('original accepted validator source changed before bridge')
    patterns = parse_json((args.saved_solution/'patterns.json').read_text())
    if 'patterns' in row and row['patterns'] != patterns:
        raise ValueError('accepted pattern ancestry differs from saved original raw')
    snapshots = {str(p): artifact_hashes(p) for p in (args.accepted_evidence, args.saved_solution)}
    modules = [Path(__file__), *(Path(__file__).with_name(n) for n in
        ('extend_planar_curved_shapes.py', 'planar_curved_mesh_reference.py', 'planar_curved_shape_reference.py',
         'planar_curved_vector_reference.py', 'validate_planar_curved_shapes.py', 'validate_planar_curved_independent.py',
         'validate_planar_curved_convergence.py', 'validate_planar_curved_fem.py', 'validate_planar_curved_rf.py'))]
    code = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in modules}
    args.out.mkdir(parents=True, exist_ok=False)
    write = lambda name, value: (args.out/(name+'.json')).write_text(json.dumps(value, indent=2)+'\n')
    for name, value in [('implementation-before', before), ('validator-hashes', code), ('original-artifact-hashes', snapshots),
        ('source-transition', dict(original_main_source=original_source, accepted_old_source=old_before,
            changed_main_product_files=changed, accepted_old_changes=old_changes, preserved_old_main_product_files=397))]:
        write(name, value)
    try:
        shape, polarization, scale = report['shape'], report['polarization'], report['scale']
        original = corner_domain(.01*scale) if shape == 'corner' else ellipse_domain(16, scale=scale)
        print(f'physically rebuilding accepted {shape} {polarization} scale{scale} {label}, no new FEM', flush=True)
        view, charts, _ = restore_state(args.saved_solution.parent, dict(label=label, patterns=patterns), original)
        solution = PlanarCurvedSolution(**{f.name: getattr(view, f.name) for f in fields(PlanarCurvedSolution)})
        if solution.case.polarization != polarization or solution.case.modes != sum(mode_groups(shape, polarization)):
            raise ValueError('original polarization and full target/guard band must remain unchanged')
        with np.load(args.saved_solution/'fem-fields.npz', allow_pickle=False) as raw:
            np.testing.assert_array_equal(solution.coefficients, raw['coefficients'])
            np.testing.assert_array_equal(solution.frequencies_hz, raw['frequencies_hz'])
            for name, actual in [('coefficients', solution.coefficients), ('frequencies_hz', solution.frequencies_hz)]:
                if actual.dtype != raw[name].dtype or actual.tobytes() != raw[name].tobytes():
                    raise ValueError('original coefficient/frequency bitwise preservation must include signed zero')
        differences = verify_RF([planar_curved_quantities(solution, i) for i in range(solution.case.modes)], row['last_two']['second_RF'])
        band = band_checks(view, shape, scale)
        probes = sampled_original_fields(solution)
        print('original arrays/RF/public field probes matched; independent energy and actual sidewall', flush=True)
        integrals = independent_integrals(view)
        if not band['passed'] or not integrals['passed']:
            raise ValueError('source bridge full guard or independent physical integrals failed')
        after = _implementation_hashes()
        if before != after or any(artifact_hashes(Path(p)) != h for p, h in snapshots.items()) or any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != h for p, h in code.items()):
            raise ValueError('fixed product/code or preserved accepted raw changed during bridge')
        result = dict(passed=True, shape=shape, polarization=polarization, scale=scale, label=label,
            new_FEM_solves=0, physically_restored_saved_solutions=1,
            original_coefficients_frequencies_bitwise_unchanged=True, original_RF_metadata_exactly_unchanged=True,
            RF_relative_roundoff_differences=differences, independent_integrals=integrals, band=band,
            signed_original_field_probes=probes, final_original_map_relative_bound=charts.maximum_relative_coordinate_bound,
            product_files_fixed=len(after), preserved_original_main_product_files=397,
            elapsed_s=time.monotonic()-started, P07_complete=False,
            scope='accepted noncircle original arrays and full RF physically bridged to strict/cache/grouping source; no new FEM')
        write('implementation-after', after);write('report', result)
        print(json.dumps({k:v for k,v in result.items() if k not in ('band', 'independent_integrals', 'RF_relative_roundoff_differences')}, indent=2), flush=True)
    except Exception as exc:
        write('failed-evidence', dict(error=repr(exc), new_FEM_solves=0, elapsed_s=time.monotonic()-started))
        raise


if __name__ == '__main__':
    main()
