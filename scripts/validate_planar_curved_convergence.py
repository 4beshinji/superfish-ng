#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""P07 circular last-two-level gates on preserved original quadratic domains.

Reuses physically restored raw validator solutions. Uniform parent charts are
regenerated from the coarse domain, never trusted from a saved NPZ. This is
validation evidence, not a native result reader or a mode identity tracker.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from numpy.polynomial.legendre import leggauss
from superfish_ng.constants import EPS0, MU0
from superfish_ng.high_order import basis_p2
from superfish_ng.jobs import _implementation_hashes
from superfish_ng.planar_curved import PlanarCurvedCase
from superfish_ng.planar_curved_refinement import refine_planar_curved_domain
from superfish_ng.planar_curved_solver import (
    planar_curved_quantities, restore_planar_curved_solution, solve_planar_curved,
)
from superfish_ng.project import parse_json
from validate_planar_curved_rf import groups, check_solution


RF_VALUES = ('stored_energy_j_per_m', 'electric_energy_j_per_m',
    'magnetic_energy_j_per_m', 'wall_loss_w_per_m', 'surface_resistance_ohm',
    'q0', 'geometry_factor_ohm', 'wall_magnetic_integral_a2_per_m')
RF_NULLS = ('r_over_q_accelerator_ohm', 'r_over_q_circuit_ohm', 'vacc_v', 'eacc_v_per_m')


def _rule(order):
    if isinstance(order, bool) or not isinstance(order, int) or not 4 <= order <= 32:
        raise ValueError('comparison quadrature requires an integer order 4..32')
    nodes, weights = leggauss(order)
    nodes, weights = (nodes+1)/2, weights/2
    refs = np.array([[u, (1-u)*v] for u in nodes for v in nodes])
    measure = np.array([wu*wv*(1-u) for u, wu in zip(nodes, weights) for wv in weights])
    return refs, measure


def _vectors(solution, cell, refs):
    fields = solution.all_fields_at_reference(np.full(len(refs), cell), refs)
    return tuple(np.stack([fields[f'{field}{axis}_real_{unit}']+
        1j*fields[f'{field}{axis}_quadrature_{unit}'] for axis in 'xyz'], axis=1)
        for field, unit in (('E', 'V_per_m'), ('H', 'A_per_m')))


