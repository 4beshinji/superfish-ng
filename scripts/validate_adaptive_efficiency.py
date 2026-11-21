#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Fixed twelve fresh N05 executions; process exit is not scientific acceptance."""
import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from superfish_ng.adaptive_efficiency_accuracy import LIMITS
from superfish_ng.adaptive_efficiency_plan import build_adaptive_efficiency_plan
from superfish_ng.adaptive_efficiency_process import run_measured_process
from superfish_ng.adaptive_efficiency_reference import load_efficiency_reference, verify_reference_bytes
from superfish_ng.completion import digest
from superfish_ng.project import parse_json


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def source_hashes():
    return {p.relative_to(ROOT).as_posix(): digest(p)
            for name in ('src', 'tests', 'scripts', 'examples')
            for p in sorted((ROOT / name).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def binding(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
        raise ValueError('reference binding requires a regular nonlinked file')
    return dict(path=str(path), sha256=digest(path))


def environment():
    import numpy
    import scipy
    cpu = Path('/proc/cpuinfo').read_text()
    mem = Path('/proc/meminfo').read_text()
    return dict(python=sys.version, executable=sys.executable, numpy=numpy.__version__,
                scipy=scipy.__version__, platform=platform.platform(), cpuinfo=cpu,
                meminfo=mem, blas_threads=os.environ.get('OPENBLAS_NUM_THREADS'),
                gpu_used=False, clock=time.get_clock_info('perf_counter').implementation,
                commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                utc=datetime.now(timezone.utc).isoformat())


def load_worker_record(directory):
    directory = Path(directory)
    if (directory / 'result.json').is_file():
        return parse_json((directory / 'result.json').read_text())
    checkpoints = sorted(directory.glob('checkpoint-*.json'))
    return None if not checkpoints else parse_json(checkpoints[-1].read_text())


def hit(record, key):
    index = None if record is None else record.get(key)
    if index is None:
        return None
    row = record['levels'][index]
    return dict(level_index=index, dofs=row['dofs'], triangles=row['triangles'],
                **row['observed_prefix_cost'])


def summarize(execution, process, record):
    confirmed = bool(process['status'] == 'PROCESS_EXITED' and record is not None and
                     record.get('status') == 'TARGETS_MET' and
                     record.get('development_level_limit') is None and
                     record.get('confirmed_accuracy_hit_index') is not None)
    return dict(execution_id=execution['id'], case_id=execution['case_id'],
                method=execution['method'], repetition=execution['repetition'],
                process_status=process['status'], native_status=None if record is None else record['status'],
                confirmed=confirmed, first_accuracy_hit=hit(record, 'first_accuracy_hit_index'),
                confirmed_accuracy_hit=hit(record, 'confirmed_accuracy_hit_index') if confirmed else None,
                process_wall_seconds=process['wall_seconds'], peak_rss_bytes=process['peak_rss_bytes'],
                level_count=0 if record is None else len(record['levels']),
                final_dofs=None if record is None or not record['levels'] else record['levels'][-1]['dofs'])


def comparisons(rows):
    result = []
    for case in ('cylinder', 'sphere', 'rounded-two-lobe'):
        group = [r for r in rows if r['case_id'] == case]
        accepted = len(group) == 4 and all(r['confirmed'] for r in group)
        methods = {}
        if accepted:
            for method in ('uniform', 'adaptive'):
                selected = [r for r in group if r['method'] == method]
                quantities = {
                    'dofs': [r['confirmed_accuracy_hit']['dofs'] for r in selected],
                    'native_path_seconds': [r['confirmed_accuracy_hit']['native_path_cumulative_seconds'] for r in selected],
                    'confirmed_submission_seconds': [r['confirmed_accuracy_hit']['submission_prefix_wall_seconds'] for r in selected],
                    'full_process_seconds': [r['process_wall_seconds'] for r in selected],
                    'peak_rss_bytes': [r['peak_rss_bytes'] for r in selected]}
                methods[method] = {k: dict(values=v, range=[min(v), max(v)]) for k, v in quantities.items()}
        result.append(dict(case_id=case, status='PRECISION_MATCHED_REPETITIONS' if accepted else 'UNVERIFIED',
                           methods=methods, scope='two fixed repetitions only; finite target/confirmation comparison, no general efficiency superiority claim'))
    return result


def export_errors(path, executions, records):
    columns = ['execution_id', 'case_id', 'method', 'repetition', 'level_index', 'dofs', 'triangles',
               'gauss_order', 'quantity', 'relative_error', 'limit', 'gate', 'native_path_seconds',
               'submission_prefix_seconds', 'native_status']
    with Path(path).open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for execution, record in zip(executions, records):
            for row in [] if record is None else record['levels']:
                for evaluation in row.get('reference_accuracy', []):
                    accuracy = evaluation['accuracy']
                    for quantity, limit in LIMITS.items():
                        writer.writerow(dict(execution_id=execution['id'], case_id=execution['case_id'],
                            method=execution['method'], repetition=execution['repetition'], level_index=row['index'],
                            dofs=row['dofs'], triangles=row['triangles'], gauss_order=evaluation['order'],
                            quantity=quantity, relative_error=accuracy['relative_errors'][quantity], limit=limit,
                            gate=accuracy['gates'][quantity], native_path_seconds=row['observed_prefix_cost']['native_path_cumulative_seconds'],
                            submission_prefix_seconds=row['observed_prefix_cost']['submission_prefix_wall_seconds'],
                            native_status=row['end_of_level_status']))


def plot_errors(out):
    """Separate static scientific figures; no merged accuracy score or fit."""
    with (out / 'errors-vs-dofs-and-time.csv').open() as stream:
        data = list(csv.DictReader(stream))
    if not data:
        return dict(status='NO_OBSERVATIONS', files=[])
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from matplotlib.ticker import MaxNLocator, NullFormatter
    except ImportError:
        return dict(status='MATPLOTLIB_UNAVAILABLE', files=[], csv_preserved=True)
    files = []
    for case in ('cylinder', 'sphere', 'rounded-two-lobe'):
        for x, label in (('dofs', 'Native DOFs'), ('submission_prefix_seconds', 'Submission to end of level (s)')):
            fig, axes = plt.subplots(3, 3, figsize=(15, 11), constrained_layout=True)
            for ax, (quantity, limit) in zip(axes.flat, LIMITS.items()):
                observed=[]
                for method, color in (('uniform', 'tab:blue'), ('adaptive', 'tab:orange')):
                    for repetition in (1, 2):
                        for order in (16, 24):
                            rows = [r for r in data if r['case_id'] == case and r['quantity'] == quantity and
                                    r['method'] == method and int(r['repetition']) == repetition and int(r['gauss_order']) == order and
                                    r['relative_error'] and r[x]]
                            if rows:
                                observed.extend(float(r['relative_error']) for r in rows)
                                ax.plot([float(r[x]) for r in rows], [float(r['relative_error']) for r in rows],
                                        color=color, linestyle='-' if order == 24 else '--', marker='o' if repetition == 1 else 'x',
                                        markersize=3, label=f'{method} rep{repetition} G{order}')
                ax.axhline(limit, color='black', linestyle=':', label='Fixed N05 limit')
                if x=='dofs':
                    ax.set_xscale('log');ax.xaxis.set_minor_formatter(NullFormatter())
                else:ax.xaxis.set_major_locator(MaxNLocator(nbins=5))
                positive=[v for v in observed if v>0]
                upper=max([limit,*observed])*1.5
                if any(v==0 for v in observed):
                    ax.set_yscale('symlog',linthresh=1e-12);ax.set_ylim(0,upper)
                else:
                    ax.set_yscale('log');ax.set_ylim(min([limit,*positive])*.5,upper)
                ax.yaxis.set_minor_formatter(NullFormatter())
                ax.set_title(quantity); ax.set_xlabel(label); ax.set_ylabel('Relative error'); ax.grid(alpha=.2)
            handles,labels=axes.flat[0].get_legend_handles_labels()
            fig.legend(handles,labels,loc='outside lower center',ncol=5,fontsize=8)
            fig.suptitle(case + ': finite full supplied grids; all failed/limited prefixes retained')
            name=f'{case}-errors-vs-{x}.png'
            fig.savefig(out / name, dpi=130); plt.close(fig); files.append(name)
    return dict(status='PLOTS_WRITTEN', files=files, zero_error_display='positive errors use log; zero errors use nonnegative symlog with linear threshold 1e-12',
                scope='separate nine quantities, both Gauss orders and two repetitions; curves do not imply confirmed acceptance')


def run_benchmark(out, bindings):
    if os.environ.get('OPENBLAS_NUM_THREADS') != '1' or sys.platform != 'linux':
        raise ValueError('fixed N05 benchmark requires Linux and OPENBLAS_NUM_THREADS=1 before imports')
    if time.get_clock_info('perf_counter').implementation != 'clock_gettime(CLOCK_MONOTONIC)':
        raise ValueError('submission prefix requires Linux shared CLOCK_MONOTONIC')
    out = Path(out).absolute()
    if out.exists():
        raise FileExistsError(out)
    plan = build_adaptive_efficiency_plan()
    sources = source_hashes()
    # Verify every bound reference before output reservation or any new FEM.
    references = [load_efficiency_reference(row['id'], bindings) for row in plan['cases']]
    shared = {name: parse_json(Path(value['path']).read_text())['shared_preparation_observed_cost']
              for name, value in bindings.items() if name.endswith('_manifest')}
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / 'environment.json', environment())
    write_json(out / 'sources-before.json', sources)
    write_json(out / 'plan.json', plan)
    write_json(out / 'bindings.json', bindings)
    write_json(out / 'shared-reference-preparation.json', shared)
    bindings_sha = digest(out / 'bindings.json')
    rows = []; records = []
    for execution in plan['executions']:
        request_path = out / (execution['id'] + '.json')
        write_json(request_path, execution)
        origin = time.perf_counter()
        argv = [sys.executable, str(Path(__file__).resolve()), '--worker-execution', str(request_path),
                '--execution-sha256', digest(request_path), '--bindings', str(out / 'bindings.json'),
                '--bindings-sha256', bindings_sha, '--out', str(out / execution['id'] / 'native'),
                '--submission-origin', repr(origin)]
        print('START ' + execution['id'], flush=True)
        process = run_measured_process(argv, out / execution['id'] / 'process', cwd=ROOT,
                wall_limit_seconds=execution['wall_limit_seconds'], memory_limit_bytes=execution['memory_limit_bytes'])
        record = load_worker_record(out / execution['id'] / 'native')
        row = summarize(execution, process, record)
        rows.append(row); records.append(record)
        write_json(out / (execution['id'] + '-summary.json'), row)
        print('END ' + execution['id'] + ' ' + process['status'] + ' ' + str(row['native_status']), flush=True)
    for reference in references:
        verify_reference_bytes(reference)
    after = source_hashes()
    write_json(out / 'sources-after.json', after)
    if sources != after:
        raise RuntimeError('benchmark sources changed during twelve executions')
    export_errors(out / 'errors-vs-dofs-and-time.csv', plan['executions'], records)
    summary = dict(document_type='n06_fixed_twelve_efficiency_measurements', executions=rows,
        comparisons=comparisons(rows), source_bytes_unchanged=True, actual_native_executions=len(rows),
        completed_native_levels=sum(r['level_count'] for r in rows),
        partial_failed_level_scope='unfinished native artifacts retained; completed level count does not count an in-flight/failed solve',
        physical_error_bound=None, scope='fixed serial twelve fresh workers; failures/limits retained; shared preparation separate; source/domain/IDs and every quantity preserved in native artifacts')
    write_json(out / 'summary.json', summary)
    write_json(out / 'plots.json', plot_errors(out))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    parser.add_argument('--analytic-reference-manifest')
    parser.add_argument('--rounded-reference-manifest')
    parser.add_argument('--rounded-matrix')
    parser.add_argument('--worker-execution')
    parser.add_argument('--execution-sha256')
    parser.add_argument('--bindings')
    parser.add_argument('--bindings-sha256')
    parser.add_argument('--submission-origin', type=float)
    args = parser.parse_args()
    if args.worker_execution:
        from superfish_ng.adaptive_efficiency_worker import execute_efficiency_worker
        if any(getattr(args, name) for name in ('analytic_reference_manifest', 'rounded_reference_manifest', 'rounded_matrix')):
            parser.error('worker uses only the pinned bindings file')
        for path, expected in ((args.worker_execution, args.execution_sha256), (args.bindings, args.bindings_sha256)):
            if path is None or expected is None or binding(path)['sha256'] != expected:
                raise ValueError('worker execution/bindings SHA256 differs or is missing')
        execution=parse_json(Path(args.worker_execution).read_text())
        bindings=parse_json(Path(args.bindings).read_text())
        if digest(args.worker_execution)!=args.execution_sha256 or digest(args.bindings)!=args.bindings_sha256:
            raise ValueError('worker execution/bindings changed during parsing')
        execute_efficiency_worker(execution, bindings, args.out, submission_origin=args.submission_origin)
    else:
        if any(getattr(args, name) is not None for name in ('execution_sha256', 'bindings', 'bindings_sha256', 'submission_origin')):
            parser.error('worker-only arguments require --worker-execution')
        if not all((args.analytic_reference_manifest, args.rounded_reference_manifest, args.rounded_matrix)):
            parser.error('all three accepted reference manifest/matrix paths are required')
        run_benchmark(args.out, dict(analytic_manifest=binding(args.analytic_reference_manifest),
            rounded_manifest=binding(args.rounded_reference_manifest), rounded_matrix=binding(args.rounded_matrix)))


if __name__ == '__main__':
    main()
