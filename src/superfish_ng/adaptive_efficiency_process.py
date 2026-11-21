# SPDX-License-Identifier: Apache-2.0
"""Linux process costs and sampled resource stops for N06 benchmark workers.

This supervisor measures a single fresh worker, including startup and imports.
It never interprets a zero exit as numerical acceptance. RSS stops are sampled;
the terminal wait4 high-water mark also detects excess between samples.
"""
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def process_peak_rss_bytes(pid):
    """Read the live Linux worker's high-water RSS, or preserve missing data."""
    try:
        with open(f'/proc/{pid}/status', encoding='ascii') as stream:
            for line in stream:
                parts = line.split()
                if parts[:1] == ['VmHWM:'] and len(parts) == 3 and parts[2] == 'kB':
                    value = int(parts[1]) * 1024
                    return value if value > 0 else None
    except (OSError, ValueError):
        pass
    return None


def _seconds(value, name):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError(name + ' must be finite positive seconds')
    return float(value)


def _signal_group(pid, sig):
    try:
        os.killpg(pid, sig)
    except ProcessLookupError:
        pass


def _wait(process, *, blocking=False):
    pid, status, usage = os.wait4(process.pid, 0 if blocking else os.WNOHANG)
    if not pid:
        return None
    process.returncode = os.waitstatus_to_exitcode(status)
    return usage


def _stop(process, grace, poll):
    _signal_group(process.pid, signal.SIGTERM)
    deadline = time.perf_counter() + grace
    usage = None
    while process.returncode is None and time.perf_counter() < deadline:
        usage = _wait(process)
        if usage is not None:
            break
        time.sleep(min(poll, max(0, deadline - time.perf_counter())))
    # The dedicated group is ours; descendants cannot escape cleanup just
    # because the leader exited during TERM grace.
    _signal_group(process.pid, signal.SIGKILL)
    return _wait(process, blocking=True) if process.returncode is None else usage


def run_measured_process(argv, out, *, cwd=None, wall_limit_seconds=3600,
                         memory_limit_bytes=32 * 1024**3, poll_seconds=0.05,
                         terminate_grace_seconds=0.5):
    """Run one Linux worker, preserving logs and terminal costs in a new directory.

    Live memory samples cover the worker and its threads. Terminal wait4 may
    include high-water marks of descendants reaped by that worker; neither is
    concurrent tree RSS. Workers must finish their own work before exiting. Unexpected
    surviving process groups are stopped and marked unverified. No shell runs.
    """
    if sys.platform != 'linux' or not hasattr(os, 'wait4'):
        raise ValueError('N06 process budget recording requires Linux wait4 and /proc')
    if type(argv) not in (list, tuple) or not argv or any(
            type(arg) is not str or not arg or '\0' in arg for arg in argv):
        raise ValueError('argv must be a nonempty sequence of nonempty strings')
    wall = _seconds(wall_limit_seconds, 'wall_limit_seconds')
    poll = _seconds(poll_seconds, 'poll_seconds')
    grace = _seconds(terminate_grace_seconds, 'terminate_grace_seconds')
    if not 0.01 <= poll <= 1:
        raise ValueError('poll_seconds must lie between 0.01 and 1 seconds')
    if type(memory_limit_bytes) is not int or memory_limit_bytes <= 0:
        raise ValueError('memory_limit_bytes must be a positive integer')
    if cwd is not None and not Path(cwd).is_dir():
        raise ValueError('cwd must be an existing directory')
    target = Path(out)
    target.mkdir(parents=True, exist_ok=False)
    request = dict(argv=list(argv), cwd=None if cwd is None else str(Path(cwd).resolve()),
                   wall_limit_seconds=wall, memory_limit_bytes=memory_limit_bytes,
                   poll_seconds=poll, terminate_grace_seconds=grace)
    with (target / 'request.json').open('x', encoding='utf-8') as stream:
        json.dump(request, stream, indent=2)
    process = None
    usage = None
    observed_peak = None
    sample_count = 0
    missing_samples = 0
    status = 'START_FAILED'
    exception_type = None
    started = time.perf_counter()
    try:
        with (target / 'stdout.log').open('xb') as stdout, (target / 'stderr.log').open('xb') as stderr:
            process = subprocess.Popen(argv, cwd=cwd, stdout=stdout, stderr=stderr,
                                       start_new_session=True)
            status = 'RUNNING'
            while True:
                usage = _wait(process)
                if usage is not None:
                    status = 'PROCESS_EXITED' if process.returncode == 0 else 'PROCESS_FAILED'
                    break
                peak = process_peak_rss_bytes(process.pid)
                sample_count += 1
                if peak is None:
                    missing_samples += 1
                else:
                    observed_peak = max(observed_peak or 0, peak)
                if observed_peak is not None and observed_peak > memory_limit_bytes:
                    status = 'MEMORY_LIMIT'
                elif time.perf_counter() - started >= wall:
                    status = 'WALL_LIMIT'
                if status != 'RUNNING':
                    usage = _stop(process, grace, poll)
                    break
                time.sleep(poll)
    except BaseException as error:
        exception_type = type(error).__name__
        status = 'INTERRUPTED' if isinstance(error, KeyboardInterrupt) else 'SUPERVISOR_FAILED'
        if process is not None and process.returncode is None:
            usage = _stop(process, grace, poll)
        raise
    finally:
        group_remaining = False
        if process is not None:
            try:
                os.killpg(process.pid, 0)
                group_remaining = True
            except ProcessLookupError:
                pass
            if group_remaining:
                _signal_group(process.pid, signal.SIGKILL)
                if status == 'PROCESS_EXITED':
                    status = 'PROCESS_TREE_UNVERIFIED'
        terminal_peak = None if usage is None or usage.ru_maxrss <= 0 else int(usage.ru_maxrss) * 1024
        peaks = [v for v in (observed_peak, terminal_peak) if v is not None]
        peak = max(peaks) if peaks else None
        if peak is None and status == 'PROCESS_EXITED':
            status = 'MEMORY_UNVERIFIED'
        if peak is not None and peak > memory_limit_bytes and status == 'PROCESS_EXITED':
            status = 'MEMORY_LIMIT'
        ended = time.perf_counter()
        if status == 'PROCESS_EXITED' and ended - started > wall:
            status = 'WALL_LIMIT'
        result = dict(schema_version=1, document_type='adaptive_efficiency_process_cost',
                      status=status, exit_code=None if process is None else process.returncode,
                      pid=None if process is None else process.pid, exception_type=exception_type,
                      wall_seconds=ended - started, peak_rss_bytes=peak,
                      terminal_peak_rss_bytes=terminal_peak, sampled_peak_rss_bytes=observed_peak,
                      sampled_memory_scope='worker-only VmHWM including threads',
                      terminal_memory_scope='Linux wait4 high-water maximum; may include descendants reaped by worker; not concurrent tree RSS',
                      memory_status='RECORDED' if peak is not None else 'UNKNOWN',
                      samples=sample_count, missing_samples=missing_samples,
                      remaining_group_stopped=group_remaining, request=request,
                      scope='fresh Linux worker wall includes process startup/imports and stop/reap; '
                            'sampled worker RSS includes threads; terminal high-water may include reaped descendants, '
                            'not concurrent tree RSS; sampled stops plus '
                            'terminal wait4 high-water check; no numerical acceptance or continuous '
                            'RSS cap guarantee; separate reference costs remain external')
        with (target / 'process.json').open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2)
            stream.write('\n')
    return result