def compare_pair(coarse, fine, mode_groups, *, quadrature_order=10):
    """Direct weighted original E/H differences after ONE scalar group rotation.

    Two passes avoid subtraction of nearly equal Gram matrices. The first fits
    the common scalar rotation; the second integrates actual vector differences.
    Each declared group is complete in the supplied circular reference band.
    No fitted amplitudes, separate field phases, or permanent mode IDs occur.
    """
    for name in ('polarization', 'modes', 'normalization_j_per_m', 'conductivity_s_per_m'):
        if getattr(coarse.case, name) != getattr(fine.case, name):
            raise ValueError(f'fixed-domain comparison requires matching {name}')
    if not mode_groups or any(isinstance(n, bool) or not isinstance(n, int) or n < 1 for n in mode_groups) or sum(mode_groups) != coarse.case.modes:
        raise ValueError('comparison groups must partition the entire positive band')
    refs, reference_weights = _rule(quadrature_order)
    restriction = refine_planar_curved_domain(coarse.case.domain,
        max_geometry_boxes=fine.case.max_geometry_boxes)
    if restriction.domain != fine.case.domain:
        raise ValueError('fine geometry must be the regenerated original uniform restriction')
    count = coarse.case.modes
    cross = np.zeros((count, count))
    weights = np.empty((len(fine.case.domain.cell_nodes), len(refs)))
    gradients = np.array([[-1., -1.], [1., 0.], [0., 1.]])
    fine_basis = np.array([basis_p2([1-x-y, x, y], gradients)[0] for x, y in refs])
    parent_rules = {}
    for cell, parent in enumerate(restriction.parent_cells):
        vertices = restriction.parent_reference_vertices[cell]
        key = vertices.tobytes()
        if key not in parent_rules:
            parent_refs = vertices[0]+refs@(vertices[1:]-vertices[0])
            parent_basis = np.array([basis_p2([1-x-y, x, y], gradients)[0] for x, y in parent_refs])
            parent_rules[key] = (parent_refs, parent_basis)
        parent_refs, parent_basis = parent_rules[key]
        weights[cell] = reference_weights*fine.case.domain.elements[cell].evaluate(refs)['determinant_m2']
        a = parent_basis@coarse.coefficients[coarse.space.cell_nodes[parent]]
        b = fine_basis@fine.coefficients[fine.space.cell_nodes[cell]]
        cross += (a*weights[cell, :, None]).T@b
    material = MU0 if coarse.case.polarization == 'te' else EPS0
    cross *= material/(2*coarse.case.normalization_j_per_m)
    rotations, singular_values, selections = [], [], []
    offset = 0
    for multiplicity in mode_groups:
        selected = slice(offset, offset+multiplicity)
        u, singular, vt = np.linalg.svd(cross[selected, selected])
        rotations.append(u@vt)
        singular_values.append(singular.tolist())
        selections.append(selected)
        offset += multiplicity
    numerator = np.zeros((len(mode_groups), 2))
    denominator = np.zeros_like(numerator)
    for cell, parent in enumerate(restriction.parent_cells):
        vertices = restriction.parent_reference_vertices[cell]
        parent_refs = parent_rules[vertices.tobytes()][0]
        a, b = _vectors(coarse, int(parent), parent_refs), _vectors(fine, cell, refs)
        for group, (selected, rotation) in enumerate(zip(selections, rotations)):
            for field in range(2):
                reference = b[field][:, :, selected]
                difference = a[field][:, :, selected]@rotation-reference
                numerator[group, field] += np.einsum('p,pcm,pcm->', weights[cell], difference.conj(), difference).real
                denominator[group, field] += np.einsum('p,pcm,pcm->', weights[cell], reference.conj(), reference).real
    if not np.isfinite(numerator).all() or not np.isfinite(denominator).all() or np.any(denominator <= 0):
        raise ValueError('field comparison requires finite positive E and H norms')
    field_errors = np.sqrt(numerator/denominator)
    coarse_rf = [planar_curved_quantities(coarse, i) for i in range(count)]
    fine_rf = [planar_curved_quantities(fine, i) for i in range(count)]
    records = []
    for group, selected in enumerate(selections):
        ranks = list(range(selected.start, selected.stop))
        f_error = float(np.max(abs(coarse.frequencies_hz[selected]/fine.frequencies_hz[selected]-1)))
        rf_errors = {name: max(abs(coarse_rf[i][name]/fine_rf[i][name]-1) for i in ranks) for name in RF_VALUES}
        for i in ranks:
            if any(coarse_rf[i][name] is not None or fine_rf[i][name] is not None for name in RF_NULLS):
                raise ValueError('cutoff accelerating RF must remain explicitly unavailable')
            for name in ('accelerating_quantities_reason', 'phasor_convention', 'longitudinal_units'):
                if coarse_rf[i][name] != fine_rf[i][name]:
                    raise ValueError(f'RF metadata differs: {name}')
        gates = dict(frequency=f_error <= 1e-4, electric=bool(field_errors[group, 0] <= .01),
            magnetic=bool(field_errors[group, 1] <= .01), all_RF=max(rf_errors.values()) <= .005)
        records.append(dict(numerical_ranks_zero_based=ranks, frequency_relative_difference=f_error,
            electric_relative_L2_difference=float(field_errors[group, 0]),
            magnetic_relative_L2_difference=float(field_errors[group, 1]),
            RF_relative_differences=rf_errors, common_scalar_rotation=rotations[group].tolist(),
            scalar_alignment_singular_values=singular_values[group], gates=gates, passed=all(gates.values())))
    return dict(groups=records, comparison_quadrature_order=quadrature_order,
        restriction_relative_coordinate_bound=restriction.maximum_relative_coordinate_bound,
        coarse_RF=coarse_rf, fine_RF=fine_rf,
        scope='regenerated uniform parent charts; complete reference groups; no mode identity claim')


def restore_evidence(folder):
    case = PlanarCurvedCase.from_dict(parse_json((folder/'case.json').read_text()))
    with np.load(folder/'fem-fields.npz', allow_pickle=False) as raw:
        return restore_planar_curved_solution(case, raw['coefficients'], raw['frequencies_hz'])


