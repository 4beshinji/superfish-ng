#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Recover an explicitly stopped fixed RF benchmark's published prefix, without FEM.

Write a separate partial report. An unpublished checkpoint cannot establish a
terminal process cost or become a completed measurement. Native/sample byte
hashes are verified; field reconstruction and similarity remain separate checks.
"""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'scripts')]
import validate_curved_rf_goal_efficiency as benchmark
from superfish_ng.curved_rf_goal_efficiency_saved import _preflight, _same_saved, _verify_costs


def recover_measurements(measurements, out, stop_receipt, stop_sha256):
    """Verify closed JSON/cost decisions; preserve missing rows and original bytes."""
    measurements = Path(measurements).resolve()
    out = benchmark.transport.new_output(out)
    if out.resolve().is_relative_to(measurements):
        raise ValueError('recovery output must be outside the original measurements')
    bindings = {}

    def read(path, expected_sha=None):
        path = Path(path).absolute()
        sha = benchmark.transport.digest(path) if expected_sha is None else expected_sha
        value = benchmark.transport.read_json_binding(str(path), sha)
        bindings[str(path)] = sha
        return value

    def bound(binding, expected_path):
        if Path(binding['path']).resolve() != expected_path.resolve():
            raise ValueError('measurement binding must name its original row directory')
        return read(expected_path, binding['sha256'])

    stop = read(stop_receipt, stop_sha256)
    if stop.get('status') != 'STOPPED_AFTER_USER_CLEARED_GOAL':
        raise ValueError('recovery requires the explicit goal-clear stop receipt')
    plan = read(measurements / 'plan.json')
    _same_saved(plan, benchmark.build_curved_rf_goal_efficiency_plan(), 'original fixed 36 plan')
    before = read(measurements / 'sources-before.json')
    executions = plan['executions']
    paths = sorted(measurements.glob('row-*.json'))
    expected_paths = [measurements / f'row-{i+1:03d}.json' for i in range(len(paths))]
    if paths != expected_paths or len(paths) > len(executions):
        raise ValueError('published measurement rows must be a contiguous fixed-plan prefix')
    attempted = [e['id'] for e in executions if (measurements / e['id']).is_dir()]
    if attempted != [e['id'] for e in executions[:len(attempted)]] or len(attempted) <= len(paths):
        raise ValueError('stopped run must have a contiguous attempted prefix and an unreported row')
    if (type(stop.get('closed_measurement_rows')) is not int or
            stop['closed_measurement_rows'] != len(paths) or
            stop.get('last_active_execution') != attempted[-1]):
        raise ValueError('stop receipt does not match published/attempted prefixes')

    rows = []
    records = []
    for execution, path in zip(executions, paths):
        target = measurements / execution['id']
        row = read(path)
        bundle = bound(row['bundle'], target / 'manifest.json')
        source_before = read(target / 'sources-before.json')
        source_after = read(target / 'sources-after.json')
        if bundle['source_audit']['status'] != 'UNCHANGED' or source_before != before or source_after != before:
            raise ValueError('closed measurement must retain the original unchanged source endpoints')
        record = None
        if row['journal'] is not None:
            journal_path = Path(row['journal']['path']).resolve()
            if journal_path.parent != (target / 'native').resolve():
                raise ValueError('journal must belong to its original native directory')
            record = bound(row['journal'], journal_path)
            _, native_bindings = _preflight(record)
            bindings.update(native_bindings)
            _verify_costs(record)
            if any(Path(run).parent.resolve() != (target / 'native').resolve() for run in record['level_runs']):
                raise ValueError('native events must belong to their original row directory')
            if record.get('schema_version') != 1 or 'resume_origin' in record or record.get('development_event_limit') is not None:
                raise ValueError('closed fixed measurement must be fresh, not resumed or development-capped')
        derived = benchmark.summarize_execution(execution, bundle, record)
        _same_saved({key: row[key] for key in derived}, derived, 'recovered closed measurement')
        rows.append(row)
        records.append((execution, record))

    current = benchmark.source_hashes()
    source_difference = dict(added=sorted(current.keys() - before.keys()),
                             removed=sorted(before.keys() - current.keys()),
                             modified=sorted(k for k in before.keys() & current.keys() if before[k] != current[k]))
    summary = dict(schema_version=1, document_type='curved_rf_goal_interrupted_measurements',
                   status='RECOVERED_INTERRUPTED_PREFIX', rows=rows,
                   completed_measurement_rows=len(rows), observed_execution_directories=len(attempted),
                   unreported_execution_ids=attempted[len(rows):],
                   not_run_execution_ids=[e['id'] for e in executions[len(attempted):]],
                   confirmed_executions=sum(row['confirmed'] for row in rows),
                   completed_journal_events=sum(row['event_count'] for row in rows),
                   comparisons=benchmark.compare_repetitions(rows),
                   closed_row_source_endpoints_unchanged=True,
                   unreported_row_terminal_cost_status='UNKNOWN',
                   whole_run_source_endpoint_status='UNKNOWN',
                   current_analysis_source_difference=source_difference,
                   input_bindings=bindings, new_native_solves=0, physical_error_bound=None,
                   full_saved_replay_status='NOT_RUN_06_REQUIRED',
                   scope='stopped-run published JSON/cost/ancestry prefix and native/sample byte hashes; original outputs read-only; '
                         'no unpublished checkpoint promoted, no missing process cost inferred, '
                         'no native-field reconstruction/reference recomputation/similarity/GUI or fixed36 acceptance; '
                         'stop receipt is operator evidence, not a new process-liveness test')
    # Detect concurrent input changes before publishing any recovered evidence.
    for path, sha in bindings.items():
        if benchmark.transport.digest(path) != sha:
            raise ValueError('recovery input changed during inspection: ' + path)
    out.mkdir(parents=True, exist_ok=False)
    benchmark.export_errors(out / 'errors-vs-dofs-and-time.csv', records)
    benchmark.publish_rf_goal_json(out / 'summary.json', summary)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--measurements', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--stop-receipt', required=True)
    parser.add_argument('--stop-receipt-sha256', required=True)
    args = parser.parse_args(argv)
    summary = recover_measurements(args.measurements, args.out, args.stop_receipt, args.stop_receipt_sha256)
    print(f"{summary['status']}: {summary['completed_measurement_rows']}/36 closed rows")
    return 0


if __name__ == '__main__':
    sys.exit(main())
