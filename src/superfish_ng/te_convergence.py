# SPDX-License-Identifier: Apache-2.0
"""Same-physics TE refinement diagnostics with separate electric/magnetic gates."""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
from .completion import digest
from .fem import triangle_quadrature
from .mesh import element_geometry
from .te import TEFieldSampler, is_te
from .te_saved import read_te_run, _run_names

RF_KEYS = ('geometry_factor_ohm', 'q0', 'wall_loss_w',
           'stored_energy_j', 'electric_energy_j', 'magnetic_energy_j')


def _snapshot(directory, case):
    return {name: digest(directory/name) for name in _run_names(directory,case) | {'te_complete.json'}}


def _integrals(first, second, order):
    """Integrate from both native partitions, in bounded batches, on common support."""
    samplers = [TEFieldSampler(s) for s in (first, second)]
    counts = [s.case.modes for s in (first, second)]
    norms = [np.zeros((2, n)) for n in counts]
    cross = np.zeros((2, *counts))
    total = common = 0.
    samples = 0
    rule = list(triangle_quadrature(order))
    bary = np.array([b for b, w in rule])
    quadrature_weights = np.array([w for b, w in rule])
    for source in (first, second):
        curved = source.case.geometry_order == 2
        if curved:
            maps = source.space.geometry.local_maps
            count = len(maps)
        else:
            vertices, determinants, _ = element_geometry(source.mesh)
            count = len(vertices)
        for start in range(0, count, 128):
            stop = min(start+128, count)
            if curved:
                mapped = [maps[i].evaluate(bary[:, 1:]) for i in range(start, stop)]
                points = np.concatenate([m['points_rz_m'] for m in mapped])
                det = np.concatenate([m['determinant_m2'] for m in mapped])
            else:
                points = np.einsum('qi,cid->cqd', bary, vertices[start:stop]).reshape(-1, 2)
                det = np.repeat(determinants[start:stop], len(rule))
            weights = np.tile(quadrature_weights, stop-start)*det*points[:, 0]/2
            fields = [[sampler.evaluate(points, mode, outside='nan') for mode in range(n)]
                      for sampler, n in zip(samplers, counts)]
            inside = np.logical_and.reduce([v['inside'] for side in fields for v in side])
            total += float(weights.sum())
            common += float(weights[inside].sum())
            samples += int(inside.sum())
            w = weights[inside]
            electric = [np.column_stack([v['Ephi_V_per_m'][inside] for v in side]) for side in fields]
            magnetic = [[np.column_stack([v[key][inside] for v in side]) for key in
                         ('Hr_quadrature_A_per_m', 'Hz_quadrature_A_per_m')] for side in fields]
            for side in range(2):
                norms[side][0] += w @ (electric[side]**2)
                norms[side][1] += sum(w @ (v*v) for v in magnetic[side])
            cross[0] += electric[0].T @ (w[:, None]*electric[1])
            cross[1] += sum(a.T @ (w[:, None]*b) for a, b in zip(*magnetic))
    if common <= 0 or samples < 10 or any(np.any(n <= 0) for n in norms):
        raise ValueError('TE refinement requires nonzero electric/magnetic fields on common volume')
    signed = cross[0]/np.sqrt(np.outer(norms[0][0], norms[1][0]))
    return norms, cross, signed, common/total, samples