def verify_source(previous, audit_path):
    before = _implementation_hashes()
    for name in ('implementation-before.json', 'implementation-after.json'):
        if before != json.loads((previous/name).read_text()):
            raise ValueError('reuse requires the exact unchanged production implementation')
    audit = json.loads(audit_path.read_text())
    relative = previous.resolve().relative_to(audit_path.parent.resolve())
    expected = {str(Path(name).relative_to(relative)): digest
        for name, digest in audit['raw_artifact_hashes'].items()
        if Path(name).is_relative_to(relative)}
    actual = {str(path.relative_to(previous)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in previous.rglob('*') if path.is_file()}
    if not expected or expected != actual:
        raise ValueError('reused raw evidence differs from its recorded complete artifact hashes')
    return before, actual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-evidence', required=True, type=Path)
    parser.add_argument('--source-audit', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--extend-failing', action='store_true', help='one new uniform FEM level only for failed target groups')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    before, raw_hashes = verify_source(args.from_evidence, args.source_audit)
    (args.out/'implementation-before.json').write_text(json.dumps(before, indent=2)+'\n')
    (args.out/'reused-artifact-hashes.json').write_text(json.dumps(raw_hashes, indent=2)+'\n')
    rows = json.loads((args.from_evidence/'progress.json').read_text())
    records, new_solves = [], 0
    try:
        for radius in (.01, .02):
            for polarization in ('te', 'tm'):
                last = sorted((row for row in rows if row['radius_m'] == radius and row['polarization'] == polarization), key=lambda row: row['level'])[-2:]
                if len(last) != 2 or last[1]['level'] != last[0]['level']+1:
                    raise ValueError('last two adjacent preserved levels are required')
                print(f'restoring {polarization} radius={radius} levels={[r["level"] for r in last]}', flush=True)
                coarse, fine = [restore_evidence(args.from_evidence/row['label']) for row in last]
                definition = groups(polarization)
                comparison = compare_pair(coarse, fine, [row[2] for row in definition])
                passed = all(row['passed'] for row, group in zip(comparison['groups'], definition) if group[3])
                record = dict(radius_m=radius, polarization=polarization,
                    levels=[row['level'] for row in last], initial=comparison, initial_target_groups_passed=passed)
                records.append(record)
                (args.out/'progress.json').write_text(json.dumps(records, indent=2)+'\n')
                print(f'{polarization}-r{radius:g}: initial last-two targets={passed}', flush=True)
                if not passed and args.extend_failing:
                    # More geometry work is explicitly budgeted; physical gates
                    # and the original boundary maps remain unchanged.
                    refined = refine_planar_curved_domain(fine.case.domain, max_geometry_boxes=100000000)
                    case = PlanarCurvedCase(refined.domain, polarization, modes=fine.case.modes,
                        quadrature_order=fine.case.quadrature_order,
                        wall_quadrature_order=fine.case.wall_quadrature_order,
                        max_geometry_boxes=100000000)
                    folder = args.out/f'{polarization}-r{radius:g}-L{last[1]["level"]+1}'
                    folder.mkdir()
                    (folder/'case.json').write_text(json.dumps(case.to_dict(), indent=2)+'\n')
                    print(f'solving {folder.name}: {len(case.domain.cell_nodes)} cells', flush=True)
                    extended = solve_planar_curved(case)
                    new_solves += 1
                    np.savez_compressed(folder/'fem-fields.npz', coefficients=extended.coefficients, frequencies_hz=extended.frequencies_hz)
                    np.savez_compressed(folder/'parent-restriction.npz', parent_cells=refined.parent_cells,
                        parent_reference_vertices=refined.parent_reference_vertices, coordinate_error_bounds_m=refined.coordinate_error_bounds_m)
                    record['extended_analytic'] = check_solution(extended, radius)
                    record['final'] = compare_pair(fine, extended, [row[2] for row in definition])
                    record['final_levels'] = [last[1]['level'], last[1]['level']+1]
                    record['final_target_groups_passed'] = record['extended_analytic']['target_groups_passed'] and all(
                        row['passed'] for row, group in zip(record['final']['groups'], definition) if group[3])
                    (folder/'checks.json').write_text(json.dumps(record, indent=2)+'\n')
                else:
                    record['final_target_groups_passed'] = passed
                    record['final_levels'] = record['levels']
                    record['final'] = comparison
                (args.out/'progress.json').write_text(json.dumps(records, indent=2)+'\n')
                print(f'{polarization}-r{radius:g}: final targets={record["final_target_groups_passed"]}', flush=True)
        after = _implementation_hashes()
        assert after == before, 'production changed during validation'
        result = dict(passed=all(row['final_target_groups_passed'] for row in records),
            scope='P07 circular fixed-domain last-two f/E/H/all RF, two scales/polarizations only',
            new_FEM_solves=new_solves, physically_restored_previous_solutions=8,
            elapsed_s=time.monotonic()-started, product_files_unchanged=len(after), records=records,
            remaining_P07_evidence=['independent A/B meshes', 'quadrature series', 'geometry series', 'ellipse and reentrant corner'])
        (args.out/'implementation-after.json').write_text(json.dumps(after, indent=2)+'\n')
        (args.out/'report.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps({k: v for k, v in result.items() if k != 'records'}, indent=2), flush=True)
        if not result['passed']:
            raise AssertionError('last-two target gate failed; retain evidence and refine without relaxing tolerances')
    except Exception:
        (args.out/'failed-evidence.json').write_text(json.dumps(dict(records=records,
            new_FEM_solves=new_solves, elapsed_s=time.monotonic()-started), indent=2)+'\n')
        (args.out/'implementation-after-failed.json').write_text(json.dumps(_implementation_hashes(), indent=2)+'\n')
        raise


if __name__ == '__main__':
    main()
