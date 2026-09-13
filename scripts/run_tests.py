# SPDX-License-Identifier: Apache-2.0
"""Run the unittest inventory in isolated module processes with live progress.

Module/class fixtures stay together. JSON records retain the discovery inventory,
actual outcomes, process exit codes and durations; missing worker output fails.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import unittest

# Match python -m unittest: repository helpers are importable from the cwd.
sys.path.insert(0, str(Path.cwd()))


def test_ids(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from test_ids(item)
        else:
            yield item.id()


def collect(directory, pattern):
    sys.path.insert(0, str(directory))
    expected = list(test_ids(unittest.TestLoader().discover(str(directory), pattern=pattern)))
    modules = []
    for path in sorted(directory.glob(pattern)):
        if path.is_file() and path.suffix == '.py':
            ids = list(test_ids(unittest.TestLoader().discover(str(directory), pattern=path.name)))
            modules.append({'name': path.stem, 'pattern': path.name, 'test_ids': ids})
    actual = [name for module in modules for name in module['test_ids']]
    if not expected:
        raise ValueError('no tests discovered; check --start-directory and --pattern')
    if Counter(expected) != Counter(actual):
        raise ValueError('module inventory differs from unittest discovery; nested test packages require a separate start directory')
    return expected, modules


def worker(directory, pattern, result_path):
    sys.path.insert(0, str(directory))
    suite = unittest.TestLoader().discover(str(directory), pattern=pattern)
    planned = list(test_ids(suite))
    start = time.monotonic()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {
        'test_ids': planned, 'tests_run': result.testsRun, 'successful': result.wasSuccessful(),
        'failures': [test.id() for test, _ in result.failures],
        'errors': [test.id() for test, _ in result.errors],
        'skipped': [{'id': test.id(), 'reason': reason} for test, reason in result.skipped],
        'expected_failures': [test.id() for test, _ in result.expectedFailures],
        'unexpected_successes': [test.id() for test in result.unexpectedSuccesses],
        'seconds': time.monotonic() - start,
    }
    result_path.write_text(json.dumps(report, indent=2) + '\n')
    return 0 if result.wasSuccessful() else 1


def stop_process(process):
    if os.name == 'posix':
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    elif process.poll() is None:
        process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    finally:
        if os.name == 'posix':
            # Also stop orphaned grandchildren if a worker exited abruptly.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def run_module(module, directory, out, stop):
    record = dict(module)
    log = out / (module['name'] + '.log')
    result = out / (module['name'] + '.json')
    start = time.monotonic()
    environment = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    command = [sys.executable, str(Path(__file__).resolve()), '--start-directory', str(directory),
               '--pattern', module['pattern'], '--worker-result', str(result)]
    if stop.is_set():
        return dict(record, error='cancelled before launch', exit_code=None)
    with log.open('x') as stream:
        process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                   env=environment, start_new_session=os.name == 'posix')
        try:
            while process.poll() is None:
                if stop.wait(.1):
                    stop_process(process)
                    break
        finally:
            stop_process(process)
    record.update(exit_code=process.returncode, seconds=time.monotonic()-start, log=log.name)
    try:
        outcome = json.loads(result.read_text())
        if Counter(outcome['test_ids']) != Counter(module['test_ids']):
            raise ValueError('worker discovery inventory changed')
        record['result'] = outcome
    except (OSError, ValueError, KeyError, TypeError) as error:
        record['error'] = str(error)
    return record


def run(directory, pattern, workers, out):
    out.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    expected, modules = collect(directory, pattern)
    (out/'inventory.json').write_text(json.dumps({'test_ids': expected, 'modules': modules}, indent=2)+'\n')
    workers = min(workers, len(modules))
    print(f'Discovered {len(expected)} tests in {len(modules)} modules; {workers} processes, BLAS threads=1', flush=True)
    records = []
    stop = threading.Event()
    pool = ThreadPoolExecutor(max_workers=workers)
    futures = []
    try:
        futures = [pool.submit(run_module, module, directory, out, stop) for module in modules]
        for future in as_completed(futures):
            record = future.result()
            records.append(record)
            good = record.get('exit_code') == 0 and 'error' not in record and record.get('result', {}).get('successful')
            print(f'[{len(records)}/{len(modules)}] {"PASS" if good else "FAIL"} {record["name"]} ({record.get("seconds",0):.2f}s)', flush=True)
    finally:
        stop.set()
        pool.shutdown(wait=True, cancel_futures=True)
    records.sort(key=lambda row: row['name'])
    results = [row['result'] for row in records if 'result' in row]
    counts = {key: sum(len(result[key]) for result in results)
              for key in ('failures', 'errors', 'skipped', 'expected_failures', 'unexpected_successes')}
    successful = (len(records) == len(modules) and all(row.get('exit_code') == 0 and 'error' not in row
                  and row.get('result', {}).get('successful') for row in records))
    seconds = time.monotonic()-start
    total = sum(result['tests_run'] for result in results)
    report = dict(status='PASS' if successful else 'FAIL', workers=workers, discovered_tests=len(expected),
                  tests_run=total, seconds=seconds, counts=counts, records=records)
    (out/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    with (out/'tests.log').open('x') as log:
        for row in records:
            log.write('\n### '+row['name']+'\n')
            if 'log' in row: log.write((out/row['log']).read_text())
            if 'error' in row: log.write('WORKER ERROR: '+row['error']+'\n')
        log.write(f'\nParallel unittest total: {total} tests in {seconds:.3f}s\n')
        log.write(('OK' if successful else 'FAILED')+' '+json.dumps(counts, sort_keys=True)+'\n')
    print(f'{report["status"]}: {total} tests in {seconds:.3f}s; {counts}', flush=True)
    return 0 if successful else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start-directory', type=Path, default=Path('tests'))
    parser.add_argument('--pattern', default='test*.py')
    parser.add_argument('--workers', type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument('--out', type=Path)
    parser.add_argument('--worker-result', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.workers < 1: parser.error('--workers must be a positive integer')
    directory = args.start_directory.resolve()
    if args.worker_result:
        return worker(directory, args.pattern, args.worker_result)
    if args.out is None: parser.error('--out is required')
    try:
        return run(directory, args.pattern, args.workers, args.out.resolve())
    except KeyboardInterrupt:
        print('Test run interrupted; worker processes stopped.', file=sys.stderr)
        return 130
    except (ValueError, OSError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    raise SystemExit(main())
