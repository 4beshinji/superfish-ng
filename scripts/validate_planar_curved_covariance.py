#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Independent actual FEM under Cartesian scale, rotation and translation.

Covariance tests of the discrete formulation, not absolute shape accuracy.
Native nodes are all transformed; each problem is solved independently.
"""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from superfish_ng.constants import EPS0, MU0
from superfish_ng.jobs import _implementation_hashes
from superfish_ng.planar_curved import PlanarCurvedDomain, PlanarCurvedCase
from superfish_ng.planar_curved_solver import solve_planar_curved, planar_curved_quantities
from planar_curved_vector_reference import original_vectors
from planar_curved_shape_reference import ellipse_domain, corner_domain
from validate_planar_curved_fem import circle_domain
from validate_planar_curved_rf import groups as circle_groups
from validate_planar_curved_shapes import mode_groups
from validate_planar_curved_convergence import _rule, RF_VALUES, RF_NULLS


def transformed_domain(original, scale, rotation, translation):
    points = scale*original.points_xy_m@rotation.T+translation
    return PlanarCurvedDomain(points, original.cell_nodes, original.boundary_nodes, 100000000)


def compare_covariance(first, second, scale, rotation, translation, groups):
    rotation, translation = np.asarray(rotation, dtype=float), np.asarray(translation, dtype=float)
    if rotation.shape != (2, 2) or not np.isfinite(rotation).all() or not np.allclose(rotation.T@rotation, np.eye(2), rtol=0, atol=1e-14) or abs(np.linalg.det(rotation)-1) > 1e-14:
        raise ValueError('covariance requires an explicit proper Cartesian rotation')
    if translation.shape != (2,) or not np.isfinite(translation).all() or isinstance(scale, bool) or not isinstance(scale, (int, float)) or not np.isfinite(scale) or scale <= 0:
        raise ValueError('covariance requires positive finite scale and finite translation')
    if not groups or any(isinstance(n, bool) or not isinstance(n, int) or n < 1 for n in groups) or sum(groups) != first.case.modes:
        raise ValueError('covariance groups must partition the complete band')
    for name in ('polarization', 'modes', 'normalization_j_per_m', 'conductivity_s_per_m'):
        if getattr(first.case, name) != getattr(second.case, name):
            raise ValueError(f'covariance requires matching {name}')
    expected = transformed_domain(first.case.domain, scale, rotation, translation)
    if expected != second.case.domain:
        raise ValueError('covariance requires the complete transformed native domain')
    refs, weights = _rule(12)
    count = first.case.modes
    full_rotation = np.eye(3)
    full_rotation[:2, :2] = rotation
    material = MU0 if first.case.polarization == 'te' else EPS0
    cross = np.zeros((count, count))

    def sample(cell):
        measure = weights*first.case.domain.elements[cell].evaluate(refs)['determinant_m2']
        a = original_vectors(first, cell, refs)
        b = tuple(scale*np.einsum('pcm,cd->pdm', v, full_rotation)
            for v in original_vectors(second, cell, refs))
        return measure, a, b

    scalar_field = 1 if first.case.polarization == 'te' else 0
    for cell in range(len(first.case.domain.cell_nodes)):
        measure, a, b = sample(cell)
        cross += (a[scalar_field][:, 2].real*measure[:, None]).T@b[scalar_field][:, 2].real
    cross *= material/(2*first.case.normalization_j_per_m)
    offset, selections, rotations = 0, [], []
    for n in groups:
        selected = slice(offset, offset+n)
        u, _, vt = np.linalg.svd(cross[selected, selected])
        selections.append(selected)
        rotations.append(u@vt)
        offset += n
    numerator = np.zeros((len(groups), 2))
    denominator = np.zeros_like(numerator)
    for cell in range(len(first.case.domain.cell_nodes)):
        measure, a, b = sample(cell)
        for group, (selected, mode_rotation) in enumerate(zip(selections, rotations)):
            for field in range(2):
                reference = b[field][:, :, selected]
                difference = a[field][:, :, selected]@mode_rotation-reference
                numerator[group, field] += np.einsum('p,pcm,pcm->', measure, difference.conj(), difference).real
                denominator[group, field] += np.einsum('p,pcm,pcm->', measure, reference.conj(), reference).real
    if not np.isfinite(numerator).all() or not np.isfinite(denominator).all() or np.any(denominator <= 0):
        raise ValueError('covariance requires finite positive full E/H norms')
    errors = np.sqrt(numerator/denominator)
    rf = [[planar_curved_quantities(s, i) for i in range(count)] for s in (first, second)]
    powers = dict.fromkeys(RF_VALUES, 0.)
    powers.update(wall_loss_w_per_m=-1.5, surface_resistance_ohm=-.5, q0=.5,
        wall_magnetic_integral_a2_per_m=-1., domain_area_m2=2., boundary_length_m=1.)
    records = []
    for group, selected in enumerate(selections):
        ranks = list(range(selected.start, selected.stop))
        f = float(np.max(abs(first.frequencies_hz[selected]/(second.frequencies_hz[selected]*scale)-1)))
        differences = {name: max(abs(rf[1][i][name]/(rf[0][i][name]*scale**power)-1) for i in ranks)
            for name, power in powers.items()}
        for i in ranks:
            if any(rf[side][i][name] is not None for side in (0, 1) for name in RF_NULLS):
                raise ValueError('covariance retains cutoff accelerating quantities as unavailable')
            for name in ('phasor_convention', 'longitudinal_units', 'accelerating_quantities_reason'):
                if rf[0][i][name] != rf[1][i][name]:
                    raise ValueError(f'covariance RF metadata differs: {name}')
        gates = dict(frequency=f <= 1e-8, electric=bool(errors[group, 0] <= 1e-8),
            magnetic=bool(errors[group, 1] <= 1e-8), all_RF=max(differences.values()) <= 1e-8)
        records.append(dict(ranks_zero_based=ranks, frequency_scale_relative_error=f,
            electric_relative_L2_error=float(errors[group, 0]), magnetic_relative_L2_error=float(errors[group, 1]),
            RF_scale_relative_errors=differences, common_scalar_rotation=rotations[group].tolist(),
            gates=gates, passed=all(gates.values())))
    return dict(groups=records, passed=all(r['passed'] for r in records), first_RF=rf[0], second_RF=rf[1],
        scope='actual independent FEM; complete native affine transform; common scalar group rotation')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    before, started = _implementation_hashes(), time.monotonic()
    (args.out/'implementation-before.json').write_text(json.dumps(before, indent=2)+'\n')
    modules = [Path(__file__), *(Path(__file__).with_name(name) for name in
        ('planar_curved_vector_reference.py', 'planar_curved_shape_reference.py',
         'validate_planar_curved_shapes.py', 'validate_planar_curved_fem.py',
         'validate_planar_curved_rf.py', 'validate_planar_curved_convergence.py'))]
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in modules}
    (args.out/'validator-hashes.json').write_text(json.dumps(hashes, indent=2)+'\n')
    angle = np.pi/9
    rotation = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
    translation, scale = np.array([-.07, .02]), 2.
    records = []
    try:
        for shape in ('circle', 'ellipse', 'corner'):
            domain = (circle_domain(.01, 16) if shape == 'circle' else
                ellipse_domain(16) if shape == 'ellipse' else corner_domain(.01))
            mapped = transformed_domain(domain, scale, rotation, translation)
            for polarization in ('te', 'tm'):
                definition = [g[2] for g in circle_groups(polarization)] if shape == 'circle' else mode_groups(shape, polarization)
                case = PlanarCurvedCase(domain, polarization, modes=sum(definition), max_geometry_boxes=100000000)
                first, second = solve_planar_curved(case), solve_planar_curved(replace(case, domain=mapped))
                for name, solution in (('base', first), ('transformed', second)):
                    folder = args.out/f'{shape}-{polarization}-{name}'
                    folder.mkdir()
                    (folder/'case.json').write_text(json.dumps(solution.case.to_dict(), indent=2)+'\n')
                    np.savez_compressed(folder/'fem-fields.npz', coefficients=solution.coefficients, frequencies_hz=solution.frequencies_hz)
                comparison = compare_covariance(first, second, scale, rotation, translation, definition)
                records.append(dict(shape=shape, polarization=polarization, comparison=comparison))
                (args.out/'progress.json').write_text(json.dumps(records, indent=2)+'\n')
                print(f'{shape}-{polarization}: covariance={comparison["passed"]}', flush=True)
        after = _implementation_hashes()
        if after != before or any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != digest for p, digest in hashes.items()):
            raise ValueError('product or covariance validator changed during validation')
        result = dict(passed=all(r['comparison']['passed'] for r in records), records=records, scale=scale,
            rotation_xy=rotation.tolist(), translation_xy_m=translation.tolist(),
            new_FEM_solves=12, product_files_unchanged=len(after), elapsed_s=time.monotonic()-started,
            scope='discrete covariance of coarse original domains only; no absolute or mesh-convergence acceptance')
        (args.out/'implementation-after.json').write_text(json.dumps(after, indent=2)+'\n')
        (args.out/'report.json').write_text(json.dumps(result, indent=2)+'\n')
        if not result['passed']:
            raise AssertionError('independent FEM covariance gate failed')
    except Exception as exc:
        (args.out/'failed-evidence.json').write_text(json.dumps(dict(error=repr(exc), elapsed_s=time.monotonic()-started), indent=2)+'\n')
        raise


if __name__ == '__main__':
    main()
