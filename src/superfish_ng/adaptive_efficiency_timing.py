# SPDX-License-Identifier: Apache-2.0
"""Observed phase costs for N06; no numerical acceptance or budget enforcement.

Nested inclusive times are retained, but each observed interval contributes
only once to exclusive costs. Measurements cover the recorder lifetime; process
startup and separate reference preparation need their own outer measurements.
"""
from contextlib import contextmanager
from copy import deepcopy
from fractions import Fraction
import math
import sys
import threading
import time


def self_peak_rss_bytes():
    """Linux process-lifetime peak RSS; unknown platforms never return fake zero."""
    if sys.platform != 'linux':
        return None
    import resource
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value) * 1024 if value > 0 else None


class PhaseRecorder:
    """Serial nested observations; never substitutes timings for solver evidence."""
    def __init__(self, *, clock=time.perf_counter, rss_reader=self_peak_rss_bytes):
        if not callable(clock) or not callable(rss_reader):
            raise ValueError('clock and rss_reader must be callable')
        self._clock = clock
        self._owner_thread = threading.get_ident()
        self._rss_reader = rss_reader
        self._last = None
        self._timing_errors = []
        self._phases = []
        self._stack = []
        self._finished = None
        self._origin = self._now()

    def _require_owner(self):
        if threading.get_ident() != self._owner_thread:
            raise ValueError('serial phase recorder requires its original thread')

    def _now(self):
        try:
            value = self._clock()
            if type(value) not in (int, float):
                raise ValueError('invalid type')
            value = float(value)
            if not math.isfinite(value) or (self._last is not None and value < self._last):
                raise ValueError('nonfinite or decreasing value')
        except Exception as error:
            self._timing_errors.append(type(error).__name__)
            raise ValueError('clock must provide finite nondecreasing seconds') from error
        self._last = value
        return value

    @contextmanager
    def phase(self, name):
        self._require_owner()
        if self._finished is not None:
            raise ValueError('recorder is finished; new phases are forbidden')
        if type(name) is not str or not name or name.strip() != name:
            raise ValueError('phase name must be a nonempty string without surrounding whitespace')
        index = len(self._phases)
        row = dict(name=name, parent_index=self._stack[-1] if self._stack else None,
                   start=self._now(), end=None, status='OPEN', exception_type=None)
        self._phases.append(row)
        self._stack.append(index)
        original_error = None
        try:
            yield
        except BaseException as error:
            original_error = error
            row['exception_type'] = type(error).__name__
            raise
        finally:
            self._require_owner()
            if not self._stack or self._stack[-1] != index:
                raise ValueError('phases must close in stack order')
            self._stack.pop()
            try:
                row['end'] = self._now()
                row['status'] = 'COMPLETED' if original_error is None else 'FAILED'
            except ValueError:
                row['status'] = 'TIMING_UNKNOWN'
                # An observation failure must not hide the actual solver failure.
                if original_error is None:
                    raise

    def _summary(self, now, *, finished):
        durations = [None if p['end'] is None else Fraction(p['end']) - Fraction(p['start'])
                     for p in self._phases]
        phases = []
        for index, (row, duration) in enumerate(zip(self._phases, durations)):
            children = [durations[i] for i, p in enumerate(self._phases) if p['parent_index'] == index]
            exclusive = None if duration is None or any(v is None for v in children) else duration - sum(children, Fraction(0))
            if exclusive is not None and exclusive < 0:
                raise ValueError('observed child intervals exceed their parent interval')
            phases.append(dict(index=index, name=row['name'], parent_index=row['parent_index'],
                               status=row['status'], exception_type=row['exception_type'],
                               inclusive_seconds=None if duration is None else float(duration),
                               exclusive_seconds=None if exclusive is None else float(exclusive)))
        complete = now is not None and not self._timing_errors and all(v is not None for v in durations)
        wall = None if now is None or self._timing_errors else Fraction(now) - Fraction(self._origin)
        recorded = None if not complete else sum((duration for row, duration in zip(self._phases, durations)
                                                  if row['parent_index'] is None), Fraction(0))
        unattributed = None if wall is None or recorded is None else wall - recorded
        if unattributed is not None and unattributed < 0:
            raise ValueError('observed root intervals exceed total elapsed time')
        try:
            memory = self._rss_reader()
            valid_memory = type(memory) is int and memory > 0
            memory_reason = None if valid_memory else 'peak RSS is unavailable or invalid'
        except Exception as error:
            memory = None
            valid_memory = False
            memory_reason = 'peak RSS reader failed: ' + type(error).__name__
        status = ('TIMING_UNVERIFIED' if self._timing_errors else 'INCOMPLETE' if not finished or self._stack else
                  'FAILED' if any(p['exception_type'] is not None for p in self._phases) else 'COMPLETE')
        return dict(schema_version=1, document_type='adaptive_efficiency_observed_cost',
                    status=status, wall_seconds=None if wall is None else float(wall),
                    recorded_phase_seconds=None if recorded is None else float(recorded),
                    unattributed_seconds=None if unattributed is None else float(unattributed),
                    phases=phases, timing_errors=list(self._timing_errors),
                    peak_rss_bytes=memory if valid_memory else None,
                    memory_status='RECORDED' if valid_memory else 'UNKNOWN', memory_reason=memory_reason,
                    scope='observed serial recorder lifetime and process-lifetime RSS; exclusive phase costs avoid nested double counting; no numerical acceptance, process-start coverage, reference-cost inclusion or resource-limit enforcement')

    def snapshot(self):
        self._require_owner()
        if self._finished is not None:
            return deepcopy(self._finished)
        try:
            now = self._now()
        except ValueError:
            now = None
        return self._summary(now, finished=False)

    def finish(self):
        self._require_owner()
        if self._finished is not None:
            return deepcopy(self._finished)
        if self._stack:
            raise ValueError('cannot finish while an open phase remains')
        try:
            now = self._now()
        except ValueError:
            now = None
        self._finished = self._summary(now, finished=True)
        return deepcopy(self._finished)
