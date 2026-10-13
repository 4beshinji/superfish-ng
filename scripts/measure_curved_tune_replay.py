# SPDX-License-Identifier: Apache-2.0
"""Measure owned curved Hphi replay; never generate or solve new trials.

Cold means the first validation in a fresh interpreter after module imports.
Integrity checks can warm OS file pages; this is not a cold-disk benchmark.
Warm validations run independently in the same interpreter. Observed calls
use temporary forwarding wrappers; separate plain timings show their cost.
"""
import argparse
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import threading
import time
from unittest.mock import patch


def fingerprint(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ('src', 'tests', 'scripts', 'examples')
            for p in sorted((root / folder).rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}


def owned_files(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob('*')) if p.is_file()}


def rss_bytes():
    for line in Path('/proc/self/status').read_text().splitlines():
        if line.startswith('VmRSS:'):
            return int(line.split()[1]) * 1024
    raise RuntimeError('Linux VmRSS is required for this local benchmark')


class Observation:
    """Forward calls exactly; count binary bytes/hash payloads and native work."""
    def __init__(self):
        self.counts = {}
        self.inclusive_seconds = {}
        self.binary_bytes_read = 0
        self.binary_read_calls = 0
        self.hash_input_bytes = 0
        self.hash_instances = 0
        self.files_read = set()
        self.stack = ExitStack()

    def wrap(self, name, function):
        def observed(*args, **kwargs):
            self.counts[name] = self.counts.get(name, 0) + 1
            start = time.perf_counter()
            try:
                return function(*args, **kwargs)
            finally:
                self.inclusive_seconds[name] = self.inclusive_seconds.get(name, 0.) + time.perf_counter() - start
        return observed

    def __enter__(self):
        from superfish_ng import curved_hphi, curved_hphi_saved, curved_hphi_tuning_saved
        from superfish_ng import owned_tuning_worker
        targets = {
            'native_reads': curved_hphi_saved.read_curved_hphi_run,
            'matrix_assemblies': curved_hphi.curved_hphi_matrices,
            'history_recomputations': curved_hphi_tuning_saved._recompute,
            'checkpoint_full_verifications': curved_hphi_tuning_saved._verified,
            'prefix_validation': owned_tuning_worker.validate_checkpoint_prefixes,
        }
        # Patch all already imported aliases of these exact functions.
        bindings = [(module, key, value) for name, module in list(sys.modules.items())
                    if name.startswith('superfish_ng.') and module is not None
                    for key, value in list(vars(module).items())]
        for label, function in targets.items():
            wrapper = self.wrap(label, function)
            for module, key, value in bindings:
                if value is function:
                    self.stack.enter_context(patch.object(module, key, wrapper))
        original_sha = hashlib.sha256
        owner = self
        class Hash:
            def __init__(self, wrapped):
                self.wrapped = wrapped
            def update(self, data):
                owner.hash_input_bytes += len(data)
                return self.wrapped.update(data)
            def copy(self):
                return Hash(self.wrapped.copy())
            def __getattr__(self, name):
                return getattr(self.wrapped, name)
        def counted_sha(data=b'', **kwargs):
            owner.hash_instances += 1
            owner.hash_input_bytes += len(data)
            return Hash(original_sha(data, **kwargs))
        self.stack.enter_context(patch.object(hashlib, 'sha256', counted_sha))
        original_open = Path.open
        class BinaryReader:
            def __init__(self, stream, path):
                self.stream, self.path = stream, str(path)
            def account(self, size):
                owner.binary_bytes_read += size
                owner.binary_read_calls += 1
                owner.files_read.add(self.path)
            def read(self, *args):
                data = self.stream.read(*args)
                self.account(len(data))
                return data
            def readline(self, *args):
                data = self.stream.readline(*args)
                self.account(len(data))
                return data
            def readinto(self, buffer):
                count = self.stream.readinto(buffer)
                self.account(count or 0)
                return count
            def __enter__(self):
                self.stream.__enter__()
                return self
            def __exit__(self, *args):
                return self.stream.__exit__(*args)
            def __getattr__(self, name):
                return getattr(self.stream, name)
        def counted_open(path, mode='r', *args, **kwargs):
            stream = original_open(path, mode, *args, **kwargs)
            return BinaryReader(stream, path) if 'b' in mode and 'r' in mode else stream
        self.stack.enter_context(patch.object(Path, 'open', counted_open))
        return self

    def __exit__(self, *args):
        return self.stack.__exit__(*args)

    def report(self):
        return dict(counts=self.counts, inclusive_seconds=self.inclusive_seconds,
                    binary_bytes_read=self.binary_bytes_read, binary_read_calls=self.binary_read_calls,
                    distinct_binary_paths=len(self.files_read), sha256_input_bytes=self.hash_input_bytes,
                    sha256_instances=self.hash_instances,
                    metric_scope='binary bytes through Path.open and SHA256 payload bytes; not physical disk traffic; nested function times are not additive')


def sample(call, observed):
    begin_rss = rss_bytes()
    peak = [begin_rss]
    stop = threading.Event()
    def monitor():
        while not stop.wait(.02):
            peak[0] = max(peak[0], rss_bytes())
    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    observation = Observation() if observed else None
    try:
        start = time.perf_counter()
        if observation is None:
            value = call()
        else:
            with observation:
                value = call()
        seconds = time.perf_counter() - start
    finally:
        stop.set()
        thread.join()
        end_rss = rss_bytes()
        peak[0] = max(peak[0], end_rss)
    return value, dict(wall_seconds=seconds, rss_before_bytes=begin_rss,
                       rss_after_bytes=end_rss, sampled_peak_rss_bytes=peak[0],
                       process_peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                       rss_scope='20 ms sampled operation RSS; process peak is cumulative Linux high-water RSS',
                       observation=None if observation is None else observation.report())


