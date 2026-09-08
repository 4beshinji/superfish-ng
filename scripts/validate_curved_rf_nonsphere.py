# SPDX-License-Identifier: Apache-2.0
"""Measure version 5 on two prolate scales against an archived uniform reference.

The reference is a previously validated report, not a fresh solve or an absolute
RF error bound. All version 5 events, including discarded probes, are timed.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import time
from unittest.mock import patch

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
from validate_curved_nonsphere import scaled_request, volume, row, difference
from benchmark_curved_refinement import LIMITS, fingerprints
from superfish_ng import curved_rf_adaptive_refinement as engine


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True,
                        help='directory containing the accepted v4 validation.json and scale reports')
    parser.add_argument('--max-events', type=int, default=12)
    args = parser.parse_args()
    reference = args.reference.resolve()
    paths = [reference/name for name in ('validation.json', 'scale-1.json', 'scale-2.json')]
    archived_bytes = {p.name: p.read_bytes() for p in paths}
    archived = json.loads(archived_bytes['validation.json'])
    if not archived['passed'] or archived['source_changed_during_run']:
        raise ValueError('reference must be a passed, source-stable two-scale validation')
    if archived['reference_difference_limits'] != LIMITS:
        raise ValueError('reference tolerances differ from this comparison')
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=False)
    before = fingerprints(); checks = {}
    reference_hashes = {name: hashlib.sha256(data).hexdigest() for name, data in archived_bytes.items()}
    write(out/'reference-provenance.json', dict(directory=str(reference), sha256=reference_hashes,
          original_source_sha256=archived['source_sha256'],
          scope='Archived accepted numerical reports; reference fields are not recomputed in this run.'))
    for scale in (1, 2):
        old = json.loads(archived_bytes[f'scale-{scale}.json'])
        if old != archived['checks'][str(scale)] or not old['passed']:
            raise ValueError('scale report differs from the accepted aggregate reference')
        request = scaled_request(scale)
        # Keep the exact old source mesh and all physics/accuracy settings.
        request['initial_mesh'] = old['request']['initial_mesh']
        if request != old['request']:
            raise ValueError('current version 4 example differs from the archived request')
        request['schema_version'] = 5; request['max_levels'] = args.max_events
        case = engine.validate_request(request)
        write(out/f'request-{scale}.json', request)
        timings = []; original = engine.solve

        def measured(*a, **kw):
            start = time.perf_counter(); solution = original(*a, **kw)
            solve_seconds = time.perf_counter()-start
            domain_volume = volume(solution.space)
            timings.append((solve_seconds, domain_volume))
            print(f'scale {scale}: solve event {len(timings)}, '
                  f'{len(solution.space.geometry.cell_nodes)} triangles, {solve_seconds:.3f}s', flush=True)
            return solution

        start = time.perf_counter()
        with patch.object(engine, 'solve', measured):
            result = engine.execute(request, out/f'scale-{scale}')
        seconds = time.perf_counter()-start
        assert len(timings) == len(result['levels'])
        rows = [dict(row(level, *timing), parent_event_index=level['parent_event_index'],
                     refinement_kind=level['refinement_kind'], accepted=level['accepted'],
                     uniform_confirmations=level['uniform_confirmations'])
                for level, timing in zip(result['levels'], timings)]
        accepted = result['decision']['accepted_event_indices']
        final = rows[accepted[-1]]
        reference_row = old['uniform'][-1]
        diffs = difference(final, reference_row)
        ritz = all(r['parent_event_index'] is None or
                   r['intervals']['frequency_hz'][0] <= rows[r['parent_event_index']]['intervals']['frequency_hz'][0]*(1+1e-10)
                   for r in rows)
        initial = max(difference(rows[0], old['uniform'][0]).values())
        base_volume = old['uniform'][0]['fixed_domain_volume_m3']
        invariant = max(abs(r['fixed_domain_volume_m3']/base_volume-1) for r in rows)
        native_error = abs(case.curved_contour.volume_m3/(4*math.pi*(.16*scale)*(.08*scale)**2/3)-1)
        passed = (result['status'] == 'TARGETS_MET' and final['uniform_confirmations'] == 2
                  and all(r['quadrature_check']['passed'] for r in rows)
                  and reference_row['dofs'] > max(r['dofs'] for r in rows)
                  and ritz and initial < 1e-10 and invariant < 2e-12 and native_error < 2e-12
                  and all(v is not None and v <= LIMITS[k] for k, v in diffs.items()))
        checks[str(scale)] = dict(passed=passed, status=result['status'], events=rows,
            accepted_event_indices=accepted, reference_differences=diffs,
            reference_dofs=reference_row['dofs'], parent_child_ritz=ritz,
            initial_quantities_relative_difference=initial,
            fixed_volume_invariance_relative_difference=invariant,
            analytic_native_volume_relative_error=native_error,
            workflow_seconds=seconds, all_solve_seconds=sum(t[0] for t in timings),
            archived_v4_workflow_seconds=old['adaptive_workflow_seconds'],
            archived_uniform_confirmation_seconds=old['uniform_confirmation_workflow_seconds'],
            archived_uniform_confirmation_dofs=old['uniform'][old['uniform_confirmation_index']]['dofs'])
        write(out/f'scale-{scale}.json', checks[str(scale)])
        print(f'scale {scale}: {result["status"]}, {len(rows)} solves, {seconds:.3f}s', flush=True)
    a, b = checks['1']['events'], checks['2']['events']
    same_graph = (len(a) == len(b) and all(all(x[k] == y[k] for k in
                  ('triangles', 'dofs', 'parent_event_index', 'refinement_kind', 'accepted', 'uniform_confirmations'))
                  for x, y in zip(a, b)))
    similarity = {k: max(abs(y*(2 if k == 'frequency_hz' else 1)/x-1)
                        for aa, bb in zip(a, b) for x, y in zip(aa['intervals'][k], bb['intervals'][k])) for k in LIMITS}
    volume_similarity = max(abs(bb['fixed_domain_volume_m3']/(8*aa['fixed_domain_volume_m3'])-1)
                            for aa, bb in zip(a, b))
    unchanged = before == fingerprints()
    reference_unchanged = all(p.read_bytes() == archived_bytes[p.name] for p in paths)
    passed = (all(c['passed'] for c in checks.values()) and same_graph and max(similarity.values()) < 2e-8
              and volume_similarity < 2e-12 and unchanged and reference_unchanged)
    write(out/'validation.json', dict(passed=passed, checks=checks, same_event_graph=same_graph,
          similarity_relative_differences=similarity, volume_similarity_relative_difference=volume_similarity,
          reference_difference_limits=LIMITS, source_sha256=before, source_unchanged=unchanged,
          reference_sha256=reference_hashes, reference_unchanged=reference_unchanged,
          environment=dict(python=platform.python_version(), platform=platform.platform(),
                           openblas_num_threads=os.environ.get('OPENBLAS_NUM_THREADS')),
          scope='Synthetic prolate fixed quadratic domain; all probes, selection, assembly, tracking, saving and diagnostic volume integration are included in current workflow time. Historical v4/uniform times are not same-process timing trials. Archived finer uniform differences are not absolute RF error bounds.'))
    print('RF nonsphere '+('PASS' if passed else 'FAIL'), flush=True)
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