def compare_te_refinement(first_directory, second_directory):
    from .studies import _physical_spec
    from . import Case
    paths = [Path(p) for p in (first_directory, second_directory)]
    cases = [Case.load(p/'case.json') for p in paths]
    if not all(is_te(case) for case in cases):
        raise ValueError('TE refinement cannot compare mixed TE/TM physics')
    snapshots = [_snapshot(p, c) for p, c in zip(paths, cases)]
    first, second = [read_te_run(p) for p in paths]
    reflection_comparison = None
    if any(s.reflection_source_case is not None for s in (first,second)):
        if any(s.reflection_source_case is None for s in (first,second)):
            raise ValueError('TE refinement cannot mix ordinary and reflected spectra')
        from .te_saved import _restore_fields, _reflection_metadata
        sources = [s.reflection_source_case for s in (first,second)]
        if _physical_spec(sources[0]) != _physical_spec(sources[1]):
            raise ValueError('TE reflected refinement requires identical source physics and symmetry sector')
        reflection_comparison = dict(domain='reconstructed source half-domain',
            mode_indices='source parity-filtered order; not full-spectrum ranks',
            source_reflections=[_reflection_metadata(c) for c in sources])
        first, second = [_restore_fields(s.reflection_source_case, s.source_mesh_data,
            s.reflection_source_coefficients, s.frequencies_hz) for s in (first,second)]
    if _physical_spec(first.case) != _physical_spec(second.case):
        raise ValueError('TE refinement requires identical physical cases')
    if reflection_comparison is None:
        results = [json.loads((p/'results.json').read_text()) for p in paths]
    else:
        from .te import te_quantities
        results = [dict(modes=[te_quantities(s,i) for i in range(s.case.modes)]) for s in (first,second)]
    low, high = [_integrals(first, second, order) for order in (3, 5)]
    norms, cross, signed, fraction, samples = high
    scores = np.abs(signed)
    rows, columns = linear_sum_assignment(1-scores)
    records = []
    for i, j in zip(rows, columns):
        sign = 1 if signed[i, j] >= 0 else -1
        def errors(integrals):
            ns, cs = integrals[:2]
            return [float(np.sqrt(max(0., ns[0][k, i]+ns[1][k, j]-2*sign*cs[k, i, j])/ns[0][k, i])) for k in range(2)]
        electric, magnetic = errors(high)
        lower = errors(low)
        competing = max(np.max(np.delete(scores[i], j), initial=0), np.max(np.delete(scores[:, j], i), initial=0))
        separated = all(not np.any(np.delete(abs(s.frequencies_hz/s.frequencies_hz[k]-1), k) < .001)
                        for s, k in ((first, i), (second, j)))
        identifiable = bool(scores[i, j] >= .98 and scores[i, j]-competing >= .02 and separated)
        integration_stable = bool(max(abs(electric-lower[0]), abs(magnetic-lower[1]),
                                      abs(scores[i, j]-abs(low[2][i, j]))) < .001)
        a, b = results[0]['modes'][i], results[1]['modes'][j]
        changes = {k: abs(b[k]/a[k]-1) if a[k] else None for k in ('frequency_hz', *RF_KEYS)}
        gates = dict(frequency=changes['frequency_hz'] < .001,
                     electric_field=electric < .01, magnetic_field=magnetic < .01,
                     rf=all(changes[k] is not None and changes[k] < .01 for k in RF_KEYS))
        verified = identifiable and integration_stable and min(fraction, low[3]) >= .999
        records.append(dict(first_mode_index=int(i+1), second_mode_index=int(j+1),
                            field_overlap=float(scores[i, j]), pair_identified=identifiable,
                            electric_relative_l2=electric, magnetic_relative_l2=magnetic,
                            integration_stable=integration_stable, relative_changes=changes,
                            gates=gates, status=('PASS' if all(gates.values()) else 'FAIL') if verified else 'UNVERIFIED'))
    status = ('UNVERIFIED' if first.case.modes != second.case.modes or any(m['status']=='UNVERIFIED' for m in records)
              else 'PASS' if all(m['status']=='PASS' for m in records) else 'FAIL')
    if snapshots != [_snapshot(p, c) for p, c in zip(paths, cases)]:
        raise ValueError('TE refinement source changed during comparison; retry with stable native files')
    result = dict(physics='axisymmetric_m0_te', status=status, modes=records,
                pairing='same physical case; volume-weighted Ephi overlap; unresolved clusters abstain',
                samples=samples, common_volume_fraction=fraction,
                sampling='both native cell partitions, all cells, Duffy orders 3 and 5; common support only',
                limits=dict(frequency=.001, electric_field=.01, magnetic_field=.01, rf=.01,
                            pair_overlap=.98, pair_margin=.02, relative_cluster_gap=.001,
                            integration_absolute_change=.001, common_volume_fraction=.999),
                accelerating_quantities_status='NOT_APPLICABLE: TE axial electric field is zero',
                surface_field='not assessed; sampled volume changes are not physical error bounds')

    if reflection_comparison is not None:
        result['reflection_comparison'] = reflection_comparison
    return result