def child(args):
    sys.path.insert(0, str(args.source_root / 'src'))
    from superfish_ng import curved_hphi_tuning_jobs, curved_hphi_tuning_saved
    from superfish_ng.json_codec import parse_json
    import numpy as np
    assert Path(curved_hphi_tuning_jobs.__file__).resolve().is_relative_to(args.source_root.resolve())
    dataset = parse_json(args.histories.read_text())
    case = next(c for c in dataset['cases'] if c['label'] == args.case)
    directory = Path(case['worker'])
    before_source = fingerprint(args.source_root)
    before_owned = owned_files(directory)
    expected = deepcopy(case['result'])
    def operation():
        if case['kind'] == 'worker':
            state = parse_json((directory / 'job.json').read_text())
            manifest = parse_json((directory / 'manifest.json').read_text())
            return curved_hphi_tuning_jobs.verify_curved_hphi_tune_job(directory, state, manifest)
        if case['kind'] == 'checkpoint':
            return curved_hphi_tuning_saved.read_curved_hphi_tune(case['checkpoint'])
        raise ValueError('benchmark case must select worker or completed checkpoint replay')
    # Restoration legitimately reassembles and verifies the stored spectrum.
    # No operation may create a new trial solve or native output.
    def forbidden(*args, **kwargs):
        raise AssertionError('benchmark replay attempted a new trial solve')
    from superfish_ng.curved_hphi import solve_curved_hphi
    solve_bindings = [(module, key) for name, module in list(sys.modules.items())
                      if name.startswith('superfish_ng.') and module is not None
                      for key, value in list(vars(module).items()) if value is solve_curved_hphi]
    rows = []
    with ExitStack() as prohibition:
        for module, key in solve_bindings:
            prohibition.enter_context(patch.object(module, key, forbidden))
        for index in range(args.warm_repeats + 1):
            result, measurements = sample(operation, args.observe)
            assert result == expected, (case['label'], 'replay changed original trials/IDs/decision')
            rows.append(dict(condition='process-cold' if index == 0 else 'same-process-warm',
                             repeat=index, **measurements))
    dofs = []
    for run in expected['trial_runs']:
        with np.load(Path(run) / 'solution/fields.npz', allow_pickle=False) as arrays:
            shape = arrays['coefficients'].shape
            dofs.append(dict(dofs=shape[0], modes=shape[1]))
    assert owned_files(directory) == before_owned
    assert fingerprint(args.source_root) == before_source
    report = dict(status='PASS', label=case['label'], kind=case['kind'], history_length=case['history_length'],
                  tuning_status=expected['status'], worker_status=case['worker_status'], native_trial_sizes=dofs,
                  rows=rows, observer_enabled=args.observe, source_files=len(before_source),
                  source_inventory_sha256=hashlib.sha256(json.dumps(before_source, sort_keys=True).encode()).hexdigest(),
                  source_unchanged=True, owned_file_count=len(before_owned), owned_files_unchanged=True,
                  old_native_report_and_all_ids_decisions_equal=True, new_trial_solves=0,
                  cold_scope='fresh interpreter after benchmark imports, no previous physical validation; integrity prechecks may warm OS pages',
                  warm_scope='same process, independent full operation each time; no benchmark cache',
                  python=sys.version, numpy=np.__version__)
    with args.child_out.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--histories', type=Path, required=True, help='owned histories.json from the documented real-worker preparation')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--source-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--warm-repeats', type=int, default=2)
    parser.add_argument('--case')
    parser.add_argument('--child-out', type=Path)
    parser.add_argument('--observe', action='store_true')
    args = parser.parse_args()
    if args.warm_repeats < 1:
        parser.error('--warm-repeats must be positive')
    args.histories = args.histories.resolve()
    args.source_root = args.source_root.resolve()
    if args.child_out:
        if not args.case:
            parser.error('--child-out requires --case')
        child(args)
        return
    if not args.out:
        parser.error('--out is required for the measurement controller')
    args.out.mkdir(parents=True, exist_ok=False)
    data = json.loads(args.histories.read_text())
    reports = []
    before = fingerprint(args.source_root)
    for case in data['cases']:
        for observe in (False, True):
            name = case['label'] + ('-observed' if observe else '-plain')
            output = args.out / (name + '.json')
            command = [sys.executable, str(Path(__file__).resolve()), '--histories', str(args.histories),
                       '--source-root', str(args.source_root), '--case', case['label'],
                       '--child-out', str(output), '--warm-repeats', str(args.warm_repeats)]
            if observe:
                command.append('--observe')
            with (args.out / (name + '.log')).open('x') as log:
                run = subprocess.run(command, cwd=args.source_root, stdout=log, stderr=subprocess.STDOUT)
            if run.returncode:
                raise RuntimeError(f'measurement failed with code {run.returncode}: {name}; original log retained')
            report = json.loads(output.read_text())
            reports.append(report)
            print(name, [(row['condition'], round(row['wall_seconds'], 6)) for row in report['rows']], flush=True)
    assert fingerprint(args.source_root) == before
    result = dict(status='PASS', source_root=str(args.source_root), source_sha256=before,
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  input_sha256=hashlib.sha256(args.histories.read_bytes()).hexdigest(),
                  reports=reports, source_unchanged=True, new_trial_solves=0,
                  total_measured_operations=sum(len(r['rows']) for r in reports),
                  performance_scope='only declared synthetic owned curved Hphi histories on this host; no general performance/accuracy claim')
    with (args.out / 'report.json').open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
